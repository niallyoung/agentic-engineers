"""
Regression tests for Claude Code harness ErrorClassifier.

Tests for error classification into ErrorType categories and
retry/escalation policy determination.
"""

from __future__ import annotations

import pytest

from src.harnesses.claude_code.error_handler import (
    ErrorClassifier,
    ErrorType,
    RetryPolicy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def classifier() -> ErrorClassifier:
    """Shared ErrorClassifier instance."""
    return ErrorClassifier()


# ---------------------------------------------------------------------------
# E1.1-E1.6: Error classification
# ---------------------------------------------------------------------------


class TestErrorClassification:
    """Error classification into ErrorType categories."""

    def test_classify_timeout_error(
        self, classifier: ErrorClassifier
    ) -> None:
        """TimeoutError classifies as TIMEOUT."""
        error = TimeoutError("deadline exceeded")
        result = classifier.classify(error)
        assert result == ErrorType.TIMEOUT

    def test_classify_connection_error_is_transient(
        self, classifier: ErrorClassifier
    ) -> None:
        """ConnectionError with neutral message classifies as TRANSIENT.

        Note: messages containing 'refus' trigger safeguard check first
        (e.g. 'connection refused'), so we use a neutral message here.
        """
        error = ConnectionError("network unreachable")
        result = classifier.classify(error)
        assert result == ErrorType.TRANSIENT

    def test_classify_connection_reset_error_is_transient(
        self, classifier: ErrorClassifier
    ) -> None:
        """ConnectionResetError classifies as TRANSIENT."""
        error = ConnectionResetError("connection reset by peer")
        result = classifier.classify(error)
        assert result == ErrorType.TRANSIENT

    def test_classify_connection_aborted_error_is_transient(
        self, classifier: ErrorClassifier
    ) -> None:
        """ConnectionAbortedError classifies as TRANSIENT."""
        error = ConnectionAbortedError("connection aborted")
        result = classifier.classify(error)
        assert result == ErrorType.TRANSIENT

    def test_classify_value_error_is_permanent(
        self, classifier: ErrorClassifier
    ) -> None:
        """ValueError classifies as PERMANENT."""
        error = ValueError("invalid input")
        result = classifier.classify(error)
        assert result == ErrorType.PERMANENT

    def test_classify_type_error_is_permanent(
        self, classifier: ErrorClassifier
    ) -> None:
        """TypeError classifies as PERMANENT."""
        error = TypeError("wrong type")
        result = classifier.classify(error)
        assert result == ErrorType.PERMANENT

    def test_classify_key_error_is_permanent(
        self, classifier: ErrorClassifier
    ) -> None:
        """KeyError classifies as PERMANENT."""
        error = KeyError("missing key")
        result = classifier.classify(error)
        assert result == ErrorType.PERMANENT

    def test_classify_attribute_error_is_permanent(
        self, classifier: ErrorClassifier
    ) -> None:
        """AttributeError classifies as PERMANENT."""
        error = AttributeError("no attribute")
        result = classifier.classify(error)
        assert result == ErrorType.PERMANENT

    def test_classify_refusal_message_is_safeguard(
        self, classifier: ErrorClassifier
    ) -> None:
        """Exception with 'refus' in message classifies as SAFEGUARD_PAUSE."""
        error = RuntimeError("Model refuses this request")
        result = classifier.classify(error)
        assert result == ErrorType.SAFEGUARD_PAUSE

    def test_classify_not_allowed_message_is_safeguard(
        self, classifier: ErrorClassifier
    ) -> None:
        """Exception with 'not allowed' in message classifies as SAFEGUARD_PAUSE."""
        error = Exception("action not allowed by policy")
        result = classifier.classify(error)
        assert result == ErrorType.SAFEGUARD_PAUSE

    def test_classify_unknown_exception_is_unknown(
        self, classifier: ErrorClassifier
    ) -> None:
        """Unrecognised exception classifies as UNKNOWN."""
        error = Exception("unexpected failure")
        result = classifier.classify(error)
        assert result == ErrorType.UNKNOWN

    def test_classify_http_500_is_transient(
        self, classifier: ErrorClassifier
    ) -> None:
        """HTTP 500 status code in context classifies as TRANSIENT."""
        error = RuntimeError("server error")
        result = classifier.classify(error, context={"status_code": 500})
        assert result == ErrorType.TRANSIENT

    def test_classify_http_503_is_transient(
        self, classifier: ErrorClassifier
    ) -> None:
        """HTTP 503 status code in context classifies as TRANSIENT."""
        error = RuntimeError("service unavailable")
        result = classifier.classify(error, context={"status_code": 503})
        assert result == ErrorType.TRANSIENT

    def test_classify_http_429_is_transient(
        self, classifier: ErrorClassifier
    ) -> None:
        """HTTP 429 (rate limit) classifies as TRANSIENT."""
        error = RuntimeError("rate limited")
        result = classifier.classify(error, context={"status_code": 429})
        assert result == ErrorType.TRANSIENT

    def test_classify_http_400_is_permanent(
        self, classifier: ErrorClassifier
    ) -> None:
        """HTTP 400 status code in context classifies as PERMANENT."""
        error = RuntimeError("bad request")
        result = classifier.classify(error, context={"status_code": 400})
        assert result == ErrorType.PERMANENT

    def test_classify_http_404_is_permanent(
        self, classifier: ErrorClassifier
    ) -> None:
        """HTTP 404 status code in context classifies as PERMANENT."""
        error = RuntimeError("not found")
        result = classifier.classify(error, context={"status_code": 404})
        assert result == ErrorType.PERMANENT

    def test_classify_no_context_defaults_to_none(
        self, classifier: ErrorClassifier
    ) -> None:
        """classify() with no context argument works without error."""
        error = RuntimeError("something failed")
        # Should not raise; unknown exception defaults to UNKNOWN
        result = classifier.classify(error)
        assert isinstance(result, ErrorType)


# ---------------------------------------------------------------------------
# E1.7-E1.12: Retry policy determination
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    """Retry and escalation policy decisions based on error type."""

    def test_transient_error_should_retry(
        self, classifier: ErrorClassifier
    ) -> None:
        """TRANSIENT error at retry_count=0 produces should_retry=True."""
        policy = classifier.retry_policy(ErrorType.TRANSIENT, retry_count=0)
        assert policy.should_retry is True
        assert policy.max_retries == 3
        assert policy.should_escalate is False

    def test_transient_error_retry_count_exceeded(
        self, classifier: ErrorClassifier
    ) -> None:
        """TRANSIENT error at retry_count=max_retries does not retry."""
        policy = classifier.retry_policy(ErrorType.TRANSIENT, retry_count=3)
        assert policy.should_retry is False

    def test_transient_error_backoff_increases(
        self, classifier: ErrorClassifier
    ) -> None:
        """Backoff increases with retry count for TRANSIENT errors."""
        p0 = classifier.retry_policy(ErrorType.TRANSIENT, retry_count=0)
        p1 = classifier.retry_policy(ErrorType.TRANSIENT, retry_count=1)
        p2 = classifier.retry_policy(ErrorType.TRANSIENT, retry_count=2)
        assert p0.backoff_seconds < p1.backoff_seconds < p2.backoff_seconds

    def test_timeout_error_no_retry_escalates(
        self, classifier: ErrorClassifier
    ) -> None:
        """TIMEOUT error does not retry and escalates."""
        policy = classifier.retry_policy(ErrorType.TIMEOUT, retry_count=0)
        assert policy.should_retry is False
        assert policy.should_escalate is True

    def test_safeguard_pause_no_retry_escalates(
        self, classifier: ErrorClassifier
    ) -> None:
        """SAFEGUARD_PAUSE does not retry and escalates."""
        policy = classifier.retry_policy(
            ErrorType.SAFEGUARD_PAUSE, retry_count=0
        )
        assert policy.should_retry is False
        assert policy.should_escalate is True

    def test_permanent_error_no_retry_escalates(
        self, classifier: ErrorClassifier
    ) -> None:
        """PERMANENT error does not retry and escalates."""
        policy = classifier.retry_policy(ErrorType.PERMANENT, retry_count=0)
        assert policy.should_retry is False
        assert policy.should_escalate is True

    def test_unknown_error_no_retry_escalates(
        self, classifier: ErrorClassifier
    ) -> None:
        """UNKNOWN error does not retry and escalates."""
        policy = classifier.retry_policy(ErrorType.UNKNOWN, retry_count=0)
        assert policy.should_retry is False
        assert policy.should_escalate is True

    def test_retry_policy_returns_dataclass(
        self, classifier: ErrorClassifier
    ) -> None:
        """retry_policy() returns a RetryPolicy dataclass."""
        policy = classifier.retry_policy(ErrorType.TRANSIENT)
        assert isinstance(policy, RetryPolicy)
        assert hasattr(policy, "should_retry")
        assert hasattr(policy, "max_retries")
        assert hasattr(policy, "backoff_seconds")
        assert hasattr(policy, "should_escalate")


# ---------------------------------------------------------------------------
# E1.13-E1.15: Backoff calculation
# ---------------------------------------------------------------------------


class TestBackoffCalculation:
    """Exponential backoff calculations."""

    def test_backoff_retry_0_returns_1(self) -> None:
        """backoff(0, base=2.0) returns 1.0."""
        assert ErrorClassifier.backoff(0, base=2.0) == 1.0

    def test_backoff_retry_1_returns_2(self) -> None:
        """backoff(1, base=2.0) returns 2.0."""
        assert ErrorClassifier.backoff(1, base=2.0) == 2.0

    def test_backoff_retry_2_returns_4(self) -> None:
        """backoff(2, base=2.0) returns 4.0."""
        assert ErrorClassifier.backoff(2, base=2.0) == 4.0

    def test_backoff_high_retry_capped_at_60(self) -> None:
        """backoff(20, base=2.0) is capped at 60.0."""
        result = ErrorClassifier.backoff(20, base=2.0)
        assert result == 60.0

    def test_backoff_exactly_at_cap(self) -> None:
        """backoff result is never greater than 60.0."""
        for i in range(0, 15):
            result = ErrorClassifier.backoff(i)
            assert result <= 60.0

    def test_backoff_custom_base(self) -> None:
        """backoff(1, base=3.0) returns 3.0."""
        result = ErrorClassifier.backoff(1, base=3.0)
        assert result == 3.0


# ---------------------------------------------------------------------------
# E1.16: ErrorType enum values
# ---------------------------------------------------------------------------


class TestErrorTypeEnum:
    """ErrorType enum values."""

    def test_error_type_values(self) -> None:
        """All expected ErrorType variants exist."""
        assert ErrorType.TRANSIENT == "transient"
        assert ErrorType.PERMANENT == "permanent"
        assert ErrorType.SAFEGUARD_PAUSE == "safeguard"
        assert ErrorType.TIMEOUT == "timeout"
        assert ErrorType.UNKNOWN == "unknown"

    def test_error_type_is_string_enum(self) -> None:
        """ErrorType is a str-based enum (can be compared to strings)."""
        assert ErrorType.TRANSIENT == "transient"

    def test_error_type_all_variants_present(self) -> None:
        """All five ErrorType variants are accessible."""
        variants = {e.value for e in ErrorType}
        assert variants == {
            "transient", "permanent", "safeguard", "timeout", "unknown"
        }
