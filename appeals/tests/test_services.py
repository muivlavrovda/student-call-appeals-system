from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from appeals.models import Appeal, AppealComment, AppealHistoryEvent
from appeals.services import (
    add_appeal_comment,
    close_appeal,
    create_appeal,
    start_appeal_processing,
    transfer_appeal,
)
from appeals.tests.factories import AppealCategoryFactory, AppealFactory, DepartmentFactory
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


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_start_appeal_processing_sets_worker_started_at_status_and_history():
    accepted_at = datetime(2026, 1, 10, 10, 30, tzinfo=UTC)
    appeal = AppealFactory()
    worker = UserFactory()

    with patch("appeals.services.timezone.now", return_value=accepted_at):
        accepted_appeal = start_appeal_processing(
            appeal=appeal,
            started_by=worker,
        )

    assert accepted_appeal.status == Appeal.Status.IN_PROGRESS
    assert accepted_appeal.accepted_by == worker
    assert accepted_appeal.accepted_at == accepted_at

    appeal.refresh_from_db()
    assert appeal.status == Appeal.Status.IN_PROGRESS
    assert appeal.accepted_by == worker
    assert appeal.accepted_at == accepted_at

    event = AppealHistoryEvent.objects.get(appeal=appeal)
    assert event.actor == worker
    assert event.event_type == AppealHistoryEvent.EventType.ACCEPTED
    assert event.message == "Appeal processing started."


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.parametrize(
    "status",
    [
        Appeal.Status.IN_PROGRESS,
        Appeal.Status.CLOSED,
    ],
)
def test_start_appeal_processing_rejects_appeals_that_are_not_new(status):
    appeal = AppealFactory(status=status)

    with pytest.raises(ValidationError) as error:
        start_appeal_processing(
            appeal=appeal,
            started_by=UserFactory(),
        )

    assert "status" in error.value.message_dict
    appeal.refresh_from_db()
    assert appeal.status == status
    assert appeal.accepted_by is None
    assert appeal.accepted_at is None
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_add_appeal_comment_creates_comment_and_history():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    author = UserFactory()

    comment = add_appeal_comment(
        appeal=appeal,
        author=author,
        text="Проверили документы",
    )

    assert comment.appeal == appeal
    assert comment.author == author
    assert comment.text == "Проверили документы"

    event = AppealHistoryEvent.objects.get(appeal=appeal)
    assert event.actor == author
    assert event.event_type == AppealHistoryEvent.EventType.COMMENT_ADDED
    assert event.message == "Comment added."


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_add_appeal_comment_allows_new_appeals():
    appeal = AppealFactory(status=Appeal.Status.NEW)

    comment = add_appeal_comment(
        appeal=appeal,
        author=UserFactory(),
        text="Оператор уточнил детали",
    )

    assert comment.appeal == appeal


@pytest.mark.django_db
@pytest.mark.integration
def test_add_appeal_comment_rejects_closed_appeals():
    appeal = AppealFactory(status=Appeal.Status.CLOSED)

    with pytest.raises(ValidationError) as error:
        add_appeal_comment(
            appeal=appeal,
            author=UserFactory(),
            text="Новый комментарий",
        )

    assert "status" in error.value.message_dict
    assert AppealComment.objects.count() == 0
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_add_appeal_comment_runs_model_validation():
    with pytest.raises(ValidationError) as error:
        add_appeal_comment(
            appeal=AppealFactory(),
            author=UserFactory(),
            text="",
        )

    assert "text" in error.value.message_dict
    assert AppealComment.objects.count() == 0
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_close_appeal_sets_result_closed_at_status_and_history():
    closed_at = datetime(2026, 1, 10, 11, 0, tzinfo=UTC)
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    worker = UserFactory()

    with patch("appeals.services.timezone.now", return_value=closed_at):
        closed_appeal = close_appeal(
            appeal=appeal,
            closed_by=worker,
            result="  справка   подготовлена  ",
        )

    assert closed_appeal.status == Appeal.Status.CLOSED
    assert closed_appeal.result == "справка подготовлена"
    assert closed_appeal.closed_at == closed_at

    appeal.refresh_from_db()
    assert appeal.status == Appeal.Status.CLOSED
    assert appeal.result == "справка подготовлена"
    assert appeal.closed_at == closed_at

    event = AppealHistoryEvent.objects.get(appeal=appeal)
    assert event.actor == worker
    assert event.event_type == AppealHistoryEvent.EventType.CLOSED
    assert event.message == "Appeal closed."


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_close_appeal_allows_new_appeals():
    appeal = AppealFactory(status=Appeal.Status.NEW)

    closed_appeal = close_appeal(
        appeal=appeal,
        closed_by=UserFactory(),
        result="Решено во время звонка",
    )

    assert closed_appeal.status == Appeal.Status.CLOSED


