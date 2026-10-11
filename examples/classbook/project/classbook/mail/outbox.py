"""Best-effort send AFTER commit (ADR-0004): pending row -> mailer -> recorded | failed. Never raises."""
from __future__ import annotations

import logging

from ..kernel import db
from ..kernel.timeutil import Clock, to_text
from ..logging_setup import log
from . import Mailer
from .templates import render


def send_confirmation(db_path, clock: Clock, mailer: Mailer, *, kind: str, booking_id: int,
                      to_email: str, class_title: str, starts_at) -> None:
    """Call only once the booking/cancellation has committed. Logs ids and error types only (no user data)."""
    try:
        subject, body = render(kind, to_email, class_title, starts_at)
        with db.write_tx(db_path) as conn:  # unique (booking_id, kind): a duplicate inserts nothing
            new = conn.execute(
                "INSERT INTO messages (to_email, subject, body, kind, booking_id, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'pending', ?) ON CONFLICT (booking_id, kind) DO NOTHING",
                (to_email, subject, body, kind, booking_id, to_text(clock.now())),
            ).rowcount
            msg_id = conn.execute("SELECT id FROM messages WHERE booking_id = ? AND kind = ?", (booking_id, kind)).fetchone()[0]
        if not new:
            return
    except Exception as exc:
        log(logging.ERROR, "message not queued", kind=kind, booking_id=booking_id, exc_type=type(exc).__name__)
        return
    status = "recorded"
    try:
        mailer.send(to_email, subject, body)
    except Exception as exc:
        status = "failed"
        log(logging.ERROR, "message send failed", kind=kind, booking_id=booking_id, exc_type=type(exc).__name__)
    try:
        with db.write_tx(db_path) as conn:
            conn.execute("UPDATE messages SET status = ? WHERE id = ?", (status, msg_id))
    except Exception as exc:  # row stays 'pending': visible, and the booking is untouched
        log(logging.ERROR, "message status not saved", kind=kind, booking_id=booking_id, exc_type=type(exc).__name__)
