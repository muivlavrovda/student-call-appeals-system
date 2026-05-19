from django.contrib.auth.models import Group, Permission
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate

from appeals.permissions import OPERATOR_PERMISSIONS, RESPONSIBLE_PERMISSIONS

ADMIN_GROUP = "Admin"
OPERATOR_GROUP = "Operator"
RESPONSIBLE_GROUP = "Responsible"


def register_role_sync() -> None:
    post_migrate.connect(
        _sync_access_groups_after_migrate,
        dispatch_uid="appeals.sync_access_groups",
    )


def _sync_access_groups_after_migrate(
    *,
    using: str,
    **kwargs,
) -> None:
    sync_access_groups(using=using)


def sync_access_groups(using: str = DEFAULT_DB_ALIAS) -> None:
    admin_group = _get_group(ADMIN_GROUP, using=using)
    operator_group = _get_group(OPERATOR_GROUP, using=using)
    responsible_group = _get_group(RESPONSIBLE_GROUP, using=using)

    admin_group.permissions.set(Permission.objects.using(using).all())
    operator_group.permissions.set(_get_permissions(OPERATOR_PERMISSIONS, using=using))
    responsible_group.permissions.set(_get_permissions(RESPONSIBLE_PERMISSIONS, using=using))


def _get_group(
    name: str,
    *,
    using: str,
) -> Group:
    group, _created = Group.objects.db_manager(using).get_or_create(name=name)
    return group


def _get_permissions(
    permission_keys: list[str],
    *,
    using: str,
) -> list[Permission]:
    keys_by_app = {}
    for permission_key in permission_keys:
        app_label, codename = permission_key.split(".", 1)
        keys_by_app.setdefault(app_label, set()).add(codename)

    permissions = []
    for app_label, codenames in keys_by_app.items():
        permissions.extend(
            Permission.objects.using(using).filter(
                content_type__app_label=app_label,
                codename__in=codenames,
            )
        )

    return permissions
