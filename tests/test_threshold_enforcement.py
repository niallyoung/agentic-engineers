"""
Tests for ThresholdEnforcer — Quality threshold enforcement.

Coverage:
  - Default thresholds by task type
  - Custom threshold configuration
  - Passing evaluations
  - Warning violations (small gap)
  - Error violations (large gap, escalation)
  - Critical violations (security tasks)
  - Compliance report generation
  - Violations summary
  - Edge cases (boundary scores, unknown task types)
"""

from __future__ import annotations

import pytest

from src.orchestration.quality.threshold_enforcement import (
    ThresholdEnforcer,
    ThresholdViolation,
    EnforcementResult,
    ViolationSeverity,
    DEFAULT_THRESHOLDS,
)


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

class TestDefaultThresholds:
    def test_code_threshold(self):
        enforcer = ThresholdEnforcer()
        assert enforcer.get_threshold("code") == 90.0

    def test_test_threshold(self):
        enforcer = ThresholdEnforcer()
        assert enforcer.get_threshold("test") == 90.0

    def test_documentation_threshold(self):
        enforcer = ThresholdEnforcer()
        assert enforcer.get_threshold("documentation") == 85.0

    def test_performance_threshold(self):
        enforcer = ThresholdEnforcer()
        assert enforcer.get_threshold("performance") == 85.0

    def test_security_threshold(self):
        enforcer = ThresholdEnforcer()
        assert enforcer.get_threshold("security") == 95.0

    def test_default_threshold_for_unknown(self):
        enforcer = ThresholdEnforcer()
        assert enforcer.get_threshold("unknown_type") == 85.0


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------

class TestCustomThresholds:
    def test_set_threshold(self):
        enforcer = ThresholdEnforcer()
        enforcer.set_threshold("code", 95.0)
        assert enforcer.get_threshold("code") == 95.0

    def test_set_threshold_invalid_raises(self):
        enforcer = ThresholdEnforcer()
        with pytest.raises(ValueError):
            enforcer.set_threshold("code", 101.0)

    def test_constructor_thresholds(self):
        enforcer = ThresholdEnforcer(thresholds={"code": 80.0})
        assert enforcer.get_threshold("code") == 80.0


# ---------------------------------------------------------------------------
# Passing evaluations
# ---------------------------------------------------------------------------

class TestPassingEvaluations:
    def test_code_at_threshold_passes(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 90.0)
        assert result.passed is True
        assert result.violations == []

    def test_code_above_threshold_passes(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 95.0)
        assert result.passed is True

    def test_security_at_threshold_passes(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("security", 95.0)
        assert result.passed is True

    def test_pass_recommendation_contains_pass(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 92.0)
        assert "PASS" in result.recommendation

    def test_compliance_pct_at_threshold(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 90.0)
        assert result.compliance_pct == pytest.approx(100.0)

    def test_compliance_pct_above_threshold_capped(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 100.0)
        assert result.compliance_pct == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Warning violations
# ---------------------------------------------------------------------------

class TestWarningViolations:
    def test_small_gap_is_warning(self):
        enforcer = ThresholdEnforcer()
        # code threshold = 90, score = 85 → gap = 5 < 10 → WARNING
        result = enforcer.evaluate("code", 85.0)
        assert not result.passed
        assert result.violations[0].severity == ViolationSeverity.WARNING

    def test_warning_does_not_escalate(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 85.0)
        assert not result.violations[0].escalate

    def test_warning_recommendation_contains_rework(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 85.0)
        assert "REWORK" in result.recommendation

    def test_violation_gap_correct(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 85.0)
        assert result.violations[0].gap == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Error violations (escalation)
# ---------------------------------------------------------------------------

class TestErrorViolations:
    def test_large_gap_is_error(self):
        enforcer = ThresholdEnforcer()
        # code threshold = 90, score = 75 → gap = 15 ≥ 10 → ERROR
        result = enforcer.evaluate("code", 75.0)
        assert result.violations[0].severity == ViolationSeverity.ERROR

    def test_error_requires_escalation(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 75.0)
        assert result.violations[0].escalate is True
        assert result.requires_escalation is True

    def test_escalation_recommendation(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 75.0)
        assert "ESCALATE" in result.recommendation


# ---------------------------------------------------------------------------
# Critical violations (security)
# ---------------------------------------------------------------------------

class TestCriticalViolations:
    def test_security_below_threshold_is_critical(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("security", 90.0)
        assert result.violations[0].severity == ViolationSeverity.CRITICAL

    def test_security_violation_always_escalates(self):
        enforcer = ThresholdEnforcer()
        # Even a small gap (94 vs 95) should escalate for security
        result = enforcer.evaluate("security", 94.0)
        assert result.violations[0].escalate is True

    def test_security_violation_message_contains_critical(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("security", 90.0)
        assert "CRITICAL" in result.violations[0].message


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_score_zero(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 0.0)
        assert not result.passed

    def test_score_hundred(self):
        enforcer = ThresholdEnforcer()
        result = enforcer.evaluate("code", 100.0)
        assert result.passed

    def test_invalid_score_raises(self):
        enforcer = ThresholdEnforcer()
        with pytest.raises(ValueError):
            enforcer.evaluate("code", -1.0)

    def test_invalid_score_above_100_raises(self):
        enforcer = ThresholdEnforcer()
        with pytest.raises(ValueError):
            enforcer.evaluate("code", 101.0)


# ---------------------------------------------------------------------------
# Compliance report
# ---------------------------------------------------------------------------

class TestComplianceReport:
    def test_empty_report(self):
        enforcer = ThresholdEnforcer()
        report = enforcer.compliance_report()
        assert report["total"] == 0
        assert report["compliance_rate"] is None

    def test_all_pass_report(self):
        enforcer = ThresholdEnforcer()
        enforcer.evaluate("code", 92.0, task_id="t1")
        enforcer.evaluate("code", 95.0, task_id="t2")
        report = enforcer.compliance_report()
        assert report["total"] == 2
        assert report["passed"] == 2
        assert report["failed"] == 0
        assert report["compliance_rate"] == pytest.approx(100.0)

    def test_mixed_report(self):
        enforcer = ThresholdEnforcer()
        enforcer.evaluate("code", 92.0, task_id="t1")
        enforcer.evaluate("code", 80.0, task_id="t2")
        report = enforcer.compliance_report()
        assert report["passed"] == 1
        assert report["failed"] == 1
        assert report["compliance_rate"] == pytest.approx(50.0)

    def test_escalations_counted(self):
        enforcer = ThresholdEnforcer()
        enforcer.evaluate("code", 75.0, task_id="t1")  # gap=15, escalates
        report = enforcer.compliance_report()
        assert report["escalations"] == 1

    def test_report_includes_history(self):
        enforcer = ThresholdEnforcer()
        enforcer.evaluate("code", 92.0, task_id="t1")
        report = enforcer.compliance_report()
        assert len(report["history"]) == 1
        assert report["history"][0]["task_id"] == "t1"

    def test_violations_summary(self):
        enforcer = ThresholdEnforcer()
        enforcer.evaluate("code", 80.0, task_id="t1")
        summary = enforcer.violations_summary()
        assert len(summary) == 1
        assert summary[0]["task_id"] == "t1"
        assert summary[0]["task_type"] == "code"
