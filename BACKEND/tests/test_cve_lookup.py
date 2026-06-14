from nexura.cve_lookup import CVEDetail, CVEResult, _cvss_to_severity


def test_cvss_to_severity_critical():
    assert _cvss_to_severity(9.5) == "CRITICAL"
    assert _cvss_to_severity(9.0) == "CRITICAL"


def test_cvss_to_severity_high():
    assert _cvss_to_severity(7.5) == "HIGH"
    assert _cvss_to_severity(7.0) == "HIGH"


def test_cvss_to_severity_medium():
    assert _cvss_to_severity(5.5) == "MEDIUM"
    assert _cvss_to_severity(4.0) == "MEDIUM"


def test_cvss_to_severity_low():
    assert _cvss_to_severity(2.5) == "LOW"
    assert _cvss_to_severity(0.1) == "LOW"


def test_cvss_to_severity_unknown():
    assert _cvss_to_severity(None) == "UNKNOWN"
    assert _cvss_to_severity(0.0) == "UNKNOWN"


def test_cve_result_model():
    cve = CVEResult(cve_id="CVE-2024-0001", description="Test vuln", severity="HIGH")
    assert cve.cve_id == "CVE-2024-0001"
    assert cve.severity == "HIGH"
    assert cve.url == ""


def test_cve_detail_model():
    detail = CVEDetail(
        cve_id="CVE-2024-0002",
        description="Critical vuln",
        cvss_score=9.8,
        severity="CRITICAL",
        published="2024-01-15",
    )
    assert detail.cvss_score == 9.8
    assert detail.severity == "CRITICAL"
    assert detail.published == "2024-01-15"


def test_lookup_empty_service():
    from nexura.cve_lookup import CVELookup
    result = CVELookup().lookup_by_service_sync("", "")
    assert result == []
