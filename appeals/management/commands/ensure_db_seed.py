import shutil
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Seed the database file into persistent storage on first run. "
        "Copies the committed db.sqlite3 to DJ_DB_PATH if the target is missing."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        target = Path(settings.DATABASES["default"]["NAME"])
        seed = settings.BASE_DIR / "db.sqlite3"

        # На хостинге БД лежит в постоянном хранилище (DJ_DB_PATH=/data/db.sqlite3),
        # которое при первом запуске пустое. Переносим в него заранее наполненную
        # базу из репозитория, чтобы демонстрационные данные были на месте.
        if target == seed:
            self.stdout.write(
                self.style.NOTICE("DB path equals the bundled file; nothing to seed.")
            )
            return

        if target.exists():
            self.stdout.write(self.style.NOTICE(f"DB already present at {target}; skipping seed."))
            return

        if not seed.exists():
            self.stdout.write(self.style.WARNING(f"No bundled DB at {seed}; nothing to seed."))
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed, target)
        self.stdout.write(self.style.SUCCESS(f"Seeded database into {target}."))
