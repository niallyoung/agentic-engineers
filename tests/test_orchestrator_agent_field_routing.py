"""
Regression tests for C1: canonical `agent` field routing.

Defect: TaskRouter.route_task() gated Priority 1 routing on `"role" in
delegate` ONLY. It never read the canonical `agent` field written by
queue_ops.enqueue() (hyphenated, e.g. "security-engineer"). queue_ops.py
explicitly REJECTS `role` as a legacy field at enqueue time, so a properly
enqueued canonical DELEGATE for security-engineer carried `agent:
security-engineer` and no `role` key at all.

Because Priority 1 never fired, routing fell through to the Priority 2
keyword heuristics, which do not recognise `agent`/hyphenated names and
returned ("engineer", None) by default — silently routing security-scoped
work to Haiku instead of fable-5, and skipping the C5 fable-5
restricted-scope gate (DelegateValidator._check_fable5_gate) entirely,
since that gate is only reached via validate_routing_role() inside
Priority 1.

These tests prove:
  1. `agent: security-engineer` (canonical, hyphenated, no `role` key)
     routes to security_engineer, which resolves to fable-5.
  2. `agent: principal-engineer` routes to principal_engineer (opus-5).
  3. `agent: engineer` routes to engineer (haiku).
  4. Hyphens are normalized to underscores so AGENT_NAMES/VALID_ROLES/
     ModelResolver agree.
  5. `role` still works as a backwards-compatible fallback when `agent`
     is absent.
  6. An invalid `agent` value is rejected (not silently re-routed), same
     as the existing `role` enforcement.
"""

import pytest

from src.orchestration.agents.orchestrator import TaskRouter
from src.orchestration.agents.delegate_validator import RoleRoutingError
from src.orchestration.models.canonical_resolver import ModelResolver


@pytest.fixture
def router():
    return TaskRouter()


@pytest.fixture
def resolver():
    return ModelResolver.from_defaults()


def _canonical_security_delegate():
    """A properly enqueued canonical DELEGATE: `agent` only, no `role`.

    This is exactly the shape queue_ops.enqueue() accepts and writes to
    disk — reproducing the real production bug scenario, not just a
    direct-call unit-test shape.
    """
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-08-07-fix-tls-vuln",
        "agent": "security-engineer",
        "model": "claude-fable-5",
        "effort": "max",
        "scope": (
            "Remediate the TLS certificate validation vulnerability in "
            "the authentication service to prevent encryption downgrade attacks"
        ),
    }


class TestCanonicalAgentFieldRouting:
    def test_agent_security_engineer_routes_to_fable5(self, router, resolver):
        """C1 regression: agent: security-engineer must route to
        security_engineer, and security_engineer must resolve to fable-5 —
        proving the C5 defensive-only gate is now reachable."""
        agent_name, agent = router.route_task(_canonical_security_delegate())
        assert agent_name == "security_engineer"
        assert agent is None
        assert resolver.resolve(agent_name) == "claude-fable-5"

    def test_agent_principal_engineer_routes_to_opus5(self, router, resolver):
        delegate = {
            "task_id": "2026-08-07-cross-service-redesign",
            "agent": "principal-engineer",
            "model": "claude-opus-5",
            "effort": "high",
            "scope": "Design the cross-service architecture for the new billing pipeline",
        }
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "principal_engineer"
        assert agent is None
        assert resolver.resolve(agent_name) == "claude-opus-5"

    def test_agent_engineer_routes_to_haiku(self, router, resolver):
        delegate = {
            "task_id": "2026-08-07-small-fix",
            "agent": "engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Add a small helper function to format dates in the utils module today",
        }
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "engineer"
        assert agent is None
        assert resolver.resolve(agent_name) == "claude-haiku-4.5"

    def test_hyphens_normalized_to_underscores_once(self, router):
        """agent: "quality-engineer" (hyphenated wire format) must resolve
        identically to the underscored internal form."""
        delegate = {
            "task_id": "2026-08-07-review-task",
            "agent": "quality-engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Review the implementation of the new caching layer for correctness",
            "is_code_review": True,
        }
        agent_name, _ = router.route_task(delegate)
        assert agent_name == "quality_engineer"
        assert "-" not in agent_name

    def test_role_still_works_as_fallback_when_agent_absent(self, router):
        """Backwards compatibility: legacy `role` field alone still routes."""
        delegate = {
            "task_id": "2026-08-07-legacy-role-task",
            "role": "engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Add a small helper function to format dates in the utils module today",
        }
        agent_name, _ = router.route_task(delegate)
        assert agent_name == "engineer"

    def test_agent_field_takes_priority_over_role(self, router):
        """When both are present, the canonical `agent` field wins."""
        delegate = {
            "task_id": "2026-08-07-both-fields-task",
            "agent": "security-engineer",
            "role": "security_engineer",
            "model": "claude-fable-5",
            "effort": "max",
            "scope": (
                "Remediate the TLS certificate validation vulnerability in "
                "the authentication service to prevent encryption downgrade attacks"
            ),
        }
        agent_name, _ = router.route_task(delegate)
        assert agent_name == "security_engineer"

    def test_invalid_agent_value_is_rejected(self, router):
        """An unrecognised `agent` value must be rejected, not silently
        re-routed to the Priority 2 keyword heuristics."""
        delegate = {
            "task_id": "2026-08-07-bogus-agent",
            "agent": "wizard-engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Add a small helper function to format dates in the utils module today",
        }
        with pytest.raises(RoleRoutingError):
            router.route_task(delegate)

    def test_security_scope_with_wrong_agent_is_rejected(self, router):
        """C2 gate still enforced through the `agent` field: a
        security-scoped task mis-tagged agent: engineer must be rejected."""
        delegate = {
            "task_id": "2026-08-07-sec-wrong-agent",
            "agent": "engineer",
            "model": "claude-haiku-4.5",
            "effort": "medium",
            "scope": (
                "Remediate the TLS certificate validation vulnerability in "
                "the authentication service to prevent encryption downgrade attacks"
            ),
        }
        with pytest.raises(RoleRoutingError) as exc:
            router.route_task(delegate)
        assert "security" in str(exc.value).lower()
