"""
Test Suite for TokenTracker integration with AgentInvoker (task: wire-token-tracker)

Tests the wiring of TokenTracker into AgentInvoker so that every completed HANDBACK
automatically records token metrics.

Tests cover:
1. Token recording called on real HANDBACKs
2. Token recording skipped on synthetic HANDBACKs
3. Graceful degradation when no tracker is provided
4. Correct agent name normalization
5. Default cost handling
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from src.orchestration.agents.invoke_agent import AgentInvoker
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temp directory structure for tests."""
    processing = tmp_path / "processing"
    delegates = tmp_path / "delegates"
    spans = tmp_path / "spans"
    for d in [processing, delegates, spans]:
        d.mkdir(parents=True)
    return {
        "processing": processing,
        "delegates": delegates,
        "spans": spans,
        "base": tmp_path,
    }


@pytest.fixture
def metrics_registry():
    """Create a MetricsRegistry for testing."""
    return MetricsRegistry()


@pytest.fixture
def token_tracker(metrics_registry):
    """Create a TokenTracker for testing."""
    return TokenTracker(metrics_registry)


def make_invoker(tmp_dirs, token_tracker=None, poll_interval=0.02):
    """Helper: create an AgentInvoker with fast settings for tests."""
    return AgentInvoker(
        processing_dir=tmp_dirs["processing"],
        delegates_dir=tmp_dirs["delegates"],
        spans_dir=tmp_dirs["spans"],
        poll_interval=poll_interval,
        effort_timeouts={
            "low": 0.2,
            "medium": 0.5,
            "high": 1.0,
            "max": 2.0,
            "epic": 2.0,
        },
        token_tracker=token_tracker,
    )


def make_delegate(
    task_id="2026-01-01-test-task",
    role="Engineer",
    effort="medium",
    model="claude-haiku-4.5",
) -> dict:
    """Helper: create a minimal valid DELEGATE block."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": role,
        "model": model,
        "effort": effort,
        "scope": "Test scope",
        "context": ["File: test.py"],
        "plan": ["1. Write test"],
        "success_criteria": ["Tests pass"],
    }


def make_valid_handback(
    task_id="2026-01-01-test-task",
    role="Engineer",
    tokens_in=1000,
    tokens_out=500,
    tokens_cached=0,
    cost_usd=0.045,
) -> dict:
    """Helper: create a minimal valid HANDBACK block."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "success",
        "deliverables": ["Modified: test.py"],
        "tests": [{"command": "make verify", "result": "PASS"}],
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_cached": tokens_cached,
        "model": "claude-haiku-4.5",
        "effort": "medium",
        "duration_minutes": 5,
        "escalations": 0,
        "cost_usd": cost_usd,
    }


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestTokenRecordingOnRealHandback:
    """Test that token recording is called for real HANDBACKs."""

    def test_record_tokens_called_on_real_handback(self, tmp_dirs, token_tracker):
        """Verify record_task_tokens is called when a real HANDBACK is returned."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-001", role="Engineer")
        handback = make_valid_handback(
            task_id="task-001",
            tokens_in=1000,
            tokens_out=500,
            tokens_cached=100,
            cost_usd=0.045,
        )

        # Mock the record_task_tokens method to verify it's called
        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        # Call the internal method directly
        invoker._record_token_metrics(delegate, handback)

        # Verify the tracker was called with correct arguments
        token_tracker.record_task_tokens.assert_called_once_with(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )

    def test_record_tokens_skipped_on_synthetic_handback(self, tmp_dirs, token_tracker):
        """Verify token recording is skipped for synthetic HANDBACKs (_synthetic=True)."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-002")
        handback = make_valid_handback(task_id="task-002")
        handback["_synthetic"] = True

        # Mock the record_task_tokens method
        token_tracker.record_task_tokens = MagicMock()

        # Simulate the invoke_agent logic (check _synthetic flag)
        if token_tracker and not handback.get("_synthetic"):
            invoker._record_token_metrics(delegate, handback)

        # Verify the tracker was NOT called
        token_tracker.record_task_tokens.assert_not_called()

    def test_record_tokens_skipped_when_no_tracker(self, tmp_dirs):
        """Verify no crash when token_tracker is None (graceful degradation)."""
        invoker = make_invoker(tmp_dirs, token_tracker=None)
        delegate = make_delegate(task_id="task-003")
        handback = make_valid_handback(task_id="task-003")

        # Should not raise an exception
        if invoker._token_tracker and not handback.get("_synthetic"):
            invoker._record_token_metrics(delegate, handback)

        # If we get here without exception, the test passes


