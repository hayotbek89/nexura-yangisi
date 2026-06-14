from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from nexura.history_db import HistoryDB
from nexura.models.schemas import (
    PortInfo,
    ScanPlan,
    ScanReport,
    ScanResult,
    ToolCommand,
    ToolType,
    Vulnerability,
)
from nexura.report.generator import ReportGenerator
from nexura.runner import ScanRunner


def test_full_scan_save_and_report(tmp_path):
    """End-to-end: scan -> save to DB -> generate report."""
    db_path = str(tmp_path / "integration.db")
    db = HistoryDB(db_path=db_path)
    reporter = ReportGenerator()

    report = ScanReport(
        id="int-test-001",
        target="scanme.org",
        intent="test integration",
        start_time=datetime(2026, 5, 31, 10, 0, 0),
        end_time=datetime(2026, 5, 31, 10, 5, 30),
        status="completed",
    )
    result = ScanResult(
        tool="nmap",
        target="scanme.org",
        start_time=datetime(2026, 5, 31, 10, 0, 0),
        end_time=datetime(2026, 5, 31, 10, 5, 0),
        success=True,
        raw_output="Nmap scan report for scanme.org\n22/tcp open ssh\n80/tcp open http\n443/tcp open https\n",
    )
    result.ports = [
        PortInfo(port=22, state="open", service="SSH", version="OpenSSH 8.9"),
        PortInfo(port=80, state="open", service="HTTP", version="Apache 2.4"),
        PortInfo(port=443, state="open", service="HTTPS", version="Apache 2.4"),
    ]
    result.vulnerabilities = [
        Vulnerability(
            name="Weak SSH Ciphers",
            severity="MEDIUM",
            cve="CVE-2024-9999",
            cvss_score=5.0,
        ),
        Vulnerability(
            name="Missing Security Headers",
            severity="LOW",
            cve="",
        ),
    ]
    report.results.append(result)

    html_path = reporter.save(report, fmt="both")
    assert html_path is not None
    assert os.path.exists(html_path)

    db.save_session(report)

    sessions = db.get_all_sessions()
    assert len(sessions) >= 1
    found = [s for s in sessions if s["id"] == "int-test-001"]
    assert len(found) == 1
    assert found[0]["target"] == "scanme.org"
    assert found[0]["total_vulns"] == 2

    session = db.get_session("int-test-001")
    assert session is not None
    assert len(session["vulnerabilities"]) == 2
    assert len(session["ports"]) == 3

    stats = db.get_stats()
    assert stats["total_scans"] >= 1


def test_scan_plan_execution_flow(tmp_path):
    """Test plan creation and execution flow with mocked runner."""
    report = ScanReport(
        id="flow-test",
        target="test.local",
        intent="port scan",
        start_time=datetime.now(),
        status="running",
    )

    plan = ScanPlan(
        target="test.local",
        intent="port scan",
        reasoning="test",
        tools=[
            ToolCommand(tool=ToolType.NMAP, args=["-sV", "-p", "80,443", "test.local"], description=""),
            ToolCommand(tool=ToolType.NUCLEI, args=["-severity", "medium", "test.local"], description=""),
        ],
    )

    runner = ScanRunner()
    with (
        patch("shutil.which", return_value="/usr/bin/nmap"),
        patch.object(runner, "_execute") as mock_exec,
        patch.object(runner, "_parse") as mock_parse,
    ):
        mock_exec.return_value = ("mock output", 0)
        mock_parse.return_value = type("MockParserResult", (), {
            "ports": [
                PortInfo(port=80, state="open", service="HTTP"),
                PortInfo(port=443, state="open", service="HTTPS"),
            ],
            "vulnerabilities": [],
            "summary": "mock summary",
        })()

        for tc in plan.tools:
            result = runner.run(tc, plan.target)
            report.results.append(result)

    report.end_time = datetime.now()
    report.status = "completed"

    assert len(report.results) == 2
    for r in report.results:
        assert r.success is True
        assert len(r.ports) > 0


def test_runner_execute_binary_not_found(tmp_path):
    """Runner handles missing binary gracefully."""
    runner = ScanRunner()
    tc = ToolCommand(tool=ToolType.NMAP, args=["test.local"], description="")
    with patch("shutil.which", return_value=None):
        result = runner.run(tc, "test.local")
    assert result.success is False
    assert result.error is not None


def test_history_db_persistence(tmp_path):
    """Database persists data across HistoryDB instances."""
    db_path = str(tmp_path / "persist.db")

    db1 = HistoryDB(db_path=db_path)
    report = ScanReport(
        id="persist-test",
        target="persist.test",
        intent="persistence test",
        start_time=datetime.now(),
        status="completed",
    )
    result = ScanResult(tool="nmap", target="persist.test", start_time=datetime.now(), success=True)
    result.vulnerabilities.append(Vulnerability(name="Test Vuln", severity="INFO"))
    report.results.append(result)
    db1.save_session(report)

    db2 = HistoryDB(db_path=db_path)
    sessions = db2.get_all_sessions()
    found = [s for s in sessions if s["id"] == "persist-test"]
    assert len(found) == 1

    stats = db2.get_stats()
    assert stats["total_scans"] >= 1


def test_report_generator_output_exists(tmp_path):
    """ReportGenerator creates output files."""
    reporter = ReportGenerator()
    report = ScanReport(
        id="gen-test",
        target="gen.test",
        intent="generator test",
        start_time=datetime.now(),
        status="completed",
    )
    result = ScanResult(tool="nmap", target="gen.test", start_time=datetime.now(), success=True)
    result.ports.append(PortInfo(port=80, state="open", service="HTTP"))
    report.results.append(result)

    html_path = reporter.save(report, fmt="both")
    assert html_path is not None
    assert os.path.exists(html_path)
    assert Path(html_path).suffix == ".html"
