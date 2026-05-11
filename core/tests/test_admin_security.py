import pytest
from django.urls import reverse

from users.tests.factories import StaffUserFactory, UserFactory


@pytest.mark.django_db
@pytest.mark.security
def test_anonymous_user_is_redirected_from_admin(client):
    response = client.get(reverse("admin:index"))
    assert response.status_code == 302
    assert reverse("admin:login") in response["Location"]


@pytest.mark.django_db
@pytest.mark.security
def test_regular_user_cannot_open_admin(client):
    user = UserFactory(password="secret")
    assert client.login(email=user.email, password="secret")

    response = client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert reverse("admin:login") in response["Location"]


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.functional
def test_staff_user_can_open_admin(client):
    user = StaffUserFactory(password="secret")
    assert client.login(email=user.email, password="secret")

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200
