from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from appeals.models import Appeal
from appeals.roles import ADMIN_GROUP, OPERATOR_GROUP, RESPONSIBLE_GROUP, sync_access_groups
from appeals.tests.factories import AppealFactory, DepartmentFactory
from users.tests.factories import UserFactory

LIST_URL_NAME = "appeals:appeal_list"
LOGIN_URL = "/accounts/login/"


def _user_in_group(*group_names: str, password: str = "secret"):
    sync_access_groups()
    user = UserFactory(password=password)
    user.groups.add(*Group.objects.filter(name__in=group_names))
    return user


# --- appeal list: access control ---------------------------------------------


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_list_redirects_anonymous_to_login(client):
    response = client.get(reverse(LIST_URL_NAME))

    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_list_forbidden_without_view_permission(client):
    user = UserFactory(password="secret")
    client.login(email=user.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_list_scopes_to_operator_own_appeals(client):
    operator = _user_in_group(OPERATOR_GROUP)
    own = AppealFactory(created_by=operator, summary="моя заявка")
    other = AppealFactory(summary="чужая заявка")
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))
    appeals = list(response.context["appeals"])

    assert appeals == [own]
    assert "моя заявка" in response.content.decode()
    assert "чужая заявка" not in response.content.decode()
    assert other not in appeals


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_list_scopes_to_responsible_department(client):
    responsible = _user_in_group(RESPONSIBLE_GROUP)
    department = DepartmentFactory()
    department.members.add(responsible)
    in_scope = AppealFactory(department=department)
    out_of_scope = AppealFactory()
    client.login(email=responsible.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))
    appeals = list(response.context["appeals"])

    assert appeals == [in_scope]
    assert out_of_scope not in appeals


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_list_shows_all_appeals_to_admin(client):
    admin = _user_in_group(ADMIN_GROUP)
    appeals = [AppealFactory(), AppealFactory()]
    client.login(email=admin.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))

    assert set(response.context["appeals"]) == set(appeals)


# --- appeal list: rendering ---------------------------------------------------


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_list_shows_empty_state(client):
    operator = _user_in_group(OPERATOR_GROUP)
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))

    assert response.status_code == 200
    assert "Обращений пока нет." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_list_marks_overdue_appeal(client):
    operator = _user_in_group(OPERATOR_GROUP)
    AppealFactory(
        created_by=operator,
        status=Appeal.Status.NEW,
        due_at=timezone.now() - timedelta(days=1),
    )
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))

    assert "Просрочено" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_list_is_paginated(client):
    operator = _user_in_group(OPERATOR_GROUP)
    AppealFactory.create_batch(25, created_by=operator)
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(LIST_URL_NAME))

    assert response.context["is_paginated"] is True
    assert len(response.context["appeals"]) == 20
