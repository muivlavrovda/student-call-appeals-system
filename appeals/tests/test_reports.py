from datetime import timedelta

import pytest
from django.utils import timezone

from appeals.models import Appeal
from appeals.reports import STATUS_LABELS, build_appeal_report
from appeals.tests.factories import (
    AppealCategoryFactory,
    AppealFactory,
    DepartmentFactory,
)


def _by_label(rows):
    return {row.label: row.count for row in rows}


@pytest.mark.django_db
@pytest.mark.unit
def test_report_counts_total_and_statuses():
    AppealFactory(status=Appeal.Status.NEW)
    AppealFactory(status=Appeal.Status.IN_PROGRESS)
    AppealFactory(status=Appeal.Status.CLOSED)
    AppealFactory(status=Appeal.Status.CLOSED)

    report = build_appeal_report(Appeal.objects.all())

    assert report.total == 4
    counts = _by_label(report.by_status)
    assert counts[STATUS_LABELS[Appeal.Status.NEW]] == 1
    assert counts[STATUS_LABELS[Appeal.Status.IN_PROGRESS]] == 1
    assert counts[STATUS_LABELS[Appeal.Status.CLOSED]] == 2


@pytest.mark.django_db
@pytest.mark.unit
def test_report_status_rows_follow_fixed_order_even_when_empty():
    AppealFactory(status=Appeal.Status.NEW)

    report = build_appeal_report(Appeal.objects.all())

    labels = [row.label for row in report.by_status]
    assert labels == list(STATUS_LABELS.values())
    # Статусы без обращений всё равно присутствуют с нулём.
    assert _by_label(report.by_status)[STATUS_LABELS[Appeal.Status.CLOSED]] == 0


@pytest.mark.django_db
@pytest.mark.unit
def test_report_counts_overdue_only_for_unclosed_past_due():
    now = timezone.now()
    AppealFactory(status=Appeal.Status.NEW, due_at=now - timedelta(days=1))
    AppealFactory(status=Appeal.Status.IN_PROGRESS, due_at=now - timedelta(days=2))
    # Просрочена по дате, но закрыта — не считается.
    AppealFactory(status=Appeal.Status.CLOSED, due_at=now - timedelta(days=3))
    # Срок ещё не наступил.
    AppealFactory(status=Appeal.Status.NEW, due_at=now + timedelta(days=1))

    report = build_appeal_report(Appeal.objects.all())

    assert report.overdue == 2


@pytest.mark.django_db
@pytest.mark.unit
def test_report_groups_by_category_and_department():
    learning = DepartmentFactory(name="Учебный отдел")
    hr = DepartmentFactory(name="Отдел кадров")
    certificates = AppealCategoryFactory(name="Справки", department=learning)
    transfers = AppealCategoryFactory(name="Переводы", department=learning)
    staffing = AppealCategoryFactory(name="Кадры", department=hr)

    AppealFactory(category=certificates, department=learning)
    AppealFactory(category=certificates, department=learning)
    AppealFactory(category=transfers, department=learning)
    AppealFactory(category=staffing, department=hr)

    report = build_appeal_report(Appeal.objects.all())

    assert _by_label(report.by_category) == {
        "Справки": 2,
        "Переводы": 1,
        "Кадры": 1,
    }
    assert _by_label(report.by_department) == {
        "Учебный отдел": 3,
        "Отдел кадров": 1,
    }


@pytest.mark.django_db
@pytest.mark.unit
def test_report_breakdown_sorted_by_count_then_name():
    department = DepartmentFactory()
    rare = AppealCategoryFactory(name="Яблоко", department=department)
    common = AppealCategoryFactory(name="Банан", department=department)
    tie = AppealCategoryFactory(name="Апельсин", department=department)

    AppealFactory(category=common, department=department)
    AppealFactory(category=common, department=department)
    AppealFactory(category=rare, department=department)
    AppealFactory(category=tie, department=department)

    report = build_appeal_report(Appeal.objects.all())

    # Сначала по убыванию количества, при равенстве — по алфавиту названия.
    assert [(row.label, row.count) for row in report.by_category] == [
        ("Банан", 2),
        ("Апельсин", 1),
        ("Яблоко", 1),
    ]


@pytest.mark.django_db
@pytest.mark.unit
def test_report_empty_when_no_appeals():
    report = build_appeal_report(Appeal.objects.none())

    assert report.total == 0
    assert report.overdue == 0
    assert report.by_category == []
    assert report.by_department == []
    # Статусы остаются как нулевые строки фиксированного порядка.
    assert [row.count for row in report.by_status] == [0, 0, 0]
