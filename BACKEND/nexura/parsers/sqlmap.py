import json
import logging

from nexura.models.schemas import ParserResult, Vulnerability

logger = logging.getLogger(__name__)


def parse_sqlmap(raw: str) -> ParserResult:
    if not raw or not isinstance(raw, str):
        logger.warning("sqlmap output is empty or invalid")
        return ParserResult(summary="SQL injection aniqlanmadi")

    vulns = []

    data = _try_parse_json(raw)
    if data is not None:
        return _parse_sqlmap_json(data)

    for line in raw.splitlines():
        try:
            low = line.lower()
            sev = "CRITICAL"
            if "low" in low:
                sev = "LOW"
            elif "medium" in low:
                sev = "MEDIUM"
            elif "high" in low:
                sev = "HIGH"
            if "Parameter:" in line or "Type:" in line or "Title:" in line:
                vulns.append(Vulnerability(name=line.strip()[:120], severity=sev))
            if "is vulnerable" in low:
                vulns.append(Vulnerability(name="SQL Injection", severity=sev))
            if "not injectable" in low and not vulns:
                return ParserResult(vulnerabilities=[], summary="SQL injection topilmadi")
        except Exception as e:
            logger.debug("Error parsing sqlmap line: %s", e)
            continue

    if vulns:
        return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta potentsial SQL injection topildi")
    return ParserResult(vulnerabilities=[], summary="SQL injection aniqlanmadi yoki skaner ishlamadi")


def _try_parse_json(raw: str) -> dict | list | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines:
            return json.loads(lines[0])
    except (json.JSONDecodeError, IndexError):
        pass
    return None


def _parse_sqlmap_json(data: dict | list) -> ParserResult:
    vulns = []

    try:
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for task in data.get("taskdata", []):
                if isinstance(task, dict):
                    items.extend(task.get("data", []))

        for item in items:
            try:
                if isinstance(item, dict):
                    title = item.get("title", "") or ""
                    payload = item.get("payload", "")
                    technique = item.get("technique", "")
                    vulns.append(Vulnerability(
                        name=title[:120] if title else (f"SQL Injection: {technique}" if technique else "SQL Injection"),
                        severity="CRITICAL",
                        description=f"Technique: {technique}, Payload: {payload[:200]}" if payload else None,
                    ))
            except (ValueError, TypeError) as e:
                logger.debug("Error parsing sqlmap finding: %s", e)
                continue
    except Exception as e:
        logger.warning("Error parsing sqlmap JSON: %s", e)

    if vulns:
        return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta SQL injection topildi")
    return ParserResult(vulnerabilities=[], summary="SQL injection aniqlanmadi")
