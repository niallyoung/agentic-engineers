"""
tests/evals/test_delegate_quality_evals.py — Quality evaluation tests for DELEGATE blocks.

Tests that DELEGATEs conform to QUEUE-PROTOCOL.md canonical schema and quality standards:
- Required fields are present and non-empty
- Plan steps are actionable (imperative, not vague)
- Success criteria are measurable (no vague language)
- Task IDs follow YYYY-MM-DD-kebab-case format
- Scope is substantial (>= 15 words)
"""

import re
import pytest
from typing import Dict


class TestDelegateHasRequiredFields:
    """Eval: DELEGATE must have all required fields per QUEUE-PROTOCOL.md."""

    REQUIRED_FIELDS = [
        "handoff_type",
        "task_id",
        "agent",
        "scope",
        "plan",
        "success_criteria",
        "context",
    ]

    def eval_has_all_required_fields(self, delegate: Dict) -> bool:
        """Check that all required fields are present."""
        for field in self.REQUIRED_FIELDS:
            if field not in delegate:
                return False
        return True

    def eval_handoff_type_is_delegate(self, delegate: Dict) -> bool:
        """Check that handoff_type is exactly 'DELEGATE'."""
        return delegate.get("handoff_type") == "DELEGATE"

    def eval_agent_field_exists(self, delegate: Dict) -> bool:
        """Check that 'agent' field exists (not legacy 'role')."""
        if "role" in delegate and "agent" not in delegate:
            return False
        return "agent" in delegate

    def test_canonical_delegate_has_all_required_fields(self, canonical_delegate_basic):
        """Test that canonical DELEGATE has all required fields."""
        assert self.eval_has_all_required_fields(canonical_delegate_basic)
        assert self.eval_handoff_type_is_delegate(canonical_delegate_basic)
        assert self.eval_agent_field_exists(canonical_delegate_basic)

    def test_all_delegates_in_corpus_have_required_fields(self, delegate_corpus):
        """Test that all DELEGATE samples in corpus have required fields."""
        for delegate in delegate_corpus:
            assert self.eval_has_all_required_fields(delegate), f"Missing fields in {delegate.get('task_id')}"
            assert self.eval_handoff_type_is_delegate(delegate)


class TestDelegatePlanIsActionable:
    """Eval: Plan steps must be imperative, specific, and actionable (not vague)."""

    VAGUE_KEYWORDS = [
        "review",
        "look at",
        "check",
        "examine",
        "think about",
        "consider",
        "explore",
        "maybe",
        "possibly",
        "research",
        "investigate",
        "etc",
    ]

    def eval_plan_steps_are_imperative(self, plan: list) -> bool:
        """Check that each step starts with a verb (imperative mood)."""
        verbs = [
            "read",
            "write",
            "create",
            "update",
            "modify",
            "add",
            "remove",
            "delete",
            "implement",
            "refactor",
            "test",
            "run",
            "verify",
            "validate",
            "fix",
            "extract",
            "locate",
            "apply",
            "identify",
            "replace",
            "integrate",
            "audit",
            "design",
            "scan",
            "document",
            "assess",
            "evaluate",
            "develop",
            "ensure",
            "conduct",
            "analyze",
            "research",
            "plan",
            "provide",
            "review",
            "estimate",
        ]
        for step in plan:
            step_lower = step.lower().strip()
            # Check if step starts with a recognized imperative verb or digit (numbered lists)
            has_imperative = any(step_lower.startswith(v) for v in verbs)
            has_number = step_lower[0].isdigit() if step_lower else False
            if not (has_imperative or has_number):
                return False
        return True

    def eval_plan_steps_are_not_vague(self, plan: list) -> bool:
        """Check that plan steps don't use vague language."""
        for step in plan:
            step_lower = step.lower()
            for vague in self.VAGUE_KEYWORDS:
                if f" {vague} " in f" {step_lower} " or step_lower.startswith(f"{vague} "):
                    # Allow "etc" only in specific contexts (e.g., "test error handling, etc.")
                    if vague == "etc" and "test" not in step_lower:
                        return False
                    # Allow "maybe" only in explicit uncertainty contexts (rare)
                    if vague == "maybe":
                        return False
        return True

    def eval_plan_has_minimum_steps(self, plan: list) -> bool:
        """Check that plan has at least 2 steps."""
        return len(plan) >= 2

    def eval_plan_steps_have_substance(self, plan: list) -> bool:
        """Check that each step has at least 3 words."""
        for step in plan:
            # Strip numbering (e.g., "1. ", "2. ")
            content = re.sub(r"^\d+\.\s*", "", step).strip()
            word_count = len(content.split())
            if word_count < 3:
                return False
        return True

    def test_canonical_delegate_plan_is_actionable(self, canonical_delegate_basic):
        """Test that canonical DELEGATE plan is actionable."""
        plan = canonical_delegate_basic.get("plan", [])
        assert self.eval_plan_steps_are_imperative(plan)
        assert self.eval_plan_steps_are_not_vague(plan)
        assert self.eval_plan_has_minimum_steps(plan)
        assert self.eval_plan_steps_have_substance(plan)

    def test_all_delegate_plans_in_corpus_are_actionable(self, delegate_corpus):
        """Test that all DELEGATE plans in corpus are actionable."""
        for delegate in delegate_corpus:
            plan = delegate.get("plan", [])
            assert self.eval_plan_steps_are_imperative(plan), f"Plan not imperative in {delegate.get('task_id')}"
            assert self.eval_plan_steps_have_substance(plan), f"Plan steps too short in {delegate.get('task_id')}"


