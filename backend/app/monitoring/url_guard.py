import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}
BLOCKED_HOSTNAMES = {"localhost", "host.docker.internal", "metadata.google.internal"}
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan")


class UnsafeURLError(ValueError):
    """Raised when a URL points somewhere we must never connect to."""


def is_public_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    # ::ffff:127.0.0.1 is just 127.0.0.1 in disguise, so unwrap it first
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def validate_url(url: str) -> None:
    """Raise UnsafeURLError unless the URL is safe to request."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Only http:// and https:// URLs are allowed")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL has no hostname")

    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with a username or password are not allowed")

    # Local testing mode: skip the network-location checks below
    if settings.allow_private_targets:
        return

    try:
        port = parsed.port
    except ValueError:
        raise UnsafeURLError("Invalid port in URL")
    if port not in ALLOWED_PORTS:
        raise UnsafeURLError("Only ports 80 and 443 are allowed")

    host = host.lower().rstrip(".")
    if host in BLOCKED_HOSTNAMES or host.endswith(BLOCKED_SUFFIXES):
        raise UnsafeURLError("This hostname is not allowed")

    default_port = 443 if parsed.scheme == "https" else 80
    try:
        infos = socket.getaddrinfo(
            host, port or default_port, proto=socket.IPPROTO_TCP
        )
    except socket.gaierror:
        # A domain that does not resolve is something the monitor should
        # REPORT as a problem, not a security risk, so we let it through.
        return

    for info in infos:
        if not is_public_ip(info[4][0]):
            raise UnsafeURLError("This address points to a private or internal network")