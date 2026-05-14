"""
Validators Module

Groups A/B/C validation, HANDBACK validation, and cycle detection.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DelegateValidator:
    """DELEGATE validation (Groups A/B/C)."""

    def __init__(self, queue_path: Path):
        """
        Initialize validator with queue path.

        Args:
            queue_path: Path to session queue directory
        """
        self.queue_path = Path(queue_path)

        # Valid roles
        self.valid_roles = {
            "Engineer",
            "Senior Engineer",
            "Lead Engineer",
            "Principal Engineer",
            "Quality Engineer",
            "Security Engineer",
            "Healing Engineer",
            "Model Engineer",
            "Orchestrator",
            "Spec Engineer",
        }

        # Valid effort levels
        self.valid_efforts = {"low", "medium", "high"}

        # Valid models
        self.valid_models = {
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.3-codex",
            "gpt-5.2-codex",
            "gpt-5.2",
            "gpt-5.4-mini",
            "gpt-5-mini",
            "gpt-4.1",
            "claude-sonnet-4.6",
            "claude-sonnet-4.5",
            "claude-haiku-4.5",
            "claude-opus-4.7",
        }

    def validate_groups(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """
        Validate Groups A/B/C validation rules.

        Group A: task_id format, required fields
        Group B: scope ≥15 words, plan present, context present
        Group C: effort/model/role combination valid

        Args:
            delegate: DELEGATE dict to validate

        Returns:
            (valid: bool, errors: List[str])
        """
        errors = []

        # Group A checks
        group_a_errors = self.check_group_a(delegate)
        errors.extend(group_a_errors)

        # Group B checks
        group_b_errors = self.check_group_b(delegate)
        errors.extend(group_b_errors)

        # Group C checks
        group_c_errors = self.check_group_c(delegate)
        errors.extend(group_c_errors)

        return len(errors) == 0, errors

    def check_group_a(self, delegate: Dict) -> List[str]:
        """
        Check Group A rules: task_id format, required fields.

        Group A Rules:
        • task_id: kebab-case, 3-50 chars, matches [a-z0-9-]+
        • Required fields: task_id, role, scope, plan, context
        • All fields must be non-empty

        Args:
            delegate: DELEGATE dict

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check required fields exist
        required_fields = {"task_id", "role", "scope", "plan", "context"}
        missing = required_fields - set(delegate.keys())
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")

        # Check task_id format
        task_id = delegate.get("task_id", "")
        if not task_id:
            errors.append("task_id must not be empty")
        elif not isinstance(task_id, str):
            errors.append("task_id must be a string")
        elif len(task_id) < 3 or len(task_id) > 50:
            errors.append("task_id must be 3-50 characters")
        elif not re.match(r"^[a-z0-9-]+$", task_id):
            errors.append(
                "task_id must match [a-z0-9-]+ (kebab-case, lowercase, digits, hyphens)"
            )

        # Check role is valid
        role = delegate.get("role", "")
        if not role:
            errors.append("role must not be empty")
        elif role not in self.valid_roles:
            errors.append(
                f"role must be one of: {', '.join(sorted(self.valid_roles))}"
            )

        # Check scope is non-empty
        scope = delegate.get("scope", "")
        if not scope:
            errors.append("scope must not be empty")
        elif not isinstance(scope, str):
            errors.append("scope must be a string")

        # Check plan is list with items
        plan = delegate.get("plan", [])
        if not plan:
            errors.append("plan must be a non-empty list")
        elif not isinstance(plan, list):
            errors.append("plan must be a list")

        # Check context is non-empty
        context = delegate.get("context", "")
        if not context:
            errors.append("context must not be empty")
        elif not isinstance(context, str):
            errors.append("context must be a string")

        return errors

    def check_group_b(self, delegate: Dict) -> List[str]:
        """
        Check Group B rules: scope ≥15 words, plan valid, context valid.

        Group B Rules:
        • scope: ≥15 words (split by whitespace)
        • plan: ≥2 steps, each ≥3 words
        • context: ≥20 words

        Args:
            delegate: DELEGATE dict

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check scope word count
        scope = delegate.get("scope", "")
        scope_words = len(scope.split())
        if scope_words < 15:
            errors.append(
                f"scope must be ≥15 words, got {scope_words}: {scope[:50]}..."
            )

        # Check plan
        plan = delegate.get("plan", [])
        if isinstance(plan, list):
            if len(plan) < 2:
                errors.append("plan must have ≥2 steps, got {len(plan)}")
            else:
                for i, step in enumerate(plan):
                    if not isinstance(step, str):
                        errors.append(f"plan step {i} must be a string")
                    elif len(step.split()) < 3:
                        errors.append(
                            f"plan step {i} must be ≥3 words, got: {step}"
                        )

        # Check context word count
        context = delegate.get("context", "")
        context_words = len(context.split())
        if context_words < 20:
            errors.append(
                f"context must be ≥20 words, got {context_words}: {context[:50]}..."
            )

        return errors

    def check_group_c(self, delegate: Dict) -> List[str]:
        """
        Check Group C rules: effort/model/role combination and sub-task fields.

        Group C Rules:
        • effort: low, medium, or high (optional, default: medium)
        • model: one of valid_models list (optional)
        • role must be in valid_roles (already checked in Group A)
        • task_tier: 0-5 integer when present (optional)
        • parent_task_id: must be paired with task_tier (if either is set)

        Args:
            delegate: DELEGATE dict

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check effort if present
        effort = delegate.get("effort")
        if effort and effort not in self.valid_efforts:
            errors.append(f"effort must be one of: {', '.join(self.valid_efforts)}")

        # Check model if present
        model = delegate.get("model")
        if model and model not in self.valid_models:
            errors.append(
                f"model must be one of: {', '.join(sorted(self.valid_models))}"
            )

        # Check task_tier if present
        task_tier = delegate.get("task_tier")
        if task_tier is not None:
            if not isinstance(task_tier, int):
                errors.append("task_tier must be an integer")
            elif task_tier < 0 or task_tier > 5:
                errors.append("task_tier must be between 0 and 5 (max depth is 5)")

        # parent_task_id + task_tier consistency
        parent_task_id = delegate.get("parent_task_id")
        if parent_task_id is not None and task_tier is None:
            errors.append(
                "task_tier must be set when parent_task_id is provided"
            )
        if task_tier is not None and task_tier > 0 and parent_task_id is None:
            errors.append(
                "parent_task_id must be set when task_tier > 0"
            )

        return errors


