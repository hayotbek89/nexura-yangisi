from __future__ import annotations

import json
import logging
import shutil
import socket
import ssl
import subprocess
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import httpx

from nexura import config
from nexura.config import SUBPROCESS_ENV
from nexura.models.schemas import PortInfo, ScanResult
from nexura.models.services import DEFAULT_PORTS, WELL_KNOWN_SERVICES

logger = logging.getLogger(__name__)


class NetworkScanner:
    _executor = ThreadPoolExecutor(max_workers=50)

    def __init__(self):
        self._dns_cache = DNSCache()

    def quick_scan(self, host: str, ports: list[int] | None = None) -> ScanResult:
        target = self._normalize(host)
        start = datetime.now()
        result = ScanResult(tool="network", target=target, start_time=start, success=False)

        ip = self._resolve(target)
        if not ip:
            result.error = f"DNS resolve failed: {target}"
            result.end_time = datetime.now()
            return result

        # SECURITY: Block private IP ranges (SSRF prevention)
        if self._is_private_ip(ip):
            result.error = f"Scanning private IP ranges blocked for security: {ip}"
            result.end_time = datetime.now()
            logger.warning("SSRF attempt blocked: %s -> %s", target, ip)
            return result

        ports = ports or DEFAULT_PORTS
        open_ports = []

        futures = {self._executor.submit(self._tcp_connect, ip, p): p for p in ports}
        for future in as_completed(futures):
            port = futures[future]
            is_open, _ = future.result()
            if is_open:
                open_ports.append(PortInfo(
                    port=port,
                    state="open",
                    service=WELL_KNOWN_SERVICES.get(port, "unknown"),
                ))
        open_ports.sort(key=lambda p: p.port)

        result.ports = open_ports
        result.summary = f"{len(open_ports)}/{len(ports)} ports open"
        result.success = True
        result.end_time = datetime.now()
        return result

    def full_health_check(self, target: str) -> dict:
        hostname = self._normalize(target)
        ip = self._resolve(hostname)
        if not ip:
            return {"target": target, "reachable": False, "error": "DNS resolve failed"}

        info = {"target": target, "ip": ip, "reachable": False, "ports": [], "ssl": {}, "waf": "UNKNOWN"}

        is_open, latency = self._tcp_connect(ip, 80)
        if not is_open:
            is_open, latency = self._tcp_connect(ip, 443)

        info["reachable"] = is_open
        info["latency_ms"] = latency

        if not is_open:
            info["error"] = "Not reachable on ports 80/443"
            return info

        for port in [21, 22, 80, 443, 8080, 8443, 3306, 5432]:
            o, _ = self._tcp_connect(ip, port)
            if o:
                info["ports"].append(port)

        if 443 in info["ports"] or 8443 in info["ports"]:
            info["ssl"] = self._check_ssl(hostname)

        url = f"https://{hostname}" if 443 in info["ports"] else f"http://{hostname}"
        info["waf"] = self._detect_waf(url)

        return info

    def detect_technologies(self, url: str) -> dict:
        hostname = self._normalize(url)
        ip = self._resolve(hostname)
        if ip and self._is_private_ip(ip):
            logger.warning("SSRF blocked in detect_technologies: %s -> %s", url, ip)
            return {"cms": None, "server": None, "language": None, "frameworks": [], "cdn": None, "detected_via": "blocked"}
        result = {
            "cms": None,
            "server": None,
            "language": None,
            "frameworks": [],
            "cdn": None,
            "detected_via": "headers",
        }
        whatweb_path = shutil.which("whatweb")
        if whatweb_path:
            try:
                r = subprocess.run(
                    [whatweb_path, "--log-json=-", url],
                    capture_output=True, text=True, timeout=30,
                    env=SUBPROCESS_ENV,
                )
                if r.stdout:
                    lines = r.stdout.strip().splitlines()
                    for line in lines:
                        try:
                            data = json.loads(line)
                            plugins = data.get("plugins", {}) or data
                            for plugin_name, plugin_data in (plugins.items() if isinstance(plugins, dict) else []):
                                pl = plugin_name.lower()
                                if any(c in pl for c in ["wordpress", "drupal", "joomla", "magento"]):
                                    result["cms"] = plugin_name
                                elif "php" in pl:
                                    v = ""
                                    if isinstance(plugin_data, dict):
                                        v = (
                                            plugin_data.get("version", [""])[0]
                                            if isinstance(plugin_data.get("version"), list)
                                            else ""
                                        )
                                    result["language"] = f"PHP {v}".strip()
                                elif "nginx" in pl or "apache" in pl or "iis" in pl or "caddy" in pl:
                                    result["server"] = plugin_name
                                elif "cloudflare" in pl or "akamai" in pl or "incapsula" in pl:
                                    result["cdn"] = plugin_name
                                elif ("jquery" in pl or "bootstrap" in pl or "react" in pl
                                      or "vue" in pl or "angular" in pl):
                                    result["frameworks"].append(plugin_name)
                        except (json.JSONDecodeError, AttributeError):
                            continue
                    result["detected_via"] = "whatweb"
                    return result
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.warning("whatweb failed: %s", e)

        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True, verify=config.SSL_VERIFY)
            headers = resp.headers
            server = headers.get("server", "")
            if server:
                result["server"] = server
            x_powered = headers.get("x-powered-by", "")
            if x_powered:
                result["language"] = x_powered
            x_gen = headers.get("x-generator", "")
            if "WordPress" in x_gen or "wordpress" in x_gen:
                result["cms"] = "WordPress"
            elif "Drupal" in x_gen:
                result["cms"] = "Drupal"
            if "cf-ray" in headers or "cloudflare" in headers.get("server", "").lower():
                result["cdn"] = "Cloudflare"
            waf = self._detect_waf(url)
            if waf and waf not in ("NONE", "UNKNOWN"):
                result["cdn"] = waf
        except Exception as e:
            logger.warning("Technology detection failed for %s: %s", url, e, exc_info=True)

        return result

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private/reserved ranges (SSRF prevention)"""
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False
            octets = [int(p) for p in parts]
            
            # 127.0.0.0 - 127.255.255.255 (Loopback)
            if octets[0] == 127:
                return True
            # 10.0.0.0 - 10.255.255.255 (Private)
            if octets[0] == 10:
                return True
            # 172.16.0.0 - 172.31.255.255 (Private)
            if octets[0] == 172 and 16 <= octets[1] <= 31:
                return True
            # 192.168.0.0 - 192.168.255.255 (Private)
            if octets[0] == 192 and octets[1] == 168:
                return True
            # 169.254.0.0 - 169.254.255.255 (Link-local)
            if octets[0] == 169 and octets[1] == 254:
                return True
            # 0.0.0.0 - 0.255.255.255 (Current network)
            if octets[0] == 0:
                return True
            # 255.255.255.255 (Broadcast)
            if ip == "255.255.255.255":
                return True
            # IPv6 loopback (::1)
            if ip == "::1":
                return True
            return False
        except (ValueError, IndexError):
            logger.debug("Invalid IP format for private check: %s", ip)
            return False

    def _normalize(self, target: str) -> str:
        target = target.strip().lower()
        for prefix in ["https://", "http://", "ftp://"]:
            if target.startswith(prefix):
                return target[len(prefix):].split("/")[0]
        return target.split("/")[0]

    def _resolve(self, hostname: str) -> str | None:
        try:
            return self._dns_cache.resolve(hostname)
        except Exception:
            return None

    def _tcp_connect(self, ip: str, port: int, timeout: float | None = None) -> tuple[bool, float]:
        if timeout is None:
            timeout = config.SOCKET_TIMEOUT
        start = time.time()
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True, round((time.time() - start) * 1000, 2)
        except Exception as e:
            logger.debug("TCP connect failed to %s:%d: %s", ip, port, e)
            return False, 0.0

    def _check_ssl(self, hostname: str, port: int = 443) -> dict:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        return {"valid": False, "error": "No certificate"}
                    expiry_str = cert.get("notAfter", "")
                    try:
                        expiry = datetime.strptime(expiry_str.replace(" GMT", ""), "%b %d %H:%M:%S %Y")
                        now_utc = datetime.now(timezone.utc)
                        days = (expiry - now_utc).days
                    except Exception:
                        days = -1
                    issuer = ""
                    for part in cert.get("issuer", ()):
                        for k, v in part:
                            if k == "organizationName":
                                issuer = v
                    return {
                        "valid": days > 0,
                        "issuer": issuer,
                        "days_left": days,
                        "protocol": ssock.version(),
                        "cipher": ssock.cipher()[0] if ssock.cipher() else "",
                    }
        except Exception as e:
            return {"valid": False, "error": str(e)[:100]}

    def _detect_waf(self, url: str) -> str:
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            server = resp.headers.get("server", "").lower()
            waf_map = {
                "cloudflare": "Cloudflare", "sucuri": "Sucuri",
                "incapsula": "Imperva", "akamai": "Akamai",
                "f5": "F5 BIG-IP", "barracuda": "Barracuda",
                "fortinet": "Fortinet", "aws": "AWS WAF",
                "modsecurity": "ModSecurity",
            }
            for sig, name in waf_map.items():
                if sig in server:
                    return name
            if "cf-ray" in resp.headers:
                return "Cloudflare"
            return "NONE"
        except Exception as e:
            logger.debug("WAF detection failed for %s: %s", url, e)
            return "UNKNOWN"


class DNSCache:
    def __init__(self, max_entries: int = 1000, ttl: int = 300):
        self.max = max_entries
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = threading.Lock()

    def resolve(self, hostname: str) -> str:
        with self._lock:
            now = time.time()
            if hostname in self._cache:
                ip, ts = self._cache[hostname]
                if now - ts < self.ttl:
                    return ip
            ip = socket.gethostbyname(hostname)
            if len(self._cache) >= self.max:
                self._cache.popitem(last=False)
            self._cache[hostname] = (ip, time.time())
        return ip
