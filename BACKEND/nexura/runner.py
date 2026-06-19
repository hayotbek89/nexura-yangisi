from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from nexura import config
from nexura.config import TOOL_PATHS, get_env
from nexura.cve_lookup import CVELookup
from nexura.models.schemas import (
    ParserResult,
    ScanResult,
    ToolCommand,
    ToolType,
    Vulnerability,
)
from nexura.parsers.amass import parse_amass
from nexura.parsers.gobuster import parse_gobuster
from nexura.parsers.network import parse_network
from nexura.parsers.nikto import parse_nikto
from nexura.parsers.nmap import parse_nmap
from nexura.parsers.nuclei import parse_nuclei
from nexura.parsers.sqlmap import parse_sqlmap
from nexura.parsers.whatweb import parse_whatweb
from nexura.scanners.network import NetworkScanner

logger = logging.getLogger(__name__)


_SAFE_ARG_RE = re.compile(r'^[a-zA-Z0-9@.,_/+:=~%?-]+$')


def _sanitize_args(tool: ToolType, args: list[str]) -> list[str]:
    clean = []
    for a in args:
        if not _SAFE_ARG_RE.match(a):
            logger.warning("Blocked dangerous arg for %s: %r", tool.value, a)
            continue
        clean.append(a)
    return clean


def _resolve_binary(tool: ToolType) -> str | None:
    configured = TOOL_PATHS.get(tool.value)
    if configured and os.path.isfile(configured):
        return configured
    return shutil.which(tool.value)


class ScanRunner:
    PARSER_MAP = {}

    @classmethod
    def _init_parser_map(cls):
        if cls.PARSER_MAP:
            return
        cls.PARSER_MAP = {
            ToolType.NMAP: parse_nmap,
            ToolType.NUCLEI: parse_nuclei,
            ToolType.NIKTO: parse_nikto,
            ToolType.SQLMAP: parse_sqlmap,
            ToolType.GOBUSTER: parse_gobuster,
            ToolType.NETWORK: parse_network,
            ToolType.AMASS: parse_amass,
            ToolType.WHATWEB: parse_whatweb,
        }

    def __init__(self):
        num_workers = int(os.getenv("NEXURA_SCANNER_WORKERS", str(min(4, os.cpu_count() or 2))))
        self._executor = ThreadPoolExecutor(max_workers=max(1, num_workers))
        self._cve_lookup = CVELookup()
        self._init_parser_map()

    def close(self):
        self._executor.shutdown(wait=False)

    def run(self, command: ToolCommand, target: str) -> ScanResult:
        tool = command.tool
        start = datetime.now()
        result = ScanResult(tool=tool.value, target=target, start_time=start, success=False)

        if tool == ToolType.NETWORK:
            scanner = NetworkScanner()
            ports_list = []
            for arg in command.args:
                for part in arg.split(","):
                    part = part.strip()
                    if part.isdigit():
                        ports_list.append(int(part))
            return scanner.quick_scan(target, ports_list or None)

        binary = _resolve_binary(tool)
        if not binary:
            result.error = f"{tool.value} topilmadi. O'rnatish kerak."
            result.end_time = datetime.now()
            return result

        safe_args = _sanitize_args(tool, command.args)
        cmd = [binary] + safe_args
        if tool == ToolType.NMAP and "-oX" not in safe_args:
            cmd.insert(1, "-oX")
            cmd.insert(2, "-")

        raw_output, returncode = self._execute(cmd)
        result.raw_output = raw_output

        parsed = self._parse(tool, raw_output)
        result.ports = parsed.ports
        result.vulnerabilities = parsed.vulnerabilities
        result.summary = parsed.summary
        result.success = (returncode == 0)
        result.end_time = datetime.now()

        if result.ports:
            try:
                cve_results = self._enrich_cves_sync(result.ports)
                for cv in cve_results:
                    result.vulnerabilities.append(Vulnerability(
                        name=f"CVE: {cv.cve_id} — {cv.description[:100]}",
                        severity=cv.severity,
                        cve=cv.cve_id,
                        cvss=cv.cvss_score,
                        url=cv.url,
                    ))
            except Exception as e:
                logger.warning("CVE enrichment failed: %s", e, exc_info=True)

        return result

    def _enrich_cves_sync(self, ports: list) -> list:
        all_results = []
        seen = set()
        for port in ports:
            if port.service and port.service != "unknown":
                results = self._cve_lookup.lookup_by_service_sync(port.service, port.version or "")
                for r in results:
                    if r.cve_id not in seen:
                        seen.add(r.cve_id)
                        all_results.append(r)
        return all_results

    async def run_async(self, command: ToolCommand, target: str) -> ScanResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.run, command, target)

    def _execute(self, cmd: list[str]) -> tuple[str, int]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=config.TIMEOUT, env=get_env())
            return (r.stdout or r.stderr, r.returncode)
        except subprocess.TimeoutExpired:
            return (f"TIMEOUT: Skanerlash {config.TIMEOUT} soniyadan oshdi.", -1)
        except Exception as e:
            return (f"ERROR: {e}", -1)

    def _parse(self, tool: ToolType, output: str) -> ParserResult:
        parser = self.PARSER_MAP.get(tool)
        if parser:
            return parser(output)
        return ParserResult(summary=output[:200])

    # ---- Individual tool methods for Claude tool calling ----

    def run_nmap(self, target: str, fast: bool = True) -> dict:
        args = ["-sV", "-sC"]
        if fast:
            args += ["-F"]
        else:
            args += ["-p-"]
        args.append(target)
        tc = ToolCommand(tool=ToolType.NMAP, args=args, description="Port scan")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def run_nuclei(self, target: str, severity: str = "medium,high,critical") -> dict:
        args = ["-severity", severity, target]
        tc = ToolCommand(tool=ToolType.NUCLEI, args=args, description="Vulnerability scan")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def run_nikto(self, target: str) -> dict:
        args = ["-h", target]
        tc = ToolCommand(tool=ToolType.NIKTO, args=args, description="Web server scan")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def run_whatweb(self, target: str) -> dict:
        args = [target]
        tc = ToolCommand(tool=ToolType.WHATWEB, args=args, description="Technology detection")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def run_sqlmap(self, target: str) -> dict:
        args = ["-u", target, "--batch", "--level=1", "--risk=1"]
        tc = ToolCommand(tool=ToolType.SQLMAP, args=args, description="SQL injection test")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def run_gobuster(self, target: str) -> dict:
        args = ["dir", "-u", target, "-w", "/usr/share/wordlists/dirb/common.txt"]
        tc = ToolCommand(tool=ToolType.GOBUSTER, args=args, description="Directory brute-force")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def run_amass(self, target: str) -> dict:
        args = ["enum", "-d", target]
        tc = ToolCommand(tool=ToolType.AMASS, args=args, description="Subdomain enumeration")
        result = self.run(tc, target)
        return self._result_to_dict(result)

    def _result_to_dict(self, result: ScanResult) -> dict:
        return {
            "success": result.success,
            "tool": result.tool,
            "target": result.target,
            "ports": [
                {"port": p.port, "state": p.state, "service": p.service, "version": p.version}
                for p in result.ports
            ],
            "vulnerabilities": [
                {
                    "name": v.name,
                    "severity": v.severity,
                    "port": v.port,
                    "cve": v.cve,
                    "cvss": v.cvss,
                }
                for v in result.vulnerabilities
            ],
            "summary": result.summary,
            "error": result.error,
        }
