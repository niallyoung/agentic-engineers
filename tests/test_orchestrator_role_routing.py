"""
Regression tests for role enforcement in orchestrator task routing.

Defect: the DELEGATE role validator (DelegateValidator / validate_delegate_pre_flight)
was imported into the orchestrator but NEVER invoked during routing. As a result
TaskRouter.route_task honoured whatever explicit ``role`` a DELEGATE carried —
even an invalid role, or a role that conflicted with the task scope (e.g. a
security-scoped task tagged ``role: engineer``) — silently mis-routing work.

These tests prove routing now enforces the role validator.
"""

import pytest

from src.orchestration.agents.orchestrator import TaskRouter
from src.orchestration.agents.delegate_validator import RoleRoutingError


@pytest.fixture
def router():
    return TaskRouter()


def _security_delegate(role):
    return {
        "task_id": "2026-05-30-sec-task",
        "role": role,
        "model": "claude-opus-4.8",
        "effort": "medium",
        "scope": (
            "Remediate the TLS certificate validation vulnerability in "
            "the authentication service to prevent encryption downgrade attacks"
        ),
    }


class TestRoutingRoleEnforcement:
    def test_valid_matching_role_routes_normally(self, router):
        """A security-scoped task tagged security_engineer routes through."""
        agent_name, agent = router.route_task(_security_delegate("security_engineer"))
        assert agent_name == "security_engineer"
        assert agent is None

    def test_security_scope_with_wrong_role_is_rejected(self, router):
        """A security-scoped task tagged role=engineer must be rejected."""
        with pytest.raises(RoleRoutingError) as exc:
            router.route_task(_security_delegate("engineer"))
        # Error message should reference the routing-sanity violation.
        assert "security" in str(exc.value).lower()

    def test_invalid_role_is_rejected(self, router):
        """An unrecognised explicit role must be rejected, not silently re-routed."""
        delegate = {
            "task_id": "2026-05-30-bogus-role",
            "role": "wizard",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Add a small helper function to format dates in the utils module today",
        }
        with pytest.raises(RoleRoutingError):
            router.route_task(delegate)

    def test_benign_explicit_role_still_routes(self, router):
        """A plain well-formed engineer task is unaffected by enforcement."""
        delegate = {
            "task_id": "2026-05-30-plain-task",
            "role": "engineer",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": "Add a small helper function to format dates in the utils module today",
        }
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "engineer"

    def test_no_explicit_role_uses_decision_tree(self, router):
        """Without an explicit role, routing falls back to the decision tree."""
        delegate = {
            "task_id": "2026-05-30-no-role",
            "scope": "Implement a new caching layer for the data access module",
            "complexity": "medium",
        }
        agent_name, _ = router.route_task(delegate)
        assert agent_name in router.AGENT_NAMES
