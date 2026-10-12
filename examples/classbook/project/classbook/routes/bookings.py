"""Routes: T5 book, my bookings, cancel. HTTP only; every rule lives in services/bookings.py."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..kernel import db, rules
from ..kernel.timeutil import format_london, from_text
from ..mail.outbox import send_confirmation
from ..services import bookings as svc
from ..services.bookings import Outcome
from ..web import flash, render
from ..web.deps import User, get_clock, get_mailer, get_settings, require_student

router = APIRouter()
O = Outcome

# outcome -> (status, heading, message) for refusals shown as a page
_REFUSALS = {
    O.STARTED_OR_CANCELLED: (409, "Class not available", "This class has already started or has been cancelled, so it cannot be booked."),
    O.FULL: (409, "Class is full", "Sorry, this class is full. No booking was made."),
    O.TOO_LATE: (409, "Too late to cancel", "Classes can only be cancelled online up to 12 hours before they start. Your booking is unchanged."),
    O.THROTTLED: (429, "Too many requests", "You have made a lot of booking changes in the last hour. Please try again later."),
}


def _refusal(request: Request, result: svc.Result):
    if result.outcome is O.TOO_FAR_AHEAD:
        status, heading = 409, "Not open for booking yet"
        message = f"Booking for this class opens on {format_london(result.opens_at)}."
    else:
        status, heading, message = _REFUSALS[result.outcome]
    resp = render(request, "bookings/refused.html", {"heading": heading, "message": message}, status=status)
    if status == 429:
        resp.headers["Retry-After"] = "3600"
    return resp


def _mail(tasks: BackgroundTasks, settings, clock, mailer, result: svc.Result, kind: str):
    """Queue the confirmation to run after the response, i.e. after commit. Only for a real change."""
    if result.changed:
        tasks.add_task(send_confirmation, settings.database_path, clock, mailer, kind=kind,
                       booking_id=result.booking_id, to_email=result.user_email,
                       class_title=result.class_title, starts_at=result.starts_at)


def _done(request: Request, text: str, level: str = "success"):
    resp = RedirectResponse("/my-bookings", status_code=303)
    flash(request, resp, text, level)
    return resp


@router.post("/classes/{class_id}/book")
def book(class_id: int, request: Request, tasks: BackgroundTasks, user: User = Depends(require_student),
         settings=Depends(get_settings), clock=Depends(get_clock),
         mailer=Depends(get_mailer)):
    result = svc.book(settings.database_path, clock, user.id, class_id)
    if result.outcome is O.NOT_FOUND:
        raise HTTPException(404)
    _mail(tasks, settings, clock, mailer, result, "booked")
    if result.outcome is O.BOOKED:
        return _done(request, f"Booked: {result.class_title}, {format_london(result.starts_at)}.")
    if result.outcome is O.ALREADY_BOOKED:
        return _done(request, "You are already booked on this class.", "info")
    return _refusal(request, result)


@router.get("/my-bookings")
def my_bookings(request: Request, user: User = Depends(require_student),
                settings=Depends(get_settings), clock=Depends(get_clock)):
    now = clock.now()
    with db.read_conn(settings.database_path) as conn:
        rows = svc.upcoming_for(conn, user.id, now)
    items = [{**r, "when": format_london(from_text(r["starts_at"])),
              "studio_cancelled": r["status"] == "cancelled",
              "can_cancel": r["status"] == "booked" and rules.cancel_allowed(r, now)} for r in rows]
    return render(request, "bookings/my_bookings.html", {"items": items})


@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, request: Request, tasks: BackgroundTasks, user: User = Depends(require_student),
           settings=Depends(get_settings), clock=Depends(get_clock), mailer=Depends(get_mailer)):
    result = svc.cancel(settings.database_path, clock, user.id, booking_id)
    if result.outcome is O.NOT_FOUND:
        raise HTTPException(404)
    _mail(tasks, settings, clock, mailer, result, "cancelled")
    if result.outcome is O.CANCELLED:
        return _done(request, f"Cancelled: {result.class_title}, {format_london(result.starts_at)}.")
    if result.outcome is O.ALREADY_CANCELLED:
        return _done(request, "That booking was already cancelled.", "info")
    return _refusal(request, result)
