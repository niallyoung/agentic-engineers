"""
Core Protocol Validator — Phase 3 Protocol Simplification.

Validates DELEGATE/HANDBACK against Core (7 required fields) and
Extension (optional metadata) rules independently.

Core validation: strict, <50ms
Extension validation: loose, <10ms
"""

import re
from typing import Tuple, List, Dict, Any, Union
from pathlib import Path


# Valid agents per Phase 3 spec (uses hyphenated names, unlike old underscore names)
VALID_AGENTS = {
    'orchestrator', 'engineer', 'senior-engineer', 'lead-engineer',
    'principal-engineer', 'security-engineer', 'quality-engineer', 'model-engineer'
}

VALID_STATUSES = {'success', 'failure', 'partial', 'blocked', 'escalate'}

VALID_EFFORTS = {'low', 'medium', 'high'}

# task_id: kebab-case, 3-50 chars total
TASK_ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$')


def _count_words(text: str) -> int:
    return len(text.split())


def _skill_exists(skill: str) -> bool:
    """Check if skill exists in skills/ directory."""
    if not skill or not isinstance(skill, str):
        return False
    repo_root = Path(__file__).resolve().parents[3]  # skills/queue-management/scripts/ -> repo root
    skills_dir = repo_root / "skills"
    if not skills_dir.exists():
        return True  # Can't check, allow it
    # Check for skill directory or skill .md file
    skill_dir = skills_dir / skill
    skill_md = skills_dir / f"{skill}.md"
    return skill_dir.exists() or skill_md.exists()


class CoreProtocolValidator:
    """Validate DELEGATE/HANDBACK core fields only (strict, fast <50ms)."""

    def validate_delegate_core(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """Validate 7 required core fields of a DELEGATE."""
        errors = []

        # 1. task_id: kebab-case, 3-50 chars
        task_id = delegate.get('task_id')
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id: required, must be a string")
        elif not TASK_ID_PATTERN.match(task_id):
            errors.append(f"task_id: must be kebab-case, 3-50 chars (got '{task_id}')")

        # 2. skill: must exist in skills/
        skill = delegate.get('skill')
        if not skill or not isinstance(skill, str):
            errors.append("skill: required, must be a string")
        elif not _skill_exists(skill):
            errors.append(f"skill: unknown skill '{skill}' (not found in skills/)")

        # 3. agent: must be in VALID_AGENTS
        agent = delegate.get('agent')
        if not agent or not isinstance(agent, str):
            errors.append("agent: required, must be a string")
        elif agent not in VALID_AGENTS:
            errors.append(f"agent: invalid agent '{agent}' (must be one of {sorted(VALID_AGENTS)})")

        # 4. scope: >=15 words
        scope = delegate.get('scope', '')
        if not scope or not isinstance(scope, str):
            errors.append("scope: required, must be a string")
        elif _count_words(scope) < 15:
            errors.append(f"scope: must be >=15 words ({_count_words(scope)} provided)")

        # 5. success_criteria: non-empty array
        sc = delegate.get('success_criteria')
        if sc is None:
            errors.append("success_criteria: required")
        elif not isinstance(sc, list) or len(sc) == 0:
            errors.append("success_criteria: must be a non-empty array")

        # 6. plan: >=2 steps, each >=3 words (9 chars minimum used as proxy)
        plan = delegate.get('plan')
        if plan is None:
            errors.append("plan: required")
        elif not isinstance(plan, list) or len(plan) < 2:
            errors.append(f"plan: must have >=2 steps ({len(plan) if isinstance(plan, list) else 0} provided)")
        else:
            for i, step in enumerate(plan):
                if isinstance(step, str) and _count_words(step) < 3:
                    errors.append(f"plan[{i}]: each step must be >=3 words (got '{step}')")

        # 7. context: >=20 words (string) or non-empty list of strings
        context = delegate.get('context')
        if context is None:
            errors.append("context: required")
        elif isinstance(context, str):
            if _count_words(context) < 20:
                errors.append(f"context: must be >=20 words ({_count_words(context)} provided)")
        elif isinstance(context, list):
            if len(context) == 0:
                errors.append("context: must be non-empty when provided as array")
        else:
            errors.append("context: must be a string or array of strings")

        return (len(errors) == 0, errors)

    def validate_handback_core(self, handback: Dict) -> Tuple[bool, List[str]]:
        """Validate 4 required core fields of a HANDBACK."""
        errors = []

        # 1. task_id
        task_id = handback.get('task_id')
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id: required, must be a string")

        # 2. status
        status = handback.get('status')
        if not status:
            errors.append("status: required")
        elif status not in VALID_STATUSES:
            errors.append(f"status: invalid value '{status}' (must be one of {sorted(VALID_STATUSES)})")

        # 3. output: required (any value is acceptable, but key must be present)
        if 'output' not in handback:
            errors.append("output: required")

        # 4. metrics: required object with quality, tokens, cost, duration_seconds
        metrics = handback.get('metrics')
        if metrics is None:
            errors.append("metrics: required")
        elif not isinstance(metrics, dict):
            errors.append("metrics: must be an object")
        else:
            q = metrics.get('quality')
            if q is None:
                errors.append("metrics.quality: required")
            elif not isinstance(q, (int, float)) or not (0.0 <= q <= 1.0):
                errors.append(f"metrics.quality: must be 0.0-1.0 (got {q})")

            tokens = metrics.get('tokens')
            if tokens is None:
                errors.append("metrics.tokens: required")
            elif not isinstance(tokens, int) or tokens < 0:
                errors.append(f"metrics.tokens: must be non-negative integer (got {tokens})")

            cost = metrics.get('cost')
            if cost is None:
                errors.append("metrics.cost: required")
            elif not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"metrics.cost: must be non-negative number (got {cost})")

            dur = metrics.get('duration_seconds')
            if dur is None:
                errors.append("metrics.duration_seconds: required")
            elif not isinstance(dur, (int, float)) or dur < 0:
                errors.append(f"metrics.duration_seconds: must be non-negative number (got {dur})")

        return (len(errors) == 0, errors)


