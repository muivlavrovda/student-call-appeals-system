import pytest
from django.contrib.auth.models import Group, Permission

from appeals.models import Appeal
from appeals.roles import (
    ADMIN_GROUP,
    OPERATOR_GROUP,
    OPERATOR_PERMISSIONS,
    RESPONSIBLE_GROUP,
    RESPONSIBLE_PERMISSIONS,
    sync_access_groups,
)


@pytest.mark.unit
def test_appeal_declares_workflow_permissions():
    assert set(Appeal._meta.permissions) == {
        ("start_appeal_processing", "Can start appeal processing"),
        ("comment_appeal", "Can comment appeal"),
        ("close_appeal", "Can close appeal"),
        ("transfer_appeal", "Can transfer appeal"),
    }


@pytest.mark.django_db
@pytest.mark.integration
def test_sync_access_groups_creates_groups_and_assigns_permissions():
    Group.objects.filter(
        name__in=[
            ADMIN_GROUP,
            OPERATOR_GROUP,
            RESPONSIBLE_GROUP,
        ]
    ).delete()

    sync_access_groups()

    admin_group = Group.objects.get(name=ADMIN_GROUP)
    operator_group = Group.objects.get(name=OPERATOR_GROUP)
    responsible_group = Group.objects.get(name=RESPONSIBLE_GROUP)

    assert _permission_keys(operator_group) == set(OPERATOR_PERMISSIONS)
    assert _permission_keys(responsible_group) == set(RESPONSIBLE_PERMISSIONS)
    assert set(admin_group.permissions.values_list("pk", flat=True)) == set(
        Permission.objects.values_list("pk", flat=True)
    )


def _permission_keys(group: Group) -> set[str]:
    return {
        f"{app_label}.{codename}"
        for app_label, codename in group.permissions.values_list(
            "content_type__app_label",
            "codename",
        )
    }
