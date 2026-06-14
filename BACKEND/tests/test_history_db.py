import os
from datetime import datetime

from nexura.history_db import HistoryDB, _init_db
from nexura.models.schemas import PortInfo, ScanReport, ScanResult, Vulnerability


def _get_test_db(tmp_path):
    db_path = str(tmp_path / "test_nexura.db")
    db = HistoryDB(db_path=db_path)
    return db, db_path


def test_init_db(tmp_path):
    db_path = str(tmp_path / "test_init.db")
    _init_db(db_path)
    assert os.path.exists(db_path)


def test_save_and_get_session(tmp_path):
    db, db_path = _get_test_db(tmp_path)
    report = ScanReport(
        id="test123",
        target="example.com",
        intent="test scan",
        start_time=datetime(2026, 5, 31, 12, 0, 0),
        end_time=datetime(2026, 5, 31, 12, 5, 0),
        status="completed",
    )
    result = ScanResult(
        tool="nmap",
        target="example.com",
        start_time=datetime(2026, 5, 31, 12, 0, 0),
        success=True,
    )
    result.ports.append(PortInfo(port=80, state="open", service="HTTP"))
    result.vulnerabilities.append(Vulnerability(
        name="Test Vuln", severity="HIGH", cve="CVE-2024-0001"
    ))
    report.results.append(result)

    db.save_session(report)
    sessions = db.get_all_sessions()
    assert len(sessions) >= 1
    found = [s for s in sessions if s["id"] == "test123"]
    assert len(found) == 1
    assert found[0]["target"] == "example.com"
    assert found[0]["total_vulns"] >= 1

    session = db.get_session("test123")
    assert session is not None
    assert len(session["vulnerabilities"]) >= 1
    assert len(session["ports"]) >= 1


def test_delete_session(tmp_path):
    db, db_path = _get_test_db(tmp_path)
    report = ScanReport(
        id="delete_me",
        target="test.com",
        intent="delete test",
        start_time=datetime.now(),
        status="completed",
    )
    db.save_session(report)
    assert db.delete_session("delete_me") is True
    assert db.get_session("delete_me") is None
    assert db.delete_session("nonexistent") is False


def test_get_stats(tmp_path):
    db, db_path = _get_test_db(tmp_path)
    stats = db.get_stats()
    assert "total_scans" in stats
    assert "total_vulns" in stats
    assert "critical_count" in stats
