"""
Artifact Memory Store - Persistent session memory in ~/.agentic-engineers/

Manages memory/state for agent tasks, metrics, and analysis by storing data
in the local artifact directory with session isolation.

Usage:
    store = ArtifactMemoryStore(session_id="abc-123")
    store.write("metrics", {"tokens": 1000, "cost": 5.0})
    data = store.read("metrics")
    
    # Aggregate all session memory
    full_memory = store.aggregate_session()
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import hashlib


class ArtifactMemoryStore:
    """
    Persistent session memory stored in ~/.agentic-engineers/{session_id}/memory/
    
    Provides read/write/aggregate operations for session state, metrics, logs, and analysis.
    """

    def __init__(self, session_id: str, base_dir: Optional[str] = None):
        """
        Initialize memory store for a session.
        
        Args:
            session_id: Unique identifier for the session (e.g., "abc-123")
            base_dir: Base directory for artifact storage (default: ~/.agentic-engineers)
        """
        if base_dir is None:
            base_dir = os.path.expanduser("~/.agentic-engineers")
        
        self.session_id = session_id
        self.base_dir = Path(base_dir)
        self.memory_dir = self.base_dir / session_id / "memory"
        
        # Ensure memory directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def write(self, key: str, data: Any, subdir: str = "") -> Path:
        """
        Write data to memory store.
        
        Args:
            key: Memory key (e.g., "metrics", "delegates", "logs")
            data: Data to store (will be serialized as JSON)
            subdir: Optional subdirectory (e.g., "metrics/daily")
        
        Returns:
            Path to the written file
        """
        if subdir:
            target_dir = self.memory_dir / subdir
        else:
            target_dir = self.memory_dir
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Write with timestamp suffix if key already exists (for versioning)
        filepath = target_dir / f"{key}.json"
        if filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = target_dir / f"{key}_{timestamp}.json"
        
        with open(filepath, "w") as f:
            json.dump(
                {
                    "key": key,
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                },
                f,
                indent=2,
                default=str,
            )
        
        return filepath
    
    def read(self, key: str, subdir: str = "") -> Optional[Dict[str, Any]]:
        """
        Read data from memory store.
        
        Args:
            key: Memory key to retrieve
            subdir: Optional subdirectory
        
        Returns:
            Memory data dict with keys: key, session_id, timestamp, data
            Returns None if key not found
        """
        if subdir:
            target_dir = self.memory_dir / subdir
        else:
            target_dir = self.memory_dir
        
        filepath = target_dir / f"{key}.json"
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def append_metric(
        self, metric_name: str, metric_value: Any, subdir: str = "metrics"
    ) -> Path:
        """
        Append a single metric data point to a JSONL file (for time-series metrics).
        
        Args:
            metric_name: Name of the metric (e.g., "token_usage", "quality_score")
            metric_value: Value to append
            subdir: Subdirectory for metrics (default: "metrics")
        
        Returns:
            Path to the metrics file
        """
        target_dir = self.memory_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = target_dir / f"{metric_name}.jsonl"
        
        metric_entry = {
            "timestamp": datetime.now().isoformat(),
            "value": metric_value,
        }
        
        with open(filepath, "a") as f:
            f.write(json.dumps(metric_entry, default=str) + "\n")
        
        return filepath
    
    def list_all(self, subdir: str = "") -> Dict[str, List[str]]:
        """
        List all memory files organized by type.
        
        Args:
            subdir: Optional subdirectory to list (default: entire memory dir)
        
        Returns:
            Dict mapping subdirectories to list of files
        """
        if subdir:
            search_dir = self.memory_dir / subdir
        else:
            search_dir = self.memory_dir
        
        if not search_dir.exists():
            return {}
        
        result = {}
        for item in search_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(search_dir)
                subdir_name = str(rel_path.parent) if rel_path.parent != Path(".") else "root"
                if subdir_name not in result:
                    result[subdir_name] = []
                result[subdir_name].append(str(rel_path))
        
        return result
    
    def aggregate_session(self) -> Dict[str, Any]:
        """
        Aggregate all session memory into a single dictionary.
        
        Returns:
            Dict with keys: session_id, timestamp, memory_summary (count by type)
        """
        memory_index = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "memory_by_type": {},
            "file_count": 0,
            "total_size_bytes": 0,
        }
        
        # Scan all memory files
        for memory_file in self.memory_dir.rglob("*.json"):
            rel_path = memory_file.relative_to(self.memory_dir)
            file_type = rel_path.parent.name or "root"
            
            if file_type not in memory_index["memory_by_type"]:
                memory_index["memory_by_type"][file_type] = []
            
            memory_index["memory_by_type"][file_type].append({
                "file": str(rel_path),
                "size_bytes": memory_file.stat().st_size,
                "modified": datetime.fromtimestamp(memory_file.stat().st_mtime).isoformat(),
            })
            
            memory_index["file_count"] += 1
            memory_index["total_size_bytes"] += memory_file.stat().st_size
        
        # Scan all jsonl files
        for jsonl_file in self.memory_dir.rglob("*.jsonl"):
            rel_path = jsonl_file.relative_to(self.memory_dir)
            file_type = rel_path.parent.name or "root"
            
            # Count lines in JSONL
            try:
                with open(jsonl_file, "r") as f:
                    line_count = sum(1 for _ in f if _.strip())
            except IOError:
                line_count = 0
            
            if file_type not in memory_index["memory_by_type"]:
                memory_index["memory_by_type"][file_type] = []
            
            memory_index["memory_by_type"][file_type].append({
                "file": str(rel_path),
                "lines": line_count,
                "size_bytes": jsonl_file.stat().st_size,
                "modified": datetime.fromtimestamp(jsonl_file.stat().st_mtime).isoformat(),
            })
            
            memory_index["file_count"] += 1
            memory_index["total_size_bytes"] += jsonl_file.stat().st_size
        
        return memory_index
    
    def aggregate_delegates(self) -> Dict[str, Any]:
        """
        Aggregate all DELEGATE files from this session.
        
        Returns:
            Dict with delegate statistics and summary
        """
        delegates_dir = self.base_dir / self.session_id / "delegates"
        if not delegates_dir.exists():
            return {"count": 0, "delegates": []}
        
        delegates = []
        for yaml_file in delegates_dir.glob("*.yaml"):
            try:
                # Simple YAML parsing (looking for handoff_type and task_id)
                with open(yaml_file, "r") as f:
                    content = f.read()
                    # Extract handoff_type and task_id
                    lines = content.split("\n")
                    task_id = None
                    handoff_type = None
                    for line in lines:
                        if line.startswith("task_id:"):
                            task_id = line.split(":", 1)[1].strip()
                        elif line.startswith("handoff_type:"):
                            handoff_type = line.split(":", 1)[1].strip()
                    
                    if task_id and handoff_type:
                        delegates.append({
                            "file": str(yaml_file.relative_to(self.base_dir)),
                            "task_id": task_id,
                            "handoff_type": handoff_type,
                        })
            except IOError:
                continue
        
        return {
            "count": len(delegates),
            "delegates": delegates,
        }
    
    def aggregate_handbacks(self) -> Dict[str, Any]:
        """
        Aggregate all HANDBACK files from this session.
        
        Returns:
            Dict with handback statistics and summary
        """
        handbacks_dir = self.base_dir / self.session_id / "handbacks"
        if not handbacks_dir.exists():
            return {"count": 0, "handbacks": []}
        
        handbacks = []
        for yaml_file in handbacks_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    content = f.read()
                    lines = content.split("\n")
                    task_id = None
                    status = None
                    for line in lines:
                        if line.startswith("task_id:"):
                            task_id = line.split(":", 1)[1].strip()
                        elif line.startswith("status:"):
                            status = line.split(":", 1)[1].strip()
                    
                    if task_id and status:
                        handbacks.append({
                            "file": str(yaml_file.relative_to(self.base_dir)),
                            "task_id": task_id,
                            "status": status,
                        })
            except IOError:
                continue
        
        return {
            "count": len(handbacks),
            "handbacks": handbacks,
        }
    
    def write_index(self) -> Path:
        """
        Write a complete memory index file (index.json) for the session.
        
        Returns:
            Path to the written index file
        """
        index = {
            "session_id": self.session_id,
            "generated_at": datetime.now().isoformat(),
            "memory_summary": self.aggregate_session(),
            "delegates": self.aggregate_delegates(),
            "handbacks": self.aggregate_handbacks(),
        }
        
        filepath = self.memory_dir / "index.json"
        with open(filepath, "w") as f:
            json.dump(index, f, indent=2, default=str)
        
        return filepath


class MemoryIndexBuilder:
    """Build comprehensive memory indices across multiple sessions."""

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize builder."""
        if base_dir is None:
            base_dir = os.path.expanduser("~/.agentic-engineers")
        
        self.base_dir = Path(base_dir)
    
    def build_global_index(self) -> Dict[str, Any]:
        """
        Build index of all sessions with memory.
        
        Returns:
            Dict with global memory statistics
        """
        global_index = {
            "generated_at": datetime.now().isoformat(),
            "sessions": [],
            "total_sessions": 0,
            "total_memory_bytes": 0,
        }
        
        # Scan all session directories
        if self.base_dir.exists():
            for session_dir in self.base_dir.iterdir():
                if session_dir.is_dir() and (session_dir / "memory").exists():
                    session_id = session_dir.name
                    store = ArtifactMemoryStore(session_id, str(self.base_dir))
                    summary = store.aggregate_session()
                    
                    global_index["sessions"].append({
                        "session_id": session_id,
                        "memory_size_bytes": summary.get("total_size_bytes", 0),
                        "file_count": summary.get("file_count", 0),
                    })
                    
                    global_index["total_memory_bytes"] += summary.get("total_size_bytes", 0)
        
        global_index["total_sessions"] = len(global_index["sessions"])
        
        return global_index
