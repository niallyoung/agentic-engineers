"""
Pytest configuration and fixtures for orchestrator skill tests.
"""

import pytest


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
