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
from decimal import Decimal


@dataclass(frozen=True)
class AIConfig:
    """Разобранные параметры подключения к ИИ-модели."""

    model: str
    base_url: str
    api_key: str


@dataclass(frozen=True)
class ModelPricing:
    """Цены модели за 1 млн токенов: кэш-попадание, кэш-промах, ответ."""

    cache_hit: Decimal
    cache_miss: Decimal
    output: Decimal


# Цены в долларах за 1 млн токенов (официальный прайс DeepSeek). Если модель
# неизвестна, стоимость не считаем — токены всё равно сохраняются в журнале.
MODEL_PRICING: dict[str, ModelPricing] = {
    "deepseek-v4-flash": ModelPricing(
        cache_hit=Decimal("0.0028"),
        cache_miss=Decimal("0.14"),
        output=Decimal("0.28"),
    ),
    "deepseek-v4-pro": ModelPricing(
        cache_hit=Decimal("0.003625"),
        cache_miss=Decimal("0.435"),
        output=Decimal("0.87"),
    ),
}

_PER_MILLION = Decimal(1_000_000)


def compute_cost(
    model: str,
    *,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """Считает стоимость вызова по тарифам модели с учётом кэширования префикса.

    Для неизвестной модели возвращает 0: цены меняются и заведены не для всех
    моделей, но это не должно мешать сохранить журнал вызова.
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return Decimal(0)

    cost = (
        pricing.cache_hit * cache_hit_tokens
        + pricing.cache_miss * cache_miss_tokens
        + pricing.output * completion_tokens
    ) / _PER_MILLION
    return cost.quantize(Decimal("0.00000001"))


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