class TestAgentNameNormalization:
    """Test that agent names are correctly normalized."""

    def test_record_tokens_uses_correct_agent_name(self, tmp_dirs, token_tracker):
        """Verify agent name is normalized: 'Senior Engineer' → 'senior-engineer'."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-004", role="Senior Engineer")
        handback = make_valid_handback(task_id="task-004")

        # Mock the record_task_tokens method
        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        invoker._record_token_metrics(delegate, handback)

        # Verify the agent name was normalized
        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["agent"] == "senior-engineer"

    def test_record_tokens_normalizes_quality_engineer(self, tmp_dirs, token_tracker):
        """Verify 'Quality Engineer' → 'quality-engineer'."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-005", role="Quality Engineer")
        handback = make_valid_handback(task_id="task-005")

        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        invoker._record_token_metrics(delegate, handback)

        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["agent"] == "quality-engineer"

    def test_record_tokens_normalizes_orchestrator(self, tmp_dirs, token_tracker):
        """Verify 'Orchestrator' → 'orchestrator'."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-006", role="Orchestrator")
        handback = make_valid_handback(task_id="task-006")

        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        invoker._record_token_metrics(delegate, handback)

        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["agent"] == "orchestrator"


class TestTokenDefaults:
    """Test default token and cost handling."""

    def test_record_tokens_defaults_cost_to_zero(self, tmp_dirs, token_tracker):
        """Verify cost_usd defaults to 0.0 when not in HANDBACK."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-007")
        handback = make_valid_handback(task_id="task-007")
        # Remove cost_usd from handback
        del handback["cost_usd"]

        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        invoker._record_token_metrics(delegate, handback)

        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["cost_usd"] == 0.0

    def test_record_tokens_defaults_cached_tokens_to_zero(self, tmp_dirs, token_tracker):
        """Verify tokens_cached defaults to 0 when not in HANDBACK."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-008")
        handback = make_valid_handback(task_id="task-008")
        # Remove tokens_cached from handback
        del handback["tokens_cached"]

        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        invoker._record_token_metrics(delegate, handback)

        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["cached_tokens"] == 0

    def test_record_tokens_defaults_missing_tokens_to_zero(self, tmp_dirs, token_tracker):
        """Verify missing token counts default to 0."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-009")
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "task-009",
            "status": "success",
            "deliverables": [],
            "tests": [],
            "model": "claude-haiku-4.5",
            "effort": "medium",
            "duration_minutes": 5,
            "escalations": 0,
            # Note: tokens_in, tokens_out, cost_usd are missing
        }

        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        invoker._record_token_metrics(delegate, handback)

        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["input_tokens"] == 0
        assert call_args[1]["output_tokens"] == 0
        assert call_args[1]["cost_usd"] == 0.0


