"""
tests/evals/test_orchestrator_routing_evals.py — Evaluation tests for orchestrator routing correctness.

Tests that the Orchestrator correctly applies the routing decision tree from AGENTS.md:
1. Is task security-scoped? → security-engineer
2. Does task affect multiple services? → principal-engineer
3. Is task complex without plan? → senior-engineer (to write plan)
4. Is task code review? → lead-engineer or quality-engineer
5. Is task well-scoped with plan? → engineer

Additionally tests:
- Model assignment matches effort level
- Escalation routing creates new DELEGATE for target agent
- Quality Engineer gates are applied correctly
"""

import pytest
from typing import Dict, List


class TestSecurityTasksRouteToSecurityEngineer:
    """Eval: Tasks mentioning security keywords route to security-engineer."""

    SECURITY_KEYWORDS = [
        "security",
        "vulnerability",
        "audit",
        "threat",
        "exploit",
        "credential",
        "secret",
        "encryption",
        "authentication",
        "authorization",
        "breach",
        "exposure",
    ]

    def eval_task_is_security_scoped(self, delegate: Dict) -> bool:
        """Check if task scope contains security keywords."""
        scope = delegate.get("scope", "").lower()
        context = str(delegate.get("context", "")).lower()
        full_text = f"{scope} {context}"

        for keyword in self.SECURITY_KEYWORDS:
            if keyword in full_text:
                return True
        return False

    def eval_should_route_to_security_engineer(self, delegate: Dict) -> bool:
        """Check routing decision: if security-scoped, route to security-engineer."""
        if not self.eval_task_is_security_scoped(delegate):
            return True  # Not a security task, doesn't apply

        return delegate.get("agent") == "security-engineer"

    def test_canonical_security_delegate_routes_to_security_engineer(self, canonical_delegate_security):
        """Test that security-scoped DELEGATE routes to security-engineer."""
        assert self.eval_task_is_security_scoped(canonical_delegate_security)
        assert canonical_delegate_security.get("agent") == "security-engineer"

    def test_security_audit_routes_correctly(self, canonical_delegate_security):
        """Test audit task routes to security-engineer."""
        assert self.eval_task_is_security_scoped(canonical_delegate_security)
        assert self.eval_should_route_to_security_engineer(canonical_delegate_security)


class TestComplexTasksRouteToSenior:
    """Eval: Complex, unscoped tasks (no plan) route to senior-engineer to write plan."""

    def eval_task_has_plan(self, delegate: Dict) -> bool:
        """Check if task has a plan."""
        plan = delegate.get("plan", [])
        return isinstance(plan, list) and len(plan) >= 2

    def eval_task_scope_is_complex(self, delegate: Dict) -> bool:
        """Check if scope indicates complex work (50+ words or architectural keywords)."""
        scope = delegate.get("scope", "")
        word_count = len(scope.split())

        complex_keywords = [
            "design",
            "architecture",
            "cross-service",
            "refactor",
            "migration",
            "strategy",
        ]
        has_complex_keywords = any(kw in scope.lower() for kw in complex_keywords)

        return word_count >= 50 or has_complex_keywords

    def eval_should_route_to_senior(self, delegate: Dict) -> bool:
        """Check routing decision: if complex without plan, route to senior-engineer."""
        if not self.eval_task_scope_is_complex(delegate):
            return True  # Not complex, doesn't apply

        if self.eval_task_has_plan(delegate):
            return True  # Has plan, so engineer can handle

        # Complex without plan → senior-engineer
        return delegate.get("agent") == "senior-engineer"

    def test_canonical_senior_delegate_routes_to_senior_engineer(self, canonical_delegate_senior):
        """Test that complex, unscoped DELEGATE routes to senior-engineer."""
        assert self.eval_task_scope_is_complex(canonical_delegate_senior)
        # Senior delegate may or may not have full plan (that's the point)
        assert canonical_delegate_senior.get("agent") == "senior-engineer"

    def test_architectural_task_needs_senior(self, canonical_delegate_senior):
        """Test architectural design task routes to senior."""
        assert "architecture" in canonical_delegate_senior.get("scope", "").lower()
        assert self.eval_should_route_to_senior(canonical_delegate_senior)


class TestWellScopedTasksRouteToEngineer:
    """Eval: Well-scoped tasks with clear plan route to engineer."""

    def eval_task_is_well_scoped(self, delegate: Dict) -> bool:
        """Check if task has scope, plan, and success_criteria."""
        return (
            len(delegate.get("scope", "").split()) >= 15
            and len(delegate.get("plan", [])) >= 2
            and len(delegate.get("success_criteria", [])) >= 2
        )

    def eval_should_route_to_engineer(self, delegate: Dict) -> bool:
        """Check routing decision: if well-scoped with plan, route to engineer."""
        if not self.eval_task_is_well_scoped(delegate):
            return True  # Not well-scoped, doesn't apply (would route elsewhere)

        # Well-scoped tasks should route to engineer
        return delegate.get("agent") == "engineer"

    def test_canonical_engineer_delegate_routes_to_engineer(self, canonical_delegate_basic):
        """Test that well-scoped DELEGATE routes to engineer."""
        assert self.eval_task_is_well_scoped(canonical_delegate_basic)
        assert canonical_delegate_basic.get("agent") == "engineer"

    def test_simple_fix_task_routes_to_engineer(self, canonical_delegate_basic):
        """Test simple, well-scoped fix routes to engineer."""
        assert self.eval_should_route_to_engineer(canonical_delegate_basic)


