"""
Fable-5 defensive-only routing gate (C5).

Validates the Orchestrator-side enforcement documented in
docs/SPEC.md > Security Engineer: Multi-Model Strategy:

- fable-5 may only be requested for security_engineer
- offensive-scoped work must never route to fable-5
- fable-5 runs at effort <= medium
- the DELEGATE must carry `model_constraint: defensive-only`
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
        "model_constraint": "defensive-only",
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
        assert any("offensive" in f for f in failures)

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

    def test_high_effort_rejected(self):
        failures = c5_failures(make_delegate(effort="high"))
        assert any("effort" in f for f in failures)

    def test_missing_model_constraint_rejected(self):
        delegate = make_delegate()
        del delegate["model_constraint"]
        failures = c5_failures(delegate)
        assert any("model_constraint" in f for f in failures)

    def test_opus_delegate_not_gated(self):
        assert c5_failures(make_delegate(model="claude-opus-4.8")) == []

    def test_gate_enforced_via_validate_routing_role(self):
        ok, failures = DelegateValidator.validate_routing_role(
            make_delegate(scope=OFFENSIVE_SCOPE)
        )
        assert not ok
        assert any(f.startswith("C5") for f in failures)

    def test_defensive_delegate_passes_validate_routing_role(self):
        ok, failures = DelegateValidator.validate_routing_role(make_delegate())
        assert ok, failures
