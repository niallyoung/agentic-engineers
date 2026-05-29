"""
Orchestrator Integration Module - Connects expanded protocol schemas to Orchestrator.

This module provides:
1. ExpandedDelegateHandler: Creates expanded DELEGATEs with quality baselines
2. ExpandedHandbackHandler: Processes expanded HANDBACKs with quality evaluation
3. QualityEvaluationEngine: Computes quality scores and assessments
4. FeedbackLoopEngine: Creates feedback/outcome artifacts and recommendations
5. OptimizationEngine: Analyzes historical outcomes and generates optimization recommendations
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from .expanded_delegate import ExpandedDelegate
from .expanded_handback import ExpandedHandback
from .quality_evaluation import QualityEvaluation
from .feedback_outcome import FeedbackOutcome
from .optimization import Optimization, CostOpportunity, QualityOpportunity
from .event_model import Event, EventType
from .artifact_linking import ArtifactLink, ArtifactLinkage

logger = logging.getLogger(__name__)


class ExpandedDelegateHandler:
    """Creates and manages expanded DELEGATEs with quality baselines."""
    
    @staticmethod
    def create_delegate(
        task_id: str,
        role: str,
        model: str,
        effort: str,
        scope: str,
        plan: List[str],
        quality_baseline: int = 90,
        acceptance_criteria: Optional[List[str]] = None,
        quality_thresholds: Optional[Dict[str, int]] = None,
        tags: Optional[List[str]] = None,
        priority: str = "medium",
        dependencies: Optional[List[str]] = None,
        estimated_tokens: int = 0,
        estimated_time_minutes: int = 0,
        constraints: Optional[List[str]] = None,
        feedback_required: bool = True,
        feedback_topics: Optional[List[str]] = None,
        optimization_targets: Optional[List[str]] = None,
        cost_target: float = 0.0,
        parent_task_id: Optional[str] = None,
        related_artifacts: Optional[List[str]] = None,
    ) -> ExpandedDelegate:
        """
        Create an expanded DELEGATE with quality baseline and metadata.
        
        Args:
            task_id: Unique task identifier (YYYY-MM-DD-kebab-case)
            role: Agent role (engineer, senior-engineer, lead-engineer, principal-engineer, security-engineer, quality-engineer)
             model: Model to use (claude-haiku-4.5, claude-sonnet-4.6, claude-opus-4.6, claude-opus-4.8)
            effort: Effort level (low, medium, high, extra-high)
            scope: Task description (≥15 words)
            plan: Numbered list of concrete steps
            quality_baseline: Expected quality score (0-100, default 90)
            acceptance_criteria: List of acceptance criteria
            quality_thresholds: Dict of metric thresholds
            tags: List of tags for categorization
            priority: Priority level (low, medium, high, critical)
            dependencies: List of task IDs this task depends on
            estimated_tokens: Estimated token budget
            estimated_time_minutes: Estimated execution time
            constraints: List of constraints
            feedback_required: Whether feedback is required
            feedback_topics: List of feedback topics
            optimization_targets: List of optimization targets
            cost_target: Target cost in dollars
            parent_task_id: Parent task ID (for sub-tasks)
            related_artifacts: List of related artifact paths
        
        Returns:
            ExpandedDelegate instance
        """
        delegate = ExpandedDelegate(
            task_id=task_id,
            role=role,
            model=model,
            effort=effort,
            scope=scope,
            quality_baseline=quality_baseline,
            acceptance_criteria=acceptance_criteria or [],
            quality_thresholds=quality_thresholds or {},
            quality_required_by=datetime.now().isoformat(),
            tags=tags or [],
            priority=priority,
            dependencies=dependencies or [],
            related_tasks=[],
            plan=plan,
            estimated_tokens=estimated_tokens,
            estimated_time_minutes=estimated_time_minutes,
            constraints=constraints or [],
            feedback_required=feedback_required,
            feedback_topics=feedback_topics or [],
            optimization_targets=optimization_targets or [],
            cost_target=cost_target,
            parent_task_id=parent_task_id,
            related_artifacts=related_artifacts or [],
        )
        
        # Validate delegate
        errors = delegate.validate()
        if errors:
            logger.warning(f"Delegate validation warnings: {errors}")
        
        return delegate
    
    @staticmethod
    def to_dict(delegate: ExpandedDelegate) -> Dict:
        """Convert expanded DELEGATE to dictionary for YAML serialization."""
        return delegate.to_dict()
    
    @staticmethod
    def from_dict(data: Dict) -> ExpandedDelegate:
        """Create expanded DELEGATE from dictionary (YAML deserialization)."""
        return ExpandedDelegate.from_dict(data)


class ExpandedHandbackHandler:
    """Processes and manages expanded HANDBACKs with quality evaluation."""
    
    @staticmethod
    def create_handback(
        task_id: str,
        status: str,
        deliverables: Optional[List[str]] = None,
        tests: Optional[Dict[str, bool]] = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        time_elapsed_minutes: float = 0,
        cost_actual: float = 0.0,
        model_used: str = "",
        quality_score: int = 0,
        test_coverage: float = 0.0,
        regressions_detected: int = 0,
        acceptance_criteria_met: Optional[List[str]] = None,
        model_assessment: str = "",
        blockers: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        escalation_reason: str = "",
        success_rate: float = 0.0,
        quality_trend: str = "",
        cost_trend: str = "",
        effort_actual: str = "medium",
        related_delegates: Optional[List[str]] = None,
        related_handbacks: Optional[List[str]] = None,
        artifact_paths: Optional[List[str]] = None,
        notes: str = "",
    ) -> ExpandedHandback:
        """
        Create an expanded HANDBACK with quality metrics and feedback.
        
        Args:
            task_id: Task identifier (matches DELEGATE)
            status: Task status (complete, failed, partial, blocked)
            deliverables: List of deliverables
            tests: Dict of test results
            tokens_in: Input tokens used
            tokens_out: Output tokens used
            time_elapsed_minutes: Execution time
            cost_actual: Actual cost in dollars
            model_used: Model actually used
            quality_score: Quality score (0-100)
            test_coverage: Test coverage percentage (0-1)
            regressions_detected: Number of regressions
            acceptance_criteria_met: List of met criteria
            model_assessment: Model suitability assessment
            blockers: List of blockers encountered
            recommendations: List of recommendations
            escalation_reason: Reason for escalation (if any)
            success_rate: Success rate (0-1)
            quality_trend: Quality trend vs baseline
            cost_trend: Cost trend vs budget
            effort_actual: Actual effort level
            related_delegates: List of related DELEGATE task IDs
            related_handbacks: List of related HANDBACK task IDs
            artifact_paths: List of artifact file paths
            notes: Free-form notes
        
        Returns:
            ExpandedHandback instance
        """
        handback = ExpandedHandback(
            task_id=task_id,
            status=status,
            deliverables=deliverables or [],
            tests=tests or {},
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            time_elapsed_minutes=time_elapsed_minutes,
            cost_actual=cost_actual,
            model_used=model_used,
            quality_score=quality_score,
            test_coverage=test_coverage,
            regressions_detected=regressions_detected,
            acceptance_criteria_met=acceptance_criteria_met or [],
            model_assessment=model_assessment,
            blockers=blockers or [],
            recommendations=recommendations or [],
            escalation_reason=escalation_reason,
            success_rate=success_rate,
            quality_trend=quality_trend,
            cost_trend=cost_trend,
            effort_actual=effort_actual,
            related_delegates=related_delegates or [],
            related_handbacks=related_handbacks or [],
            artifact_paths=artifact_paths or [],
            duration_minutes=time_elapsed_minutes,
            notes=notes,
        )
        
        # Validate handback
        errors = handback.validate()
        if errors:
            logger.warning(f"Handback validation warnings: {errors}")
        
        return handback
    
    @staticmethod
    def to_dict(handback: ExpandedHandback) -> Dict:
        """Convert expanded HANDBACK to dictionary for YAML serialization."""
        return handback.to_dict()
    
    @staticmethod
    def from_dict(data: Dict) -> ExpandedHandback:
        """Create expanded HANDBACK from dictionary (YAML deserialization)."""
        return ExpandedHandback.from_dict(data)


class QualityEvaluationEngine:
    """Evaluates quality by comparing DELEGATE baseline with HANDBACK results."""
    
    @staticmethod
    def evaluate(
        delegate: ExpandedDelegate,
        handback: ExpandedHandback,
    ) -> QualityEvaluation:
        """
        Evaluate quality by comparing DELEGATE baseline with HANDBACK results.
        
        Args:
            delegate: Original DELEGATE with quality_baseline
            handback: HANDBACK with quality_score and metrics
        
        Returns:
            QualityEvaluation with computed quality score and assessment
        """
        # Compute quality score
        quality_score = handback.quality_score
        
        # Determine assessment (exceeds, meets, below)
        quality_baseline = delegate.quality_baseline
        if quality_score >= quality_baseline + 5:
            assessment = "exceeds"
        elif quality_score >= quality_baseline - 5:
            assessment = "meets"
        else:
            assessment = "below"
        
        # Assess acceptance criteria
        acceptance_criteria_assessment = {}
        for criterion in delegate.acceptance_criteria:
            if criterion in handback.acceptance_criteria_met:
                acceptance_criteria_assessment[criterion] = "met"
            else:
                acceptance_criteria_assessment[criterion] = "not_met"
        
        # Identify issues
        issues = []
        if handback.regressions_detected > 0:
            issues.append(f"Regressions detected: {handback.regressions_detected}")
        if handback.test_coverage < 0.8:
            issues.append(f"Test coverage below 80%: {handback.test_coverage * 100:.1f}%")
        if assessment == "below":
            issues.append(f"Quality below baseline: {quality_score} < {quality_baseline}")
        
        # Generate recommendations
        recommendations = []
        if assessment == "below":
            recommendations.append("Review quality issues and resubmit")
        if handback.test_coverage < 0.8:
            recommendations.append("Increase test coverage to ≥80%")
        if handback.regressions_detected > 0:
            recommendations.append("Fix regressions before merging")
        
        # Determine escalation
        escalation_required = (
            quality_score < 70 or
            handback.regressions_detected > 0 or
            len([c for c in acceptance_criteria_assessment.values() if c == "not_met"]) > 0
        )
        
        escalation_reason = ""
        if quality_score < 70:
            escalation_reason = f"Quality score below 70: {quality_score}"
        elif handback.regressions_detected > 0:
            escalation_reason = f"Regressions detected: {handback.regressions_detected}"
        
        evaluation = QualityEvaluation(
            task_id=delegate.task_id,
            delegate_task_id=delegate.task_id,
            handback_task_id=handback.task_id,
            quality_baseline=delegate.quality_baseline,
            quality_achieved=handback.quality_score,
            quality_score=quality_score,
            evaluation_results={
                "assessment": assessment,
                "test_coverage": handback.test_coverage,
                "regressions": handback.regressions_detected,
            },
            acceptance_criteria_assessment=acceptance_criteria_assessment,
            issues_found=issues,
            recommendations=recommendations,
            escalation_required=escalation_required,
            escalation_reason=escalation_reason,
        )
        
        return evaluation


class FeedbackLoopEngine:
    """Creates feedback/outcome artifacts and generates recommendations."""
    
    @staticmethod
    def create_feedback(
        handback: ExpandedHandback,
        delegate: ExpandedDelegate,
        quality_evaluation: QualityEvaluation,
        historical_outcomes: Optional[List[Dict]] = None,
    ) -> FeedbackOutcome:
        """
        Create feedback/outcome artifact from HANDBACK and quality evaluation.
        
        Args:
            handback: HANDBACK with metrics
            delegate: Original DELEGATE with baseline
            quality_evaluation: Quality evaluation results
            historical_outcomes: List of past similar tasks (for trend analysis)
        
        Returns:
            FeedbackOutcome with assessments and recommendations
        """
        # Determine outcome
        if handback.status == "complete" and quality_evaluation.quality_score >= 80:
            outcome = "success"
        elif handback.status == "complete" and quality_evaluation.quality_score >= 70:
            outcome = "partial"
        else:
            outcome = "failed"
        
        # Create feedback outcome
        feedback = FeedbackOutcome(
            task_id=delegate.task_id,
            outcome=outcome,
            quality_baseline=delegate.quality_baseline,
            quality_achieved=handback.quality_score,
            cost_budget=delegate.cost_target,
            cost_actual=handback.cost_actual,
        )
        
        # Compute assessments
        feedback.compute_assessments()
        
        # Add trend data if historical outcomes available
        if historical_outcomes:
            feedback.trend_7day = FeedbackLoopEngine._compute_trend(
                historical_outcomes, days=7
            )
            feedback.trend_30day = FeedbackLoopEngine._compute_trend(
                historical_outcomes, days=30
            )
        
        # Add recommendations
        feedback.recommendations = quality_evaluation.recommendations
        
        # Add routing recommendation
        if outcome == "success":
            feedback.routing_recommendation = delegate.role
            feedback.model_recommendation = delegate.model
            feedback.effort_recommendation = delegate.effort
        else:
            # Recommend escalation or different approach
            if quality_evaluation.quality_score < 70:
                feedback.routing_recommendation = "senior_engineer"
            else:
                feedback.routing_recommendation = delegate.role
        
        return feedback
    
    @staticmethod
    def _compute_trend(outcomes: List[Dict], days: int) -> Dict:
        """Compute moving average trend over N days."""
        if not outcomes:
            return {}
        
        # Filter outcomes within N days
        now = datetime.now()
        recent = [
            o for o in outcomes
            if (now - datetime.fromisoformat(o.get("timestamp", now.isoformat()))).days <= days
        ]
        
        if not recent:
            return {}
        
        # Compute averages
        avg_quality = sum(o.get("quality_score", 0) for o in recent) / len(recent)
        avg_cost = sum(o.get("cost_actual", 0) for o in recent) / len(recent)
        success_count = sum(1 for o in recent if o.get("outcome") == "success")
        success_rate = success_count / len(recent)
        
        return {
            "days": days,
            "count": len(recent),
            "avg_quality": avg_quality,
            "avg_cost": avg_cost,
            "success_rate": success_rate,
        }


class OptimizationEngine:
    """Analyzes historical outcomes and generates optimization recommendations."""
    
    @staticmethod
    def analyze(
        delegate: ExpandedDelegate,
        handback: ExpandedHandback,
        feedback: FeedbackOutcome,
        historical_outcomes: Optional[List[Dict]] = None,
    ) -> Optimization:
        """
        Analyze task outcomes and generate optimization recommendations.
        
        Args:
            delegate: Original DELEGATE
            handback: HANDBACK with metrics
            feedback: Feedback/outcome analysis
            historical_outcomes: List of past similar tasks
        
        Returns:
            Optimization with cost/quality opportunities and recommendations
        """
        historical_outcomes = historical_outcomes or []
        
        # Compute historical metrics
        if historical_outcomes:
            historical_success_rate = sum(
                1 for o in historical_outcomes if o.get("outcome") == "success"
            ) / len(historical_outcomes)
            historical_avg_quality = sum(
                o.get("quality_score", 0) for o in historical_outcomes
            ) / len(historical_outcomes)
            historical_avg_cost = sum(
                o.get("cost_actual", 0) for o in historical_outcomes
            ) / len(historical_outcomes)
        else:
            historical_success_rate = 0.0
            historical_avg_quality = 0
            historical_avg_cost = 0.0
        
        # Identify cost opportunities
        cost_opportunities = []
         if delegate.model == "claude-opus-4.8" and handback.quality_score >= 85:
            # Could downgrade to Sonnet
            cost_opportunities.append(
                CostOpportunity(
                    opportunity_type="model_downgrade",
                    description="Downgrade from Opus to Sonnet",
                    estimated_savings=0.33,  # $0.33 savings
                    estimated_savings_percent=0.33,  # 33% cost reduction
                    confidence=0.7,
                    implementation_effort="low",
                )
            )
        
        if delegate.effort == "high" and handback.quality_score >= 90:
            # Could reduce effort
            cost_opportunities.append(
                CostOpportunity(
                    opportunity_type="effort_reduction",
                    description="Reduce effort from high to medium",
                    estimated_savings=0.25,  # $0.25 savings
                    estimated_savings_percent=0.25,  # 25% cost reduction
                    confidence=0.6,
                    implementation_effort="medium",
                )
            )
        
        # Identify quality opportunities
        quality_opportunities = []
         if handback.quality_score < 85 and delegate.model not in ("claude-opus-4.6", "claude-opus-4.8"):
            # Could upgrade model
            quality_opportunities.append(
                QualityOpportunity(
                    opportunity_type="model_upgrade",
                    description="Upgrade to Opus for better quality",
                    estimated_improvement=5,  # 5 point improvement
                    estimated_cost_increase=0.33,  # $0.33 cost increase
                    confidence=0.8,
                    implementation_effort="low",
                )
            )
        
        if handback.test_coverage < 0.9:
            # Could add more testing
            quality_opportunities.append(
                QualityOpportunity(
                    opportunity_type="additional_testing",
                    description="Add more comprehensive tests",
                    estimated_improvement=3,  # 3 point improvement
                    estimated_cost_increase=0.15,  # $0.15 cost increase
                    confidence=0.7,
                    implementation_effort="medium",
                )
            )
        
        # Generate recommendations
        recommendations = []
        if cost_opportunities:
            recommendations.append(f"Consider cost optimization: {cost_opportunities[0].description}")
        if quality_opportunities:
            recommendations.append(f"Consider quality improvement: {quality_opportunities[0].description}")
        
        # Determine primary recommendation
        primary_recommendation = ""
        if feedback.outcome == "success":
            if cost_opportunities:
                primary_recommendation = f"Replicate approach with cost optimization: {cost_opportunities[0].description}"
            else:
                primary_recommendation = "Replicate this approach for similar tasks"
        else:
            if quality_opportunities:
                primary_recommendation = f"Improve approach: {quality_opportunities[0].description}"
            else:
                primary_recommendation = "Review and improve approach for next attempt"
        
        # Compute confidence
        confidence = 0.7 if historical_outcomes else 0.5
        
        # Compute estimated savings/improvement
        estimated_savings = sum(o.estimated_savings for o in cost_opportunities)
        estimated_improvement = sum(o.estimated_improvement for o in quality_opportunities)
        
        optimization = Optimization(
            task_id=delegate.task_id,
            historical_outcomes=historical_outcomes,
            historical_success_rate=historical_success_rate,
            historical_avg_quality=historical_avg_quality,
            historical_avg_cost=historical_avg_cost,
            cost_opportunities=cost_opportunities,
            quality_opportunities=quality_opportunities,
            recommendations=recommendations,
            primary_recommendation=primary_recommendation,
            confidence_score=confidence,
            estimated_total_savings=estimated_savings,
            estimated_quality_improvement=estimated_improvement,
        )
        
        return optimization


class ProtocolEventPublisher:
    """Publishes events for task lifecycle tracking."""
    
    def __init__(self):
        self.events: List[Event] = []
    
    def publish_event(
        self,
        event_type: EventType,
        task_id: str,
        actor: str,
        actor_role: str,
        data: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        priority: str = "normal",
    ) -> Event:
        """Publish a task lifecycle event."""
        event = Event(
            event_id=f"{task_id}-{event_type.value}-{datetime.now().isoformat()}",
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            actor=actor,
            actor_role=actor_role,
            data=data or {},
            tags=tags or [],
            priority=priority,
            related_events=[],
        )
        
        self.events.append(event)
        logger.info(f"Event published: {event_type.value} for task {task_id}")
        
        return event
    
    def get_events(self, task_id: str) -> List[Event]:
        """Get all events for a task."""
        return [e for e in self.events if e.task_id == task_id]
