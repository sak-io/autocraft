"""Double-submit CSRF that works before any session exists (architecture s5, T-6).

The middleware keeps the token in the per-request state dict; `csrf_field()` embeds it in a form and marks
the page `Cache-Control: no-store` (F22), so a token can never be cached or shared by accident.
"""
from __future__ import annotations

import re
import secrets
from urllib.parse import parse_qs

from jinja2 import pass_context
from markupsafe import Markup, escape

FIELD = "csrf_token"
_VALID = re.compile(r"^[A-Za-z0-9_-]{43}$")  # token_urlsafe(32)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def is_valid_shape(token: str | None) -> bool:
    return bool(token) and _VALID.match(token) is not None


def token_for(state: dict) -> str:
    """Token for this request and flag that the page uses it (so it is set as cookie + no-store)."""
    state["csrf_used"] = True
    state["no_store"] = True
    return state["csrf_token"]


def rotate_csrf(request) -> None:
    """Call at login and logout: a new token is sent as the cookie on this response."""
    request.state.csrf_token = new_token()
    request.state.csrf_rotated = True


@pass_context
def csrf_field(ctx) -> Markup:
    """Template helper: `{{ csrf_field() }}` inside every POST form."""
    token = token_for(ctx["request"].scope.setdefault("state", {}))
    return Markup(f'<input type="hidden" name="{FIELD}" value="{escape(token)}">')


def token_from_body(content_type: str, body: bytes) -> str | None:
    if not content_type.lower().startswith("application/x-www-form-urlencoded"):
        return None  # multipart/JSON posts are not used by any form; refuse them
    values = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True).get(FIELD)
    return values[0] if values else None


def matches(cookie_token: str | None, form_token: str | None) -> bool:
    return (
        is_valid_shape(cookie_token)
        and form_token is not None
        and secrets.compare_digest(cookie_token.encode(), form_token.encode())
    )