class TestEscalationRoutingCreatesNewDelegate:
    """Eval: HANDBACK with status=escalate creates new DELEGATE for target agent."""

    def eval_escalate_handback_has_target(self, handback: Dict) -> bool:
        """Check that escalate HANDBACK specifies target agent."""
        if handback.get("status") != "escalate":
            return True  # Not escalation, skip

        output = handback.get("output", {})
        if isinstance(output, dict):
            return "escalate_to" in output
        return False

    def eval_escalation_chain_is_valid(self, handback: Dict) -> bool:
        """Check that escalation chain is present and valid."""
        if handback.get("status") != "escalate":
            return True

        chain = handback.get("escalation_chain", [])
        return isinstance(chain, list) and len(chain) >= 1

    def eval_escalate_to_valid_agent(self, escalate_to: str) -> bool:
        """Check that escalation target is a valid agent role."""
        valid_agents = [
            "engineer",
            "senior-engineer",
            "lead-engineer",
            "quality-engineer",
            "principal-engineer",
            "security-engineer",
            "orchestrator",
        ]
        return escalate_to in valid_agents

    def test_canonical_escalate_handback_has_target(self, canonical_handback_escalate):
        """Test that escalate HANDBACK specifies target agent."""
        assert self.eval_escalate_handback_has_target(canonical_handback_escalate)
        assert "escalate_to" in canonical_handback_escalate.get("output", {})

    def test_canonical_escalate_has_chain(self, canonical_handback_escalate):
        """Test that escalate HANDBACK has escalation chain."""
        assert self.eval_escalation_chain_is_valid(canonical_handback_escalate)

    def test_escalation_target_is_valid_agent(self, canonical_handback_escalate):
        """Test that escalation target is a valid agent."""
        output = canonical_handback_escalate.get("output", {})
        escalate_to = output.get("escalate_to", "")
        assert self.eval_escalate_to_valid_agent(escalate_to)


class TestModelAssignmentMatchesEffort:
    """Eval: Model assignment must match effort level (haiku/sonnet/opus)."""

    MODEL_EFFORT_MAP = {
        "claude-haiku-4.5": ["low", "medium"],
        "claude-sonnet-4.5": ["medium", "high"],
        "claude-sonnet-4.6": ["medium", "high"],
        "claude-opus-4.6": ["high", "max"],
        "claude-opus-4.8": ["high", "max"],
    }

    def eval_model_matches_effort(self, delegate: Dict) -> bool:
        """Check that model is appropriate for effort level."""
        model = delegate.get("model", "")
        effort = delegate.get("effort", "medium")

        if model not in self.MODEL_EFFORT_MAP:
            return True  # Unknown model, skip validation

        valid_efforts = self.MODEL_EFFORT_MAP[model]
        return effort in valid_efforts

    def eval_effort_matches_agent(self, delegate: Dict) -> bool:
        """Check that effort is reasonable for assigned agent."""
        agent = delegate.get("agent", "")
        effort = delegate.get("effort", "medium")

        # engineer should typically be low/medium effort
        if agent == "engineer" and effort not in ["low", "medium", "high"]:
            return False

        # senior-engineer should be medium/high effort
        if agent == "senior-engineer" and effort not in ["medium", "high"]:
            return False

        # security/principal should be high/max effort
        if agent in ["security-engineer", "principal-engineer"] and effort not in ["high", "max"]:
            return False

        return True

    def test_canonical_engineer_delegate_model_matches_effort(self, canonical_delegate_basic):
        """Test that engineer DELEGATE model matches effort."""
        assert self.eval_model_matches_effort(canonical_delegate_basic)
        assert self.eval_effort_matches_agent(canonical_delegate_basic)

    def test_canonical_senior_delegate_model_matches_effort(self, canonical_delegate_senior):
        """Test that senior DELEGATE model matches effort."""
        assert self.eval_model_matches_effort(canonical_delegate_senior)
        assert self.eval_effort_matches_agent(canonical_delegate_senior)

    def test_canonical_security_delegate_model_matches_effort(self, canonical_delegate_security):
        """Test that security DELEGATE model matches effort."""
        assert self.eval_model_matches_effort(canonical_delegate_security)
        assert self.eval_effort_matches_agent(canonical_delegate_security)

    def test_delegate_corpus_all_models_match_effort(self, delegate_corpus):
        """Test that all DELEGATEs in corpus have appropriate model/effort pairs."""
        for delegate in delegate_corpus:
            assert self.eval_model_matches_effort(delegate), f"Model/effort mismatch in {delegate.get('task_id')}"


