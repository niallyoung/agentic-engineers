"""Pytest conftest for claude tests."""

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def skills_root() -> Path:
    """Fixture providing path to skills root directory."""
    return Path.home() / ".claude" / "skills"


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
        "skill-creator",
        "spec-management",
        "spec-validator",
        "usage-tracking",
        "voice-notify",
        "workflow-review",
    ]
