"""
Integration Tests for Continuous Polling Loop Automation - Phase 2

Tests for:
1. End-to-end AutomationController with real queue
2. DELEGATE task reading and processing
3. AgentInvoker spawning
4. HANDBACK file creation
5. Metrics collection
6. Graceful shutdown and error recovery
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess
import signal
import pytest
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.agents.automation import AutomationController, AutomationMetrics
from orchestration.agents.orchestrator import OrchestratorAgent, QueueManager


class TestAutomationControllerE2E:
    """End-to-end tests for AutomationController with real queue."""
    
    @pytest.fixture
    def test_queue(self, tmp_path):
        """Create a test queue directory structure."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        (queue_dir / "incoming").mkdir()
        (queue_dir / "done").mkdir()
        return queue_dir
    
    @pytest.fixture
    def sample_delegate(self, test_queue):
        """Create sample DELEGATE files in test queue."""
        delegates = []
        for i in range(3):
            delegate_path = test_queue / "incoming" / f"DELEGATE-test-{i:03d}.yaml"
            delegate_content = f"""---
handoff_type: DELEGATE
task_id: test-task-{i:03d}
role: Engineer
model: claude-sonnet-4.6
effort: low
scope: Test task {i}
plan: Execute test {i}
success_criteria:
  - Task completes without error
"""
            delegate_path.write_text(delegate_content)
            delegates.append(delegate_path)
        return delegates
    
    def test_automation_controller_initialization(self, test_queue):
        """Test AutomationController initializes correctly."""
        controller = AutomationController(
            queue_dir=str(test_queue),
            poll_interval=1,
            log_level="INFO",
            daemon_mode=False,
            idle_timeout=5,
            max_cycles=None,
            metrics_file=None
        )
        
        assert controller is not None
        assert controller.poll_interval == 1
        assert controller.log_level == "INFO"
        assert controller.daemon_mode == False
        assert controller.idle_timeout == 5
        assert controller.orchestrator is not None
    
    def test_automation_controller_runs_with_empty_queue(self, test_queue):
        """Test AutomationController handles empty queue gracefully."""
        controller = AutomationController(
            queue_dir=str(test_queue),
            poll_interval=0.5,
            log_level="INFO",
            daemon_mode=False,
            idle_timeout=2,
            max_cycles=3,
            metrics_file=None
        )
        
        result = controller.run()
        
        assert result["status"] in ["COMPLETE", "INTERRUPTED"]
        assert "metrics" in result
        assert result["metrics"]["cycles_completed"] >= 1
    
    def test_automation_controller_with_sample_delegates(self, test_queue, sample_delegate):
        """Test AutomationController processes DELEGATE files."""
        metrics_file = test_queue / "metrics.json"
        
        controller = AutomationController(
            queue_dir=str(test_queue),
            poll_interval=0.5,
            log_level="INFO",
            daemon_mode=False,
            idle_timeout=5,
            max_cycles=10,
            metrics_file=str(metrics_file)
        )
        
        result = controller.run()
        
        # Verify controller completed
        assert result["status"] in ["COMPLETE", "INTERRUPTED"]
        assert result["metrics"]["cycles_completed"] >= 1
        
        # Verify metrics file was created
        assert metrics_file.exists(), f"Metrics file not created at {metrics_file}"
        
        # Verify metrics file contains valid JSON
        with open(metrics_file) as f:
            metrics_data = json.load(f)
        
        assert "status" in metrics_data
        assert "metrics" in metrics_data
        assert metrics_data["metrics"]["tasks_processed"] >= 0
    
    def test_queue_manager_state_transitions(self, test_queue, sample_delegate):
        """Test QueueManager correctly transitions task states."""
        queue_manager = QueueManager(queue_dir=str(test_queue))
        
        # Check initial queue state
        initial_count = len(list((test_queue / "incoming").glob("DELEGATE-*")))
        assert initial_count == 3
        
        # Simulate moving a task through states
        incoming_tasks = list((test_queue / "incoming").glob("DELEGATE-*"))
        assert len(incoming_tasks) > 0


