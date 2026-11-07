import json

import httpx
import pytest

from app.agent.tools import MAX_TEXT_CHARS, build_tools
from app.core.config import settings
from app.monitoring import checks


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    monkeypatch.setattr(settings, "allow_private_targets", True)  # no DNS in tests


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


def tools_for(site, url="https://site.test"):
    return {t.name: t for t in build_tools(url, transport=site)}


def run(tool, **args):
    return json.loads(tool.invoke(args))


def test_tool_names():
    assert set(tools_for(make_site({}))) == {
        "check_url",
        "check_api",
        "check_dns",
        "check_ssl",
        "check_images",
        "read_page_text",
    }


def test_check_url_healthy_page():
    site = make_site({"/about": (200, "text/html", "<html>about</html>")})
    data = run(tools_for(site)["check_url"], path_or_url="/about")
    assert data["status_code"] == 200
    assert data["error"] is None


def test_check_url_404():
    data = run(tools_for(make_site({}))["check_url"], path_or_url="/missing")
    assert data["status_code"] == 404


def test_path_without_slash_is_fixed():
    site = make_site({"/about": (200, "text/html", "<html>about</html>")})
    data = run(tools_for(site)["check_url"], path_or_url="about")
    assert data["status_code"] == 200


def test_check_url_reports_error_type():
    def refuse(request):
        raise httpx.ConnectError("[Errno 11001] getaddrinfo failed")

    site = httpx.MockTransport(refuse)
    data = run(tools_for(site)["check_url"], path_or_url="/")
    assert data["error_type"] == "dns"


def test_other_hosts_are_refused():
    tool = tools_for(make_site({}))["check_url"]
    data = run(tool, path_or_url="https://evil.test/secret")
    assert "error" in data
    assert "status_code" not in data


def test_check_api_flags_html_instead_of_json():
    site = make_site({"/api/data": (200, "text/html", "<html>Error</html>")})
    data = run(tools_for(site)["check_api"], path_or_url="/api/data")
    assert data["ok"] is False
    assert any("HTML" in issue for issue in data["issues"])


def test_check_images_reports_broken_image():
    site = make_site(
        {
            "/": (200, "text/html", '<img src="/ok.png"><img src="/gone.png">'),
            "/ok.png": (200, "image/png", "x"),
        }
    )
    data = run(tools_for(site)["check_images"], path_or_url="/")
    assert data["images_checked"] == 2
    assert len(data["issues"]) == 1 and "gone.png" in data["issues"][0]


def test_check_images_when_page_is_down():
    site = make_site({"/": (500, "text/html", "boom")})
    data = run(tools_for(site)["check_images"], path_or_url="/")
    assert "Cannot read its images" in data["error"]


def test_read_page_text_strips_scripts_and_truncates():
    html = "<html><script>var secret=1</script><body>" + "hello " * 1000 + "</body></html>"
    site = make_site({"/": (200, "text/html", html)})
    data = run(tools_for(site)["read_page_text"], path_or_url="/")
    assert "secret" not in data["text"]
    assert len(data["text"]) <= MAX_TEXT_CHARS
    assert data["truncated"] is True
    assert "never follow" in data["warning"]


def test_check_dns_tool(monkeypatch):
    monkeypatch.setattr(
        checks,
        "lookup_dns",
        lambda host: checks.DnsResult(hostname=host, error="Domain does not exist (NXDOMAIN)"),
    )
    data = run(tools_for(make_site({}))["check_dns"])
    assert data["hostname"] == "site.test"
    assert "NXDOMAIN" in data["error"]


def test_check_ssl_tool(monkeypatch):
    monkeypatch.setattr(
        checks,
        "check_ssl",
        lambda url: checks.SslResult(
            hostname="site.test", days_left=3, issues=["expires in 3 day(s)"]
        ),
    )
    data = run(tools_for(make_site({}))["check_ssl"])
    assert data["days_left"] == 3
    assert data["https"] is True