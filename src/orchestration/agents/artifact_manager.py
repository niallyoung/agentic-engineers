"""
Artifact Manager - Read/Write DELEGATE/HANDBACK/FEEDBACK YAML blocks

Manages serialization of DELEGATE, HANDBACK, and FEEDBACK blocks to the
canonical artifacts directory: ~/.agentic-engineers/{harness}/{session-id}/
Supports date-keyed organization for historical archival.
"""

import os
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class ArtifactManager:
    """Manage DELEGATE/HANDBACK/FEEDBACK artifact storage."""

    def __init__(self, base_dir: str = "artifacts"):
        self.base_dir = base_dir
        self._ensure_base_dir()

    def _ensure_base_dir(self):
        """Ensure base artifacts directory exists."""
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def _get_date_dir(self) -> str:
        """Get date-keyed subdirectory (YYYY-MM-DD format)."""
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = os.path.join(self.base_dir, today)
        Path(date_dir).mkdir(parents=True, exist_ok=True)
        return date_dir

    def write_delegate(self, task_id: str, delegate_block: Dict) -> str:
        """Write DELEGATE block to artifacts/YYYY-MM-DD/DELEGATE-{task_id}.yaml"""
        date_dir = self._get_date_dir()
        filename = f"DELEGATE-{task_id}.yaml"
        filepath = os.path.join(date_dir, filename)

        with open(filepath, 'w') as f:
            yaml.dump(delegate_block, f, default_flow_style=False, sort_keys=False)

        return filepath

    def write_handback(self, task_id: str, handback_block: Dict) -> str:
        """Write HANDBACK block to artifacts/YYYY-MM-DD/HANDBACK-{task_id}.yaml"""
        date_dir = self._get_date_dir()
        filename = f"HANDBACK-{task_id}.yaml"
        filepath = os.path.join(date_dir, filename)

        with open(filepath, 'w') as f:
            yaml.dump(handback_block, f, default_flow_style=False, sort_keys=False)

        return filepath

    def write_feedback(self, task_id: str, feedback_block: Dict) -> str:
        """Write FEEDBACK block to artifacts/YYYY-MM-DD/FEEDBACK-{task_id}.yaml"""
        date_dir = self._get_date_dir()
        filename = f"FEEDBACK-{task_id}.yaml"
        filepath = os.path.join(date_dir, filename)

        with open(filepath, 'w') as f:
            yaml.dump(feedback_block, f, default_flow_style=False, sort_keys=False)

        return filepath

    def read_delegate(self, task_id: str, date: Optional[str] = None) -> Dict:
        """
        Read DELEGATE block.

        Args:
            task_id: Task identifier
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Parsed DELEGATE block dict
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        filepath = os.path.join(self.base_dir, date, f"DELEGATE-{task_id}.yaml")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"DELEGATE not found: {filepath}")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def read_handback(self, task_id: str, date: Optional[str] = None) -> Dict:
        """
        Read HANDBACK block.

        Args:
            task_id: Task identifier
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Parsed HANDBACK block dict
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        filepath = os.path.join(self.base_dir, date, f"HANDBACK-{task_id}.yaml")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"HANDBACK not found: {filepath}")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def read_feedback(self, task_id: str, date: Optional[str] = None) -> Dict:
        """
        Read FEEDBACK block.

        Args:
            task_id: Task identifier
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Parsed FEEDBACK block dict
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        filepath = os.path.join(self.base_dir, date, f"FEEDBACK-{task_id}.yaml")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"FEEDBACK not found: {filepath}")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def list_artifacts(self, date: Optional[str] = None) -> Dict:
        """
        List all artifacts for a given date.

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Dict with keys 'delegates', 'handbacks', 'feedbacks' (lists of filenames)
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        date_dir = os.path.join(self.base_dir, date)
        if not os.path.exists(date_dir):
            return {"delegates": [], "handbacks": [], "feedbacks": []}

        files = os.listdir(date_dir)
        return {
            "delegates": sorted([f for f in files if f.startswith("DELEGATE-")]),
            "handbacks": sorted([f for f in files if f.startswith("HANDBACK-")]),
            "feedbacks": sorted([f for f in files if f.startswith("FEEDBACK-")])
        }

    def export_json(self, task_id: str, date: Optional[str] = None) -> str:
        """
        Export all artifacts for a task as JSON.

        Returns:
            JSON string with delegate, handback, feedback (all available)
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        result = {
            "task_id": task_id,
            "date": date,
            "delegate": None,
            "handback": None,
            "feedback": None
        }

        try:
            result["delegate"] = self.read_delegate(task_id, date)
        except FileNotFoundError:
            pass

        try:
            result["handback"] = self.read_handback(task_id, date)
        except FileNotFoundError:
            pass

        try:
            result["feedback"] = self.read_feedback(task_id, date)
        except FileNotFoundError:
            pass

        return json.dumps(result, indent=2, default=str)
