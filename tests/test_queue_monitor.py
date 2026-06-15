"""
Tests for scripts/queue-monitor.py

Targets: QueueMonitor — curses TUI for monitoring DELEGATE/HANDBACK queue state.

Coverage target: queue display, polling, key handling, graceful degradation for
                 missing queue, non-tty environment.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib.util

# Import via path injection — queue-monitor uses hyphens (not a Python package)
_REPO_ROOT = Path(__file__).resolve().parents[0].parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


class TestQueueMonitorImport:
    """Tests for queue-monitor.py module import and basic functionality."""

    def test_queue_monitor_exists(self):
        """queue-monitor.py should exist in scripts directory."""
        monitor_path = _REPO_ROOT / "scripts" / "queue-monitor.py"
        assert monitor_path.exists(), f"queue-monitor.py not found at {monitor_path}"

    def test_queue_monitor_imports_without_error(self):
        """queue-monitor.py should import without raising an error."""
        monitor_path = _REPO_ROOT / "scripts" / "queue-monitor.py"
        spec = importlib.util.spec_from_file_location("queue_monitor", monitor_path)
        module = importlib.util.module_from_spec(spec)

        # Should not raise any import errors
        spec.loader.exec_module(module)
        assert hasattr(module, "QueueMonitor"), "QueueMonitor class not found in module"

    def test_queue_monitor_has_main(self):
        """queue-monitor.py should have a main() function."""
        monitor_path = _REPO_ROOT / "scripts" / "queue-monitor.py"
        spec = importlib.util.spec_from_file_location("queue_monitor", monitor_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "main"), "main() function not found in module"


class TestQueueMonitorFunctionality:
    """Tests for QueueMonitor class functionality."""

    def test_queue_monitor_initialization(self, tmp_path):
        """QueueMonitor should initialize with harness and session."""
        monitor_path = _REPO_ROOT / "scripts" / "queue-monitor.py"
        spec = importlib.util.spec_from_file_location("queue_monitor", monitor_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        monitor = module.QueueMonitor(harness="test", session="test-session")
        assert monitor.harness == "test"
        assert monitor.session == "test-session"

    def test_queue_monitor_poll_queue_missing_path(self, tmp_path):
        """poll_queue should gracefully handle missing queue path."""
        monitor_path = _REPO_ROOT / "scripts" / "queue-monitor.py"
        spec = importlib.util.spec_from_file_location("queue_monitor", monitor_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        monitor = module.QueueMonitor(harness="test", session="test-session")
        counts = monitor.poll_queue()

        # Should return all zeros for missing queue
        assert counts["incoming"] == 0
        assert counts["processing"] == 0
        assert counts["done"] == 0
        assert counts["failed"] == 0

    def test_queue_monitor_format_elapsed(self, tmp_path):
        """format_elapsed should format seconds as HH:MM:SS."""
        monitor_path = _REPO_ROOT / "scripts" / "queue-monitor.py"
        spec = importlib.util.spec_from_file_location("queue_monitor", monitor_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        monitor = module.QueueMonitor()

        # Test various time values
        assert monitor.format_elapsed(0) == "00:00:00"
        assert monitor.format_elapsed(61) == "00:01:01"
        assert monitor.format_elapsed(3661) == "01:01:01"  # 1h 1m 1s
