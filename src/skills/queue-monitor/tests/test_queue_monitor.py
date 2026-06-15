"""Tests for queue-monitor skill."""

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

# Import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.queue_monitor import QueueMonitor, QueueMonitorUI, TaskMetadata, QueueState


class TestTaskMetadata:
    """Tests for TaskMetadata dataclass."""

    def test_task_metadata_creation(self):
        """Test TaskMetadata initialization."""
        task = TaskMetadata(
            task_id="test-task-001",
            agent="engineer",
            status="success",
            duration_seconds=120,
        )
        assert task.task_id == "test-task-001"
        assert task.agent == "engineer"
        assert task.status == "success"
        assert task.duration_seconds == 120

    def test_task_metadata_defaults(self):
        """Test TaskMetadata with default values."""
        task = TaskMetadata(task_id="minimal-task")
        assert task.task_id == "minimal-task"
        assert task.agent is None
        assert task.status is None
        assert task.duration_seconds is None


class TestQueueState:
    """Tests for QueueState dataclass."""

    def test_queue_state_creation(self):
        """Test QueueState initialization."""
        state = QueueState()
        assert state.incoming == []
        assert state.processing == []
        assert state.done == []
        assert state.failed == []
        assert isinstance(state.last_updated, datetime)

    def test_queue_state_with_tasks(self):
        """Test QueueState with populated task lists."""
        task1 = TaskMetadata(task_id="task-1", status="success")
        task2 = TaskMetadata(task_id="task-2")
        state = QueueState(incoming=[task2], done=[task1])
        assert len(state.incoming) == 1
        assert len(state.done) == 1
        assert state.incoming[0].task_id == "task-2"


