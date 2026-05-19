import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group
from django.test import RequestFactory
from django.utils import timezone

from appeals.admin import (
    AppealAdmin,
    AppealCommentAdmin,
    AppealCommentInline,
    AppealHistoryEventAdmin,
    AppealHistoryEventInline,
)
from appeals.models import Appeal, AppealComment, AppealHistoryEvent
from appeals.roles import ADMIN_GROUP, OPERATOR_GROUP, RESPONSIBLE_GROUP, sync_access_groups
from appeals.tests.factories import AppealFactory, DepartmentFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_admin_queryset_is_scoped_for_operator():
    operator = _staff_user_in_group(OPERATOR_GROUP)
    own_appeal = AppealFactory(created_by=operator)
    other_appeal = AppealFactory()
    model_admin = _appeal_admin()

    queryset = model_admin.get_queryset(_request_for(operator))

    assert list(queryset) == [own_appeal]
    assert model_admin.has_view_permission(_request_for(operator), own_appeal)
    assert not model_admin.has_view_permission(_request_for(operator), other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_admin_queryset_is_scoped_for_responsible_user():
    responsible = _staff_user_in_group(RESPONSIBLE_GROUP)
    department = DepartmentFactory()
    department.members.add(responsible)
    department_appeal = AppealFactory(department=department)
    other_appeal = AppealFactory()
    model_admin = _appeal_admin()

    queryset = model_admin.get_queryset(_request_for(responsible))

    assert list(queryset) == [department_appeal]
    assert model_admin.has_view_permission(_request_for(responsible), department_appeal)
    assert not model_admin.has_view_permission(_request_for(responsible), other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_admin_allows_admin_group_to_change_but_not_delete():
    admin_user = _staff_user_in_group(ADMIN_GROUP)
    appeal = AppealFactory()
    model_admin = _appeal_admin()
    request = _request_for(admin_user)

    assert model_admin.has_change_permission(request, appeal)
    assert model_admin.has_change_permission(request)
    assert model_admin.has_view_permission(request)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_delete_permission(request, appeal)


@pytest.mark.unit
def test_appeal_admin_workflow_fields_are_readonly():
    readonly_fields = set(AppealAdmin.readonly_fields)

    assert {
        "status",
        "created_by",
        "accepted_by",
        "accepted_at",
        "closed_at",
        "created_at",
        "updated_at",
    } <= readonly_fields


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_admin_overdue_indicator():
    model_admin = _appeal_admin()
    overdue_appeal = AppealFactory(
        status=Appeal.Status.NEW,
        due_at=timezone.now() - timezone.timedelta(days=1),
    )
    closed_appeal = AppealFactory(
        status=Appeal.Status.CLOSED,
        due_at=timezone.now() - timezone.timedelta(days=1),
    )

    assert model_admin.is_overdue(overdue_appeal)
    assert not model_admin.is_overdue(closed_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_appeal_comment_and_history_inlines_are_readonly_but_visible_with_appeal_access():
    operator = _staff_user_in_group(OPERATOR_GROUP)
    appeal = AppealFactory(created_by=operator)
    request = _request_for(operator)

    comment_inline = AppealCommentInline(Appeal, AdminSite())
    history_inline = AppealHistoryEventInline(Appeal, AdminSite())

    assert not comment_inline.has_add_permission(request, appeal)
    assert not comment_inline.has_change_permission(request, appeal)
    assert comment_inline.has_view_permission(request, appeal)
    assert set(comment_inline.readonly_fields) == {
        "author",
        "text",
        "created_at",
    }

    assert not history_inline.has_add_permission(request, appeal)
    assert not history_inline.has_change_permission(request, appeal)
    assert history_inline.has_view_permission(request, appeal)
    assert set(history_inline.readonly_fields) == {
        "actor",
        "event_type",
        "message",
        "created_at",
    }


@pytest.mark.unit
def test_comment_and_history_admin_are_readonly():
    comment_admin = AppealCommentAdmin(AppealComment, AdminSite())
    history_admin = AppealHistoryEventAdmin(AppealHistoryEvent, AdminSite())

    assert not comment_admin.has_add_permission(None)
    assert not comment_admin.has_change_permission(None)
    assert not comment_admin.has_delete_permission(None)
    assert set(comment_admin.readonly_fields) == {
        "appeal",
        "author",
        "text",
        "created_at",
    }

    assert not history_admin.has_add_permission(None)
    assert not history_admin.has_change_permission(None)
    assert not history_admin.has_delete_permission(None)
    assert set(history_admin.readonly_fields) == {
        "appeal",
        "actor",
        "event_type",
        "message",
        "created_at",
    }


def _appeal_admin() -> AppealAdmin:
    return AppealAdmin(Appeal, AdminSite())


def _request_for(user):
    request = RequestFactory().get("/")
    request.user = user
    return request


def _staff_user_in_group(group_name: str):
    sync_access_groups()
    user = UserFactory(is_staff=True)
    user.groups.add(Group.objects.get(name=group_name))
    return user
