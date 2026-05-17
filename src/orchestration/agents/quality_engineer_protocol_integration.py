"""
Quality Engineer Protocol Integration Module

Extends the Quality Engineer with expanded protocol schema support:
1. Automatic quality scoring based on evaluation results
2. Escalation logic based on quality thresholds
3. Quality dashboard with trend analysis
4. Recommendation generation for improvements
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..protocol.orchestrator_integration import (
    QualityEvaluationEngine,
    FeedbackLoopEngine,
)
from ..protocol.quality_evaluation import QualityEvaluation
from ..protocol.feedback_outcome import FeedbackOutcome

logger = logging.getLogger(__name__)


class QualityEngineerProtocolIntegration:
    """Integrates expanded protocol schemas with Quality Engineer."""
    
    def __init__(self):
        self.evaluations: List[QualityEvaluation] = []
        self.feedback_outcomes: List[FeedbackOutcome] = []
        self.quality_trends: Dict[str, List[Dict]] = defaultdict(list)  # role -> trends
        self.escalations: List[Dict] = []
    
    def evaluate_quality(
        self,
        delegate_dict: Dict,
        handback_dict: Dict,
    ) -> QualityEvaluation:
        """
        Evaluate quality by comparing DELEGATE baseline with HANDBACK results.
        
        This is the automatic quality scoring step.
        
        Args:
            delegate_dict: Original DELEGATE dict
            handback_dict: HANDBACK dict with results
        
        Returns:
            QualityEvaluation with computed quality score and assessment
        """
        from ..protocol.orchestrator_integration import (
            ExpandedDelegateHandler,
            ExpandedHandbackHandler,
        )
        
        # Convert to expanded schemas
        delegate = ExpandedDelegateHandler.from_dict(delegate_dict)
        handback = ExpandedHandbackHandler.from_dict(handback_dict)
        
        # Evaluate quality
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        
        # Store evaluation
        self.evaluations.append(evaluation)
        
        # Track quality trend
        self._track_quality_trend(delegate.role, evaluation)
        
        logger.info(
            f"Quality evaluation for {evaluation.task_id}: "
            f"score={evaluation.quality_score}, "
            f"assessment={evaluation.acceptance_criteria_assessment}"
        )
        
        return evaluation
    
    def check_escalation(
        self,
        evaluation: QualityEvaluation,
        delegate_dict: Dict,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if task should be escalated based on quality evaluation.
        
        Escalation triggers:
        - Quality score < 70
        - Regressions detected > 0
        - Acceptance criteria not met
        - Test coverage < 80%
        - Critical issues found
        
        Args:
            evaluation: QualityEvaluation with results
            delegate_dict: Original DELEGATE dict
        
        Returns:
            Tuple of (should_escalate, escalation_context)
        """
        should_escalate = evaluation.escalation_required
        escalation_context = None
        
        if should_escalate:
            escalation_context = {
                "task_id": evaluation.task_id,
                "reason": evaluation.escalation_reason,
                "quality_score": evaluation.quality_score,
                "quality_baseline": evaluation.quality_baseline,
                "issues": evaluation.issues_found,
                "recommendations": evaluation.recommendations,
                "escalation_level": self._determine_escalation_level(evaluation),
                "timestamp": datetime.now().isoformat(),
                "delegate_role": delegate_dict.get("role"),
                "delegate_model": delegate_dict.get("model"),
                "delegate_effort": delegate_dict.get("effort"),
            }
            
            # Store escalation
            self.escalations.append(escalation_context)
            
            logger.warning(
                f"Escalation required for {evaluation.task_id}: "
                f"{escalation_context['reason']}"
            )
        
        return (should_escalate, escalation_context)
    
    def _determine_escalation_level(self, evaluation: QualityEvaluation) -> str:
        """Determine escalation level based on quality evaluation."""
        if evaluation.quality_score < 60:
            return "principal_engineer"
        elif evaluation.quality_score < 70:
            return "senior_engineer"
        else:
            return "lead_engineer"
    
    def _track_quality_trend(self, role: str, evaluation: QualityEvaluation):
        """Track quality trend for a role."""
        trend_entry = {
            "task_id": evaluation.task_id,
            "quality_score": evaluation.quality_score,
            "quality_baseline": evaluation.quality_baseline,
            "assessment": evaluation.acceptance_criteria_assessment,
            "timestamp": datetime.now().isoformat(),
            "role": role,
        }
        
        self.quality_trends[role].append(trend_entry)
    
    def get_quality_metrics(self, role: str, days: int = 7) -> Dict:
        """
        Get quality metrics for a role over N days.
        
        Args:
            role: Agent role (engineer, senior-engineer, etc.)
            days: Number of days to analyze (default 7)
        
        Returns:
            Dict with quality metrics
        """
        trends = self.quality_trends.get(role, [])
        
        # Filter by date
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        recent_trends = [
            t for t in trends
            if datetime.fromisoformat(t["timestamp"]) >= cutoff
        ]
        
        if not recent_trends:
            return {
                "role": role,
                "days": days,
                "count": 0,
                "avg_quality": 0,
                "min_quality": 0,
                "max_quality": 0,
                "success_rate": 0,
            }
        
        # Compute metrics
        quality_scores = [t["quality_score"] for t in recent_trends]
        baselines = [t["quality_baseline"] for t in recent_trends]
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        min_quality = min(quality_scores)
        max_quality = max(quality_scores)
        
        # Success rate: percentage of tasks with quality >= baseline
        success_count = sum(
            1 for score, baseline in zip(quality_scores, baselines)
            if score >= baseline
        )
        success_rate = success_count / len(quality_scores)
        
        return {
            "role": role,
            "days": days,
            "count": len(recent_trends),
            "avg_quality": avg_quality,
            "min_quality": min_quality,
            "max_quality": max_quality,
            "success_rate": success_rate,
            "trend": self._compute_trend_direction(quality_scores),
        }
    
    def _compute_trend_direction(self, scores: List[int]) -> str:
        """Compute trend direction (improving, stable, declining)."""
        if len(scores) < 2:
            return "stable"
        
        # Compare first half with second half
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / len(scores[:mid]) if mid > 0 else scores[0]
        second_half_avg = sum(scores[mid:]) / len(scores[mid:]) if len(scores) > mid else scores[-1]
        
        diff = second_half_avg - first_half_avg
        if diff > 2:
            return "improving"
        elif diff < -2:
            return "declining"
        else:
            return "stable"
    
    def get_quality_dashboard(self) -> Dict:
        """
        Get quality dashboard with metrics for all roles.
        
        Returns:
            Dict with quality metrics for each role
        """
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "total_evaluations": len(self.evaluations),
            "total_escalations": len(self.escalations),
            "roles": {},
        }
        
        # Get metrics for each role
        for role in self.quality_trends.keys():
            dashboard["roles"][role] = {
                "7_day": self.get_quality_metrics(role, days=7),
                "30_day": self.get_quality_metrics(role, days=30),
            }
        
        # Overall metrics
        if self.evaluations:
            all_scores = [e.quality_score for e in self.evaluations]
            dashboard["overall"] = {
                "avg_quality": sum(all_scores) / len(all_scores),
                "min_quality": min(all_scores),
                "max_quality": max(all_scores),
                "escalation_rate": len(self.escalations) / len(self.evaluations),
            }
        
        return dashboard
    
    def get_escalations(self, role: Optional[str] = None) -> List[Dict]:
        """
        Get escalations, optionally filtered by role.
        
        Args:
            role: Optional role to filter by
        
        Returns:
            List of escalation contexts
        """
        if role:
            return [e for e in self.escalations if e.get("delegate_role") == role]
        return self.escalations
    
    def generate_improvement_recommendations(
        self,
        role: str,
    ) -> List[str]:
        """
        Generate improvement recommendations for a role based on quality trends.
        
        Args:
            role: Agent role
        
        Returns:
            List of recommendations
        """
        metrics = self.get_quality_metrics(role, days=30)
        recommendations = []
        
        # Check average quality
        if metrics["avg_quality"] < 80:
            recommendations.append(
                f"Average quality for {role} is {metrics['avg_quality']:.1f}. "
                "Consider additional training or code review."
            )
        
        # Check success rate
        if metrics["success_rate"] < 0.8:
            recommendations.append(
                f"Success rate for {role} is {metrics['success_rate']:.1%}. "
                "Review failed tasks and identify patterns."
            )
        
        # Check trend
        if metrics["trend"] == "declining":
            recommendations.append(
                f"Quality trend for {role} is declining. "
                "Investigate recent changes or increased complexity."
            )
        
        # Check min quality
        if metrics["min_quality"] < 70:
            recommendations.append(
                f"Minimum quality for {role} is {metrics['min_quality']}. "
                "Implement stricter quality gates."
            )
        
        return recommendations
    
    def generate_escalation_summary(self) -> Dict:
        """
        Generate summary of escalations by level and reason.
        
        Returns:
            Dict with escalation summary
        """
        summary = {
            "total_escalations": len(self.escalations),
            "by_level": defaultdict(int),
            "by_reason": defaultdict(int),
            "by_role": defaultdict(int),
        }
        
        for escalation in self.escalations:
            summary["by_level"][escalation.get("escalation_level", "unknown")] += 1
            summary["by_reason"][escalation.get("reason", "unknown")] += 1
            summary["by_role"][escalation.get("delegate_role", "unknown")] += 1
        
        return dict(summary)
