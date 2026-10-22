"""T7 (2): every route is accounted for, every non-public route has a guard, and the docs match the code.

Threat model T-2: "enumeration test fails on any unguarded non-public route". The policy table below is the
declared intent; a new route that is not in the table fails here, so nobody can add an open route by accident.
"""
import re
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends, FastAPI
from starlette.routing import Mount

from classbook.app import create_app
from classbook.routes import ROUTERS
from classbook.web import deps

ROOT = Path(__file__).resolve().parents[2]

# (method, path) -> declared guard. "open" = deliberately no guard (health probe only).
POLICY = {
    ("GET", "/health"): "open",
    ("GET", "/"): "public",
    ("GET", "/classes/{class_id}"): "public",
    ("GET", "/login"): "public", ("POST", "/login"): "public",
    ("GET", "/signup"): "public", ("POST", "/signup"): "public",
    ("POST", "/logout"): "user",
    ("POST", "/classes/{class_id}/book"): "student",
    ("GET", "/my-bookings"): "student",
    ("POST", "/bookings/{booking_id}/cancel"): "student",
    ("GET", "/admin/classes"): "admin",
    ("GET", "/admin/classes/new"): "admin",
    ("POST", "/admin/classes"): "admin",
    ("GET", "/admin/classes/{class_id}"): "admin",
    ("GET", "/admin/classes/{class_id}/edit"): "admin",
    ("POST", "/admin/classes/{class_id}"): "admin",
    ("POST", "/admin/classes/{class_id}/cancel"): "admin",
}
GUARD_LEVEL = {deps.optional_user: "public", deps.require_user: "user",
               deps.require_student: "student", deps.require_admin: "admin"}
STRENGTH = ["open", "public", "user", "student", "admin"]
# Documented in api.md but not built yet. T8 owns it; delete the entry when T8 lands (the parity test then
# forces the route into POLICY and the authz matrix).
NOT_BUILT_YET = {("GET", "/admin/backup")}


def _walk(dependant, seen):
    for sub in dependant.dependencies:
        if sub.call in GUARD_LEVEL:
            seen.add(GUARD_LEVEL[sub.call])
        _walk(sub, seen)


def guard_of(route) -> str:
    """Strongest declared guard of a route ("open" when none); "conflict" if student and admin both appear."""
    seen: set[str] = set()
    _walk(route.dependant, seen)
    for dep in getattr(route, "dependencies", None) or []:  # router- and include-level dependencies
        if dep.dependency in GUARD_LEVEL:
            seen.add(GUARD_LEVEL[dep.dependency])
    if "student" in seen and "admin" in seen:
        return "conflict"
    for level in reversed(STRENGTH):
        if level in seen:
            return level
    return "open"


def _flatten(routes):
    """Yield every concrete route, whatever this FastAPI version calls included routers."""
    for r in routes:
        if hasattr(r, "effective_candidates"):  # FastAPI >= 0.14x lazy included router
            yield from _flatten(r.effective_candidates())
        elif hasattr(r, "routes") and not isinstance(r, Mount):
            yield from _flatten(r.routes)
        else:
            yield r


def enumerate_routes(app: FastAPI) -> dict[tuple[str, str], str]:
    found = {}
    for r in _flatten(app.router.routes):
        if getattr(r, "dependant", None) is not None and getattr(r, "methods", None):
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                assert (m, r.path) not in found, f"duplicate route {m} {r.path}"
                found[(m, r.path)] = guard_of(r)
        else:
            assert isinstance(r, Mount) and r.path == "/static", f"unexpected non-API route {r!r}"
    return found


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from tests.qa.support import env_for
    from classbook.config import Settings
    path = tmp_path_factory.mktemp("guards") / "g.db"
    return create_app(Settings.from_env(env_for(path)))


def test_every_route_is_declared_and_guarded_as_intended(app):
    found = enumerate_routes(app)
    assert set(found) == set(POLICY), (
        f"undeclared routes: {sorted(set(found) - set(POLICY))}; stale policy entries: {sorted(set(POLICY) - set(found))}")
    wrong = {k: (found[k], POLICY[k]) for k in POLICY if found[k] != POLICY[k]}
    assert not wrong, f"guard differs from declared policy (actual, declared): {wrong}"


def test_only_the_health_probe_is_open_and_every_other_route_has_a_guard(app):
    open_routes = [k for k, g in enumerate_routes(app).items() if g == "open"]
    assert open_routes == [("GET", "/health")]


def test_every_state_changing_or_private_route_is_not_public(app):
    for (method, path), guard in enumerate_routes(app).items():
        if path.startswith(("/admin", "/my-bookings", "/bookings", "/logout")) or path.endswith("/book"):
            assert guard in ("user", "student", "admin"), (method, path, guard)


def test_admin_paths_demand_the_admin_guard_and_student_actions_the_student_guard(app):
    for (method, path), guard in enumerate_routes(app).items():
        if path.startswith("/admin"):
            assert guard == "admin", (method, path)
    assert enumerate_routes(app)[("POST", "/classes/{class_id}/book")] == "student"


def test_the_enumeration_really_detects_an_unguarded_route():
    """Self-test with a mutant app: a route that forgot its guard must show up as 'open', a student-guarded
    admin path as 'student'."""
    router = APIRouter()

    @router.get("/admin/secret")
    def secret():
        return "x"

    @router.post("/admin/oops")
    def oops(user=Depends(deps.require_student)):
        return "x"

    @router.get("/admin/ok")
    def ok(user=Depends(deps.require_admin)):
        return "x"

    mutant = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    mutant.include_router(router)
    found = enumerate_routes(mutant)
    assert found[("GET", "/admin/secret")] == "open"
    assert found[("POST", "/admin/oops")] == "student"
    assert found[("GET", "/admin/ok")] == "admin"


def test_every_router_registered_in_the_factory_has_routes():
    """STATUS follow-up (T5 M-2 / T5fix): an accidentally empty router must be caught."""
    assert len(ROUTERS) >= 3
    for router in ROUTERS:
        assert len(router.routes) > 0, f"empty router {router!r}"


def test_no_interactive_docs_or_schema_endpoints_are_exposed(world):
    anon = world.browser(None)
    for path in ("/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"):
        assert anon.get(path).status_code == 404, path


def _documented_routes() -> set[tuple[str, str]]:
    text = (ROOT / "docs/architecture/api.md").read_text()
    out = set()
    for line in text.splitlines():
        if not re.match(r"\| \d+ \|", line):
            continue
        cell = line.split("|")[2]
        for chunk in re.findall(r"`([^`]+)`", cell):
            m = re.match(r"((?:GET|POST)(?:/(?:GET|POST))?) (/\S*)", chunk)
            if m:
                for method in m.group(1).split("/"):
                    out.add((method, m.group(2)))
    return out


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


def test_api_md_and_the_code_describe_the_same_routes(app):
    """Docs are the source of truth (rule 4): every built route is documented, and only the declared
    not-yet-built route is documented without existing."""
    documented = {(m, _norm(p)) for m, p in _documented_routes()}
    built = {(m, _norm(p)) for m, p in enumerate_routes(app)}
    assert len(documented) >= 18, documented  # the parser itself works
    assert built <= documented, f"routes missing from api.md: {sorted(built - documented)}"
    missing = documented - built
    assert missing == {(m, _norm(p)) for m, p in NOT_BUILT_YET}, f"documented but not built: {sorted(missing)}"
