"""Cookie naming and attributes: one `Secure` switch (APP_ENV=production) and `__Host-` prefixes there."""
from __future__ import annotations

from ..config import Settings


def cookie_name(settings: Settings, base: str) -> str:
    # __Host- needs Secure + Path=/ + no Domain, which only holds over HTTPS (production).
    return f"__Host-{base}" if settings.is_production else base


def set_cookie_header(settings: Settings, base: str, value: str) -> tuple[bytes, bytes]:
    parts = [f"{cookie_name(settings, base)}={value}", "Path=/", "HttpOnly", "SameSite=Lax"]
    if settings.is_production:
        parts.append("Secure")
    return b"set-cookie", "; ".join(parts).encode("latin-1")
