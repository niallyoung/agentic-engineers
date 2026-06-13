"""
Unit tests for queue staleness detection and monitoring.

Tests cover:
- Timestamp recording (created_at, last_updated, state_changes)
- Task age calculation
- Staleness alert thresholds (5 min)
- Staleness escalation thresholds (10 min)
- Multi-state monitoring (incoming, processing, done, failed)
- Edge cases (missing timestamps, malformed JSON, etc.)
"""

import json
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from src.skills.orchestrator.scripts.queue_staleness_monitoring import (
    record_task_timestamp,
    get_task_age_seconds,
    detect_stale_tasks,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_queue():
    """Create a temporary queue directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_root = Path(tmpdir) / "queue"
        queue_root.mkdir()
        for state in ("incoming", "processing", "done", "failed"):
            (queue_root / state).mkdir(exist_ok=True)
        yield queue_root


# ─────────────────────────────────────────────────────────────────────────────
# Test: record_task_timestamp
# ─────────────────────────────────────────────────────────────────────────────

def test_record_task_timestamp_creates_file(temp_queue):
    """Test that timestamp recording creates the sidecar file."""
    task_id = "task-001"
    state = "incoming"

    record_task_timestamp(task_id, temp_queue, state, "created")

    timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"
    assert timestamps_file.exists()


def test_record_task_timestamp_contains_created_at(temp_queue):
    """Test that timestamp file contains created_at field."""
    task_id = "task-001"
    state = "incoming"

    record_task_timestamp(task_id, temp_queue, state, "created")

    timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"
    with timestamps_file.open("r") as f:
        ts_data = json.load(f)

    assert "created_at" in ts_data
    assert ts_data["created_at"]  # Non-empty


def test_record_task_timestamp_tracks_state_changes(temp_queue):
    """Test that state changes are tracked in state_changes array."""
    task_id = "task-001"

    # Record initial creation
    record_task_timestamp(task_id, temp_queue, "incoming", "created")

    # Record claim action (move to processing)
    record_task_timestamp(task_id, temp_queue, "processing", "claimed")

    # Check processing state file
    timestamps_file = temp_queue / "processing" / f"{task_id}.timestamps.json"
    with timestamps_file.open("r") as f:
        ts_data = json.load(f)

    assert "state_changes" in ts_data
    assert len(ts_data["state_changes"]) >= 1
    assert ts_data["state_changes"][-1]["action"] == "claimed"
    assert ts_data["state_changes"][-1]["state"] == "processing"


def test_record_task_timestamp_immutable_created_at(temp_queue):
    """Test that created_at timestamp is preserved across updates."""
    task_id = "task-001"

    # Record initial creation
    record_task_timestamp(task_id, temp_queue, "incoming", "created")
    timestamps_file = temp_queue / "incoming" / f"{task_id}.timestamps.json"
    with timestamps_file.open("r") as f:
        initial_data = json.load(f)
    initial_created_at = initial_data["created_at"]

    # Wait a bit and record another action
    time.sleep(0.1)
    record_task_timestamp(task_id, temp_queue, "incoming", "updated")

    with timestamps_file.open("r") as f:
        updated_data = json.load(f)

    assert updated_data["created_at"] == initial_created_at


def test_record_task_timestamp_updates_last_updated(temp_queue):
    """Test that last_updated is updated on each record."""
    task_id = "task-001"

    record_task_timestamp(task_id, temp_queue, "incoming", "created")
    timestamps_file = temp_queue / "incoming" / f"{task_id}.timestamps.json"
    with timestamps_file.open("r") as f:
        data1 = json.load(f)
    last_updated_1 = data1["last_updated"]

    time.sleep(0.1)
    record_task_timestamp(task_id, temp_queue, "incoming", "updated")

    with timestamps_file.open("r") as f:
        data2 = json.load(f)
    last_updated_2 = data2["last_updated"]

    # last_updated should be different
    assert last_updated_2 >= last_updated_1


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_task_age_seconds
# ─────────────────────────────────────────────────────────────────────────────

def test_get_task_age_returns_float(temp_queue):
    """Test that task age is returned as a float."""
    task_id = "task-001"
    state = "incoming"

    record_task_timestamp(task_id, temp_queue, state, "created")
    time.sleep(0.5)

    age_sec = get_task_age_seconds(task_id, temp_queue, state)

    assert isinstance(age_sec, float)
    assert age_sec >= 0.4  # At least 400ms have passed


def test_get_task_age_returns_none_if_no_timestamps(temp_queue):
    """Test that None is returned if timestamps file doesn't exist."""
    age_sec = get_task_age_seconds("nonexistent", temp_queue, "incoming")
    assert age_sec is None


def test_get_task_age_nonzero_for_aged_task(temp_queue):
    """Test that age increases over time."""
    task_id = "task-001"
    state = "incoming"

    record_task_timestamp(task_id, temp_queue, state, "created")

    # Record now
    age1 = get_task_age_seconds(task_id, temp_queue, state)

    # Sleep and check again
    time.sleep(0.2)
    age2 = get_task_age_seconds(task_id, temp_queue, state)

    assert age2 > age1


# ─────────────────────────────────────────────────────────────────────────────
# Test: detect_stale_tasks – Alert Threshold (5 min)
# ─────────────────────────────────────────────────────────────────────────────

def test_detect_stale_tasks_alert_threshold(temp_queue):
    """Test that tasks exceeding alert threshold are detected."""
    task_id = "task-alert"
    state = "incoming"

    # Create task with old timestamp (6 minutes ago)
    record_task_timestamp(task_id, temp_queue, state, "created")
    timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"

    old_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=360)).isoformat()
    with timestamps_file.open("r") as f:
        ts_data = json.load(f)
    ts_data["created_at"] = old_time
    with timestamps_file.open("w") as f:
        json.dump(ts_data, f)

    # Create dummy DELEGATE file
    (temp_queue / state / f"{task_id}.yaml").touch()

    # Run detection
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300)

    assert result["alerted_count"] >= 1
    assert len(result["stale_tasks"]) >= 1
    assert result["stale_tasks"][0]["task_id"] == task_id
    assert result["stale_tasks"][0]["alert_level"] == "ALERT"


