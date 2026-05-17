"""
SmartRouter - Intelligent task routing with skill integration and historical feedback.

Extends basic routing with:
- Task complexity analysis (TRIVIAL → CRITICAL)
- Skill-based routing (match task requirements to agent skills)
- Historical success rate tracking
- Confidence scoring per routing decision
- Multi-signal routing decisions
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & constants
# ---------------------------------------------------------------------------

class TaskComplexity(Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RoutingSignal(Enum):
    """Signals that influence routing decisions."""
    EXPLICIT_ROLE = "explicit_role"
    SECURITY_SCOPED = "security_scoped"
    CROSS_SERVICE = "cross_service"
    PRECOMMIT_GATE = "precommit_gate"
    CODE_REVIEW = "code_review"
    SKILL_MATCH = "skill_match"
    COMPLEXITY = "complexity"
    HAS_PLAN = "has_plan"
    HISTORICAL_SUCCESS = "historical_success"
    DEFAULT = "default"


# Skill → agent affinity map
SKILL_AGENT_AFFINITY: Dict[str, str] = {
    "security": "security_engineer",
    "cryptography": "security_engineer",
    "authentication": "security_engineer",
    "authorization": "security_engineer",
    "vulnerability": "security_engineer",
    "architecture": "principal_engineer",
    "cross_service": "principal_engineer",
    "distributed": "principal_engineer",
    "infrastructure": "principal_engineer",
    "code_review": "lead_engineer",
    "refactoring": "lead_engineer",
    "design_review": "lead_engineer",
    "quality": "quality_engineer",
    "testing": "quality_engineer",
    "validation": "quality_engineer",
    "metrics": "model_engineer",
    "cost_optimization": "model_engineer",
    "model_selection": "model_engineer",
    "planning": "senior_engineer",
    "debugging": "senior_engineer",
    "root_cause": "senior_engineer",
    "implementation": "engineer",
    "feature": "engineer",
    "bugfix": "engineer",
}

# Complexity → preferred agent (when no other signal fires)
COMPLEXITY_AGENT_MAP: Dict[TaskComplexity, str] = {
    TaskComplexity.TRIVIAL: "engineer",
    TaskComplexity.LOW: "engineer",
    TaskComplexity.MEDIUM: "engineer",
    TaskComplexity.HIGH: "senior_engineer",
    TaskComplexity.CRITICAL: "principal_engineer",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RoutingDecision:
    """Result of a smart routing analysis."""
    target_agent: str
    confidence: float          # 0.0 – 1.0
    signals_fired: List[RoutingSignal]
    rationale: str
    complexity: TaskComplexity
    required_skills: List[str]
    alternative_agent: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "target_agent": self.target_agent,
            "confidence": self.confidence,
            "signals_fired": [s.value for s in self.signals_fired],
            "rationale": self.rationale,
            "complexity": self.complexity.value,
            "required_skills": self.required_skills,
            "alternative_agent": self.alternative_agent,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentPerformanceRecord:
    """Historical performance data for an agent."""
    agent_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    total_quality_score: float = 0.0
    skill_successes: Dict[str, int] = field(default_factory=dict)
    skill_attempts: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.75  # neutral prior
        return self.successful_tasks / self.total_tasks

    @property
    def avg_quality(self) -> float:
        if self.total_tasks == 0:
            return 80.0  # neutral prior
        return self.total_quality_score / self.total_tasks

    def skill_success_rate(self, skill: str) -> float:
        attempts = self.skill_attempts.get(skill, 0)
        if attempts == 0:
            return 0.75
        return self.skill_successes.get(skill, 0) / attempts


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """
    Loads available skills from the skills/ directory and provides lookup.

    Skills are discovered by scanning for SKILL.md files under skills/.
    Each skill directory name becomes the skill identifier.
    """

    def __init__(self, skills_root: Optional[Path] = None):
        if skills_root is None:
            # Default: repo root / skills/
            skills_root = Path(__file__).parents[4] / "skills"
        self.skills_root = Path(skills_root)
        self._skills: Dict[str, Dict] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Scan skills_root for SKILL.md files and register each skill."""
        if not self.skills_root.exists():
            logger.debug("Skills root not found: %s", self.skills_root)
            return

        for skill_dir in self.skills_root.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_id = skill_dir.name
            skill_md = skill_dir / "SKILL.md"
            self._skills[skill_id] = {
                "id": skill_id,
                "path": str(skill_dir),
                "has_skill_md": skill_md.exists(),
                "description": self._read_description(skill_md),
            }
        logger.debug("SkillRegistry loaded %d skills", len(self._skills))

    def _read_description(self, skill_md: Path) -> str:
        if not skill_md.exists():
            return ""
        try:
            text = skill_md.read_text(encoding="utf-8")
            # Return first non-empty line after the title
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    return line[:200]
        except OSError:
            pass
        return ""

    def available_skills(self) -> List[str]:
        return list(self._skills.keys())

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def get_skill(self, skill_id: str) -> Optional[Dict]:
        return self._skills.get(skill_id)

    def match_skills_to_task(self, task_description: str, scope: str = "") -> List[str]:
        """Return skill IDs whose names appear in the task text."""
        text = (task_description + " " + scope).lower()
        matched = []
        for skill_id in self._skills:
            if skill_id.replace("-", "_").replace("-", " ") in text or skill_id in text:
                matched.append(skill_id)
        return matched


