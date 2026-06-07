from io import StringIO

import pytest
from django.core.management import call_command


def _run(settings, *, db_path, base_dir):
    # Подменяем путь к БД и корень проекта, чтобы проверить перенос файла, не
    # затрагивая настоящую базу.
    settings.DATABASES["default"]["NAME"] = str(db_path)
    settings.BASE_DIR = base_dir
    out = StringIO()
    call_command("ensure_db_seed", stdout=out)
    return out.getvalue()


@pytest.mark.integration
@pytest.mark.functional
def test_seeds_db_when_target_missing(settings, tmp_path):
    base = tmp_path / "repo"
    base.mkdir()
    (base / "db.sqlite3").write_bytes(b"seed-bytes")
    target = tmp_path / "data" / "db.sqlite3"

    output = _run(settings, db_path=target, base_dir=base)

    assert target.exists()
    assert target.read_bytes() == b"seed-bytes"
    assert "Seeded database" in output


@pytest.mark.integration
def test_skips_when_target_exists(settings, tmp_path):
    base = tmp_path / "repo"
    base.mkdir()
    (base / "db.sqlite3").write_bytes(b"seed-bytes")
    target = tmp_path / "data" / "db.sqlite3"
    target.parent.mkdir()
    target.write_bytes(b"existing")

    output = _run(settings, db_path=target, base_dir=base)

    assert target.read_bytes() == b"existing"  # не перезаписали
    assert "already present" in output


@pytest.mark.integration
def test_noop_when_path_equals_bundled_file(settings, tmp_path):
    base = tmp_path / "repo"
    base.mkdir()
    seed = base / "db.sqlite3"
    seed.write_bytes(b"seed-bytes")

    output = _run(settings, db_path=seed, base_dir=base)

    assert "nothing to seed" in output


@pytest.mark.integration
def test_warns_when_no_bundled_db(settings, tmp_path):
    base = tmp_path / "repo"
    base.mkdir()  # без db.sqlite3 внутри
    target = tmp_path / "data" / "db.sqlite3"

    output = _run(settings, db_path=target, base_dir=base)

    assert not target.exists()
    assert "nothing to seed" in output
