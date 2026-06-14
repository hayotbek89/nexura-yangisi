from __future__ import annotations

import re

from nexura.models.schemas import ParserResult, PortInfo
from nexura.models.services import port_by_service_name, service_by_port


def parse_network(
    raw: str,
    *,
    port: int | None = None,
    protocol: str | None = None,
    pid: int | None = None,
) -> ParserResult:
    summary_parts = []
    ports = []

    rows = _parse_netstat(raw) or _parse_ss(raw) or _parse_lsof(raw)

    for row in rows:
        if port is not None and row["port"] != port:
            continue
        if protocol is not None and protocol.upper() != row["proto"].upper():
            continue
        if pid is not None and row["pid"] != pid:
            continue

        ports.append(PortInfo(
            port=row["port"],
            state=row["state"],
            service=row["service"],
            version=row.get("version"),
        ))

    if ports:
        summary_parts.append(f"{len(ports)} listening port(s) found")

    return ParserResult(
        ports=ports,
        summary="; ".join(summary_parts) if summary_parts else None,
    )


def _parse_netstat(raw: str) -> list[dict]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"Proto\s+Local Address", line, re.IGNORECASE):
            header_idx = i
            break

    if header_idx is None:
        return []

    results = []
    for line in lines[header_idx + 1:]:
        parts = line.split()
        if len(parts) < 4:
            continue

        proto = parts[0].upper()
        if proto not in ("TCP", "UDP", "TCP6", "UDP6"):
            continue

        local = parts[1]
        port_str = local.rsplit(":", 1)[-1]
        if not port_str.isdigit():
            continue
        port_num = int(port_str)

        state = parts[3] if proto.startswith("TCP") else "LISTENING"

        pid_str = parts[-1]
        pid_num = int(pid_str) if pid_str.isdigit() else None

        service = service_by_port(port_num)

        results.append({
            "port": port_num,
            "proto": proto,
            "state": _normalize_state(state),
            "service": service,
            "pid": pid_num,
        })

    return results


def _parse_ss(raw: str) -> list[dict]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"(State|Netid)\s", line, re.IGNORECASE):
            header_idx = i
            break

    if header_idx is None:
        return []

    results = []
    for line in lines[header_idx + 1:]:
        parts = line.split()
        if len(parts) < 5:
            continue

        state = parts[0]
        local = parts[3]
        port_str = local.rsplit(":", 1)[-1]
        if not port_str.isdigit():
            continue
        port_num = int(port_str)

        pid_num = None
        users_str = line[line.find("users:("):] if "users:(" in line else ""
        m = re.search(r"pid=(\d+)", users_str)
        if m:
            pid_num = int(m.group(1))

        proto = "TCP"
        if line.startswith("udp"):
            proto = "UDP"

        service = service_by_port(port_num)

        results.append({
            "port": port_num,
            "proto": proto,
            "state": _normalize_state(state),
            "service": service,
            "pid": pid_num,
        })

    return results


def _parse_lsof(raw: str) -> list[dict]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("COMMAND") and "PID" in line:
            header_idx = i
            break

    if header_idx is None:
        return []

    results = []
    for line in lines[header_idx + 1:]:
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue

        pid_str = parts[1]
        pid_num = int(pid_str) if pid_str.isdigit() else None
        name = parts[8]

        proto = parts[7].upper()
        if proto not in ("TCP", "UDP"):
            proto = "TCP"

        name_body = name.split("(")[0].strip()
        host_port = name_body
        if " " in host_port:
            host_port = host_port.rsplit(None, 1)[-1]
        if "->" in host_port:
            host_port = host_port.split("->")[0]

        port_str = host_port.rsplit(":", 1)[-1].strip()
        if port_str.isdigit():
            port_num = int(port_str)
        else:
            port_num = port_by_service_name(port_str)

        if port_num is None:
            continue

        m = re.search(r"\((LISTEN|ESTABLISHED|CLOSE_WAIT|TIME_WAIT)\)", name, re.IGNORECASE)
        state = m.group(1).upper() if m else "LISTENING"

        results.append({
            "port": port_num,
            "proto": proto,
            "state": _normalize_state(state),
            "service": service_by_port(port_num),
            "pid": pid_num,
        })

    return results


def _normalize_state(state: str) -> str:
    s = state.upper().strip()
    mapping = {
        "LISTENING": "LISTEN",
        "LISTEN": "LISTEN",
        "ESTABLISHED": "ESTABLISHED",
        "TIME_WAIT": "TIME_WAIT",
        "CLOSE_WAIT": "CLOSE_WAIT",
    }
    return mapping.get(s, "UNKNOWN")