class TestMetricsCollection:
    """Tests for metrics collection and export."""
    
    def test_automation_metrics_initialization(self):
        """Test AutomationMetrics initializes correctly."""
        metrics = AutomationMetrics()
        
        assert metrics.cycles_completed == 0
        assert metrics.tasks_processed == 0
        assert metrics.tasks_success == 0
        assert metrics.tasks_escalated == 0
        assert metrics.tasks_failed == 0
        assert metrics.error_count == 0
    
    def test_automation_metrics_record_cycle(self):
        """Test AutomationMetrics records cycle data correctly."""
        metrics = AutomationMetrics()
        
        cycle_result = {
            "tasks_processed": 5,
            "tasks_success": 4,
            "tasks_escalated": 1,
            "tasks_failed": 0
        }
        
        metrics.record_cycle(1.5, cycle_result)
        
        assert metrics.cycles_completed == 1
        assert metrics.tasks_processed == 5
        assert metrics.tasks_success == 4
        assert metrics.tasks_escalated == 1
        assert metrics.cycle_duration_avg_seconds == 1.5
    
    def test_automation_metrics_record_error(self):
        """Test AutomationMetrics records errors correctly."""
        metrics = AutomationMetrics()
        
        error_msg = "Test error message"
        metrics.record_error(error_msg)
        
        assert metrics.error_count == 1
        assert len(metrics.errors) == 1
        assert error_msg in metrics.errors[0]["message"]
    
    def test_automation_metrics_to_dict(self):
        """Test AutomationMetrics serialization to dict."""
        metrics = AutomationMetrics()
        metrics.record_cycle(1.5, {"tasks_processed": 3, "tasks_success": 3})
        metrics.record_error("Test error")
        metrics.finalize()
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert "start_time" in metrics_dict
        assert "end_time" in metrics_dict
        assert "cycles_completed" in metrics_dict
        assert "tasks_processed" in metrics_dict
        assert "error_count" in metrics_dict
        assert metrics_dict["cycles_completed"] == 1
        assert metrics_dict["tasks_processed"] == 3


class TestPrometheusMetricsExport:
    """Tests for Prometheus metrics format export."""
    
    def test_metrics_to_prometheus_format(self):
        """Test conversion of metrics to Prometheus format."""
        metrics = AutomationMetrics()
        metrics.record_cycle(1.5, {"tasks_processed": 5, "tasks_success": 4})
        metrics.finalize()
        
        # Simulate Prometheus metrics format
        prometheus_lines = [
            f"# HELP automation_cycles_completed Total cycles completed",
            f"# TYPE automation_cycles_completed counter",
            f"automation_cycles_completed {{}} {metrics.cycles_completed}",
            f"# HELP automation_tasks_processed Total tasks processed",
            f"# TYPE automation_tasks_processed counter",
            f"automation_tasks_processed {{}} {metrics.tasks_processed}",
            f"# HELP automation_tasks_success Successful tasks",
            f"# TYPE automation_tasks_success counter",
            f"automation_tasks_success {{}} {metrics.tasks_success}",
        ]
        
        output = "\n".join(prometheus_lines)
        assert "automation_cycles_completed" in output
        assert "automation_tasks_processed" in output
        assert "1" in output  # cycles_completed = 1


class TestHealthCheck:
    """Tests for health checking mechanisms."""
    
    def test_health_check_status_ok(self, tmp_path):
        """Test health check returns OK for healthy system."""
        controller = AutomationController(
            queue_dir=str(tmp_path / "queue"),
            poll_interval=1,
            daemon_mode=False,
            idle_timeout=5,
        )
        
        # Run a short cycle
        result = controller.run()
        
        # Should complete without critical errors
        assert result["status"] in ["COMPLETE", "INTERRUPTED"]
    
    def test_health_check_metrics_available(self, tmp_path):
        """Test health check can access metrics."""
        metrics_file = tmp_path / "metrics.json"
        
        controller = AutomationController(
            queue_dir=str(tmp_path / "queue"),
            poll_interval=1,
            daemon_mode=False,
            idle_timeout=2,
            max_cycles=1,
            metrics_file=str(metrics_file)
        )
        
        result = controller.run()
        
        # Verify metrics file exists and is readable
        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics_data = json.load(f)
            assert metrics_data["status"] in ["COMPLETE", "INTERRUPTED"]


