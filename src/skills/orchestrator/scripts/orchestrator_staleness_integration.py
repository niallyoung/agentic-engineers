"""
Orchestrator Skill – Staleness Monitoring Integration

Adds staleness detection to the OrchestratorSkill class.
Provides methods to:
- Record timestamps when tasks are created/claimed
- Monitor staleness with configurable SLA thresholds
- Emit alerts and escalations to span files

Usage in OrchestratorSkill:
    1. In claim_task(): call self._record_task_timestamp(task_id, "processing", "claimed")
    2. In poll_queue(): call self.monitor_staleness() periodically
    3. Timestamps are automatically tracked in .timestamps.json sidecars
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_task_staleness_metadata(queue_root: Path, session_id: str) -> Dict[str, Any]:
    """
    Get or create staleness monitoring metadata for a queue session.

    Maintains:
    - alert_threshold_sec: Seconds before alert (default 300 = 5 min)
    - escalation_threshold_sec: Seconds before escalation (default 600 = 10 min)
    - last_staleness_check: ISO timestamp of last check

    Args:
        queue_root: Path to queue root directory
        session_id: Session identifier

    Returns:
        Dictionary with staleness configuration
    """
    session_root = queue_root.parent
    staleness_path = session_root / "staleness.json"

    if staleness_path.exists():
        try:
            with staleness_path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            pass

    # Create default metadata
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    metadata = {
        "session_id": session_id,
        "queue_created_at": now_iso,
        "alert_threshold_sec": 300,  # 5 minutes
        "escalation_threshold_sec": 600,  # 10 minutes
        "last_staleness_check": now_iso,
    }

    try:
        with staleness_path.open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write staleness metadata: {e}")

    return metadata


def update_staleness_check_timestamp(queue_root: Path) -> None:
    """
    Update the last_staleness_check timestamp in the staleness metadata.

    Args:
        queue_root: Path to queue root directory
    """
    session_root = queue_root.parent
    staleness_path = session_root / "staleness.json"

    if not staleness_path.exists():
        return

    try:
        with staleness_path.open("r", encoding="utf-8") as fh:
            metadata = json.load(fh)
    except json.JSONDecodeError:
        return

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    metadata["last_staleness_check"] = now_iso

    try:
        with staleness_path.open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)
    except Exception as e:
        logger.warning(f"Failed to update staleness check timestamp: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Integration Methods (to be added to OrchestratorSkill)
# ─────────────────────────────────────────────────────────────────────────────

STALENESS_INTEGRATION_METHODS = """
    def _record_task_timestamp(
        self,
        task_id: str,
        state: str = "incoming",
        action: str = "created",
    ) -> None:
        \"\"\"
        Record a task timestamp event in a sidecar file.

        Creates/updates <queue_root>/<state>/<task_id>.timestamps.json with:
        - 'created_at': When task was first created (immutable)
        - 'last_updated': When task was last modified
        - 'state_changes': Array of {timestamp, action, state} transitions

        Args:
            task_id: Task identifier
            state: Queue state (incoming, processing, done, failed)
            action: Action description (created, claimed, completed, failed)
        \"\"\"
        state_dir = self.queue_root / state
        state_dir.mkdir(parents=True, exist_ok=True)

        timestamps_path = state_dir / f"{task_id}.timestamps.json"
        now_iso = datetime.now(tz=timezone.utc).isoformat()

        if timestamps_path.exists():
            try:
                with timestamps_path.open("r") as f:
                    ts_data = json.load(f)
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
            with timestamps_path.open("w") as f:
                json.dump(ts_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record timestamp for task {task_id}: {e}")

    def monitor_staleness(self) -> Dict[str, Any]:
        \"\"\"
        Monitor queue for stale tasks and emit alerts/escalations.

        Scans incoming/ and processing/ for aged tasks.
        Issues alerts at 5 min, escalates at 10 min (configurable via staleness.json).

        Returns:
            Dict with keys:
            - 'alerted_count': Number of tasks alerted
            - 'escalated_count': Number of tasks escalated
            - 'stale_tasks': List of {task_id, state, age_sec, alert_level}
        \"\"\"
        # Get staleness configuration
        staleness_meta = get_task_staleness_metadata(self.queue_root, self.session_id)
        STALENESS_ALERT_SEC = staleness_meta.get("alert_threshold_sec", 300)
        STALENESS_ESCALATION_SEC = staleness_meta.get("escalation_threshold_sec", 600)

        alerted_count = 0
        escalated_count = 0
        stale_tasks = []

        now = datetime.now(tz=timezone.utc)

        # Monitor incoming and processing states
        for state in ("incoming", "processing"):
            state_dir = self.queue_root / state
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
                    with timestamps_file.open("r") as f:
                        ts_data = json.load(f)
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

                # Check staleness thresholds
                if age_sec >= STALENESS_ESCALATION_SEC:
                    escalated_count += 1
                    alert_level = "ESCALATE"
                    logger.error(
                        f"STALE TASK ESCALATED: {task_id} in {state}/ "
                        f"(age={age_sec:.0f}s, threshold={STALENESS_ESCALATION_SEC}s)"
                    )

                    self.capture_span(
                        "staleness_escalation",
                        task_id=task_id,
                        state=state,
                        age_sec=age_sec,
                        alert_level=alert_level,
                    )

                    stale_tasks.append({
                        "task_id": task_id,
                        "state": state,
                        "age_sec": age_sec,
                        "alert_level": alert_level,
                    })

                elif age_sec >= STALENESS_ALERT_SEC:
                    alerted_count += 1
                    alert_level = "ALERT"
                    logger.warning(
                        f"STALE TASK ALERTED: {task_id} in {state}/ "
                        f"(age={age_sec:.0f}s, threshold={STALENESS_ALERT_SEC}s)"
                    )

                    self.capture_span(
                        "staleness_alert",
                        task_id=task_id,
                        state=state,
                        age_sec=age_sec,
                        alert_level=alert_level,
                    )

                    stale_tasks.append({
                        "task_id": task_id,
                        "state": state,
                        "age_sec": age_sec,
                        "alert_level": alert_level,
                    })

        # Update last check timestamp
        update_staleness_check_timestamp(self.queue_root)

        if alerted_count > 0 or escalated_count > 0:
            logger.info(
                f"Staleness check: alerted={alerted_count}, escalated={escalated_count}"
            )

        return {
            "alerted_count": alerted_count,
            "escalated_count": escalated_count,
            "stale_tasks": stale_tasks,
        }
"""
