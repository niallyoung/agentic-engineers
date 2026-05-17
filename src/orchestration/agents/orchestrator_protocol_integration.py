"""
Orchestrator Protocol Integration Module

Extends the Orchestrator with expanded protocol schema support:
1. Creates expanded DELEGATEs with quality baselines
2. Processes expanded HANDBACKs with quality evaluation
3. Integrates Quality Evaluation Engine
4. Integrates Feedback Loop Engine
5. Integrates Optimization Engine
6. Publishes task lifecycle events
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..protocol.orchestrator_integration import (
    ExpandedDelegateHandler,
    ExpandedHandbackHandler,
    QualityEvaluationEngine,
    FeedbackLoopEngine,
    OptimizationEngine,
    ProtocolEventPublisher,
)
from ..protocol.event_model import EventType

logger = logging.getLogger(__name__)


class OrchestratorProtocolIntegration:
    """Integrates expanded protocol schemas with Orchestrator."""
    
    def __init__(self):
        self.event_publisher = ProtocolEventPublisher()
        self.historical_outcomes: Dict[str, List[Dict]] = {}  # task_id -> outcomes
    
    def create_expanded_delegate(
        self,
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
    ):
        """
        Create an expanded DELEGATE with quality baseline.
        
        This replaces the standard DELEGATE creation in the Orchestrator.
        """
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id=task_id,
            role=role,
            model=model,
            effort=effort,
            scope=scope,
            plan=plan,
            quality_baseline=quality_baseline,
            acceptance_criteria=acceptance_criteria,
            quality_thresholds=quality_thresholds,
            tags=tags,
            priority=priority,
            dependencies=dependencies,
            estimated_tokens=estimated_tokens,
            estimated_time_minutes=estimated_time_minutes,
            constraints=constraints,
            feedback_required=feedback_required,
            feedback_topics=feedback_topics,
            optimization_targets=optimization_targets,
            cost_target=cost_target,
            parent_task_id=parent_task_id,
            related_artifacts=related_artifacts,
        )
        
        # Publish delegate.created event
        self.event_publisher.publish_event(
            event_type=EventType.DELEGATE_CREATED,
            task_id=task_id,
            actor="orchestrator",
            actor_role="orchestrator",
            data={
                "role": role,
                "model": model,
                "effort": effort,
                "quality_baseline": quality_baseline,
            },
            tags=["protocol", "delegate"],
        )
        
        logger.info(f"Created expanded DELEGATE {task_id} with quality_baseline={quality_baseline}")
        return delegate
    
    def process_expanded_handback(
        self,
        handback_dict: Dict,
        original_delegate_dict: Dict,
    ) -> Tuple[str, Dict]:
        """
        Process expanded HANDBACK with quality evaluation.
        
        This replaces the standard route_handback method in the Orchestrator.
        
        Returns:
            Tuple of (action, context) where:
            - action: 'PROCEED' | 'MANUAL_REVIEW' | 'REWORK' | 'ESCALATE'
            - context: Dict with routing details, evaluation results, recommendations
        """
        task_id = handback_dict.get("task_id", "unknown")
        
        # Convert to expanded schemas
        handback = ExpandedHandbackHandler.from_dict(handback_dict)
        delegate = ExpandedDelegateHandler.from_dict(original_delegate_dict)
        
        # Publish execution.completed event
        self.event_publisher.publish_event(
            event_type=EventType.EXECUTION_COMPLETED,
            task_id=task_id,
            actor="agent",
            actor_role=delegate.role,
            data={
                "status": handback.status,
                "quality_score": handback.quality_score,
                "cost_actual": handback.cost_actual,
            },
        )
        
        # Step 1: Quality Evaluation
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        
        # Publish quality.evaluated event
        self.event_publisher.publish_event(
            event_type=EventType.QUALITY_EVALUATED,
            task_id=task_id,
            actor="quality_engine",
            actor_role="quality_engineer",
            data={
                "quality_score": evaluation.quality_score,
                "assessment": evaluation.acceptance_criteria_assessment,
                "escalation_required": evaluation.escalation_required,
            },
            priority="high" if evaluation.escalation_required else "normal",
        )
        
        logger.info(
            f"Quality evaluation for {task_id}: "
            f"baseline={evaluation.quality_baseline}, "
            f"achieved={evaluation.quality_achieved}, "
            f"assessment={evaluation.acceptance_criteria_assessment}"
        )
        
        # Step 2: Route based on quality evaluation
        action, context = self._route_by_quality_evaluation(
            evaluation, delegate, handback, original_delegate_dict
        )
        
        # Step 3: If PROCEED, create feedback and optimization
        if action == "PROCEED":
            # Get historical outcomes for this task type
            historical = self.historical_outcomes.get(delegate.role, [])
            
            # Create feedback/outcome
            feedback = FeedbackLoopEngine.create_feedback(
                handback, delegate, evaluation, historical_outcomes=historical
            )
            
            # Publish feedback.recorded event
            self.event_publisher.publish_event(
                event_type=EventType.FEEDBACK_RECORDED,
                task_id=task_id,
                actor="feedback_loop",
                actor_role="feedback_loop",
                data={
                    "outcome": feedback.outcome,
                    "quality_assessment": feedback.quality_assessment,
                    "cost_assessment": feedback.cost_assessment,
                    "routing_recommendation": feedback.routing_recommendation,
                },
            )
            
            # Create optimization analysis
            optimization = OptimizationEngine.analyze(
                delegate, handback, feedback, historical_outcomes=historical
            )
            
            # Publish optimization.recommended event
            self.event_publisher.publish_event(
                event_type=EventType.OPTIMIZATION_RECOMMENDED,
                task_id=task_id,
                actor="optimization_engine",
                actor_role="optimization_engine",
                data={
                    "primary_recommendation": optimization.primary_recommendation,
                    "estimated_savings": optimization.estimated_total_savings,
                    "estimated_improvement": optimization.estimated_quality_improvement,
                },
            )
            
            # Add feedback and optimization to context
            context["feedback"] = {
                "outcome": feedback.outcome,
                "quality_assessment": feedback.quality_assessment,
                "cost_assessment": feedback.cost_assessment,
                "routing_recommendation": feedback.routing_recommendation,
                "model_recommendation": feedback.model_recommendation,
                "effort_recommendation": feedback.effort_recommendation,
            }
            
            context["optimization"] = {
                "primary_recommendation": optimization.primary_recommendation,
                "cost_opportunities": len(optimization.cost_opportunities),
                "quality_opportunities": len(optimization.quality_opportunities),
                "estimated_savings": optimization.estimated_total_savings,
                "estimated_improvement": optimization.estimated_quality_improvement,
            }
            
            # Record outcome for historical analysis
            self._record_outcome(delegate, handback, feedback)
            
            logger.info(
                f"Task {task_id} PROCEED with feedback: "
                f"outcome={feedback.outcome}, "
                f"recommendation={optimization.primary_recommendation}"
            )
        
        # Publish task.completed event (if PROCEED)
        if action == "PROCEED":
            self.event_publisher.publish_event(
                event_type=EventType.TASK_COMPLETED,
                task_id=task_id,
                actor="orchestrator",
                actor_role="orchestrator",
                data={"status": "done", "quality_score": evaluation.quality_score},
            )
        
        return (action, context)
    
    def _route_by_quality_evaluation(
        self,
        evaluation,
        delegate,
        handback,
        original_delegate_dict: Dict,
    ) -> Tuple[str, Dict]:
        """Route HANDBACK based on quality evaluation results."""
        
        quality_score = evaluation.quality_score
        task_id = evaluation.task_id
        
        # Check for escalation requirements
        if evaluation.escalation_required:
            escalation_context = {
                "action": "ESCALATE",
                "reason": evaluation.escalation_reason,
                "quality_score": quality_score,
                "escalation_level": "principal_engineer" if quality_score < 70 else "lead_engineer",
                "issues": evaluation.issues_found,
                "recommendations": evaluation.recommendations,
                "evaluation": {
                    "baseline": evaluation.quality_baseline,
                    "achieved": evaluation.quality_achieved,
                    "assessment": evaluation.acceptance_criteria_assessment,
                },
            }
            return ("ESCALATE", escalation_context)
        
        # Route based on quality score bands
        if quality_score >= 90:
            return (
                "PROCEED",
                {
                    "action": "PROCEED",
                    "reason": "High quality score (90+)",
                    "quality_score": quality_score,
                    "assessment": "exceeds",
                },
            )
        
        elif quality_score >= 80:
            return (
                "PROCEED",
                {
                    "action": "PROCEED",
                    "reason": "Acceptable quality score (80-89)",
                    "quality_score": quality_score,
                    "assessment": "meets",
                    "notes": "Minor improvements possible in future iterations",
                },
            )
        
        elif quality_score >= 70:
            return (
                "MANUAL_REVIEW",
                {
                    "action": "MANUAL_REVIEW",
                    "reason": "Gray zone score (70-79) requires human judgment",
                    "quality_score": quality_score,
                    "reviewer_role": "lead_engineer",
                    "assessment": "below",
                    "issues": evaluation.issues_found,
                    "recommendations": evaluation.recommendations,
                },
            )
        
        else:
            return (
                "ESCALATE",
                {
                    "action": "ESCALATE",
                    "reason": f"Critical quality issue: score {quality_score} < 70",
                    "quality_score": quality_score,
                    "escalation_level": "principal_engineer",
                    "issues": evaluation.issues_found,
                    "recommendations": evaluation.recommendations,
                },
            )
    
    def _record_outcome(self, delegate, handback, feedback):
        """Record task outcome for historical analysis."""
        outcome = {
            "task_id": delegate.task_id,
            "role": delegate.role,
            "model": delegate.model,
            "effort": delegate.effort,
            "quality_baseline": delegate.quality_baseline,
            "quality_achieved": handback.quality_score,
            "cost_budget": delegate.cost_target,
            "cost_actual": handback.cost_actual,
            "outcome": feedback.outcome,
            "quality_assessment": feedback.quality_assessment,
            "cost_assessment": feedback.cost_assessment,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Store by role for historical analysis
        if delegate.role not in self.historical_outcomes:
            self.historical_outcomes[delegate.role] = []
        
        self.historical_outcomes[delegate.role].append(outcome)
        
        logger.info(f"Recorded outcome for {delegate.task_id}: {feedback.outcome}")
    
    def get_events(self, task_id: str) -> List:
        """Get all events for a task."""
        return self.event_publisher.get_events(task_id)
    
    def get_historical_outcomes(self, role: str) -> List[Dict]:
        """Get historical outcomes for a role."""
        return self.historical_outcomes.get(role, [])
