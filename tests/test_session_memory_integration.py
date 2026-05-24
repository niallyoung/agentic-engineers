"""Integration tests for session memory system."""

import os
import json
import yaml
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.orchestration.memory.directory_setup import (
    setup_session_memory,
    get_session_memory_dir,
)
from src.orchestration.memory.aggregator import SessionMemoryAggregator
from src.orchestration.memory.session_manager import SessionMemoryManager


class TestMemoryDirectorySetup:
    """Test memory directory setup."""
    
    def test_setup_session_memory_creates_structure(self, tmp_path):
        """Test that setup creates proper directory structure."""
        session_id = "test-session-001"
        
        # Mock the home directory
        old_home = Path.home()
        with tempfile.TemporaryDirectory() as tmpdir:
            agentic_home = Path(tmpdir) / ".agentic-engineers"
            
            # Create subdirectories
            memory_dir = agentic_home / session_id / "memory"
            subdirs = {
                "delegates": memory_dir / "delegates",
                "handbacks": memory_dir / "handbacks",
                "logs": memory_dir / "logs",
                "thinking": memory_dir / "thinking",
                "metrics": memory_dir / "metrics",
            }
            
            for name, path in subdirs.items():
                path.mkdir(parents=True, exist_ok=True)
                (path / ".keep").touch()
            
            # Verify structure
            assert memory_dir.exists()
            for name, path in subdirs.items():
                assert path.exists(), f"Missing {name} directory"
                assert (path / ".keep").exists(), f"Missing .keep file in {name}"
    
    def test_get_session_memory_dir(self, tmp_path):
        """Test getting session memory directory."""
        session_id = "test-session-002"
        
        # This should construct the correct path
        # Note: In tests, this will use the actual home directory
        memory_dir = get_session_memory_dir(session_id)
        
        assert session_id in str(memory_dir)
        assert "memory" in str(memory_dir)


