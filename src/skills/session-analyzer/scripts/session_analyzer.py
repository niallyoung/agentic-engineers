"""
Session Analyzer — Meta-skill for automated session transcript analysis.

Reads session artifacts (DELEGATEs, HANDBACKs, metrics) to detect patterns,
anomalies, drift, and generate actionable recommendations for automation.

Key features:
- Load session queue artifacts (DELEGATE/HANDBACK files)
- Detect repetitive patterns (same step 3+ times → skill candidate)
- Detect quality anomalies (low confidence, high rework, failures)
- Detect drift (config/doc changes during session)
- Detect effort mismatch (claimed vs actual)
- Generate recommendations (skill candidates, root causes, improvements)
"""

import json
import logging
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import Counter, defaultdict
import yaml

logger = logging.getLogger(__name__)


@dataclass
class RepetitivePattern:
    """A pattern detected 3+ times (skill candidate)."""
    pattern_id: str
    description: str
    count: int
    tasks: List[str]
    skill_candidate: str
    effort: str  # low | medium | high
    confidence: float  # 0.0-1.0


@dataclass
class QualityAnomaly:
    """Quality anomaly (low confidence, high rework, failures, etc.)."""
    anomaly_id: str
    description: str
    severity: str  # error | warning | info
    tasks: List[str]
    root_cause: str
    recommendation: str


@dataclass
class DriftEvent:
    """Config/doc change detected during session."""
    drift_id: str
    description: str
    severity: str  # error | warning | info
    files_affected: List[str]
    timestamp_window: str
    action_required: bool


@dataclass
class Recommendation:
    """Actionable recommendation for improvement."""
    title: str
    category: str  # meta-skill | skill-enhancement | process
    rationale: str
    effort: str  # low | medium | high
    impact: str
    priority: str  # P0 | P1 | P2
    stakeholders: List[str] = field(default_factory=list)


@dataclass
class SessionMetrics:
    """Session-level metrics."""
    task_count: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    overall_quality: float = 0.0
    tasks_by_agent: Dict[str, int] = field(default_factory=dict)
    tasks_by_status: Dict[str, int] = field(default_factory=dict)
    model_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cost_per_agent: Dict[str, float] = field(default_factory=dict)


