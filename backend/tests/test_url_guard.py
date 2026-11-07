import pytest

from app.core.config import settings
from app.monitoring.url_guard import UnsafeURLError, is_public_ip, validate_url


@pytest.fixture(autouse=True)
def strict_mode(monkeypatch):
    """Always test with the guard fully on, whatever your .env says."""
    monkeypatch.setattr(settings, "allow_private_targets", False)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
        "http://10.0.0.5",
        "http://192.168.1.10",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://example.local",
        "ftp://example.com",
        "http://example.com:5432",
        "http://user:pass@example.com",
        "http://",
    ],
)
def test_blocks_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


@pytest.mark.parametrize(
    "url",
    ["https://8.8.8.8", "http://8.8.8.8/health", "https://8.8.8.8:443/"],
)
def test_allows_public_urls(url):
    validate_url(url)  # must not raise


def test_is_public_ip():
    assert is_public_ip("8.8.8.8")
    assert not is_public_ip("127.0.0.1")
    assert not is_public_ip("10.1.2.3")
    assert not is_public_ip("100.64.0.1")  # carrier-grade NAT range
    assert not is_public_ip("::1")