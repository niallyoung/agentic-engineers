"""
Error Handler for the Claude Code harness.

Error classification and retry policy determination. Distinguishes between
transient errors (retry-able), permanent errors (don't retry), safeguard
pauses (escalate), and timeouts.

Usage::

    from src.harnesses.claude_code.error_handler import (
        ErrorClassifier, ErrorType
    )

    classifier = ErrorClassifier()
    error_type = classifier.classify(some_exception)
    policy = classifier.retry_policy(error_type, retry_count=0)
    print(policy.should_retry, policy.max_retries)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Classification of error types for retry/escalation decisions."""

    TRANSIENT = "transient"  # network blip, retry-able
    PERMANENT = "permanent"  # bad input, don't retry
    SAFEGUARD_PAUSE = "safeguard"  # model refusal, escalate
    TIMEOUT = "timeout"  # deadline exceeded
    UNKNOWN = "unknown"


@dataclass
class RetryPolicy:
    """Policy for retrying or escalating on error."""

    should_retry: bool
    max_retries: int
    backoff_seconds: float
    should_escalate: bool


class ErrorClassifier:
    """Classify errors and determine retry/escalation policies.

    Supports standard Python exceptions and provides structured
    retry policies based on error classification.
    """

    def __init__(self) -> None:
        """Initialize the error classifier."""
        pass

    def classify(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ErrorType:
        """Classify an exception into an error type.

        Args:
            error: The exception to classify.
            context: Optional contextual information (e.g., HTTP status code).

        Returns:
            ErrorType classification.
        """
        if context is None:
            context = {}

        error_name = type(error).__name__
        error_msg = str(error).lower()

        # Timeout errors
        if error_name in ("TimeoutError", "asyncio.TimeoutError"):
            logger.info(
                "error.classify",
                extra={
                    "error_type": "timeout",
                    "error_name": error_name,
                },
            )
            return ErrorType.TIMEOUT

        # Safeguard pause (model refusal, content policy)
        if "refus" in error_msg or "not allowed" in error_msg:
            logger.info(
                "error.classify",
                extra={
                    "error_type": "safeguard",
                    "error_name": error_name,
                },
            )
            return ErrorType.SAFEGUARD_PAUSE

        # Transient network errors
        if error_name in (
            "ConnectionError",
            "ConnectionResetError",
            "ConnectionAbortedError",
            "TimeoutError",
            "socket.error",
        ):
            logger.info(
                "error.classify",
                extra={
                    "error_type": "transient",
                    "error_name": error_name,
                },
            )
            return ErrorType.TRANSIENT

        # HTTP errors from context (if provided)
        if "status_code" in context:
            status = context["status_code"]
            if status >= 500:  # Server error
                logger.info(
                    "error.classify",
                    extra={
                        "error_type": "transient",
                        "error_name": error_name,
                        "http_status": status,
                    },
                )
                return ErrorType.TRANSIENT
            elif status == 429:  # Rate limited
                logger.info(
                    "error.classify",
                    extra={
                        "error_type": "transient",
                        "error_name": error_name,
                        "http_status": status,
                    },
                )
                return ErrorType.TRANSIENT
            elif 400 <= status < 500:  # Client error
                logger.info(
                    "error.classify",
                    extra={
                        "error_type": "permanent",
                        "error_name": error_name,
                        "http_status": status,
                    },
                )
                return ErrorType.PERMANENT

        # Permanent errors (bad input, validation, etc.)
        if error_name in (
            "ValueError",
            "TypeError",
            "KeyError",
            "AttributeError",
        ):
            logger.info(
                "error.classify",
                extra={
                    "error_type": "permanent",
                    "error_name": error_name,
                },
            )
            return ErrorType.PERMANENT

        # Default to UNKNOWN
        logger.warning(
            "error.classify_unknown",
            extra={
                "error_type": "unknown",
                "error_name": error_name,
            },
        )
        return ErrorType.UNKNOWN

    def retry_policy(
        self, error_type: ErrorType, retry_count: int = 0
    ) -> RetryPolicy:
        """Determine retry policy based on error type.

        Args:
            error_type: Classification from classify().
            retry_count: Current retry attempt number.

        Returns:
            RetryPolicy with retry/escalation decisions.
        """
        if error_type == ErrorType.TRANSIENT:
            # Transient errors get retried with exponential backoff
            max_retries = 3
            should_retry = retry_count < max_retries
            backoff = self.backoff(retry_count, base=2.0)
            return RetryPolicy(
                should_retry=should_retry,
                max_retries=max_retries,
                backoff_seconds=backoff,
                should_escalate=False,
            )

        elif error_type == ErrorType.TIMEOUT:
            # Timeouts do not retry; escalate immediately
            return RetryPolicy(
                should_retry=False,
                max_retries=0,
                backoff_seconds=0.0,
                should_escalate=True,
            )

        elif error_type == ErrorType.SAFEGUARD_PAUSE:
            # Safeguard pauses escalate without retry
            return RetryPolicy(
                should_retry=False,
                max_retries=0,
                backoff_seconds=0.0,
                should_escalate=True,
            )

        elif error_type == ErrorType.PERMANENT:
            # Permanent errors do not retry; escalate for operator review
            return RetryPolicy(
                should_retry=False,
                max_retries=0,
                backoff_seconds=0.0,
                should_escalate=True,
            )

        else:  # UNKNOWN
            # Unknown errors are treated conservatively: don't retry
            return RetryPolicy(
                should_retry=False,
                max_retries=0,
                backoff_seconds=0.0,
                should_escalate=True,
            )

    @staticmethod
    def backoff(retry_count: int, base: float = 2.0) -> float:
        """Calculate exponential backoff delay in seconds.

        Formula: base^retry_count, capped at 60 seconds.

        Args:
            retry_count: Current retry attempt number (0-indexed).
            base: Base for exponential backoff (default: 2.0).

        Returns:
            Delay in seconds.

        Examples:
            backoff(0, base=2.0) -> 1.0
            backoff(1, base=2.0) -> 2.0
            backoff(2, base=2.0) -> 4.0
            backoff(10, base=2.0) -> 60.0 (capped)
        """
        delay = base ** retry_count
        return min(delay, 60.0)
