"""
FeedbackLoop - Track task outcomes, agent performance, and skill effectiveness.

Collects feedback from Quality Engineer HANDBACKs and stores it for use by:
- SmartRouter (historical success rates)
- SelfImprovement (trend analysis)
- ThresholdEnforcer (quality trend monitoring)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TaskOutcome:
    """Record of a single completed task."""
    task_id: str
    agent_role: str
    model: str
    quality_score: float
    status: str                       # complete | failed | escalated | rework
    skills_used: List[str]
    tokens_used: int
    duration_minutes: float
    retry_count: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    feedback_notes: str = ""

    @property
    def success(self) -> bool:
        return self.status in ("complete", "passed")

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AgentFeedbackSummary:
    """Aggregated feedback for a single agent role."""
    agent_role: str
    total_tasks: int = 0
    successful_tasks: int = 0
    total_quality: float = 0.0
    total_tokens: int = 0
    total_retries: int = 0
    skill_quality: Dict[str, List[float]] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        return self.successful_tasks / self.total_tasks if self.total_tasks else 0.0

    @property
    def avg_quality(self) -> float:
        return self.total_quality / self.total_tasks if self.total_tasks else 0.0

    @property
    def avg_tokens(self) -> float:
        return self.total_tokens / self.total_tasks if self.total_tasks else 0.0

    def to_dict(self) -> Dict:
        return {
            "agent_role": self.agent_role,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "success_rate": round(self.success_rate, 3),
            "avg_quality": round(self.avg_quality, 1),
            "avg_tokens": round(self.avg_tokens, 0),
            "total_retries": self.total_retries,
            "skill_quality": {
                k: round(sum(v) / len(v), 1) for k, v in self.skill_quality.items() if v
            },
        }


# ---------------------------------------------------------------------------
# FeedbackStore
# ---------------------------------------------------------------------------

class FeedbackStore:
    """
    Persistent storage for task outcomes.

    Stores outcomes as newline-delimited JSON in a single file.
    Designed for append-only writes and full-scan reads (suitable for
    hundreds of tasks; replace with DB for thousands).
    """

    def __init__(self, store_path: Optional[Path] = None):
        if store_path is None:
            store_path = Path("metrics/feedback_store.jsonl")
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, outcome: TaskOutcome) -> None:
        with open(self.store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(outcome.to_dict()) + "\n")

    def read_all(self) -> List[TaskOutcome]:
        if not self.store_path.exists():
            return []
        outcomes = []
        with open(self.store_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    outcomes.append(TaskOutcome(**d))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Skipping malformed feedback record: %s", e)
        return outcomes

    def read_since(self, since: datetime) -> List[TaskOutcome]:
        return [o for o in self.read_all() if o.timestamp >= since.isoformat()]

    def clear(self) -> None:
        if self.store_path.exists():
            self.store_path.unlink()


# ---------------------------------------------------------------------------
# FeedbackLoop
# ---------------------------------------------------------------------------

class FeedbackLoop:
    """
    Central feedback collection and analysis hub.

    Usage:
        loop = FeedbackLoop()
        loop.record(outcome)
        summary = loop.agent_summary("engineer")
        trends = loop.quality_trend("engineer", days=7)
    """

    def __init__(self, store: Optional[FeedbackStore] = None):
        self.store = store or FeedbackStore()
        self._cache: Optional[List[TaskOutcome]] = None
        self._skill_raw_feedback: Dict[str, List[Dict]] = {}

        # Load persisted skill feedback from disk to resume across sessions
        self._load_skill_feedback_from_disk()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, outcome: TaskOutcome) -> None:
        """Persist a task outcome and invalidate cache."""
        self.store.append(outcome)
        self._cache = None
        logger.debug(
            "Feedback recorded: task=%s agent=%s quality=%.1f status=%s",
            outcome.task_id, outcome.agent_role, outcome.quality_score, outcome.status,
        )

    def record_from_handback(self, handback: Dict, delegate: Dict) -> TaskOutcome:
        """
        Convenience: build a TaskOutcome from HANDBACK + DELEGATE dicts and record it.

        Returns the TaskOutcome that was recorded.
        """
        task_id = handback.get("task_id", "unknown")
        agent_role = delegate.get("role", handback.get("role", "unknown"))
        model = delegate.get("model", handback.get("model", "unknown"))
        quality_score = float(handback.get("quality_score", 0))
        status = handback.get("status", "unknown")
        skills_used = handback.get("skills_used", delegate.get("required_skills", []))
        tokens = handback.get("tokens_used", 0) or (
            handback.get("tokens_in", 0) + handback.get("tokens_out", 0)
        )
        effort_hours = float(handback.get("effort_actual", 0) or 0)
        duration_minutes = effort_hours * 60
        retry_count = handback.get("retry_count", 0)
        notes = handback.get("feedback_notes", "")

        outcome = TaskOutcome(
            task_id=task_id,
            agent_role=agent_role,
            model=model,
            quality_score=quality_score,
            status=status,
            skills_used=skills_used if isinstance(skills_used, list) else [],
            tokens_used=int(tokens),
            duration_minutes=float(duration_minutes),
            retry_count=int(retry_count),
            feedback_notes=str(notes),
        )
        self.record(outcome)

        # Extract and route skill_feedback if present
        skill_feedback = handback.get("skill_feedback", [])
        if skill_feedback:
            # Group items by skill_name
            feedback_by_skill: Dict[str, List[Dict]] = {}
            for item in skill_feedback:
                skill_name = item.get("skill_name")
                if skill_name:
                    feedback_by_skill.setdefault(skill_name, []).append(item)

            # Record each skill's feedback
            for skill_name, items in feedback_by_skill.items():
                self.record_skill_feedback(skill_name, items)

        return outcome

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _outcomes(self) -> List[TaskOutcome]:
        if self._cache is None:
            self._cache = self.store.read_all()
        return self._cache

    def agent_summary(self, agent_role: str) -> AgentFeedbackSummary:
        """Return aggregated feedback for a specific agent role."""
        summary = AgentFeedbackSummary(agent_role=agent_role)
        for o in self._outcomes():
            if o.agent_role != agent_role:
                continue
            summary.total_tasks += 1
            summary.total_quality += o.quality_score
            summary.total_tokens += o.tokens_used
            summary.total_retries += o.retry_count
            if o.success:
                summary.successful_tasks += 1
            for skill in o.skills_used:
                summary.skill_quality.setdefault(skill, []).append(o.quality_score)
        return summary

    def all_agent_summaries(self) -> Dict[str, AgentFeedbackSummary]:
        roles = {o.agent_role for o in self._outcomes()}
        return {role: self.agent_summary(role) for role in roles}

    def quality_trend(self, agent_role: str, days: int = 7) -> List[Tuple[str, float]]:
        """
        Return daily average quality scores for the last `days` days.

        Returns list of (date_str, avg_quality) tuples sorted ascending.
        """
        since = datetime.now() - timedelta(days=days)
        daily: Dict[str, List[float]] = {}
        for o in self._outcomes():
            if o.agent_role != agent_role:
                continue
            if o.timestamp < since.isoformat():
                continue
            date = o.timestamp[:10]
            daily.setdefault(date, []).append(o.quality_score)

        return [
            (date, round(sum(scores) / len(scores), 1))
            for date, scores in sorted(daily.items())
        ]

    def skill_effectiveness(self) -> Dict[str, Dict]:
        """Return quality stats grouped by skill."""
        skill_data: Dict[str, List[float]] = {}
        for o in self._outcomes():
            for skill in o.skills_used:
                skill_data.setdefault(skill, []).append(o.quality_score)

        return {
            skill: {
                "count": len(scores),
                "avg_quality": round(sum(scores) / len(scores), 1),
                "min_quality": min(scores),
                "max_quality": max(scores),
            }
            for skill, scores in skill_data.items()
        }

    def recent_outcomes(self, limit: int = 20) -> List[TaskOutcome]:
        outcomes = self._outcomes()
        return sorted(outcomes, key=lambda o: o.timestamp, reverse=True)[:limit]

    def overall_stats(self) -> Dict:
        outcomes = self._outcomes()
        if not outcomes:
            return {"total_tasks": 0}
        total = len(outcomes)
        successful = sum(1 for o in outcomes if o.success)
        avg_quality = sum(o.quality_score for o in outcomes) / total
        avg_tokens = sum(o.tokens_used for o in outcomes) / total
        return {
            "total_tasks": total,
            "successful_tasks": successful,
            "success_rate": round(successful / total, 3),
            "avg_quality": round(avg_quality, 1),
            "avg_tokens": round(avg_tokens, 0),
        }

    # ------------------------------------------------------------------
    # Skill Feedback Recording
    # ------------------------------------------------------------------

    def _load_skill_feedback_from_disk(self) -> None:
        """Load persisted skill feedback from artifacts/metrics/skill-feedback/."""
        feedback_dir = Path("artifacts/metrics/skill-feedback")
        if not feedback_dir.exists():
            logger.debug(f"Skill feedback directory not found: {feedback_dir}")
            return

        try:
            for jsonl_file in feedback_dir.glob("*.jsonl"):
                skill_name = jsonl_file.stem
                with jsonl_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                            self._skill_raw_feedback.setdefault(skill_name, []).append(item)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Skipping malformed skill feedback line in {jsonl_file}: {e}")
            logger.debug(f"Loaded skill feedback from disk: {len(self._skill_raw_feedback)} skills")
        except Exception as e:
            logger.warning(f"Error loading skill feedback from disk: {e}")

    def record_skill_feedback(self, skill_name: str, items: List[Dict]) -> None:
        """
        Record skill feedback items and persist to disk.

        Args:
            skill_name: Kebab-case skill name
            items: List of feedback dictionaries
        """
        if not items:
            return

        # Append to in-memory accumulator
        self._skill_raw_feedback.setdefault(skill_name, []).extend(items)

        # Persist to JSONL file
        feedback_dir = Path("artifacts/metrics/skill-feedback")
        feedback_dir.mkdir(parents=True, exist_ok=True)

        feedback_file = feedback_dir / f"{skill_name}.jsonl"
        try:
            with feedback_file.open("a", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item) + "\n")
            logger.debug(
                f"Recorded {len(items)} skill feedback item(s) for {skill_name}"
            )
        except Exception as e:
            logger.error(f"Failed to persist skill feedback for {skill_name}: {e}")

    def get_accumulated_count(self, skill_name: str) -> int:
        """
        Get the accumulated count of feedback items for a skill.

        Args:
            skill_name: Kebab-case skill name

        Returns:
            Number of accumulated feedback items
        """
        return len(self._skill_raw_feedback.get(skill_name, []))

    def get_top_feedback_candidates(self, threshold: int = 3) -> List[Tuple[str, List[Dict]]]:
        """
        Get all skills with accumulated feedback count >= threshold.

        Args:
            threshold: Minimum feedback count to return (default 3)

        Returns:
            List of (skill_name, feedback_items) tuples for skills meeting threshold
        """
        candidates = []
        for skill_name, items in self._skill_raw_feedback.items():
            if len(items) >= threshold:
                candidates.append((skill_name, items))
        return candidates
