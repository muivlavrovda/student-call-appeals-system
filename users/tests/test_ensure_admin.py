from io import StringIO

import pytest
from django.core.management import call_command

from users.models import User
from users.tests.factories import SuperUserFactory


def _run(monkeypatch, env_value):
    if env_value is None:
        monkeypatch.delenv("DJ_DEFAULT_ADMIN", raising=False)
    else:
        monkeypatch.setenv("DJ_DEFAULT_ADMIN", env_value)
    out = StringIO()
    call_command("ensure_admin", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.functional
def test_creates_admin_when_env_set_and_user_missing(monkeypatch):
    output = _run(monkeypatch, "admin@example.com|pw")

    user = User.objects.get(email="admin@example.com")
    assert user.is_superuser is True
    assert user.is_staff is True
    assert user.check_password("pw")
    assert "created" in output


@pytest.mark.django_db
@pytest.mark.integration
def test_no_op_when_env_not_set(monkeypatch):
    output = _run(monkeypatch, None)

    assert User.objects.count() == 0
    assert "not set" in output


@pytest.mark.django_db
@pytest.mark.integration
def test_warns_on_bad_format(monkeypatch):
    output = _run(monkeypatch, "no-pipe-here")

    assert User.objects.count() == 0
    assert "email|password" in output


@pytest.mark.django_db
@pytest.mark.integration
def test_skips_when_user_already_exists(monkeypatch):
    SuperUserFactory(email="admin@example.com", password="original")

    output = _run(monkeypatch, "admin@example.com|different")

    assert User.objects.count() == 1
    user = User.objects.get(email="admin@example.com")
    assert user.check_password("original")
    assert "already exists" in output


@pytest.mark.django_db
@pytest.mark.integration
def test_password_with_pipe_character(monkeypatch):
    output = _run(monkeypatch, "admin@example.com|pa|ss|word")

    user = User.objects.get(email="admin@example.com")
    assert user.check_password("pa|ss|word")
    assert "created" in output
