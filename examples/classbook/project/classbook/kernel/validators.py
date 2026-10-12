"""Field validators and limits (architecture s3, "Input limits").

Each validator returns the cleaned value or raises FieldError(field, message).
Messages never echo the submitted value.
"""
from __future__ import annotations

import re
import unicodedata

MAX_BODY_BYTES = 16 * 1024
NAME_MAX = 80
EMAIL_MAX = 254
TITLE_MAX = 100
INSTRUCTOR_MAX = 80
CAPACITY_MIN, CAPACITY_MAX = 1, 200
DURATION_MIN, DURATION_MAX = 5, 480
PASSWORD_MIN, PASSWORD_MAX = 10, 128
ADMIN_PASSWORD_MIN = 14

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_INT_RE = re.compile(r"^-?[0-9]+$")


class FieldError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field, self.message = field, message


def has_control_chars(value: str) -> bool:
    """Control characters (incl. newline, tab, DEL) and Unicode line/paragraph separators."""
    return any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in value)


def _text(field: str, value, max_len: int, label: str) -> str:
    if not isinstance(value, str):
        raise FieldError(field, f"{label} is required")
    value = value.strip()
    if not value:
        raise FieldError(field, f"{label} is required")
    if has_control_chars(value):
        raise FieldError(field, f"{label} contains characters that are not allowed")
    if len(value) > max_len:
        raise FieldError(field, f"{label} must be at most {max_len} characters")
    return value


def name(value, field: str = "name") -> str:
    return _text(field, value, NAME_MAX, "Name")


def title(value, field: str = "title") -> str:
    return _text(field, value, TITLE_MAX, "Title")


def instructor(value, field: str = "instructor") -> str:
    return _text(field, value, INSTRUCTOR_MAX, "Instructor")


def email(value, field: str = "email") -> str:
    """Trimmed, lowercased, basic shape check, at most 254 characters."""
    value = _text(field, value, EMAIL_MAX, "Email").lower()
    if not _EMAIL_RE.match(value):
        raise FieldError(field, "Enter a valid email address")
    return value


def _int(field: str, value, lo: int, hi: int, label: str) -> int:
    if isinstance(value, bool):
        raise FieldError(field, f"{label} must be a whole number")
    if isinstance(value, str):
        text = value.strip()
        if not (text.isascii() and _INT_RE.match(text)):
            raise FieldError(field, f"{label} must be a whole number")
        value = int(text)
    elif not isinstance(value, int):
        raise FieldError(field, f"{label} must be a whole number")
    if not lo <= value <= hi:
        raise FieldError(field, f"{label} must be between {lo} and {hi}")
    return value


def capacity(value, field: str = "capacity") -> int:
    return _int(field, value, CAPACITY_MIN, CAPACITY_MAX, "Capacity")


def duration_min(value, field: str = "duration_min") -> int:
    return _int(field, value, DURATION_MIN, DURATION_MAX, "Duration (minutes)")


def password(value, field: str = "password", minimum: int = PASSWORD_MIN) -> str:
    """Length only (counted in characters); not stripped. Admin env password uses minimum=14."""
    if not isinstance(value, str) or len(value) < minimum:
        raise FieldError(field, f"Password must be at least {minimum} characters")
    if len(value) > PASSWORD_MAX:
        raise FieldError(field, f"Password must be at most {PASSWORD_MAX} characters")
    return value


def admin_password(value, field: str = "password") -> str:
    return password(value, field, ADMIN_PASSWORD_MIN)
