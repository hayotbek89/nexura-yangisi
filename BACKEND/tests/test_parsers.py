import json

from nexura.parsers.amass import parse_amass
from nexura.parsers.gobuster import parse_gobuster
from nexura.parsers.network import parse_network
from nexura.parsers.nikto import parse_nikto
from nexura.parsers.nmap import parse_nmap
from nexura.parsers.nuclei import parse_nuclei
from nexura.parsers.sqlmap import parse_sqlmap

NMAP_OUTPUT = """
Starting Nmap 7.95 ( https://nmap.org )
Nmap scan report for example.com (93.184.216.34)
PORT    STATE    SERVICE
22/tcp  open     SSH
80/tcp  open     HTTP
443/tcp open     HTTPS
8080/tcp closed  HTTP-Alt

Nmap done: 1 IP address scanned
"""

NUCLEI_OUTPUT = """
[critical] test-sqli-1 [http://example.com]
[high] test-xss-2 [http://example.com]
[medium] test-config [http://example.com]
[low] test-info [http://example.com]
"""

NIKTO_OUTPUT = """
- Nikto v2.5.0
+ Server: nginx
+ /: Retrieved x-powered-by header: PHP/7.4.
+ /admin/: Admin login page found.
"""

GOBUSTER_OUTPUT = """
/admin (Status: 200)
/login (Status: 200)
/backup (Status: 403)
/robots.txt (Status: 200)
/admin/login.php (Status: 301)
"""

AMASS_OUTPUT = """
{"name": "sub.example.com", "addresses": [{"ip": "1.2.3.4"}], "tag": "ns", "sources": ["dns"]}
{"name": "mail.example.com", "addresses": [{"ip": "5.6.7.8"}], "tag": "mx", "sources": ["dns"]}
"""

SQLMAP_OUTPUT = json.dumps({
    "taskdata": [{
        "data": [{
            "title": "POST parameter 'id' is vulnerable",
            "payload": "id=1 AND 1=1",
            "technique": "boolean-based blind",
        }],
        "logged-requests": [{"id": 1}],
    }],
})

NETSTAT_OUTPUT = """Proto  Local Address          Foreign Address        State           PID
TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1234
TCP    0.0.0.0:445            0.0.0.0:0              LISTENING       4
UDP    0.0.0.0:500            *:*                                    999
"""


def test_parse_nmap():
    result = parse_nmap(NMAP_OUTPUT)
    open_ports = [p for p in result.ports if p.state == "open"]
    assert len(open_ports) == 3
    assert open_ports[0].port == 22
    assert open_ports[0].service == "SSH"
    assert open_ports[2].port == 443


def test_parse_nuclei():
    result = parse_nuclei(NUCLEI_OUTPUT)
    assert len(result.vulnerabilities) == 4
    assert result.vulnerabilities[0].severity == "CRITICAL"
    assert result.vulnerabilities[1].severity == "HIGH"
    assert "test-sqli" in result.vulnerabilities[0].name


def test_parse_nikto():
    result = parse_nikto(NIKTO_OUTPUT)
    assert len(result.vulnerabilities) > 0


def test_parse_gobuster():
    result = parse_gobuster(GOBUSTER_OUTPUT)
    assert len(result.vulnerabilities) >= 3


def test_parse_amass():
    result = parse_amass(AMASS_OUTPUT)
    assert result.summary is not None
    assert "subdomain" in result.summary.lower() or "topildi" in result.summary


def test_parse_sqlmap():
    result = parse_sqlmap(SQLMAP_OUTPUT)
    assert len(result.vulnerabilities) >= 1


def test_parse_network():
    result = parse_network(NETSTAT_OUTPUT)
    assert len(result.ports) == 3
    result = parse_network(NETSTAT_OUTPUT, port=445)
    assert len(result.ports) == 1 and result.ports[0].port == 445
    result = parse_network(NETSTAT_OUTPUT, protocol="UDP")
    assert len(result.ports) == 1 and result.ports[0].port == 500
    result = parse_network(NETSTAT_OUTPUT, pid=1234)
    assert len(result.ports) == 1 and result.ports[0].port == 135
    result = parse_network("", port=80)
    assert len(result.ports) == 0
    result = parse_network("random text not network output")
    assert len(result.ports) == 0