# ─────────────────────────────────────────────────────────────────────────────
# Test: detect_stale_tasks – Escalation Threshold (10 min)
# ─────────────────────────────────────────────────────────────────────────────

def test_detect_stale_tasks_escalation_threshold(temp_queue):
    """Test that tasks exceeding escalation threshold are detected."""
    task_id = "task-escalate"
    state = "processing"

    # Create task with very old timestamp (11 minutes ago)
    record_task_timestamp(task_id, temp_queue, state, "created")
    timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"

    old_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=660)).isoformat()
    with timestamps_file.open("r") as f:
        ts_data = json.load(f)
    ts_data["created_at"] = old_time
    with timestamps_file.open("w") as f:
        json.dump(ts_data, f)

    # Create dummy DELEGATE file
    (temp_queue / state / f"{task_id}.yaml").touch()

    # Run detection
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300, escalation_threshold_sec=600)

    assert result["escalated_count"] >= 1
    assert len(result["stale_tasks"]) >= 1
    assert result["stale_tasks"][0]["alert_level"] == "ESCALATE"


# ─────────────────────────────────────────────────────────────────────────────
# Test: detect_stale_tasks – Multi-State Monitoring
# ─────────────────────────────────────────────────────────────────────────────

def test_detect_stale_tasks_monitors_multiple_states(temp_queue):
    """Test that staleness detection monitors both incoming and processing."""
    # Create old task in incoming
    incoming_task = "task-incoming"
    record_task_timestamp(incoming_task, temp_queue, "incoming", "created")
    (temp_queue / "incoming" / f"{incoming_task}.yaml").touch()

    # Create old task in processing
    processing_task = "task-processing"
    record_task_timestamp(processing_task, temp_queue, "processing", "created")
    (temp_queue / "processing" / f"{processing_task}.yaml").touch()

    # Backdate both
    for task_id, state in [(incoming_task, "incoming"), (processing_task, "processing")]:
        timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"
        old_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=360)).isoformat()
        with timestamps_file.open("r") as f:
            ts_data = json.load(f)
        ts_data["created_at"] = old_time
        with timestamps_file.open("w") as f:
            json.dump(ts_data, f)

    # Run detection
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300)

    assert result["alerted_count"] >= 2
    task_ids = {t["task_id"] for t in result["stale_tasks"]}
    assert incoming_task in task_ids
    assert processing_task in task_ids


