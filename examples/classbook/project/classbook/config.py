"""Environment-only configuration, validated at startup (fail fast, never echo values)."""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field

from .kernel import validators as v

APP_ENVS = ("development", "test", "production")


class ConfigError(Exception):
    """problems: list of 'NAME: reason' strings that never contain configured values."""

    def __init__(self, problems: list[str]):
        super().__init__("Invalid configuration:\n" + "\n".join(f"  - {p}" for p in problems))
        self.problems = problems


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_path: str
    admin_email: str
    admin_password: str = field(repr=False)  # secret: excluded from repr/logs
    admin_promote_existing: bool = False
    admin_allow_email_change: bool = False
    trusted_proxy_hops: int = 0
    mail_backend: str = "recording"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        problems: list[str] = []

        def get(name: str) -> str | None:
            val = env.get(name)
            return val if val not in (None, "") else None

        def flag(name: str) -> bool:
            val = get(name)
            if val is None:
                return False
            if val.lower() in ("true", "false"):
                return val.lower() == "true"
            problems.append(f"{name}: must be 'true' or 'false'")
            return False

        app_env = get("APP_ENV") or "development"
        if app_env not in APP_ENVS:
            problems.append(f"APP_ENV: must be one of {', '.join(APP_ENVS)}")
        prod = app_env == "production"

        db_path = get("DATABASE_PATH")
        if db_path is None:
            if prod:
                problems.append("DATABASE_PATH: required in production")
            db_path = "classbook.db"

        admin_email = get("ADMIN_EMAIL")
        if admin_email is None:
            problems.append("ADMIN_EMAIL: required")
        else:
            try:
                admin_email = v.email(admin_email, "ADMIN_EMAIL")
            except v.FieldError:
                problems.append("ADMIN_EMAIL: must be a valid email address")

        admin_password = env.get("ADMIN_PASSWORD") or None
        if admin_password is None:
            problems.append("ADMIN_PASSWORD: required")
        else:
            try:
                v.admin_password(admin_password, "ADMIN_PASSWORD")
            except v.FieldError:
                problems.append(
                    f"ADMIN_PASSWORD: must be {v.ADMIN_PASSWORD_MIN} to {v.PASSWORD_MAX} characters"
                )

        hops_raw = get("TRUSTED_PROXY_HOPS")
        hops = 0
        if hops_raw is None:
            if prod:
                problems.append("TRUSTED_PROXY_HOPS: required in production (1 on Render)")
        elif hops_raw.isascii() and hops_raw.isdigit() and int(hops_raw) <= 10:
            hops = int(hops_raw)
        else:
            problems.append("TRUSTED_PROXY_HOPS: must be a whole number from 0 to 10")

        mail_backend = get("MAIL_BACKEND") or "recording"
        if mail_backend != "recording":
            problems.append("MAIL_BACKEND: only 'recording' is supported in phase 1")

        promote = flag("ADMIN_PROMOTE_EXISTING")
        allow_change = flag("ADMIN_ALLOW_EMAIL_CHANGE")

        if problems:
            raise ConfigError(problems)
        return cls(
            app_env=app_env,
            database_path=db_path,
            admin_email=admin_email,
            admin_password=admin_password,
            admin_promote_existing=promote,
            admin_allow_email_change=allow_change,
            trusted_proxy_hops=hops,
            mail_backend=mail_backend,
        )


def load_or_exit() -> Settings:
    """Load settings for a real start; print the problems (no values) and exit 1 if invalid."""
    try:
        return Settings.from_env()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from None
