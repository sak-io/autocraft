"""Jinja environment, `render()` and cookie-carried flash messages.

Flash cookie is NOT signed (the architecture has no secret to sign with). That is acceptable: it is HttpOnly
and always HTML-escaped, so a forged one can only show some text to the browser that set it.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from .cookies import cookie_name, set_cookie_header
from .csrf import csrf_field

HERE = Path(__file__).parent
LEVELS = ("info", "success", "error")
MAX_FLASHES, MAX_TEXT = 3, 160


def make_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=str(HERE / "templates"))
    templates.env.globals["csrf_field"] = csrf_field
    return templates


def read_flashes(request: Request) -> list[dict]:
    raw = request.cookies.get(cookie_name(request.app.state.settings, "flash"))
    if not raw:
        return []
    try:
        items = json.loads(base64.urlsafe_b64decode(raw.encode() + b"=" * (-len(raw) % 4)))
        return [{"level": i["level"] if i["level"] in LEVELS else "info", "text": str(i["text"])[:MAX_TEXT]}
                for i in items][:MAX_FLASHES]
    except Exception:
        return []


def flash(request: Request, response: Response, text: str, level: str = "info") -> None:
    """Queue a message for the next page shown (use on the 303 response)."""
    items = read_flashes(request) + [{"level": level if level in LEVELS else "info", "text": text[:MAX_TEXT]}]
    encoded = base64.urlsafe_b64encode(json.dumps(items[-MAX_FLASHES:], ensure_ascii=False).encode()).decode().rstrip("=")
    name, value = set_cookie_header(request.app.state.settings, "flash", encoded)
    response.headers.append(name.decode(), value.decode("latin-1"))


def render(request: Request, template: str, context: dict | None = None, status: int = 200) -> Response:
    """Render a page with the request, flashes and (if a guard ran) the user available to the template."""
    flashes = read_flashes(request)
    ctx = {"user": getattr(request.state, "user", None), "flashes": flashes, **(context or {})}
    response = request.app.state.templates.TemplateResponse(request, template, ctx, status_code=status)
    if flashes:  # shown now: clear, and never cache
        s = request.app.state.settings
        response.delete_cookie(cookie_name(s, "flash"), path="/", secure=s.is_production, httponly=True)
        request.state.no_store = True
    return response
