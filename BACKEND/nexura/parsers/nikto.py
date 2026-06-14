import json
import logging

from nexura.models.schemas import ParserResult, Vulnerability

logger = logging.getLogger(__name__)


def parse_nikto(raw: str) -> ParserResult:
    if not raw or not isinstance(raw, str):
        logger.warning("Nikto output is empty or invalid")
        return ParserResult(summary="No nikto output received")

    vulns = []

    data = _try_parse_json(raw)
    if data is not None:
        return _parse_nikto_json(data)

    for line in raw.splitlines():
        try:
            if "+" in line[:2] or "-" in line[:2] or "|" in line:
                clean = line.strip().lstrip("+-| ")
                if clean:
                    sev = _detect_severity(clean)
                    vulns.append(Vulnerability(name=clean[:120], severity=sev))
        except Exception as e:
            logger.debug("Error parsing nikto line: %s", e)
            continue

    return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta xatolik topildi")


def _detect_severity(text: str) -> str:
    low = text.lower()
    critical_kw = ["critical", "exploit", "remote code execution", "rce"]
    high_kw = ["cve-", "vulnerability", "sql injection", "xss", "path traversal"]
    medium_kw = ["warning", "misconfiguration", "information disclosure", "information leak"]
    info_kw = ["info", "notice", "cookie", "header"]
    for kw in critical_kw:
        if kw in low:
            return "CRITICAL"
    for kw in high_kw:
        if kw in low:
            return "HIGH"
    for kw in medium_kw:
        if kw in low:
            return "MEDIUM"
    for kw in info_kw:
        if kw in low:
            return "INFO"
    return "MEDIUM"


def _try_parse_json(raw: str) -> dict | list | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try first non-empty line
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if lines:
        try:
            return json.loads(lines[0])
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _parse_nikto_json(data: dict | list) -> ParserResult:
    vulns = []
    try:
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            for finding in item.get("findings", item.get("vulnerabilities", [item])):
                try:
                    if isinstance(finding, dict):
                        title = finding.get("title", finding.get("name", ""))
                        sev = finding.get("severity", "MEDIUM")
                        desc = finding.get("description", "")
                        if not isinstance(sev, str):
                            sev = "MEDIUM"
                        vulns.append(Vulnerability(
                            name=title[:120] if title else "Unknown finding",
                            severity=sev.upper(),
                            description=str(desc)[:300] if desc else None,
                        ))
                except (ValueError, TypeError) as e:
                    logger.debug("Error parsing nikto finding: %s", e)
                    continue
    except Exception as e:
        logger.warning("Error parsing nikto JSON: %s", e)

    return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta xatolik topildi")
