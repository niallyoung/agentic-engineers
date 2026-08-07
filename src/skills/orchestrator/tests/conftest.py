"""
Pytest configuration and fixtures for orchestrator skill tests.
"""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(autouse=True)
def isolate_feedback_storage():
    """Run each test in an isolated working directory.

    ``FeedbackLoop`` persists skill feedback to repo-relative paths
    (``artifacts/metrics/skill-feedback/<skill>.jsonl`` and
    ``metrics/feedback_store.jsonl``). Without isolation these files
    accumulate across tests and runs, leaking state — e.g. enough
    queue-management feedback persists that
    ``test_route_skill_feedback_below_threshold`` wrongly crosses the
    spawn threshold. Chdir'ing into a fresh tempdir per test gives each
    test a clean, throwaway storage root.
    """
    prev_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            yield
        finally:
            os.chdir(prev_cwd)
