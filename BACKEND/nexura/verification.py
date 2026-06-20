from __future__ import annotations

import logging
import secrets

import dns.resolver

logger = logging.getLogger(__name__)

_PRIVATE_PREFIXES = ("127.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                     "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                     "172.30.", "172.31.", "192.168.", "0.")
_LOCAL_DOMAINS = ("localhost", "localhost.localdomain", "nexuraai.uz")
_LOOPBACK = ("127.0.0.1", "::1", "0.0.0.0")


def is_private_target(target: str) -> bool:
    t = target.strip().lower()
    if t in _LOCAL_DOMAINS or t in _LOOPBACK:
        return True
    if t.startswith(_PRIVATE_PREFIXES):
        return True
    return False


def extract_domain(target: str) -> str:
    t = target.strip().lower()
    for prefix in ("http://", "https://"):
        if t.startswith(prefix):
            t = t[len(prefix):]
    t = t.split("/")[0].split(":")[0]
    return t


class DomainVerification:
    def generate_token(self) -> str:
        return secrets.token_hex(16)

    def check_txt_record(self, domain: str, expected_token: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            for rdata in answers:
                txt_value = "".join(
                    s.decode() if isinstance(s, bytes) else s
                    for s in rdata.strings
                )
                if txt_value == f"nexura-verify={expected_token}":
                    return True
            return False
        except Exception as e:
            logger.debug("DNS TXT check failed for %s: %s", domain, e)
            return False
