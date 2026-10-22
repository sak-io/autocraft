import pytest

from tests.qa.support import build_template, copy_world


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    return build_template(tmp_path_factory.mktemp("qa-template"))


@pytest.fixture
def world(template_db, tmp_path):
    """A private copy of the seeded database with a running app (FixedClock at NOW)."""
    return copy_world(template_db, tmp_path)
