"""Routes: T4 schedule, class page, admin class management (api.md #1, #2, #9-#13).

Rules come from the kernel (`is_bookable`, `opens_at`, `is_listed`, spots-left SQL); nothing here re-implements them.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..auth.service import last_sign_in
from ..config import Settings
from ..kernel import db, rules, validators as v
from ..kernel.timeutil import (Clock, NonexistentLocalTime, format_london, from_text, parse_london_input,
                               to_london, to_text)
from ..web import flash, render
from ..web.deps import User, class_id_param, get_clock, get_settings, optional_user, require_admin

router = APIRouter()

SELECT = (f"SELECT c.*, {rules.SPOTS_LEFT_SQL} AS spots_left, "
          "(SELECT COUNT(*) FROM bookings b WHERE b.class_id = c.id AND b.status = 'booked') AS booked FROM classes c")


def state_of(row, now: datetime) -> str:
    """cancelled | started | opens_later | full | bookable (the single place the page states are decided)."""
    if row["status"] == "cancelled":
        return "cancelled"
    if from_text(row["starts_at"]) <= now:
        return "started"
    if not rules.is_bookable(row, now):
        return "opens_later"
    return "full" if row["spots_left"] <= 0 else "bookable"


def view(row, now: datetime) -> dict:
    return {"id": row["id"], "title": row["title"], "instructor": row["instructor"], "duration": row["duration_min"],
            "capacity": row["capacity"], "booked": row["booked"], "left": row["spots_left"], "status": row["status"],
            "when": format_london(from_text(row["starts_at"])), "state": state_of(row, now),
            "opens": format_london(rules.opens_at(row))}


def get_class(conn, class_id: int):
    try:
        row = conn.execute(SELECT + " WHERE c.id = ?", (class_id,)).fetchone()
    except OverflowError:  # an id larger than SQLite's 64-bit integers cannot exist
        row = None
    if row is None:
        raise HTTPException(404)
    return row


def refuse(request: Request, message: str, status: int = 409):
    return render(request, "error.html", {"heading": "Cannot do that", "message": message}, status=status)


def back(request: Request, url: str, message: str):
    resp = RedirectResponse(url, status_code=303)
    flash(request, resp, message, "success")
    return resp


# ---- public: schedule and class page -------------------------------------------------------------------------
@router.get("/")
def schedule(request: Request, user: User | None = Depends(optional_user), settings: Settings = Depends(get_settings),
             clock: Clock = Depends(get_clock)):
    now = clock.now()
    with db.read_conn(settings.database_path) as conn:  # prefilter by text bounds, then ask the kernel
        rows = conn.execute(SELECT + " WHERE c.status = 'active' AND c.starts_at > ? AND c.starts_at <= ? "
                            "ORDER BY c.starts_at, c.id",
                            (to_text(now), to_text(now + rules.LISTING_HORIZON))).fetchall()
    return render(request, "classes/schedule.html", {"classes": [view(r, now) for r in rows if rules.is_listed(r, now)]})


@router.get("/classes/{class_id}")
def class_page(request: Request, class_id: int = Depends(class_id_param), user: User | None = Depends(optional_user),
               settings: Settings = Depends(get_settings), clock: Clock = Depends(get_clock)):
    now = clock.now()
    with db.read_conn(settings.database_path) as conn:
        c = view(get_class(conn, class_id), now)
        mine = user is not None and user.role == "student" and conn.execute(
            "SELECT 1 FROM bookings WHERE class_id = ? AND user_id = ? AND status = 'booked'", (class_id, user.id)
        ).fetchone() is not None
    request.state.no_store = True  # spots left is live data, and signed-in pages embed a CSRF token
    return render(request, "classes/detail.html", {"c": c, "already_booked": mine})


# ---- admin ------------------------------------------------------------------------------------------------------
def class_form(title: str = Form(""), starts_at: str = Form(""), duration_min: str = Form(""),
               instructor: str = Form(""), capacity: str = Form("")) -> dict:
    return {"title": title, "starts_at": starts_at, "duration_min": duration_min, "instructor": instructor,
            "capacity": capacity}


def parse_form(form: dict) -> tuple[dict, dict]:
    """-> (clean values, per-field errors). The past-start check needs `now`, so it is done under the lock."""
    clean, errors = {}, {}
    for field, check in (("title", v.title), ("instructor", v.instructor), ("capacity", v.capacity),
                         ("duration_min", v.duration_min)):
        try:
            clean[field] = check(form[field])
        except v.FieldError as exc:
            errors[field] = exc.message
    try:
        clean["starts"] = parse_london_input(form["starts_at"])
    except NonexistentLocalTime:
        errors["starts_at"] = "That time does not exist in London (the clocks go forward). Pick another time."
    except ValueError as exc:
        errors["starts_at"] = str(exc)
    return clean, errors


PAST = "The start must be in the future."


def form_page(request: Request, values: dict, errors: dict, action: str, heading: str, status: int = 200):
    return render(request, "classes/admin_form.html",
                  {"values": values, "errors": errors, "action": action, "heading": heading}, status=status)


@router.get("/admin/classes")
def admin_list(request: Request, user: User = Depends(require_admin), settings: Settings = Depends(get_settings),
               clock: Clock = Depends(get_clock)):
    now = clock.now()
    with db.read_conn(settings.database_path) as conn:
        rows = conn.execute(SELECT + " ORDER BY c.starts_at DESC, c.id DESC").fetchall()
        info = last_sign_in(conn, user.id)
    last = format_london(from_text(info["previous"])) if info["previous"] else None
    return render(request, "classes/admin_list.html", {"classes": [view(r, now) for r in rows], "last_signin": last,
                                                       "failures": info["failures_since"]})


@router.get("/admin/classes/new")
def admin_new(request: Request, user: User = Depends(require_admin)):
    values = {"title": "", "starts_at": "", "duration_min": "60", "instructor": "", "capacity": "10"}
    return form_page(request, values, {}, "/admin/classes", "Add a class")


@router.post("/admin/classes")
def admin_create(request: Request, form: dict = Depends(class_form), user: User = Depends(require_admin),
                 settings: Settings = Depends(get_settings), clock: Clock = Depends(get_clock)):
    clean, errors = parse_form(form)
    new_id = None
    with db.write_tx(settings.database_path) as conn:
        now = clock.now()
        if "starts" in clean and clean["starts"] <= now:
            errors["starts_at"] = PAST
        if not errors:
            new_id = conn.execute(
                "INSERT INTO classes (title, starts_at, duration_min, instructor, capacity, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (clean["title"], to_text(clean["starts"]), clean["duration_min"], clean["instructor"],
                 clean["capacity"], to_text(now))).lastrowid
    if errors:
        return form_page(request, form, errors, "/admin/classes", "Add a class", 422)
    return back(request, f"/admin/classes/{new_id}", "Class added.")


@router.get("/admin/classes/{class_id}")
def admin_detail(request: Request, class_id: int = Depends(class_id_param), user: User = Depends(require_admin),
                 settings: Settings = Depends(get_settings), clock: Clock = Depends(get_clock)):
    now = clock.now()
    with db.read_conn(settings.database_path) as conn:
        c = view(get_class(conn, class_id), now)
        roster = conn.execute(
            "SELECT u.name, u.email FROM bookings b JOIN users u ON u.id = b.user_id "
            "WHERE b.class_id = ? AND b.status = 'booked' ORDER BY b.created_at, b.id", (class_id,)).fetchall()
    return render(request, "classes/admin_detail.html", {"c": c, "roster": roster})


def edit_values(row) -> dict:
    return {"title": row["title"], "instructor": row["instructor"], "capacity": row["capacity"],
            "duration_min": row["duration_min"],
            "starts_at": to_london(from_text(row["starts_at"])).strftime("%Y-%m-%dT%H:%M")}


@router.get("/admin/classes/{class_id}/edit")
def admin_edit(request: Request, class_id: int = Depends(class_id_param), user: User = Depends(require_admin),
               settings: Settings = Depends(get_settings), clock: Clock = Depends(get_clock)):
    with db.read_conn(settings.database_path) as conn:
        row = get_class(conn, class_id)
    if state_of(row, clock.now()) in ("cancelled", "started"):
        return refuse(request, "This class has been cancelled or has already started, so it cannot be edited.")
    return form_page(request, edit_values(row), {}, f"/admin/classes/{class_id}", "Edit class")


@router.post("/admin/classes/{class_id}")
def admin_update(request: Request, class_id: int = Depends(class_id_param), form: dict = Depends(class_form),
                 user: User = Depends(require_admin), settings: Settings = Depends(get_settings),
                 clock: Clock = Depends(get_clock)):
    clean, errors = parse_form(form)
    closed, status = False, 422
    with db.write_tx(settings.database_path) as conn:  # booked count and update under one lock (AC-6.2 race)
        now = clock.now()
        row = get_class(conn, class_id)
        if state_of(row, now) in ("cancelled", "started"):
            closed = True
        else:
            if "starts" in clean and clean["starts"] <= now:
                errors["starts_at"] = PAST
            if "capacity" in clean and clean["capacity"] < row["booked"]:  # shown even beside other field errors
                n = row["booked"]
                status = 422 if errors else 409
                errors["capacity"] = f"{n} {'student is' if n == 1 else 'students are'} already booked, so capacity cannot go below {n}."
            if not errors:
                conn.execute("UPDATE classes SET title=?, starts_at=?, duration_min=?, instructor=?, capacity=? WHERE id=?",
                             (clean["title"], to_text(clean["starts"]), clean["duration_min"], clean["instructor"],
                              clean["capacity"], class_id))
    if closed:
        return refuse(request, "This class has been cancelled or has already started, so it cannot be edited.")
    if errors:
        return form_page(request, form, errors, f"/admin/classes/{class_id}", "Edit class", status)
    return back(request, f"/admin/classes/{class_id}", "Class saved.")


@router.post("/admin/classes/{class_id}/cancel")
def admin_cancel(request: Request, class_id: int = Depends(class_id_param), user: User = Depends(require_admin),
                 settings: Settings = Depends(get_settings), clock: Clock = Depends(get_clock)):
    started = False
    with db.write_tx(settings.database_path) as conn:  # class and its bookings change together or not at all
        now = clock.now()
        row = get_class(conn, class_id)
        state = state_of(row, now)
        done = state not in ("cancelled", "started")
        started = state == "started"  # attendance history is not rewritten: refuse (owner decision)
        if done:
            conn.execute("UPDATE classes SET status = 'cancelled' WHERE id = ?", (class_id,))
            conn.execute("UPDATE bookings SET status = 'cancelled', cancelled_by = 'studio', cancelled_at = ? "
                         "WHERE class_id = ? AND status = 'booked'", (to_text(now), class_id))
    if started:
        return refuse(request, "This class has already started, so it cannot be cancelled.")
    return back(request, f"/admin/classes/{class_id}", "Class cancelled. Students are not emailed; please tell them." if done
                else "That class was already cancelled.")
