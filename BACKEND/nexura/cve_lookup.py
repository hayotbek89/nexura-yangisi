# Inspired by METATRON (MIT License) — github.com/sooryathejas/METATRON
# Adapted and integrated into NEXURA Scanner

from __future__ import annotations

import logging
import time
from collections import OrderedDict

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CVEResult(BaseModel):
    cve_id: str
    description: str
    cvss_score: float | None = None
    severity: str = "UNKNOWN"
    url: str = ""


class CVEDetail(BaseModel):
    cve_id: str
    description: str
    cvss_score: float | None = None
    severity: str = "UNKNOWN"
    published: str | None = None
    url: str = ""


def _cvss_to_severity(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score >= 0.1:
        return "LOW"
    return "UNKNOWN"


class _TTLCache:
    def __init__(self, maxsize: int = 500, ttl: int = 3600):
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: OrderedDict[str, tuple[float, object]] = OrderedDict()

    def get(self, key: str):
        if key not in self._store:
            return None
        ts, value = self._store[key]
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: object):
        if len(self._store) >= self._maxsize:
            self._store.popitem(last=False)
        self._store[key] = (time.time(), value)
        self._store.move_to_end(key)


class CVELookup:
    def __init__(self):
        self._async_client = httpx.AsyncClient(timeout=10.0)
        self._sync_client = httpx.Client(timeout=10.0)
        self._search_cache = _TTLCache(maxsize=500, ttl=3600)
        self._detail_cache = _TTLCache(maxsize=500, ttl=3600)

    async def lookup_by_service(self, service: str, version: str) -> list[CVEResult]:
        if not service or not service.strip():
            return []
        cache_key = f"search:{service}:{version}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        result = await self._circl_search(self._async_client.get, service, version)
        self._search_cache.set(cache_key, result)
        return result

    async def lookup_by_cve(self, cve_id: str) -> CVEDetail | None:
        cache_key = f"detail:{cve_id.upper()}"
        cached = self._detail_cache.get(cache_key)
        if cached is not None:
            return cached
        result = await self._circl_detail(self._async_client.get, cve_id)
        self._detail_cache.set(cache_key, result)
        return result

    async def close(self):
        await self._async_client.aclose()
        self._sync_client.close()

    def lookup_by_service_sync(self, service: str, version: str) -> list[CVEResult]:
        if not service or not service.strip():
            return []
        cache_key = f"search:{service}:{version}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._circl_search_sync(service, version)
        self._search_cache.set(cache_key, result)
        return result

    def lookup_by_cve_sync(self, cve_id: str) -> CVEDetail | None:
        cache_key = f"detail:{cve_id.upper()}"
        cached = self._detail_cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._circl_detail_sync(cve_id)
        self._detail_cache.set(cache_key, result)
        return result

    async def _circl_search(self, http_get, service: str, version: str) -> list[CVEResult]:
        try:
            query = f"{service} {version}" if version and version != "unknown" else service
            url = f"https://cve.circl.lu/api/search/{query}"
            resp = await http_get(url)
            if resp.status_code != 200:
                return []
            return self._extract_cve_results(resp.json())
        except Exception as e:
            logger.warning("CIRCL search failed for %s: %s", service, e)
            return []

    async def _circl_detail(self, http_get, cve_id: str) -> CVEDetail | None:
        try:
            url = f"https://cve.circl.lu/api/cve/{cve_id.upper()}"
            resp = await http_get(url)
            if resp.status_code != 200:
                return None
            return self._extract_cve_detail(cve_id, resp.json())
        except Exception as e:
            logger.warning("CIRCL detail lookup failed for %s: %s", cve_id, e)
            return None

    def _circl_search_sync(self, service: str, version: str) -> list[CVEResult]:
        try:
            query = f"{service} {version}" if version and version != "unknown" else service
            url = f"https://cve.circl.lu/api/search/{query}"
            resp = self._sync_client.get(url)
            if resp.status_code != 200:
                return []
            return self._extract_cve_results(resp.json())
        except Exception as e:
            logger.warning("CIRCL search failed for %s: %s", service, e)
            return []

    def _circl_detail_sync(self, cve_id: str) -> CVEDetail | None:
        try:
            url = f"https://cve.circl.lu/api/cve/{cve_id.upper()}"
            resp = self._sync_client.get(url)
            if resp.status_code != 200:
                return None
            return self._extract_cve_detail(cve_id, resp.json())
        except Exception as e:
            logger.warning("CIRCL detail lookup failed for %s: %s", cve_id, e)
            return None

    def _extract_cve_results(self, data) -> list[CVEResult]:
        rows = data.get("results", []) if isinstance(data, dict) else data
        results = []
        seen = set()
        for item in rows[:5]:
            cve_id = item.get("id", "")
            if not cve_id or cve_id in seen:
                continue
            seen.add(cve_id)
            cvss = item.get("cvss", None)
            if cvss is None:
                cvss = item.get("cvss_score", None)
            cvss = float(cvss) if cvss is not None else None
            desc = item.get("description", "") or item.get("summary", "") or ""
            results.append(CVEResult(
                cve_id=cve_id,
                description=desc[:300],
                cvss_score=cvss,
                severity=_cvss_to_severity(cvss),
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            ))
        if not results:
            logger.info("CIRCL bo'yicha CVE topilmadi")
        return results

    def _extract_cve_detail(self, cve_id: str, data: dict) -> CVEDetail:
        cvss = data.get("cvss", None)
        if cvss is None:
            cvss = data.get("cvss_score", None)
        cvss = float(cvss) if cvss is not None else None
        desc = data.get("description", "") or data.get("summary", "") or ""
        published = data.get("published", None) or data.get("Published", None)
        return CVEDetail(
            cve_id=cve_id.upper(),
            description=desc[:500],
            cvss_score=cvss,
            severity=_cvss_to_severity(cvss),
            published=str(published) if published else None,
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id.upper()}",
        )
