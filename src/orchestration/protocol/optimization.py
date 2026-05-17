"""
Optimization schema for cost/quality optimization recommendations.

The Optimization protocol analyzes:
1. Historical outcomes (past similar tasks)
2. Cost opportunities (model downgrade, effort reduction, etc.)
3. Quality opportunities (model upgrade, more testing, etc.)
4. Recommendations (specific changes with estimated impact)

Fields:
- task_id: Task identifier
- historical_outcomes: List of past similar tasks
- cost_opportunities: List of cost-saving opportunities
- quality_opportunities: List of quality-improvement opportunities
- recommendations: List of recommendations with impact estimates
- confidence_score: Confidence in recommendations (0-1)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class CostOpportunity:
    """Cost-saving opportunity."""
    opportunity_type: str  # model_downgrade, effort_reduction, parallelization, etc.
    description: str
    estimated_savings: float  # Estimated cost savings in dollars
    estimated_savings_percent: float  # Percentage savings
    confidence: float  # 0-1
    implementation_effort: str  # low, medium, high


@dataclass
class QualityOpportunity:
    """Quality-improvement opportunity."""
    opportunity_type: str  # model_upgrade, more_testing, additional_review, etc.
    description: str
    estimated_improvement: int  # Estimated quality score improvement (0-100)
    estimated_cost_increase: float  # Estimated cost increase in dollars
    confidence: float  # 0-1
    implementation_effort: str  # low, medium, high


@dataclass
class Optimization:
    """Optimization schema."""
    
    # Core fields
    task_id: str
    
    # Historical data
    historical_outcomes: List[Dict] = field(default_factory=list)
    historical_success_rate: float = 0.0
    historical_avg_quality: float = 0.0
    historical_avg_cost: float = 0.0
    
    # Opportunities
    cost_opportunities: List[CostOpportunity] = field(default_factory=list)
    quality_opportunities: List[QualityOpportunity] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    primary_recommendation: Optional[str] = None
    confidence_score: float = 0.0  # 0-1
    
    # Impact estimation
    estimated_total_savings: float = 0.0
    estimated_quality_improvement: int = 0
    
    # Metadata
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "task_id": self.task_id,
            "historical_outcomes": self.historical_outcomes,
            "historical_success_rate": self.historical_success_rate,
            "historical_avg_quality": self.historical_avg_quality,
            "historical_avg_cost": self.historical_avg_cost,
            "cost_opportunities": [
                {
                    "opportunity_type": op.opportunity_type,
                    "description": op.description,
                    "estimated_savings": op.estimated_savings,
                    "estimated_savings_percent": op.estimated_savings_percent,
                    "confidence": op.confidence,
                    "implementation_effort": op.implementation_effort,
                }
                for op in self.cost_opportunities
            ],
            "quality_opportunities": [
                {
                    "opportunity_type": op.opportunity_type,
                    "description": op.description,
                    "estimated_improvement": op.estimated_improvement,
                    "estimated_cost_increase": op.estimated_cost_increase,
                    "confidence": op.confidence,
                    "implementation_effort": op.implementation_effort,
                }
                for op in self.quality_opportunities
            ],
            "recommendations": self.recommendations,
            "primary_recommendation": self.primary_recommendation,
            "confidence_score": self.confidence_score,
            "estimated_total_savings": self.estimated_total_savings,
            "estimated_quality_improvement": self.estimated_quality_improvement,
            "analyzed_at": self.analyzed_at,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Optimization":
        """Create from dictionary."""
        cost_opps = []
        for op_data in data.get("cost_opportunities", []):
            cost_opps.append(CostOpportunity(
                opportunity_type=op_data["opportunity_type"],
                description=op_data["description"],
                estimated_savings=op_data["estimated_savings"],
                estimated_savings_percent=op_data["estimated_savings_percent"],
                confidence=op_data["confidence"],
                implementation_effort=op_data["implementation_effort"],
            ))
        
        quality_opps = []
        for op_data in data.get("quality_opportunities", []):
            quality_opps.append(QualityOpportunity(
                opportunity_type=op_data["opportunity_type"],
                description=op_data["description"],
                estimated_improvement=op_data["estimated_improvement"],
                estimated_cost_increase=op_data["estimated_cost_increase"],
                confidence=op_data["confidence"],
                implementation_effort=op_data["implementation_effort"],
            ))
        
        return cls(
            task_id=data["task_id"],
            historical_outcomes=data.get("historical_outcomes", []),
            historical_success_rate=data.get("historical_success_rate", 0.0),
            historical_avg_quality=data.get("historical_avg_quality", 0.0),
            historical_avg_cost=data.get("historical_avg_cost", 0.0),
            cost_opportunities=cost_opps,
            quality_opportunities=quality_opps,
            recommendations=data.get("recommendations", []),
            primary_recommendation=data.get("primary_recommendation"),
            confidence_score=data.get("confidence_score", 0.0),
            estimated_total_savings=data.get("estimated_total_savings", 0.0),
            estimated_quality_improvement=data.get("estimated_quality_improvement", 0),
            analyzed_at=data.get("analyzed_at", datetime.utcnow().isoformat()),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema."""
        errors = []
        
        if not self.task_id:
            errors.append("task_id is required")
        if not 0 <= self.historical_success_rate <= 1:
            errors.append("historical_success_rate must be 0-1")
        if not 0 <= self.historical_avg_quality <= 100:
            errors.append("historical_avg_quality must be 0-100")
        if not 0 <= self.confidence_score <= 1:
            errors.append("confidence_score must be 0-1")
        
        return errors
