import pytest
from starlette.requests import Request

from classbook.web.util import client_ip, login_url, safe_next


@pytest.mark.parametrize("value", ["/", "/classes/5", "/my-bookings", "/admin/classes?x=1", "/a%20b", "/classes/5/"])
def test_next_accepts_local_paths(value):
    assert safe_next(value) == value


@pytest.mark.parametrize("value", [
    "//evil.com", "/\\evil.com", "/\\/evil.com", "/a\\b", "https://evil.com", "http:evil.com", "javascript:alert(1)",
    "evil.com", "", None, 5, "/%2fevil.com", "/%2Fevil.com", "/x%5cevil", "/x%5Cevil", "/a//b",
    "/\tevil", "/a\nb", "/a\rb", "/a\x00b", "/a%0d%0aSet-Cookie:x", "/a%00b", "/a b", "/" + "a" * 600,
    "/http://evil.com", " /ok",
])
def test_next_rejects_unsafe_values_with_root(value):
    assert safe_next(value) == "/"


def req(client=("10.0.0.9", 1234), xff=(), method="GET", path="/classes/5"):
    headers = [(b"x-forwarded-for", v.encode()) for v in xff]
    return Request({"type": "http", "method": method, "path": path, "headers": headers, "client": client, "query_string": b""})


def test_ip_hops_zero_uses_socket_and_ignores_header():
    assert client_ip(req(xff=["6.6.6.6"]), 0) == "10.0.0.9"


def test_ip_takes_entry_from_the_right_not_what_the_client_wrote():
    # client sent "1.1.1.1" (spoof); our proxy appended the real address
    assert client_ip(req(xff=["1.1.1.1, 203.0.113.7"]), 1) == "203.0.113.7"
    assert client_ip(req(xff=["1.1.1.1", "2.2.2.2, 203.0.113.7"]), 1) == "203.0.113.7"
    assert client_ip(req(xff=["1.1.1.1, 203.0.113.7, 10.1.1.1"]), 2) == "203.0.113.7"


def test_ip_falls_back_to_socket_when_header_missing_short_or_garbage():
    assert client_ip(req(), 1) == "10.0.0.9"
    assert client_ip(req(xff=["203.0.113.7"]), 2) == "10.0.0.9"
    assert client_ip(req(xff=["1.1.1.1, not-an-ip"]), 1) == "10.0.0.9"


def test_ip_normalises_ipv6():
    assert client_ip(req(xff=["2001:DB8:0:0:0:0:0:1"]), 1) == "2001:db8::1"


def test_login_url_carries_get_path_only():
    assert login_url(req(path="/classes/5")) == "/login?next=/classes/5"
    assert login_url(req(method="POST")) == "/login"
