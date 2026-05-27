from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from appeals.models import Appeal, AppealComment, AppealHistoryEvent
from appeals.roles import ADMIN_GROUP, OPERATOR_GROUP, RESPONSIBLE_GROUP, sync_access_groups
from appeals.tests.factories import (
    AppealCategoryFactory,
    AppealCommentFactory,
    AppealFactory,
    AppealHistoryEventFactory,
    DepartmentFactory,
)
from users.tests.factories import UserFactory

LIST_URL_NAME = "appeals:appeal_list"
CREATE_URL_NAME = "appeals:appeal_create"
DETAIL_URL_NAME = "appeals:appeal_detail"
COMMENT_URL_NAME = "appeals:appeal_comment_create"
LOGIN_URL = "/accounts/login/"


def _valid_appeal_payload(category):
    return {
        "student_full_name": "Иванов Иван Иванович",
        "student_phone": "+7 (900) 123-45-67",
        "summary": "Вопрос по справке",
        "category": category.pk,
        "department": "",
        "description": "Студент просит справку об обучении.",
    }


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


# --- appeal create: access control -------------------------------------------


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_create_redirects_anonymous_to_login(client):
    response = client.get(reverse(CREATE_URL_NAME))

    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_create_forbidden_without_add_permission(client):
    # Responsible employees can view appeals but not register new ones.
    responsible = _user_in_group(RESPONSIBLE_GROUP)
    client.login(email=responsible.email, password="secret")

    response = client.get(reverse(CREATE_URL_NAME))

    assert response.status_code == 403


# --- appeal create: rendering & submission -----------------------------------


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_create_renders_form_for_operator(client):
    operator = _user_in_group(OPERATOR_GROUP)
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(CREATE_URL_NAME))

    assert response.status_code == 200
    assert "Новое обращение" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_create_only_lists_active_categories(client):
    operator = _user_in_group(OPERATOR_GROUP)
    active = AppealCategoryFactory()
    inactive = AppealCategoryFactory(is_active=False)
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(CREATE_URL_NAME))
    categories = list(response.context["form"].fields["category"].queryset)

    assert active in categories
    assert inactive not in categories


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_create_persists_appeal_and_redirects_to_detail(client):
    operator = _user_in_group(OPERATOR_GROUP)
    category = AppealCategoryFactory(default_processing_days=5)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(CREATE_URL_NAME),
        data=_valid_appeal_payload(category),
    )

    appeal = Appeal.objects.get()
    assert response.status_code == 302
    assert response["Location"] == reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk})
    assert appeal.created_by == operator
    assert appeal.department == category.department
    assert appeal.student_phone == "79001234567"
    assert appeal.status == Appeal.Status.NEW


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_create_writes_history_event(client):
    operator = _user_in_group(OPERATOR_GROUP)
    category = AppealCategoryFactory()
    client.login(email=operator.email, password="secret")

    client.post(reverse(CREATE_URL_NAME), data=_valid_appeal_payload(category))

    appeal = Appeal.objects.get()
    event = appeal.history_events.get()
    assert event.event_type == AppealHistoryEvent.EventType.CREATED
    assert event.actor == operator


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_create_shows_success_message(client):
    operator = _user_in_group(OPERATOR_GROUP)
    category = AppealCategoryFactory()
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(CREATE_URL_NAME),
        data=_valid_appeal_payload(category),
        follow=True,
    )

    assert "Обращение зарегистрировано." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_create_uses_selected_department(client):
    operator = _user_in_group(OPERATOR_GROUP)
    category = AppealCategoryFactory()
    other_department = DepartmentFactory()
    payload = _valid_appeal_payload(category)
    payload["department"] = other_department.pk
    client.login(email=operator.email, password="secret")

    client.post(reverse(CREATE_URL_NAME), data=payload)

    appeal = Appeal.objects.get()
    assert appeal.department == other_department


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_create_rejects_missing_fields(client):
    operator = _user_in_group(OPERATOR_GROUP)
    client.login(email=operator.email, password="secret")

    response = client.post(reverse(CREATE_URL_NAME), data={})

    assert response.status_code == 200
    assert Appeal.objects.count() == 0
    assert "Укажите ФИО студента." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_create_rejects_inactive_category_choice(client):
    # A crafted POST referencing an inactive category is not an allowed choice.
    operator = _user_in_group(OPERATOR_GROUP)
    inactive = AppealCategoryFactory(is_active=False)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(CREATE_URL_NAME),
        data=_valid_appeal_payload(inactive),
    )

    assert response.status_code == 200
    assert Appeal.objects.count() == 0
    assert "Выберите категорию из списка." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_create_surfaces_service_validation_error(client):
    # The form accepts an active category, but its department was deactivated
    # after render — the service rejects it and the error reaches the form.
    operator = _user_in_group(OPERATOR_GROUP)
    department = DepartmentFactory(is_active=False)
    category = AppealCategoryFactory(department=department)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(CREATE_URL_NAME),
        data=_valid_appeal_payload(category),
    )

    assert response.status_code == 200
    assert Appeal.objects.count() == 0
    assert "inactive" in response.content.decode().lower()


