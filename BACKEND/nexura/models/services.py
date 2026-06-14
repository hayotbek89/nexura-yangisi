from __future__ import annotations

WELL_KNOWN_SERVICES: dict[int, str] = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 135: "RPC",
    139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 9200: "Elasticsearch", 27017: "MongoDB",
}

DEFAULT_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143,
                 443, 445, 993, 995, 1433, 1521, 3306, 3389,
                 5432, 5900, 6379, 8080, 8443, 9200, 27017]

KNOWN_SERVICE_PORTS: dict[str, int] = {
    "ssh": 22, "ftp": 21, "telnet": 23, "smtp": 25,
    "dns": 53, "http": 80, "pop3": 110, "imap": 143,
    "https": 443, "mssql": 1433, "mysql": 3306,
    "rdp": 3389, "postgresql": 5432, "redis": 6379,
    "vnc": 5900, "mongodb": 27017,
}


def port_by_service_name(name: str) -> int | None:
    name_lower = name.lower()
    best = None
    best_len = 0
    for service, port in KNOWN_SERVICE_PORTS.items():
        if name_lower == service:
            return port
    for service, port in KNOWN_SERVICE_PORTS.items():
        if service in name_lower and len(service) > best_len:
            best = port
            best_len = len(service)
    return best


def service_by_port(port: int) -> str:
    return WELL_KNOWN_SERVICES.get(port, "unknown")
