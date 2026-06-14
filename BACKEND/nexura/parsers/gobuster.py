import json
import re
import logging

from nexura.models.schemas import ParserResult, Vulnerability

logger = logging.getLogger(__name__)


def parse_gobuster(raw: str) -> ParserResult:
    if not raw or not isinstance(raw, str):
        logger.warning("gobuster output is empty or invalid")
        return ParserResult(summary="Yo'l topilmadi")

    urls = []

    data = _try_parse_json(raw)
    if data is not None:
        return _parse_gobuster_json(data)

    for line in raw.splitlines():
        try:
            m = re.match(r"^/(\S+)\s+\(Status:\s*(\d+)\)", line)
            if not m:
                m = re.match(r"^/(\S+)\s+\((\d+)\)", line)
            if m:
                urls.append({"path": f"/{m.group(1)}", "status": m.group(2)})
        except Exception as e:
            logger.debug("Error parsing gobuster line: %s", e)
            continue

    vulns = []
    for u in urls:
        try:
            status = u["status"]
            if status.startswith("20") or status.startswith("30"):
                sev = "info" if status.startswith("30") else "low"
                vulns.append(Vulnerability(
                    name=f"Discovered: {u['path']} ({status})",
                    severity=sev,
                ))
        except Exception as e:
            logger.debug("Error processing gobuster URL: %s", e)
            continue

    return ParserResult(vulnerabilities=vulns, summary=f"{len(urls)} ta yo'l topildi")


def _try_parse_json(raw: str) -> list | None:
    results = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                results.append(data)
        except (json.JSONDecodeError, ValueError):
            pass
    return results if results else None


def _parse_gobuster_json(entries: list[dict]) -> ParserResult:
    vulns = []
    for entry in entries:
        try:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            status = entry.get("status", 0)
            if isinstance(status, int):
                if 200 <= status < 300:
                    sev = "low"
                    vulns.append(Vulnerability(
                        name=f"Discovered: {path} ({status})",
                        severity=sev,
                    ))
                elif 300 <= status < 400:
                    vulns.append(Vulnerability(
                        name=f"Redirect: {path} ({status})",
                        severity="info",
                    ))
        except (ValueError, TypeError, KeyError) as e:
            logger.debug("Error parsing gobuster entry: %s", e)
            continue
    return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta yo'l topildi")
