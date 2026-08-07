"""
Fable-5 restricted-scope gate (C5).

Validates the Orchestrator-side enforcement documented in
docs/SPEC.md > Security Engineer: Multi-Model Strategy:

- fable-5 is the unconditional default for security_engineer
- offensive-scoped work must never route to fable-5 (C5 gate enforcement)
- fable-5 runs at effort <= max
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "orchestration" / "agents"))

from delegate_validator import DelegateValidator  # noqa: E402


DEFENSIVE_SCOPE = (
    "Assess OWASP Top 10 vulnerability exposure in the user auth flow "
    "and recommend concrete remediation patches for each finding"
)
OFFENSIVE_SCOPE = (
    "Develop a working exploit and proof-of-concept attack for the auth "
    "bypass vulnerability to demonstrate red team attack capability"
)


def make_delegate(**overrides):
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": "2026-06-10-fable5-gate-test",
        "role": "security_engineer",
        "model": "claude-fable-5",
        "effort": "medium",
        "scope": DEFENSIVE_SCOPE,
    }
    delegate.update(overrides)
    return delegate


def c5_failures(delegate):
    validator = DelegateValidator()
    return [f for f in validator._check_group_c(delegate) if f.startswith("C5")]


class TestFable5DefensiveGate:
    def test_defensive_fable5_delegate_passes(self):
        assert c5_failures(make_delegate()) == []

    def test_offensive_scope_rejected(self):
        failures = c5_failures(make_delegate(scope=OFFENSIVE_SCOPE))
        assert any("restricted-topic" in f and "escalate" in f for f in failures)
        # The framework never re-routes restricted work to another model
        assert not any("must route" in f for f in failures)

    @pytest.mark.parametrize(
        "keyword",
        ["exploit", "attack automation", "offensive", "red team",
         "proof-of-concept attack", "jailbreak", "prompt injection",
         "ransomware", "data exfiltration", "detection evasion", "malware"],
    )
    def test_each_offensive_keyword_rejected(self, keyword):
        scope = f"{DEFENSIVE_SCOPE} including {keyword} work"
        assert c5_failures(make_delegate(scope=scope))

    def test_non_security_role_rejected(self):
        failures = c5_failures(make_delegate(role="senior_engineer"))
        assert any("security_engineer" in f for f in failures)

    def test_high_effort_allowed(self):
        """Fable-5 now supports any effort level for security_engineer."""
        failures = c5_failures(make_delegate(effort="high"))
        assert failures == []

    def test_defensive_scope_without_constraint_passes(self):
        """model_constraint is no longer required; fable-5 is unconditional."""
        delegate = make_delegate()
        # model_constraint should not be present in base delegate
        assert "model_constraint" not in delegate
        failures = c5_failures(delegate)
        assert failures == []

    def test_other_models_for_other_roles_not_gated(self):
        """The C5 gate only applies to fable-5 for security_engineer."""
        other_role_delegate = make_delegate(role="principal_engineer", model="claude-opus-5")
        assert c5_failures(other_role_delegate) == []

    def test_gate_enforced_via_validate_routing_role(self):
        ok, failures = DelegateValidator.validate_routing_role(
            make_delegate(scope=OFFENSIVE_SCOPE)
        )
        assert not ok
        assert any(f.startswith("C5") for f in failures)

    def test_defensive_delegate_passes_validate_routing_role(self):
        ok, failures = DelegateValidator.validate_routing_role(make_delegate())
        assert ok, failures
