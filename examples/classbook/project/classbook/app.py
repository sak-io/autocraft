"""App factory. Run: uvicorn --factory classbook.app:create_app --workers 1 (ADR-0002: one worker)."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .auth.bootstrap import BootstrapError, bootstrap_admin
from .auth.service import purge_expired
from .config import Settings, load_or_exit
from .kernel import db
from .kernel.timeutil import Clock
from . import web
from .logging_setup import configure_logging, log
from .mail import build_mailer
from .routes import ROUTERS


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    configure_logging()
    settings = settings or load_or_exit()
    parent = Path(settings.database_path).resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    applied = db.migrate(settings.database_path)
    if applied:
        log(logging.INFO, "migrations applied", versions=applied)

    clock = clock or Clock()
    try:
        bootstrap_admin(settings, clock)  # admin cases a-c; refusals stop the start (F25)
    except BootstrapError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from None
    with db.write_tx(settings.database_path) as conn:
        purge_expired(conn, clock.now())

    app = FastAPI(title="ClassBook", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.clock = clock
    app.state.last_purge = clock.now()
    app.state.mailer = build_mailer(settings)

    @app.exception_handler(db.DatabaseBusy)
    async def busy(request: Request, exc: db.DatabaseBusy):
        return HTMLResponse(
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Busy</title></head>"
            "<body><h1>We are busy right now</h1><p>Please try again in a few seconds.</p></body></html>",
            status_code=503,
            headers={"Retry-After": "5"},
        )

    @app.get("/health")
    def health():
        try:
            with db.read_conn(settings.database_path) as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception as exc:
            log(logging.ERROR, "health check failed", exc_type=type(exc).__name__)
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ok"}

    for router in ROUTERS:  # empty until T3/T4/T5 fill them in (F26)
        app.include_router(router)
    web.install(app, settings)
    return app
