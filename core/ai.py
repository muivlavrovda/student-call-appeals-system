"""Конфигурация подключения к ИИ-модели.

Все параметры подключения задаются одной необязательной переменной окружения
``AI_URL`` в формате ``model@base_url#key`` — по аналогии с тем, как одной
строкой задают подключение к базе данных. Например::

    AI_URL="deepseek-v4-flash@https://api.deepseek.com#sk-..."

Менять провайдера (DeepSeek, OpenRouter и т.п.) можно правкой одной строки, не
трогая код: достаточно указать другой OpenAI-совместимый ``base_url`` и модель.

Если переменная не задана или пуста — ИИ-функции полностью отключены, и сервис
работает как обычная форма с ручным выбором категории.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    """Разобранные параметры подключения к ИИ-модели."""

    model: str
    base_url: str
    api_key: str


def parse_ai_url(raw: str | None) -> AIConfig | None:
    """Разбирает строку ``model@base_url#key`` в конфигурацию подключения.

    Возвращает ``None``, если строка пуста или не задана — это штатное состояние
    «ИИ выключен». Если строка задана, но имеет неверный формат, поднимается
    ``ValueError``: молчаливо игнорировать испорченную настройку нельзя, иначе
    отключение ИИ из-за опечатки осталось бы незамеченным.

    Разбор устойчив к спецсимволам внутри частей: ``base_url`` содержит ``://``,
    ключ — дефисы, поэтому делим по первому ``@`` и по последнему ``#``.
    """
    if raw is None:
        return None

    value = raw.strip()
    if not value:
        return None

    model, sep, rest = value.partition("@")
    if not sep:
        raise ValueError("AI_URL: ожидался формат 'model@base_url#key' (нет '@').")

    base_url, sep, api_key = rest.rpartition("#")
    if not sep:
        raise ValueError("AI_URL: ожидался формат 'model@base_url#key' (нет '#').")

    model = model.strip()
    base_url = base_url.strip()
    api_key = api_key.strip()
    if not (model and base_url and api_key):
        raise ValueError("AI_URL: пустая модель, адрес или ключ в 'model@base_url#key'.")

    return AIConfig(model=model, base_url=base_url, api_key=api_key)
