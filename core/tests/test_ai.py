import pytest

from core.ai import AIConfig, parse_ai_url


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
