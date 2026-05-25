"""Session Memory Manager

Manages the lifecycle of session memory: initialization, collection, and aggregation.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from .directory_setup import setup_session_memory, get_session_memory_dir, initialize_memory_index
from .aggregator import SessionMemoryAggregator

logger = logging.getLogger(__name__)


class SessionMemoryManager:
    """Manages session memory lifecycle."""
    
    def __init__(self, session_id: str, queue_dir: Optional[Path] = None):
        """
        Initialize session memory manager.
        
        Args:
            session_id: Unique session identifier
            queue_dir: Optional path to session queue directory
        """
        self.session_id = session_id
        self.queue_dir = queue_dir
        self.memory_dir = None
        self.aggregator = None
    
    def initialize(self, metadata: Optional[Dict] = None) -> Dict:
        """
        Initialize session memory.
        
        Args:
            metadata: Optional metadata to include
            
        Returns:
            Dict with initialization result
        """
        logger.info(f"Initializing session memory for {self.session_id}")
        
        try:
            # Create directory structure
            subdirs = setup_session_memory(self.session_id)
            self.memory_dir = get_session_memory_dir(self.session_id)
            
            # Initialize index
            index_path = initialize_memory_index(self.session_id, metadata)
            
            # Create aggregator
            self.aggregator = SessionMemoryAggregator(self.session_id, self.queue_dir)
            
            return {
                "success": True,
                "session_id": self.session_id,
                "memory_dir": str(self.memory_dir),
                "index_path": str(index_path),
                "subdirectories": {name: str(path) for name, path in subdirs.items()},
            }
        except Exception as e:
            logger.error(f"Failed to initialize session memory: {e}")
            return {
                "success": False,
                "session_id": self.session_id,
                "error": str(e),
            }
    
    def collect_memory_event(self, event_type: str, event_data: Dict) -> bool:
        """
        Record a memory event (typically called from orchestrator).
        
        Args:
            event_type: Type of event (delegate, handback, log, metric)
            event_data: Event data
            
        Returns:
            True if successful
        """
        if not self.aggregator:
            logger.warning("Memory manager not initialized")
            return False
        
        try:
            # Events are collected during aggregation
            # This is a placeholder for future real-time collection
            logger.debug(f"Memory event recorded: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to record memory event: {e}")
            return False
    
    def aggregate_memory(self) -> Dict:
        """
        Aggregate all session memory.
        
        Returns:
            Aggregated memory index
        """
        if not self.aggregator:
            logger.warning("Memory manager not initialized")
            return {}
        
        try:
            index = self.aggregator.aggregate_all()
            self.aggregator.export_index()
            logger.info(f"Memory aggregation complete for {self.session_id}")
            return index
        except Exception as e:
            logger.error(f"Failed to aggregate memory: {e}")
            return {}
    
    def generate_summary(self) -> str:
        """
        Generate human-readable memory summary.
        
        Returns:
            Markdown-formatted summary
        """
        if not self.aggregator:
            logger.warning("Memory manager not initialized")
            return ""
        
        index = self.aggregator.index
        summary = index.get("summary", {})
        
        markdown = f"""# Session Memory Summary

**Session ID:** {self.session_id}  
**Created:** {index.get('created_at')}  
**Updated:** {index.get('updated_at')}

## Statistics

- **Total DELEGATEs:** {summary.get('total_delegates', 0)}
- **Total HANDBACKs:** {summary.get('total_handbacks', 0)}
- **Completed Tasks:** {summary.get('completed_tasks', 0)}
- **Failed Tasks:** {summary.get('failed_tasks', 0)}
- **Total Tokens Used:** {summary.get('total_tokens', 0):,}
- **Average Quality Score:** {summary.get('average_quality_score', 0):.1f}/100

## Memory Components

- **Log Files:** {summary.get('total_logs', 0)}
- **Thinking Files:** {summary.get('total_thinking_files', 0)}

## Tasks by Role

"""
        
        # Group by role
        role_counts = {}
        for delegate in index.get("delegates", []):
            role = delegate.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
        
        for role, count in sorted(role_counts.items()):
            markdown += f"- **{role}:** {count} tasks\n"
        
        return markdown
    
    def export_summary(self) -> Path:
        """Export memory summary to file."""
        if not self.memory_dir:
            logger.warning("Memory manager not initialized")
            return None
        
        summary_path = self.memory_dir / "summary.md"
        
        try:
            with open(summary_path, "w") as f:
                f.write(self.generate_summary())
            logger.info(f"Exported summary: {summary_path}")
            return summary_path
        except IOError as e:
            logger.error(f"Failed to export summary: {e}")
            return None
    
    def get_delegates(self, role: Optional[str] = None) -> list:
        """Get all DELEGATEs, optionally filtered by role."""
        if not self.aggregator:
            return []
        
        delegates = self.aggregator.index.get("delegates", [])
        
        if role:
            delegates = [d for d in delegates if d.get("role") == role]
        
        return delegates
    
    def get_handbacks(self, status: Optional[str] = None) -> list:
        """Get all HANDBACKs, optionally filtered by status."""
        if not self.aggregator:
            return []
        
        handbacks = self.aggregator.index.get("handbacks", [])
        
        if status:
            handbacks = [h for h in handbacks if h.get("status") == status]
        
        return handbacks
    
    def get_metrics(self) -> Dict:
        """Get aggregated metrics."""
        if not self.aggregator:
            return {}
        
        return self.aggregator.index.get("metrics", {})
    
    def query_by_task_id(self, task_id: str) -> Dict:
        """Query memory by task ID."""
        if not self.aggregator:
            return {}
        
        return self.aggregator.query_by_task_id(task_id)
    
    def query_by_role(self, role: str) -> Dict:
        """Query memory by agent role."""
        if not self.aggregator:
            return {}
        
        return self.aggregator.query_by_role(role)
