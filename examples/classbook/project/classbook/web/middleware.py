"""Pure ASGI middleware: security headers, 16 KB body limit, CSRF check. Order (outer to inner) is set in web.install."""
from __future__ import annotations

import logging
from http.cookies import SimpleCookie

from starlette.responses import HTMLResponse

from ..config import Settings
from ..kernel.validators import MAX_BODY_BYTES
from ..logging_setup import log
from . import csrf
from .cookies import cookie_name, set_cookie_header

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

CSP = "default-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
HSTS = "max-age=31536000; includeSubDomains"
HEADERS = [
    (b"content-security-policy", CSP.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"same-origin"),
]


def bare_page(status: int, title: str, text: str, headers: dict | None = None) -> HTMLResponse:
    """Chrome-free page for errors raised before templates are usable (busy, csrf, too large)."""
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<link rel="stylesheet" href="/static/style.css"><title>{title}</title></head>'
            f"<body><h1>{title}</h1><p>{text}</p></body></html>")
    return HTMLResponse(html, status_code=status, headers={"Cache-Control": "no-store", **(headers or {})})


class SecurityHeadersMiddleware:
    """Outermost: every response (errors included) gets the api.md headers; no-store when a page asks for it."""

    def __init__(self, app, settings: Settings):
        self.app, self.hsts = app, settings.is_production

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        state = scope.setdefault("state", {})

        async def wrapped(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                have = {k.lower() for k, _ in headers}
                extra = [h for h in HEADERS if h[0] not in have]
                if self.hsts:
                    extra.append((b"strict-transport-security", HSTS.encode()))
                if state.get("no_store") and b"cache-control" not in have:
                    extra.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers + extra}
            await send(message)

        await self.app(scope, receive, wrapped)


class _TooLarge(Exception):
    pass


def _replay(body: bytes, original):
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await original()  # block until disconnect, as the real receive does (streaming responses need it)

    return receive


async def read_body(receive, limit: int = MAX_BODY_BYTES) -> bytes:
    chunks, size = [], 0
    while True:
        msg = await receive()
        if msg["type"] != "http.request":
            return b"".join(chunks)
        size += len(msg.get("body", b""))
        if size > limit:
            raise _TooLarge
        chunks.append(msg.get("body", b""))
        if not msg.get("more_body"):
            return b"".join(chunks)


class BodyLimitMiddleware:
    """Request bodies over 16 KB (declared or streamed) get 413 before any route code runs."""

    def __init__(self, app, limit: int = MAX_BODY_BYTES):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        declared = headers.get(b"content-length", b"0")
        too_big = not declared.isdigit() or int(declared) > self.limit
        if too_big and declared != b"0":
            return await self._refuse(scope, receive, send)
        if scope["method"] in SAFE_METHODS and declared == b"0" and b"transfer-encoding" not in headers:
            return await self.app(scope, receive, send)
        try:
            body = await read_body(receive, self.limit)
        except _TooLarge:
            return await self._refuse(scope, receive, send)
        await self.app(scope, _replay(body, receive), send)

    @staticmethod
    async def _refuse(scope, receive, send):
        resp = bare_page(413, "That was too much to send", "Please send less text and try again.")
        await resp(scope, receive, send)


class CsrfMiddleware:
    def __init__(self, app, settings: Settings):
        self.app, self.settings = app, settings
        self.name = cookie_name(settings, "csrf")

    def _cookie(self, scope) -> str | None:
        raw = dict(scope["headers"]).get(b"cookie", b"").decode("latin-1")
        try:
            morsel = SimpleCookie(raw).get(self.name)
        except Exception:
            return None
        return morsel.value if morsel else None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        state = scope.setdefault("state", {})
        cookie = self._cookie(scope)
        have_valid = csrf.is_valid_shape(cookie)
        state["csrf_token"] = cookie if have_valid else csrf.new_token()

        if scope["method"] not in SAFE_METHODS:
            ctype = dict(scope["headers"]).get(b"content-type", b"").decode("latin-1")
            body = await read_body(receive)  # already size-limited upstream
            if not csrf.matches(cookie, csrf.token_from_body(ctype, body)):
                reason = "no cookie" if not have_valid else "mismatch"
                log(logging.WARNING, "csrf rejected", reason=reason, path=scope["path"])
                resp = bare_page(403, "This form has expired", "Please go back, reload the page and try again.")
                return await resp(scope, receive, send)
            receive = _replay(body, receive)

        async def wrapped(message):
            if message["type"] == "http.response.start" and (
                state.get("csrf_rotated") or (state.get("csrf_used") and not have_valid)
            ):
                state["no_store"] = True
                message = {**message, "headers": [*message.get("headers", []),
                                                  set_cookie_header(self.settings, "csrf", state["csrf_token"])]}
            await send(message)

        await self.app(scope, receive, wrapped)