@pytest.mark.django_db
@pytest.mark.integration
def test_close_appeal_rejects_blank_result():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)

    with pytest.raises(ValidationError) as error:
        close_appeal(
            appeal=appeal,
            closed_by=UserFactory(),
            result="   ",
        )

    assert "result" in error.value.message_dict
    appeal.refresh_from_db()
    assert appeal.status == Appeal.Status.IN_PROGRESS
    assert appeal.result == ""
    assert appeal.closed_at is None
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_close_appeal_rejects_closed_appeals():
    appeal = AppealFactory(
        status=Appeal.Status.CLOSED,
        result="Уже закрыто",
        closed_at=datetime(2026, 1, 9, 11, 0, tzinfo=UTC),
    )

    with pytest.raises(ValidationError) as error:
        close_appeal(
            appeal=appeal,
            closed_by=UserFactory(),
            result="Новый результат",
        )

    assert "status" in error.value.message_dict
    appeal.refresh_from_db()
    assert appeal.result == "Уже закрыто"
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_transfer_appeal_changes_department_and_history():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    original_category = appeal.category
    new_department = DepartmentFactory()
    worker = UserFactory()

    transferred_appeal = transfer_appeal(
        appeal=appeal,
        transferred_by=worker,
        department=new_department,
    )

    assert transferred_appeal.category == original_category
    assert transferred_appeal.department == new_department

    appeal.refresh_from_db()
    assert appeal.category == original_category
    assert appeal.department == new_department

    event = AppealHistoryEvent.objects.get(appeal=appeal)
    assert event.actor == worker
    assert event.event_type == AppealHistoryEvent.EventType.DEPARTMENT_CHANGED
    assert event.message == "Appeal department changed."


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_transfer_appeal_changes_category_and_uses_its_department():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    new_department = DepartmentFactory()
    new_category = AppealCategoryFactory(department=new_department)
    worker = UserFactory()

    transferred_appeal = transfer_appeal(
        appeal=appeal,
        transferred_by=worker,
        category=new_category,
    )

    assert transferred_appeal.category == new_category
    assert transferred_appeal.department == new_department

    appeal.refresh_from_db()
    assert appeal.category == new_category
    assert appeal.department == new_department

    events = list(AppealHistoryEvent.objects.filter(appeal=appeal).order_by("pk"))
    assert [event.actor for event in events] == [worker, worker]
    assert [event.event_type for event in events] == [
        AppealHistoryEvent.EventType.CATEGORY_CHANGED,
        AppealHistoryEvent.EventType.DEPARTMENT_CHANGED,
    ]
    assert [event.message for event in events] == [
        "Appeal category changed.",
        "Appeal department changed.",
    ]


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_transfer_appeal_can_change_category_without_department_change():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    new_category = AppealCategoryFactory(department=appeal.department)
    worker = UserFactory()

    transferred_appeal = transfer_appeal(
        appeal=appeal,
        transferred_by=worker,
        category=new_category,
    )

    assert transferred_appeal.category == new_category
    assert transferred_appeal.department == appeal.department

    event = AppealHistoryEvent.objects.get(appeal=appeal)
    assert event.actor == worker
    assert event.event_type == AppealHistoryEvent.EventType.CATEGORY_CHANGED
    assert event.message == "Appeal category changed."


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_transfer_appeal_allows_new_appeals():
    appeal = AppealFactory(status=Appeal.Status.NEW)
    new_department = DepartmentFactory()

    transferred_appeal = transfer_appeal(
        appeal=appeal,
        transferred_by=UserFactory(),
        department=new_department,
    )

    assert transferred_appeal.department == new_department


@pytest.mark.django_db
@pytest.mark.integration
def test_transfer_appeal_rejects_empty_route_change():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)

    with pytest.raises(ValidationError) as error:
        transfer_appeal(
            appeal=appeal,
            transferred_by=UserFactory(),
        )

    assert "__all__" in error.value.message_dict
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_transfer_appeal_rejects_closed_appeals():
    appeal = AppealFactory(status=Appeal.Status.CLOSED)
    original_department = appeal.department

    with pytest.raises(ValidationError) as error:
        transfer_appeal(
            appeal=appeal,
            transferred_by=UserFactory(),
            department=DepartmentFactory(),
        )

    assert "status" in error.value.message_dict
    appeal.refresh_from_db()
    assert appeal.department == original_department
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_transfer_appeal_rejects_inactive_category():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    original_category = appeal.category
    original_department = appeal.department

    with pytest.raises(ValidationError) as error:
        transfer_appeal(
            appeal=appeal,
            transferred_by=UserFactory(),
            category=AppealCategoryFactory(is_active=False),
        )

    assert "category" in error.value.message_dict
    appeal.refresh_from_db()
    assert appeal.category == original_category
    assert appeal.department == original_department
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_transfer_appeal_rejects_inactive_department():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)
    original_department = appeal.department

    with pytest.raises(ValidationError) as error:
        transfer_appeal(
            appeal=appeal,
            transferred_by=UserFactory(),
            department=DepartmentFactory(is_active=False),
        )

    assert "department" in error.value.message_dict
    appeal.refresh_from_db()
    assert appeal.department == original_department
    assert AppealHistoryEvent.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_transfer_appeal_rejects_unchanged_route():
    appeal = AppealFactory(status=Appeal.Status.IN_PROGRESS)

    with pytest.raises(ValidationError) as error:
        transfer_appeal(
            appeal=appeal,
            transferred_by=UserFactory(),
            department=appeal.department,
        )

    assert "__all__" in error.value.message_dict
    assert AppealHistoryEvent.objects.count() == 0
