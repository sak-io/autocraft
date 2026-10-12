import pytest

from classbook.config import ConfigError, Settings, load_or_exit
from tests.conftest import GOOD_ENV


def test_valid_config_with_defaults():
    s = Settings.from_env(GOOD_ENV)
    assert s.app_env == "test" and s.mail_backend == "recording"
    assert s.trusted_proxy_hops == 0 and not s.admin_promote_existing and not s.admin_allow_email_change
    assert s.admin_email == "maya@example.com"
    assert not s.is_production


@pytest.mark.parametrize("missing", ["ADMIN_EMAIL", "ADMIN_PASSWORD"])
def test_missing_required_fails_fast_naming_the_variable(missing):
    env = {k: v for k, v in GOOD_ENV.items() if k != missing}
    with pytest.raises(ConfigError) as e:
        Settings.from_env(env)
    assert missing in str(e.value)


def test_admin_password_shorter_than_14_refuses_and_does_not_echo():
    env = {**GOOD_ENV, "ADMIN_PASSWORD": "short-pw-13ch"}  # 13 chars
    assert len(env["ADMIN_PASSWORD"]) == 13
    with pytest.raises(ConfigError) as e:
        Settings.from_env(env)
    assert "ADMIN_PASSWORD" in str(e.value) and "short-pw" not in str(e.value)


def test_admin_password_of_exactly_14_is_accepted():
    assert Settings.from_env({**GOOD_ENV, "ADMIN_PASSWORD": "x" * 14})


def test_no_value_is_ever_echoed_in_errors():
    env = {"APP_ENV": "hunter2-env", "ADMIN_EMAIL": "hunter2-not-email", "ADMIN_PASSWORD": "hunter2",
           "TRUSTED_PROXY_HOPS": "hunter2", "MAIL_BACKEND": "hunter2", "ADMIN_PROMOTE_EXISTING": "hunter2"}
    with pytest.raises(ConfigError) as e:
        Settings.from_env(env)
    assert len(e.value.problems) >= 6
    assert "hunter2" not in str(e.value)


def test_only_recording_mail_backend_allowed():
    with pytest.raises(ConfigError) as e:
        Settings.from_env({**GOOD_ENV, "MAIL_BACKEND": "smtp"})
    assert "MAIL_BACKEND" in str(e.value)


def test_production_requires_database_path_and_proxy_hops():
    with pytest.raises(ConfigError) as e:
        Settings.from_env({**GOOD_ENV, "APP_ENV": "production"})
    assert "DATABASE_PATH" in str(e.value) and "TRUSTED_PROXY_HOPS" in str(e.value)
    s = Settings.from_env({**GOOD_ENV, "APP_ENV": "production", "DATABASE_PATH": "/data/c.db", "TRUSTED_PROXY_HOPS": "1"})
    assert s.is_production and s.trusted_proxy_hops == 1


def test_bool_flags_and_hops_parsing():
    s = Settings.from_env({**GOOD_ENV, "ADMIN_PROMOTE_EXISTING": "true", "ADMIN_ALLOW_EMAIL_CHANGE": "False", "TRUSTED_PROXY_HOPS": "2"})
    assert s.admin_promote_existing and not s.admin_allow_email_change and s.trusted_proxy_hops == 2
    for bad in ("-1", "x", "11", "1.5"):
        with pytest.raises(ConfigError):
            Settings.from_env({**GOOD_ENV, "TRUSTED_PROXY_HOPS": bad})


def test_repr_hides_the_admin_password():
    assert "a-long-test-password" not in repr(Settings.from_env(GOOD_ENV))


def test_load_or_exit_exits_1_without_secrets(monkeypatch, capsys):
    monkeypatch.setattr("os.environ", {"ADMIN_EMAIL": "maya@example.com", "ADMIN_PASSWORD": "tooshort-sec"})
    with pytest.raises(SystemExit) as e:
        load_or_exit()
    assert e.value.code == 1
    err = capsys.readouterr().err
    assert "ADMIN_PASSWORD" in err and "tooshort-sec" not in err