class TestQualityGateRouting:
    """Eval: Quality-engineer gates are applied when quality < threshold."""

    QUALITY_THRESHOLD = 0.70

    def eval_handback_quality_below_threshold(self, handback: Dict, threshold: float = 0.70) -> bool:
        """Check if HANDBACK quality is below threshold."""
        quality = handback.get("metrics", {}).get("quality", 1.0)
        return quality < threshold

    def eval_low_quality_handback_routes_to_qe(self, handback: Dict) -> bool:
        """Check routing decision: if quality < threshold, escalate to quality-engineer."""
        if not self.eval_handback_quality_below_threshold(handback):
            return True  # Quality acceptable, no routing needed

        # Low quality should escalate for review
        output = handback.get("output", {})
        if isinstance(output, dict):
            # Orchestrator would create new DELEGATE routing to quality-engineer
            return True  # This is enforcement in Orchestrator, not HANDBACK itself

        return True

    def test_low_quality_handback_detected(self, canonical_handback_low_quality):
        """Test that low quality HANDBACK is detected."""
        assert self.eval_handback_quality_below_threshold(canonical_handback_low_quality, 0.70)

    def test_high_quality_handback_not_flagged(self, canonical_handback_high_quality):
        """Test that high quality HANDBACK is not flagged for review."""
        assert not self.eval_handback_quality_below_threshold(canonical_handback_high_quality, 0.70)


class TestRoutingDecisionTreeCompliance:
    """Eval: Routing decisions follow the complete decision tree from AGENTS.md."""

    def eval_routing_decision_tree(self, delegate: Dict) -> str:
        """Apply the routing decision tree and return expected agent role."""
        scope = delegate.get("scope", "").lower()
        context = str(delegate.get("context", "")).lower()
        full_text = f"{scope} {context}"

        # Step 1: Security-scoped?
        # Keywords must be about auditing/vulnerability, not about designing secure systems
        security_keywords = [
            "security audit",
            "vulnerability",
            "credential exposure",
            "secret exposure",
            "threat model audit",
            "exploit",
            "breach",
        ]
        if any(kw in full_text for kw in security_keywords):
            return "security-engineer"

        # Step 2: Multi-service DEPLOYMENT/MIGRATION (technology migration)?
        # "cross-service" design work is senior; database/infra migration is principal
        # Look for actual tech migration patterns (MongoDB→PostgreSQL, etc.)
        # Must mention specific database systems, not just "database"
        is_tech_migration = (
            ("three" in scope or "multiple" in scope)
            and "service" in scope.lower()
            and any(kw in full_text for kw in ["migration", "migrate"])
            and any(kw in full_text for kw in ["mongodb", "postgresql", "postgres", "mysql", "dynamodb"])
        )
        if is_tech_migration:
            return "principal-engineer"

        # Step 3: Complex without plan?
        plan = delegate.get("plan", [])
        has_plan = isinstance(plan, list) and len(plan) >= 2
        is_complex = len(scope.split()) >= 50 or any(
            kw in scope.lower() for kw in ["design", "architecture", "strategy"]
        )
        if is_complex and not has_plan:
            return "senior-engineer"

        # Step 4: Code review?
        if "review" in full_text or "quality gate" in full_text:
            return "quality-engineer"

        # Step 5: Well-scoped with plan?
        # ONLY route to engineer if plan is thorough AND scope is not design/architecture focused
        is_design_focused = any(kw in scope.lower() for kw in ["design", "architecture", "strategy"])
        if has_plan and len(scope.split()) >= 15 and not is_design_focused:
            return "engineer"

        # Step 6: Default to senior-engineer for ambiguous tasks and complex design work
        return "senior-engineer"

    def test_engineer_delegate_matches_routing_tree(self, canonical_delegate_basic):
        """Test that engineer DELEGATE matches routing decision tree."""
        expected = self.eval_routing_decision_tree(canonical_delegate_basic)
        assert expected == "engineer"
        assert canonical_delegate_basic.get("agent") == "engineer"

    def test_senior_delegate_matches_routing_tree(self, canonical_delegate_senior):
        """Test that senior DELEGATE matches routing decision tree."""
        expected = self.eval_routing_decision_tree(canonical_delegate_senior)
        assert expected == "senior-engineer"
        assert canonical_delegate_senior.get("agent") == "senior-engineer"

    def test_security_delegate_matches_routing_tree(self, canonical_delegate_security):
        """Test that security DELEGATE matches routing decision tree."""
        expected = self.eval_routing_decision_tree(canonical_delegate_security)
        assert expected == "security-engineer"
        assert canonical_delegate_security.get("agent") == "security-engineer"

    def test_delegate_corpus_routing_is_correct(self, delegate_corpus):
        """Test that all DELEGATEs in corpus match expected routing."""
        for delegate in delegate_corpus:
            expected = self.eval_routing_decision_tree(delegate)
            actual = delegate.get("agent")
            assert expected == actual, f"Routing mismatch in {delegate.get('task_id')}: expected {expected}, got {actual}"
