"""
Queue Staleness Monitoring Module

Provides timestamp tracking and staleness detection for queue tasks.
Integrates with OrchestratorSkill to track task ages and emit alerts/escalations.

Features:
- Per-task timestamp tracking (created_at, last_updated, state_changes)
- Staleness detection (alert at 5 min, escalate at 10 min)
- Span/metrics emission for observability
- Configurable SLA thresholds
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Timestamp Recording
# ─────────────────────────────────────────────────────────────────────────────

def record_task_timestamp(
    task_id: str,
    queue_root: Path,
    state: str = "incoming",
    action: str = "created",
) -> None:
    """
    Record a task timestamp event in a sidecar file.

    Creates/updates <queue_root>/<state>/<task_id>.timestamps.json with:
    - 'created_at': When task was first created (immutable)
    - 'last_updated': When task was last modified
    - 'state_changes': Array of {timestamp, action, state} transitions

    Args:
        task_id: Task identifier
        queue_root: Path to the queue root directory
        state: Queue state (incoming, processing, done, failed)
        action: Action description (created, claimed, completed, failed)
    """
    state_dir = queue_root / state
    state_dir.mkdir(parents=True, exist_ok=True)

    timestamps_path = state_dir / f"{task_id}.timestamps.json"
    now_iso = datetime.now(tz=timezone.utc).isoformat()

    if timestamps_path.exists():
        try:
            with timestamps_path.open("r", encoding="utf-8") as fh:
                ts_data = json.load(fh)
        except json.JSONDecodeError:
            ts_data = {"created_at": now_iso}
    else:
        ts_data = {"created_at": now_iso}

    ts_data["last_updated"] = now_iso

    if "state_changes" not in ts_data:
        ts_data["state_changes"] = []

    ts_data["state_changes"].append({
        "timestamp": now_iso,
        "action": action,
        "state": state,
    })

    try:
        with timestamps_path.open("w", encoding="utf-8") as fh:
            json.dump(ts_data, fh, indent=2)
    except Exception as e:
        logger.warning(f"Failed to record timestamp for task {task_id}: {e}")


def get_task_age_seconds(
    task_id: str,
    queue_root: Path,
    state: str = "incoming",
) -> Optional[float]:
    """
    Get the age (in seconds) of a task since creation.

    Args:
        task_id: Task identifier
        queue_root: Path to the queue root directory
        state: Queue state where task currently resides

    Returns:
        Age in seconds (as float), or None if timestamps file not found
    """
    timestamps_path = queue_root / state / f"{task_id}.timestamps.json"

    if not timestamps_path.exists():
        return None

    try:
        with timestamps_path.open("r", encoding="utf-8") as fh:
            ts_data = json.load(fh)
    except (json.JSONDecodeError, IOError):
        return None

    created_at_str = ts_data.get("created_at")
    if not created_at_str:
        return None

    try:
        created_at = datetime.fromisoformat(created_at_str)
        now = datetime.now(tz=timezone.utc)
        return (now - created_at).total_seconds()
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Staleness Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_stale_tasks(
    queue_root: Path,
    alert_threshold_sec: int = 300,
    escalation_threshold_sec: int = 600,
) -> Dict[str, Any]:
    """
    Scan queue for stale tasks and classify them by alert level.

    Monitors incoming/ and processing/ directories only
    (done/ and failed/ are already resolved).

    Args:
        queue_root: Path to the queue root directory
        alert_threshold_sec: Seconds before alert (default: 300 = 5 min)
        escalation_threshold_sec: Seconds before escalation (default: 600 = 10 min)

    Returns:
        Dict with keys:
        - 'alerted_count': Number of tasks in alert state
        - 'escalated_count': Number of tasks in escalation state
        - 'stale_tasks': List of {task_id, state, age_sec, alert_level}
    """
    alerted_count = 0
    escalated_count = 0
    stale_tasks: List[Dict[str, Any]] = []

    now = datetime.now(tz=timezone.utc)

    # Monitor incoming/ and processing/ states
    for state in ("incoming", "processing"):
        state_dir = queue_root / state
        if not state_dir.exists():
            continue

        try:
            yaml_files = list(state_dir.glob("*.yaml"))
        except Exception as e:
            logger.error(f"Failed to list {state} directory: {e}")
            continue

        for yaml_file in yaml_files:
            task_id = yaml_file.stem

            # Get task timestamp
            timestamps_file = state_dir / f"{task_id}.timestamps.json"
            if not timestamps_file.exists():
                continue

            try:
                with timestamps_file.open("r", encoding="utf-8") as fh:
                    ts_data = json.load(fh)
            except (json.JSONDecodeError, IOError):
                continue

            created_at_str = ts_data.get("created_at")
            if not created_at_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
                age_sec = (now - created_at).total_seconds()
            except (ValueError, TypeError):
                continue

            # Classify by alert level
            if age_sec >= escalation_threshold_sec:
                escalated_count += 1
                alert_level = "ESCALATE"
                stale_tasks.append({
                    "task_id": task_id,
                    "state": state,
                    "age_sec": age_sec,
                    "alert_level": alert_level,
                })
                logger.error(
                    f"STALE TASK ESCALATED: {task_id} in {state}/ "
                    f"(age={age_sec:.0f}s, threshold={escalation_threshold_sec}s)"
                )

            elif age_sec >= alert_threshold_sec:
                alerted_count += 1
                alert_level = "ALERT"
                stale_tasks.append({
                    "task_id": task_id,
                    "state": state,
                    "age_sec": age_sec,
                    "alert_level": alert_level,
                })
                logger.warning(
                    f"STALE TASK ALERTED: {task_id} in {state}/ "
                    f"(age={age_sec:.0f}s, threshold={alert_threshold_sec}s)"
                )

    return {
        "alerted_count": alerted_count,
        "escalated_count": escalated_count,
        "stale_tasks": stale_tasks,
    }
