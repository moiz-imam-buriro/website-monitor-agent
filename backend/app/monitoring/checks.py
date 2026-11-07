import http
import json
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import certifi
import dns.exception
import dns.resolver
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.monitoring.url_guard import UnsafeURLError, validate_url

MAX_REDIRECTS = 5
MAX_BODY_BYTES = 1_000_000
SLOW_RESPONSE_MS = 3000
REDIRECT_CODES = {301, 302, 303, 307, 308}
USER_AGENT = "WebsiteMonitorAgent/1.0 (uptime monitoring)"
DNS_HINTS = (
    "getaddrinfo",
    "name or service not known",
    "nodename nor servname",
    "no address associated",
    "temporary failure in name resolution",
)
MAX_IMAGES = 30
MAX_IMAGE_ISSUES = 10
MAX_WORKERS = 5
SSL_WARN_DAYS = 14

@dataclass
class FetchResult:
    """Everything we learned from requesting one URL."""

    url: str
    final_url: str
    status_code: int | None = None
    elapsed_ms: int | None = None
    redirects: list[str] = field(default_factory=list)
    content_type: str = ""
    text: str = ""
    # dns | timeout | ssl | connection | redirect | unsafe | other
    error_type: str | None = None
    error: str | None = None


@dataclass
class CheckOutcome:
    """The verdict for one page, route or API endpoint."""

    url: str
    ok: bool
    status_code: int | None
    response_time_ms: int | None
    issues: list[str]
    text: str = field(default="", repr=False)
    final_url: str = ""
    error_type: str | None = None


def build_url(base_url: str, path: str) -> str:
    """'/login' becomes 'https://site.com/login'. Full URLs are kept as they are."""
    if path.startswith(("http://", "https://")):
        return path
    return base_url.rstrip("/") + path


def _read_body(response: httpx.Response) -> str:
    """Read at most MAX_BODY_BYTES, so a huge page cannot eat our memory."""
    chunks, size = [], 0
    for chunk in response.iter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_BODY_BYTES:
            break
    data = b"".join(chunks)[:MAX_BODY_BYTES]
    return data.decode(response.encoding or "utf-8", errors="replace")


def _classify_error(exc: Exception) -> tuple[str, str]:
    """Turn a technical exception into (error_type, plain-English message)."""
    messages, current = [], exc
    while current is not None and len(messages) < 5:
        messages.append(str(current).lower())
        current = current.__cause__ or current.__context__
    text = " ".join(messages)

    if isinstance(exc, httpx.TimeoutException):
        return "timeout", f"No response within {settings.request_timeout_seconds} seconds"
    if any(hint in text for hint in DNS_HINTS):
        return "dns", "Domain name could not be resolved (DNS failure)"
    if "certificate" in text or "ssl" in text or "tls" in text:
        return "ssl", f"SSL/TLS problem: {exc}"
    if isinstance(exc, httpx.ConnectError):
        return "connection", "Could not connect to the server (refused or unreachable)"
    return "other", f"{type(exc).__name__}: {exc}"


def fetch_url(
    url: str,
    method: str = "GET",
    transport: httpx.BaseTransport | None = None,
) -> FetchResult:
    """
    Request a URL and never raise: every failure ends up inside the result.
    Redirects are followed by hand, so each hop passes the URL guard.
    `transport` exists only so tests can fake a website without internet.
    """
    result = FetchResult(url=url, final_url=url)
    current = url
    started = time.perf_counter()

    try:
        with httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                validate_url(current)
                with client.stream(method, current) as response:
                    result.final_url = current
                    result.status_code = response.status_code
                    result.content_type = response.headers.get("content-type", "")

                    location = response.headers.get("location")
                    if response.status_code in REDIRECT_CODES and location:
                        current = urljoin(current, location)
                        result.redirects.append(current)
                        continue

                    if method == "GET":
                        result.text = _read_body(response)
                    break
            else:
                result.error_type = "redirect"
                result.error = f"Too many redirects (more than {MAX_REDIRECTS})"
    except UnsafeURLError as e:
        result.error_type = "unsafe"
        result.error = f"Blocked unsafe address: {e}"
    except httpx.HTTPError as e:
        result.error_type, result.error = _classify_error(e)

    result.elapsed_ms = int((time.perf_counter() - started) * 1000)
    return result


def _phrase(code: int) -> str:
    try:
        return http.HTTPStatus(code).phrase
    except ValueError:
        return "Unknown status"


