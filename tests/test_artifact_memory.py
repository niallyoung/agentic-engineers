"""Tests for artifact memory store and session memory management."""

import pytest
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

from src.orchestration.memory import (
    ArtifactMemoryStore,
    MemoryIndexBuilder,
    SessionMemoryManager,
    GlobalMemoryManager,
    setup_session_memory,
    get_session_memory_dir,
)


class TestArtifactMemoryStore:
    """Test ArtifactMemoryStore functionality."""

    @pytest.fixture
    def temp_artifact_dir(self):
        """Create temporary artifact directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def store(self, temp_artifact_dir):
        """Create ArtifactMemoryStore instance."""
        return ArtifactMemoryStore(session_id="test-session-123", base_dir=temp_artifact_dir)

    def test_store_initialization(self, store, temp_artifact_dir):
        """Test store initializes memory directory."""
        expected_dir = Path(temp_artifact_dir) / "test-session-123" / "memory"
        assert store.memory_dir == expected_dir
        assert store.memory_dir.exists()

    def test_write_and_read_data(self, store):
        """Test writing and reading data."""
        test_data = {"tokens": 1000, "cost": 5.0, "quality": 95}
        
        path = store.write("test_metrics", test_data)
        assert path.exists()
        
        result = store.read("test_metrics")
        assert result is not None
        assert result["data"] == test_data
        assert result["session_id"] == "test-session-123"

    def test_write_with_subdir(self, store):
        """Test writing data to subdirectory."""
        test_data = {"daily": 1000}
        
        path = store.write("metrics", test_data, subdir="metrics/daily")
        assert path.exists()
        assert path.parent.name == "daily"
        
        result = store.read("metrics", subdir="metrics/daily")
        assert result is not None
        assert result["data"] == test_data

    def test_append_metric(self, store):
        """Test appending metrics to JSONL file."""
        store.append_metric("token_usage", {"tokens": 100}, subdir="metrics")
        store.append_metric("token_usage", {"tokens": 200}, subdir="metrics")
        
        metrics_file = store.memory_dir / "metrics" / "token_usage.jsonl"
        assert metrics_file.exists()
        
        # Verify both entries were written
        lines = metrics_file.read_text().strip().split("\n")
        assert len(lines) == 2
        
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        assert entry1["value"]["tokens"] == 100
        assert entry2["value"]["tokens"] == 200

    def test_list_all_files(self, store):
        """Test listing all memory files."""
        store.write("metrics", {"test": 1}, subdir="metrics")
        store.write("logs", {"log": 1}, subdir="logs")
        store.append_metric("usage", {"val": 1}, subdir="metrics")
        
        all_files = store.list_all()
        assert "metrics" in all_files
        assert "logs" in all_files
        assert len(all_files["metrics"]) == 2  # metrics.json and usage.jsonl

    def test_aggregate_session(self, store):
        """Test aggregating session memory."""
        store.write("metrics", {"test": 1}, subdir="metrics")
        store.write("logs", {"log": 1}, subdir="logs")
        
        aggregate = store.aggregate_session()
        assert aggregate["session_id"] == "test-session-123"
        assert aggregate["file_count"] == 2
        assert aggregate["total_size_bytes"] > 0
        assert "memory_by_type" in aggregate

    def test_write_index(self, store):
        """Test writing session index."""
        store.write("metrics", {"test": 1})
        
        index_path = store.write_index()
        assert index_path.exists()
        
        with open(index_path) as f:
            index = json.load(f)
        
        assert index["session_id"] == "test-session-123"
        assert "memory_summary" in index
        assert "delegates" in index
        assert "handbacks" in index

    def test_multiple_writes_to_same_key(self, store):
        """Test that multiple writes to same key create versioned files."""
        store.write("metrics", {"v1": 1})
        store.write("metrics", {"v2": 2})
        
        files = list((store.memory_dir).glob("metrics*.json"))
        assert len(files) == 2


class TestMemoryIndexBuilder:
    """Test MemoryIndexBuilder functionality."""

    @pytest.fixture
    def temp_artifact_dir(self):
        """Create temporary artifact directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def builder(self, temp_artifact_dir):
        """Create builder instance."""
        return MemoryIndexBuilder(base_dir=temp_artifact_dir)

    def test_build_global_index_empty(self, builder):
        """Test building index with no sessions."""
        index = builder.build_global_index()
        assert index["total_sessions"] == 0
        assert index["total_memory_bytes"] == 0

    def test_build_global_index_with_sessions(self, builder, temp_artifact_dir):
        """Test building index with multiple sessions."""
        # Create some session memory
        store1 = ArtifactMemoryStore("session-1", temp_artifact_dir)
        store1.write("metrics", {"test": 1})
        
        store2 = ArtifactMemoryStore("session-2", temp_artifact_dir)
        store2.write("logs", {"log": 1})
        
        index = builder.build_global_index()
        assert index["total_sessions"] == 2
        assert index["total_memory_bytes"] > 0
        assert len(index["sessions"]) == 2


