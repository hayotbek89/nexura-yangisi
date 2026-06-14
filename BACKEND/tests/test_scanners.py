from nexura.scanners.network import DEFAULT_PORTS, WELL_KNOWN_SERVICES, DNSCache, NetworkScanner


def test_well_known_services():
    assert WELL_KNOWN_SERVICES[80] == "HTTP"
    assert WELL_KNOWN_SERVICES[443] == "HTTPS"
    assert WELL_KNOWN_SERVICES[22] == "SSH"
    assert 3306 in WELL_KNOWN_SERVICES


def test_default_ports():
    assert 80 in DEFAULT_PORTS
    assert 443 in DEFAULT_PORTS
    assert 22 in DEFAULT_PORTS
    assert len(DEFAULT_PORTS) > 10


def test_normalize():
    scanner = NetworkScanner()
    assert scanner._normalize("https://example.com/path") == "example.com"
    assert scanner._normalize("http://example.com") == "example.com"
    assert scanner._normalize("example.com") == "example.com"


def test_dns_cache():
    cache = DNSCache(max_entries=10, ttl=60)
    assert cache.max == 10
    assert cache.ttl == 60


def test_detect_technologies_empty_url():
    scanner = NetworkScanner()
    result = scanner.detect_technologies("http://invalid.nonexistent.example")
    assert isinstance(result, dict)
    assert "detected_via" in result
