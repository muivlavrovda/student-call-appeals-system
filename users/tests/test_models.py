import pytest
from django.db import IntegrityError

from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.unit
def test_username_field_is_email():
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []


@pytest.mark.unit
def test_user_has_no_username_attribute():
    assert User.username is None


@pytest.mark.django_db
@pytest.mark.unit
def test_email_is_unique():
    UserFactory(email="dup@example.com")
    with pytest.raises(IntegrityError):
        UserFactory(email="dup@example.com")


@pytest.mark.django_db
@pytest.mark.unit
def test_default_ordering_is_recent_first():
    older = UserFactory()
    newer = UserFactory()
    assert list(User.objects.all()) == [newer, older]