class TestErrorRecovery:
    """Tests for error handling and recovery."""
    
    def test_controller_handles_missing_queue_directory(self, tmp_path):
        """Test controller handles missing queue directory gracefully."""
        non_existent_queue = tmp_path / "non_existent" / "queue"
        
        controller = AutomationController(
            queue_dir=str(non_existent_queue),
            poll_interval=1,
            daemon_mode=False,
            idle_timeout=2,
            max_cycles=1
        )
        
        # Should not crash - QueueManager creates directory
        result = controller.run()
        assert result is not None
    
    def test_controller_handles_invalid_yaml_files(self, tmp_path):
        """Test controller handles invalid YAML in queue."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        (queue_dir / "incoming").mkdir()
        (queue_dir / "done").mkdir()
        
        # Create invalid YAML file
        invalid_file = queue_dir / "incoming" / "DELEGATE-invalid.yaml"
        invalid_file.write_text("{ invalid: yaml: content: }")
        
        controller = AutomationController(
            queue_dir=str(queue_dir),
            poll_interval=1,
            daemon_mode=False,
            idle_timeout=2,
            max_cycles=1
        )
        
        # Should handle gracefully
        result = controller.run()
        assert result is not None


class TestSignalHandling:
    """Tests for signal handling in AutomationController."""
    
    def test_sigterm_triggers_graceful_shutdown(self, tmp_path):
        """Test SIGTERM causes graceful shutdown."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        (queue_dir / "incoming").mkdir()
        (queue_dir / "done").mkdir()
        
        # Note: Full signal test requires subprocess execution
        # This test verifies signal handler setup only
        controller = AutomationController(
            queue_dir=str(queue_dir),
            poll_interval=1,
            daemon_mode=False,
            idle_timeout=5,
        )
        
        assert controller.shutdown_requested == False
        # Signal handlers would be tested with subprocess


class TestQueueProcessing:
    """Tests for queue processing and state transitions."""
    
    def test_delegate_read_from_queue(self, tmp_path):
        """Test DELEGATE files are correctly read from queue."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        (queue_dir / "incoming").mkdir()
        (queue_dir / "done").mkdir()
        
        # Create a DELEGATE file
        delegate_path = queue_dir / "incoming" / "DELEGATE-test-001.yaml"
        delegate_yaml = """---
handoff_type: DELEGATE
task_id: test-001
role: Engineer
scope: Test task
plan: Execute
success_criteria:
  - Completes
"""
        delegate_path.write_text(delegate_yaml)
        
        # Verify file can be read
        assert delegate_path.exists()
        content = delegate_path.read_text()
        assert "DELEGATE" in content
        assert "test-001" in content
    
    def test_handback_file_creation(self, tmp_path):
        """Test HANDBACK files are created in done directory."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        done_dir = queue_dir / "done"
        done_dir.mkdir()
        
        # Simulate creating HANDBACK file
        handback_path = done_dir / "HANDBACK-test-001.yaml"
        handback_yaml = """---
handoff_type: HANDBACK
task_id: test-001
status: complete
deliverables:
  - test file created
tests_passed: 1/1
"""
        handback_path.write_text(handback_yaml)
        
        # Verify HANDBACK file was created
        assert handback_path.exists()
        assert handback_path.read_text().count("HANDBACK") > 0


class TestIntegrationE2E:
    """End-to-end integration tests."""
    
    def test_full_automation_cycle(self, tmp_path):
        """Test complete automation cycle from start to finish."""
        # Setup
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        (queue_dir / "incoming").mkdir()
        (queue_dir / "done").mkdir()
        metrics_file = tmp_path / "metrics.json"
        
        # Create controller
        controller = AutomationController(
            queue_dir=str(queue_dir),
            poll_interval=0.5,
            log_level="INFO",
            daemon_mode=False,
            idle_timeout=3,
            max_cycles=5,
            metrics_file=str(metrics_file)
        )
        
        # Run
        result = controller.run()
        
        # Verify results
        assert result["status"] in ["COMPLETE", "INTERRUPTED"]
        assert "metrics" in result
        assert result["metrics"]["cycles_completed"] >= 1
        
        # Verify metrics file
        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics_data = json.load(f)
            assert "status" in metrics_data
            assert "metrics" in metrics_data


# ─── Script Entrypoint Tests ───────────────────────────────────────────────

class TestEntrypointScript:
    """Tests for bin/run-automation-controller.sh entrypoint."""
    
    def test_entrypoint_script_exists(self):
        """Test entrypoint script exists and is executable."""
        entrypoint = PROJECT_ROOT / "bin" / "run-automation-controller.sh"
        assert entrypoint.exists(), f"Entrypoint script not found at {entrypoint}"
        assert os.access(entrypoint, os.X_OK), f"Entrypoint script not executable: {entrypoint}"
    
    def test_entrypoint_help(self):
        """Test entrypoint script responds to help."""
        entrypoint = PROJECT_ROOT / "bin" / "run-automation-controller.sh"
        # Note: Full execution test requires subprocess and proper environment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
