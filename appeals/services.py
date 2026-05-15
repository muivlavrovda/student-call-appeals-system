from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from appeals.models import (
    Appeal,
    AppealCategory,
    AppealComment,
    AppealHistoryEvent,
    Department,
    normalize_spaces,
)
from users.models import User


def create_appeal(
    *,
    student_full_name: str,
    student_phone: str,
    summary: str,
    description: str,
    category: AppealCategory,
    created_by: User,
    department: Department | None = None,
) -> Appeal:
    """Вызывается после подтверждения формы создания заявки оператором.

    Категория и отдел уже должны быть выбраны: вручную оператором или после
    подсказки отдельного сервиса классификации.
    """
    created_at = timezone.now()
    selected_department = department or category.department

    errors = {}
    if not category.is_active:
        errors["category"] = _("Selected appeal category is inactive.")
    if not selected_department.is_active:
        errors["department"] = _("Selected department is inactive.")
    if errors:
        raise ValidationError(errors)

    appeal = Appeal(
        student_full_name=student_full_name,
        student_phone=student_phone,
        summary=summary,
        description=description,
        category=category,
        department=selected_department,
        due_at=created_at + timedelta(days=category.default_processing_days),
        created_by=created_by,
        created_at=created_at,
    )
    appeal.full_clean()

    with transaction.atomic():
        appeal.save()
        _create_history_event(
            appeal=appeal,
            actor=created_by,
            event_type=AppealHistoryEvent.EventType.CREATED,
            message=_("Appeal created."),
        )

    return appeal


def accept_appeal(
    *,
    appeal: Appeal,
    accepted_by: User,
) -> Appeal:
    """Вызывается, когда сотрудник принимает новую заявку в работу.

    Проверка прав доступа выполняется до вызова функции, а здесь фиксируется
    переход состояния и запись в истории заявки.
    """
    accepted_at = timezone.now()

    with transaction.atomic():
        locked_appeal = Appeal.objects.select_for_update().get(pk=appeal.pk)
        if locked_appeal.status != Appeal.Status.NEW:
            raise ValidationError(
                {
                    "status": _("Only new appeals can be accepted."),
                }
            )

        locked_appeal.status = Appeal.Status.IN_PROGRESS
        locked_appeal.accepted_by = accepted_by
        locked_appeal.accepted_at = accepted_at
        locked_appeal.full_clean()
        locked_appeal.save(
            update_fields=[
                "status",
                "accepted_by",
                "accepted_at",
                "updated_at",
            ],
        )
        _create_history_event(
            appeal=locked_appeal,
            actor=accepted_by,
            event_type=AppealHistoryEvent.EventType.ACCEPTED,
            message=_("Appeal accepted."),
        )

    return locked_appeal


def add_appeal_comment(
    *,
    appeal: Appeal,
    author: User,
    text: str,
) -> AppealComment:
    """Вызывается, когда сотрудник добавляет комментарий к открытой заявке.

    Проверка прав доступа выполняется до вызова функции, а здесь создается
    сам комментарий и запись в истории заявки.
    """
    with transaction.atomic():
        locked_appeal = Appeal.objects.select_for_update().get(pk=appeal.pk)
        if locked_appeal.status == Appeal.Status.CLOSED:
            raise ValidationError(
                {
                    "status": _("Closed appeals cannot be commented."),
                }
            )

        comment = AppealComment(
            appeal=locked_appeal,
            author=author,
            text=text,
        )
        comment.full_clean()
        comment.save()
        _create_history_event(
            appeal=locked_appeal,
            actor=author,
            event_type=AppealHistoryEvent.EventType.COMMENT_ADDED,
            message=_("Comment added."),
        )

    return comment


def close_appeal(
    *,
    appeal: Appeal,
    closed_by: User,
    result: str,
) -> Appeal:
    """Вызывается, когда оператор или сотрудник закрывает обработанную заявку.

    Проверка прав доступа выполняется до вызова функции, а здесь сохраняется
    результат обработки, финальный статус и события истории.
    """
    closed_at = timezone.now()
    normalized_result = normalize_spaces(result)
    if not normalized_result:
        raise ValidationError(
            {
                "result": _("Appeal result is required to close appeal."),
            }
        )

    with transaction.atomic():
        locked_appeal = Appeal.objects.select_for_update().get(pk=appeal.pk)
        if locked_appeal.status == Appeal.Status.CLOSED:
            raise ValidationError(
                {
                    "status": _("Appeal is already closed."),
                }
            )

        locked_appeal.result = normalized_result
        locked_appeal.status = Appeal.Status.CLOSED
        locked_appeal.closed_at = closed_at
        locked_appeal.full_clean()
        locked_appeal.save(
            update_fields=[
                "result",
                "status",
                "closed_at",
                "updated_at",
            ],
        )
        _create_history_event(
            appeal=locked_appeal,
            actor=closed_by,
            event_type=AppealHistoryEvent.EventType.CLOSED,
            message=_("Appeal closed."),
        )

    return locked_appeal


def _create_history_event(
    *,
    appeal: Appeal,
    actor: User,
    event_type: AppealHistoryEvent.EventType,
    message: str,
) -> AppealHistoryEvent:
    return AppealHistoryEvent.objects.create(
        appeal=appeal,
        actor=actor,
        event_type=event_type,
        message=message,
    )
