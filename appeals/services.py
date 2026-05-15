from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from appeals.models import Appeal, AppealCategory, AppealHistoryEvent, Department
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

    _validate_appeal_catalogs(
        category=category,
        department=selected_department,
    )

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
        AppealHistoryEvent.objects.create(
            appeal=appeal,
            actor=created_by,
            event_type=AppealHistoryEvent.EventType.CREATED,
            message=_("Appeal created."),
        )

    return appeal


def _validate_appeal_catalogs(
    *,
    category: AppealCategory,
    department: Department,
) -> None:
    errors = {}

    if not category.is_active:
        errors["category"] = _("Selected appeal category is inactive.")

    if not department.is_active:
        errors["department"] = _("Selected department is inactive.")

    if errors:
        raise ValidationError(errors)
