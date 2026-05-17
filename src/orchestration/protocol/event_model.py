"""
Event model for task lifecycle events.

Event types (10+):
- delegate.created: DELEGATE written to queue
- delegate.assigned: Agent assigned to task
- execution.started: Agent begins work
- execution.progress: Periodic progress updates
- execution.completed: Work finished
- handback.created: HANDBACK written
- quality.evaluated: QE review complete
- feedback.recorded: Feedback loop processed
- optimization.recommended: Optimization engine suggests changes
- task.completed: Moved to done/
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Task lifecycle event types."""
    DELEGATE_CREATED = "delegate.created"
    DELEGATE_ASSIGNED = "delegate.assigned"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_PROGRESS = "execution.progress"
    EXECUTION_COMPLETED = "execution.completed"
    HANDBACK_CREATED = "handback.created"
    QUALITY_EVALUATED = "quality.evaluated"
    FEEDBACK_RECORDED = "feedback.recorded"
    OPTIMIZATION_RECOMMENDED = "optimization.recommended"
    TASK_COMPLETED = "task.completed"


@dataclass
class Event:
    """Task lifecycle event."""
    
    # Core fields
    event_id: str
    event_type: EventType
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Task reference
    task_id: str = ""
    
    # Actor (which agent/component)
    actor: str = ""
    actor_role: str = ""
    
    # Event-specific data
    data: Dict = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    priority: str = "normal"  # low, normal, high, critical
    related_events: List[str] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "actor": self.actor,
            "actor_role": self.actor_role,
            "data": self.data,
            "tags": self.tags,
            "priority": self.priority,
            "related_events": self.related_events,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            task_id=data.get("task_id", ""),
            actor=data.get("actor", ""),
            actor_role=data.get("actor_role", ""),
            data=data.get("data", {}),
            tags=data.get("tags", []),
            priority=data.get("priority", "normal"),
            related_events=data.get("related_events", []),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema."""
        errors = []
        
        if not self.event_id:
            errors.append("event_id is required")
        if not self.task_id:
            errors.append("task_id is required")
        if self.priority not in ["low", "normal", "high", "critical"]:
            errors.append(f"Invalid priority: {self.priority}")
        
        return errors
