"""
Tests for implementations.py — Agent stubs for all 13 agent roles.

Covers: create_agent factory, each agent class's do_work() and execute(),
        routing logic, HANDBACK structure, validation, error paths.
"""

import pytest
from src.orchestration.agents.implementations import (
    GeneralOrchestrator,
    EngineerAgent,
    SeniorEngineerAgent,
    LeadEngineerAgent,
    PrincipalEngineerAgent,
    QualityEngineerAgent,
    ModelEngineerAgent,
    SecurityEngineerAgent,
    SecurityAgentQG,
    TestingAgent,
    MetricsAgent,
    HealingAgent,
    SpecEngineerAgent,
    QualityGateOrchestrator,
    create_agent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_delegate(role: str, extra: dict = None) -> dict:
    """Build a minimal valid DELEGATE block for a given role."""
    block = {
        "task_id": "2025-01-01-test-task-abc",
        "role": role,
        "model": "claude-haiku-4.5",
        "effort": "medium",
        "scope": "Execute test task for quality validation purposes",
    }
    if extra:
        block.update(extra)
    return block


# ---------------------------------------------------------------------------
# create_agent factory
# ---------------------------------------------------------------------------

class TestCreateAgentFactory:
    @pytest.mark.parametrize("role", [
        "orchestrator", "engineer", "senior_engineer", "lead_engineer",
        "principal_engineer", "quality_engineer", "model_engineer",
        "security_engineer", "security_agent", "testing_agent",
        "metrics_agent", "healing_agent", "spec_engineer",
        "quality_gate_orchestrator",
    ])
    def test_create_agent_returns_agent_instance(self, role):
        """create_agent returns an instance for every known role."""
        agent = create_agent(role)
        assert agent is not None

    def test_create_agent_unknown_role_raises_value_error(self):
        """create_agent raises ValueError for an unknown role."""
        with pytest.raises(ValueError, match="Unknown agent role"):
            create_agent("wizard_engineer")

    def test_create_agent_orchestrator_type(self):
        assert isinstance(create_agent("orchestrator"), GeneralOrchestrator)

    def test_create_agent_engineer_type(self):
        assert isinstance(create_agent("engineer"), EngineerAgent)

    def test_create_agent_quality_gate_orchestrator_type(self):
        assert isinstance(create_agent("quality_gate_orchestrator"), QualityGateOrchestrator)


# ---------------------------------------------------------------------------
# HANDBACK structure contract (all agents)
# ---------------------------------------------------------------------------

class TestHandbackStructureContract:
    """Every agent must return a HANDBACK with standard required keys."""

    REQUIRED_KEYS = {"handoff_type", "task_id", "timestamp", "status", "severity"}

    @pytest.mark.parametrize("role,extra", [
        ("orchestrator", {"complexity": "medium", "has_plan": False, "is_security_scoped": False}),
        ("engineer", {"plan": ["Step 1", "test step"], "success_criteria": ["Tests pass"]}),
        ("senior_engineer", {}),
        ("lead_engineer", {}),
        ("principal_engineer", {}),
        ("quality_engineer", {"quality_score": 90}),
        ("model_engineer", {"quality_score": 90}),
        ("security_engineer", {}),
        ("security_agent", {}),
        ("testing_agent", {}),
        ("metrics_agent", {}),
        ("healing_agent", {}),
        ("spec_engineer", {}),
        ("quality_gate_orchestrator", {}),
    ])
    def test_handback_has_required_keys(self, role, extra):
        """All agents must return a HANDBACK with required keys."""
        agent = create_agent(role)
        handback = agent.execute(_make_delegate(role, extra))
        missing = self.REQUIRED_KEYS - set(handback.keys())
        assert missing == set(), f"{role}: HANDBACK missing keys: {missing}"

    @pytest.mark.parametrize("role,extra", [
        ("engineer", {"plan": ["Step 1", "test step"], "success_criteria": ["Tests pass"]}),
        ("senior_engineer", {}),
        ("quality_engineer", {"quality_score": 90}),
    ])
    def test_handback_status_is_pass_on_success(self, role, extra):
        """Successful execution produces status=PASS."""
        agent = create_agent(role)
        handback = agent.execute(_make_delegate(role, extra))
        assert handback["status"] == "PASS"

    def test_handback_task_id_matches_delegate(self):
        """HANDBACK task_id must match the DELEGATE task_id."""
        agent = create_agent("senior_engineer")
        delegate = _make_delegate("senior_engineer")
        handback = agent.execute(delegate)
        assert handback["task_id"] == delegate["task_id"]


# ---------------------------------------------------------------------------
# GeneralOrchestrator
# ---------------------------------------------------------------------------

class TestGeneralOrchestrator:
    def test_security_scoped_routes_to_security_engineer(self):
        """Security-scoped tasks route to security_engineer."""
        agent = create_agent("orchestrator")
        delegate = _make_delegate("orchestrator", {
            "complexity": "medium",
            "has_plan": False,
            "is_security_scoped": True,
        })
        handback = agent.execute(delegate)
        assert handback["routing_decision"] == "security_engineer"

    def test_high_complexity_no_plan_routes_to_senior_engineer(self):
        """High complexity without plan routes to senior_engineer."""
        agent = create_agent("orchestrator")
        delegate = _make_delegate("orchestrator", {
            "complexity": "high",
            "has_plan": False,
            "is_security_scoped": False,
        })
        handback = agent.execute(delegate)
        assert handback["routing_decision"] == "senior_engineer"

    def test_has_plan_routes_to_engineer(self):
        """Task with plan routes to engineer."""
        agent = create_agent("orchestrator")
        delegate = _make_delegate("orchestrator", {
            "complexity": "medium",
            "has_plan": True,
            "is_security_scoped": False,
        })
        handback = agent.execute(delegate)
        assert handback["routing_decision"] == "engineer"

    def test_no_plan_no_security_no_high_routes_to_lead(self):
        """Standard task without plan routes to lead_engineer."""
        agent = create_agent("orchestrator")
        delegate = _make_delegate("orchestrator", {
            "complexity": "medium",
            "has_plan": False,
            "is_security_scoped": False,
        })
        handback = agent.execute(delegate)
        assert handback["routing_decision"] == "lead_engineer"

    def test_confidence_is_numeric(self):
        """Routing confidence is a float between 0 and 1."""
        agent = create_agent("orchestrator")
        delegate = _make_delegate("orchestrator", {
            "complexity": "medium",
            "has_plan": True,
            "is_security_scoped": False,
        })
        handback = agent.execute(delegate)
        assert 0.0 <= handback["confidence"] <= 1.0

    def test_security_overrides_plan(self):
        """Security flag overrides has_plan in routing."""
        agent = create_agent("orchestrator")
        delegate = _make_delegate("orchestrator", {
            "complexity": "medium",
            "has_plan": True,
            "is_security_scoped": True,
        })
        handback = agent.execute(delegate)
        assert handback["routing_decision"] == "security_engineer"


# ---------------------------------------------------------------------------
# EngineerAgent
# ---------------------------------------------------------------------------

class TestEngineerAgent:
    def test_executes_all_plan_steps(self):
        """Engineer executes all steps in the plan."""
        plan = ["Analyse code", "Implement fix", "Write tests"]
        agent = create_agent("engineer")
        delegate = _make_delegate("engineer", {"plan": plan, "success_criteria": ["Tests pass"]})
        handback = agent.execute(delegate)
        assert len(handback["execution_results"]) == len(plan)

    def test_each_step_has_status(self):
        """Each execution result includes a step status."""
        plan = ["Analyse code", "Write tests", "Validate output"]
        agent = create_agent("engineer")
        delegate = _make_delegate("engineer", {"plan": plan, "success_criteria": []})
        handback = agent.execute(delegate)
        for step_result in handback["execution_results"]:
            assert "status" in step_result

    def test_missing_plan_escalates(self):
        """EngineerAgent escalates when plan is missing from DELEGATE."""
        agent = create_agent("engineer")
        delegate = _make_delegate("engineer")  # no plan key
        handback = agent.execute(delegate)
        assert handback["status"] == "ESCALATE"

    def test_quality_score_in_handback(self):
        """EngineerAgent includes quality_score in HANDBACK."""
        agent = create_agent("engineer")
        delegate = _make_delegate("engineer", {
            "plan": ["Implement feature", "test coverage"],
            "success_criteria": ["All tests pass"],
        })
        handback = agent.execute(delegate)
        assert "quality_score" in handback
        assert 0 <= handback["quality_score"] <= 100

    def test_high_quality_score_when_all_criteria_pass(self):
        """Quality score ≥ 80 when all success criteria pass."""
        agent = create_agent("engineer")
        delegate = _make_delegate("engineer", {
            "plan": ["Step A", "test step B"],
            "success_criteria": ["All tests pass"],
        })
        handback = agent.execute(delegate)
        assert handback["quality_score"] >= 80


# ---------------------------------------------------------------------------
# SeniorEngineerAgent
# ---------------------------------------------------------------------------

class TestSeniorEngineerAgent:
    def test_returns_plan(self):
        """SeniorEngineerAgent returns a non-empty plan."""
        agent = create_agent("senior_engineer")
        handback = agent.execute(_make_delegate("senior_engineer"))
        assert "plan" in handback
        assert len(handback["plan"]) > 0

    def test_returns_root_cause_analysis(self):
        """SeniorEngineerAgent returns root cause analysis."""
        agent = create_agent("senior_engineer")
        handback = agent.execute(_make_delegate("senior_engineer"))
        assert "root_cause_analysis" in handback

    def test_returns_deliverables(self):
        agent = create_agent("senior_engineer")
        handback = agent.execute(_make_delegate("senior_engineer"))
        assert "deliverables" in handback
        assert isinstance(handback["deliverables"], list)


# ---------------------------------------------------------------------------
# LeadEngineerAgent
# ---------------------------------------------------------------------------

class TestLeadEngineerAgent:
    def test_returns_review_checklist(self):
        """LeadEngineerAgent returns 8-point review checklist."""
        agent = create_agent("lead_engineer")
        handback = agent.execute(_make_delegate("lead_engineer"))
        assert "review_checklist" in handback
        assert len(handback["review_checklist"]) == 8

    def test_quality_score_is_100_when_all_pass(self):
        """Quality score is 100 when all 8 checklist items pass."""
        agent = create_agent("lead_engineer")
        handback = agent.execute(_make_delegate("lead_engineer"))
        assert handback["quality_score"] == 100.0

    def test_decision_is_approve(self):
        """LeadEngineerAgent decision is APPROVE for a clean handback."""
        agent = create_agent("lead_engineer")
        handback = agent.execute(_make_delegate("lead_engineer"))
        assert handback["decision"] == "APPROVE"


# ---------------------------------------------------------------------------
# PrincipalEngineerAgent
# ---------------------------------------------------------------------------

class TestPrincipalEngineerAgent:
    def test_returns_options_analyzed(self):
        agent = create_agent("principal_engineer")
        handback = agent.execute(_make_delegate("principal_engineer"))
        assert handback["options_analyzed"] == 2

    def test_returns_recommended_option(self):
        agent = create_agent("principal_engineer")
        handback = agent.execute(_make_delegate("principal_engineer"))
        assert "recommended_option" in handback

    def test_returns_implementation_roadmap(self):
        agent = create_agent("principal_engineer")
        handback = agent.execute(_make_delegate("principal_engineer"))
        assert "implementation_roadmap" in handback
        assert isinstance(handback["implementation_roadmap"], list)


# ---------------------------------------------------------------------------
# QualityEngineerAgent
# ---------------------------------------------------------------------------

class TestQualityEngineerAgent:
    def test_returns_quality_score(self):
        agent = create_agent("quality_engineer")
        handback = agent.execute(_make_delegate("quality_engineer", {"quality_score": 90}))
        assert "quality_score" in handback

    def test_production_ready_is_true(self):
        agent = create_agent("quality_engineer")
        handback = agent.execute(_make_delegate("quality_engineer", {"quality_score": 90}))
        assert handback["production_ready"] is True

    def test_returns_test_coverage(self):
        agent = create_agent("quality_engineer")
        handback = agent.execute(_make_delegate("quality_engineer", {"quality_score": 90}))
        assert "test_coverage" in handback


# ---------------------------------------------------------------------------
# ModelEngineerAgent
# ---------------------------------------------------------------------------

class TestModelEngineerAgent:
    def test_returns_rank_1_model(self):
        agent = create_agent("model_engineer")
        handback = agent.execute(_make_delegate("model_engineer", {"quality_score": 90}))
        assert "rank_1_model" in handback

    def test_high_quality_score_increases_confidence(self):
        """Quality score > 85 increases confidence above baseline."""
        agent_high = create_agent("model_engineer")
        delegate_high = _make_delegate("model_engineer", {"quality_score": 90})
        handback_high = agent_high.execute(delegate_high)

        agent_low = create_agent("model_engineer")
        delegate_low = _make_delegate("model_engineer", {"quality_score": 50})
        handback_low = agent_low.execute(delegate_low)

        assert handback_high["confidence"] > handback_low["confidence"]

    def test_confidence_bounded_between_0_and_1(self):
        """Confidence is always in [0, 1]."""
        for score in [0, 50, 85, 100]:
            agent = create_agent("model_engineer")
            delegate = _make_delegate("model_engineer", {"quality_score": score})
            handback = agent.execute(delegate)
            assert 0.0 <= handback["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# SecurityEngineerAgent
# ---------------------------------------------------------------------------

class TestSecurityEngineerAgent:
    def test_returns_security_score(self):
        agent = create_agent("security_engineer")
        handback = agent.execute(_make_delegate("security_engineer"))
        assert "security_score" in handback

    def test_no_hardcoded_credentials(self):
        agent = create_agent("security_engineer")
        handback = agent.execute(_make_delegate("security_engineer"))
        assert handback["hardcoded_credentials"] is False


# ---------------------------------------------------------------------------
# Quality Gate Sub-Agents
# ---------------------------------------------------------------------------

class TestQualityGateSubAgents:
    @pytest.mark.parametrize("role", [
        "security_agent", "testing_agent", "metrics_agent",
        "healing_agent", "spec_engineer",
    ])
    def test_subagent_returns_pass_status(self, role):
        """All QG sub-agents return status=PASS in normal conditions."""
        agent = create_agent(role)
        handback = agent.execute(_make_delegate(role))
        assert handback["status"] == "PASS"

    def test_testing_agent_returns_coverage(self):
        agent = create_agent("testing_agent")
        handback = agent.execute(_make_delegate("testing_agent"))
        assert "coverage" in handback
        assert handback["coverage"] > 0

    def test_spec_engineer_returns_compliance_score(self):
        agent = create_agent("spec_engineer")
        handback = agent.execute(_make_delegate("spec_engineer"))
        assert "compliance_score" in handback


# ---------------------------------------------------------------------------
# QualityGateOrchestrator
# ---------------------------------------------------------------------------

class TestQualityGateOrchestrator:
    def test_returns_proceed_when_all_pass(self):
        """QG orchestrator returns PROCEED when all sub-agents pass."""
        agent = create_agent("quality_gate_orchestrator")
        handback = agent.execute(_make_delegate("quality_gate_orchestrator"))
        assert handback["decision"] == "PROCEED"

    def test_returns_5_agent_audit_trail(self):
        """QG orchestrator includes audit trail with 5 sub-agent results."""
        agent = create_agent("quality_gate_orchestrator")
        handback = agent.execute(_make_delegate("quality_gate_orchestrator"))
        assert len(handback["audit_trail"]) == 5

    def test_agents_passed_count(self):
        """QG orchestrator reports 5 agents passed."""
        agent = create_agent("quality_gate_orchestrator")
        handback = agent.execute(_make_delegate("quality_gate_orchestrator"))
        assert handback["agents_passed"] == 5


# ---------------------------------------------------------------------------
# Input validation (missing required fields)
# ---------------------------------------------------------------------------

class TestInputValidation:
    @pytest.mark.parametrize("missing_field", ["task_id", "role", "model", "effort", "scope"])
    def test_missing_required_field_escalates(self, missing_field):
        """Agent escalates when any required DELEGATE field is missing."""
        delegate = _make_delegate("senior_engineer")
        del delegate[missing_field]
        agent = create_agent("senior_engineer")
        handback = agent.execute(delegate)
        assert handback["status"] == "ESCALATE"

    def test_escalated_handback_has_error_key(self):
        """Escalated HANDBACK includes an 'error' key."""
        delegate = _make_delegate("senior_engineer")
        del delegate["task_id"]
        agent = create_agent("senior_engineer")
        handback = agent.execute(delegate)
        assert "error" in handback
