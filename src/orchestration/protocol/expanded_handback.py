"""
Expanded HANDBACK schema with 25+ fields for cross-lifecycle reuse.

Core fields (4):
- task_id: Task identifier (matches DELEGATE)
- status: Task status (complete, failed, partial, blocked, escalate)
- deliverables: List of deliverables
- tests: Dict of test results

Execution metrics (5):
- tokens_in: Input tokens used
- tokens_out: Output tokens used
- time_elapsed_minutes: Execution time
- cost_actual: Actual cost in dollars
- model_used: Model actually used

Quality metrics (4):
- quality_score: Quality score (0-100)
- test_coverage: Test coverage percentage
- regressions_detected: Number of regressions
- acceptance_criteria_met: List of met criteria

Feedback fields (4):
- model_assessment: Model suitability assessment
- blockers: List of blockers encountered
- recommendations: List of recommendations
- escalation_reason: Reason for escalation (if any)

Outcome fields (4):
- success_rate: Success rate (0-1)
- quality_trend: Quality trend vs baseline
- cost_trend: Cost trend vs budget
- effort_actual: Actual effort level

Linked artifacts (3):
- related_delegates: List of related DELEGATE task IDs
- related_handbacks: List of related HANDBACK task IDs
- artifact_paths: List of artifact file paths

Metadata fields (2):
- duration_minutes: Total duration
- notes: Free-form notes
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ExpandedHandback:
    """Expanded HANDBACK schema with 25+ fields."""
    
    # Core fields (4)
    task_id: str
    status: str  # complete, failed, partial, blocked, escalate
    deliverables: List[str] = field(default_factory=list)
    tests: Dict[str, bool] = field(default_factory=dict)
    
    # Execution metrics (5)
    tokens_in: int = 0
    tokens_out: int = 0
    time_elapsed_minutes: int = 0
    cost_actual: float = 0.0
    model_used: str = ""
    
    # Quality metrics (4)
    quality_score: int = 0  # 0-100
    test_coverage: float = 0.0  # 0-1
    regressions_detected: int = 0
    acceptance_criteria_met: List[str] = field(default_factory=list)
    
    # Feedback fields (4)
    model_assessment: str = ""  # haiku_suitable, sonnet_suitable, opus_required, over_engineered
    blockers: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    escalation_reason: Optional[str] = None
    
    # Outcome fields (4)
    success_rate: float = 0.0  # 0-1
    quality_trend: str = "stable"  # improving, stable, declining
    cost_trend: str = "stable"  # under_budget, on_budget, over_budget
    effort_actual: str = "medium"  # low, medium, high, extra-high
    
    # Linked artifacts (3)
    related_delegates: List[str] = field(default_factory=list)
    related_handbacks: List[str] = field(default_factory=list)
    artifact_paths: List[str] = field(default_factory=list)
    
    # Metadata fields (2)
    duration_minutes: int = 0
    notes: str = ""
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            # Core
            "task_id": self.task_id,
            "status": self.status,
            "deliverables": self.deliverables,
            "tests": self.tests,
            # Execution metrics
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "time_elapsed_minutes": self.time_elapsed_minutes,
            "cost_actual": self.cost_actual,
            "model_used": self.model_used,
            # Quality metrics
            "quality_score": self.quality_score,
            "test_coverage": self.test_coverage,
            "regressions_detected": self.regressions_detected,
            "acceptance_criteria_met": self.acceptance_criteria_met,
            # Feedback
            "model_assessment": self.model_assessment,
            "blockers": self.blockers,
            "recommendations": self.recommendations,
            "escalation_reason": self.escalation_reason,
            # Outcome
            "success_rate": self.success_rate,
            "quality_trend": self.quality_trend,
            "cost_trend": self.cost_trend,
            "effort_actual": self.effort_actual,
            # Linked artifacts
            "related_delegates": self.related_delegates,
            "related_handbacks": self.related_handbacks,
            "artifact_paths": self.artifact_paths,
            # Metadata
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "created_at": self.created_at,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ExpandedHandback":
        """Create from dictionary (YAML deserialization)."""
        return cls(
            task_id=data["task_id"],
            status=data["status"],
            deliverables=data.get("deliverables", []),
            tests=data.get("tests", {}),
            tokens_in=data.get("tokens_in", 0),
            tokens_out=data.get("tokens_out", 0),
            time_elapsed_minutes=data.get("time_elapsed_minutes", 0),
            cost_actual=data.get("cost_actual", 0.0),
            model_used=data.get("model_used", ""),
            quality_score=data.get("quality_score", 0),
            test_coverage=data.get("test_coverage", 0.0),
            regressions_detected=data.get("regressions_detected", 0),
            acceptance_criteria_met=data.get("acceptance_criteria_met", []),
            model_assessment=data.get("model_assessment", ""),
            blockers=data.get("blockers", []),
            recommendations=data.get("recommendations", []),
            escalation_reason=data.get("escalation_reason"),
            success_rate=data.get("success_rate", 0.0),
            quality_trend=data.get("quality_trend", "stable"),
            cost_trend=data.get("cost_trend", "stable"),
            effort_actual=data.get("effort_actual", "medium"),
            related_delegates=data.get("related_delegates", []),
            related_handbacks=data.get("related_handbacks", []),
            artifact_paths=data.get("artifact_paths", []),
            duration_minutes=data.get("duration_minutes", 0),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema. Returns list of errors (empty if valid)."""
        errors = []
        
        # Core fields
        if not self.task_id:
            errors.append("task_id is required")
        if self.status not in ["complete", "failed", "partial", "blocked", "escalate"]:
            errors.append(f"Invalid status: {self.status}")
        
        # Quality metrics
        if not 0 <= self.quality_score <= 100:
            errors.append("quality_score must be 0-100")
        if not 0 <= self.test_coverage <= 1:
            errors.append("test_coverage must be 0-1")
        if not 0 <= self.success_rate <= 1:
            errors.append("success_rate must be 0-1")
        
        # Trends
        if self.quality_trend not in ["improving", "stable", "declining"]:
            errors.append(f"Invalid quality_trend: {self.quality_trend}")
        if self.cost_trend not in ["under_budget", "on_budget", "over_budget"]:
            errors.append(f"Invalid cost_trend: {self.cost_trend}")
        
        return errors
