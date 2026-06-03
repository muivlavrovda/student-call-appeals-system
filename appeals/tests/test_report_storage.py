from datetime import datetime

import pytest
from django.utils import timezone

from appeals.report_storage import (
    REPORTS_DIR,
    list_reports,
    open_report,
    save_report,
)


@pytest.fixture
def media_root(settings, tmp_path):
    # Каждый тест работает с собственным каталогом MEDIA_ROOT, чтобы не писать
    # в реальную папку проекта и не зависеть от порядка тестов.
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _moment(hour=12, minute=0):
    return timezone.make_aware(datetime(2026, 6, 2, hour, minute))


@pytest.mark.unit
def test_save_report_writes_file_to_disk(media_root):
    name = save_report(b"xlsx-bytes", fmt="xlsx", generated_at=_moment())

    saved = media_root / REPORTS_DIR / name
    assert saved.exists()
    assert saved.read_bytes() == b"xlsx-bytes"
    assert name.endswith(".xlsx")


@pytest.mark.unit
def test_save_report_uses_timestamped_name(media_root):
    name = save_report(b"data", fmt="docx", generated_at=_moment(14, 30))

    assert name == "appeal-report-20260602-143000.docx"


@pytest.mark.unit
def test_save_report_keeps_both_files_for_same_moment(media_root):
    first = save_report(b"one", fmt="xlsx", generated_at=_moment())
    second = save_report(b"two", fmt="xlsx", generated_at=_moment())

    # Совпадение секунды не должно затирать предыдущий файл.
    assert first != second
    assert (media_root / REPORTS_DIR / first).read_bytes() == b"one"
    assert (media_root / REPORTS_DIR / second).read_bytes() == b"two"


@pytest.mark.unit
def test_list_reports_returns_newest_first(media_root):
    save_report(b"old", fmt="xlsx", generated_at=_moment(10))
    save_report(b"new", fmt="docx", generated_at=_moment(18))

    reports = list_reports()

    assert [r.fmt for r in reports] == ["docx", "xlsx"]
    assert reports[0].size == len(b"new")
    assert reports[0].format_label == "Документ Word"


@pytest.mark.unit
def test_list_reports_empty_when_nothing_saved(media_root):
    assert list_reports() == []


@pytest.mark.unit
def test_open_report_reads_back_content(media_root):
    name = save_report(b"round-trip", fmt="xlsx", generated_at=_moment())

    handle = open_report(name)

    assert handle is not None
    with handle:
        assert handle.read() == b"round-trip"


@pytest.mark.unit
def test_open_report_missing_returns_none(media_root):
    assert open_report("does-not-exist.xlsx") is None


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    "malicious",
    [
        "../../etc/passwd",
        "../secrets.txt",
        "..",
        "..\\..\\windows\\win.ini",
        "reports/../secret.xlsx",
        "appeal-report.xlsx",  # не наш формат имени (нет метки времени)
        "random.txt",
        "appeal-report-20260602-120000.exe",  # чужое расширение
    ],
)
def test_open_report_rejects_paths_outside_reports(media_root, malicious):
    # Любое имя, не похожее на наш файл отчёта или пытающееся выйти за каталог,
    # трактуется как «не найдено» и не открывает посторонний файл.
    save_report(b"safe", fmt="xlsx", generated_at=_moment())

    assert open_report(malicious) is None


@pytest.mark.unit
@pytest.mark.security
def test_open_report_accepts_collision_suffixed_name(media_root):
    # При совпадении имени storage добавляет суффикс перед расширением —
    # такое имя тоже должно открываться.
    save_report(b"one", fmt="xlsx", generated_at=_moment())
    second = save_report(b"two", fmt="xlsx", generated_at=_moment())

    handle = open_report(second)
    assert handle is not None
    with handle:
        assert handle.read() == b"two"
