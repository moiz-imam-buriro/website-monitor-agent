import ipaddress
import socket
import httpx
import pytest
import ssl
import time
import dns.resolver
from app.core.config import settings
from app.monitoring import checks


@pytest.fixture(autouse=True)
def safe_env(monkeypatch):
    """Guard fully on, and DNS faked so tests never touch the internet."""
    monkeypatch.setattr(settings, "allow_private_targets", False)

    def fake_getaddrinfo(host, port, *args, **kwargs):
        try:
            ipaddress.ip_address(host)
            ip = host  # real IP addresses stay as they are
        except ValueError:
            ip = "93.184.216.34"  # any domain "resolves" to a public IP
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def fake_site(handler):
    return httpx.MockTransport(handler)


def test_healthy_page():
    transport = fake_site(lambda request: httpx.Response(200, text="<html>hello</html>"))
    result = checks.check_page("https://site.test/", transport=transport)
    assert result.ok
    assert result.status_code == 200
    assert result.issues == []


def test_404_page():
    transport = fake_site(lambda request: httpx.Response(404, text="nope"))
    result = checks.check_page("https://site.test/missing", transport=transport)
    assert not result.ok
    assert "404" in result.issues[0]


def test_500_page():
    transport = fake_site(lambda request: httpx.Response(500, text="boom"))
    result = checks.check_page("https://site.test/", transport=transport)
    assert not result.ok
    assert "500" in result.issues[0]


def test_empty_page():
    transport = fake_site(lambda request: httpx.Response(200, text=""))
    result = checks.check_page("https://site.test/", transport=transport)
    assert any("empty" in issue for issue in result.issues)


def test_slow_page(monkeypatch):
    monkeypatch.setattr(checks, "SLOW_RESPONSE_MS", -1)  # everything counts as slow
    transport = fake_site(lambda request: httpx.Response(200, text="ok"))
    result = checks.check_page("https://site.test/", transport=transport)
    assert any("slow" in issue for issue in result.issues)


def _raising(exc):
    def handler(request):
        raise exc

    return fake_site(handler)


def test_timeout_is_classified():
    result = checks.fetch_url("https://site.test/", transport=_raising(httpx.ConnectTimeout("timed out")))
    assert result.error_type == "timeout"


def test_dns_failure_is_classified():
    exc = httpx.ConnectError("[Errno 11001] getaddrinfo failed")
    result = checks.fetch_url("https://site.test/", transport=_raising(exc))
    assert result.error_type == "dns"


def test_connection_refused_is_classified():
    exc = httpx.ConnectError("All connection attempts failed")
    result = checks.fetch_url("https://site.test/", transport=_raising(exc))
    assert result.error_type == "connection"


def test_ssl_failure_is_classified():
    exc = httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    result = checks.fetch_url("https://site.test/", transport=_raising(exc))
    assert result.error_type == "ssl"


def test_follows_redirect():
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, text="new page")

    result = checks.fetch_url("https://site.test/old", transport=fake_site(handler))
    assert result.status_code == 200
    assert result.final_url.endswith("/new")
    assert len(result.redirects) == 1


def test_redirect_to_private_address_is_blocked():
    transport = fake_site(
        lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
    )
    result = checks.fetch_url("https://site.test/", transport=transport)
    assert result.error_type == "unsafe"


def test_redirect_loop_is_stopped():
    transport = fake_site(
        lambda request: httpx.Response(302, headers={"location": "/loop"})
    )
    result = checks.fetch_url("https://site.test/loop", transport=transport)
    assert result.error_type == "redirect"


def test_api_valid_json():
    transport = fake_site(lambda request: httpx.Response(200, json={"status": "ok"}))
    result = checks.check_api_endpoint("https://site.test/api/health", transport=transport)
    assert result.ok


def test_api_invalid_json():
    transport = fake_site(
        lambda request: httpx.Response(
            200, text="{broken", headers={"content-type": "application/json"}
        )
    )
    result = checks.check_api_endpoint("https://site.test/api/data", transport=transport)
    assert any("not valid JSON" in issue for issue in result.issues)


def test_api_returns_html_error_page():
    transport = fake_site(
        lambda request: httpx.Response(
            200, text="<html>Error</html>", headers={"content-type": "text/html"}
        )
    )
    result = checks.check_api_endpoint("https://site.test/api/data", transport=transport)
    assert any("HTML" in issue for issue in result.issues)


def test_build_url():
    assert checks.build_url("https://a.com/", "/login") == "https://a.com/login"
    assert checks.build_url("https://a.com", "https://b.com/x") == "https://b.com/x"

def _cert_expiring_in(days):
    expires = time.gmtime(time.time() + days * 86400 + 3600)
    return {"notAfter": time.strftime("%b %d %H:%M:%S %Y GMT", expires)}


@pytest.fixture(autouse=True)
def no_real_ssl(monkeypatch):
    """Tests never open a real TLS connection: the certificate is faked."""
    monkeypatch.setattr(checks, "_get_cert", lambda host, port=443: _cert_expiring_in(90))


def make_site(pages):
    """pages: {path: (status, content_type, body)}. Unknown paths give 404."""

    def handler(request):
        status, content_type, body = pages.get(
            request.url.path, (404, "text/plain", "not found")
        )
        return httpx.Response(
            status, headers={"content-type": content_type}, content=body.encode()
        )

    return httpx.MockTransport(handler)


# images
def test_extract_image_urls():
    html = (
        '<img src="/a.png"><img src="/a.png">'
        '<img src="data:image/gif;base64,AAA" data-src="/lazy.jpg">'
        '<img src="https://cdn.test/b.png#x"><img src="javascript:alert(1)">'
    )
    urls = checks.extract_image_urls("https://site.test/page/", html)
    assert urls == [
        "https://site.test/a.png",
        "https://site.test/lazy.jpg",
        "https://cdn.test/b.png",
    ]


