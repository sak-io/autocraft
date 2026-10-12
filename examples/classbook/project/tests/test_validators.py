import pytest

from classbook.kernel import validators as v


def bad(fn, *a, **k):
    with pytest.raises(v.FieldError) as e:
        fn(*a, **k)
    return e.value


def test_text_limits_at_the_edge():
    assert v.name("a" * 80) == "a" * 80
    bad(v.name, "a" * 81)
    assert v.title("t" * 100)
    bad(v.title, "t" * 101)
    assert v.instructor("i" * 80)
    bad(v.instructor, "i" * 81)


def test_blank_and_non_string_rejected_and_values_are_trimmed():
    for fn in (v.name, v.title, v.instructor, v.email):
        bad(fn, "   ")
        bad(fn, None)
    assert v.title("  Flow  ") == "Flow"


@pytest.mark.parametrize("ch", ["\n", "\r", "\t", "\x00", "\x7f", " ", " "])
def test_control_characters_rejected_in_text_fields(ch):
    for fn in (v.name, v.title, v.instructor):
        bad(fn, f"ab{ch}cd")


def test_email_normalised_and_shape_checked():
    assert v.email("  Maya@Example.COM ") == "maya@example.com"
    for e in ("nope", "a@b", "a b@c.de", "@x.io", "a@@x.io"):
        bad(v.email, e)
    assert v.email("a@b." + "c" * 250)
    bad(v.email, "a@" + "b" * 250)  # 255


def test_email_newline_injection_rejected():
    bad(v.email, "a@x.io\nBcc: evil@x.io")


def test_capacity_bounds_and_types():
    assert v.capacity("1") == 1 and v.capacity("200") == 200 and v.capacity(" 20 ") == 20
    for x in ("0", "-1", "201", "1.5", "abc", "", "١٢", True, None, 2.0):
        bad(v.capacity, x)


def test_duration_bounds():
    assert v.duration_min("5") == 5 and v.duration_min("480") == 480
    for x in ("4", "481", "x", "0"):
        bad(v.duration_min, x)


def test_password_length_rules():
    assert v.password("a" * 10) and v.password("a" * 128)
    bad(v.password, "a" * 9)
    bad(v.password, "a" * 129)
    assert v.password("  spaces kept  ") == "  spaces kept  "
    assert v.admin_password("a" * 14)
    bad(v.admin_password, "a" * 13)


def test_messages_do_not_echo_input():
    err = bad(v.email, "secret-value-not-an-email")
    assert "secret-value" not in err.message
    assert err.field == "email"
