"""
Feedback/Outcome schema for capturing task outcomes and feeding into feedback loops.

The Feedback/Outcome protocol captures:
1. Task outcome (success/partial/failed)
2. Quality assessment (vs baseline)
3. Cost assessment (vs budget)
4. Trend data (7/30-day moving averages)
5. Routing effectiveness (which agent, success rate)
6. Recommendations (routing, model, effort changes)

Fields:
- task_id: Task identifier
- outcome: Task outcome (success, partial, failed)
- quality_assessment: Quality vs baseline
- cost_assessment: Cost vs budget
- trend_7day: 7-day moving average
- trend_30day: 30-day moving average
- routing_effectiveness: Agent success rate
- recommendations: List of recommendations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class FeedbackOutcome:
    """Feedback/Outcome schema."""
    
    # Core fields
    task_id: str
    outcome: str  # success, partial, failed
    
    # Quality assessment
    quality_baseline: int
    quality_achieved: int
    
    # Cost assessment
    cost_budget: float
    cost_actual: float
    
    # Optional fields with defaults
    quality_assessment: str = ""  # exceeds, meets, below
    cost_assessment: str = ""  # under, on, over
    
    # Trend data
    trend_7day: Dict[str, float] = field(default_factory=dict)  # 7-day moving averages
    trend_30day: Dict[str, float] = field(default_factory=dict)  # 30-day moving averages
    
    # Routing effectiveness
    agent_role: str = ""
    agent_success_rate: float = 0.0  # 0-1
    model_used: str = ""
    effort_level: str = ""
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    routing_recommendation: Optional[str] = None  # Recommended agent for similar tasks
    model_recommendation: Optional[str] = None  # Recommended model
    effort_recommendation: Optional[str] = None  # Recommended effort level
    
    # Metadata
    recorded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "task_id": self.task_id,
            "outcome": self.outcome,
            "quality_baseline": self.quality_baseline,
            "quality_achieved": self.quality_achieved,
            "quality_assessment": self.quality_assessment,
            "cost_budget": self.cost_budget,
            "cost_actual": self.cost_actual,
            "cost_assessment": self.cost_assessment,
            "trend_7day": self.trend_7day,
            "trend_30day": self.trend_30day,
            "agent_role": self.agent_role,
            "agent_success_rate": self.agent_success_rate,
            "model_used": self.model_used,
            "effort_level": self.effort_level,
            "recommendations": self.recommendations,
            "routing_recommendation": self.routing_recommendation,
            "model_recommendation": self.model_recommendation,
            "effort_recommendation": self.effort_recommendation,
            "recorded_at": self.recorded_at,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FeedbackOutcome":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            outcome=data["outcome"],
            quality_baseline=data.get("quality_baseline", 90),
            quality_achieved=data.get("quality_achieved", 0),
            quality_assessment=data.get("quality_assessment", ""),
            cost_budget=data.get("cost_budget", 0.0),
            cost_actual=data.get("cost_actual", 0.0),
            cost_assessment=data.get("cost_assessment", ""),
            trend_7day=data.get("trend_7day", {}),
            trend_30day=data.get("trend_30day", {}),
            agent_role=data.get("agent_role", ""),
            agent_success_rate=data.get("agent_success_rate", 0.0),
            model_used=data.get("model_used", ""),
            effort_level=data.get("effort_level", ""),
            recommendations=data.get("recommendations", []),
            routing_recommendation=data.get("routing_recommendation"),
            model_recommendation=data.get("model_recommendation"),
            effort_recommendation=data.get("effort_recommendation"),
            recorded_at=data.get("recorded_at", datetime.utcnow().isoformat()),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema."""
        errors = []
        
        if not self.task_id:
            errors.append("task_id is required")
        if self.outcome not in ["success", "partial", "failed"]:
            errors.append(f"Invalid outcome: {self.outcome}")
        if not 0 <= self.quality_baseline <= 100:
            errors.append("quality_baseline must be 0-100")
        if not 0 <= self.quality_achieved <= 100:
            errors.append("quality_achieved must be 0-100")
        if not 0 <= self.agent_success_rate <= 1:
            errors.append("agent_success_rate must be 0-1")
        
        return errors
    
    def compute_assessments(self) -> None:
        """Compute quality and cost assessments."""
        # Quality assessment
        if self.quality_achieved >= self.quality_baseline:
            self.quality_assessment = "exceeds"
        elif self.quality_achieved >= self.quality_baseline * 0.9:
            self.quality_assessment = "meets"
        else:
            self.quality_assessment = "below"
        
        # Cost assessment
        if self.cost_actual <= self.cost_budget * 0.9:
            self.cost_assessment = "under"
        elif self.cost_actual <= self.cost_budget * 1.1:
            self.cost_assessment = "on"
        else:
            self.cost_assessment = "over"
