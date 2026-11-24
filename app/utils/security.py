"""Security helpers: SSRF protection, path confinement, safe filenames."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse, urljoin

from flask import current_app


# Private / reserved ranges (IPv4 + IPv6)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        return True  # unparseable = blocked


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate URL for SSRF safety.
    Returns (ok, error_message).
    - Only http/https
    - Hostname must resolve to public IP(s)
    - Blocks localhost, private, link-local, reserved
    """
    if not url or not isinstance(url, str):
        return False, "URL is required"

    url = url.strip()
    if len(url) > 2048:
        return False, "URL too long"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are allowed"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a hostname"

    # Block obvious local names
    blocked_hosts = {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "metadata",
    }
    if hostname.lower() in blocked_hosts:
        return False, "Access to local/internal hosts is forbidden"

    # Resolve all addresses and check each
    try:
        # Prefer getaddrinfo for dual-stack
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if scheme == "https" else 80),
                                   type=socket.SOCK_STREAM)
        if not infos:
            return False, "Hostname could not be resolved"

        for info in infos:
            ip_str = info[4][0]
            if _is_blocked_ip(ip_str):
                return False, f"Resolved address {ip_str} is not publicly routable"
    except socket.gaierror:
        return False, "Hostname could not be resolved"
    except Exception as e:
        return False, f"DNS resolution failed: {e}"

    return True, ""


def safe_join(base: str | Path, *paths: str) -> Path | None:
    """
    Join paths under base and ensure the result stays inside base.
    Returns None if traversal is detected.
    """
    base_path = Path(base).resolve()
    try:
        candidate = base_path.joinpath(*paths).resolve()
        # Python 3.9+ is_relative_to; fallback for older
        if hasattr(candidate, "is_relative_to"):
            if not candidate.is_relative_to(base_path):
                return None
        else:
            try:
                candidate.relative_to(base_path)
            except ValueError:
                return None
        return candidate
    except Exception:
        return None


def sanitize_filename(name: str, max_len: int = 200) -> str:
    """Remove dangerous characters and limit length."""
    if not name:
        return "download"
    # Strip path separators and control chars
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)
    name = name.strip(" .")
    if not name:
        name = "download"
    if len(name) > max_len:
        stem, ext = os.path.splitext(name)
        name = stem[: max_len - len(ext) - 1] + ext
    return name


def is_safe_redirect(url: str, allowed_hosts: set[str] | None = None) -> bool:
    """Basic open-redirect guard (for future use)."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme and not parsed.netloc:
            return True  # relative
        if parsed.scheme not in ("http", "https"):
            return False
        if allowed_hosts and parsed.hostname not in allowed_hosts:
            return False
        return True
    except Exception:
        return False
