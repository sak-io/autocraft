"""HTTP side of sessions: cookie name/attributes and the `current_user` lookup."""
from __future__ import annotations

from fastapi import Request

from ..kernel import db
from ..web.cookies import cookie_name
from . import service


def session_token(request: Request) -> str | None:
    return request.cookies.get(cookie_name(request.app.state.settings, "session"))


def session_cookie(settings, value: str, max_age: int) -> tuple[str, str]:
    parts = [f"{cookie_name(settings, 'session')}={value}", "Path=/", f"Max-Age={max_age}", "HttpOnly", "SameSite=Lax"]
    if settings.is_production:
        parts.append("Secure")  # single switch, same as the csrf and flash cookies
    return "set-cookie", "; ".join(parts)


def user_from_request(request: Request):
    from ..web.deps import User  # late import: web.deps calls this module
    s = request.app.state
    with db.read_conn(s.settings.database_path) as conn:
        row = service.session_user(conn, session_token(request), s.clock.now())
    return User(row["id"], row["email"], row["name"], row["role"]) if row else None
