import logging

import pytest
import structlog

from core.logging import setup_logging


@pytest.mark.unit
def test_rejects_unknown_log_format():
    with pytest.raises(ValueError, match="log_format"):
        setup_logging(log_format="xml", level="INFO")


@pytest.mark.unit
def test_text_logging_config_uses_console_renderer():
    config = setup_logging(log_format="text", level="DEBUG")

    assert config["root"]["level"] == "DEBUG"
    assert isinstance(config["formatters"]["structlog"]["processor"], structlog.dev.ConsoleRenderer)


@pytest.mark.unit
def test_json_logging_config_uses_json_renderer():
    config = setup_logging(log_format="json", level="INFO")

    assert config["root"]["level"] == "INFO"
    assert isinstance(
        config["formatters"]["structlog"]["processor"],
        structlog.processors.JSONRenderer,
    )
    assert config["handlers"]["console"]["class"] == "logging.StreamHandler"
    assert logging.getLogger("django")