def _fetch_issues(result: FetchResult) -> list[str]:
    """Hard failures: could not connect, or the server answered with an error."""
    if result.error:
        return [f"{result.url}: {result.error}"]
    if (result.status_code or 0) >= 400:
        return [
            f"{result.url} returned HTTP {result.status_code} "
            f"({_phrase(result.status_code)})"
        ]
    return []


def _outcome(url: str, result: FetchResult, issues: list[str]) -> CheckOutcome:
    return CheckOutcome(
        url=url,
        ok=not issues,
        status_code=result.status_code,
        response_time_ms=result.elapsed_ms,
        issues=issues,
        text=result.text,
        final_url=result.final_url,
        error_type=result.error_type,
    )


def check_page(url: str, transport: httpx.BaseTransport | None = None) -> CheckOutcome:
    """Check a main page or a route (/login, /pricing, ...)."""
    result = fetch_url(url, transport=transport)
    issues = _fetch_issues(result)

    if not issues:
        if result.elapsed_ms is not None and result.elapsed_ms > SLOW_RESPONSE_MS:
            issues.append(
                f"{url} is slow: {result.elapsed_ms} ms (limit {SLOW_RESPONSE_MS} ms)"
            )
        if not result.text.strip():
            issues.append(f"{url} returned an empty page")

    return _outcome(url, result, issues)


def check_api_endpoint(
    url: str, transport: httpx.BaseTransport | None = None
) -> CheckOutcome:
    """Check an API URL: it must answer, and the answer must look like JSON."""
    result = fetch_url(url, transport=transport)
    issues = _fetch_issues(result)

    if not issues:
        content_type = result.content_type.lower()
        if "html" in content_type:
            issues.append(
                f"{url} returned an HTML page instead of JSON (often an error page)"
            )
        elif "json" in content_type:
            try:
                json.loads(result.text)
            except ValueError:
                issues.append(f"{url} says it returns JSON, but the data is not valid JSON")
        if not issues and result.elapsed_ms is not None and result.elapsed_ms > SLOW_RESPONSE_MS:
            issues.append(
                f"{url} is slow: {result.elapsed_ms} ms (limit {SLOW_RESPONSE_MS} ms)"
            )

    return _outcome(url, result, issues)

# images
def _img_source(img) -> str | None:
    """Real image address. Also handles lazy-loaded images (data-src)."""
    for attr in ("src", "data-src", "data-lazy-src"):
        value = (img.get(attr) or "").strip()
        if value and not value.lower().startswith(("data:", "blob:", "javascript:")):
            return value
    return None