class HandbackValidator:
    """HANDBACK validation."""

    def validate(self, handback: Dict) -> Tuple[bool, List[str]]:
        """
        Pre-flight validation of HANDBACK.

        HANDBACK must include:
        • task_id: string
        • status: "complete" or "escalated"
        • quality_score: 0-100 (integer)
        • deliverables: list of strings
        • test_results: dict with at least "passed" and "total"
        • metrics: dict with token usage info

        Args:
            handback: HANDBACK dict

        Returns:
            (valid: bool, errors: List[str])
        """
        errors = []

        # Check required fields
        required = {"task_id", "status", "quality_score", "deliverables"}
        missing = required - set(handback.keys())
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")

        # Check task_id
        task_id = handback.get("task_id", "")
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id must be a non-empty string")

        # Check status
        status = handback.get("status", "")
        if status not in {"complete", "escalated"}:
            errors.append("status must be 'complete' or 'escalated'")

        # Check quality_score
        quality = handback.get("quality_score")
        if not isinstance(quality, (int, float)):
            errors.append("quality_score must be a number")
        elif not (0 <= quality <= 100):
            errors.append("quality_score must be 0-100")

        # Check deliverables
        deliverables = handback.get("deliverables")
        if not isinstance(deliverables, list):
            errors.append("deliverables must be a list")
        elif len(deliverables) == 0:
            errors.append("deliverables must not be empty")

        # Check test_results if present
        if "test_results" in handback:
            test_results = handback["test_results"]
            if not isinstance(test_results, dict):
                errors.append("test_results must be a dict")
            elif "passed" not in test_results or "total" not in test_results:
                errors.append("test_results must have 'passed' and 'total' fields")

        # Check metrics if present
        if "metrics" in handback:
            metrics = handback["metrics"]
            if not isinstance(metrics, dict):
                errors.append("metrics must be a dict")

        # ---- Sub-task / aggregation fields (all optional) ----

        # children_created: list of strings
        children_created = handback.get("children_created")
        if children_created is not None:
            if not isinstance(children_created, list):
                errors.append("children_created must be a list")
            else:
                for i, cid in enumerate(children_created):
                    if not isinstance(cid, str) or not cid:
                        errors.append(
                            f"children_created[{i}] must be a non-empty string"
                        )

        # children_results: dict keyed by task_id
        children_results = handback.get("children_results")
        if children_results is not None:
            if not isinstance(children_results, dict):
                errors.append("children_results must be a dict")
            else:
                for cid, result in children_results.items():
                    if not isinstance(result, dict):
                        errors.append(
                            f"children_results['{cid}'] must be a dict"
                        )
                    else:
                        if "status" not in result:
                            errors.append(
                                f"children_results['{cid}'] missing required field 'status'"
                            )
                        if "quality" not in result:
                            errors.append(
                                f"children_results['{cid}'] missing required field 'quality'"
                            )
                        quality = result.get("quality")
                        if quality is not None and not isinstance(quality, (int, float)):
                            errors.append(
                                f"children_results['{cid}'].quality must be a number"
                            )

        # children_failed: list of strings
        children_failed = handback.get("children_failed")
        if children_failed is not None:
            if not isinstance(children_failed, list):
                errors.append("children_failed must be a list")

        # result_aggregation_status: enum
        agg_status = handback.get("result_aggregation_status")
        valid_agg_statuses = {"all_complete", "partial", "timed_out"}
        if agg_status is not None and agg_status not in valid_agg_statuses:
            errors.append(
                f"result_aggregation_status must be one of: "
                f"{', '.join(sorted(valid_agg_statuses))}"
            )

        return len(errors) == 0, errors