def test_detect_stale_tasks_ignores_done_and_failed(temp_queue):
    """Test that done/ and failed/ states are not checked for staleness."""
    # Create old task in done (should be ignored)
    done_task = "task-done"
    record_task_timestamp(done_task, temp_queue, "done", "created")
    (temp_queue / "done" / f"{done_task}.yaml").touch()

    # Backdate it
    timestamps_file = temp_queue / "done" / f"{done_task}.timestamps.json"
    old_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=360)).isoformat()
    with timestamps_file.open("r") as f:
        ts_data = json.load(f)
    ts_data["created_at"] = old_time
    with timestamps_file.open("w") as f:
        json.dump(ts_data, f)

    # Run detection
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300)

    # Should not find the task in done/
    assert result["alerted_count"] == 0
    assert len(result["stale_tasks"]) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

def test_detect_stale_tasks_handles_missing_timestamps_file(temp_queue):
    """Test that detection handles missing timestamps gracefully."""
    task_id = "task-no-ts"

    # Create YAML but NO timestamps file
    (temp_queue / "incoming" / f"{task_id}.yaml").touch()

    # Should not crash
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300)

    assert result["alerted_count"] == 0


def test_detect_stale_tasks_handles_malformed_timestamps_json(temp_queue):
    """Test that detection handles corrupted timestamps file."""
    task_id = "task-bad-json"
    state = "incoming"

    # Create YAML file
    (temp_queue / state / f"{task_id}.yaml").touch()

    # Create malformed timestamps file
    timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"
    with timestamps_file.open("w") as f:
        f.write("{invalid json")

    # Should not crash
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300)

    assert result["alerted_count"] == 0


def test_detect_stale_tasks_empty_queue(temp_queue):
    """Test that detection works on empty queue."""
    result = detect_stale_tasks(temp_queue, alert_threshold_sec=300)

    assert result["alerted_count"] == 0
    assert result["escalated_count"] == 0
    assert len(result["stale_tasks"]) == 0


def test_detect_stale_tasks_with_custom_thresholds(temp_queue):
    """Test that custom thresholds are applied correctly."""
    task_id = "task-custom"
    state = "incoming"

    # Create task that is 2 minutes old
    record_task_timestamp(task_id, temp_queue, state, "created")
    (temp_queue / state / f"{task_id}.yaml").touch()

    timestamps_file = temp_queue / state / f"{task_id}.timestamps.json"
    old_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=120)).isoformat()
    with timestamps_file.open("r") as f:
        ts_data = json.load(f)
    ts_data["created_at"] = old_time
    with timestamps_file.open("w") as f:
        json.dump(ts_data, f)

    # With default thresholds (5 min alert, 10 min escalate) - should not alert
    result1 = detect_stale_tasks(temp_queue, alert_threshold_sec=300, escalation_threshold_sec=600)
    assert result1["alerted_count"] == 0

    # With custom thresholds (1 min alert, 3 min escalate) - should alert
    result2 = detect_stale_tasks(temp_queue, alert_threshold_sec=60, escalation_threshold_sec=180)
    assert result2["alerted_count"] >= 1