def extract_image_urls(base_url: str, html: str) -> list[str]:
    """All unique image URLs on a page, as full URLs, at most MAX_IMAGES."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    urls: list[str] = []
    for img in soup.find_all("img"):
        source = _img_source(img)
        if not source:
            continue
        full = urljoin(base_url, source).split("#")[0]
        if not full.startswith(("http://", "https://")) or full in seen:
            continue
        seen.add(full)
        urls.append(full)
        if len(urls) >= MAX_IMAGES:
            break
    return urls


def _check_one_image(url: str, transport: httpx.BaseTransport | None) -> str | None:
    """Return a problem description, or None if the image is fine."""
    # HEAD asks only for headers, so we do not download the picture
    result = fetch_url(url, method="HEAD", transport=transport)
    if result.error_type is None and result.status_code in (403, 405, 501):
        result = fetch_url(url, method="GET", transport=transport)  # HEAD refused

    if result.error_type == "unsafe":
        return None  # points to a private address: not our job to follow it
    if result.error:
        return f"Image failed to load: {url} ({result.error})"
    if (result.status_code or 0) >= 400:
        return (
            f"Broken image: {url} returned HTTP {result.status_code} "
            f"({_phrase(result.status_code)})"
        )
    if "text/html" in result.content_type.lower():
        return f"Image URL {url} returns a web page instead of an image"
    return None


def check_images(
    base_url: str, html: str, transport: httpx.BaseTransport | None = None
) -> tuple[int, list[str]]:
    """Test every image on the page. Returns (images_checked, issues)."""
    urls = extract_image_urls(base_url, html)
    if not urls:
        return 0, []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(lambda u: _check_one_image(u, transport), urls))

    broken = [r for r in results if r]
    issues = broken[:MAX_IMAGE_ISSUES]
    if len(broken) > MAX_IMAGE_ISSUES:
        issues.append(f"... and {len(broken) - MAX_IMAGE_ISSUES} more broken images")
    return len(urls), issues


# SSL
@dataclass
class SslResult:
    hostname: str
    days_left: int | None = None
    issues: list[str] = field(default_factory=list)


def _get_cert(hostname: str, port: int = 443) -> dict:
    """Open a TLS connection and return the server certificate (tests replace this)."""
    context = ssl.create_default_context(cafile=certifi.where())
    with socket.create_connection(
        (hostname, port), timeout=settings.request_timeout_seconds
    ) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as tls:
            return tls.getpeercert()


def check_ssl(url: str) -> SslResult:
    """Is the certificate valid, and how many days are left?"""
    parsed = urlparse(url)
    host = parsed.hostname
    result = SslResult(hostname=host or "")
    if parsed.scheme != "https" or not host:
        return result

    try:
        validate_url(url)
    except UnsafeURLError:
        return result  # the page check already reports this

    try:
        cert = _get_cert(host, parsed.port or 443)
    except ssl.SSLCertVerificationError as e:  # must come before SSLError
        reason = getattr(e, "verify_message", None) or str(e)
        result.issues.append(f"SSL certificate problem for {host}: {reason}")
        return result
    except ssl.SSLError as e:
        result.issues.append(f"SSL/TLS error for {host}: {e}")
        return result
    except OSError:
        return result  # cannot connect at all: the page check reports that

    not_after = cert.get("notAfter")
    if not_after:
        seconds_left = ssl.cert_time_to_seconds(not_after) - time.time()
        result.days_left = int(seconds_left // 86400)
        if result.days_left <= SSL_WARN_DAYS:
            result.issues.append(
                f"SSL certificate for {host} expires in {result.days_left} day(s)"
            )
    return result


# DNS
@dataclass
class DnsResult:
    hostname: str
    a_records: list[str] = field(default_factory=list)
    aaaa_records: list[str] = field(default_factory=list)
    error: str | None = None


def lookup_dns(hostname: str) -> DnsResult:
    """Ask DNS for the addresses of a domain and explain what went wrong."""
    result = DnsResult(hostname=hostname)
    for record_type, bucket in (("A", result.a_records), ("AAAA", result.aaaa_records)):
        try:
            answers = dns.resolver.resolve(hostname, record_type, lifetime=5)
            bucket.extend(str(r) for r in answers)
        except dns.resolver.NoAnswer:
            continue  # no records of this type: normal
        except dns.resolver.NXDOMAIN:
            result.error = "Domain does not exist (NXDOMAIN)"
            return result
        except dns.exception.Timeout:
            result.error = "DNS servers did not answer in time"
            return result
        except dns.resolver.NoNameservers:
            result.error = "No DNS server could answer the question"
            return result
        except dns.exception.DNSException as e:
            result.error = f"DNS error: {e}"
            return result

    if not result.a_records and not result.aaaa_records:
        result.error = "Domain exists but has no A/AAAA records (no address to connect to)"
    return result


# full run
@dataclass
class RunReport:
    """The result of checking one whole monitor."""

    url: str
    ok: bool
    status_code: int | None
    response_time_ms: int | None
    issues: list[str]
    pages_checked: int
    images_checked: int
    ssl_days_left: int | None


def run_checks(
    url: str,
    routes: list[str] | None = None,
    api_endpoints: list[str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> RunReport:
    """Main page + routes + API endpoints + images + SSL, in one report."""
    main = check_page(url, transport=transport)

    jobs = [(check_page, build_url(url, r)) for r in routes or []]
    jobs += [(check_api_endpoint, build_url(url, e)) for e in api_endpoints or []]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        extra = list(pool.map(lambda job: job[0](job[1], transport=transport), jobs))

    issues = list(main.issues)
    for outcome in extra:
        issues.extend(outcome.issues)

    # Images: only if the main page really loaded
    images_checked = 0
    if main.error_type is None and (main.status_code or 0) < 400 and main.text:
        images_checked, image_issues = check_images(
            main.final_url, main.text, transport=transport
        )
        issues.extend(image_issues)

    # SSL: only if we could connect (otherwise the page check already explains it)
    ssl_days_left = None
    if main.error_type is None and url.startswith("https://"):
        ssl_result = check_ssl(url)
        ssl_days_left = ssl_result.days_left
        issues.extend(ssl_result.issues)

    return RunReport(
        url=url,
        ok=not issues,
        status_code=main.status_code,
        response_time_ms=main.response_time_ms,
        issues=issues,
        pages_checked=1 + len(extra),
        images_checked=images_checked,
        ssl_days_left=ssl_days_left,
    )