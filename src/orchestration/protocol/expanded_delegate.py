"""
Expanded DELEGATE schema with 20+ fields for cross-lifecycle reuse.

Core fields (5):
- task_id: Unique task identifier (YYYY-MM-DD-kebab-case)
- role: Agent role (engineer, senior-engineer, lead-engineer, principal-engineer, security-engineer, quality-engineer)
- model: Model to use (claude-haiku-4.5, claude-sonnet-4.6, claude-opus-4.6, claude-opus-4.7)
- effort: Effort level (low, medium, high, extra-high)
- scope: Task description (≥15 words)

Quality fields (4):
- quality_baseline: Expected quality score (0-100)
- acceptance_criteria: List of acceptance criteria
- quality_thresholds: Dict of metric thresholds (coverage, regressions, etc.)
- quality_required_by: Timestamp when quality evaluation is required

Metadata fields (4):
- tags: List of tags for categorization
- priority: Priority level (low, medium, high, critical)
- dependencies: List of task IDs this task depends on
- related_tasks: List of related task IDs

Execution fields (4):
- plan: Numbered list of concrete steps
- estimated_tokens: Estimated token budget
- estimated_time_minutes: Estimated execution time
- constraints: List of constraints (e.g., "no external API calls")

Feedback fields (2):
- feedback_required: Boolean, whether feedback is required
- feedback_topics: List of feedback topics (e.g., "model_suitability", "cost_efficiency")

Optimization fields (2):
- optimization_targets: List of optimization targets (e.g., "cost", "speed", "quality")
- cost_target: Target cost in dollars

Artifact linking fields (2):
- parent_task_id: Parent task ID (for sub-tasks)
- related_artifacts: List of related artifact paths
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ExpandedDelegate:
    """Expanded DELEGATE schema with 20+ fields."""
    
    # Core fields (5)
    task_id: str
    role: str  # engineer, senior-engineer, lead-engineer, principal-engineer, security-engineer, quality-engineer
    model: str  # claude-haiku-4.5, claude-sonnet-4.6, claude-opus-4.6, claude-opus-4.7
    effort: str  # low, medium, high, extra-high
    scope: str  # ≥15 words
    
    # Quality fields (4)
    quality_baseline: int = 90  # 0-100
    acceptance_criteria: List[str] = field(default_factory=list)
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "coverage": 0.90,
        "regressions": 0,
        "test_pass_rate": 1.0,
    })
    quality_required_by: Optional[str] = None  # ISO 8601 timestamp
    
    # Metadata fields (4)
    tags: List[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high, critical
    dependencies: List[str] = field(default_factory=list)
    related_tasks: List[str] = field(default_factory=list)
    
    # Execution fields (4)
    plan: List[str] = field(default_factory=list)
    estimated_tokens: int = 2000
    estimated_time_minutes: int = 60
    constraints: List[str] = field(default_factory=list)
    
    # Feedback fields (2)
    feedback_required: bool = False
    feedback_topics: List[str] = field(default_factory=list)
    
    # Optimization fields (2)
    optimization_targets: List[str] = field(default_factory=list)
    cost_target: Optional[float] = None
    
    # Artifact linking fields (2)
    parent_task_id: Optional[str] = None
    related_artifacts: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            # Core
            "task_id": self.task_id,
            "role": self.role,
            "model": self.model,
            "effort": self.effort,
            "scope": self.scope,
            # Quality
            "quality_baseline": self.quality_baseline,
            "acceptance_criteria": self.acceptance_criteria,
            "quality_thresholds": self.quality_thresholds,
            "quality_required_by": self.quality_required_by,
            # Metadata
            "tags": self.tags,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "related_tasks": self.related_tasks,
            # Execution
            "plan": self.plan,
            "estimated_tokens": self.estimated_tokens,
            "estimated_time_minutes": self.estimated_time_minutes,
            "constraints": self.constraints,
            # Feedback
            "feedback_required": self.feedback_required,
            "feedback_topics": self.feedback_topics,
            # Optimization
            "optimization_targets": self.optimization_targets,
            "cost_target": self.cost_target,
            # Artifact linking
            "parent_task_id": self.parent_task_id,
            "related_artifacts": self.related_artifacts,
            # Metadata
            "created_at": self.created_at,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ExpandedDelegate":
        """Create from dictionary (YAML deserialization)."""
        return cls(
            task_id=data["task_id"],
            role=data["role"],
            model=data["model"],
            effort=data["effort"],
            scope=data["scope"],
            quality_baseline=data.get("quality_baseline", 90),
            acceptance_criteria=data.get("acceptance_criteria", []),
            quality_thresholds=data.get("quality_thresholds", {}),
            quality_required_by=data.get("quality_required_by"),
            tags=data.get("tags", []),
            priority=data.get("priority", "medium"),
            dependencies=data.get("dependencies", []),
            related_tasks=data.get("related_tasks", []),
            plan=data.get("plan", []),
            estimated_tokens=data.get("estimated_tokens", 2000),
            estimated_time_minutes=data.get("estimated_time_minutes", 60),
            constraints=data.get("constraints", []),
            feedback_required=data.get("feedback_required", False),
            feedback_topics=data.get("feedback_topics", []),
            optimization_targets=data.get("optimization_targets", []),
            cost_target=data.get("cost_target"),
            parent_task_id=data.get("parent_task_id"),
            related_artifacts=data.get("related_artifacts", []),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema. Returns list of errors (empty if valid)."""
        errors = []
        
        # Core fields
        if not self.task_id or len(self.task_id) < 5:
            errors.append("task_id must be at least 5 characters")
        if self.role not in ["engineer", "senior-engineer", "lead-engineer", "principal-engineer", "security-engineer", "quality-engineer"]:
            errors.append(f"Invalid role: {self.role}")
        if self.effort not in ["low", "medium", "high", "extra-high"]:
            errors.append(f"Invalid effort: {self.effort}")
        if len(self.scope.split()) < 15:
            errors.append("scope must be at least 15 words")
        
        # Quality fields
        if not 0 <= self.quality_baseline <= 100:
            errors.append("quality_baseline must be 0-100")
        
        # Execution fields
        if not self.plan:
            errors.append("plan must not be empty")
        if self.estimated_tokens < 100:
            errors.append("estimated_tokens must be at least 100")
        
        return errors
