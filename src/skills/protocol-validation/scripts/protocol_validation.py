"""
Protocol Validation — Canonical DELEGATE/HANDBACK validator.

This module is the SINGLE SOURCE OF TRUTH for DELEGATE/HANDBACK schema
validation across agentic-engineers. The evaluation framework, the renderer,
and the queue-management system all delegate to the functions exposed here
instead of carrying their own copies.

Public API:
    validate_delegate(delegate: dict) -> (valid: bool, errors: list[str])
    validate_handback(handback: dict) -> (valid: bool, errors: list[str])

These validate the Core (required) fields plus the loose Extension (optional)
fields. Core validation is strict; extension validation is loose so the schema
can evolve without breaking older producers.

Design notes:
- The class-based validators (CoreProtocolValidator, ExtensionValidator) are
  retained for backward compatibility — callers that previously imported them
  from queue-management can still do so.
- The module-level validate_delegate / validate_handback functions combine
  core + extension validation into a single (bool, errors) result, which is
  what evals and renderers want.
"""

import re
from typing import Tuple, List, Dict, Any
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


def _repo_root() -> Path:
    # src/skills/protocol-validation/scripts/protocol_validation.py -> repo root
    return Path(__file__).resolve().parents[4]


def _skill_exists(skill: str) -> bool:
    """Check if a skill exists in the repository's skills directories.

    Looks in both the canonical source layout (src/skills/) and the legacy
    top-level skills/ directory for forward/backward compatibility. If neither
    directory is present (e.g. running outside a checkout) the skill is allowed.
    """
    if not skill or not isinstance(skill, str):
        return False

    repo_root = _repo_root()
    candidate_dirs = [
        repo_root / "src" / "skills",
        repo_root / "skills",
    ]

    existing_dirs = [d for d in candidate_dirs if d.exists()]
    if not existing_dirs:
        return True  # Can't check, allow it

    for skills_dir in existing_dirs:
        if (skills_dir / skill).exists() or (skills_dir / f"{skill}.md").exists():
            return True
    return False


# ---------------------------------------------------------------------------
# Core validators (strict)
# ---------------------------------------------------------------------------

class CoreProtocolValidator:
    """Validate DELEGATE/HANDBACK core fields only (strict, fast <50ms)."""

    def validate_delegate_core(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """Validate 7 required core fields of a DELEGATE."""
        errors: List[str] = []

        if not isinstance(delegate, dict):
            return (False, ["delegate: must be a mapping/object"])

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

        # 6. plan: >=2 steps, each >=3 words
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
        errors: List[str] = []

        if not isinstance(handback, dict):
            return (False, ["handback: must be a mapping/object"])

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

        # 3. output: required (any value acceptable, but key must be present)
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
            elif not isinstance(q, (int, float)) or isinstance(q, bool) or not (0.0 <= q <= 1.0):
                errors.append(f"metrics.quality: must be 0.0-1.0 (got {q})")

            tokens = metrics.get('tokens')
            if tokens is None:
                errors.append("metrics.tokens: required")
            elif not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
                errors.append(f"metrics.tokens: must be non-negative integer (got {tokens})")

            cost = metrics.get('cost')
            if cost is None:
                errors.append("metrics.cost: required")
            elif not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
                errors.append(f"metrics.cost: must be non-negative number (got {cost})")

            dur = metrics.get('duration_seconds')
            if dur is None:
                errors.append("metrics.duration_seconds: required")
            elif not isinstance(dur, (int, float)) or isinstance(dur, bool) or dur < 0:
                errors.append(f"metrics.duration_seconds: must be non-negative number (got {dur})")

        return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Extension validators (loose)
# ---------------------------------------------------------------------------

class ExtensionValidator:
    """Validate optional extension fields (loose, fast <10ms)."""

    def validate_extensions(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """Validate only DELEGATE extension fields with loose validation."""
        errors: List[str] = []

        if 'effort' in delegate:
            if delegate['effort'] not in VALID_EFFORTS:
                errors.append(f"effort: invalid value '{delegate['effort']}' (must be low|medium|high)")

        if 'model' in delegate and not isinstance(delegate['model'], str):
            errors.append("model: must be a string")

        if 'budget' in delegate:
            if not isinstance(delegate['budget'], (int, float)) or delegate['budget'] < 0:
                errors.append("budget: must be a non-negative number")

        if 'priority' in delegate:
            p = delegate['priority']
            if not isinstance(p, int) or isinstance(p, bool) or p < 1 or p > 10:
                errors.append(f"priority: must be integer 1-10 (got {p})")

        if 'deadline' in delegate and not isinstance(delegate['deadline'], str):
            errors.append("deadline: must be a string (ISO 8601 format)")

        if 'dependencies' in delegate:
            if not isinstance(delegate['dependencies'], list):
                errors.append("dependencies: must be an array")

        if 'parent_task_id' in delegate and not isinstance(delegate['parent_task_id'], str):
            errors.append("parent_task_id: must be a string")

        if 'retry_context' in delegate and not isinstance(delegate['retry_context'], dict):
            errors.append("retry_context: must be an object")

        return (len(errors) == 0, errors)

    def validate_handback_extensions(self, handback: Dict) -> Tuple[bool, List[str]]:
        """Validate HANDBACK extension fields with loose validation."""
        errors: List[str] = []

        if 'retry_count' in handback:
            if not isinstance(handback['retry_count'], int) or isinstance(handback['retry_count'], bool) or handback['retry_count'] < 0:
                errors.append("retry_count: must be a non-negative integer")

        if 'model_used' in handback and not isinstance(handback['model_used'], str):
            errors.append("model_used: must be a string")

        if 'effort_actual' in handback:
            if handback['effort_actual'] not in VALID_EFFORTS:
                errors.append("effort_actual: invalid value (must be low|medium|high)")

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


# ---------------------------------------------------------------------------
# Public functional API — the canonical entry points
# ---------------------------------------------------------------------------

# Module-level singletons (validators are stateless)
_core = CoreProtocolValidator()
_ext = ExtensionValidator()


def validate_delegate(delegate: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a DELEGATE block (core + extension fields).

    Args:
        delegate: DELEGATE dict to validate.

    Returns:
        (valid, errors) where valid is True only when there are no core or
        extension errors, and errors is the combined list of error messages.
    """
    core_valid, core_errors = _core.validate_delegate_core(delegate)
    ext_valid, ext_errors = _ext.validate_extensions(delegate) if isinstance(delegate, dict) else (True, [])
    errors = list(core_errors) + list(ext_errors)
    return (len(errors) == 0, errors)


def validate_handback(handback: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a HANDBACK block (core + extension fields).

    Args:
        handback: HANDBACK dict to validate.

    Returns:
        (valid, errors) where valid is True only when there are no core or
        extension errors, and errors is the combined list of error messages.
    """
    core_valid, core_errors = _core.validate_handback_core(handback)
    ext_valid, ext_errors = _ext.validate_handback_extensions(handback) if isinstance(handback, dict) else (True, [])
    errors = list(core_errors) + list(ext_errors)
    return (len(errors) == 0, errors)


__all__ = [
    "validate_delegate",
    "validate_handback",
    "CoreProtocolValidator",
    "ExtensionValidator",
    "VALID_AGENTS",
    "VALID_STATUSES",
    "VALID_EFFORTS",
    "TASK_ID_PATTERN",
]
