"""Mutation probes (T7): apply one plausible wrong change to a COPY of the production code and check that the
named tests notice. Nothing in the real tree is touched.

Run from the repository root:   python tests/qa/mutation_probes.py [name-prefix ...]
Prints CAUGHT or SURVIVED for each mutant (all 21 were CAUGHT when T7 was written).
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
WORK = pathlib.Path(tempfile.mkdtemp(prefix="classbook-mutant-"))

MUTANTS = [
 ("M1 mail sent inline, not after the response", "classbook/routes/bookings.py",
  "        tasks.add_task(send_confirmation, settings.database_path, clock, mailer, kind=kind,\n                       booking_id=result.booking_id, to_email=result.user_email,\n                       class_title=result.class_title, starts_at=result.starts_at)",
  "        send_confirmation(settings.database_path, clock, mailer, kind=kind,\n                       booking_id=result.booking_id, to_email=result.user_email,\n                       class_title=result.class_title, starts_at=result.starts_at)",
  "tests/qa/test_followups.py -k 'after_the_response'"),
 ("M2 student e-mail appended to the message body", "classbook/mail/templates.py",
  'f"Status: {kind}\\n\\nThis is an automatic message from ClassBook.\\n")',
  'f"Status: {kind}\\n\\nThis is an automatic message from ClassBook.\\nSent to {to_email}\\n")',
  "tests/qa/test_followups.py -k 'not_the_students_name'"),
 ("M3 password hashed inside the signup write transaction", "classbook/routes/accounts.py",
  '        pw_hash = hash_password(clean["password"])  # outside the transaction\n        try:\n            with db.write_tx(path) as conn:\n',
  '        try:\n            with db.write_tx(path) as conn:\n                pw_hash = hash_password(clean["password"])\n',
  "tests/qa/test_followups.py -k 'no_password_hashing'"),
 ("M4a scrypt p=2", "classbook/auth/passwords.py", "N, R, P, DKLEN = 2**14, 8, 1, 32", "N, R, P, DKLEN = 2**14, 8, 2, 32",
  "tests/qa/test_followups.py -k 'scrypt_parameters'"),
 ("M4b scrypt N=2**13 (weaker)", "classbook/auth/passwords.py", "N, R, P, DKLEN = 2**14, 8, 1, 32", "N, R, P, DKLEN = 2**13, 8, 1, 32",
  "tests/qa/test_followups.py -k 'scrypt_parameters'"),
 ("M5 lock timeout answers 500 instead of 503", "classbook/app.py", "status_code=503,\n            headers={\"Retry-After\": \"5\"},", "status_code=500,\n            headers={\"Retry-After\": \"5\"},",
  "tests/qa/test_followups.py -k 'every_write_route'"),
 ("M6 studio class cancel also queues e-mails", "classbook/routes/classes.py",
  "                         \"WHERE class_id = ? AND status = 'booked'\", (to_text(now), class_id))",
  "                         \"WHERE class_id = ? AND status = 'booked'\", (to_text(now), class_id))\n            conn.execute(\"INSERT INTO messages (to_email, subject, body, kind, booking_id, status, created_at) SELECT u.email,'s','b','cancelled',b.id,'recorded','2026-01-01T00:00:00Z' FROM bookings b JOIN users u ON u.id=b.user_id WHERE b.class_id=?\", (class_id,))",
  "tests/qa/test_followups.py -k 'studio_cancelling'"),
 ("M7 an empty router is registered", "classbook/routes/__init__.py", "ROUTERS = [accounts.router, classes.router, bookings.router]",
  "from fastapi import APIRouter\nROUTERS = [accounts.router, classes.router, bookings.router, APIRouter()]",
  "tests/qa/test_route_guards.py -k 'every_router'"),
 ("M8 admin class-cancel loses its admin guard", "classbook/routes/classes.py",
  "def admin_cancel(class_id: int, request: Request, user: User = Depends(require_admin),", "def admin_cancel(class_id: int, request: Request, user: User = Depends(optional_user),",
  "tests/qa/test_route_guards.py tests/qa/test_authz_matrix.py -x"),
 ("M8b booking cancel loses the student guard (admin allowed)", "classbook/routes/bookings.py",
  "def cancel(booking_id: int, request: Request, tasks: BackgroundTasks, user: User = Depends(require_student),", "def cancel(booking_id: int, request: Request, tasks: BackgroundTasks, user: User = Depends(__import__('classbook.web.deps', fromlist=['x']).require_user),",
  "tests/qa/test_route_guards.py tests/qa/test_authz_matrix.py -x"),
 ("M9 cancel no longer checks booking ownership", "classbook/services/bookings.py", '"FROM bookings b JOIN classes c ON c.id = b.class_id WHERE b.id = ? AND b.user_id = ?",\n            (booking_id, user_id),',
  '"FROM bookings b JOIN classes c ON c.id = b.class_id WHERE b.id = ? AND ? > 0",\n            (booking_id, user_id),',
  "tests/qa/test_authz_matrix.py -x"),
 ("M10 login label removed", "classbook/web/templates/login.html", '<label for="email">Email</label><br>', 'Email<br>',
  "tests/qa/test_accessibility.py -k 'structurally and login' -x"),
 ("M11 html lang removed", "classbook/web/templates/base.html", '<html lang="en">', '<html>', "tests/qa/test_accessibility.py -x"),
 ("M12 second h1 on the schedule", "classbook/web/templates/classes/schedule.html", '<h2><a href="/classes/{{ c.id }}">{{ c.title }}</a></h2>', '<h1><a href="/classes/{{ c.id }}">{{ c.title }}</a></h1>',
  "tests/qa/test_accessibility.py -x"),
 ("M13 focus outline removed", "classbook/web/static/style.css", "outline: 3px solid var(--accent); outline-offset: 2px;", "outline: none;",
  "tests/qa/test_accessibility.py -k focus -x"),
 ("M14 muted colour too pale", "classbook/web/static/style.css", "--muted:#5b6770", "--muted:#99a3aa",
  "tests/qa/test_accessibility.py -k wcag -x"),
 ("M15 book race: BEGIN IMMEDIATE -> BEGIN", "classbook/kernel/db.py", 'conn.execute("BEGIN IMMEDIATE")', 'conn.execute("BEGIN")',
  "tests/e2e/test_booking_race_http.py -x"),
 ("M16 overbooking check weakened (<= 0 -> < 0)", "classbook/services/bookings.py", "if rules.spots_left(conn, class_id) <= 0:", "if rules.spots_left(conn, class_id) < 0:",
  "tests/e2e/test_booking_race_http.py -x"),
 ("M17 duplicate-booking guard removed (and unique index tolerated)", "classbook/services/bookings.py", "        if existing:\n            return Result(Outcome.ALREADY_BOOKED, booking_id=existing[\"id\"], **base)\n", "",
  "tests/e2e/test_booking_race_http.py -k double_click -x"),
 ("M18 studio cancel leaves bookings 'booked'", "classbook/routes/classes.py", "UPDATE bookings SET status = 'cancelled', cancelled_by = 'studio', cancelled_at = ? \"\n                         \"WHERE class_id = ? AND status = 'booked'\"", "UPDATE bookings SET cancelled_at = ? \"\n                         \"WHERE class_id = ? AND status = 'booked'\"",
  "tests/e2e/test_journey_http.py tests/e2e/test_booking_race_http.py -x"),
 ("M19 session cookie not HttpOnly", "classbook/auth/web.py", '"Max-Age={max_age}", "HttpOnly", "SameSite=Lax"]', '"Max-Age={max_age}", "SameSite=Lax"]',
  "tests/e2e/test_journey_http.py -x"),
]
only = sys.argv[1:]
for name, f, old, new, sel in MUTANTS:
    if only and not any(name.startswith(o) for o in only): continue
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()
    shutil.copytree(SRC/"classbook", WORK/"classbook", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(SRC/"tests", WORK/"tests", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(SRC/"pytest.ini", WORK/"pytest.ini")
    (WORK/"docs/architecture").mkdir(parents=True); shutil.copy(SRC/"docs/architecture/api.md", WORK/"docs/architecture/api.md")
    p = WORK/f; s = p.read_text()
    if old not in s:
        print(f"{name}: PATTERN NOT FOUND"); continue
    p.write_text(s.replace(old, new, 1))
    r = subprocess.run(f"{PY} -m pytest -o addopts='' -q -p no:cacheprovider {sel} 2>&1 | tail -3", shell=True, cwd=WORK, capture_output=True, text=True)
    last = [l for l in r.stdout.strip().splitlines() if "passed" in l or "failed" in l or "error" in l]
    print(f"{name}: {'CAUGHT' if ' failed' in (last[-1] if last else '') or ' error' in (last[-1] if last else '') else 'SURVIVED'}  [{last[-1] if last else r.stdout[-200:]}]")
