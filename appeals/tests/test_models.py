from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.utils.translation import gettext as _

from appeals.models import (
    AILog,
    Appeal,
    AppealCategory,
    AppealComment,
    AppealHistoryEvent,
    Department,
)
from appeals.tests.factories import (
    AppealCategoryFactory,
    AppealCommentFactory,
    AppealFactory,
    AppealHistoryEventFactory,
    DepartmentFactory,
)


@pytest.mark.django_db
@pytest.mark.integration
def test_department_normalizes_name_on_save():
    department = DepartmentFactory(name="  учебный   отдел  ")

    assert department.name == "учебный отдел"
    assert department.name_key == "учебный отдел"
    assert str(department) == "учебный отдел"


@pytest.mark.django_db
@pytest.mark.integration
def test_department_full_clean_catches_case_insensitive_duplicate_name():
    DepartmentFactory(name="Аптечка")

    duplicate = DepartmentFactory.build(name="аптечка")

    with pytest.raises(ValidationError):
        duplicate.full_clean()


@pytest.mark.django_db
@pytest.mark.integration
def test_department_name_key_is_enforced_by_database():
    DepartmentFactory(name="Аптечка")

    with pytest.raises(IntegrityError):
        DepartmentFactory(name="аптечка")


@pytest.mark.unit
def test_department_ordering_uses_name_then_latest_pk():
    assert Department._meta.ordering == ["name", "-pk"]


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_category_normalizes_name_on_save():
    category = AppealCategoryFactory(name="  оплата   обучения  ")

    assert category.name == "оплата обучения"
    assert category.name_key == "оплата обучения"
    assert str(category) == "оплата обучения"


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_category_full_clean_catches_case_insensitive_duplicate_name():
    AppealCategoryFactory(name="Оплата")

    duplicate = AppealCategoryFactory.build(name="оплата")

    with pytest.raises(ValidationError):
        duplicate.full_clean()


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_category_name_key_is_enforced_by_database():
    AppealCategoryFactory(name="Оплата")

    with pytest.raises(IntegrityError):
        AppealCategoryFactory(name="оплата")


@pytest.mark.unit
def test_appeal_category_ordering_uses_name_then_latest_pk():
    assert AppealCategory._meta.ordering == ["name", "-pk"]


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_category_requires_positive_processing_days():
    category = AppealCategoryFactory.build(default_processing_days=0)

    with pytest.raises(ValidationError):
        category.full_clean()


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_normalizes_student_name_phone_and_summary_on_save():
    appeal = AppealFactory(
        student_full_name="  иванов   иван  ",
        student_phone="+7 (906) 123-45-67",
        summary="  нужна   справка  ",
    )

    assert appeal.student_full_name == "иванов иван"
    assert appeal.student_phone == "79061234567"
    assert appeal.summary == "нужна справка"


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_full_clean_accepts_formatted_phone():
    appeal = AppealFactory()
    appeal.student_phone = "+7 (906) 123-45-67"

    appeal.full_clean()


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_full_clean_rejects_invalid_phone():
    appeal = AppealFactory()
    appeal.student_phone = "123"

    with pytest.raises(ValidationError) as error:
        appeal.full_clean()

    assert "student_phone" in error.value.message_dict


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_default_status_and_ordering():
    older = AppealFactory(created_at=timezone.now() - timedelta(days=1))
    newer = AppealFactory(created_at=timezone.now())

    assert older.status == Appeal.Status.NEW
    assert list(Appeal.objects.all())[:2] == [newer, older]
    assert Appeal._meta.ordering == ["-created_at", "-pk"]


@pytest.mark.unit
def test_comment_and_history_ordering_uses_latest_pk_as_tiebreaker():
    assert AppealComment._meta.ordering == ["created_at", "-pk"]
    assert AppealHistoryEvent._meta.ordering == ["created_at", "-pk"]


@pytest.mark.django_db
@pytest.mark.integration
def test_appeal_string_uses_pk_and_summary():
    appeal = AppealFactory(summary="нужна справка")

    assert str(appeal) == f"#{appeal.pk} нужна справка"


@pytest.mark.django_db
@pytest.mark.integration
def test_comment_string_references_appeal():
    comment = AppealCommentFactory()

    assert str(comment) == _("Comment for appeal #{id}").format(id=comment.appeal_id)


@pytest.mark.django_db
@pytest.mark.integration
def test_history_event_uses_declared_event_type_choices():
    event = AppealHistoryEventFactory(event_type=AppealHistoryEvent.EventType.ACCEPTED)

    assert event.event_type == AppealHistoryEvent.EventType.ACCEPTED
    assert str(event) == _("History event for appeal #{id}").format(id=event.appeal_id)


@pytest.mark.django_db
@pytest.mark.unit
def test_appeal_is_overdue_when_open_and_past_due():
    appeal = AppealFactory(
        status=Appeal.Status.NEW,
        due_at=timezone.now() - timedelta(hours=1),
    )

    assert appeal.is_overdue is True


@pytest.mark.django_db
@pytest.mark.unit
def test_appeal_is_not_overdue_when_open_and_due_in_future():
    appeal = AppealFactory(
        status=Appeal.Status.IN_PROGRESS,
        due_at=timezone.now() + timedelta(days=1),
    )

    assert appeal.is_overdue is False


@pytest.mark.django_db
@pytest.mark.unit
def test_appeal_is_not_overdue_when_closed_even_if_past_due():
    appeal = AppealFactory(
        status=Appeal.Status.CLOSED,
        due_at=timezone.now() - timedelta(days=2),
    )

    assert appeal.is_overdue is False


@pytest.mark.django_db
@pytest.mark.integration
def test_ai_log_keeps_record_when_category_deleted():
    # Журнал вызова ИИ не должен мешать удалить категорию: ссылка обнуляется,
    # а сама запись с расходом токенов сохраняется.
    category = AppealCategoryFactory()
    log = AILog.objects.create(
        model="deepseek-v4-flash",
        status=AILog.Status.OK,
        description_in="Нужна справка",
        chosen_category=category,
        summary_out="Справка об обучении",
        prompt_tokens=600,
        cache_hit_tokens=512,
    )

    category.delete()
    log.refresh_from_db()

    assert log.chosen_category is None
    assert log.prompt_tokens == 600


@pytest.mark.django_db
@pytest.mark.unit
def test_ai_log_str_includes_status():
    saved = AILog.objects.create(model="deepseek-v4-flash", status=AILog.Status.OK)

    assert str(saved) == f"AILog #{saved.pk} (ok)"
    assert str(AILog()) == "AILog"


@pytest.mark.django_db
@pytest.mark.unit
def test_ai_log_undecided_allows_blank_category():
    # Когда модель не смогла определить категорию — запись без категории валидна.
    log = AILog.objects.create(
        model="deepseek-v4-flash",
        status=AILog.Status.UNDECIDED,
        description_in="Во сколько обед?",
        reason="Вопрос не относится ни к одной категории.",
    )

    assert log.chosen_category is None
    assert log.status == AILog.Status.UNDECIDED
