"""
Regression tests for Claude Code harness TokenBudgetManager.

Tests for per-agent token budget tracking, enforcement limits,
and concurrent access safety.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.harnesses.claude_code.token_budget import (
    AGENT_ALLOCATIONS,
    SESSION_BUDGET_DEFAULT,
    BudgetStatus,
    TokenBudgetManager,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager() -> TokenBudgetManager:
    """Fresh TokenBudgetManager instance for each test."""
    return TokenBudgetManager(session_budget=200_000)


@pytest.fixture
def manager_custom() -> TokenBudgetManager:
    """TokenBudgetManager with custom allocations."""
    allocations = {
        "orchestrator": 0.50,
        "engineer": 0.30,
        "lead-engineer": 0.20,
    }
    return TokenBudgetManager(session_budget=100_000, allocations=allocations)


# ---------------------------------------------------------------------------
# D2.1-D2.3: Basic usage recording and budget tracking
# ---------------------------------------------------------------------------


class TestTokenRecording:
    """Token usage recording and status tracking."""

    def test_record_usage_within_budget(self, manager: TokenBudgetManager) -> None:
        """Recording usage within allocated budget returns ok status."""
        status = manager.record_usage("orchestrator", 50_000)
        assert isinstance(status, BudgetStatus)
        assert status.agent == "orchestrator"
        assert status.used == 50_000
        assert status.allocated == 120_000  # 0.60 * 200_000
        assert status.warn is False
        assert status.blocked is False

    def test_record_usage_accumulates(self, manager: TokenBudgetManager) -> None:
        """Multiple record_usage calls accumulate token count."""
        manager.record_usage("engineer", 5_000)
        status = manager.record_usage("engineer", 8_000)
        assert status.used == 13_000  # 5_000 + 8_000

    def test_record_usage_triggers_warn_at_threshold(
        self, manager: TokenBudgetManager
    ) -> None:
        """Recording usage at 85% allocation triggers warn flag."""
        # engineer allocation: 0.18 * 200_000 = 36_000
        # 85% of 36_000 = 30_600
        status = manager.record_usage("engineer", 30_600)
        assert status.warn is True
        assert status.blocked is False

    def test_record_usage_blocks_at_limit(
        self, manager: TokenBudgetManager
    ) -> None:
        """Recording usage at or over 100% allocation triggers blocked flag."""
        # engineer allocation: 0.18 * 200_000 = 36_000
        status = manager.record_usage("engineer", 36_000)
        assert status.blocked is True
        assert status.warn is True

    def test_record_usage_blocks_over_limit(
        self, manager: TokenBudgetManager
    ) -> None:
        """Recording usage over 100% allocation triggers blocked flag."""
        # engineer allocation: 0.18 * 200_000 = 36_000
        status = manager.record_usage("engineer", 40_000)
        assert status.blocked is True
        assert status.percent > 1.0

    def test_record_usage_unknown_agent_initializes(
        self, manager: TokenBudgetManager
    ) -> None:
        """Recording usage for unknown agent initializes with zero allocation."""
        status = manager.record_usage("unknown-agent", 1_000)
        assert status.agent == "unknown-agent"
        assert status.allocated == 0  # No allocation for unknown agent
        assert status.used == 1_000


# ---------------------------------------------------------------------------
# D2.4: Budget status reporting
# ---------------------------------------------------------------------------


class TestBudgetStatusReporting:
    """Budget status query and reporting."""

    def test_check_budget_returns_correct_percent(
        self, manager: TokenBudgetManager
    ) -> None:
        """check_budget() returns utilization percentage."""
        manager.record_usage("orchestrator", 60_000)
        status = manager.check_budget("orchestrator")
        # orchestrator allocation: 0.60 * 200_000 = 120_000
        # used: 60_000, so percent: 60_000 / 120_000 = 0.5
        assert status.percent == 0.5

    def test_check_budget_without_recording(
        self, manager: TokenBudgetManager
    ) -> None:
        """check_budget() works without prior record_usage calls."""
        status = manager.check_budget("lead-engineer")
        # lead-engineer allocation: 0.05 * 200_000 = 10_000
        assert status.used == 0
        assert status.allocated == 10_000
        assert status.percent == 0.0
        assert status.warn is False
        assert status.blocked is False

    def test_budget_status_dataclass_fields(self) -> None:
        """BudgetStatus has all expected fields."""
        status = BudgetStatus(
            agent="test", used=100, allocated=1000, percent=0.1, warn=False,
            blocked=False
        )
        assert status.agent == "test"
        assert status.used == 100
        assert status.allocated == 1000
        assert status.percent == 0.1
        assert status.warn is False
        assert status.blocked is False


# ---------------------------------------------------------------------------
# D2.5: Session summary and aggregate reporting
# ---------------------------------------------------------------------------


class TestSessionSummary:
    """Session-level budget aggregation and reporting."""

    def test_session_summary_totals(self, manager: TokenBudgetManager) -> None:
        """session_summary() aggregates per-agent usage into totals."""
        manager.record_usage("orchestrator", 50_000)
        manager.record_usage("engineer", 10_000)
        manager.record_usage("lead-engineer", 5_000)

        summary = manager.session_summary()
        assert summary["total_used"] == 65_000
        assert summary["total_allocated"] == 200_000
        assert summary["utilization_percent"] == 32.5

    def test_session_summary_per_agent_breakdown(
        self, manager: TokenBudgetManager
    ) -> None:
        """session_summary() includes per-agent breakdown."""
        manager.record_usage("orchestrator", 50_000)
        manager.record_usage("engineer", 10_000)

        summary = manager.session_summary()
        assert "per_agent" in summary
        assert "orchestrator" in summary["per_agent"]
        assert "engineer" in summary["per_agent"]

        orch_info = summary["per_agent"]["orchestrator"]
        assert orch_info["used"] == 50_000
        assert orch_info["allocated"] == 120_000

    def test_session_summary_empty_state(self, manager: TokenBudgetManager) -> None:
        """session_summary() with no recordings shows 0% utilization."""
        summary = manager.session_summary()
        assert summary["total_used"] == 0
        assert summary["utilization_percent"] == 0.0

    def test_session_summary_after_partial_recording(
        self, manager: TokenBudgetManager
    ) -> None:
        """session_summary() reflects all recorded agents."""
        manager.record_usage("orchestrator", 10_000)
        summary = manager.session_summary()
        # All agents should be in per_agent, even those with zero usage
        assert "engineer" in summary["per_agent"]


# ---------------------------------------------------------------------------
# D2.6: Reset functionality
# ---------------------------------------------------------------------------


class TestReset:
    """Session reset and state clearing."""

    def test_reset_clears_all(self, manager: TokenBudgetManager) -> None:
        """reset() clears all recorded usage."""
        manager.record_usage("orchestrator", 50_000)
        manager.record_usage("engineer", 10_000)
        manager.reset()

        status = manager.check_budget("orchestrator")
        assert status.used == 0
        assert status.percent == 0.0

    def test_reset_multiple_times(self, manager: TokenBudgetManager) -> None:
        """Multiple reset() calls work idempotently."""
        manager.record_usage("orchestrator", 50_000)
        manager.reset()
        manager.reset()  # Second reset should be safe

        status = manager.check_budget("orchestrator")
        assert status.used == 0

    def test_session_summary_after_reset(self, manager: TokenBudgetManager) -> None:
        """session_summary() after reset() shows no usage."""
        manager.record_usage("orchestrator", 50_000)
        manager.reset()

        summary = manager.session_summary()
        assert summary["total_used"] == 0
        assert summary["utilization_percent"] == 0.0


# ---------------------------------------------------------------------------
# D2.7: Thread safety for concurrent operations
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Concurrent access safety."""

    def test_thread_safety_concurrent_record_usage(
        self, manager: TokenBudgetManager
    ) -> None:
        """concurrent record_usage calls are safe (no race conditions)."""
        agent = "orchestrator"
        allocation = AGENT_ALLOCATIONS[agent] * 200_000

        def record_batch(tokens: int) -> None:
            for _ in range(100):
                manager.record_usage(agent, tokens)

        # Launch 5 threads, each recording 100 times
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(record_batch, 10) for _ in range(5)
            ]
            for future in futures:
                future.result()

        # Total: 5 threads * 100 iterations * 10 tokens = 5_000
        status = manager.check_budget(agent)
        assert status.used == 5_000
        # Verify we're still within budget
        assert status.blocked is False or status.percent <= 1.0

    def test_thread_safety_concurrent_check_and_record(
        self, manager: TokenBudgetManager
    ) -> None:
        """concurrent check_budget and record_usage calls are safe."""
        results = []
        lock = threading.Lock()

        def mixed_operations() -> None:
            for _ in range(50):
                manager.record_usage("engineer", 100)
                status = manager.check_budget("engineer")
                with lock:
                    results.append(status.used)
                time.sleep(0.001)  # Yield to other threads

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(mixed_operations) for _ in range(3)
            ]
            for future in futures:
                future.result()

        # Verify consistency (last check should match total)
        final_status = manager.check_budget("engineer")
        assert final_status.used == 3 * 50 * 100  # 15_000 tokens total

    def test_thread_safety_reset_during_recording(
        self, manager: TokenBudgetManager
    ) -> None:
        """reset() during concurrent recording is safe."""
        def record_continuously() -> None:
            for _ in range(100):
                manager.record_usage("orchestrator", 10)
                time.sleep(0.001)

        recording_thread = threading.Thread(target=record_continuously)
        recording_thread.start()

        time.sleep(0.05)  # Let some recording happen
        manager.reset()  # Reset while recording
        recording_thread.join()

        # Should be safe; final state should be consistent
        status = manager.check_budget("orchestrator")
        assert isinstance(status, BudgetStatus)


