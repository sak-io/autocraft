"""Mailer interface and the phase-1 RecordingMailer (ADR-0004)."""
from __future__ import annotations

from typing import Protocol

from ..config import Settings


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None:
        """Deliver or record one plain-text message. May raise; callers treat that as 'failed', never as a booking error."""


class RecordingMailer:
    """Phase 1 'delivery': the `messages` row written by mail.outbox IS the record, nothing leaves the process.

    It still refuses what a real mailer must refuse: line breaks in the address or subject (header injection).
    """

    def send(self, to: str, subject: str, body: str) -> None:
        if any(c in s for s in (to, subject) for c in "\r\n\0") or "@" not in to:
            raise ValueError("invalid recipient or subject")


def build_mailer(settings: Settings) -> Mailer:
    """Only 'recording' exists (config refuses anything else): real delivery waits for email verification."""
    if settings.mail_backend != "recording":
        raise ValueError("unsupported MAIL_BACKEND")
    return RecordingMailer()
