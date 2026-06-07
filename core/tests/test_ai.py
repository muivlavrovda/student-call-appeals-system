from decimal import Decimal

import pytest

from core.ai import AIConfig, compute_cost, parse_ai_url


@pytest.mark.unit
def test_parse_full_url_returns_config():
    config = parse_ai_url("deepseek-v4-flash@https://api.deepseek.com#sk-abc-123")

    assert config == AIConfig(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key="sk-abc-123",
    )


@pytest.mark.unit
def test_parse_keeps_base_url_with_path():
    # У OpenRouter base_url содержит путь — он не должен потеряться при разборе.
    config = parse_ai_url("anthropic/claude-3.5-sonnet@https://openrouter.ai/api/v1#sk-or-xyz")

    assert config is not None
    assert config.model == "anthropic/claude-3.5-sonnet"
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.api_key == "sk-or-xyz"


@pytest.mark.unit
def test_parse_strips_surrounding_whitespace():
    config = parse_ai_url("  model@https://host#key  ")

    assert config == AIConfig(model="model", base_url="https://host", api_key="key")


@pytest.mark.unit
@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_returns_none_when_unset_or_blank(raw):
    # Пустое значение — штатное состояние «ИИ выключен», не ошибка.
    assert parse_ai_url(raw) is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "model-without-separators",
        "model@https://host",  # нет '#'
        "model@#key",  # пустой base_url
        "@https://host#key",  # пустая модель
        "model@https://host#",  # пустой ключ
    ],
)
def test_parse_rejects_malformed_value(raw):
    # Заданная, но испорченная строка должна явно падать, а не тихо отключать ИИ.
    with pytest.raises(ValueError):
        parse_ai_url(raw)


@pytest.mark.unit
def test_compute_cost_uses_tiered_rates():
    # 1 млн токенов каждого вида по тарифам deepseek-v4-flash:
    # hit 0.0028 + miss 0.14 + output 0.28 = 0.4228.
    cost = compute_cost(
        "deepseek-v4-flash",
        cache_hit_tokens=1_000_000,
        cache_miss_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert cost == Decimal("0.42280000")


@pytest.mark.unit
def test_compute_cost_counts_cache_hit_cheaper_than_miss():
    # Те же токены, но в кэше — должно быть существенно дешевле, чем мимо кэша.
    hit = compute_cost(
        "deepseek-v4-flash", cache_hit_tokens=1000, cache_miss_tokens=0, completion_tokens=0
    )
    miss = compute_cost(
        "deepseek-v4-flash", cache_hit_tokens=0, cache_miss_tokens=1000, completion_tokens=0
    )

    assert hit < miss


@pytest.mark.unit
def test_compute_cost_unknown_model_is_zero():
    # Неизвестная модель не должна мешать сохранить журнал — стоимость 0.
    cost = compute_cost(
        "some-other-model",
        cache_hit_tokens=500,
        cache_miss_tokens=500,
        completion_tokens=500,
    )

    assert cost == Decimal(0)
