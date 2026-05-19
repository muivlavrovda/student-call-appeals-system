from django.db.models import Q, QuerySet

from appeals.models import Appeal
from appeals.permissions import (
    ADD_APPEAL_PERMISSION,
    CHANGE_APPEAL_PERMISSION,
    CLOSE_APPEAL_PERMISSION,
    COMMENT_APPEAL_PERMISSION,
    START_APPEAL_PROCESSING_PERMISSION,
    TRANSFER_APPEAL_PERMISSION,
    VIEW_APPEAL_PERMISSION,
)
from users.models import User


def visible_appeals_for(user: User) -> QuerySet[Appeal]:
    if not _can_use_app(user) or not user.has_perm(VIEW_APPEAL_PERMISSION):
        return Appeal.objects.none()

    if _has_full_appeal_access(user):
        return Appeal.objects.all()

    filters = Q()
    if user.has_perm(ADD_APPEAL_PERMISSION):
        filters |= Q(created_by=user)
    if _has_department_appeal_access(user):
        filters |= Q(department__members=user)

    if not filters:
        return Appeal.objects.none()

    return Appeal.objects.filter(filters).distinct()


def can_create_appeal(user: User) -> bool:
    return _can_use_app(user) and user.has_perm(ADD_APPEAL_PERMISSION)


def can_view_appeal(user: User, appeal: Appeal) -> bool:
    if not _can_use_app(user) or not user.has_perm(VIEW_APPEAL_PERMISSION):
        return False
    return visible_appeals_for(user).filter(pk=appeal.pk).exists()


def can_start_appeal_processing(user: User, appeal: Appeal) -> bool:
    return _can_act_on_department_appeal(
        user,
        appeal,
        permission=START_APPEAL_PROCESSING_PERMISSION,
    )


def can_comment_appeal(user: User, appeal: Appeal) -> bool:
    return _can_act_on_visible_appeal(
        user,
        appeal,
        permission=COMMENT_APPEAL_PERMISSION,
    )


def can_close_appeal(user: User, appeal: Appeal) -> bool:
    return _can_act_on_visible_appeal(
        user,
        appeal,
        permission=CLOSE_APPEAL_PERMISSION,
    )


def can_transfer_appeal(user: User, appeal: Appeal) -> bool:
    return _can_act_on_department_appeal(
        user,
        appeal,
        permission=TRANSFER_APPEAL_PERMISSION,
    )


def _can_act_on_visible_appeal(
    user: User,
    appeal: Appeal,
    *,
    permission: str,
) -> bool:
    return (
        _can_use_app(user)
        and user.has_perm(permission)
        and visible_appeals_for(user).filter(pk=appeal.pk).exists()
    )


def _can_act_on_department_appeal(
    user: User,
    appeal: Appeal,
    *,
    permission: str,
) -> bool:
    return (
        _can_use_app(user)
        and user.has_perm(permission)
        and _department_appeals_for(user).filter(pk=appeal.pk).exists()
    )


def _can_use_app(user: User) -> bool:
    return user.is_authenticated and user.is_active


def _has_full_appeal_access(user: User) -> bool:
    return user.is_superuser or user.has_perm(CHANGE_APPEAL_PERMISSION)


def _has_department_appeal_access(user: User) -> bool:
    return user.has_perm(START_APPEAL_PROCESSING_PERMISSION) or user.has_perm(
        TRANSFER_APPEAL_PERMISSION
    )


def _department_appeals_for(user: User) -> QuerySet[Appeal]:
    if _has_full_appeal_access(user):
        return Appeal.objects.all()
    return Appeal.objects.filter(department__members=user).distinct()