class TestQueueMonitor:
    """Tests for QueueMonitor class."""

    def test_monitor_initialization_with_defaults(self):
        """Test QueueMonitor with no arguments."""
        monitor = QueueMonitor(session_id="test-session", harness="test-harness", auto_detect=False)
        assert monitor.session_id == "test-session"
        assert monitor.harness == "test-harness"
        assert monitor.poll_count == 0

    def test_monitor_queue_path_detection(self, tmp_path):
        """Test auto-detection of queue path."""
        # Create queue directory structure
        queue_root = tmp_path / "test-harness" / "test-session" / "queue"
        queue_root.mkdir(parents=True, exist_ok=True)
        (queue_root / "incoming").mkdir(exist_ok=True)
        (queue_root / "processing").mkdir(exist_ok=True)
        (queue_root / "done").mkdir(exist_ok=True)

        monitor = QueueMonitor(
            session_id="test-session",
            harness="test-harness",
            base_dir=str(tmp_path),
        )
        assert monitor.queue_root == queue_root

    def test_monitor_parse_delegate_yaml(self, tmp_path):
        """Test parsing of DELEGATE YAML file."""
        queue_root = tmp_path / "queue"
        incoming_dir = queue_root / "incoming"
        incoming_dir.mkdir(parents=True, exist_ok=True)

        # Create a DELEGATE YAML file
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "test-delegate-001",
            "agent": "engineer",
            "scope": "Test scope",
        }
        delegate_file = incoming_dir / "DELEGATE-test-001.yaml"
        delegate_file.write_text(yaml.dump(delegate_data))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        task = monitor._parse_task_file(delegate_file, "incoming")

        assert task is not None
        assert task.task_id == "test-delegate-001"
        assert task.agent == "engineer"
        assert task.task_type == "DELEGATE"

    def test_monitor_parse_handback_yaml(self, tmp_path):
        """Test parsing of HANDBACK YAML file."""
        queue_root = tmp_path / "queue"
        done_dir = queue_root / "done"
        done_dir.mkdir(parents=True, exist_ok=True)

        # Create a HANDBACK YAML file
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "test-handback-001",
            "status": "success",
            "metrics": {
                "quality": 0.95,
                "tokens": 1200,
                "cost": 0.04,
                "duration_seconds": 180,
            },
        }
        handback_file = done_dir / "HANDBACK-test-001.yaml"
        handback_file.write_text(yaml.dump(handback_data))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        task = monitor._parse_task_file(handback_file, "done")

        assert task is not None
        assert task.task_id == "test-handback-001"
        assert task.status == "success"
        assert task.duration_seconds == 180
        assert task.task_type == "HANDBACK"

    def test_monitor_parse_handback_json(self, tmp_path):
        """Test parsing of HANDBACK JSON file."""
        queue_root = tmp_path / "queue"
        done_dir = queue_root / "done"
        done_dir.mkdir(parents=True, exist_ok=True)

        # Create a HANDBACK JSON file
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "test-json-001",
            "status": "failure",
            "metrics": {"duration_seconds": 45},
        }
        handback_file = done_dir / "HANDBACK-test-json-001.json"
        handback_file.write_text(json.dumps(handback_data))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        task = monitor._parse_task_file(handback_file, "done")

        assert task is not None
        assert task.task_id == "test-json-001"
        assert task.status == "failure"
        assert task.task_type == "HANDBACK"

    def test_monitor_full_poll(self, tmp_path):
        """Test full queue polling with multiple states."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        # Add tasks to each state
        incoming_data = {
            "handoff_type": "DELEGATE",
            "task_id": "incoming-001",
            "agent": "engineer",
        }
        (queue_root / "incoming" / "DELEGATE-incoming-001.yaml").write_text(
            yaml.dump(incoming_data)
        )

        processing_data = {
            "handoff_type": "DELEGATE",
            "task_id": "processing-001",
            "agent": "senior-engineer",
        }
        (queue_root / "processing" / "DELEGATE-processing-001.yaml").write_text(
            yaml.dump(processing_data)
        )

        done_data = {
            "handoff_type": "HANDBACK",
            "task_id": "done-001",
            "status": "success",
            "metrics": {"duration_seconds": 120},
        }
        (queue_root / "done" / "HANDBACK-done-001.yaml").write_text(
            yaml.dump(done_data)
        )

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        monitor.poll()

        assert len(monitor.state.incoming) == 1
        assert len(monitor.state.processing) == 1
        assert len(monitor.state.done) == 1
        assert len(monitor.state.failed) == 0
        assert monitor.poll_count == 1

    def test_monitor_metrics_calculation(self, tmp_path):
        """Test metrics aggregation from queue state."""
        queue_root = tmp_path / "queue"
        done_dir = queue_root / "done"
        done_dir.mkdir(parents=True, exist_ok=True)

        # Add multiple completed tasks
        for i, (task_id, status, duration) in enumerate([
            ("task-1", "success", 100),
            ("task-2", "success", 200),
            ("task-3", "failure", 50),
        ]):
            data = {
                "handoff_type": "HANDBACK",
                "task_id": task_id,
                "status": status,
                "metrics": {"duration_seconds": duration},
            }
            (done_dir / f"HANDBACK-{task_id}.yaml").write_text(yaml.dump(data))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        monitor.poll()

        metrics = monitor.get_metrics()
        assert metrics["done_count"] == 3
        assert metrics["succeeded_count"] == 2
        assert metrics["failed_count"] == 1
        assert metrics["success_rate"] == pytest.approx(66.66, rel=0.01)
        assert metrics["avg_duration_seconds"] == 116  # (100 + 200 + 50) / 3

    def test_monitor_metrics_with_empty_queue(self, tmp_path):
        """Test metrics with no completed tasks."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        monitor.poll()

        metrics = monitor.get_metrics()
        assert metrics["done_count"] == 0
        assert metrics["succeeded_count"] == 0
        assert metrics["failed_count"] == 0
        assert metrics["success_rate"] == 0

    def test_monitor_processing_duration_estimation(self, tmp_path):
        """Test duration estimation for processing tasks."""
        queue_root = tmp_path / "queue"
        processing_dir = queue_root / "processing"
        processing_dir.mkdir(parents=True, exist_ok=True)

        # Create a task file and modify its timestamp
        processing_data = {
            "handoff_type": "DELEGATE",
            "task_id": "slow-task",
            "agent": "engineer",
        }
        task_file = processing_dir / "DELEGATE-slow-task.yaml"
        task_file.write_text(yaml.dump(processing_data))

        # Set mtime to 10 seconds ago
        old_time = time.time() - 10
        os.utime(task_file, (old_time, old_time))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        monitor.poll()

        assert len(monitor.state.processing) == 1
        task = monitor.state.processing[0]
        # Duration should be approximately 10 seconds
        assert task.duration_seconds is not None
        assert 9 <= task.duration_seconds <= 11

    def test_monitor_invalid_yaml_handling(self, tmp_path):
        """Test graceful handling of invalid YAML files."""
        queue_root = tmp_path / "queue"
        incoming_dir = queue_root / "incoming"
        incoming_dir.mkdir(parents=True, exist_ok=True)

        # Create an invalid YAML file
        invalid_file = incoming_dir / "DELEGATE-invalid.yaml"
        invalid_file.write_text("{ invalid: yaml: syntax: [")

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root

        # Should not raise exception
        task = monitor._parse_task_file(invalid_file, "incoming")
        assert task is None

    def test_monitor_missing_fields_handling(self, tmp_path):
        """Test handling of YAML with missing required fields."""
        queue_root = tmp_path / "queue"
        incoming_dir = queue_root / "incoming"
        incoming_dir.mkdir(parents=True, exist_ok=True)

        # Create a YAML with minimal fields
        minimal_data = {"handoff_type": "DELEGATE"}
        minimal_file = incoming_dir / "DELEGATE-minimal.yaml"
        minimal_file.write_text(yaml.dump(minimal_data))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        task = monitor._parse_task_file(minimal_file, "incoming")

        assert task is not None
        assert task.task_id == "DELEGATE-minimal"
        assert task.agent is None
        assert task.status is None


