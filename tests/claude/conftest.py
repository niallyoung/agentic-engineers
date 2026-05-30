"""Pytest conftest for claude tests."""

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def skills_root() -> Path:
    """Fixture providing path to skills root directory."""
    return Path.home() / ".claude" / "skills"


@pytest.fixture(scope="session")
def test_skills_list() -> list:
    """Fixture providing list of expected test skills."""
    return [
        "ab-testing",
        "agent-creator",
        "cicd-monitor",
        "consistency-checker",
        "cost-aggregation",
        "file-sync",
        "metrics-etl",
        "model-engineer",
        "model-selection",
        "protocol-validator",
        "queue-management",
        "repo-init",
        "skill-creator",
        "spec-management",
        "spec-validator",
        "tokenadvisor",
        "usage-tracking",
        "voice-notify",
        "workflow-review",
    ]
