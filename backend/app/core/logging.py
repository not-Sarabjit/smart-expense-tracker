"""Structured logging.

Every log line — from structlog loggers *and* plain ``logging.getLogger(...)``
loggers (uvicorn, SQLAlchemy, existing modules) — goes through the same
structlog processor chain and comes out as one JSON object per line, stamped
with ``request_id`` / ``user_id`` when emitted during a request.

    {"event": "transaction.created", "transaction_id": 17, "request_id": "4f0c…",
     "user_id": 3, "logger": "app.services.transaction_service", "level": "info",
     "timestamp": "2026-10-03T10:22:31.123456Z"}

Filter one request:  ``grep '"request_id": "4f0c…"' logs/app.log``  (or ``jq 'select(.request_id=="4f0c…")'``).

New code: ``logger = get_logger(__name__)`` then ``logger.info("thing.happened", key=value)``.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

from app.core.request_context import add_request_context

# Marks handlers installed by setup_logging so a second call doesn't duplicate them
_HANDLER_FLAG = "_app_structlog_handler"

# Processors shared by structlog loggers and stdlib ("foreign") log records
_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    add_request_context,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.ExtraAdder(),
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def build_formatter(json_logs: bool = True) -> structlog.stdlib.ProcessorFormatter:
    """The formatter every handler uses: JSON lines, or coloured key=value for local dev."""
    renderer = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )


def setup_logging(level: str = "INFO", json_logs: bool = True, log_dir: str = "logs") -> None:
    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    root.setLevel(level.upper())

    # Prevent duplicate handlers if setup_logging() is called more than once
    if any(getattr(handler, _HANDLER_FLAG, False) for handler in root.handlers):
        return

    # Console: JSON in every environment except when explicitly asked for pretty output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(build_formatter(json_logs))

    # File: always JSON (machine-readable), rotating at 5 MB × 5 backups
    path = Path(log_dir)
    path.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        path / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(build_formatter(json_logs=True))

    for handler in (console_handler, file_handler):
        setattr(handler, _HANDLER_FLAG, True)
        root.addHandler(handler)

    # Our middleware writes one access line per request (with request_id);
    # uvicorn's own access log would duplicate it without the ids.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # Let uvicorn's error/startup loggers flow through our handlers instead of their own
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)