# ---------------------------------------------------------------------------
# SmartRouter
# ---------------------------------------------------------------------------

class SmartRouter:
    """
    Intelligent task router combining multiple routing signals.

    Signal priority (highest → lowest):
    1. Explicit role in DELEGATE
    2. Pre-commit quality gate
    3. Security-scoped flag
    4. Cross-service / architectural flag
    5. Skill-based affinity match
    6. Code review flag
    7. Complexity + plan status
    8. Historical success rates
    9. Default fallback
    """

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        performance_records: Optional[Dict[str, AgentPerformanceRecord]] = None,
    ):
        self.skill_registry = skill_registry or SkillRegistry()
        self._performance: Dict[str, AgentPerformanceRecord] = performance_records or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, delegate: Dict) -> RoutingDecision:
        """
        Analyse a DELEGATE block and return a RoutingDecision.

        Args:
            delegate: Parsed DELEGATE YAML dict.

        Returns:
            RoutingDecision with target agent, confidence, and rationale.
        """
        signals: List[RoutingSignal] = []
        complexity = self._assess_complexity(delegate)
        required_skills = self._extract_required_skills(delegate)

        # --- Signal 1: Explicit role ---
        explicit_role = delegate.get("role", "").lower().replace(" ", "_")
        if explicit_role and explicit_role not in ("", "unknown"):
            signals.append(RoutingSignal.EXPLICIT_ROLE)
            return RoutingDecision(
                target_agent=explicit_role,
                confidence=0.99,
                signals_fired=signals,
                rationale=f"Explicit role '{explicit_role}' specified in DELEGATE.",
                complexity=complexity,
                required_skills=required_skills,
            )

        context = delegate.get("context", {})
        scope = delegate.get("scope", "").lower()
        description = str(delegate.get("description", "")).lower()
        text = scope + " " + description

        # --- Signal 2: Pre-commit quality gate ---
        if context.get("is_precommit_quality_gate") or "pre-commit" in text or "precommit" in text:
            signals.append(RoutingSignal.PRECOMMIT_GATE)
            return RoutingDecision(
                target_agent="quality_engineer",
                confidence=0.97,
                signals_fired=signals,
                rationale="Pre-commit quality gate — routes to Quality Engineer (priority).",
                complexity=complexity,
                required_skills=required_skills,
            )

        # --- Signal 3: Security-scoped ---
        is_security = (
            context.get("is_security_scoped")
            or delegate.get("is_security_scoped")
            or any(kw in text for kw in ("security", "auth", "cryptograph", "vulnerability", "secret"))
        )
        if is_security:
            signals.append(RoutingSignal.SECURITY_SCOPED)
            return RoutingDecision(
                target_agent="security_engineer",
                confidence=0.95,
                signals_fired=signals,
                rationale="Security-scoped task — routes to Security Engineer.",
                complexity=complexity,
                required_skills=required_skills,
            )

        # --- Signal 4: Cross-service / architectural ---
        is_cross = (
            context.get("is_cross_service")
            or delegate.get("is_cross_service")
            or any(kw in text for kw in ("cross-service", "cross_service", "architecture", "multi-service"))
        )
        if is_cross:
            signals.append(RoutingSignal.CROSS_SERVICE)
            return RoutingDecision(
                target_agent="principal_engineer",
                confidence=0.92,
                signals_fired=signals,
                rationale="Cross-service / architectural task — routes to Principal Engineer.",
                complexity=complexity,
                required_skills=required_skills,
            )

        # --- Signal 5: Skill-based affinity ---
        skill_agent = self._route_by_skills(required_skills, text)
        if skill_agent:
            signals.append(RoutingSignal.SKILL_MATCH)
            return RoutingDecision(
                target_agent=skill_agent,
                confidence=0.88,
                signals_fired=signals,
                rationale=f"Skill affinity match for skills {required_skills} → {skill_agent}.",
                complexity=complexity,
                required_skills=required_skills,
            )

        # --- Signal 6: Code review ---
        is_code_review = context.get("is_code_review") or "code review" in text or "pr review" in text
        if is_code_review:
            signals.append(RoutingSignal.CODE_REVIEW)
            target = "quality_engineer" if "validat" in text else "lead_engineer"
            return RoutingDecision(
                target_agent=target,
                confidence=0.87,
                signals_fired=signals,
                rationale=f"Code review task — routes to {target}.",
                complexity=complexity,
                required_skills=required_skills,
            )

        # --- Signal 7: Complexity + plan ---
        has_plan = bool(delegate.get("plan") or context.get("has_plan"))
        signals.append(RoutingSignal.COMPLEXITY)
        if has_plan:
            signals.append(RoutingSignal.HAS_PLAN)

        complexity_agent = self._route_by_complexity(complexity, has_plan)

        # --- Signal 8: Historical success rate adjustment ---
        final_agent = self._adjust_by_history(complexity_agent, required_skills, signals)

        confidence = self._compute_confidence(signals, complexity, has_plan)
        alt = "senior_engineer" if final_agent == "engineer" else "engineer"

        return RoutingDecision(
            target_agent=final_agent,
            confidence=confidence,
            signals_fired=signals,
            rationale=self._build_rationale(signals, final_agent, complexity, has_plan),
            complexity=complexity,
            required_skills=required_skills,
            alternative_agent=alt,
        )

    def record_outcome(
        self,
        agent_name: str,
        success: bool,
        quality_score: float,
        skills_used: Optional[List[str]] = None,
    ) -> None:
        """Record task outcome to improve future routing decisions."""
        if agent_name not in self._performance:
            self._performance[agent_name] = AgentPerformanceRecord(agent_name=agent_name)

        rec = self._performance[agent_name]
        rec.total_tasks += 1
        rec.total_quality_score += quality_score
        if success:
            rec.successful_tasks += 1

        for skill in (skills_used or []):
            rec.skill_attempts[skill] = rec.skill_attempts.get(skill, 0) + 1
            if success:
                rec.skill_successes[skill] = rec.skill_successes.get(skill, 0) + 1

    def get_performance(self, agent_name: str) -> Optional[AgentPerformanceRecord]:
        return self._performance.get(agent_name)

    def all_performance(self) -> Dict[str, AgentPerformanceRecord]:
        return dict(self._performance)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assess_complexity(self, delegate: Dict) -> TaskComplexity:
        effort = delegate.get("effort", "medium").lower()
        complexity_str = delegate.get("complexity", "").lower()
        estimated_tokens = delegate.get("estimated_tokens", 0) or 0

        # Map effort label
        effort_map = {
            "low": TaskComplexity.LOW,
            "medium": TaskComplexity.MEDIUM,
            "high": TaskComplexity.HIGH,
            "max": TaskComplexity.CRITICAL,
        }
        base = effort_map.get(effort, TaskComplexity.MEDIUM)

        # Override with explicit complexity if provided
        complexity_map = {
            "trivial": TaskComplexity.TRIVIAL,
            "low": TaskComplexity.LOW,
            "medium": TaskComplexity.MEDIUM,
            "high": TaskComplexity.HIGH,
            "critical": TaskComplexity.CRITICAL,
        }
        if complexity_str in complexity_map:
            base = complexity_map[complexity_str]

        # Token-based upgrade
        if estimated_tokens > 5000 and base.value in ("trivial", "low", "medium"):
            base = TaskComplexity.HIGH
        if estimated_tokens > 10000:
            base = TaskComplexity.CRITICAL

        return base

    def _extract_required_skills(self, delegate: Dict) -> List[str]:
        """Extract skill requirements from DELEGATE."""
        skills: List[str] = []

        # Explicit skills field
        explicit = delegate.get("required_skills") or delegate.get("skills") or []
        if isinstance(explicit, list):
            skills.extend(explicit)

        # Match against skill registry
        scope = delegate.get("scope", "")
        description = str(delegate.get("description", ""))
        registry_matches = self.skill_registry.match_skills_to_task(description, scope)
        skills.extend(registry_matches)

        return list(dict.fromkeys(skills))  # deduplicate preserving order

    def _route_by_skills(self, required_skills: List[str], text: str) -> Optional[str]:
        """Return agent with highest affinity for required skills."""
        agent_scores: Dict[str, int] = {}
        for skill in required_skills:
            agent = SKILL_AGENT_AFFINITY.get(skill)
            if agent:
                agent_scores[agent] = agent_scores.get(agent, 0) + 1

        # Also scan text for affinity keywords
        for keyword, agent in SKILL_AGENT_AFFINITY.items():
            if keyword in text:
                agent_scores[agent] = agent_scores.get(agent, 0) + 1

        if not agent_scores:
            return None

        return max(agent_scores, key=lambda a: agent_scores[a])

    def _route_by_complexity(self, complexity: TaskComplexity, has_plan: bool) -> str:
        if complexity in (TaskComplexity.TRIVIAL, TaskComplexity.LOW, TaskComplexity.MEDIUM):
            return "engineer"
        if complexity == TaskComplexity.HIGH:
            return "engineer" if has_plan else "senior_engineer"
        # CRITICAL
        return "principal_engineer"

    def _adjust_by_history(
        self,
        candidate: str,
        skills: List[str],
        signals: List[RoutingSignal],
    ) -> str:
        """Optionally downgrade/upgrade based on historical success rates."""
        rec = self._performance.get(candidate)
        if rec is None or rec.total_tasks < 5:
            return candidate  # not enough data

        # If candidate has poor success rate (<60%) try alternative
        if rec.success_rate < 0.60:
            signals.append(RoutingSignal.HISTORICAL_SUCCESS)
            # Escalate one level
            escalation = {
                "engineer": "senior_engineer",
                "senior_engineer": "lead_engineer",
                "lead_engineer": "principal_engineer",
            }
            return escalation.get(candidate, candidate)

        return candidate

    def _compute_confidence(
        self,
        signals: List[RoutingSignal],
        complexity: TaskComplexity,
        has_plan: bool,
    ) -> float:
        base = 0.70
        if RoutingSignal.HAS_PLAN in signals:
            base += 0.08
        if RoutingSignal.HISTORICAL_SUCCESS in signals:
            base += 0.05
        if complexity in (TaskComplexity.TRIVIAL, TaskComplexity.LOW):
            base += 0.05
        return min(round(base, 2), 0.95)

    def _build_rationale(
        self,
        signals: List[RoutingSignal],
        agent: str,
        complexity: TaskComplexity,
        has_plan: bool,
    ) -> str:
        parts = [f"Complexity={complexity.value}"]
        if has_plan:
            parts.append("has_plan=True")
        if RoutingSignal.HISTORICAL_SUCCESS in signals:
            parts.append("adjusted by historical success rates")
        parts.append(f"→ {agent}")
        return "; ".join(parts)
