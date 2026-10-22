"""Dependency seams. T3 overrides `current_user` (session lookup); T4/T5 tests override it with fixtures.

Every route declares exactly one guard: `optional_user` (public), `require_user`, `require_student` or
`require_admin`. Authenticated responses are marked no-store.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from ..config import Settings
from ..kernel.timeutil import Clock
from ..mail import Mailer
from .util import login_url


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    role: str  # 'student' | 'admin'


class RedirectTo(Exception):
    def __init__(self, location: str):
        self.location = location


def current_user(request: Request) -> User | None:
    """The signed-in user from the session cookie, or None. Tests of other tasks override this dependency."""
    from ..auth.web import user_from_request  # late import: auth imports web.cookies
    return user_from_request(request)


def optional_user(request: Request, user: User | None = Depends(current_user)) -> User | None:
    request.state.user = user
    if user is not None:
        request.state.no_store = True
    return user


def require_user(request: Request, user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise RedirectTo(login_url(request))
    return user


def require_student(user: User = Depends(require_user)) -> User:
    if user.role != "student":
        raise HTTPException(403)
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403)
    return user


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_mailer(request: Request) -> Mailer:
    return request.app.state.mailer


MAX_ID = 2**63 - 1  # SQLite INTEGER PRIMARY KEY upper bound; anything larger cannot exist


def _parse_id(raw: str) -> int:
    """The one place a path id is checked: digits only and within SQLite's range, else the site's 404 page."""
    if not (raw.isascii() and raw.isdigit()) or len(raw) > 19 or int(raw) > MAX_ID:
        raise HTTPException(404)
    return int(raw)


def class_id_param(class_id: str) -> int:
    return _parse_id(class_id)


def booking_id_param(booking_id: str) -> int:
    return _parse_id(booking_id)
