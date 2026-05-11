import pytest

from users.models import User


@pytest.mark.django_db
@pytest.mark.unit
def test_create_user_hashes_password():
    user = User.objects.create_user(email="a@example.com", password="secret")
    assert user.password != "secret"
    assert user.check_password("secret")


@pytest.mark.django_db
@pytest.mark.unit
def test_create_user_defaults():
    user = User.objects.create_user(email="a@example.com", password="x")
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_active is True


@pytest.mark.django_db
@pytest.mark.unit
def test_create_user_lowercases_entire_email():
    user = User.objects.create_user(email="User.Name@EXAMPLE.COM", password="x")
    assert user.email == "user.name@example.com"


@pytest.mark.django_db
@pytest.mark.unit
def test_get_by_natural_key_is_case_insensitive():
    User.objects.create_user(email="user@example.com", password="x")
    fetched = User.objects.get_by_natural_key("User@Example.COM")
    assert fetched.email == "user@example.com"


@pytest.mark.django_db
@pytest.mark.unit
def test_save_normalizes_email_when_bypassing_manager():
    user = User(email="Direct@Example.COM")
    user.set_password("x")
    user.save()
    assert user.email == "direct@example.com"


@pytest.mark.django_db
@pytest.mark.unit
def test_create_user_requires_email():
    with pytest.raises(ValueError, match="Email must be set"):
        User.objects.create_user(email="", password="x")


@pytest.mark.django_db
@pytest.mark.unit
def test_create_superuser_sets_flags():
    user = User.objects.create_superuser(email="admin@example.com", password="x")
    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
@pytest.mark.unit
def test_create_superuser_rejects_is_staff_false():
    with pytest.raises(ValueError, match="is_staff=True"):
        User.objects.create_superuser(email="admin@example.com", password="x", is_staff=False)


@pytest.mark.django_db
@pytest.mark.unit
def test_create_superuser_rejects_is_superuser_false():
    with pytest.raises(ValueError, match="is_superuser=True"):
        User.objects.create_superuser(email="admin@example.com", password="x", is_superuser=False)
