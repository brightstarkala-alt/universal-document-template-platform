"""
Application-wide structured logging configuration.

Usage elsewhere in the codebase:

    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("something happened", extra={"user_id": 123})

In development, logs are human-readable. In production, logs are emitted
as single-line JSON so they can be ingested by any log aggregator
(CloudWatch, Datadog, Supabase Logs, etc.) without extra parsing rules.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings

_RESERVED_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
    "message",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED_LOG_RECORD_ATTRS and not key.startswith("_")
        }
        if extras:
            payload["context"] = extras

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class HumanFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


_configured = False


def configure_logging() -> None:
    """Configure the root logger once, on application startup."""
    global _configured
    if _configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.is_production else HumanFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers unless we're debugging.
    for noisy_logger in ("uvicorn.access", "httpx"):
        logging.getLogger(noisy_logger).setLevel(
            logging.WARNING if settings.LOG_LEVEL.upper() != "DEBUG" else logging.DEBUG
        )

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
