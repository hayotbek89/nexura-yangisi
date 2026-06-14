from nexura.models.schemas import PortInfo, ScanPlan, ScanResult, ToolCommand, ToolType, Vulnerability


def test_tool_command():
    cmd = ToolCommand(tool=ToolType.NMAP, args=["-sV", "example.com"], description="test")
    assert cmd.tool == "nmap"
    assert cmd.args[0] == "-sV"


def test_port_info():
    p = PortInfo(port=80, state="open", service="HTTP")
    assert p.port == 80
    assert p.service == "HTTP"


def test_vulnerability():
    v = Vulnerability(name="SQL Injection", severity="CRITICAL", cve="CVE-2024-0001")
    assert v.severity == "CRITICAL"


def test_scan_plan():
    plan = ScanPlan(
        target="example.com",
        intent="test scan",
        tools=[ToolCommand(tool=ToolType.NMAP, args=["-sV", "example.com"], description="test")],
        reasoning="testing",
    )
    assert len(plan.tools) == 1
    assert plan.target == "example.com"


def test_scan_result():
    from datetime import datetime
    result = ScanResult(tool="nmap", target="example.com", success=True, start_time=datetime.now())
    result.ports.append(PortInfo(port=443, state="open", service="HTTPS"))
    result.vulnerabilities.append(Vulnerability(name="Test", severity="LOW"))
    assert len(result.ports) == 1
    assert len(result.vulnerabilities) == 1
