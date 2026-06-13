"""
Tests for src/orchestration/memory/directory_setup.py (coverage gaps) and
src/orchestration/memory/session_manager.py (coverage gaps).

Extends coverage for:
- directory_setup: error paths, cleanup_session_memory(), get_memory_stats()
- session_manager: all uncovered methods and error paths

Coverage targets:
  directory_setup.py  57% → 90%+
  session_manager.py  46% → 90%+
"""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.orchestration.memory.directory_setup import (
    setup_session_memory,
    get_session_memory_dir,
    get_agentic_engineers_home,
    initialize_memory_index,
    cleanup_session_memory,
    get_memory_stats,
)
from src.orchestration.memory.session_manager import SessionMemoryManager


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Redirect Path.home() to a temporary directory."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    return fake_home


# ===========================================================================
# TestDirectorySetup (gap coverage)
# ===========================================================================

class TestDirectorySetupErrors:
    """Tests for error paths in directory_setup module."""

    def test_setup_session_memory_raises_on_oserror(self, temp_home):
        """setup_session_memory should propagate OSError from mkdir."""
        with patch("pathlib.Path.mkdir", side_effect=OSError("permission denied")):
            with pytest.raises(OSError):
                setup_session_memory("test-session-err")

    def test_initialize_memory_index_raises_on_ioerror(self, temp_home):
        """initialize_memory_index should propagate IOError on write failure."""
        session_id = "test-session-io-err"
        # Create the memory directory first
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        with patch("builtins.open", side_effect=IOError("no space left")):
            with pytest.raises(IOError):
                initialize_memory_index(session_id)


class TestCleanupSessionMemory:
    """Tests for cleanup_session_memory()."""

    def test_cleanup_nonexistent_returns_false(self, temp_home):
        """cleanup of non-existent session should return False."""
        result = cleanup_session_memory("nonexistent-session")
        assert result is False

    def test_cleanup_archive_moves_memory_dir(self, temp_home):
        """cleanup with archive=True should move memory to archive dir."""
        session_id = "test-session-cleanup-001"
        # Set up memory structure
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "data.json").write_text('{"test": 1}')

        result = cleanup_session_memory(session_id, archive=True)
        assert result is True
        # Memory dir should no longer be in original location
        assert not memory_dir.exists()

    def test_cleanup_delete_removes_memory_dir(self, temp_home):
        """cleanup with archive=False should delete memory directory."""
        session_id = "test-session-cleanup-002"
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "data.json").write_text('{"test": 1}')

        result = cleanup_session_memory(session_id, archive=False)
        assert result is True
        assert not memory_dir.exists()

    def test_cleanup_returns_false_on_exception(self, temp_home):
        """cleanup should return False when an exception occurs."""
        session_id = "test-session-cleanup-003"
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        with patch("shutil.move", side_effect=Exception("move failed")):
            result = cleanup_session_memory(session_id, archive=True)
        assert result is False


class TestGetMemoryStats:
    """Tests for get_memory_stats()."""

    def test_stats_for_nonexistent_session(self, temp_home):
        """stats for non-existent session should have exists=False."""
        stats = get_memory_stats("nonexistent-session")
        assert stats["exists"] is False
        assert stats["session_id"] == "nonexistent-session"

    def test_stats_for_existing_empty_session(self, temp_home):
        """stats for existing session with no files should return zero counts."""
        session_id = "test-session-stats-001"
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        # Create subdirs but no files
        for sub in ["delegates", "handbacks", "logs", "thinking", "metrics"]:
            (memory_dir / sub).mkdir(parents=True, exist_ok=True)

        stats = get_memory_stats(session_id)
        assert stats["exists"] is True
        assert stats["delegates_count"] == 0
        assert stats["handbacks_count"] == 0
        assert stats["logs_count"] == 0

    def test_stats_counts_yaml_files_in_delegates(self, temp_home):
        """stats should count .yaml files in delegates dir."""
        session_id = "test-session-stats-002"
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        delegates_dir = memory_dir / "delegates"
        delegates_dir.mkdir(parents=True, exist_ok=True)
        (delegates_dir / "task-001.yaml").write_text("data: 1")
        (delegates_dir / "task-002.yaml").write_text("data: 2")
        # Create other needed subdirs
        for sub in ["handbacks", "logs", "thinking", "metrics"]:
            (memory_dir / sub).mkdir(parents=True, exist_ok=True)

        stats = get_memory_stats(session_id)
        assert stats["delegates_count"] == 2

    def test_stats_counts_log_files(self, temp_home):
        """stats should count .log files in logs dir."""
        session_id = "test-session-stats-003"
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        logs_dir = memory_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "agent.log").write_text("log content")
        for sub in ["delegates", "handbacks", "thinking", "metrics"]:
            (memory_dir / sub).mkdir(parents=True, exist_ok=True)

        stats = get_memory_stats(session_id)
        assert stats["logs_count"] == 1

    def test_stats_returns_memory_dir_path(self, temp_home):
        """stats should include the memory dir path."""
        session_id = "test-session-stats-004"
        memory_dir = temp_home / ".agentic-engineers" / session_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        for sub in ["delegates", "handbacks", "logs", "thinking", "metrics"]:
            (memory_dir / sub).mkdir(parents=True, exist_ok=True)

        stats = get_memory_stats(session_id)
        assert "memory_dir" in stats
        assert session_id in stats["memory_dir"]


