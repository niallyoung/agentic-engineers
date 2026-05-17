"""
tests/conftest.py — Shared pytest fixtures and utilities for agentic-engineers tests.

Provides common DELEGATE/HANDBACK factory functions and fixtures to eliminate
duplication across test modules. Import via pytest fixture injection or directly.

Usage (fixture injection):
    def test_something(delegate_block, handback_block):
        ...

Usage (direct import):
    from tests.conftest import make_delegate, make_handback
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Factory functions (importable directly, not just as fixtures)
# ---------------------------------------------------------------------------

def make_delegate(
    task_id: str = "2026-01-01-test-task",
    role: str = "engineer",
    effort: str = "medium",
    model: str = "claude-haiku-4-5",
    scope: str = "Test scope",
    context: Optional[list] = None,
    plan: Optional[list] = None,
    success_criteria: Optional[list] = None,
    **overrides,
) -> Dict:
    """
    Create a minimal valid DELEGATE block for testing.

    All parameters have sensible defaults. Use ``**overrides`` to set any
    additional or non-default fields.

    Example::

        make_delegate(task_id="my-task", role="senior_engineer", effort="high")
        make_delegate(is_security_scoped=True)
    """
    block = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": role,
        "model": model,
        "effort": effort,
        "scope": scope,
        "context": context if context is not None else ["File: test.py"],
        "plan": plan if plan is not None else ["1. Write test", "2. Verify"],
        "success_criteria": success_criteria if success_criteria is not None else ["Tests pass"],
    }
    block.update(overrides)
    return block


def make_handback(
    task_id: str = "2026-01-01-test-task",
    status: str = "complete",
    quality_score: int = 90,
    tokens_in: int = 1000,
    tokens_out: int = 500,
    cost_usd: float = 0.05,
    effort_actual: float = 0.5,
    **overrides,
) -> Dict:
    """
    Create a minimal valid HANDBACK block for testing.

    All parameters have sensible defaults. Use ``**overrides`` to set any
    additional or non-default fields.

    Example::

        make_handback(quality_score=75, status="complete")
        make_handback(task_id="my-task", tokens_in=2000, tokens_out=800)
    """
    block = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": status,
        "quality_score": quality_score,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "effort_actual": effort_actual,
        "deliverables": [],
        "tests": {"passed": 10, "failed": 0, "coverage": 95.0},
    }
    block.update(overrides)
    return block


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def delegate_block() -> Dict:
    """Minimal valid DELEGATE block."""
    return make_delegate()


@pytest.fixture
def handback_block() -> Dict:
    """Minimal valid HANDBACK block."""
    return make_handback()


@pytest.fixture
def high_quality_handback() -> Dict:
    """HANDBACK with high quality score (90+), triggers PROCEED."""
    return make_handback(quality_score=95)


@pytest.fixture
def low_quality_handback() -> Dict:
    """HANDBACK with low quality score (<60), triggers ESCALATE."""
    return make_handback(quality_score=45)


@pytest.fixture
def gray_zone_handback() -> Dict:
    """HANDBACK with gray-zone quality score (70-79), triggers MANUAL_REVIEW."""
    return make_handback(quality_score=74)


@pytest.fixture
def tmp_queue(tmp_path: Path) -> Path:
    """
    Temporary queue directory with incoming/processing/done subdirectories.

    Returns the base queue path. Subdirectories are pre-created.
    """
    for subdir in ("incoming", "processing", "done"):
        (tmp_path / subdir).mkdir(parents=True)
    return tmp_path