# --- appeal detail ------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_detail_redirects_anonymous_to_login(client):
    appeal = AppealFactory()
    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_detail_renders_for_owner(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator, summary="моя заявка")
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.status_code == 200
    assert "моя заявка" in response.content.decode()
    assert appeal.student_full_name in response.content.decode()


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_detail_hidden_appeal_returns_404(client):
    operator = _user_in_group(OPERATOR_GROUP)
    other = AppealFactory(summary="чужая заявка")
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": other.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_detail_forbidden_without_view_permission(client):
    appeal = AppealFactory()
    user = UserFactory(password="secret")
    client.login(email=user.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.security
def test_appeal_detail_denies_deactivated_user_with_live_session(client):
    # Deactivating a user invalidates their live session: the auth backend stops
    # resolving the session to a user, so the next request is anonymous and is
    # bounced to login instead of seeing the appeal.
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator, summary="секретная заявка")
    client.login(email=operator.email, password="secret")
    operator.is_active = False
    operator.save(update_fields=["is_active"])

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]
    assert "секретная заявка" not in response.content.decode()


# --- appeal detail: timeline & comments rendering ----------------------------


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_detail_shows_history_timeline(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    AppealHistoryEventFactory(
        appeal=appeal,
        actor=operator,
        event_type=AppealHistoryEvent.EventType.CREATED,
    )
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))
    content = response.content.decode()

    assert list(response.context["history_events"]) == list(appeal.history_events.all())
    assert "История" in content
    assert "timeline" in content


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_detail_lists_comments(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    AppealCommentFactory(appeal=appeal, author=operator, text="комментарий оператора")
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert "комментарий оператора" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_detail_shows_comment_form_for_commenter(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.context["can_comment"] is True
    assert "Добавить комментарий" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_appeal_detail_lets_responsible_comment_department_appeal(client):
    responsible = _user_in_group(RESPONSIBLE_GROUP)
    department = DepartmentFactory()
    department.members.add(responsible)
    appeal = AppealFactory(department=department)
    client.login(email=responsible.email, password="secret")

    response = client.get(reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.context["can_comment"] is True
    assert "Добавить комментарий" in response.content.decode()


# --- appeal comment create ---------------------------------------------------


@pytest.mark.django_db
@pytest.mark.security
def test_comment_create_redirects_anonymous_to_login(client):
    appeal = AppealFactory()
    response = client.post(reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}), data={"text": "x"})

    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
@pytest.mark.security
def test_comment_create_forbidden_without_comment_permission(client):
    appeal = AppealFactory()
    user = UserFactory(password="secret")
    client.login(email=user.email, password="secret")

    response = client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}),
        data={"text": "Комментарий"},
    )

    assert response.status_code == 403
    assert AppealComment.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_comment_create_returns_404_for_out_of_scope_appeal(client):
    # Operator has the comment permission globally but cannot see others'
    # appeals, so commenting one is a 404 (no existence leak), not a 403.
    operator = _user_in_group(OPERATOR_GROUP)
    other = AppealFactory()
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": other.pk}),
        data={"text": "Комментарий"},
    )

    assert response.status_code == 404
    assert AppealComment.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.functional
def test_comment_create_rejects_get(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    client.login(email=operator.email, password="secret")

    response = client.get(reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}))

    assert response.status_code == 405


@pytest.mark.django_db
@pytest.mark.integration
def test_comment_create_adds_comment_and_redirects(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}),
        data={"text": "Уточнил детали обращения"},
    )

    comment = AppealComment.objects.get()
    assert comment.appeal == appeal
    assert comment.author == operator
    assert comment.text == "Уточнил детали обращения"
    assert response.status_code == 302
    detail_url = reverse(DETAIL_URL_NAME, kwargs={"pk": appeal.pk})
    assert response["Location"] == f"{detail_url}#comments"


@pytest.mark.django_db
@pytest.mark.integration
def test_comment_create_writes_history_event(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    client.login(email=operator.email, password="secret")

    client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}),
        data={"text": "Комментарий"},
    )

    event = appeal.history_events.get()
    assert event.event_type == AppealHistoryEvent.EventType.COMMENT_ADDED
    assert event.actor == operator


@pytest.mark.django_db
@pytest.mark.functional
def test_comment_create_shows_success_message(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}),
        data={"text": "Комментарий"},
        follow=True,
    )

    assert "Комментарий добавлен." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_comment_create_rejects_empty_text(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}),
        data={"text": "   "},
        follow=True,
    )

    assert AppealComment.objects.count() == 0
    assert "Введите текст комментария." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.integration
def test_comment_create_rejects_closed_appeal(client):
    operator = _user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator, status=Appeal.Status.CLOSED)
    client.login(email=operator.email, password="secret")

    response = client.post(
        reverse(COMMENT_URL_NAME, kwargs={"pk": appeal.pk}),
        data={"text": "Комментарий к закрытой"},
        follow=True,
    )

    assert AppealComment.objects.count() == 0
    assert "Нельзя комментировать закрытое обращение." in response.content.decode()