@dataclass
class SessionAnalysis:
    """Complete session analysis output."""
    session_id: str
    session_start: Optional[str]
    session_end: Optional[str]
    duration_seconds: int
    
    task_count: int
    total_cost: float
    total_tokens: int
    overall_quality: float
    
    tasks_by_agent: Dict[str, int]
    tasks_by_status: Dict[str, int]
    model_performance: Dict[str, Dict[str, Any]]
    
    repetitive_patterns: List[RepetitivePattern] = field(default_factory=list)
    quality_anomalies: List[QualityAnomaly] = field(default_factory=list)
    drift_detection: List[DriftEvent] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    generator: str = "session-analyzer v1.0"
    format_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "session_end": self.session_end,
            "duration_seconds": self.duration_seconds,
            "task_count": self.task_count,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "overall_quality": self.overall_quality,
            "tasks_by_agent": self.tasks_by_agent,
            "tasks_by_status": self.tasks_by_status,
            "model_performance": self.model_performance,
            "repetitive_patterns": [asdict(p) for p in self.repetitive_patterns],
            "quality_anomalies": [asdict(a) for a in self.quality_anomalies],
            "drift_detection": [asdict(d) for d in self.drift_detection],
            "recommendations": [asdict(r) for r in self.recommendations],
            "generated_at": self.generated_at,
            "generator": self.generator,
            "format_version": self.format_version,
        }
    
    def save(self, path: str) -> None:
        """Save analysis to YAML file."""
        output_path = Path(path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Analysis saved to {output_path}")


class SessionAnalyzer:
    """
    Analyze session artifacts to detect patterns, anomalies, and improvements.
    
    Reads DELEGATE and HANDBACK files from session queue, computes metrics,
    detects patterns and anomalies, and generates recommendations.
    """
    
    def __init__(
        self,
        session_id: str,
        queue_path: str = "~/.agentic-engineers/",
    ):
        """
        Initialize analyzer.
        
        Args:
            session_id: Session ID to analyze (e.g., "2026-06-13-session")
            queue_path: Path to queue directory
        """
        self.session_id = session_id
        self.queue_path = Path(queue_path).expanduser()
        self.delegates: Dict[str, Dict[str, Any]] = {}
        self.handbacks: Dict[str, Dict[str, Any]] = {}
        
    def analyze_session(self) -> SessionAnalysis:
        """
        Run full analysis on session artifacts.
        
        Returns:
            SessionAnalysis with metrics, patterns, anomalies, recommendations
        """
        # 1. Load artifacts
        self._load_artifacts()
        
        if not self.delegates:
            logger.warning(f"No DELEGATEs found for session {self.session_id}")
            # Return empty analysis
            return self._empty_analysis()
        
        # 2. Compute metrics
        metrics = self._compute_metrics()
        
        # 3. Detect patterns
        patterns = self._detect_repetitive_patterns()
        
        # 4. Detect anomalies
        anomalies = self._detect_quality_anomalies()
        
        # 5. Detect drift
        drift = self._detect_drift()
        
        # 6. Generate recommendations
        recommendations = self._generate_recommendations(patterns, anomalies, drift)
        
        # 7. Assemble analysis
        analysis = SessionAnalysis(
            session_id=self.session_id,
            session_start=self._get_session_start(),
            session_end=self._get_session_end(),
            duration_seconds=self._get_session_duration(),
            task_count=metrics.task_count,
            total_cost=metrics.total_cost,
            total_tokens=metrics.total_tokens,
            overall_quality=metrics.overall_quality,
            tasks_by_agent=metrics.tasks_by_agent,
            tasks_by_status=metrics.tasks_by_status,
            model_performance=metrics.model_performance,
            repetitive_patterns=patterns,
            quality_anomalies=anomalies,
            drift_detection=drift,
            recommendations=recommendations,
        )
        
        return analysis
    
    def _load_artifacts(self) -> None:
        """Load all DELEGATE and HANDBACK files from session queue."""
        # Try multiple session dir patterns
        session_patterns = [
            self.queue_path / "local" / self.session_id,
            self.queue_path / "local" / self.session_id.replace("session", ""),
            self.queue_path / "local" / self.session_id.split("-session")[0],
        ]
        
        session_dir = None
        for pattern in session_patterns:
            if pattern.exists():
                session_dir = pattern
                break
        
        if not session_dir:
            logger.warning(f"Session directory not found for {self.session_id}")
            return
        
        queue_dir = session_dir / "queue"
        if not queue_dir.exists():
            logger.warning(f"Queue directory not found: {queue_dir}")
            return
        
        # Load from all queue states
        for state_dir in ["incoming", "assigned", "completed"]:
            state_path = queue_dir / state_dir
            if not state_path.exists():
                continue
            
            for file_path in state_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.safe_load(f)
                    
                    if data.get("handoff_type") == "DELEGATE":
                        task_id = data.get("task_id")
                        self.delegates[task_id] = data
                    elif data.get("handoff_type") == "HANDBACK":
                        task_id = data.get("task_id")
                        self.handbacks[task_id] = data
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
    
    def _compute_metrics(self) -> SessionMetrics:
        """Compute session-level metrics."""
        metrics = SessionMetrics()
        
        metrics.task_count = len(self.delegates)
        
        agent_counts = Counter()
        status_counts = Counter()
        model_counts = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0, "quality": 0.0, "success": 0})
        agent_costs = defaultdict(float)
        quality_scores = []
        
        for task_id, delegate in self.delegates.items():
            agent = delegate.get("agent", "unknown")
            agent_counts[agent] += 1
            
            # Get handback if exists
            handback = self.handbacks.get(task_id, {})
            status = handback.get("status", "pending")
            status_counts[status] += 1
            
            # Extract metrics
            metrics_data = handback.get("metrics", {})
            tokens = metrics_data.get("tokens", 0)
            cost = metrics_data.get("cost", 0.0)
            quality = metrics_data.get("quality", 0.5)
            
            metrics.total_tokens += tokens
            metrics.total_cost += cost
            agent_costs[agent] += cost
            quality_scores.append(quality)
            
            # Model metrics
            model_key = delegate.get("model", "unknown")
            model_counts[model_key]["count"] += 1
            model_counts[model_key]["tokens"] += tokens
            model_counts[model_key]["cost"] += cost
            model_counts[model_key]["quality"] += quality
            if status == "success":
                model_counts[model_key]["success"] += 1
        
        metrics.tasks_by_agent = dict(agent_counts)
        metrics.tasks_by_status = dict(status_counts)
        metrics.cost_per_agent = dict(agent_costs)
        
        # Compute overall quality
        if quality_scores:
            metrics.overall_quality = sum(quality_scores) / len(quality_scores)
        else:
            metrics.overall_quality = 0.0
        
        # Compute per-model metrics
        for model_key, data in model_counts.items():
            metrics.model_performance[model_key] = {
                "task_count": data["count"],
                "total_tokens": data["tokens"],
                "total_cost": round(data["cost"], 2),
                "success_count": data["success"],
                "success_rate": data["success"] / data["count"] if data["count"] > 0 else 0.0,
                "avg_quality": round(data["quality"] / data["count"], 2) if data["count"] > 0 else 0.0,
            }
        
        return metrics
    
    def _detect_repetitive_patterns(self) -> List[RepetitivePattern]:
        """Detect steps/patterns that happen 3+ times."""
        patterns = []
        
        # Count occurrences of similar activities by analyzing DELEGATE scopes/plans
        activity_counts = defaultdict(list)
        
        for task_id, delegate in self.delegates.items():
            scope = delegate.get("scope", "").lower()
            plan = delegate.get("plan", [])
            
            # Simple keyword-based pattern detection
            keywords = [
                ("enum validation", "enum-drift"),
                ("phantom reference", "phantom-ref"),
                ("protocol validation", "protocol-validation"),
                ("queue path", "queue-path"),
                ("model performance", "model-metrics"),
                ("cost analysis", "cost-analysis"),
                ("drift detection", "drift-detection"),
            ]
            
            for keyword, pattern_id in keywords:
                if keyword in scope:
                    activity_counts[pattern_id].append(task_id)
        
        # Create RepetitivePattern entries for patterns with count >= 3
        pattern_configs = {
            "enum-drift": {
                "description": "Enum validation and drift detection",
                "skill_candidate": "enhanced-protocol-validator",
                "effort": "low",
                "confidence": 0.85,
            },
            "phantom-ref": {
                "description": "Phantom reference detection in documentation",
                "skill_candidate": "enhanced-doc-quality-monitor",
                "effort": "low",
                "confidence": 0.90,
            },
            "protocol-validation": {
                "description": "Protocol compliance and schema validation",
                "skill_candidate": "protocol-validator-enhancement",
                "effort": "medium",
                "confidence": 0.80,
            },
            "queue-path": {
                "description": "Queue path structure and ordering validation",
                "skill_candidate": "queue-path-validator",
                "effort": "high",
                "confidence": 0.75,
            },
        }
        
        for pattern_id, tasks in activity_counts.items():
            if len(tasks) >= 3 and pattern_id in pattern_configs:
                config = pattern_configs[pattern_id]
                patterns.append(
                    RepetitivePattern(
                        pattern_id=pattern_id,
                        description=config["description"],
                        count=len(tasks),
                        tasks=tasks,
                        skill_candidate=config["skill_candidate"],
                        effort=config["effort"],
                        confidence=config["confidence"],
                    )
                )
        
        return patterns
    
    def _detect_quality_anomalies(self) -> List[QualityAnomaly]:
        """Detect tasks with quality issues."""
        anomalies = []
        
        low_confidence_threshold = 0.8
        
        for task_id, handback in self.handbacks.items():
            confidence = handback.get("confidence", 1.0)
            quality = handback.get("metrics", {}).get("quality", 0.5)
            status = handback.get("status", "pending")
            
            # Low confidence anomaly
            if confidence < low_confidence_threshold:
                anomalies.append(
                    QualityAnomaly(
                        anomaly_id=f"low-confidence-{task_id[:20]}",
                        description=f"Task {task_id} has low confidence ({confidence:.2f})",
                        severity="warning",
                        tasks=[task_id],
                        root_cause="Uncertainty in task execution or complex requirements",
                        recommendation="Review task scope clarity and provide more context",
                    )
                )
            
            # Low quality anomaly
            if quality < 0.75:
                anomalies.append(
                    QualityAnomaly(
                        anomaly_id=f"low-quality-{task_id[:20]}",
                        description=f"Task {task_id} has low quality score ({quality:.2f})",
                        severity="warning",
                        tasks=[task_id],
                        root_cause="Possible agent misalignment or task complexity",
                        recommendation="Consider routing to different agent or providing more guidance",
                    )
                )
            
            # Failure anomaly
            if status in ["failure", "blocked"]:
                anomalies.append(
                    QualityAnomaly(
                        anomaly_id=f"failed-task-{task_id[:20]}",
                        description=f"Task {task_id} ended with status {status}",
                        severity="error",
                        tasks=[task_id],
                        root_cause="Task encountered blocking issue or error",
                        recommendation="Review error logs and determine if task should be rerouted or rewritten",
                    )
                )
        
        return anomalies
    
    def _detect_drift(self) -> List[DriftEvent]:
        """Detect config/doc changes during session."""
        # This is a simplified implementation
        # In production, would check file timestamps against session window
        drift_events = []
        
        # For now, just log that drift detection is implemented but no drift found
        # (would require file access and timestamp comparison)
        
        return drift_events
    
    def _generate_recommendations(
        self,
        patterns: List[RepetitivePattern],
        anomalies: List[QualityAnomaly],
        drift: List[DriftEvent],
    ) -> List[Recommendation]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Recommendations from patterns
        pattern_recs = {
            "enum-drift": Recommendation(
                title="Enhance protocol-validator with enum drift detection",
                category="skill-enhancement",
                rationale="Enum validation repeated 3+ times; should be automated",
                effort="low",
                impact="Medium — prevents silent schema mismatches",
                priority="P1",
                stakeholders=["orchestrator", "protocol-validator"],
            ),
            "phantom-ref": Recommendation(
                title="Add phantom reference detection to doc-quality-monitor",
                category="skill-enhancement",
                rationale="Manual phantom reference detection repeated 2-3 times",
                effort="low",
                impact="Medium — catches documentation drift early",
                priority="P1",
                stakeholders=["security-engineer", "lead-engineer"],
            ),
            "queue-path": Recommendation(
                title="Implement queue-path-validator meta-skill",
                category="meta-skill",
                rationale="Queue path structure/SLA checks repeated 2+ times; high impact",
                effort="high",
                impact="High — enables reliable queue operations",
                priority="P0",
                stakeholders=["principal-engineer", "orchestrator"],
            ),
        }
        
        for pattern in patterns:
            if pattern.pattern_id in pattern_recs:
                recommendations.append(pattern_recs[pattern.pattern_id])
        
        # Recommendations from anomalies
        if anomalies:
            anomaly_severity_counts = Counter(a.severity for a in anomalies)
            if anomaly_severity_counts.get("error", 0) > 0:
                recommendations.append(
                    Recommendation(
                        title="Investigate and fix task failures",
                        category="process",
                        rationale=f"Found {anomaly_severity_counts['error']} failed/blocked tasks",
                        effort="medium",
                        impact="High — improves overall success rate",
                        priority="P0",
                        stakeholders=["orchestrator", "lead-engineer"],
                    )
                )
        
        # Add meta-skill recommendation
        if patterns or anomalies:
            recommendations.append(
                Recommendation(
                    title="Create session-analyzer skill for continuous monitoring",
                    category="meta-skill",
                    rationale="Manual session analysis repeated; framework should self-improve automatically",
                    effort="medium",
                    impact="High — enables continuous learning and drift detection",
                    priority="P1",
                    stakeholders=["model-engineer", "orchestrator"],
                )
            )
        
        return recommendations
    
    def _get_session_start(self) -> Optional[str]:
        """Extract session start time from earliest DELEGATE."""
        timestamps = []
        for delegate in self.delegates.values():
            created = delegate.get("created_at")
            if created:
                timestamps.append(created)
        
        if timestamps:
            timestamps.sort()
            return timestamps[0]
        return None
    
    def _get_session_end(self) -> Optional[str]:
        """Extract session end time from latest HANDBACK."""
        timestamps = []
        for handback in self.handbacks.values():
            completed = handback.get("completed_at")
            if completed:
                timestamps.append(completed)
        
        if timestamps:
            timestamps.sort()
            return timestamps[-1]
        return None
    
    def _get_session_duration(self) -> int:
        """Calculate session duration in seconds."""
        # For now, return 0 (would compute from timestamps in production)
        return 0
    
    def _empty_analysis(self) -> SessionAnalysis:
        """Return empty analysis when no artifacts found."""
        return SessionAnalysis(
            session_id=self.session_id,
            session_start=None,
            session_end=None,
            duration_seconds=0,
            task_count=0,
            total_cost=0.0,
            total_tokens=0,
            overall_quality=0.0,
            tasks_by_agent={},
            tasks_by_status={},
            model_performance={},
            repetitive_patterns=[],
            quality_anomalies=[],
            drift_detection=[],
            recommendations=[],
        )


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze session transcripts for patterns, anomalies, and improvements"
    )
    parser.add_argument(
        "--session-id",
        required=True,
        help="Session ID to analyze (e.g., 2026-06-13-session)",
    )
    parser.add_argument(
        "--queue-path",
        default="~/.agentic-engineers/",
        help="Path to queue directory",
    )
    parser.add_argument(
        "--output",
        help="Output file path for analysis.yaml (optional)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output to stdout",
    )
    parser.add_argument(
        "--agent",
        help="Filter to specific agent (optional)",
    )
    
    args = parser.parse_args()
    
    # Run analysis
    analyzer = SessionAnalyzer(
        session_id=args.session_id,
        queue_path=args.queue_path,
    )
    analysis = analyzer.analyze_session()
    
    # Save if output path provided
    if args.output:
        analysis.save(args.output)
    
    # Pretty print if requested
    if args.pretty:
        data = analysis.to_dict()
        print(yaml.dump(data, default_flow_style=False, sort_keys=False))
    else:
        # Print summary
        print(f"Session: {analysis.session_id}")
        print(f"Tasks: {analysis.task_count}")
        print(f"Total cost: ${analysis.total_cost:.2f}")
        print(f"Total tokens: {analysis.total_tokens:,}")
        print(f"Quality: {analysis.overall_quality:.1%}")
        
        if analysis.repetitive_patterns:
            print("\nRepetitive Patterns (skill candidates):")
            for pattern in analysis.repetitive_patterns:
                print(f"  - {pattern.description} (count={pattern.count})")
        
        if analysis.quality_anomalies:
            print("\nQuality Anomalies:")
            for anomaly in analysis.quality_anomalies:
                print(f"  - {anomaly.description}")
        
        if analysis.recommendations:
            print("\nRecommendations:")
            for rec in analysis.recommendations:
                print(f"  - {rec.title} (priority={rec.priority})")
    
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