class TestSessionMemoryManager:
    """Test SessionMemoryManager functionality."""

    @pytest.fixture
    def temp_artifact_dir(self):
        """Create temporary artifact directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def manager(self, temp_artifact_dir):
        """Create manager instance."""
        return SessionMemoryManager("test-session", base_dir=temp_artifact_dir)

    def test_collect_session_memory(self, manager):
        """Test collecting session memory."""
        manager.store.write("metrics", {"tokens": 100})
        
        collected = manager.collect_session_memory()
        assert collected["session_id"] == "test-session"
        assert "memory" in collected
        assert collected["memory"]["file_count"] > 0

    def test_finalize_session_memory(self, manager):
        """Test finalizing session memory."""
        manager.store.write("metrics", {"tokens": 100})
        
        index_path = manager.finalize_session_memory()
        assert index_path.exists()

    def test_write_session_summary(self, manager):
        """Test writing session summary."""
        summary_data = {
            "delegates": {"count": 5},
            "handbacks": {"count": 5},
            "memory": {"file_count": 10, "total_size_bytes": 5000},
        }
        
        summary_path = manager.write_session_summary(summary_data)
        assert summary_path.exists()
        assert summary_path.name == "summary.md"
        
        content = summary_path.read_text()
        assert "test-session" in content
        assert "Delegates" in content


class TestGlobalMemoryManager:
    """Test GlobalMemoryManager functionality."""

    @pytest.fixture
    def temp_artifact_dir(self):
        """Create temporary artifact directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def manager(self, temp_artifact_dir):
        """Create global manager instance."""
        return GlobalMemoryManager(base_dir=temp_artifact_dir)

    def test_build_global_index(self, manager, temp_artifact_dir):
        """Test building and writing global index."""
        # Create some session memory
        store = ArtifactMemoryStore("session-1", temp_artifact_dir)
        store.write("metrics", {"test": 1})
        
        index_path = manager.build_global_index()
        assert index_path.exists()
        assert index_path.name == "MEMORY_INDEX.json"
        
        with open(index_path) as f:
            index = json.load(f)
        
        assert index["total_sessions"] == 1


class TestDirectorySetup:
    """Test directory setup utilities."""

    @pytest.fixture
    def temp_home(self):
        """Create temporary home directory."""
        temp_dir = tempfile.mkdtemp()
        original_home = Path.home()
        
        # Temporarily replace home
        import os
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = temp_dir
        
        yield temp_dir
        
        # Restore
        if old_home:
            os.environ["HOME"] = old_home
        else:
            del os.environ["HOME"]
        
        shutil.rmtree(temp_dir)

    def test_setup_session_memory(self, temp_home):
        """Test setting up session memory directories."""
        import os
        temp_artifact = Path(temp_home) / ".agentic-engineers"
        os.environ["AGENTIC_ENGINEERS_HOME"] = str(temp_artifact)
        
        subdirs = setup_session_memory("test-session")
        
        assert subdirs["delegates"].exists()
        assert subdirs["handbacks"].exists()
        assert subdirs["logs"].exists()
        assert subdirs["thinking"].exists()
        assert subdirs["metrics"].exists()

    def test_get_session_memory_dir(self):
        """Test getting session memory directory path."""
        session_dir = get_session_memory_dir("test-session")
        assert "test-session" in str(session_dir)
        assert "memory" in str(session_dir)


class TestMemoryIntegration:
    """Integration tests for memory system."""

    @pytest.fixture
    def temp_artifact_dir(self):
        """Create temporary artifact directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_full_workflow(self, temp_artifact_dir):
        """Test complete memory workflow."""
        # Create session with multiple memory writes
        store = ArtifactMemoryStore("workflow-session", temp_artifact_dir)
        
        # Write different types of data
        store.write("metrics", {"tokens": 1000, "cost": 5.0})
        store.write("config", {"model": "claude-haiku"}, subdir="config")
        store.append_metric("quality", {"score": 95}, subdir="metrics")
        store.append_metric("quality", {"score": 92}, subdir="metrics")
        
        # Create manager and finalize
        manager = SessionMemoryManager("workflow-session", temp_artifact_dir)
        collected = manager.collect_session_memory()
        
        assert collected["memory"]["file_count"] >= 3
        assert collected["memory"]["total_size_bytes"] > 0
        
        # Build global index
        global_manager = GlobalMemoryManager(temp_artifact_dir)
        global_index = global_manager.build_global_index()
        assert global_index.exists()
        
        # Verify data persistence
        store2 = ArtifactMemoryStore("workflow-session", temp_artifact_dir)
        metrics = store2.read("metrics")
        assert metrics["data"]["tokens"] == 1000

    def test_memory_persistence(self, temp_artifact_dir):
        """Test that memory persists across instances."""
        # Write with first instance
        store1 = ArtifactMemoryStore("persist-session", temp_artifact_dir)
        store1.write("test", {"value": 42})
        
        # Read with second instance
        store2 = ArtifactMemoryStore("persist-session", temp_artifact_dir)
        result = store2.read("test")
        
        assert result is not None
        assert result["data"]["value"] == 42

    def test_memory_size_calculation(self, temp_artifact_dir):
        """Test accurate memory size calculation."""
        store = ArtifactMemoryStore("size-session", temp_artifact_dir)
        
        # Write known amount of data
        test_data = {"data": "x" * 1000}  # ~1000 bytes
        store.write("test", test_data)
        
        aggregate = store.aggregate_session()
        assert aggregate["file_count"] == 1
        assert aggregate["total_size_bytes"] > 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
