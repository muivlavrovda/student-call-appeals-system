from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from appeals.models import Appeal, AppealHistoryEvent
from appeals.services import create_appeal
from appeals.tests.factories import AppealCategoryFactory, DepartmentFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_create_appeal_uses_category_department_due_date_and_history():
    created_at = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    operator = UserFactory()
    category = AppealCategoryFactory(default_processing_days=5)

    with patch("appeals.services.timezone.now", return_value=created_at):
        appeal = create_appeal(
            student_full_name="  иванов   иван  ",
            student_phone="+7 (906) 123-45-67",
            summary="  нужна   справка  ",
            description="Подробности обращения",
            category=category,
            created_by=operator,
        )

    assert appeal.status == Appeal.Status.NEW
    assert appeal.student_full_name == "иванов иван"
    assert appeal.student_phone == "79061234567"
    assert appeal.summary == "нужна справка"
    assert appeal.category == category
    assert appeal.department == category.department
    assert appeal.created_by == operator
    assert appeal.created_at == created_at
    assert appeal.due_at == created_at + timedelta(days=5)

    event = AppealHistoryEvent.objects.get(appeal=appeal)
    assert event.actor == operator
    assert event.event_type == AppealHistoryEvent.EventType.CREATED
    assert event.message == "Appeal created."


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_create_appeal_allows_department_override():
    category = AppealCategoryFactory()
    selected_department = DepartmentFactory()

    appeal = create_appeal(
        student_full_name="Иванов Иван",
        student_phone="+7 (906) 123-45-67",
        summary="Нужна справка",
        description="Подробности обращения",
        category=category,
        created_by=UserFactory(),
        department=selected_department,
    )

    assert appeal.department == selected_department


@pytest.mark.django_db
@pytest.mark.integration
def test_create_appeal_rejects_inactive_category():
    category = AppealCategoryFactory(is_active=False)

    with pytest.raises(ValidationError) as error:
        create_appeal(
            student_full_name="Иванов Иван",
            student_phone="+7 (906) 123-45-67",
            summary="Нужна справка",
            description="Подробности обращения",
            category=category,
            created_by=UserFactory(),
        )

    assert "category" in error.value.message_dict
    assert Appeal.objects.count() == 0
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_create_appeal_rejects_inactive_department():
    category = AppealCategoryFactory()
    selected_department = DepartmentFactory(is_active=False)

    with pytest.raises(ValidationError) as error:
        create_appeal(
            student_full_name="Иванов Иван",
            student_phone="+7 (906) 123-45-67",
            summary="Нужна справка",
            description="Подробности обращения",
            category=category,
            created_by=UserFactory(),
            department=selected_department,
        )

    assert "department" in error.value.message_dict
    assert Appeal.objects.count() == 0
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_create_appeal_runs_model_validation():
    with pytest.raises(ValidationError) as error:
        create_appeal(
            student_full_name="Иванов Иван",
            student_phone="123",
            summary="Нужна справка",
            description="Подробности обращения",
            category=AppealCategoryFactory(),
            created_by=UserFactory(),
        )

    assert "student_phone" in error.value.message_dict
    assert Appeal.objects.count() == 0
    assert AppealHistoryEvent.objects.count() == 0
