from __future__ import annotations

from typing import Any

import structlog
from structlog.dev import RichTracebackFormatter
from structlog.processors import CallsiteParameter


def setup_logging(log_format: str, level: str) -> dict[str, Any]:
    if log_format not in ("text", "json"):
        raise ValueError(f"log_format must be 'text' or 'json', got {log_format!r}")

    timestamper = (
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=True)
        if log_format == "text"
        else structlog.processors.TimeStamper(fmt="iso", utc=True)
    )

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME,
            ],
        ),
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]
    if log_format == "json":
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: structlog.typing.Processor = (
        structlog.dev.ConsoleRenderer(
            exception_formatter=RichTracebackFormatter(show_locals=False),
        )
        if log_format == "text"
        else structlog.processors.JSONRenderer()
    )

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": renderer,
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structlog",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            "django": {"level": "INFO", "propagate": True},
            "gunicorn.error": {"level": "INFO", "propagate": True},
        },
    }