def test_broken_image_detected():
    site = make_site({"/ok.png": (200, "image/png", "x")})
    html = '<img src="/ok.png"><img src="/gone.png">'
    checked, issues = checks.check_images("https://site.test/", html, transport=site)
    assert checked == 2
    assert len(issues) == 1
    assert "gone.png" in issues[0] and "404" in issues[0]


def test_image_head_refused_falls_back_to_get():
    def handler(request):
        if request.method == "HEAD":
            return httpx.Response(405)
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"x")

    checked, issues = checks.check_images(
        "https://site.test/", '<img src="/a.png">', transport=httpx.MockTransport(handler)
    )
    assert checked == 1 and issues == []


def test_image_url_returning_html():
    site = make_site({"/a.png": (200, "text/html", "<html>error</html>")})
    _, issues = checks.check_images("https://site.test/", '<img src="/a.png">', transport=site)
    assert "instead of an image" in issues[0]


def test_many_broken_images_are_summarized():
    html = "".join(f'<img src="/i{n}.png">' for n in range(15))
    _, issues = checks.check_images("https://site.test/", html, transport=make_site({}))
    assert len(issues) == checks.MAX_IMAGE_ISSUES + 1
    assert "5 more" in issues[-1]


# SSL
def test_ssl_valid_certificate():
    result = checks.check_ssl("https://site.test")
    assert result.days_left == 90
    assert result.issues == []


def test_ssl_expiring_soon(monkeypatch):
    monkeypatch.setattr(checks, "_get_cert", lambda host, port=443: _cert_expiring_in(5))
    result = checks.check_ssl("https://site.test")
    assert result.days_left == 5
    assert "expires" in result.issues[0]


def test_ssl_verification_error(monkeypatch):
    def broken(host, port=443):
        raise ssl.SSLCertVerificationError(1, "certificate has expired")

    monkeypatch.setattr(checks, "_get_cert", broken)
    result = checks.check_ssl("https://site.test")
    assert "SSL certificate problem" in result.issues[0]


def test_ssl_skipped_for_plain_http(monkeypatch):
    def must_not_run(host, port=443):
        raise AssertionError("SSL check should not run for http://")

    monkeypatch.setattr(checks, "_get_cert", must_not_run)
    assert checks.check_ssl("http://site.test").issues == []


def test_ssl_connection_failure_is_left_to_page_check(monkeypatch):
    def refused(host, port=443):
        raise ConnectionRefusedError()

    monkeypatch.setattr(checks, "_get_cert", refused)
    result = checks.check_ssl("https://site.test")
    assert result.issues == [] and result.days_left is None


# DNS
def test_dns_ok(monkeypatch):
    def fake_resolve(host, record_type, **kwargs):
        if record_type == "A":
            return ["93.184.216.34"]
        raise dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    result = checks.lookup_dns("site.test")
    assert result.a_records == ["93.184.216.34"]
    assert result.error is None


def test_dns_domain_does_not_exist(monkeypatch):
    def fake_resolve(host, record_type, **kwargs):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert "NXDOMAIN" in checks.lookup_dns("site.test").error


def test_dns_timeout(monkeypatch):
    def fake_resolve(host, record_type, **kwargs):
        raise dns.exception.Timeout()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert "in time" in checks.lookup_dns("site.test").error


def test_dns_no_records(monkeypatch):
    def fake_resolve(host, record_type, **kwargs):
        raise dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert "no A/AAAA records" in checks.lookup_dns("site.test").error


# run_checks
def test_run_checks_healthy_site():
    site = make_site(
        {
            "/": (200, "text/html", '<html><img src="/logo.png"></html>'),
            "/about": (200, "text/html", "<html>about</html>"),
            "/logo.png": (200, "image/png", "x"),
            "/api/status": (200, "application/json", '{"ok": true}'),
        }
    )
    report = checks.run_checks(
        "https://site.test", routes=["/about"], api_endpoints=["/api/status"], transport=site
    )
    assert report.ok
    assert report.issues == []
    assert report.pages_checked == 3
    assert report.images_checked == 1


def test_run_checks_reports_every_problem():
    site = make_site(
        {
            "/": (200, "text/html", '<html><img src="/logo.png"><img src="/missing.png"></html>'),
            "/about": (200, "text/html", "<html>about</html>"),
            "/logo.png": (200, "image/png", "x"),
            "/api/status": (200, "application/json", '{"ok": true}'),
        }
    )
    report = checks.run_checks(
        "https://site.test",
        routes=["/about", "/pricing"],
        api_endpoints=["/api/status", "/api/broken"],
        transport=site,
    )
    assert not report.ok
    assert report.status_code == 200
    assert report.pages_checked == 5
    assert report.images_checked == 2
    assert report.ssl_days_left == 90
    problems = " ".join(report.issues)
    assert "/pricing" in problems
    assert "/api/broken" in problems
    assert "missing.png" in problems
    assert "/about" not in problems
    assert "/api/status" not in problems
    assert "logo.png" not in problems


def test_run_checks_main_page_down_skips_images_and_ssl():
    def refuse(request):
        raise httpx.ConnectError("All connection attempts failed")

    report = checks.run_checks(
        "https://site.test", routes=["/about"], transport=httpx.MockTransport(refuse)
    )
    assert not report.ok
    assert len(report.issues) == 2  # main page + the route, nothing else
    assert report.images_checked == 0
    assert report.ssl_days_left is None