# ---------------------------------------------------------------------------
# D2.8: Custom allocations
# ---------------------------------------------------------------------------


class TestCustomAllocations:
    """Custom agent allocation overrides."""

    def test_custom_allocations_respected(
        self, manager_custom: TokenBudgetManager
    ) -> None:
        """Custom allocations override defaults."""
        # orchestrator: 50% of 100_000 = 50_000
        # engineer: 30% of 100_000 = 30_000
        # lead-engineer: 20% of 100_000 = 20_000

        orch_status = manager_custom.check_budget("orchestrator")
        assert orch_status.allocated == 50_000

        eng_status = manager_custom.check_budget("engineer")
        assert eng_status.allocated == 30_000

        lead_status = manager_custom.check_budget("lead-engineer")
        assert lead_status.allocated == 20_000

    def test_custom_allocations_in_summary(
        self, manager_custom: TokenBudgetManager
    ) -> None:
        """session_summary() reflects custom allocations."""
        manager_custom.record_usage("orchestrator", 25_000)
        summary = manager_custom.session_summary()

        assert summary["per_agent"]["orchestrator"]["allocated"] == 50_000
        assert summary["per_agent"]["orchestrator"]["used"] == 25_000

    def test_default_allocations_match_constant(self) -> None:
        """Default manager uses AGENT_ALLOCATIONS constant."""
        manager = TokenBudgetManager()
        summary = manager.session_summary()

        # Verify all default agents are present
        for agent in AGENT_ALLOCATIONS:
            assert agent in summary["per_agent"]

    def test_session_budget_parameter(self) -> None:
        """Custom session_budget parameter is respected."""
        manager = TokenBudgetManager(session_budget=500_000)
        summary = manager.session_summary()

        assert summary["total_allocated"] == 500_000
        # orchestrator: 0.60 * 500_000 = 300_000
        assert (
            summary["per_agent"]["orchestrator"]["allocated"] == 300_000
        )
