"""
Quality Evaluation schema for assessing HANDBACK results against DELEGATE baselines.

The Quality Evaluation protocol bridges DELEGATE (what was requested) and HANDBACK (what was delivered).

Fields:
- task_id: Task identifier
- delegate_task_id: Reference to DELEGATE
- handback_task_id: Reference to HANDBACK
- quality_baseline: Expected quality from DELEGATE
- quality_achieved: Actual quality from HANDBACK
- quality_score: Evaluation score (0-100)
- evaluation_results: Dict of evaluation results
- acceptance_criteria_assessment: Assessment of each criterion
- issues_found: List of issues
- recommendations: List of recommendations
- escalation_required: Boolean, whether escalation is needed
- escalation_reason: Reason for escalation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class QualityEvaluation:
    """Quality Evaluation schema."""
    
    # Core fields
    task_id: str
    delegate_task_id: str
    handback_task_id: str
    
    # Quality assessment
    quality_baseline: int  # Expected quality from DELEGATE
    quality_achieved: int  # Actual quality from HANDBACK
    quality_score: int = 0  # Evaluation score (0-100)
    
    # Evaluation results
    evaluation_results: Dict[str, bool] = field(default_factory=dict)
    acceptance_criteria_assessment: Dict[str, bool] = field(default_factory=dict)
    
    # Issues and recommendations
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Escalation
    escalation_required: bool = False
    escalation_reason: Optional[str] = None
    
    # Metadata
    evaluated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    evaluator: str = "quality-engineer"
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "task_id": self.task_id,
            "delegate_task_id": self.delegate_task_id,
            "handback_task_id": self.handback_task_id,
            "quality_baseline": self.quality_baseline,
            "quality_achieved": self.quality_achieved,
            "quality_score": self.quality_score,
            "evaluation_results": self.evaluation_results,
            "acceptance_criteria_assessment": self.acceptance_criteria_assessment,
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
            "escalation_required": self.escalation_required,
            "escalation_reason": self.escalation_reason,
            "evaluated_at": self.evaluated_at,
            "evaluator": self.evaluator,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "QualityEvaluation":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            delegate_task_id=data["delegate_task_id"],
            handback_task_id=data["handback_task_id"],
            quality_baseline=data["quality_baseline"],
            quality_achieved=data["quality_achieved"],
            quality_score=data.get("quality_score", 0),
            evaluation_results=data.get("evaluation_results", {}),
            acceptance_criteria_assessment=data.get("acceptance_criteria_assessment", {}),
            issues_found=data.get("issues_found", []),
            recommendations=data.get("recommendations", []),
            escalation_required=data.get("escalation_required", False),
            escalation_reason=data.get("escalation_reason"),
            evaluated_at=data.get("evaluated_at", datetime.utcnow().isoformat()),
            evaluator=data.get("evaluator", "quality-engineer"),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema."""
        errors = []
        
        if not self.task_id:
            errors.append("task_id is required")
        if not self.delegate_task_id:
            errors.append("delegate_task_id is required")
        if not self.handback_task_id:
            errors.append("handback_task_id is required")
        if not 0 <= self.quality_baseline <= 100:
            errors.append("quality_baseline must be 0-100")
        if not 0 <= self.quality_achieved <= 100:
            errors.append("quality_achieved must be 0-100")
        if not 0 <= self.quality_score <= 100:
            errors.append("quality_score must be 0-100")
        
        return errors
    
    def compute_quality_score(self) -> int:
        """Compute quality score based on evaluation results."""
        if not self.evaluation_results:
            return 0
        
        passed = sum(1 for v in self.evaluation_results.values() if v)
        total = len(self.evaluation_results)
        
        # Base score from evaluation results
        base_score = int((passed / total) * 100) if total > 0 else 0
        
        # Adjust based on acceptance criteria
        if self.acceptance_criteria_assessment:
            criteria_passed = sum(1 for v in self.acceptance_criteria_assessment.values() if v)
            criteria_total = len(self.acceptance_criteria_assessment)
            criteria_score = int((criteria_passed / criteria_total) * 100) if criteria_total > 0 else 0
            
            # Weight: 70% evaluation, 30% acceptance criteria
            self.quality_score = int(0.7 * base_score + 0.3 * criteria_score)
        else:
            self.quality_score = base_score
        
        # Deduct for issues
        if self.issues_found:
            deduction = min(len(self.issues_found) * 5, 30)  # Max 30 point deduction
            self.quality_score = max(0, self.quality_score - deduction)
        
        return self.quality_score
