"""Small request helpers: trusted-proxy client IP, the `next` validator, login URL."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import quote

from fastapi import Request

_BAD_ESCAPE = re.compile(r"%(2f|5c|[01][0-9a-f]|7f)", re.I)  # encoded / \ and control characters
MAX_NEXT = 512


def safe_next(value: object) -> str:
    """Return `value` if it is a safe local path (api.md rule), else "/"."""
    if not isinstance(value, str) or not value or len(value) > MAX_NEXT:
        return "/"
    if not value.startswith("/") or value.startswith("//") or "//" in value or "\\" in value:
        return "/"
    if any(ord(c) < 0x20 or ord(c) == 0x7F or c in "  \x85" for c in value):
        return "/"
    if _BAD_ESCAPE.search(value) or re.match(r"/*[A-Za-z][A-Za-z0-9+.-]*:", value):
        return "/"  # encoded slash/backslash/control, or a scheme-looking prefix
    return value


def login_url(request: Request) -> str:
    """/login, carrying the current path as `next` for GET requests only."""
    if request.method == "GET":
        return "/login?next=" + quote(request.url.path, safe="/")
    return "/login"


def client_ip(request: Request, hops: int | None = None) -> str:
    """The client address. hops=0: socket address. hops=N: the Nth entry from the RIGHT of X-Forwarded-For
    (the one our own proxy appended); anything the client wrote further left is ignored. If the header has
    fewer entries than hops or the entry is not an IP, fall back to the socket address (never trust it)."""
    if hops is None:
        hops = request.app.state.settings.trusted_proxy_hops
    socket_addr = request.client.host if request.client else "unknown"
    if hops <= 0:
        return socket_addr
    raw = ",".join(v.decode("latin-1") for k, v in request.scope["headers"] if k == b"x-forwarded-for")
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    if len(entries) < hops:
        return socket_addr
    try:
        return str(ipaddress.ip_address(entries[-hops]))
    except ValueError:
        return socket_addr
