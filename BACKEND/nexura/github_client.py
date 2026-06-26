from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

import httpx

from nexura import config

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


async def create_repo_from_findings(
    token: str,
    repo_name: str,
    findings: list[dict],
    target: str,
    tool: str,
) -> dict:
    """Create a GitHub repo and push a security report as README."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    readme_content = _build_readme(findings, target, tool)

    async with httpx.AsyncClient(timeout=30) as client:
        # Create repo
        resp = await client.post(
            f"{GITHUB_API}/user/repos",
            headers=headers,
            json={
                "name": repo_name,
                "description": f"NEXURA Security Scan Report — {target}",
                "private": False,
                "auto_init": True,
            },
        )
        if resp.status_code == 422:
            existing = resp.json()
            if "already exists" in str(existing):
                return {"success": True, "repo_url": f"https://github.com/{existing.get('owner', {}).get('login', 'user')}/{repo_name}", "message": "Repo already exists"}
            return {"success": False, "error": existing.get("message", str(existing))}
        if resp.status_code not in (201, 200):
            return {"success": False, "error": resp.json().get("message", f"HTTP {resp.status_code}")}

        repo_data = resp.json()
        full_name = repo_data["full_name"]
        repo_url = repo_data["html_url"]

        # Get default branch
        branch = repo_data.get("default_branch", "main")

        # Get the SHA of the existing README (created by auto_init)
        readme_resp = await client.get(
            f"{GITHUB_API}/repos/{full_name}/contents/README.md",
            headers=headers,
        )
        sha = None
        if readme_resp.status_code == 200:
            sha = readme_resp.json().get("sha")

        # Update README with scan report content
        import base64
        encoded = base64.b64encode(readme_content.encode()).decode()

        update_resp = await client.put(
            f"{GITHUB_API}/repos/{full_name}/contents/README.md",
            headers=headers,
            json={
                "message": f"NEXURA Security Scan Report — {target}",
                "content": encoded,
                "sha": sha,
                "branch": branch,
            },
        )

        if update_resp.status_code not in (200, 201):
            return {"success": True, "repo_url": repo_url, "warning": "Repo created but README update failed", "message": f"Scan report pushed to {repo_url}"}

        # Create a SECURITY.md with detailed findings
        security_md = _build_security_md(findings, target, tool)
        encoded_sec = base64.b64encode(security_md.encode()).decode()
        await client.put(
            f"{GITHUB_API}/repos/{full_name}/contents/SECURITY.md",
            headers=headers,
            json={
                "message": "Add security scan findings",
                "content": encoded_sec,
                "branch": branch,
            },
        )

        return {"success": True, "repo_url": repo_url, "message": f"Hisobot {repo_url} ga yuklandi"}


async def scan_repo(token: str, repo_url: str) -> dict:
    """Clone a GitHub repo and run basic static analysis."""
    import base64

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Parse owner/repo from URL
    match = re.match(r"(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
    if not match:
        # Try as owner/repo format
        match = re.match(r"^([^/]+)/([^/]+)$", repo_url)
    if not match:
        return {"success": False, "error": "Noto'g'ri GitHub repo manzili. Masalan: https://github.com/user/repo yoki user/repo"}

    owner, repo = match.group(1), match.group(2).rstrip("/")
    full_name = f"{owner}/{repo}"

    async with httpx.AsyncClient(timeout=60) as client:
        # Get repo info
        repo_resp = await client.get(f"{GITHUB_API}/repos/{full_name}", headers=headers)
        if repo_resp.status_code != 200:
            return {"success": False, "error": f"Repo topilmadi: {full_name}"}

        repo_data = repo_resp.json()
        default_branch = repo_data.get("default_branch", "main")

        # Get repo contents (tree)
        tree_resp = await client.get(
            f"{GITHUB_API}/repos/{full_name}/git/trees/{default_branch}?recursive=1",
            headers=headers,
        )
        if tree_resp.status_code != 200:
            return {"success": False, "error": "Repo kontenti olinmadi"}

        tree_data = tree_resp.json()
        files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

        # Scan for issues
        issues = []
        alerts = []

        # 1. Check dependency files
        dep_files = {
            "package.json": "npm",
            "requirements.txt": "pip",
            "Pipfile": "pipenv",
            "Cargo.toml": "cargo",
            "go.mod": "go",
            "Gemfile": "bundler",
            "composer.json": "composer",
            "build.gradle": "gradle",
            "pom.xml": "maven",
        }
        found_deps = []
        for f in files:
            fname = f.split("/")[-1]
            if fname in dep_files:
                found_deps.append({"file": f, "manager": dep_files[fname]})
        if found_deps:
            for d in found_deps:
                issues.append({"type": "info", "severity": "info", "title": f"Bog'liqlik fayli: {d['file']}", "detail": f"Paket menejeri: {d['manager']}. Zaifliklar uchun `npm audit` yoki `pip-audit` ishlatish tavsiya etiladi."})
        else:
            issues.append({"type": "info", "severity": "info", "title": "Bog'liqlik fayllari topilmadi", "detail": "Loyihada package.json, requirements.txt kabi fayllar mavjud emas."})

        # 2. Check for secrets / API keys in files (only text files)
        text_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".env", ".ini", ".cfg", ".conf", ".sh", ".bash", ".zsh", ".toml", ".md", ".txt", ".php", ".rb", ".go", ".java", ".rs", ".vue", ".css", ".scss", ".html", ".xml"}
        secret_patterns = [
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
            (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
            (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
            (r'xox[bpsa]-[0-9a-zA-Z-]{10,}', "Slack Token"),
            (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private SSH Key"),
            (r'(?i)password\s*[=:]\s*["\'][^"\']+["\']', "Hardcoded Password"),
            (r'(?i)(?:api[-_]?key|apikey)\s*[=:]\s*["\'][^"\']+["\']', "API Key"),
            (r'(?i)secret\s*[=:]\s*["\'][^"\']+["\']', "Secret Key"),
            (r'(?i)(?:db|database|mongo|postgres|mysql)_url\s*[=:]\s*["\'][^"\']+["\']', "Database URL"),
            (r'(?i)token\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Access Token"),
        ]

        secret_files = [f for f in files if any(f.endswith(ext) for ext in text_extensions) and "node_modules" not in f and ".git" not in f]
        sample_files = secret_files[:30]

        # Fetch file contents in parallel (limit to avoid rate limiting)
        async def check_file(filepath):
            try:
                content_resp = await client.get(
                    f"{GITHUB_API}/repos/{full_name}/contents/{filepath}",
                    headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                )
                if content_resp.status_code != 200:
                    return None
                content = content_resp.text
                findings_in_file = []
                for pattern, label in secret_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        findings_in_file.append({"pattern": label, "count": len(matches), "lines": [i + 1 for i, line in enumerate(content.split("\n")) if re.search(pattern, line)][:5]})
                return {"file": filepath, "findings": findings_in_file}
            except Exception:
                return None

        tasks = [check_file(f) for f in sample_files]
        results = await asyncio.gather(*tasks)

        secret_count = 0
        for r in results:
            if r and r["findings"]:
                secret_count += sum(f["count"] for f in r["findings"])
                for f in r["findings"]:
                    alerts.append({
                        "severity": "high" if "Key" in f["pattern"] or "Secret" in f["pattern"] or "Private" in f["pattern"] else "medium",
                        "title": f"{f['pattern']} — {r['file']}",
                        "detail": f"{f['count']} ta topildi. Qatorlar: {f['lines'][:3]}",
                    })

        if secret_count == 0:
            issues.append({"type": "secret", "severity": "good", "title": "Maxfiy kalitlar topilmadi", "detail": "Maxfiy ma'lumotlar (API key, password) aniqlanmadi."})
        else:
            issues.append({"type": "secret", "severity": "warning", "title": f"{secret_count} ta maxfiy kalit topildi", "detail": f"{secret_count} ta potentsial maxfiy ma'lumot topildi. Ularni environment variable'larga ko'chirish tavsiya etiladi."})

        # 3. Check for .gitignore, LICENSE, README
        if ".gitignore" not in files:
            issues.append({"type": "config", "severity": "medium", "title": ".gitignore topilmadi", "detail": "Loyihada .gitignore fayli mavjud emas. Sensitiv fayllarni tasodifan commit qilish xavfi bor."})
        if "LICENSE" not in [f.upper() for f in files]:
            issues.append({"type": "config", "severity": "low", "title": "LICENCE fayli topilmadi", "detail": "Loyihada litsenziya fayli mavjud emas."})

        # 4. Check for environment files
        env_files = [f for f in files if ".env" in f]
        if env_files:
            for ef in env_files:
                alerts.append({"severity": "critical", "title": f".env fayli commit qilingan: {ef}", "detail": ".env fayllari odatda maxfiy ma'lumotlarni saqlaydi va .gitignore ga qo'shilishi kerak."})

        # Summary
        summary = {
            "total_files": len(files),
            "scanned_files": len(sample_files),
            "dependencies": found_deps,
            "secrets_found": secret_count,
            "alerts": len(alerts),
            "language": repo_data.get("language", "Noma'lum"),
            "repo_url": repo_data["html_url"],
            "default_branch": default_branch,
            "description": repo_data.get("description", ""),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
        }

        return {
            "success": True,
            "summary": summary,
            "issues": issues,
            "alerts": alerts,
        }


def _build_readme(findings: list[dict], target: str, tool: str) -> str:
    lines = [
        f"# NEXURA Security Scan Report — {target}",
        "",
        f"**Tool:** {tool.upper()}  **Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Findings",
        "",
    ]
    for f in findings:
        sev = f.get("severity", "unknown").lower()
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(sev, "⚪")
        lines.append(f"| {icon} | **{f.get('title', 'N/A')}** | {f.get('detail', '')} |")
    if not findings:
        lines.append("Hech qanday zaiflik topilmadi.")
    lines.extend(["", "---", "", "*Generated by NEXURA AI Security Scanner*"])
    return "\n".join(lines)


def _build_security_md(findings: list[dict], target: str, tool: str) -> str:
    lines = [
        "# Security Policy",
        "",
        "## Supported Versions",
        "",
        "| Version | Supported |",
        "|---------|-----------|",
        "| Latest  | ✅ |",
        "",
        "## Scanning Results",
        "",
        f"**Target:** {target}  ",
        f"**Tool:** {tool.upper()}  ",
        f"**Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "### Vulnerabilities Found",
        "",
    ]
    for f in findings:
        sev = f.get("severity", "unknown").lower()
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(sev, "⚪")
        lines.append(f"- {icon} **{f.get('title', 'N/A')}** (Severity: {sev.upper()})")
        if f.get("detail"):
            lines.append(f"  - {f['detail']}")
    if not findings:
        lines.append("Hech qanday zaiflik topilmadi.")
    return "\n".join(lines)