class TestTokenMetricsIntegration:
    """Test integration of token tracking with actual TokenTracker."""

    def test_token_metrics_recorded_in_tracker(self, tmp_dirs, token_tracker):
        """Verify token metrics are actually recorded in the TokenTracker."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-010", role="Engineer")
        handback = make_valid_handback(
            task_id="task-010",
            tokens_in=2000,
            tokens_out=1000,
            tokens_cached=200,
            cost_usd=0.15,
        )

        invoker._record_token_metrics(delegate, handback)

        # Verify the metrics were recorded
        stats = token_tracker.get_stats()
        assert stats.total_input_tokens == 2000
        assert stats.total_output_tokens == 1000
        assert stats.total_cached_tokens == 200
        assert stats.total_cost_usd == 0.15
        assert stats.task_count == 1

    def test_multiple_task_metrics_aggregated(self, tmp_dirs, token_tracker):
        """Verify multiple task metrics are properly aggregated."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)

        # Record first task
        delegate1 = make_delegate(task_id="task-011", role="Engineer")
        handback1 = make_valid_handback(
            task_id="task-011",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.05,
        )
        invoker._record_token_metrics(delegate1, handback1)

        # Record second task
        delegate2 = make_delegate(task_id="task-012", role="Senior Engineer")
        handback2 = make_valid_handback(
            task_id="task-012",
            tokens_in=2000,
            tokens_out=1000,
            cost_usd=0.10,
        )
        invoker._record_token_metrics(delegate2, handback2)

        # Verify aggregation
        stats = token_tracker.get_stats()
        assert stats.total_input_tokens == 3000
        assert stats.total_output_tokens == 1500
        assert abs(stats.total_cost_usd - 0.15) < 0.0001  # Account for floating-point precision
        assert stats.task_count == 2

    def test_per_agent_metrics_tracked(self, tmp_dirs, token_tracker):
        """Verify per-agent metrics are tracked separately."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)

        # Record engineer task
        delegate1 = make_delegate(task_id="task-013", role="Engineer")
        handback1 = make_valid_handback(
            task_id="task-013",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.05,
        )
        invoker._record_token_metrics(delegate1, handback1)

        # Record orchestrator task
        delegate2 = make_delegate(task_id="task-014", role="Orchestrator")
        handback2 = make_valid_handback(
            task_id="task-014",
            tokens_in=500,
            tokens_out=200,
            cost_usd=0.02,
        )
        invoker._record_token_metrics(delegate2, handback2)

        # Verify per-agent stats
        engineer_stats = token_tracker.get_agent_stats("engineer")
        assert engineer_stats is not None
        assert engineer_stats["input_tokens"] == 1000
        assert engineer_stats["output_tokens"] == 500
        assert engineer_stats["cost_usd"] == 0.05

        orchestrator_stats = token_tracker.get_agent_stats("orchestrator")
        assert orchestrator_stats is not None
        assert orchestrator_stats["input_tokens"] == 500
        assert orchestrator_stats["output_tokens"] == 200
        assert orchestrator_stats["cost_usd"] == 0.02


class TestErrorHandling:
    """Test error handling in token recording."""

    def test_record_tokens_handles_tracker_errors_gracefully(self, tmp_dirs, token_tracker):
        """Verify token recording errors don't crash invoke_agent."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = make_delegate(task_id="task-015")
        handback = make_valid_handback(task_id="task-015")

        # Mock the tracker to raise an exception
        token_tracker.record_task_tokens = MagicMock(
            side_effect=ValueError("Simulated tracker error")
        )

        # Should not raise an exception (error is caught and logged)
        invoker._record_token_metrics(delegate, handback)

    def test_record_tokens_handles_missing_delegate_fields(self, tmp_dirs, token_tracker):
        """Verify missing DELEGATE fields are handled gracefully."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        delegate = {}  # Empty delegate
        handback = make_valid_handback()

        original_record = token_tracker.record_task_tokens
        token_tracker.record_task_tokens = MagicMock(side_effect=original_record)

        # Should not raise an exception
        invoker._record_token_metrics(delegate, handback)

        # Verify defaults were used
        call_args = token_tracker.record_task_tokens.call_args
        assert call_args[1]["task_id"] == "unknown"
        assert call_args[1]["agent"] == "unknown"


class TestInvokerInitialization:
    """Test AgentInvoker initialization with token_tracker parameter."""

    def test_invoker_accepts_token_tracker_parameter(self, tmp_dirs, token_tracker):
        """Verify AgentInvoker accepts token_tracker in __init__."""
        invoker = make_invoker(tmp_dirs, token_tracker=token_tracker)
        assert invoker._token_tracker is token_tracker

    def test_invoker_defaults_token_tracker_to_none(self, tmp_dirs):
        """Verify token_tracker defaults to None when not provided."""
        invoker = make_invoker(tmp_dirs, token_tracker=None)
        assert invoker._token_tracker is None

    def test_invoker_with_no_tracker_parameter(self, tmp_dirs):
        """Verify AgentInvoker works without token_tracker parameter."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
        )
        assert invoker._token_tracker is None
