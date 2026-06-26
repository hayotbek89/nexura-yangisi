from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexura.models.schemas import PortInfo, ScanPlan, ScanResult, ToolCommand, ToolType, Vulnerability
from nexura.web.app import app


@pytest.fixture
def client():
    from nexura.models.schemas import ScanReport
    runner = MagicMock()
    runner.run_async = AsyncMock(return_value=ScanResult(
        tool="nmap", target="example.com", start_time=datetime.now(), success=True,
    ))
    reporter = MagicMock()
    reporter.create_report.side_effect = lambda target, intent: ScanReport(
        id="test-id", target=target, intent=intent, start_time=datetime.now(),
    )
    reporter.save.return_value = "/reports/test.html"
    scanner = MagicMock()
    scanner.quick_scan.return_value = ScanResult(
        tool="network", target="example.com", start_time=datetime.now(), success=True,
    )
    scanner.detect_technologies.return_value = {"cms": None, "server": "nginx"}
    history_db = MagicMock()
    history_db.get_all_sessions.return_value = []
    history_db.get_stats.return_value = {
        "total_scans": 0, "total_vulns": 0, "critical_count": 0,
        "most_scanned_target": None, "this_week_scans": 0,
    }
    engine = MagicMock()
    engine.is_ready = False
    engine.ask_structured_async = AsyncMock(return_value={
        "target": "example.com", "intent": "test scan",
        "tools": [{"tool": "nmap", "args": ["-sV", "example.com"], "description": "test"}],
        "reasoning": "testing",
    })
    selector = MagicMock()
    selector.create_plan_async = AsyncMock(return_value=ScanPlan(
        target="example.com", intent="test scan",
        tools=[ToolCommand(tool=ToolType.NMAP, args=["-sV", "example.com"], description="test")],
        reasoning="testing",
    ))
    selector.run_agentic_scan_async = AsyncMock(return_value=[])
    cve_lookup = MagicMock()
    cve_lookup.lookup_by_service = AsyncMock(return_value=[])
    cve_lookup.close = AsyncMock()

    app.state.runner = runner
    app.state.reporter = reporter
    app.state.scanner = scanner
    app.state.history_db = history_db
    app.state.engine = engine
    app.state.selector = selector
    app.state.cve_lookup = cve_lookup

    with TestClient(app) as c:
        yield c


class TestAPIChat:
    @patch("nexura.web.app.ask_ollama")
    def test_chat_basic(self, mock_ask, client):
        mock_ask.return_value = {"response": "Salom! Qanday yordam kerak?", "error": False}
        resp = client.post("/api/chat", json={
            "message": "salom",
            "session_id": "test-session",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Salom" in data["response"]
        assert data["scan_data"] is None

    @patch("nexura.web.app.ask_ollama")
    def test_chat_ollama_error(self, mock_ask, client):
        mock_ask.return_value = {"response": "Ollama xatosi", "error": True}
        resp = client.post("/api/chat", json={
            "message": "salom",
        })
        assert resp.status_code == 200
        assert "Ollama xatosi" in resp.json()["response"]


class TestAPIStatus:
    @patch("nexura.web.app._check_tools")
    def test_get_status(self, mock_check_tools, client):
        mock_check_tools.return_value = {"nmap": True, "nuclei": False}
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Nexura Scanner"
        assert "ai_ready" in data
        assert data["tools"]["nmap"] is True


class TestAPIQuickScan:
    def test_quick_scan_success(self, client):
        resp = client.post("/api/quick-scan", json={"target": "example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool"] == "network"
        assert data["success"] is True

    def test_quick_scan_empty_target(self, client):
        resp = client.post("/api/quick-scan", json={"target": ""})
        assert resp.status_code == 200


class TestAPIScan:
    def test_scan_basic(self, client):
        resp = client.post("/api/scan", json={
            "prompt": "test example.com",
            "target": "example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["target"] == "example.com"

    def test_scan_agentic(self, client):
        resp = client.post("/api/scan", json={
            "prompt": "deep scan example.com",
            "target": "example.com",
            "agentic": True,
        })
        assert resp.status_code == 200

    def test_scan_no_target(self, client):
        resp = client.post("/api/scan", json={
            "prompt": "scan something",
        })
        assert resp.status_code == 200

    def test_scan_prompt_too_long(self, client):
        resp = client.post("/api/scan", json={
            "prompt": "x" * 2001,
        })
        assert resp.status_code == 422


class TestAPIHistory:
    def test_get_history(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert resp.json() == {"reports": []}

    def test_get_history_with_data(self, client):
        client.app.state.history_db.get_all_sessions.return_value = [
            {"id": "1", "target": "example.com", "date": "2026-01-01", "status": "completed",
             "total_vulns": 0, "severities": {}, "tools": [], "intent": ""},
        ]
        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reports"]) == 1
        assert data["reports"][0]["target"] == "example.com"


class TestAPIStats:
    def test_get_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scans"] == 0


class TestAPISession:
    def test_get_session_not_found(self, client):
        client.app.state.history_db.get_session.return_value = None
        resp = client.get("/api/history/nonexistent")
        assert resp.status_code == 404
        assert "topilmadi" in resp.json()["error"]

    def test_get_session_found(self, client):
        client.app.state.history_db.get_session.return_value = {
            "id": "abc", "target": "example.com", "vulnerabilities": [], "ports": [],
            "ai_analysis": [], "technologies": {},
        }
        resp = client.get("/api/history/abc")
        assert resp.status_code == 200
        assert resp.json()["id"] == "abc"

    def test_delete_session(self, client):
        client.app.state.history_db.delete_session.return_value = True
        resp = client.delete("/api/history/test-id")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_session_not_found(self, client):
        client.app.state.history_db.delete_session.return_value = False
        resp = client.delete("/api/history/missing")
        assert resp.status_code == 404