class TestQueueMonitorUI:
    """Tests for QueueMonitorUI class."""

    def test_ui_initialization(self, tmp_path):
        """Test UI initialization with monitor."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        ui = QueueMonitorUI(monitor)

        assert ui.monitor is monitor
        assert ui.running is True
        assert ui.poll_interval == 5.0

    def test_ui_handle_quit_input(self, tmp_path):
        """Test quit key handling."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        ui = QueueMonitorUI(monitor)

        ui._handle_input(ord("q"))
        assert ui.running is False

    def test_ui_handle_help_toggle(self, tmp_path):
        """Test help visibility toggle."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        ui = QueueMonitorUI(monitor)

        assert ui.help_visible is False
        ui._handle_input(ord("?"))
        assert ui.help_visible is True
        ui._handle_input(ord("?"))
        assert ui.help_visible is False

    def test_ui_handle_refresh_input(self, tmp_path):
        """Test refresh key handling."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        ui = QueueMonitorUI(monitor)

        ui.last_poll = time.time()
        old_poll_time = ui.last_poll
        ui._handle_input(ord("r"))
        assert ui.last_poll == 0  # Should be reset to 0 to force refresh


class TestIntegration:
    """Integration tests for queue monitor."""

    def test_monitor_poll_cycle(self, tmp_path):
        """Test complete poll cycle with realistic queue."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        # Setup initial state
        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root

        # First poll (empty)
        monitor.poll()
        assert monitor.poll_count == 1
        assert len(monitor.state.incoming) == 0

        # Add tasks
        incoming_data = {
            "handoff_type": "DELEGATE",
            "task_id": "wave1-task-001",
            "agent": "engineer",
        }
        (queue_root / "incoming" / "DELEGATE-wave1-001.yaml").write_text(
            yaml.dump(incoming_data)
        )

        # Second poll
        monitor.poll()
        assert monitor.poll_count == 2
        assert len(monitor.state.incoming) == 1

        # Metrics should be accessible
        metrics = monitor.get_metrics()
        assert metrics["incoming_count"] == 1
        assert metrics["processing_count"] == 0

    def test_monitor_real_queue_structure(self, tmp_path):
        """Test monitor with realistic multi-state queue."""
        queue_root = tmp_path / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        # Create realistic tasks in each state
        incoming_tasks = [
            {"handoff_type": "DELEGATE", "task_id": "incoming-001", "agent": "engineer"},
            {"handoff_type": "DELEGATE", "task_id": "incoming-002", "agent": "senior-engineer"},
        ]
        for data in incoming_tasks:
            (queue_root / "incoming" / f"DELEGATE-{data['task_id']}.yaml").write_text(yaml.dump(data))

        processing_tasks = [
            {"handoff_type": "DELEGATE", "task_id": "processing-001", "agent": "lead-engineer"},
        ]
        for data in processing_tasks:
            (queue_root / "processing" / f"DELEGATE-{data['task_id']}.yaml").write_text(yaml.dump(data))

        done_tasks = [
            {
                "handoff_type": "HANDBACK",
                "task_id": "done-001",
                "status": "success",
                "metrics": {"duration_seconds": 100},
            },
            {
                "handoff_type": "HANDBACK",
                "task_id": "done-002",
                "status": "success",
                "metrics": {"duration_seconds": 200},
            },
            {
                "handoff_type": "HANDBACK",
                "task_id": "done-003",
                "status": "failure",
                "metrics": {"duration_seconds": 50},
            },
        ]
        for data in done_tasks:
            (queue_root / "done" / f"HANDBACK-{data['task_id']}.yaml").write_text(yaml.dump(data))

        failed_tasks = [
            {
                "handoff_type": "HANDBACK",
                "task_id": "failed-001",
                "status": "failure",
                "metrics": {"duration_seconds": 25},
            },
        ]
        for data in failed_tasks:
            (queue_root / "failed" / f"HANDBACK-{data['task_id']}.yaml").write_text(yaml.dump(data))

        monitor = QueueMonitor(base_dir=str(tmp_path.parent), auto_detect=False)
        monitor.queue_root = queue_root
        monitor.poll()

        # Verify state counts
        assert len(monitor.state.incoming) == 2
        assert len(monitor.state.processing) == 1
        assert len(monitor.state.done) == 3
        assert len(monitor.state.failed) == 1

        # Verify metrics
        metrics = monitor.get_metrics()
        assert metrics["incoming_count"] == 2
        assert metrics["processing_count"] == 1
        assert metrics["done_count"] == 3
        assert metrics["failed_count"] == 1
        assert metrics["succeeded_count"] == 2
        assert metrics["success_rate"] == pytest.approx(66.66, rel=0.01)
        assert metrics["avg_duration_seconds"] == 116  # (100 + 200 + 50) / 3

    def test_monitor_cli_main_function(self, tmp_path):
        """Test main CLI entry point can be called."""
        queue_root = tmp_path / "test-harness" / "test-session" / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_root / state).mkdir(parents=True, exist_ok=True)

        # Create a simple DELEGATE
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "cli-test-001",
            "agent": "engineer",
        }
        (queue_root / "incoming" / "DELEGATE-cli-test.yaml").write_text(yaml.dump(delegate_data))

        # Test that we can create a monitor with the CLI parameters
        monitor = QueueMonitor(
            session_id="test-session",
            harness="test-harness",
            base_dir=str(tmp_path),
        )
        assert monitor.queue_root == queue_root
        monitor.poll()
        assert len(monitor.state.incoming) == 1