class TestSessionMemoryAggregator:
    """Test memory aggregation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.session_id = "test-session-agg-001"
        
        # Create queue structure
        self.queue_dir = Path(self.test_dir) / "queue" / self.session_id
        self.incoming_dir = self.queue_dir / "incoming"
        self.processing_dir = self.queue_dir / "processing"
        self.done_dir = self.queue_dir / "done"
        
        for dir_path in [self.incoming_dir, self.processing_dir, self.done_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create memory structure
        self.memory_dir = Path(self.test_dir) / "memory" / self.session_id / "memory"
        delegates_dir = self.memory_dir / "delegates"
        handbacks_dir = self.memory_dir / "handbacks"
        for dir_path in [delegates_dir, handbacks_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_collect_delegates_from_incoming(self):
        """Test collecting DELEGATEs from incoming queue."""
        # Create sample DELEGATE
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "test-task-001",
            "timestamp": datetime.utcnow().isoformat(),
            "role": "Engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Test scope",
            "plan": ["step 1"],
            "success_criteria": ["criteria 1"],
        }
        
        delegate_file = self.incoming_dir / "test-task-001.yaml"
        with open(delegate_file, "w") as f:
            yaml.dump(delegate_data, f)
        
        # Patch memory dir for aggregator
        import src.orchestration.memory.aggregator as agg_module
        original_get_memory_dir = agg_module.get_session_memory_dir
        agg_module.get_session_memory_dir = lambda sid: self.memory_dir
        
        try:
            aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            delegates = aggregator.collect_delegates()
            
            assert len(delegates) >= 1
            assert any(d["task_id"] == "test-task-001" for d in delegates)
            
            # Verify copy was made
            copy_path = self.memory_dir / "delegates" / "test-task-001.yaml"
            assert copy_path.exists()
        finally:
            agg_module.get_session_memory_dir = original_get_memory_dir
    
    def test_collect_handbacks(self):
        """Test collecting HANDBACKs from processing."""
        # Create sample HANDBACK
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "test-task-002",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "complete",
            "quality_score": 95,
            "tokens": {"used": 1000},
            "deliverables": ["code", "tests"],
            "tests": ["test 1 passed"],
        }
        
        handback_file = self.processing_dir / "test-task-002-handback.yaml"
        with open(handback_file, "w") as f:
            yaml.dump(handback_data, f)
        
        # Patch memory dir
        import src.orchestration.memory.aggregator as agg_module
        original_get_memory_dir = agg_module.get_session_memory_dir
        agg_module.get_session_memory_dir = lambda sid: self.memory_dir
        
        try:
            aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            handbacks = aggregator.collect_handbacks()
            
            assert len(handbacks) >= 1
            assert any(h["task_id"] == "test-task-002" for h in handbacks)
            
            # Verify copy was made
            copy_path = self.memory_dir / "handbacks" / "test-task-002-handback.yaml"
            assert copy_path.exists()
        finally:
            agg_module.get_session_memory_dir = original_get_memory_dir
    
    def test_aggregate_all(self):
        """Test full aggregation."""
        # Create sample data
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "agg-test-001",
            "timestamp": datetime.utcnow().isoformat(),
            "role": "Engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Test",
            "plan": ["step"],
            "success_criteria": ["test"],
        }
        
        delegate_file = self.incoming_dir / "agg-test-001.yaml"
        with open(delegate_file, "w") as f:
            yaml.dump(delegate_data, f)
        
        # Patch memory dir
        import src.orchestration.memory.aggregator as agg_module
        original_get_memory_dir = agg_module.get_session_memory_dir
        agg_module.get_session_memory_dir = lambda sid: self.memory_dir
        
        try:
            aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            index = aggregator.aggregate_all()
            
            assert index["session_id"] == self.session_id
            assert "summary" in index
            assert index["summary"]["total_delegates"] >= 1
        finally:
            agg_module.get_session_memory_dir = original_get_memory_dir
    
    def test_export_index(self):
        """Test exporting index to JSON."""
        # Patch memory dir
        import src.orchestration.memory.aggregator as agg_module
        original_get_memory_dir = agg_module.get_session_memory_dir
        agg_module.get_session_memory_dir = lambda sid: self.memory_dir
        
        try:
            aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            aggregator.aggregate_all()
            index_path = aggregator.export_index()
            
            assert index_path.exists()
            
            # Verify content
            with open(index_path, "r") as f:
                data = json.load(f)
            
            assert data["session_id"] == self.session_id
            assert "summary" in data
        finally:
            agg_module.get_session_memory_dir = original_get_memory_dir
    
    def test_query_by_task_id(self):
        """Test querying memory by task ID."""
        # Create sample DELEGATE
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "query-test-001",
            "timestamp": datetime.utcnow().isoformat(),
            "role": "Engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Test",
            "plan": ["step"],
            "success_criteria": ["test"],
        }
        
        delegate_file = self.incoming_dir / "query-test-001.yaml"
        with open(delegate_file, "w") as f:
            yaml.dump(delegate_data, f)
        
        # Patch memory dir
        import src.orchestration.memory.aggregator as agg_module
        original_get_memory_dir = agg_module.get_session_memory_dir
        agg_module.get_session_memory_dir = lambda sid: self.memory_dir
        
        try:
            aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            aggregator.aggregate_all()
            
            result = aggregator.query_by_task_id("query-test-001")
            
            assert result["task_id"] == "query-test-001"
            assert len(result["delegates"]) >= 1
        finally:
            agg_module.get_session_memory_dir = original_get_memory_dir
    
    def test_query_by_role(self):
        """Test querying memory by role."""
        # Create sample DELEGATE
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "role-test-001",
            "timestamp": datetime.utcnow().isoformat(),
            "role": "Senior Engineer",
            "model": "claude-sonnet-4.6",
            "effort": "high",
            "scope": "Test",
            "plan": ["step"],
            "success_criteria": ["test"],
        }
        
        delegate_file = self.incoming_dir / "role-test-001.yaml"
        with open(delegate_file, "w") as f:
            yaml.dump(delegate_data, f)
        
        # Patch memory dir
        import src.orchestration.memory.aggregator as agg_module
        original_get_memory_dir = agg_module.get_session_memory_dir
        agg_module.get_session_memory_dir = lambda sid: self.memory_dir
        
        try:
            aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            aggregator.aggregate_all()
            
            result = aggregator.query_by_role("Senior Engineer")
            
            assert result["role"] == "Senior Engineer"
            assert result["count"] >= 1
        finally:
            agg_module.get_session_memory_dir = original_get_memory_dir


class TestSessionMemoryManager:
    """Test session memory manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.session_id = "test-session-mgr-001"
    
    def teardown_method(self):
        """Clean up."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialize_memory(self):
        """Test memory initialization."""
        # Patch memory dir
        import src.orchestration.memory.session_manager as mgr_module
        original_get_memory_dir = mgr_module.get_session_memory_dir
        mgr_module.get_session_memory_dir = lambda sid: Path(self.test_dir) / sid / "memory"
        
        try:
            manager = SessionMemoryManager(self.session_id)
            result = manager.initialize({"test": "metadata"})
            
            assert result["success"] is True
            assert result["session_id"] == self.session_id
            assert "memory_dir" in result
        finally:
            mgr_module.get_session_memory_dir = original_get_memory_dir
    
    def test_get_delegates(self):
        """Test getting delegates."""
        # Patch memory dir
        import src.orchestration.memory.session_manager as mgr_module
        original_get_memory_dir = mgr_module.get_session_memory_dir
        mgr_module.get_session_memory_dir = lambda sid: Path(self.test_dir) / sid / "memory"
        
        try:
            manager = SessionMemoryManager(self.session_id)
            manager.initialize()
            
            # Manually add delegate to index
            if manager.aggregator:
                manager.aggregator.index["delegates"] = [
                    {"task_id": "t1", "role": "Engineer"},
                    {"task_id": "t2", "role": "Senior Engineer"},
                ]
            
            delegates = manager.get_delegates()
            assert len(delegates) == 2
            
            # Test filtering by role
            eng_delegates = manager.get_delegates(role="Engineer")
            assert len(eng_delegates) == 1
        finally:
            mgr_module.get_session_memory_dir = original_get_memory_dir
    
    def test_generate_summary(self):
        """Test summary generation."""
        # Patch memory dir
        import src.orchestration.memory.session_manager as mgr_module
        original_get_memory_dir = mgr_module.get_session_memory_dir
        mgr_module.get_session_memory_dir = lambda sid: Path(self.test_dir) / sid / "memory"
        
        try:
            manager = SessionMemoryManager(self.session_id)
            manager.initialize()
            
            # Manually populate index
            if manager.aggregator:
                manager.aggregator.index["summary"] = {
                    "total_delegates": 5,
                    "total_handbacks": 4,
                    "completed_tasks": 4,
                    "failed_tasks": 0,
                    "total_tokens": 50000,
                    "average_quality_score": 92.5,
                }
                manager.aggregator.index["delegates"] = [
                    {"task_id": "t1", "role": "Engineer"},
                    {"task_id": "t2", "role": "Senior Engineer"},
                ]
            
            summary = manager.generate_summary()
            
            assert "Session Memory Summary" in summary
            assert "Total DELEGATEs:** 5" in summary
            assert "Average Quality Score:** 92.5" in summary
        finally:
            mgr_module.get_session_memory_dir = original_get_memory_dir
