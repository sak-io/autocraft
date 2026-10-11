"""Admin bootstrap at every startup (architecture s5 cases a-c, F25, AR-1). Refusals raise BootstrapError."""
from __future__ import annotations

import logging

from ..config import Settings
from ..kernel import db
from ..kernel.timeutil import Clock, to_text
from ..logging_setup import log
from .passwords import hash_password, verify_password

ADMIN_NAME = "Studio admin"


class BootstrapError(Exception):
    """Startup must stop. Messages name settings, never values."""


def bootstrap_admin(settings: Settings, clock: Clock) -> list[str]:
    """Returns the actions taken: created, promoted, email_changed, password_reset (empty = nothing to do)."""
    path, email, password = settings.database_path, settings.admin_email, settings.admin_password
    with db.read_conn(path) as c:
        admin = c.execute("SELECT id, email, password_hash FROM users WHERE role = 'admin'").fetchone()
        holder = c.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    now, actions = to_text(clock.now()), []

    if admin is None:  # case (a)
        if holder is not None and not settings.admin_promote_existing:
            raise BootstrapError("ADMIN_EMAIL belongs to an existing student account. Refusing to make it the admin. "
                                 "Set ADMIN_PROMOTE_EXISTING=true to promote it on purpose.")
        new_hash = hash_password(password)  # outside the transaction
        with db.write_tx(path) as c:
            if holder is None:
                c.execute("INSERT INTO users (email, name, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
                          (email, ADMIN_NAME, new_hash, now))
            else:
                c.execute("UPDATE users SET role = 'admin', password_hash = ? WHERE id = ?", (new_hash, holder["id"]))
                c.execute("DELETE FROM sessions WHERE user_id = ?", (holder["id"],))
        actions.append("created" if holder is None else "promoted")
    else:
        changing = admin["email"] != email
        if changing and not settings.admin_allow_email_change:  # case (b)
            raise BootstrapError("ADMIN_EMAIL differs from the existing admin's email. Refusing to start. "
                                 "Set ADMIN_ALLOW_EMAIL_CHANGE=true to change the admin's email on purpose.")
        if changing and holder is not None:
            raise BootstrapError("ADMIN_EMAIL is already used by another account. Refusing to start.")
        reset = not verify_password(password, admin["password_hash"])  # case (c), outside the transaction
        if changing or reset:
            new_hash = hash_password(password) if reset else admin["password_hash"]
            with db.write_tx(path) as c:
                c.execute("UPDATE users SET email = ?, password_hash = ? WHERE id = ?", (email, new_hash, admin["id"]))
                c.execute("DELETE FROM sessions WHERE user_id = ?", (admin["id"],))  # old sign-ins end
            actions += (["email_changed"] if changing else []) + (["password_reset"] if reset else [])
    if actions:
        log(logging.WARNING, "admin bootstrap", actions=actions)  # no email or password in the log
    return actions
