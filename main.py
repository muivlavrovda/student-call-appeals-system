#!/usr/bin/env python
"""Точка входа для запуска приложения.

Запускает веб-сервис «Журнал учёта телефонных обращений обучающихся»: применяет
миграции базы данных, собирает переводы интерфейса, а затем поднимает сервер
разработки. Управляющие команды по-прежнему доступны через ``manage.py``
(``python manage.py <команда>``); этот файл нужен лишь для простого старта одной
командой ``python main.py``.

По умолчанию сервер слушает 127.0.0.1:8000. Адрес можно переопределить
аргументом, например: ``python main.py 0.0.0.0:8080``.
"""

import os
import sys

DEFAULT_ADDRPORT = "127.0.0.1:8000"


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что зависимости из "
            "requirements.txt установлены в активированном виртуальном окружении."
        ) from exc

    # Адрес сервера можно передать первым аргументом, иначе берём адрес по
    # умолчанию. Прочие аргументы пробрасываем в runserver без изменений.
    args = sys.argv[1:]
    addrport = args[0] if args and ":" in args[0] else DEFAULT_ADDRPORT
    extra = [arg for arg in args if arg != addrport]

    # Сначала приводим схему БД в актуальное состояние.
    execute_from_command_line(["manage.py", "migrate"])

    # Собираем переводы интерфейса (.po -> .mo). Команде нужен установленный
    # gettext; если его нет, не валим запуск, а просто работаем без переводов.
    try:
        execute_from_command_line(["manage.py", "compilemessages"])
    except Exception as exc:  # noqa: BLE001 — старт сервера важнее переводов
        print(f"Не удалось собрать переводы (compilemessages): {exc}")

    # Запускаем сервер.
    execute_from_command_line(["manage.py", "runserver", addrport, *extra])


if __name__ == "__main__":
    main()
