"""Pytest conftest for claude tests."""

import pytest
from pathlib import Path

# Repo root computed from this file's location:
# tests/claude/conftest.py -> parents[2] == repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def skills_root() -> Path:
    """Fixture providing path to the claude skills root directory.

    Points at the repository's rendered claude harness output
    ``dist/claude/skills``. This directory is produced by ``make render-claude``
    (a step CI runs *before* the test step) and is deterministic on every
    machine, including a fresh CI runner.

    Previously this read the developer's ``~/.claude/skills``, which is only
    populated by ``make install-claude`` (a step CI never runs). On a clean CI
    runner that directory is empty, so ``discover_skills()`` returned ``[]`` and
    ~22 skill discovery / metadata / render tests failed with ``assert 0 > 0``.
    Reading the rendered ``dist/claude/skills`` instead makes these tests
    hermetic and validates the actual claude-harness render output.
    """
    return REPO_ROOT / "dist" / "claude" / "skills"


@pytest.fixture(scope="session")
def test_skills_list() -> list:
    """Fixture providing list of expected test skills.
    
    Note: 5 skills have been deprecated and moved to archive:
    - ab-testing (deprecated)
    - cicd-monitor (deprecated)
    - repo-init (deprecated)
    - metrics-etl (deprecated)
    - tokenadvisor (deprecated)
    """
    return [
        "agent-creator",
        "consistency-checker",
        "cost-aggregation",
        "file-sync",
        "model-engineer",
        "model-selection",
        "protocol-validator",
        "queue-management",
        "spec-management",
        "spec-validator",
        "usage-tracking",
        "workflow-review",
    ]
