"""
Structured Logger — JSON-format logging for all Orchestrator operations.

Provides consistent, machine-parseable log output with:
- ISO 8601 timestamps
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Contextual fields (task_id, role, model, trace_id)
- Exception tracebacks in structured form

Usage:
    logger = get_logger("orchestrator")
    logger.info("Task routed", task_id="task-001", role="engineer")
    logger.error("Validation failed", task_id="task-001", error="missing field")
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra fields attached to the record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """
    Structured logger that emits JSON log records.

    Wraps Python's standard logging with structured field support.
    """

    def __init__(self, name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._context: Dict[str, Any] = {}

        # Add structured handler if not already present
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self._logger.addHandler(handler)
            self._logger.propagate = False

    def bind(self, **kwargs) -> "StructuredLogger":
        """Return a new logger with additional context fields bound."""
        new_logger = StructuredLogger.__new__(StructuredLogger)
        new_logger._logger = self._logger
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _log(self, level: int, message: str, **kwargs) -> None:
        extra = {**self._context, **kwargs}
        self._logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log an error with exception info."""
        extra = {**self._context, **kwargs}
        self._logger.exception(message, extra=extra)


# Module-level logger cache
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """Get or create a named StructuredLogger."""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)
    return _loggers[name]
