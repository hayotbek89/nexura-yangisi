from nexura.models.schemas import ParserResult, Vulnerability
import logging

logger = logging.getLogger(__name__)


def parse_nuclei(raw: str) -> ParserResult:
    if not raw or not isinstance(raw, str):
        logger.warning("Nuclei output is empty or invalid type")
        return ParserResult(summary="No nuclei output received")

    vulns = []
    seen = set()
    valid_severities = {"critical", "high", "medium", "low", "info"}

    for line in raw.splitlines():
        if not line.strip():
            continue
        low = line.lower()
        sev = "unknown"
        for s in valid_severities:
            if f"[{s}]" in low:
                sev = s
                break
        if sev == "unknown":
            continue
        try:
            name = line.strip()[:120]
            key = f"{sev}:{name}"
            if key not in seen:
                seen.add(key)
                vulns.append(Vulnerability(name=name, severity=sev.upper()))
        except Exception as e:
            logger.debug("Error parsing nuclei line: %s - %s", line[:50], e)
            continue

    return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta zaiflik topildi")
