"""Хранение сформированных отчётов в файловой системе.

Сформированные выгрузки сохраняются на диск (в каталог ``reports`` внутри
``MEDIA_ROOT``), откуда их можно позже просмотреть и скачать. Работа с диском
ведётся через стандартное хранилище Django, поэтому каталог берётся из настроек,
а не задаётся жёстко.
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

# Подкаталог в MEDIA_ROOT, где складываются файлы отчётов.
REPORTS_DIR = "reports"

# Допустимое имя файла отчёта: только то, что сами и создаём в save_report.
# Жёсткий шаблон отсекает любые попытки выйти за каталог (.., слэши, бэкслэши).
REPORT_NAME_RE = re.compile(r"^appeal-report-\d{8}-\d{6}(?:_\w+)?\.(?:xlsx|docx)$")

# Человекочитаемые подписи форматов для списка сохранённых файлов.
FORMAT_LABELS = {
    "xlsx": "Таблица Excel",
    "docx": "Документ Word",
}


@dataclass(frozen=True)
class StoredReport:
    """Сведения о сохранённом на диск файле отчёта."""

    name: str
    path: str
    fmt: str
    size: int
    created_at: datetime

    @property
    def format_label(self) -> str:
        return FORMAT_LABELS.get(self.fmt, self.fmt.upper())


def save_report(content: bytes, *, fmt: str, generated_at: datetime) -> str:
    """Сохраняет содержимое отчёта на диск и возвращает имя файла.

    Имя складывается из даты-времени формирования и формата, чтобы файлы не
    перезаписывали друг друга и были узнаваемы в списке.
    """
    stamp = timezone.localtime(generated_at).strftime("%Y%m%d-%H%M%S")
    name = f"appeal-report-{stamp}.{fmt}"
    path = f"{REPORTS_DIR}/{name}"
    # Если файл с таким именем уже есть (повтор за ту же секунду), storage сам
    # подберёт свободное имя, поэтому используем фактически записанное.
    saved_path = default_storage.save(path, ContentFile(content))
    return saved_path.rsplit("/", 1)[-1]


def list_reports() -> list[StoredReport]:
    """Возвращает сохранённые отчёты, начиная с самых новых.

    Если каталог ещё не создан (ни один отчёт не сохранялся), возвращается
    пустой список.
    """
    if not default_storage.exists(REPORTS_DIR):
        return []

    _dirs, files = default_storage.listdir(REPORTS_DIR)
    reports = []
    for name in files:
        path = f"{REPORTS_DIR}/{name}"
        fmt = name.rsplit(".", 1)[-1].lower()
        reports.append(
            StoredReport(
                name=name,
                path=path,
                fmt=fmt,
                size=default_storage.size(path),
                created_at=default_storage.get_created_time(path),
            )
        )

    reports.sort(key=lambda report: report.created_at, reverse=True)
    return reports


def open_report(name: str):
    """Открывает сохранённый файл отчёта по имени для чтения с диска.

    Имя сводится к одному сегменту пути и сверяется со строгим шаблоном имени
    отчёта, поэтому выход за пределы каталога (``..``, слэши, бэкслэши) и любые
    посторонние файлы исключены. Неподходящее имя трактуется как «не найдено».
    """
    # basename отсекает каталоги по обоим разделителям, шаблон — всё прочее.
    safe_name = os.path.basename(name.replace("\\", "/"))
    if not REPORT_NAME_RE.fullmatch(safe_name):
        return None

    path = f"{REPORTS_DIR}/{safe_name}"
    if not default_storage.exists(path):
        return None
    return default_storage.open(path, "rb")
