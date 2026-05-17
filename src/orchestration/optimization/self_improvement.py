"""
SelfImprovement - Analyze feedback trends and generate routing improvement recommendations.

Consumes data from FeedbackLoop and ThresholdEnforcer to:
- Identify underperforming agents/skills
- Recommend routing changes
- Generate improvement reports
- Track improvement metrics over time
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ImprovementRecommendation:
    """A single actionable improvement recommendation."""
    category: str          # routing | skill | model | threshold | process
    priority: str          # HIGH | MEDIUM | LOW
    title: str
    description: str
    affected_agents: List[str]
    expected_quality_gain: float   # estimated points improvement
    evidence: Dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "affected_agents": self.affected_agents,
            "expected_quality_gain": self.expected_quality_gain,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class ImprovementReport:
    """Full improvement analysis report."""
    generated_at: str
    analysis_period_days: int
    total_tasks_analyzed: int
    recommendations: List[ImprovementRecommendation]
    agent_rankings: List[Dict]         # agents ranked by performance
    skill_effectiveness: Dict[str, Dict]
    quality_trends: Dict[str, List]
    summary: str

    def to_dict(self) -> Dict:
        return {
            "generated_at": self.generated_at,
            "analysis_period_days": self.analysis_period_days,
            "total_tasks_analyzed": self.total_tasks_analyzed,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "agent_rankings": self.agent_rankings,
            "skill_effectiveness": self.skill_effectiveness,
            "quality_trends": self.quality_trends,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# SelfImprovement
# ---------------------------------------------------------------------------

class SelfImprovement:
    """
    Analyze feedback trends and generate routing improvement recommendations.

    Designed to be called periodically (e.g., daily) to produce an
    ImprovementReport that the Orchestrator can act on.
    """

    # Thresholds for generating recommendations
    LOW_SUCCESS_RATE_THRESHOLD = 0.70
    LOW_QUALITY_THRESHOLD = 75.0
    HIGH_RETRY_RATE_THRESHOLD = 0.30
    SKILL_LOW_QUALITY_THRESHOLD = 70.0

    def __init__(self):
        self._improvement_history: List[ImprovementReport] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        agent_summaries: Dict,          # from FeedbackLoop.all_agent_summaries()
        skill_effectiveness: Dict,      # from FeedbackLoop.skill_effectiveness()
        quality_trends: Dict,           # {agent_role: [(date, avg_quality), ...]}
        degradation_alerts: List,       # from ThresholdEnforcer.all_alerts()
        analysis_period_days: int = 7,
    ) -> ImprovementReport:
        """
        Analyze feedback data and produce an ImprovementReport.

        Args:
            agent_summaries: Dict of AgentFeedbackSummary objects (or dicts).
            skill_effectiveness: Skill quality stats dict.
            quality_trends: Quality trend data per agent.
            degradation_alerts: List of DegradationAlert objects.
            analysis_period_days: Window of analysis.

        Returns:
            ImprovementReport with prioritized recommendations.
        """
        recommendations: List[ImprovementRecommendation] = []
        total_tasks = sum(
            s.get("total_tasks", 0) if isinstance(s, dict) else s.total_tasks
            for s in agent_summaries.values()
        )

        # Analyze each agent
        for role, summary in agent_summaries.items():
            recs = self._analyze_agent(role, summary, quality_trends.get(role, []))
            recommendations.extend(recs)

        # Analyze skill effectiveness
        skill_recs = self._analyze_skills(skill_effectiveness)
        recommendations.extend(skill_recs)

        # Analyze degradation alerts
        for alert in degradation_alerts:
            alert_dict = alert.to_dict() if hasattr(alert, "to_dict") else alert
            rec = self._alert_to_recommendation(alert_dict)
            if rec:
                recommendations.append(rec)

        # Sort by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 3))

        # Build agent rankings
        rankings = self._rank_agents(agent_summaries)

        # Build summary
        summary_text = self._build_summary(recommendations, total_tasks)

        report = ImprovementReport(
            generated_at=datetime.now().isoformat(),
            analysis_period_days=analysis_period_days,
            total_tasks_analyzed=total_tasks,
            recommendations=recommendations,
            agent_rankings=rankings,
            skill_effectiveness=skill_effectiveness,
            quality_trends={
                role: [(d, q) for d, q in trend]
                for role, trend in quality_trends.items()
            },
            summary=summary_text,
        )

        self._improvement_history.append(report)
        logger.info(
            "SelfImprovement report: %d recommendations for %d tasks",
            len(recommendations), total_tasks,
        )
        return report

    def latest_report(self) -> Optional[ImprovementReport]:
        return self._improvement_history[-1] if self._improvement_history else None

    def all_reports(self) -> List[ImprovementReport]:
        return list(self._improvement_history)

    def top_recommendations(self, n: int = 5) -> List[ImprovementRecommendation]:
        report = self.latest_report()
        if not report:
            return []
        return report.recommendations[:n]

    # ------------------------------------------------------------------
    # Internal analysis
    # ------------------------------------------------------------------

    def _get_summary_attr(self, summary, attr: str, default=0):
        """Get attribute from summary dict or object."""
        if isinstance(summary, dict):
            return summary.get(attr, default)
        return getattr(summary, attr, default)

    def _analyze_agent(
        self,
        role: str,
        summary,
        trend: List[Tuple],
    ) -> List[ImprovementRecommendation]:
        recs = []
        total_tasks = self._get_summary_attr(summary, "total_tasks", 0)
        if total_tasks < 3:
            return recs  # not enough data

        success_rate = self._get_summary_attr(summary, "success_rate", 1.0)
        avg_quality = self._get_summary_attr(summary, "avg_quality", 100.0)
        total_retries = self._get_summary_attr(summary, "total_retries", 0)
        retry_rate = total_retries / total_tasks if total_tasks else 0

        # Low success rate
        if success_rate < self.LOW_SUCCESS_RATE_THRESHOLD:
            recs.append(ImprovementRecommendation(
                category="routing",
                priority="HIGH",
                title=f"Low success rate for {role}",
                description=(
                    f"{role} has success rate {success_rate:.1%} < "
                    f"{self.LOW_SUCCESS_RATE_THRESHOLD:.0%}. "
                    "Consider routing complex tasks to a higher-tier agent."
                ),
                affected_agents=[role],
                expected_quality_gain=10.0,
                evidence={
                    "success_rate": success_rate,
                    "total_tasks": total_tasks,
                    "threshold": self.LOW_SUCCESS_RATE_THRESHOLD,
                },
            ))

        # Low average quality
        if avg_quality < self.LOW_QUALITY_THRESHOLD:
            recs.append(ImprovementRecommendation(
                category="routing",
                priority="HIGH" if avg_quality < 65 else "MEDIUM",
                title=f"Low average quality for {role}",
                description=(
                    f"{role} avg quality {avg_quality:.1f} < {self.LOW_QUALITY_THRESHOLD}. "
                    "Review task complexity assignments or upgrade model tier."
                ),
                affected_agents=[role],
                expected_quality_gain=self.LOW_QUALITY_THRESHOLD - avg_quality,
                evidence={
                    "avg_quality": avg_quality,
                    "threshold": self.LOW_QUALITY_THRESHOLD,
                },
            ))

        # High retry rate
        if retry_rate > self.HIGH_RETRY_RATE_THRESHOLD:
            recs.append(ImprovementRecommendation(
                category="process",
                priority="MEDIUM",
                title=f"High retry rate for {role}",
                description=(
                    f"{role} retry rate {retry_rate:.1%} > "
                    f"{self.HIGH_RETRY_RATE_THRESHOLD:.0%}. "
                    "Tasks may be under-specified or routed to wrong agent."
                ),
                affected_agents=[role],
                expected_quality_gain=5.0,
                evidence={
                    "retry_rate": retry_rate,
                    "total_retries": total_retries,
                    "total_tasks": total_tasks,
                },
            ))

        # Negative quality trend
        if len(trend) >= 3:
            recent_scores = [q for _, q in trend[-3:]]
            if len(recent_scores) >= 2:
                trend_delta = recent_scores[-1] - recent_scores[0]
                if trend_delta < -5:
                    recs.append(ImprovementRecommendation(
                        category="routing",
                        priority="MEDIUM",
                        title=f"Declining quality trend for {role}",
                        description=(
                            f"{role} quality dropped {abs(trend_delta):.1f} points "
                            "over recent tasks. Investigate task complexity changes."
                        ),
                        affected_agents=[role],
                        expected_quality_gain=abs(trend_delta) * 0.5,
                        evidence={
                            "trend_delta": trend_delta,
                            "recent_scores": recent_scores,
                        },
                    ))

        return recs

    def _analyze_skills(self, skill_effectiveness: Dict) -> List[ImprovementRecommendation]:
        recs = []
        for skill, stats in skill_effectiveness.items():
            avg_q = stats.get("avg_quality", 100)
            count = stats.get("count", 0)
            if count < 3:
                continue
            if avg_q < self.SKILL_LOW_QUALITY_THRESHOLD:
                recs.append(ImprovementRecommendation(
                    category="skill",
                    priority="MEDIUM",
                    title=f"Skill '{skill}' underperforming",
                    description=(
                        f"Tasks using skill '{skill}' average {avg_q:.1f} quality "
                        f"({count} tasks). Review skill routing affinity."
                    ),
                    affected_agents=[],
                    expected_quality_gain=self.SKILL_LOW_QUALITY_THRESHOLD - avg_q,
                    evidence=stats,
                ))
        return recs

    def _alert_to_recommendation(self, alert: Dict) -> Optional[ImprovementRecommendation]:
        drop = alert.get("drop", 0)
        if drop < 5:
            return None
        return ImprovementRecommendation(
            category="routing",
            priority="HIGH" if alert.get("alert_level") == "CRITICAL" else "MEDIUM",
            title=f"Quality degradation: {alert.get('agent_role')}/{alert.get('task_type')}",
            description=(
                f"Quality dropped {drop:.1f} points "
                f"({alert.get('previous_avg')} → {alert.get('current_avg')}). "
                "Immediate routing review recommended."
            ),
            affected_agents=[alert.get("agent_role", "unknown")],
            expected_quality_gain=drop * 0.7,
            evidence=alert,
        )

    def _rank_agents(self, agent_summaries: Dict) -> List[Dict]:
        rankings = []
        for role, summary in agent_summaries.items():
            total_tasks = self._get_summary_attr(summary, "total_tasks", 0)
            if total_tasks == 0:
                continue
            avg_quality = self._get_summary_attr(summary, "avg_quality", 0.0)
            success_rate = self._get_summary_attr(summary, "success_rate", 0.0)
            # Composite score: 60% quality + 40% success rate (scaled to 100)
            composite = (avg_quality * 0.6) + (success_rate * 100 * 0.4)
            rankings.append({
                "agent_role": role,
                "composite_score": round(composite, 1),
                "avg_quality": round(avg_quality, 1),
                "success_rate": round(success_rate, 3),
                "total_tasks": total_tasks,
            })
        return sorted(rankings, key=lambda r: r["composite_score"], reverse=True)

    def _build_summary(self, recommendations: List[ImprovementRecommendation], total_tasks: int) -> str:
        high = sum(1 for r in recommendations if r.priority == "HIGH")
        medium = sum(1 for r in recommendations if r.priority == "MEDIUM")
        low = sum(1 for r in recommendations if r.priority == "LOW")
        return (
            f"Analyzed {total_tasks} tasks. "
            f"Found {len(recommendations)} recommendations: "
            f"{high} HIGH, {medium} MEDIUM, {low} LOW priority."
        )