class CycleDetector:
    """Detect cycles in @parent task chains."""

    def __init__(self, queue_path: Path):
        """
        Initialize cycle detector.

        Args:
            queue_path: Path to session queue directory
        """
        self.queue_path = Path(queue_path)
        self.max_depth = 5
        self.max_width = 10

    def has_cycle(
        self, task_id: str, parent_task_id: str, max_depth: int = 5,
        max_width: int = 10
    ) -> bool:
        """
        Check if linking task_id to parent_task_id would create cycle.

        Algorithm: Follow parent chain, detect revisits (A→B→C→A)
        Limits: max 5 tiers deep (task_tier ≤ 5), 10 children per parent

        Args:
            task_id: Task being created
            parent_task_id: Proposed parent task
            max_depth: Maximum depth to traverse (default 5)
            max_width: Maximum children per parent (default 10)

        Returns:
            True if cycle detected, False otherwise
        """
        # Can't be parent of itself
        if task_id == parent_task_id:
            return True

        # Follow parent chain up to detect cycle
        visited = set()
        current = parent_task_id
        depth = 0

        while current and depth < max_depth:
            if current in visited:
                # Cycle detected
                return True
            if current == task_id:
                # Would create cycle by going back to task_id
                return True

            visited.add(current)
            current = self._get_parent(current)
            depth += 1

        return False

    def validate_parent(self, parent_task_id: str) -> Tuple[bool, str]:
        """
        Validate @parent_task_id exists and is reachable.

        Args:
            parent_task_id: Parent task ID to validate

        Returns:
            (valid: bool, error_msg: str)
        """
        # Check if parent exists in any state
        for state in ["incoming", "processing", "done"]:
            task_file = self.queue_path / state / f"{parent_task_id}.json"
            if task_file.exists():
                return True, ""

        return False, f"Parent task {parent_task_id} not found"

    def check_width_limit(self, parent_task_id: str) -> Tuple[bool, int]:
        """
        Check if parent has too many children.

        Args:
            parent_task_id: Parent task ID

        Returns:
            (valid: bool, child_count: int)
        """
        child_count = 0
        for state in ["incoming", "processing", "done"]:
            state_path = self.queue_path / state
            if state_path.exists():
                for task_file in state_path.glob("*.json"):
                    try:
                        with open(task_file) as f:
                            task = json.load(f)
                            if task.get("parent_task_id") == parent_task_id:
                                child_count += 1
                    except (json.JSONDecodeError, IOError):
                        continue

        return child_count < self.max_width, child_count

    def _get_parent(self, task_id: str) -> Optional[str]:
        """Get parent_task_id of a task, if it exists."""
        for state in ["incoming", "processing", "done"]:
            task_file = self.queue_path / state / f"{task_id}.json"
            if task_file.exists():
                try:
                    with open(task_file) as f:
                        task = json.load(f)
                        return task.get("parent_task_id")
                except (json.JSONDecodeError, IOError):
                    pass

        return None
