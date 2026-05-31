from dataclasses import dataclass, field

from django.db.models import QuerySet
from django.utils import timezone

from appeals.models import Appeal

# Подписи статусов для отчётов и выгрузок. Это часть представления (документ
# читает человек), поэтому они на русском, а не из англоязычных choice-меток
# модели. Порядок задаёт и порядок строк в сводке.
STATUS_LABELS: dict[str, str] = {
    Appeal.Status.NEW: "Новые",
    Appeal.Status.IN_PROGRESS: "В работе",
    Appeal.Status.CLOSED: "Закрытые",
}


@dataclass(frozen=True)
class Breakdown:
    """Одна строка разбивки: название группы и число обращений в ней."""

    label: str
    count: int


@dataclass(frozen=True)
class AppealReport:
    """Сводка по набору обращений для страницы отчётов и выгрузок.

    Строится из уже отфильтрованного по доступу queryset, поэтому ничего не
    знает о правах: какие обращения попадут в отчёт, решает слой доступа.
    """

    total: int
    overdue: int
    by_status: list[Breakdown] = field(default_factory=list)
    by_category: list[Breakdown] = field(default_factory=list)
    by_department: list[Breakdown] = field(default_factory=list)


def build_appeal_report(appeals: QuerySet[Appeal]) -> AppealReport:
    """Собирает сводку по обращениям из переданного queryset.

    Просроченные считаем по тому же правилу, что и ``Appeal.is_overdue``:
    не закрыто и срок обработки уже прошёл.
    """
    now = timezone.now()
    appeals = appeals.select_related("category", "department")

    total = 0
    overdue = 0
    status_counts: dict[str, int] = {status: 0 for status in STATUS_LABELS}
    category_counts: dict[str, int] = {}
    department_counts: dict[str, int] = {}

    for appeal in appeals:
        total += 1
        status_counts[appeal.status] = status_counts.get(appeal.status, 0) + 1
        if appeal.status != Appeal.Status.CLOSED and appeal.due_at < now:
            overdue += 1
        category_counts[appeal.category.name] = category_counts.get(appeal.category.name, 0) + 1
        department_counts[appeal.department.name] = (
            department_counts.get(appeal.department.name, 0) + 1
        )

    return AppealReport(
        total=total,
        overdue=overdue,
        by_status=[
            Breakdown(label=STATUS_LABELS[status], count=status_counts[status])
            for status in STATUS_LABELS
        ],
        by_category=_sorted_breakdown(category_counts),
        by_department=_sorted_breakdown(department_counts),
    )


def _sorted_breakdown(counts: dict[str, int]) -> list[Breakdown]:
    # Сначала по убыванию количества, при равенстве — по названию, чтобы
    # порядок строк был устойчивым и не зависел от порядка обхода словаря.
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [Breakdown(label=name, count=count) for name, count in ordered]
