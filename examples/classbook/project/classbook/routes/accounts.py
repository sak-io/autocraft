"""Routes: sign up, log in, log out (api.md #3-#5). Never log or echo submitted emails or passwords."""
from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from starlette.responses import RedirectResponse

from ..auth import service
from ..auth.passwords import dummy_hash, hash_password, verify_password
from ..auth.web import session_cookie, session_token
from ..kernel import db, validators as v
from ..kernel.timeutil import to_text
from ..logging_setup import log
from ..web import flash, render, rotate_csrf
from ..web.deps import User, optional_user, require_user
from ..web.util import client_ip, safe_next

router = APIRouter()
RETRY_AFTER = {"Retry-After": "900"}
BAD_LOGIN = "That email and password do not match. Please try again."
BAD_SIGNUP = "We could not create an account with these details."


def _signed_in(request: Request, token: str, where: str, message: str) -> RedirectResponse:
    """303 with the new session cookie, a rotated CSRF token (T-5, T-6) and a flash message."""
    s = request.app.state
    resp = RedirectResponse(safe_next(where), status_code=303)
    resp.headers.append(*session_cookie(s.settings, token, service.SESSION_DAYS * 86400))
    rotate_csrf(request)
    flash(request, resp, message, "success")
    return resp


def _maybe_purge(request: Request) -> None:
    s, now = request.app.state, request.app.state.clock.now()
    if (now - s.last_purge).total_seconds() >= 86400:  # daily
        with db.write_tx(s.settings.database_path) as conn:
            service.purge_expired(conn, now)
        s.last_purge = now


@router.get("/login")
def login_form(request: Request, next: str = "", user: User | None = Depends(optional_user)):
    return render(request, "login.html", {"next": safe_next(next), "email": ""})


@router.post("/login")
def login(request: Request, email: str = Form(""), password: str = Form(""), next: str = Form(""),
          user: User | None = Depends(optional_user)):
    s, now, ip = request.app.state, request.app.state.clock.now(), client_ip(request)
    path = s.settings.database_path
    email = email.strip().lower()[:254]
    with db.read_conn(path) as conn:
        if service.login_throttled(conn, email, ip, now):
            log(logging.WARNING, "login throttled")
            raise HTTPException(429, headers=RETRY_AFTER)
        row = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    # Unknown email still pays for one scrypt verify (dummy hash), outside any write transaction.
    ok = verify_password(password[: v.PASSWORD_MAX], row["password_hash"] if row else dummy_hash())
    if not ok or row is None:
        with db.write_tx(path) as conn:
            service.record(conn, [service.email_key(email), service.ip_key(ip)], now)
        log(logging.INFO, "login failed")  # deliberately no user-supplied fields
        return render(request, "login.html", {"next": safe_next(next), "email": email[:254], "error": BAD_LOGIN}, status=401)
    with db.write_tx(path) as conn:
        service.delete_session(conn, session_token(request))  # never keep a presented token alive
        token = service.create_session(conn, row["id"], now)
        service.mark_sign_in(conn, row["id"], now)
    _maybe_purge(request)
    log(logging.INFO, "login ok", user_id=row["id"])
    return _signed_in(request, token, next, "Signed in.")


@router.get("/signup")
def signup_form(request: Request, next: str = "", user: User | None = Depends(optional_user)):
    return render(request, "signup.html", {"next": safe_next(next), "values": {}, "errors": {}})


@router.post("/signup")
def signup(request: Request, name: str = Form(""), email: str = Form(""), password: str = Form(""),
           next: str = Form(""), user: User | None = Depends(optional_user)):
    s, now, ip = request.app.state, request.app.state.clock.now(), client_ip(request)
    path = s.settings.database_path
    with db.write_tx(path) as conn:  # count every attempt, then check (10 per hour per IP)
        service.record(conn, [service.signup_key(ip)], now)
        throttled = service.count_since(conn, service.signup_key(ip), now - service.SIGNUP_WINDOW) > service.SIGNUP_CAP
    if throttled:
        log(logging.WARNING, "signup throttled")
        raise HTTPException(429, headers={"Retry-After": "3600"})
    errors: dict[str, str] = {}
    clean: dict[str, str] = {}
    for field, check, value in (("name", v.name, name), ("email", v.email, email), ("password", v.password, password)):
        try:
            clean[field] = check(value)
        except v.FieldError as exc:
            errors[field] = exc.message
    if not errors:
        pw_hash = hash_password(clean["password"])  # outside the transaction
        try:
            with db.write_tx(path) as conn:
                uid = conn.execute("INSERT INTO users (email, name, password_hash, role, created_at) VALUES (?, ?, ?, 'student', ?)",
                                   (clean["email"], clean["name"], pw_hash, to_text(now))).lastrowid
                token = service.create_session(conn, uid, now)
                service.mark_sign_in(conn, uid, now)
        except sqlite3.IntegrityError:
            errors["form"] = BAD_SIGNUP  # same message whether or not the email exists (T-10)
        else:
            log(logging.INFO, "signup ok", user_id=uid)
            return _signed_in(request, token, next, "Welcome to ClassBook.")
    values = {"name": name[:80], "email": email[:254]}  # never the password
    return render(request, "signup.html", {"next": safe_next(next), "values": values, "errors": errors}, status=422)


@router.post("/logout")
def logout(request: Request, user: User = Depends(require_user)):
    s = request.app.state
    with db.write_tx(s.settings.database_path) as conn:
        service.delete_session(conn, session_token(request))
    resp = RedirectResponse("/", status_code=303)
    resp.headers.append(*session_cookie(s.settings, "", 0))
    rotate_csrf(request)
    flash(request, resp, "Signed out.", "success")
    return resp
