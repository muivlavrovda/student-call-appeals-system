import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from appeals.roles import ADMIN_GROUP, OPERATOR_GROUP, RESPONSIBLE_GROUP, sync_access_groups
from users.tests.factories import UserFactory

POST_LOGIN_URL_NAME = "post_login"
LIST_URL_NAME = "appeals:appeal_list"
LOGIN_URL = "/accounts/login/"


def _user_in_group(*group_names: str, password: str = "secret"):
    sync_access_groups()
    user = UserFactory(password=password)
    user.groups.add(*Group.objects.filter(name__in=group_names))
    return user


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_redirects_anonymous_to_login(client):
    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_sends_staff_to_admin_panel(client):
    admin = _user_in_group(ADMIN_GROUP, password="secret")
    admin.is_staff = True
    admin.save(update_fields=["is_staff"])
    client.login(email=admin.email, password="secret")

    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert response["Location"] == reverse("admin:index")


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_sends_staff_without_appeal_perms_to_admin_panel(client):
    # Staff access alone is enough to land in the admin panel.
    user = UserFactory(password="secret", is_staff=True)
    client.login(email=user.email, password="secret")

    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert response["Location"] == reverse("admin:index")


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_sends_nonstaff_admin_group_to_cabinet(client):
    # Regression: an Admin-group member who is not staff has the appeal
    # permissions but no admin access, so the cabinet is the right landing.
    admin = _user_in_group(ADMIN_GROUP, password="secret")
    assert admin.is_staff is False
    client.login(email=admin.email, password="secret")

    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert response["Location"] == reverse(LIST_URL_NAME)


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_sends_operator_to_cabinet(client):
    operator = _user_in_group(OPERATOR_GROUP, password="secret")
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert response["Location"] == reverse(LIST_URL_NAME)


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_sends_responsible_to_cabinet(client):
    responsible = _user_in_group(RESPONSIBLE_GROUP, password="secret")
    client.login(email=responsible.email, password="secret")

    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert response["Location"] == reverse(LIST_URL_NAME)


@pytest.mark.django_db
@pytest.mark.functional
def test_post_login_sends_plain_user_home(client):
    user = UserFactory(password="secret")
    client.login(email=user.email, password="secret")

    response = client.get(reverse(POST_LOGIN_URL_NAME))

    assert response.status_code == 302
    assert response["Location"] == reverse("public:home")
