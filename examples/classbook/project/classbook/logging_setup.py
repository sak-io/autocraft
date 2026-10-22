"""One-line JSON logs to stdout with a request id; never passwords, tokens, cookies or bodies."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
logger = logging.getLogger("classbook")

_SENSITIVE = ("password", "token", "cookie", "secret", "authorization", "session", "csrf")


def _redact(fields: dict) -> dict:
    return {
        k: ("[redacted]" if any(s in k.lower() for s in _SENSITIVE) else v)
        for k, v in fields.items()
    }


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        out.update(_redact(getattr(record, "fields", {})))
        return json.dumps(out, default=str)


def configure_logging(stream=None) -> None:
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.handlers[:] = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log(level: int, msg: str, **fields) -> None:
    logger.log(level, msg, extra={"fields": fields})


_ERROR_PAGE = (
    b"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    b"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    b"<link rel=\"stylesheet\" href=\"/static/style.css\"><title>Something went wrong</title></head>"
    b"<body><h1>Something went wrong</h1><p>Please try again in a moment. Reference: %s</p></body></html>"
)


class RequestContextMiddleware:
    """Outermost ASGI layer: request id, access log line, and the generic 500 page.

    Unhandled exceptions are logged with the request id and the exception TYPE and
    stack locations only (the message and source lines can contain user input), and the client gets a
    generic page.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        rid = uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = {"code": 0, "sent": False}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"], status["sent"] = message["status"], True
                message = {**message, "headers": [*message.get("headers", []), (b"x-request-id", rid.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            frames = [f"{f.filename}:{f.lineno} {f.name}" for f in traceback.extract_tb(exc.__traceback__)]
            log(logging.ERROR, "unhandled exception", exc_type=type(exc).__name__, frames=frames)
            if not status["sent"]:
                body = _ERROR_PAGE % rid.encode()
                status["code"] = 500
                await send_wrapper({"type": "http.response.start", "status": 500, "headers": [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                    (b"cache-control", b"no-store"),
                ]})
                await send_wrapper({"type": "http.response.body", "body": body})
        finally:
            # path only: query strings can carry tokens
            log(logging.INFO, "request", method=scope["method"], path=scope["path"],
                status=status["code"], ms=round((time.perf_counter() - started) * 1000, 1))
            request_id_var.reset(token)