class ExtensionValidator:
    """Validate optional extension fields (loose, fast <10ms)."""

    def validate_extensions(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """Validate only extension fields with loose validation."""
        errors = []

        # effort: enum check only
        if 'effort' in delegate:
            if delegate['effort'] not in VALID_EFFORTS:
                errors.append(f"effort: invalid value '{delegate['effort']}' (must be low|medium|high)")

        # model: allow any string (soft validation, no catalog check)
        if 'model' in delegate and not isinstance(delegate['model'], str):
            errors.append("model: must be a string")

        # budget: numeric check only
        if 'budget' in delegate:
            if not isinstance(delegate['budget'], (int, float)) or delegate['budget'] < 0:
                errors.append("budget: must be a non-negative number")

        # priority: 1-10 range
        if 'priority' in delegate:
            p = delegate['priority']
            if not isinstance(p, int) or p < 1 or p > 10:
                errors.append(f"priority: must be integer 1-10 (got {p})")

        # deadline: basic string check (loose — don't fully parse ISO 8601)
        if 'deadline' in delegate and not isinstance(delegate['deadline'], str):
            errors.append("deadline: must be a string (ISO 8601 format)")

        # dependencies: must be a list if present
        if 'dependencies' in delegate:
            if not isinstance(delegate['dependencies'], list):
                errors.append("dependencies: must be an array")

        # parent_task_id: string check
        if 'parent_task_id' in delegate and not isinstance(delegate['parent_task_id'], str):
            errors.append("parent_task_id: must be a string")

        # retry_context: object check
        if 'retry_context' in delegate and not isinstance(delegate['retry_context'], dict):
            errors.append("retry_context: must be an object")

        return (len(errors) == 0, errors)

    def validate_handback_extensions(self, handback: Dict) -> Tuple[bool, List[str]]:
        """Validate handback extension fields with loose validation."""
        errors = []

        if 'retry_count' in handback:
            if not isinstance(handback['retry_count'], int) or handback['retry_count'] < 0:
                errors.append("retry_count: must be a non-negative integer")

        if 'model_used' in handback and not isinstance(handback['model_used'], str):
            errors.append("model_used: must be a string")

        if 'effort_actual' in handback:
            if handback['effort_actual'] not in VALID_EFFORTS:
                errors.append(f"effort_actual: invalid value (must be low|medium|high)")

        if 'flags' in handback:
            if not isinstance(handback['flags'], list):
                errors.append("flags: must be an array")

        if 'error' in handback and not isinstance(handback['error'], str):
            errors.append("error: must be a string")

        if 'children_created' in handback:
            if not isinstance(handback['children_created'], list):
                errors.append("children_created: must be an array")

        if 'children_results' in handback and not isinstance(handback['children_results'], dict):
            errors.append("children_results: must be an object")

        return (len(errors) == 0, errors)
