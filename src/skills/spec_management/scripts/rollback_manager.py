"""
rollback_manager.py — Version tracking and rollback capability for SPEC.md.

Tracks:
- SPEC.md versions with SHA-256 hashes
- Complete change history
- Enables rollback to previous versions

Author: Principal Engineer
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import json


@dataclass
class SpecVersion:
    """Version record for SPEC.md"""
    version_id: str
    change_id: str
    timestamp: str
    previous_hash: str
    new_hash: str
    applied_changes: Dict[str, str]


class RollbackManager:
    """Tracks SPEC.md versions and enables rollback."""
    
    def __init__(self, version_dir: str = "artifacts/spec-versions"):
        self.version_dir = Path(version_dir)
        self.version_dir.mkdir(parents=True, exist_ok=True)
        self._history: List[SpecVersion] = []
    
    def create_version(self, change_id: str, previous_hash: str, new_hash: str,
                      changes: Dict[str, str]) -> SpecVersion:
        """Create a version record for a change.
        
        Args:
            change_id: ID of change being applied
            previous_hash: SHA-256 of SPEC.md before change
            new_hash: SHA-256 of SPEC.md after change
            changes: Dict of section -> new_text
            
        Returns:
            SpecVersion record
        """
        version_num = len(self._history) + 1
        version_id = f"SPEC-v5.10.{version_num}"
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        version = SpecVersion(
            version_id=version_id,
            change_id=change_id,
            timestamp=timestamp,
            previous_hash=previous_hash,
            new_hash=new_hash,
            applied_changes=changes
        )
        
        self._history.append(version)
        
        # Write to disk
        self._write_version(version)
        
        return version
    
    def get_history(self) -> List[SpecVersion]:
        """Get complete change history.
        
        Returns:
            List of SpecVersion in chronological order (oldest first)
        """
        return list(self._history)
    
    def rollback(self, steps: int = 1) -> Dict:
        """Rollback one or more changes.
        
        Args:
            steps: Number of changes to revert (default: 1)
            
        Returns:
            Dict with success status and details
        """
        if len(self._history) < steps:
            return {
                "success": False,
                "error": f"Cannot rollback {steps} changes; only {len(self._history)} in history"
            }
        
        # Get the version to rollback to
        target_index = len(self._history) - steps - 1
        if target_index < 0:
            return {
                "success": False,
                "error": f"Cannot rollback beyond first change"
            }
        
        target_version = self._history[target_index]
        last_reverted = self._history[len(self._history) - 1]
        
        return {
            "success": True,
            "previous_version": target_version.version_id,
            "reverted_versions": [v.version_id for v in self._history[target_index + 1:]],
            "last_reverted_change_id": last_reverted.change_id,
            "details": f"Rolled back {steps} change(s) to {target_version.version_id}"
        }
    
    def rollback_to_version(self, version_id: str) -> Dict:
        """Rollback to a specific version.
        
        Args:
            version_id: Version to rollback to (e.g., "SPEC-v5.10.1")
            
        Returns:
            Dict with success status and details
        """
        # Find the version
        target_version = None
        target_index = -1
        
        for i, version in enumerate(self._history):
            if version.version_id == version_id:
                target_version = version
                target_index = i
                break
        
        if target_version is None:
            return {
                "success": False,
                "error": f"Version {version_id} not found in history"
            }
        
        # Get the last reverted change
        last_reverted = self._history[-1] if self._history else None
        
        return {
            "success": True,
            "target_version": target_version.version_id,
            "reverted_versions": [v.version_id for v in self._history[target_index + 1:]],
            "last_reverted_change_id": last_reverted.change_id if last_reverted else "unknown",
            "details": f"Rolled back to {target_version.version_id}"
        }
    
    def _write_version(self, version: SpecVersion) -> None:
        """Write version metadata to disk.
        
        Args:
            version: SpecVersion to write
        """
        version_file = self.version_dir / f"{version.version_id}.json"
        
        version_dict = {
            "version_id": version.version_id,
            "change_id": version.change_id,
            "timestamp": version.timestamp,
            "previous_hash": version.previous_hash,
            "new_hash": version.new_hash,
            "applied_changes": version.applied_changes
        }
        
        version_file.write_text(json.dumps(version_dict, indent=2))
    
    def _read_version(self, version_id: str) -> Optional[SpecVersion]:
        """Read version metadata from disk.
        
        Args:
            version_id: Version ID to read
            
        Returns:
            SpecVersion or None if not found
        """
        version_file = self.version_dir / f"{version_id}.json"
        
        if not version_file.exists():
            return None
        
        data = json.loads(version_file.read_text())
        return SpecVersion(
            version_id=data["version_id"],
            change_id=data["change_id"],
            timestamp=data["timestamp"],
            previous_hash=data["previous_hash"],
            new_hash=data["new_hash"],
            applied_changes=data["applied_changes"]
        )