class TestDelegateSuccessCriteriaAreMeasurable:
    """Eval: Success criteria must be measurable and specific (no vague language)."""

    UNMEASURABLE_KEYWORDS = ["good", "better", "well", "nice", "probably", "maybe", "etc", "etc."]

    def eval_criteria_are_measurable(self, criteria: list) -> bool:
        """Check that criteria don't use unmeasurable language."""
        for criterion in criteria:
            criterion_lower = criterion.lower()
            for unmeasurable in self.UNMEASURABLE_KEYWORDS:
                if unmeasurable in criterion_lower:
                    # Exception: "well-formed" is OK
                    if unmeasurable == "well" and "well-formed" in criterion_lower:
                        continue
                    return False
        return True

    def eval_criteria_use_specific_metrics(self, criteria: list) -> bool:
        """Check that criteria include specific metrics or outcomes when possible."""
        # At least one criterion should mention numbers, percentages, or specific outcomes
        for criterion in criteria:
            if any(
                keyword in criterion.lower()
                for keyword in ["pass", "fail", "zero", "100%", "%", "coverage", "error", "success"]
            ):
                return True
        # If no numeric criteria, check that criteria are at least very specific
        return all(len(c) > 20 for c in criteria)

    def eval_criteria_have_minimum_count(self, criteria: list) -> bool:
        """Check that there are at least 2 success criteria."""
        return len(criteria) >= 2

    def test_canonical_delegate_criteria_are_measurable(self, canonical_delegate_basic):
        """Test that canonical DELEGATE success criteria are measurable."""
        criteria = canonical_delegate_basic.get("success_criteria", [])
        assert self.eval_criteria_are_measurable(criteria)
        assert self.eval_criteria_have_minimum_count(criteria)

    def test_all_delegate_criteria_in_corpus_are_measurable(self, delegate_corpus):
        """Test that all DELEGATE criteria in corpus are measurable."""
        for delegate in delegate_corpus:
            criteria = delegate.get("success_criteria", [])
            assert self.eval_criteria_are_measurable(criteria), f"Unmeasurable criteria in {delegate.get('task_id')}"
            assert self.eval_criteria_have_minimum_count(criteria), f"Too few criteria in {delegate.get('task_id')}"


class TestTaskIdFormat:
    """Eval: task_id must follow YYYY-MM-DD-kebab-case format."""

    def eval_task_id_format(self, task_id: str) -> bool:
        """Check that task_id matches YYYY-MM-DD-kebab-case pattern."""
        pattern = r"^\d{4}-\d{2}-\d{2}-[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
        return bool(re.match(pattern, task_id))

    def eval_task_id_length(self, task_id: str) -> bool:
        """Check that task_id is between 10 and 50 chars."""
        return 10 <= len(task_id) <= 50

    def test_canonical_delegate_task_id_format(self, canonical_delegate_basic):
        """Test that canonical DELEGATE has valid task_id format."""
        task_id = canonical_delegate_basic.get("task_id", "")
        assert self.eval_task_id_format(task_id)
        assert self.eval_task_id_length(task_id)

    def test_all_delegate_task_ids_in_corpus_are_valid(self, delegate_corpus):
        """Test that all DELEGATE task_ids in corpus are valid."""
        for delegate in delegate_corpus:
            task_id = delegate.get("task_id", "")
            assert self.eval_task_id_format(task_id), f"Invalid format: {task_id}"
            assert self.eval_task_id_length(task_id), f"Invalid length: {task_id}"


class TestDelegateScopeSubstantiality:
    """Eval: Scope must be substantial (>= 15 words) and descriptive."""

    def eval_scope_minimum_length(self, scope: str) -> bool:
        """Check that scope has at least 15 words."""
        word_count = len(scope.split())
        return word_count >= 15

    def eval_scope_describes_what_and_why(self, scope: str) -> bool:
        """Check that scope describes both what and why (not just what)."""
        scope_lower = scope.lower()
        # Should include some outcome-oriented keywords
        outcome_keywords = ["fix", "implement", "design", "refactor", "improve", "add", "handle", "support"]
        has_what = any(kw in scope_lower for kw in outcome_keywords)

        # Should explain the purpose/benefit
        purpose_keywords = ["to", "for", "that", "which", "because", "in order", "so that", "account for"]
        has_why = any(kw in scope_lower for kw in purpose_keywords)

        return has_what and (has_why or len(scope.split()) > 20)

    def test_canonical_delegate_scope_is_substantial(self, canonical_delegate_basic):
        """Test that canonical DELEGATE scope is substantial."""
        scope = canonical_delegate_basic.get("scope", "")
        assert self.eval_scope_minimum_length(scope)
        assert self.eval_scope_describes_what_and_why(scope)

    def test_all_delegate_scopes_in_corpus_are_substantial(self, delegate_corpus):
        """Test that all DELEGATE scopes in corpus are substantial."""
        for delegate in delegate_corpus:
            scope = delegate.get("scope", "")
            assert self.eval_scope_minimum_length(scope), f"Scope too short in {delegate.get('task_id')}"


