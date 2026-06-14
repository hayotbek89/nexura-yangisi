import re
import xml.etree.ElementTree as ET
import logging

from nexura.models.schemas import ParserResult, PortInfo, Vulnerability

logger = logging.getLogger(__name__)

def parse_nmap(raw: str) -> ParserResult:
    # Try XML parsing first
    if raw.strip().startswith("<?xml") or "<nmaprun" in raw:
        try:
            # Extract XML part if there's garbage around it
            xml_start = raw.find("<?xml")
            if xml_start == -1:
                xml_start = raw.find("<nmaprun")

            xml_content = raw[xml_start:]
            root = ET.fromstring(xml_content)
            return _parse_nmap_xml(root)
        except ET.ParseError as e:
            logger.warning("Nmap XML parse error (malformed XML): %s", e)
            return _parse_nmap_text(raw)
        except ValueError as e:
            logger.warning("Nmap value error (integer parsing failed): %s", e)
            return _parse_nmap_text(raw)
        except Exception as e:
            logger.warning("Nmap XML parsing failed, falling back to regex: %s (%s)", e, type(e).__name__)
            return _parse_nmap_text(raw)

    return _parse_nmap_text(raw)

def _parse_nmap_xml(root: ET.Element) -> ParserResult:
    ports = []
    vulns = []

    for host in root.findall("host"):
        ports_elem = host.find("ports")
        if ports_elem is None:
            logger.debug("No ports element found in host")
            continue
        for port_elem in ports_elem.findall("port"):
            try:
                port_id = int(port_elem.get("portid", "0"))
                if not (1 <= port_id <= 65535):
                    logger.debug("Invalid port number: %d, skipping", port_id)
                    continue
            except (ValueError, TypeError):
                logger.debug("Port ID not numeric, skipping")
                continue
            protocol = port_elem.get("protocol")
            state_elem = port_elem.find("state")
            state = state_elem.get("state") if state_elem is not None else "unknown"

            service_elem = port_elem.find("service")
            service_name = "unknown"
            version = None
            if service_elem is not None:
                service_name = service_elem.get("name") or "unknown"
                product = service_elem.get("product")
                extrainfo = service_elem.get("extrainfo")
                v = service_elem.get("version")
                version_parts = [p for p in [product, v, extrainfo] if p]
                if version_parts:
                    version = " ".join(version_parts)

            ports.append(PortInfo(
                port=port_id,
                state=state,
                service=service_name,
                version=version
            ))

            # Extract script outputs for vulnerabilities
            for script in port_elem.findall("script"):
                script_id = script.get("id")
                output = script.get("output")
                if script_id and output and any(word in script_id.lower() or word in output.lower() for word in ["vuln", "cve", "exploit"]):
                    severity = "MEDIUM" # Default for scripts
                    if "critical" in output.lower(): severity = "CRITICAL"
                    elif "high" in output.lower(): severity = "HIGH"

                    vulns.append(Vulnerability(
                        name=f"Script: {script_id}",
                        severity=severity,
                        description=output[:500]
                    ))

    return ParserResult(
        ports=ports,
        vulnerabilities=vulns,
        summary=f"{len(ports)} port topildi (XML parser)"
    )

def _parse_nmap_text(raw: str) -> ParserResult:
    ports = []
    in_port_section = False

    for line in raw.splitlines():
        if "PORT" in line and "STATE" in line and "SERVICE" in line:
            in_port_section = True
            continue
        if in_port_section:
            if not line.strip() or "TRACEROUTE" in line or "OS DETECTION" in line:
                in_port_section = False
                continue
            m = re.match(r"^(\d+)/(tcp|udp)\s+(\S+)\s+(\S+)?\s*(.*)?", line)
            if m:
                state = m.group(3)
                service = m.group(4) or "unknown"
                version = m.group(5).strip() if m.group(5) else None
                ports.append(PortInfo(
                    port=int(m.group(1)),
                    state=state,
                    service=service,
                    version=version,
                ))

    vulns = []
    for line in raw.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if stripped.startswith("|") and len(stripped) > 2 and stripped[1] in (" ", "_"):
            if any(word in low for word in ["cve-", "cve ", "vulnerability", "vuln"]):
                vulns.append(Vulnerability(name=stripped, severity="UNKNOWN"))

    return ParserResult(
        ports=ports,
        vulnerabilities=vulns,
        summary=f"{len(ports)} port topildi (Regex fallback)",
    )
