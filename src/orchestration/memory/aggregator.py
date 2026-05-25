"""Session Memory Aggregator

Collects DELEGATEs, HANDBACKs, logs, and metrics into a unified session memory index.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import shutil

from .directory_setup import get_session_memory_dir, get_agentic_engineers_home

logger = logging.getLogger(__name__)


class SessionMemoryAggregator:
    """Aggregates and indexes all session memory events."""
    
    def __init__(self, session_id: str, queue_dir: Optional[Path] = None):
        """
        Initialize aggregator.
        
        Args:
            session_id: Session identifier
            queue_dir: Optional queue directory (defaults to ~/.copilot/queue/{session_id})
        """
        self.session_id = session_id
        self.memory_dir = get_session_memory_dir(session_id)
        
        # Default queue directory
        if queue_dir is None:
            home = Path.home()
            # Try copilot first, then claude
            copilot_queue = home / ".copilot" / "queue" / session_id
            claude_queue = home / ".claude" / "queue" / session_id
            
            if copilot_queue.exists():
                queue_dir = copilot_queue
            elif claude_queue.exists():
                queue_dir = claude_queue
            else:
                # Default to copilot
                queue_dir = copilot_queue
        
        self.queue_dir = Path(queue_dir)
        
        # Subdirectories in session memory
        self.delegates_dir = self.memory_dir / "delegates"
        self.handbacks_dir = self.memory_dir / "handbacks"
        self.logs_dir = self.memory_dir / "logs"
        self.thinking_dir = self.memory_dir / "thinking"
        self.metrics_dir = self.memory_dir / "metrics"
        
        # Global artifacts directories
        artifacts_root = Path.cwd() / "artifacts"
        self.artifacts_delegates_dir = artifacts_root / "delegates"
        self.artifacts_handbacks_dir = artifacts_root / "handbacks"
        self.artifacts_spans_dir = artifacts_root / "spans"
        
        self.index_path = self.memory_dir / "index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load existing index or create new one."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse index: {self.index_path}")
        
        # Create new index
        return {
            "session_id": self.session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "delegates": [],
            "handbacks": [],
            "logs": [],
            "thinking": [],
            "metrics": [],
            "summary": {},
        }
    
    def collect_delegates(self) -> List[Dict]:
        """
        Collect all DELEGATE files from queue and artifacts.
        
        Returns:
            List of delegate records
        """
        delegates = []
        
        # Collect from queue incoming directory
        queue_incoming = self.queue_dir / "incoming"
        if queue_incoming.exists():
            for yaml_file in queue_incoming.glob("*.yaml"):
                try:
                    delegate = self._read_yaml_file(yaml_file)
                    if delegate.get("handoff_type") == "DELEGATE":
                        record = {
                            "task_id": delegate.get("task_id"),
                            "timestamp": delegate.get("timestamp"),
                            "role": delegate.get("role"),
                            "model": delegate.get("model"),
                            "effort": delegate.get("effort"),
                            "scope": delegate.get("scope", ""),
                            "source": "queue-incoming",
                            "source_file": str(yaml_file.relative_to(self.queue_dir.parent)),
                        }
                        delegates.append(record)
                        
                        # Copy to memory storage
                        dest = self.delegates_dir / yaml_file.name
                        shutil.copy2(yaml_file, dest)
                        logger.debug(f"Copied DELEGATE: {yaml_file.name}")
                except Exception as e:
                    logger.error(f"Failed to process DELEGATE {yaml_file}: {e}")
        
        # Collect from processing directory
        queue_processing = self.queue_dir / "processing"
        if queue_processing.exists():
            for yaml_file in queue_processing.glob("*.yaml"):
                try:
                    delegate = self._read_yaml_file(yaml_file)
                    if delegate.get("handoff_type") == "DELEGATE":
                        task_id = delegate.get("task_id")
                        # Skip if already collected
                        if any(d["task_id"] == task_id for d in delegates):
                            continue
                        
                        record = {
                            "task_id": task_id,
                            "timestamp": delegate.get("timestamp"),
                            "role": delegate.get("role"),
                            "model": delegate.get("model"),
                            "effort": delegate.get("effort"),
                            "scope": delegate.get("scope", ""),
                            "source": "queue-processing",
                            "source_file": str(yaml_file.relative_to(self.queue_dir.parent)),
                        }
                        delegates.append(record)
                        
                        # Copy to memory storage
                        dest = self.delegates_dir / yaml_file.name
                        shutil.copy2(yaml_file, dest)
                except Exception as e:
                    logger.error(f"Failed to process DELEGATE {yaml_file}: {e}")
        
        # Collect from global artifacts/delegates
        if self.artifacts_delegates_dir.exists():
            for yaml_file in self.artifacts_delegates_dir.glob("*.yaml"):
                try:
                    # Skip .keep files
                    if yaml_file.name.startswith("."):
                        continue
                    
                    with open(yaml_file, "r") as f:
                        content = f.read()
                        # Handle YAML documents (may have multiple --- separators)
                        for doc in yaml.safe_load_all(content):
                            if doc and doc.get("handoff_type") == "DELEGATE":
                                task_id = doc.get("task_id")
                                # Skip if already collected
                                if any(d["task_id"] == task_id for d in delegates):
                                    continue
                                
                                record = {
                                    "task_id": task_id,
                                    "timestamp": doc.get("timestamp"),
                                    "role": doc.get("role"),
                                    "model": doc.get("model"),
                                    "effort": doc.get("effort"),
                                    "scope": doc.get("scope", ""),
                                    "source": "artifacts-delegates",
                                    "source_file": f"artifacts/delegates/{yaml_file.name}",
                                }
                                delegates.append(record)
                except Exception as e:
                    logger.error(f"Failed to process artifact DELEGATE {yaml_file}: {e}")
        
        logger.info(f"Collected {len(delegates)} DELEGATEs")
        return delegates
    
    def collect_handbacks(self) -> List[Dict]:
        """
        Collect all HANDBACK files from queue and artifacts.
        
        Returns:
            List of handback records
        """
        handbacks = []
        
        # Collect from queue processing directory
        queue_processing = self.queue_dir / "processing"
        if queue_processing.exists():
            for yaml_file in queue_processing.glob("*handback*.yaml"):
                try:
                    handback = self._read_yaml_file(yaml_file)
                    if handback.get("handoff_type") == "HANDBACK":
                        record = {
                            "task_id": handback.get("task_id"),
                            "timestamp": handback.get("timestamp"),
                            "status": handback.get("status"),
                            "quality_score": handback.get("quality_score"),
                            "tokens_used": handback.get("tokens", {}).get("used"),
                            "source": "queue-processing",
                            "source_file": str(yaml_file.relative_to(self.queue_dir.parent)),
                        }
                        handbacks.append(record)
                        
                        # Copy to memory storage
                        dest = self.handbacks_dir / yaml_file.name
                        shutil.copy2(yaml_file, dest)
                        logger.debug(f"Copied HANDBACK: {yaml_file.name}")
                except Exception as e:
                    logger.error(f"Failed to process HANDBACK {yaml_file}: {e}")
        
        # Collect from queue done directory
        queue_done = self.queue_dir / "done"
        if queue_done.exists():
            for yaml_file in queue_done.glob("*handback*.yaml"):
                try:
                    handback = self._read_yaml_file(yaml_file)
                    if handback.get("handoff_type") == "HANDBACK":
                        task_id = handback.get("task_id")
                        # Skip if already collected
                        if any(h["task_id"] == task_id for h in handbacks):
                            continue
                        
                        record = {
                            "task_id": task_id,
                            "timestamp": handback.get("timestamp"),
                            "status": handback.get("status"),
                            "quality_score": handback.get("quality_score"),
                            "tokens_used": handback.get("tokens", {}).get("used"),
                            "source": "queue-done",
                            "source_file": str(yaml_file.relative_to(self.queue_dir.parent)),
                        }
                        handbacks.append(record)
                        
                        # Copy to memory storage
                        dest = self.handbacks_dir / yaml_file.name
                        shutil.copy2(yaml_file, dest)
                except Exception as e:
                    logger.error(f"Failed to process HANDBACK {yaml_file}: {e}")
        
        # Collect from global artifacts/handbacks
        if self.artifacts_handbacks_dir.exists():
            for yaml_file in self.artifacts_handbacks_dir.glob("*.yaml"):
                try:
                    if yaml_file.name.startswith("."):
                        continue
                    
                    with open(yaml_file, "r") as f:
                        content = f.read()
                        for doc in yaml.safe_load_all(content):
                            if doc and doc.get("handoff_type") == "HANDBACK":
                                task_id = doc.get("task_id")
                                if any(h["task_id"] == task_id for h in handbacks):
                                    continue
                                
                                record = {
                                    "task_id": task_id,
                                    "timestamp": doc.get("timestamp"),
                                    "status": doc.get("status"),
                                    "quality_score": doc.get("quality_score"),
                                    "tokens_used": doc.get("tokens", {}).get("used"),
                                    "source": "artifacts-handbacks",
                                    "source_file": f"artifacts/handbacks/{yaml_file.name}",
                                }
                                handbacks.append(record)
                except Exception as e:
                    logger.error(f"Failed to process artifact HANDBACK {yaml_file}: {e}")
        
        logger.info(f"Collected {len(handbacks)} HANDBACKs")
        return handbacks
    
    def collect_logs(self) -> List[Dict]:
        """Collect all agent logs."""
        logs = []
        
        # Look for logs in common locations
        log_locations = [
            self.queue_dir / "logs",
            Path.cwd() / "logs",
            Path.home() / ".copilot" / "logs",
        ]
        
        for log_dir in log_locations:
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    try:
                        record = {
                            "filename": log_file.name,
                            "path": str(log_file),
                            "size": log_file.stat().st_size,
                            "modified": datetime.fromtimestamp(
                                log_file.stat().st_mtime
                            ).isoformat(),
                        }
                        logs.append(record)
                        
                        # Copy to memory storage
                        dest = self.logs_dir / log_file.name
                        shutil.copy2(log_file, dest)
                    except Exception as e:
                        logger.error(f"Failed to process log {log_file}: {e}")
        
        logger.info(f"Collected {len(logs)} log files")
        return logs
    
    def collect_thinking(self) -> List[Dict]:
        """Collect thinking/reasoning output."""
        thinking = []
        
        # Look for thinking files
        think_locations = [
            self.queue_dir / "thinking",
            Path.cwd() / "thinking",
        ]
        
        for think_dir in think_locations:
            if think_dir.exists():
                for think_file in think_dir.glob("*"):
                    if think_file.is_file():
                        try:
                            record = {
                                "filename": think_file.name,
                                "path": str(think_file),
                                "size": think_file.stat().st_size,
                            }
                            thinking.append(record)
                            
                            # Copy to memory storage
                            dest = self.thinking_dir / think_file.name
                            shutil.copy2(think_file, dest)
                        except Exception as e:
                            logger.error(f"Failed to process thinking {think_file}: {e}")
        
        logger.info(f"Collected {len(thinking)} thinking files")
        return thinking
    
    def collect_metrics(self) -> Dict:
        """Collect aggregated metrics."""
        metrics = {
            "total_delegates": 0,
            "total_handbacks": 0,
            "total_tokens": 0,
            "average_quality_score": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
        }
        
        # Calculate from handbacks
        handbacks = self.collect_handbacks()
        quality_scores = []
        
        for handback in handbacks:
            metrics["total_handbacks"] += 1
            
            if handback.get("quality_score"):
                quality_scores.append(handback["quality_score"])
            
            if handback.get("tokens_used"):
                metrics["total_tokens"] += handback["tokens_used"]
            
            if handback.get("status") == "complete":
                metrics["completed_tasks"] += 1
            elif handback.get("status") == "failed":
                metrics["failed_tasks"] += 1
        
        if quality_scores:
            metrics["average_quality_score"] = sum(quality_scores) / len(quality_scores)
        
        metrics["total_delegates"] = len(self.collect_delegates())
        
        logger.info(f"Aggregated metrics: {metrics}")
        return metrics
    
    def aggregate_all(self) -> Dict:
        """Aggregate all memory into unified index."""
        logger.info(f"Starting memory aggregation for session {self.session_id}")
        
        # Collect all components
        delegates = self.collect_delegates()
        handbacks = self.collect_handbacks()
        logs = self.collect_logs()
        thinking = self.collect_thinking()
        metrics = self.collect_metrics()
        
        # Update index
        self.index.update({
            "updated_at": datetime.utcnow().isoformat(),
            "delegates": delegates,
            "handbacks": handbacks,
            "logs": logs,
            "thinking": thinking,
            "metrics": metrics,
            "summary": {
                "total_delegates": len(delegates),
                "total_handbacks": len(handbacks),
                "total_logs": len(logs),
                "total_thinking_files": len(thinking),
                "total_tokens": metrics.get("total_tokens", 0),
                "average_quality_score": metrics.get("average_quality_score", 0),
                "completed_tasks": metrics.get("completed_tasks", 0),
                "failed_tasks": metrics.get("failed_tasks", 0),
            }
        })
        
        logger.info(f"Memory aggregation complete: {self.index['summary']}")
        return self.index
    
    def export_index(self, pretty: bool = True) -> Path:
        """
        Export aggregated index to JSON file.
        
        Args:
            pretty: If True, pretty-print JSON
            
        Returns:
            Path to exported index file
        """
        try:
            with open(self.index_path, "w") as f:
                if pretty:
                    json.dump(self.index, f, indent=2)
                else:
                    json.dump(self.index, f)
            
            logger.info(f"Exported memory index: {self.index_path}")
            return self.index_path
        except IOError as e:
            logger.error(f"Failed to export index: {e}")
            raise
    
    def _read_yaml_file(self, path: Path) -> Dict:
        """Safely read YAML file."""
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    
    def query_by_task_id(self, task_id: str) -> Dict:
        """Query memory by task ID."""
        result = {
            "task_id": task_id,
            "delegates": [],
            "handbacks": [],
        }
        
        for delegate in self.index.get("delegates", []):
            if delegate.get("task_id") == task_id:
                result["delegates"].append(delegate)
        
        for handback in self.index.get("handbacks", []):
            if handback.get("task_id") == task_id:
                result["handbacks"].append(handback)
        
        return result
    
    def query_by_role(self, role: str) -> Dict:
        """Query memory by agent role."""
        result = {
            "role": role,
            "delegates": [],
            "count": 0,
        }
        
        for delegate in self.index.get("delegates", []):
            if delegate.get("role") == role:
                result["delegates"].append(delegate)
        
        result["count"] = len(result["delegates"])
        return result
