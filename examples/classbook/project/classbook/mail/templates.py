"""Plain-text confirmation emails (US-4b). No HTML, no links, and no student-chosen name (T-17)."""
from __future__ import annotations

from datetime import datetime

from ..kernel.timeutil import format_london
from ..kernel.validators import has_control_chars

BOOKED, CANCELLED = "booked", "cancelled"
KINDS = (BOOKED, CANCELLED)


class UnsafeMessage(ValueError):
    """Template input contains control characters (could inject headers or lines)."""


def render(kind: str, to_email: str, class_title: str, starts_at: datetime) -> tuple[str, str]:
    """-> (subject, body). Raises UnsafeMessage (message never echoes the data) or ValueError for a bad kind."""
    if kind not in KINDS:
        raise ValueError("unknown message kind")
    if has_control_chars(to_email) or has_control_chars(class_title) or not class_title.strip():
        raise UnsafeMessage("control characters or empty text in message data")
    when = format_london(starts_at)
    subject = f"Class {kind}: {class_title} on {when}"
    body = (f"Your class has been {kind}.\n\nClass: {class_title}\nWhen: {when} (London time)\n"
            f"Status: {kind}\n\nThis is an automatic message from ClassBook.\n")
    return subject, body
