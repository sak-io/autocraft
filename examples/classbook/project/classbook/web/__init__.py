"""Web shell (T2): templates, CSRF, flash, security headers, body limit, guards, error pages."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import RedirectResponse

from ..config import Settings
from ..logging_setup import RequestContextMiddleware
from .csrf import csrf_field, rotate_csrf  # noqa: F401  (public API for T3+)
from .deps import RedirectTo
from .middleware import BodyLimitMiddleware, CsrfMiddleware, SecurityHeadersMiddleware
from .templating import HERE, flash, make_templates, render  # noqa: F401

_MESSAGES = {
    403: ("Not allowed", "You do not have permission to do that."),
    404: ("Not found", "We could not find that page."),
    405: ("Not allowed", "That is not something this page can do."),
    429: ("Too many attempts", "Please wait a few minutes and try again."),
    503: ("We are busy right now", "Please try again in a few seconds."),
}


def install(app: FastAPI, settings: Settings) -> None:
    app.state.templates = make_templates()
    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

    @app.exception_handler(RedirectTo)
    async def redirect(request: Request, exc: RedirectTo):
        return RedirectResponse(exc.location, status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if not hasattr(request.state, "user"):  # unguarded routes (404/405) never looked the user up
            from .deps import current_user
            try:
                request.state.user = current_user(request)
            except Exception:  # an error page must still render
                request.state.user = None
            if request.state.user is not None:
                request.state.no_store = True
        heading, message = _MESSAGES.get(exc.status_code, ("Something went wrong", "Please try again."))
        resp = render(request, "error.html", {"heading": heading, "message": message}, status=exc.status_code)
        resp.headers.update(exc.headers or {})
        return resp

    # add_middleware puts the last-added outermost: headers > request id/500 > body limit > csrf > routes
    app.add_middleware(CsrfMiddleware, settings=settings)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
