import pytest
from django.urls import reverse

from users.tests.factories import UserFactory

LOGIN_URL_NAME = "login"
LOGOUT_URL_NAME = "logout"


@pytest.mark.django_db
@pytest.mark.smoke
def test_login_page_opens(client):
    response = client.get(reverse(LOGIN_URL_NAME))

    assert response.status_code == 200
    assert "Вход в систему" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_login_with_valid_credentials_redirects_through_dispatcher(client):
    user = UserFactory(password="secret")

    response = client.post(
        reverse(LOGIN_URL_NAME),
        data={"username": user.email, "password": "secret"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("post_login")


@pytest.mark.django_db
@pytest.mark.security
def test_login_with_wrong_password_shows_russian_error(client):
    user = UserFactory(password="secret")

    response = client.post(
        reverse(LOGIN_URL_NAME),
        data={"username": user.email, "password": "nope"},
    )

    assert response.status_code == 200
    assert "Неверный адрес электронной почты или пароль." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.security
def test_logout_requires_post(client):
    user = UserFactory(password="secret")
    client.login(email=user.email, password="secret")

    # GET must not log the user out (Django 5+ behavior).
    get_response = client.get(reverse(LOGOUT_URL_NAME))
    assert get_response.status_code == 405

    post_response = client.post(reverse(LOGOUT_URL_NAME))
    assert post_response.status_code == 302
    assert post_response["Location"] == reverse("public:home")
