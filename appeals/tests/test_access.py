import pytest
from django.contrib.auth.models import Group, Permission

from appeals.access import (
    can_close_appeal,
    can_comment_appeal,
    can_create_appeal,
    can_start_appeal_processing,
    can_transfer_appeal,
    can_view_appeal,
    visible_appeals_for,
)
from appeals.roles import ADMIN_GROUP, OPERATOR_GROUP, RESPONSIBLE_GROUP, sync_access_groups
from appeals.tests.factories import AppealFactory, DepartmentFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_operator_sees_only_own_appeals():
    operator = _user_in_group(OPERATOR_GROUP)
    own_appeal = AppealFactory(created_by=operator)
    other_appeal = AppealFactory()

    assert list(visible_appeals_for(operator)) == [own_appeal]
    assert can_view_appeal(operator, own_appeal)
    assert not can_view_appeal(operator, other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_responsible_sees_department_appeals():
    responsible = _user_in_group(RESPONSIBLE_GROUP)
    department = DepartmentFactory()
    department.members.add(responsible)
    department_appeal = AppealFactory(department=department)
    other_appeal = AppealFactory()

    assert list(visible_appeals_for(responsible)) == [department_appeal]
    assert can_view_appeal(responsible, department_appeal)
    assert not can_view_appeal(responsible, other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_admin_group_has_full_appeal_access():
    admin = _user_in_group(ADMIN_GROUP)
    appeals = [
        AppealFactory(),
        AppealFactory(),
    ]

    assert set(visible_appeals_for(admin)) == set(appeals)
    assert all(can_view_appeal(admin, appeal) for appeal in appeals)
    assert all(can_transfer_appeal(admin, appeal) for appeal in appeals)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_operator_permissions_are_scoped_to_own_appeals():
    operator = _user_in_group(OPERATOR_GROUP)
    own_appeal = AppealFactory(created_by=operator)
    other_appeal = AppealFactory()

    assert can_create_appeal(operator)
    assert can_comment_appeal(operator, own_appeal)
    assert can_close_appeal(operator, own_appeal)
    assert not can_start_appeal_processing(operator, own_appeal)
    assert not can_transfer_appeal(operator, own_appeal)

    assert not can_comment_appeal(operator, other_appeal)
    assert not can_close_appeal(operator, other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_responsible_permissions_are_scoped_to_departments():
    responsible = _user_in_group(RESPONSIBLE_GROUP)
    department = DepartmentFactory()
    department.members.add(responsible)
    department_appeal = AppealFactory(department=department)
    other_appeal = AppealFactory()

    assert not can_create_appeal(responsible)
    assert can_start_appeal_processing(responsible, department_appeal)
    assert can_comment_appeal(responsible, department_appeal)
    assert can_close_appeal(responsible, department_appeal)
    assert can_transfer_appeal(responsible, department_appeal)

    assert not can_start_appeal_processing(responsible, other_appeal)
    assert not can_comment_appeal(responsible, other_appeal)
    assert not can_close_appeal(responsible, other_appeal)
    assert not can_transfer_appeal(responsible, other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_user_with_both_roles_gets_operator_and_department_scopes():
    user = _user_in_group(OPERATOR_GROUP, RESPONSIBLE_GROUP)
    department = DepartmentFactory()
    department.members.add(user)
    own_appeal = AppealFactory(created_by=user)
    department_appeal = AppealFactory(department=department)
    other_appeal = AppealFactory()

    assert set(visible_appeals_for(user)) == {
        own_appeal,
        department_appeal,
    }
    assert can_comment_appeal(user, own_appeal)
    assert can_start_appeal_processing(user, department_appeal)
    assert not can_view_appeal(user, other_appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_user_without_groups_has_no_appeal_access():
    user = UserFactory()
    appeal = AppealFactory()

    assert list(visible_appeals_for(user)) == []
    assert not can_create_appeal(user)
    assert not can_view_appeal(user, appeal)
    assert not can_start_appeal_processing(user, appeal)
    assert not can_comment_appeal(user, appeal)
    assert not can_close_appeal(user, appeal)
    assert not can_transfer_appeal(user, appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_transfer_permission_without_department_scope_does_not_allow_transfer():
    user = UserFactory()
    sync_access_groups()
    responsible_group = Group.objects.get(name=RESPONSIBLE_GROUP)
    transfer_permission = responsible_group.permissions.get(codename="transfer_appeal")
    user.user_permissions.add(transfer_permission)
    appeal = AppealFactory()

    assert not can_transfer_appeal(user, appeal)


@pytest.mark.django_db
@pytest.mark.security
@pytest.mark.integration
def test_view_permission_without_scope_does_not_expose_appeals():
    user = UserFactory()
    user.user_permissions.add(Permission.objects.get(codename="view_appeal"))
    appeal = AppealFactory()

    assert list(visible_appeals_for(user)) == []
    assert not can_view_appeal(user, appeal)


def _user_in_group(*group_names: str):
    sync_access_groups()
    user = UserFactory()
    user.groups.add(*Group.objects.filter(name__in=group_names))
    return user
