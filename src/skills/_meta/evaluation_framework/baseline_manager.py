"""
Baseline Management System for Continuous CI/CD Pipeline

Handles loading, saving, and versioning of evaluation baselines.
Supports monthly snapshots and baseline comparison.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List


class BaselineManager:
    """Manages evaluation baselines and snapshots."""

    BASELINE_DIR = Path(".github/baseline_snapshots")
    CURRENT_BASELINE_FILE = "current_baseline.json"
    ARCHIVE_DIR = Path(".github/baseline_snapshots/archive")

    def __init__(self, baseline_dir: Optional[Path] = None):
        """Initialize baseline manager."""
        if baseline_dir:
            self.baseline_dir = baseline_dir
        else:
            self.baseline_dir = self.BASELINE_DIR

        # Ensure directories exist
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    @property
    def archive_dir(self) -> Path:
        """Get archive directory."""
        return self.baseline_dir / "archive"

    @archive_dir.setter
    def archive_dir(self, value: Path):
        """Set archive directory."""
        pass

    def get_current_baseline(self) -> Optional[Dict[str, Any]]:
        """
        Get the current baseline.

        Returns:
            Baseline data or None if not found
        """
        baseline_file = self.baseline_dir / self.CURRENT_BASELINE_FILE
        if not baseline_file.exists():
            return None

        try:
            with open(baseline_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def save_baseline(self, results: Dict[str, Any]) -> str:
        """
        Save evaluation results as the current baseline.

        Args:
            results: Evaluation results to save as baseline

        Returns:
            Path to saved baseline file
        """
        baseline_file = self.baseline_dir / self.CURRENT_BASELINE_FILE

        # Add metadata
        baseline_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "baseline_version": 1,
            "results": results,
        }

        with open(baseline_file, "w") as f:
            json.dump(baseline_data, f, indent=2)

        return str(baseline_file)

    def create_monthly_snapshot(self, results: Dict[str, Any]) -> str:
        """
        Create a monthly snapshot of evaluation results.

        Args:
            results: Evaluation results to snapshot

        Returns:
            Path to snapshot file
        """
        # Create snapshot filename with current date
        now = datetime.utcnow()
        snapshot_filename = f"baseline_snapshot_{now.year}-{now.month:02d}-{now.day:02d}.json"
        snapshot_file = self.baseline_dir / "archive" / snapshot_filename

        snapshot_data = {
            "timestamp": now.isoformat(),
            "snapshot_type": "monthly",
            "baseline_version": 1,
            "results": results,
        }

        with open(snapshot_file, "w") as f:
            json.dump(snapshot_data, f, indent=2)

        return str(snapshot_file)

    def get_last_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent snapshot from archive.

        Returns:
            Snapshot data or None if not found
        """
        archive_dir = self.baseline_dir / "archive"
        if not archive_dir.exists():
            return None

        # Find most recent snapshot
        snapshots = sorted(archive_dir.glob("baseline_snapshot_*.json"), reverse=True)
        if not snapshots:
            return None

        try:
            with open(snapshots[0], "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_snapshot_by_date(self, year: int, month: int, day: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific snapshot by date.

        Args:
            year: Year of snapshot
            month: Month of snapshot
            day: Day of snapshot

        Returns:
            Snapshot data or None if not found
        """
        snapshot_filename = f"baseline_snapshot_{year}-{month:02d}-{day:02d}.json"
        snapshot_file = self.baseline_dir / "archive" / snapshot_filename

        if not snapshot_file.exists():
            return None

        try:
            with open(snapshot_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all available snapshots.

        Returns:
            List of snapshot metadata
        """
        archive_dir = self.baseline_dir / "archive"
        if not archive_dir.exists():
            return []

        snapshots = []
        for snapshot_file in sorted(archive_dir.glob("baseline_snapshot_*.json"), reverse=True):
            try:
                with open(snapshot_file, "r") as f:
                    data = json.load(f)
                    snapshots.append({
                        "filename": snapshot_file.name,
                        "timestamp": data.get("timestamp"),
                        "path": str(snapshot_file),
                    })
            except (json.JSONDecodeError, IOError):
                continue

        return snapshots

    def cleanup_old_snapshots(self, keep_count: int = 12) -> List[str]:
        """
        Clean up old snapshots, keeping only the most recent ones.

        Args:
            keep_count: Number of snapshots to keep

        Returns:
            List of deleted snapshot paths
        """
        archive_dir = self.baseline_dir / "archive"
        if not archive_dir.exists():
            return []

        snapshots = sorted(archive_dir.glob("baseline_snapshot_*.json"), reverse=True)
        deleted = []

        for snapshot_file in snapshots[keep_count:]:
            try:
                snapshot_file.unlink()
                deleted.append(str(snapshot_file))
            except OSError:
                pass

        return deleted

    def get_baseline_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get baseline history for trend analysis.

        Args:
            limit: Maximum number of baselines to return

        Returns:
            List of baseline data with timestamps
        """
        archive_dir = self.baseline_dir / "archive"
        if not archive_dir.exists():
            return []

        history = []
        for snapshot_file in sorted(archive_dir.glob("baseline_snapshot_*.json"), reverse=True)[:limit]:
            try:
                with open(snapshot_file, "r") as f:
                    data = json.load(f)
                    history.append({
                        "timestamp": data.get("timestamp"),
                        "filename": snapshot_file.name,
                        "summary": data.get("results", {}).get("summary", {}),
                    })
            except (json.JSONDecodeError, IOError):
                continue

        return history