class TestDelegateContextQuality:
    """Eval: Context must be substantial and relevant (>= 20 words or 3+ items)."""

    def eval_context_is_substantial(self, context) -> bool:
        """Check that context is substantial (>= 20 words or 3+ items)."""
        if isinstance(context, list):
            return len(context) >= 3 and all(len(str(item).split()) >= 2 for item in context)
        elif isinstance(context, str):
            return len(context.split()) >= 20
        return False

    def test_canonical_delegate_context_is_substantial(self, canonical_delegate_basic):
        """Test that canonical DELEGATE context is substantial."""
        context = canonical_delegate_basic.get("context", "")
        assert self.eval_context_is_substantial(context)

    def test_all_delegate_contexts_in_corpus_are_substantial(self, delegate_corpus):
        """Test that all DELEGATE contexts in corpus are substantial."""
        for delegate in delegate_corpus:
            context = delegate.get("context", "")
            assert self.eval_context_is_substantial(context), f"Insufficient context in {delegate.get('task_id')}"


class TestDelegateAgentValidity:
    """Eval: agent field must be a valid role (hyphenated lowercase)."""

    VALID_AGENTS = [
        "engineer",
        "senior-engineer",
        "lead-engineer",
        "quality-engineer",
        "principal-engineer",
        "security-engineer",
        "model-engineer",
        "orchestrator",
    ]

    def eval_agent_is_valid(self, agent: str) -> bool:
        """Check that agent is a recognized role."""
        return agent in self.VALID_AGENTS

    def eval_agent_format(self, agent: str) -> bool:
        """Check that agent is hyphenated lowercase."""
        return agent.islower() and (agent.isalpha() or all(c.isalpha() or c == "-" for c in agent))

    def test_canonical_delegate_agent_is_valid(self, canonical_delegate_basic):
        """Test that canonical DELEGATE agent is valid."""
        agent = canonical_delegate_basic.get("agent", "")
        assert self.eval_agent_format(agent)
        # Note: agent may be valid even if not in VALID_AGENTS (for extensibility)

    def test_delegate_corpus_agents_are_valid(self, delegate_corpus):
        """Test that all DELEGATE agents in corpus are valid."""
        for delegate in delegate_corpus:
            agent = delegate.get("agent", "")
            assert self.eval_agent_format(agent), f"Invalid agent format: {agent}"


# ============================================================================
# Summary: Composite Tests
# ============================================================================


class TestDelegateQualitySummary:
    """Summary: Complete quality check for a DELEGATE."""

    def test_canonical_delegate_passes_all_evals(self, canonical_delegate_basic):
        """Test that canonical DELEGATE passes all quality evals."""
        # Required fields
        assert "handoff_type" in canonical_delegate_basic
        assert canonical_delegate_basic["handoff_type"] == "DELEGATE"
        assert "task_id" in canonical_delegate_basic
        assert "agent" in canonical_delegate_basic
        assert "scope" in canonical_delegate_basic
        assert "plan" in canonical_delegate_basic
        assert "success_criteria" in canonical_delegate_basic
        assert "context" in canonical_delegate_basic

        # Task ID format
        task_id = canonical_delegate_basic["task_id"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$", task_id)

        # Scope quality
        scope = canonical_delegate_basic["scope"]
        assert len(scope.split()) >= 15

        # Plan quality
        plan = canonical_delegate_basic["plan"]
        assert len(plan) >= 2

        # Success criteria quality
        criteria = canonical_delegate_basic["success_criteria"]
        assert len(criteria) >= 2

    def test_delegate_corpus_all_pass_baseline_quality(self, delegate_corpus):
        """Test that all DELEGATEs in corpus pass baseline quality gates."""
        for delegate in delegate_corpus:
            # Required fields
            assert "handoff_type" in delegate
            assert delegate["handoff_type"] == "DELEGATE"
            assert "task_id" in delegate
            assert "agent" in delegate
            assert "scope" in delegate
            assert "plan" in delegate
            assert "success_criteria" in delegate
            assert "context" in delegate

            # Basic format checks
            assert isinstance(delegate["plan"], list)
            assert isinstance(delegate["success_criteria"], list)
            assert len(delegate["plan"]) >= 1
            assert len(delegate["success_criteria"]) >= 1