# ===========================================================================
# TestSessionMemoryManagerGaps (uncovered methods)
# ===========================================================================

class TestSessionMemoryManagerCollectEvent:
    """Tests for SessionMemoryManager.collect_memory_event()."""

    def test_collect_event_returns_false_when_not_initialized(self):
        """collect_memory_event should return False before initialize()."""
        mgr = SessionMemoryManager("test-uninitialized")
        result = mgr.collect_memory_event("delegate", {"data": 1})
        assert result is False

    def test_collect_event_returns_true_when_initialized(self, temp_home):
        """collect_memory_event should return True after successful init."""
        mgr = SessionMemoryManager("test-event-collect")
        mgr.initialize()
        result = mgr.collect_memory_event("delegate", {"task_id": "t-001"})
        assert result is True

    def test_collect_event_returns_false_on_exception(self, temp_home):
        """collect_memory_event should return False when exception occurs."""
        mgr = SessionMemoryManager("test-event-exception")
        mgr.initialize()
        # Force exception in the method by corrupting the aggregator
        mgr.aggregator = None
        result = mgr.collect_memory_event("delegate", {})
        assert result is False


class TestSessionMemoryManagerAggregateMemory:
    """Tests for SessionMemoryManager.aggregate_memory()."""

    def test_aggregate_returns_empty_when_not_initialized(self):
        """aggregate_memory should return {} before initialize()."""
        mgr = SessionMemoryManager("test-agg-uninit")
        result = mgr.aggregate_memory()
        assert result == {}

    def test_aggregate_returns_empty_on_exception(self, temp_home):
        """aggregate_memory should return {} when aggregation fails."""
        mgr = SessionMemoryManager("test-agg-exception")
        mgr.initialize()
        # Force exception by breaking aggregator
        with patch.object(mgr.aggregator, "aggregate_all", side_effect=Exception("fail")):
            result = mgr.aggregate_memory()
        assert result == {}


class TestSessionMemoryManagerGenerateSummary:
    """Tests for SessionMemoryManager.generate_summary()."""

    def test_generate_summary_returns_empty_when_not_initialized(self):
        """generate_summary should return '' before initialize()."""
        mgr = SessionMemoryManager("test-summary-uninit")
        result = mgr.generate_summary()
        assert result == ""

    def test_generate_summary_returns_markdown(self, temp_home):
        """generate_summary should return a markdown string after init."""
        mgr = SessionMemoryManager("test-summary-ok")
        mgr.initialize()
        summary = mgr.generate_summary()
        assert isinstance(summary, str)
        assert "Session" in summary or "session" in summary

    def test_generate_summary_includes_session_id(self, temp_home):
        """generate_summary should include the session ID."""
        session_id = "test-session-summary-id"
        mgr = SessionMemoryManager(session_id)
        mgr.initialize()
        summary = mgr.generate_summary()
        assert session_id in summary


class TestSessionMemoryManagerExportSummary:
    """Tests for SessionMemoryManager.export_summary()."""

    def test_export_summary_returns_none_when_not_initialized(self):
        """export_summary should return None before initialize()."""
        mgr = SessionMemoryManager("test-export-uninit")
        result = mgr.export_summary()
        assert result is None

    def test_export_summary_creates_file(self, temp_home):
        """export_summary should write summary.md to memory directory."""
        mgr = SessionMemoryManager("test-export-ok")
        mgr.initialize()
        path = mgr.export_summary()
        assert path is not None
        assert path.exists()
        assert path.name == "summary.md"

    def test_export_summary_returns_none_on_ioerror(self, temp_home):
        """export_summary should return None when file write fails."""
        mgr = SessionMemoryManager("test-export-ioerr")
        mgr.initialize()
        with patch("builtins.open", side_effect=IOError("no space")):
            result = mgr.export_summary()
        assert result is None


