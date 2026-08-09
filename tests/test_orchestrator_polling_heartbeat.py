"""
Tests for OrchestratorSkill heartbeat/stall-detection configuration.

Covers:
- PollingConfig schema and serialization
- Heartbeat tracking and update
- Stalled task detection (no heartbeat for N seconds)
- Stalled task recovery with retry backoff

NOTE (queue-polling removal, direct-spawn migration): PollingConfig's
poll_interval_fast/poll_interval_idle/idle_threshold_polls/deep_sleep_sec
fields, and run_idle_loop()/_deep_sleep()/_deep_sleep_polling() themselves,
have been removed — see orchestrator_skill.py. This file now covers only
the heartbeat/stall-detection/retry substrate that survives under direct
sub-agent spawning.
"""

import json
import os
import pytest
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.skills.orchestrator.scripts.orchestrator_skill import (
    OrchestratorSkill,
    PollingConfig,
    TaskClaimError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_queue(tmp_path):
    """Create a temporary queue directory structure."""
    queue_dir = tmp_path / "queue"
    for state in ("incoming", "processing", "done", "failed"):
        state_dir = queue_dir / state
        state_dir.mkdir(parents=True)
        (state_dir / ".keep.me").touch()
    (queue_dir.parent / "spans").mkdir(parents=True)
    return queue_dir


@pytest.fixture
def custom_config():
    """Create a custom PollingConfig with short timeouts for testing."""
    return PollingConfig(
        heartbeat_timeout_sec=5,
        task_deadline_sec=10,
        retry_max_attempts=2,
        retry_backoff_multiplier=2.0,
    )


@pytest.fixture
def orchestrator_with_config(tmp_queue, custom_config, monkeypatch):
    """Create OrchestratorSkill with custom config and temp queue."""
    monkeypatch.setenv("AGENTIC_SESSION_ID", "test-session-id")
    return OrchestratorSkill(
        queue_root=str(tmp_queue),
        polling_config=custom_config,
    )


@pytest.fixture
def orchestrator_default(tmp_queue, monkeypatch):
    """Create OrchestratorSkill with default config and temp queue."""
    monkeypatch.setenv("AGENTIC_SESSION_ID", "test-session-id")
    return OrchestratorSkill(queue_root=str(tmp_queue))


# ─────────────────────────────────────────────────────────────────────────────
# Test PollingConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestPollingConfig:
    """Test PollingConfig schema and serialization."""

    def test_polling_config_defaults(self):
        """Test that PollingConfig uses sensible defaults."""
        config = PollingConfig()
        assert config.heartbeat_timeout_sec == 120
        assert config.task_deadline_sec == 600
        assert config.retry_max_attempts == 3

    def test_polling_config_custom(self, custom_config):
        """Test that PollingConfig accepts custom values."""
        assert custom_config.heartbeat_timeout_sec == 5
        assert custom_config.task_deadline_sec == 10

    def test_polling_config_to_dict(self, custom_config):
        """Test that PollingConfig can be serialized to dict."""
        config_dict = custom_config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["heartbeat_timeout_sec"] == 5

    def test_polling_config_from_dict(self):
        """Test that PollingConfig can be deserialized from dict."""
        config_dict = {
            "heartbeat_timeout_sec": 30,
            "task_deadline_sec": 120,
            "retry_max_attempts": 5,
            "retry_backoff_multiplier": 1.5,
        }
        config = PollingConfig.from_dict(config_dict)
        assert config.heartbeat_timeout_sec == 30


# ─────────────────────────────────────────────────────────────────────────────
# Test Initialization
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestratorInitialization:
    """Test OrchestratorSkill initialization with polling config."""

    def test_initialization_with_default_config(self, orchestrator_default):
        """Test initialization with default polling config."""
        assert isinstance(orchestrator_default.config, PollingConfig)
        assert orchestrator_default.config.heartbeat_timeout_sec == 120

    def test_initialization_with_custom_config(self, orchestrator_with_config):
        """Test initialization with custom polling config."""
        assert orchestrator_with_config.config.heartbeat_timeout_sec == 5

    def test_heartbeat_tracker_initialized(self, orchestrator_default):
        """Test that heartbeat tracker is initialized."""
        assert hasattr(orchestrator_default, "heartbeat_tracker")
        assert isinstance(orchestrator_default.heartbeat_tracker, dict)
        assert len(orchestrator_default.heartbeat_tracker) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test Heartbeat Management
# ─────────────────────────────────────────────────────────────────────────────

class TestHeartbeatManagement:
    """Test heartbeat tracking and updates."""

    def test_update_heartbeat_records_timestamp(self, orchestrator_default):
        """Test that update_heartbeat records current timestamp."""
        task_id = "test-task-001"
        before = time.time()
        orchestrator_default.update_heartbeat(task_id)
        after = time.time()

        assert task_id in orchestrator_default.heartbeat_tracker
        recorded_time = orchestrator_default.heartbeat_tracker[task_id]
        assert before <= recorded_time <= after

    def test_update_heartbeat_multiple_tasks(self, orchestrator_default):
        """Test heartbeat tracking for multiple tasks."""
        task_ids = ["task-1", "task-2", "task-3"]
        for task_id in task_ids:
            orchestrator_default.update_heartbeat(task_id)

        assert len(orchestrator_default.heartbeat_tracker) == 3
        for task_id in task_ids:
            assert task_id in orchestrator_default.heartbeat_tracker

    def test_update_heartbeat_replaces_old_timestamp(self, orchestrator_default):
        """Test that update_heartbeat replaces old timestamp."""
        task_id = "test-task-001"
        orchestrator_default.update_heartbeat(task_id)
        first_time = orchestrator_default.heartbeat_tracker[task_id]

        time.sleep(0.1)
        orchestrator_default.update_heartbeat(task_id)
        second_time = orchestrator_default.heartbeat_tracker[task_id]

        assert second_time > first_time


# ─────────────────────────────────────────────────────────────────────────────
# Test Stalled Task Detection
# ─────────────────────────────────────────────────────────────────────────────

class TestStalledTaskDetection:
    """Test detection of stalled tasks (no heartbeat)."""

    def test_detect_stalled_tasks_empty_queue(self, orchestrator_with_config):
        """Test detection when processing queue is empty."""
        stalled = orchestrator_with_config.detect_stalled_tasks()
        assert isinstance(stalled, list)
        assert len(stalled) == 0

    def test_detect_stalled_tasks_with_fresh_heartbeat(self, orchestrator_with_config, tmp_queue):
        """Test that fresh heartbeats are not detected as stalled."""
        task_id = "fresh-task"

        # Create metadata file
        processing_dir = tmp_queue / "processing"
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        metadata = {
            "task_id": task_id,
            "claimed_at": now_iso,
            "retry_count": 0,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Update heartbeat just now
        orchestrator_with_config.update_heartbeat(task_id)

        # Detect stalled
        stalled = orchestrator_with_config.detect_stalled_tasks()
        assert task_id not in stalled

    def test_detect_stalled_tasks_timeout_exceeded(self, orchestrator_with_config, tmp_queue):
        """Test that tasks without heartbeat for > timeout are detected as stalled."""
        task_id = "stalled-task"

        # Create metadata file with claimed_at in the past
        processing_dir = tmp_queue / "processing"
        past_time = datetime.now(tz=timezone.utc)
        past_time = past_time.replace(microsecond=0)  # Remove microseconds for consistency
        past_iso = (past_time.timestamp() - 10) * 1  # 10 seconds ago
        past_dt = datetime.fromtimestamp(past_iso, tz=timezone.utc)
        past_iso = past_dt.isoformat()

        metadata = {
            "task_id": task_id,
            "claimed_at": past_iso,
            "retry_count": 0,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Don't update heartbeat (timeout is 5 seconds)
        # Detect stalled
        stalled = orchestrator_with_config.detect_stalled_tasks()
        assert task_id in stalled

    def test_detect_stalled_tasks_from_heartbeat_tracker(self, orchestrator_with_config, tmp_queue):
        """Test stalled detection when heartbeat tracker shows timeout."""
        task_id = "tracked-task"

        # Create metadata
        processing_dir = tmp_queue / "processing"
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        metadata = {
            "task_id": task_id,
            "claimed_at": now_iso,
            "retry_count": 0,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Update heartbeat to old time (> 5 seconds ago)
        old_time = time.time() - 10
        orchestrator_with_config.heartbeat_tracker[task_id] = old_time

        # Detect stalled
        stalled = orchestrator_with_config.detect_stalled_tasks()
        assert task_id in stalled


# ─────────────────────────────────────────────────────────────────────────────
# Test Stalled Task Recovery
# ─────────────────────────────────────────────────────────────────────────────

class TestStalledTaskRecovery:
    """Test recovery of stalled tasks."""

    def test_recover_stalled_tasks_empty_queue(self, orchestrator_with_config):
        """Test recovery when there are no stalled tasks."""
        recovered, escalated = orchestrator_with_config.recover_stalled_tasks()
        assert recovered == 0
        assert escalated == 0

    def test_recover_stalled_tasks_increments_retry_count(self, orchestrator_with_config, tmp_queue):
        """Test that recovery increments retry count and moves to retry-pending."""
        task_id = "stalled-to-recover"

        # Create metadata with old heartbeat
        processing_dir = tmp_queue / "processing"
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        metadata = {
            "task_id": task_id,
            "claimed_at": now_iso,
            "retry_count": 0,
            "last_error": None,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Create DELEGATE file
        delegate_file = processing_dir / f"{task_id}.yaml"
        delegate_file.write_text("task_id: " + task_id)

        # Set old heartbeat to trigger stall detection
        old_time = time.time() - 10
        orchestrator_with_config.heartbeat_tracker[task_id] = old_time

        # Recover
        recovered, escalated = orchestrator_with_config.recover_stalled_tasks()
        assert recovered == 1
        assert escalated == 0

        # Verify task moved to retry-pending
        retry_pending_dir = tmp_queue / "retry-pending"
        assert (retry_pending_dir / f"{task_id}.yaml").exists()
        assert (retry_pending_dir / f"{task_id}.meta.json").exists()

        # Verify retry count incremented
        with (retry_pending_dir / f"{task_id}.meta.json").open("r") as f:
            new_metadata = json.load(f)
        assert new_metadata["retry_count"] == 1

    def test_recover_stalled_tasks_escalates_on_max_retries(self, orchestrator_with_config, tmp_queue):
        """Test that tasks exceeding max retries are escalated."""
        task_id = "stalled-exhausted"

        # Create metadata with max retry count already reached
        processing_dir = tmp_queue / "processing"
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        metadata = {
            "task_id": task_id,
            "claimed_at": now_iso,
            "retry_count": 2,  # At max (config says 2)
            "last_error": None,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Create DELEGATE file
        delegate_file = processing_dir / f"{task_id}.yaml"
        delegate_file.write_text("task_id: " + task_id)

        # Set old heartbeat
        old_time = time.time() - 10
        orchestrator_with_config.heartbeat_tracker[task_id] = old_time

        # Recover
        recovered, escalated = orchestrator_with_config.recover_stalled_tasks()
        assert recovered == 0
        assert escalated == 1

        # Verify escalation DELEGATE created in incoming/
        incoming_dir = tmp_queue / "incoming"
        escalation_files = list(incoming_dir.glob(f"*escalated*"))
        assert len(escalation_files) > 0

        # Verify task moved to done/
        done_dir = tmp_queue / "done"
        assert (done_dir / f"{task_id}.yaml").exists()

    def test_recover_stalled_tasks_removes_from_heartbeat_tracker(self, orchestrator_with_config, tmp_queue):
        """Test that recovered tasks are removed from heartbeat tracker."""
        task_id = "stalled-to-clear"

        # Create metadata
        processing_dir = tmp_queue / "processing"
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        metadata = {
            "task_id": task_id,
            "claimed_at": now_iso,
            "retry_count": 0,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Create DELEGATE
        delegate_file = processing_dir / f"{task_id}.yaml"
        delegate_file.write_text("task_id: " + task_id)

        # Set old heartbeat
        old_time = time.time() - 10
        orchestrator_with_config.heartbeat_tracker[task_id] = old_time

        # Recover
        orchestrator_with_config.recover_stalled_tasks()

        # Verify removed from tracker
        assert task_id not in orchestrator_with_config.heartbeat_tracker


# ─────────────────────────────────────────────────────────────────────────────
# NOTE (queue-polling removal, direct-spawn migration): TestIdleLoopWithConfig
# and TestDeepSleepWithConfig previously lived here, testing
# OrchestratorSkill.run_idle_loop() / _deep_sleep() / _deep_sleep_polling().
# Those methods have been removed (see orchestrator_skill.py) — they
# implemented the harness-idle-triggered sleep/deep-sleep mechanism driven by
# the now-deleted orchestrator-scheduler skill and harness idle_loop.py
# modules, which direct sub-agent spawning replaces. PollingConfig itself
# (TestPollingConfig, above) and the heartbeat/stall-detection/recovery
# machinery (TestHeartbeatManagement, TestStalledTaskDetection,
# TestStalledTaskRecovery, below) are unaffected and remain fully tested —
# none of them loop or sleep themselves.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for polling, heartbeat, and recovery."""

    def test_end_to_end_stalled_detection_and_recovery(self, orchestrator_with_config, tmp_queue):
        """Test full flow: create task, let it stall, detect, and recover."""
        task_id = "e2e-stalled-task"

        # Step 1: Create a task (claim it)
        processing_dir = tmp_queue / "processing"
        incoming_dir = tmp_queue / "incoming"

        # Create incoming DELEGATE
        delegate_file = incoming_dir / f"{task_id}.yaml"
        delegate_file.write_text(
            f"handoff_type: DELEGATE\n"
            f"task_id: {task_id}\n"
            f"agent: engineer\n"
            f"scope: Test task\n"
            f"plan:\n"
            f"  - Do something\n"
            f"success_criteria:\n"
            f"  - It works\n"
        )

        # Manually move to processing as if claimed
        processing_file = processing_dir / f"{task_id}.yaml"
        delegate_file.rename(processing_file)

        # Create metadata with old timestamp to trigger stall
        old_time = datetime.now(tz=timezone.utc)
        old_time = old_time.replace(microsecond=0)
        old_time_iso = (old_time.timestamp() - 10) * 1  # 10 seconds ago
        old_dt = datetime.fromtimestamp(old_time_iso, tz=timezone.utc)
        old_iso = old_dt.isoformat()

        metadata = {
            "task_id": task_id,
            "claimed_at": old_iso,
            "retry_count": 0,
        }
        meta_file = processing_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f)

        # Step 2: Don't update heartbeat - let it stall

        # Step 3: Detect stalled
        stalled = orchestrator_with_config.detect_stalled_tasks()
        assert task_id in stalled

        # Step 4: Recover stalled
        recovered, escalated = orchestrator_with_config.recover_stalled_tasks()
        assert recovered == 1
        assert escalated == 0

        # Step 5: Verify task in retry-pending
        retry_pending_dir = tmp_queue / "retry-pending"
        assert (retry_pending_dir / f"{task_id}.yaml").exists()

    def test_polling_config_persists_across_poll_cycles(self, orchestrator_with_config):
        """Test that config is stable across multiple poll_queue() cycles."""
        # Capture config value
        initial_heartbeat_timeout = orchestrator_with_config.config.heartbeat_timeout_sec

        # Simulate multiple poll cycles (just check config doesn't change)
        for _ in range(5):
            assert orchestrator_with_config.config.heartbeat_timeout_sec == initial_heartbeat_timeout
