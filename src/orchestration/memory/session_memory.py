"""
Session Memory Integration for Orchestrator

Hooks into orchestrator to collect and aggregate session memory at session end.
Provides utilities for writing final memory indices.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from .artifact_memory import ArtifactMemoryStore, MemoryIndexBuilder


class SessionMemoryManager:
    """Manage session memory lifecycle."""

    def __init__(self, session_id: str, base_dir: Optional[str] = None):
        """Initialize session memory manager."""
        self.session_id = session_id
        self.store = ArtifactMemoryStore(session_id, base_dir)
        self.base_dir = self.store.base_dir

    def collect_session_memory(self) -> Dict[str, Any]:
        """
        Collect all session memory into a comprehensive index.
        
        Returns:
            Dict with complete session memory summary
        """
        return {
            "session_id": self.session_id,
            "collected_at": datetime.now().isoformat(),
            "memory": self.store.aggregate_session(),
            "delegates": self.store.aggregate_delegates(),
            "handbacks": self.store.aggregate_handbacks(),
        }

    def finalize_session_memory(self) -> Path:
        """
        Finalize session memory by writing comprehensive index.
        
        Returns:
            Path to the written index file
        """
        return self.store.write_index()

    def write_session_summary(self, summary_data: Dict[str, Any]) -> Path:
        """
        Write a human-readable session summary.
        
        Args:
            summary_data: Session summary data
        
        Returns:
            Path to the written summary file
        """
        summary_file = self.store.memory_dir / "summary.md"
        
        lines = [
            f"# Session Memory Summary\n",
            f"**Session ID**: {self.session_id}\n",
            f"**Generated**: {datetime.now().isoformat()}\n\n",
        ]
        
        if summary_data.get("delegates"):
            count = summary_data["delegates"].get("count", 0)
            lines.append(f"## Delegates\n")
            lines.append(f"- Total: {count}\n\n")
        
        if summary_data.get("handbacks"):
            count = summary_data["handbacks"].get("count", 0)
            lines.append(f"## Handbacks\n")
            lines.append(f"- Total: {count}\n\n")
        
        if summary_data.get("memory"):
            mem = summary_data["memory"]
            lines.append(f"## Memory Statistics\n")
            lines.append(f"- Files: {mem.get('file_count', 0)}\n")
            lines.append(f"- Size: {mem.get('total_size_bytes', 0):,} bytes\n\n")
        
        with open(summary_file, "w") as f:
            f.writelines(lines)
        
        return summary_file


class GlobalMemoryManager:
    """Manage global memory across all sessions."""

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize global memory manager."""
        if base_dir is None:
            base_dir = os.path.expanduser("~/.agentic-engineers")
        
        self.base_dir = Path(base_dir)
        self.builder = MemoryIndexBuilder(str(self.base_dir))

    def build_global_index(self) -> Path:
        """
        Build and write global memory index.
        
        Returns:
            Path to the written global index file
        """
        global_index = self.builder.build_global_index()
        
        # Write to root of artifact directory
        index_file = self.base_dir / "MEMORY_INDEX.json"
        with open(index_file, "w") as f:
            json.dump(global_index, f, indent=2, default=str)
        
        return index_file

    def cleanup_old_sessions(self, days: int = 30) -> Dict[str, Any]:
        """
        Archive old session memory (older than N days).
        
        Args:
            days: Age threshold in days
        
        Returns:
            Dict with cleanup statistics
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        archived = []
        
        if not self.base_dir.exists():
            return {"archived_count": 0, "archived_sessions": []}
        
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            memory_dir = session_dir / "memory"
            if not memory_dir.exists():
                continue
            
            # Check modification time
            mtime = datetime.fromtimestamp(memory_dir.stat().st_mtime)
            if mtime < cutoff_time:
                # Archive this session
                archive_dir = self.base_dir / "archive" / session_dir.name
                archive_dir.mkdir(parents=True, exist_ok=True)
                
                import shutil
                try:
                    shutil.move(str(memory_dir), str(archive_dir / "memory"))
                    archived.append(session_dir.name)
                except Exception:
                    pass
        
        return {
            "archived_count": len(archived),
            "archived_sessions": archived,
        }