class TestSessionMemoryManagerGetDelegates:
    """Tests for SessionMemoryManager.get_delegates()."""

    def test_get_delegates_returns_empty_when_not_initialized(self):
        """get_delegates should return [] before initialize()."""
        mgr = SessionMemoryManager("test-delegates-uninit")
        result = mgr.get_delegates()
        assert result == []

    def test_get_delegates_returns_list_after_init(self, temp_home):
        """get_delegates should return a list after init."""
        mgr = SessionMemoryManager("test-delegates-ok")
        mgr.initialize()
        result = mgr.get_delegates()
        assert isinstance(result, list)

    def test_get_delegates_filters_by_role(self, temp_home):
        """get_delegates with role should filter by that role."""
        mgr = SessionMemoryManager("test-delegates-filter")
        mgr.initialize()
        # Seed some delegates
        mgr.aggregator.index["delegates"] = [
            {"role": "Engineer", "task_id": "t-001"},
            {"role": "Orchestrator", "task_id": "t-002"},
            {"role": "Engineer", "task_id": "t-003"},
        ]
        result = mgr.get_delegates(role="Engineer")
        assert len(result) == 2
        assert all(d["role"] == "Engineer" for d in result)


class TestSessionMemoryManagerGetHandbacks:
    """Tests for SessionMemoryManager.get_handbacks()."""

    def test_get_handbacks_returns_empty_when_not_initialized(self):
        """get_handbacks should return [] before initialize()."""
        mgr = SessionMemoryManager("test-handbacks-uninit")
        result = mgr.get_handbacks()
        assert result == []

    def test_get_handbacks_returns_list_after_init(self, temp_home):
        """get_handbacks should return a list after init."""
        mgr = SessionMemoryManager("test-handbacks-ok")
        mgr.initialize()
        result = mgr.get_handbacks()
        assert isinstance(result, list)

    def test_get_handbacks_filters_by_status(self, temp_home):
        """get_handbacks with status should filter by that status."""
        mgr = SessionMemoryManager("test-handbacks-filter")
        mgr.initialize()
        mgr.aggregator.index["handbacks"] = [
            {"status": "success", "task_id": "t-001"},
            {"status": "failure", "task_id": "t-002"},
            {"status": "success", "task_id": "t-003"},
        ]
        result = mgr.get_handbacks(status="complete")
        assert len(result) == 2
        assert all(h["status"] == "complete" for h in result)


class TestSessionMemoryManagerGetMetrics:
    """Tests for SessionMemoryManager.get_metrics()."""

    def test_get_metrics_returns_empty_when_not_initialized(self):
        """get_metrics should return {} before initialize()."""
        mgr = SessionMemoryManager("test-metrics-uninit")
        result = mgr.get_metrics()
        assert result == {}

    def test_get_metrics_returns_dict_after_init(self, temp_home):
        """get_metrics should return dict after init."""
        mgr = SessionMemoryManager("test-metrics-ok")
        mgr.initialize()
        result = mgr.get_metrics()
        assert isinstance(result, dict)


class TestSessionMemoryManagerQueryMethods:
    """Tests for query_by_task_id() and query_by_role()."""

    def test_query_by_task_id_returns_empty_when_not_initialized(self):
        """query_by_task_id should return {} before initialize()."""
        mgr = SessionMemoryManager("test-query-uninit")
        result = mgr.query_by_task_id("t-001")
        assert result == {}

    def test_query_by_task_id_delegates_to_aggregator(self, temp_home):
        """query_by_task_id should delegate to aggregator.query_by_task_id()."""
        mgr = SessionMemoryManager("test-query-task")
        mgr.initialize()
        with patch.object(mgr.aggregator, "query_by_task_id", return_value={"found": True}) as mock_q:
            result = mgr.query_by_task_id("t-001")
        mock_q.assert_called_once_with("t-001")
        assert result == {"found": True}

    def test_query_by_role_returns_empty_when_not_initialized(self):
        """query_by_role should return {} before initialize()."""
        mgr = SessionMemoryManager("test-role-uninit")
        result = mgr.query_by_role("Engineer")
        assert result == {}

    def test_query_by_role_delegates_to_aggregator(self, temp_home):
        """query_by_role should delegate to aggregator.query_by_role()."""
        mgr = SessionMemoryManager("test-role-ok")
        mgr.initialize()
        with patch.object(mgr.aggregator, "query_by_role", return_value={"count": 3}) as mock_q:
            result = mgr.query_by_role("Engineer")
        mock_q.assert_called_once_with("Engineer")
        assert result == {"count": 3}


class TestSessionMemoryManagerInitializeError:
    """Tests for SessionMemoryManager.initialize() error path."""

    def test_initialize_returns_failure_on_exception(self, temp_home):
        """initialize() should return success=False on error."""
        session_id = "test-init-error"
        mgr = SessionMemoryManager(session_id)

        with patch(
            "src.orchestration.memory.session_manager.setup_session_memory",
            side_effect=OSError("disk full"),
        ):
            result = mgr.initialize()

        assert result["success"] is False
        assert result["session_id"] == session_id
        assert "error" in result
