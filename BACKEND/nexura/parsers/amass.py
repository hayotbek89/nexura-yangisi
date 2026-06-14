import json
import re
import logging

from nexura.models.schemas import ParserResult, Vulnerability

logger = logging.getLogger(__name__)


def parse_amass(raw: str) -> ParserResult:
    if not raw or not isinstance(raw, str):
        logger.warning("amass output is empty or invalid")
        return ParserResult(summary="Subdomain topilmadi")

    vulns = []
    seen = set()

    ndjson_results = _try_parse_ndjson(raw)
    if ndjson_results is not None:
        return _parse_amass_ndjson(ndjson_results)

    for line in raw.splitlines():
        try:
            line = line.strip()
            if not line:
                continue
            if "OWASP Amass" in line:
                continue
            if "Subdomain Name" in line and "Source" in line:
                continue
            if "requests completed" in line.lower():
                continue
            if "/" in line and "requests" in line.lower():
                continue

            m = re.match(r"^([a-zA-Z0-9][a-zA-Z0-9._-]+\.[a-zA-Z]{2,})\s+", line)
            if m:
                subdomain = m.group(1).lower()
                if subdomain not in seen:
                    seen.add(subdomain)
                    vulns.append(Vulnerability(
                        name=f"Subdomain: {subdomain}",
                        severity="INFO",
                        description=f"Discovered subdomain: {subdomain}",
                        url=f"https://{subdomain}",
                    ))
        except Exception as e:
            logger.debug("Error parsing amass line: %s", e)
            continue

    if not vulns:
        domain_pattern = re.compile(r"([a-zA-Z0-9][a-zA-Z0-9._-]+\.[a-zA-Z]{2,})")
        for line in raw.splitlines():
            try:
                line = line.strip()
                if not line:
                    continue
                m = domain_pattern.match(line)
                if m:
                    subdomain = m.group(1).lower()
                    if subdomain not in seen:
                        seen.add(subdomain)
                        vulns.append(Vulnerability(
                            name=f"Subdomain: {subdomain}",
                            severity="INFO",
                            description=f"Discovered subdomain: {subdomain}",
                            url=f"https://{subdomain}",
                        ))
            except Exception as e:
                logger.debug("Error in fallback domain parsing: %s", e)
                continue

    return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta subdomain topildi")


def _try_parse_ndjson(raw: str) -> list[dict] | None:
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


def _parse_amass_ndjson(entries: list[dict]) -> ParserResult:
    vulns = []
    seen = set()

    for entry in entries:
        try:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "")
            if not name or name in seen:
                continue
            seen.add(name)

            addresses = entry.get("addresses", [])
            ips_list = []
            for a in addresses:
                if isinstance(a, dict):
                    ip = a.get("ip", "")
                    if ip:
                        ips_list.append(ip)
            ips = ", ".join(ips_list)
            
            desc = f"Discovered subdomain: {name}"
            if ips:
                desc += f" [{ips}]"

            vulns.append(Vulnerability(
                name=f"Subdomain: {name}",
                severity="INFO",
                description=desc,
                url=f"https://{name}",
            ))
        except (ValueError, KeyError, TypeError) as e:
            logger.debug("Error parsing amass entry: %s", e)
            continue

    return ParserResult(vulnerabilities=vulns, summary=f"{len(vulns)} ta subdomain topildi")
