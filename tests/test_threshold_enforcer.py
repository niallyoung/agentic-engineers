"""
Tests for ThresholdEnforcer - quality threshold enforcement.
"""

import pytest
from src.orchestration.quality.threshold_enforcer import (
    ThresholdEnforcer,
    ThresholdResult,
    EnforcementAction,
    TaskType,
    DegradationAlert,
    QUALITY_THRESHOLDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def enforcer():
    return ThresholdEnforcer()


# ---------------------------------------------------------------------------
# Basic enforcement tests
# ---------------------------------------------------------------------------

class TestThresholdEnforcement:
    def test_high_quality_proceeds(self, enforcer):
        result = enforcer.enforce(quality_score=90, task_type=TaskType.FEATURE)
        assert result.action == EnforcementAction.PROCEED

    def test_perfect_quality_proceeds(self, enforcer):
        result = enforcer.enforce(quality_score=100, task_type=TaskType.FEATURE)
        assert result.action == EnforcementAction.PROCEED

    def test_low_quality_escalates(self, enforcer):
        result = enforcer.enforce(quality_score=40, task_type=TaskType.FEATURE)
        assert result.action == EnforcementAction.ESCALATE

    def test_mid_quality_triggers_rework(self, enforcer):
        # Feature: proceed=85, manual=75, rework=65, escalate<65
        result = enforcer.enforce(quality_score=70, task_type=TaskType.FEATURE)
        assert result.action in (EnforcementAction.REWORK, EnforcementAction.MANUAL_REVIEW)

    def test_manual_review_band(self, enforcer):
        # Feature: manual_review band is [75, 85)
        result = enforcer.enforce(quality_score=78, task_type=TaskType.FEATURE)
        assert result.action == EnforcementAction.MANUAL_REVIEW

    def test_critical_issues_force_escalation(self, enforcer):
        result = enforcer.enforce(
            quality_score=95,
            task_type=TaskType.FEATURE,
            has_critical_issues=True,
        )
        assert result.action == EnforcementAction.ESCALATE

    def test_rework_max_retries_escalates(self, enforcer):
        # In rework band but max retries reached
        result = enforcer.enforce(
            quality_score=70,
            task_type=TaskType.FEATURE,
            retry_count=2,
            max_retries=2,
        )
        assert result.action == EnforcementAction.ESCALATE

    def test_rework_allows_retry(self, enforcer):
        result = enforcer.enforce(
            quality_score=70,
            task_type=TaskType.FEATURE,
            retry_count=0,
            max_retries=2,
        )
        assert result.action == EnforcementAction.REWORK

    def test_security_has_higher_threshold(self, enforcer):
        # Security proceed_min=95, feature proceed_min=85
        # Score of 88 should proceed for feature but not security
        feature_result = enforcer.enforce(quality_score=88, task_type=TaskType.FEATURE)
        security_result = enforcer.enforce(quality_score=88, task_type=TaskType.SECURITY)
        assert feature_result.action == EnforcementAction.PROCEED
        assert security_result.action != EnforcementAction.PROCEED

    def test_documentation_has_lower_threshold(self, enforcer):
        # Documentation proceed_min=75
        result = enforcer.enforce(quality_score=76, task_type=TaskType.DOCUMENTATION)
        assert result.action == EnforcementAction.PROCEED

    def test_default_task_type(self, enforcer):
        result = enforcer.enforce(quality_score=85)
        assert result.action in EnforcementAction.__members__.values()


# ---------------------------------------------------------------------------
# ThresholdResult structure tests
# ---------------------------------------------------------------------------

class TestThresholdResult:
    def test_result_has_required_fields(self, enforcer):
        result = enforcer.enforce(quality_score=85, task_type=TaskType.FEATURE)
        assert isinstance(result, ThresholdResult)
        assert result.action
        assert result.quality_score == 85
        assert result.task_type == TaskType.FEATURE
        assert result.threshold_used > 0
        assert result.rationale
        assert result.timestamp

    def test_should_proceed_property(self, enforcer):
        result = enforcer.enforce(quality_score=90, task_type=TaskType.FEATURE)
        assert result.should_proceed is True

    def test_should_not_proceed_for_rework(self, enforcer):
        result = enforcer.enforce(quality_score=70, task_type=TaskType.FEATURE)
        assert result.should_proceed is False

    def test_requires_escalation_property(self, enforcer):
        result = enforcer.enforce(quality_score=40, task_type=TaskType.FEATURE)
        assert result.requires_escalation is True

    def test_to_dict(self, enforcer):
        result = enforcer.enforce(quality_score=85, task_type=TaskType.FEATURE)
        d = result.to_dict()
        assert "action" in d
        assert "quality_score" in d
        assert "task_type" in d
        assert "rationale" in d

    def test_escalation_target_set_for_escalation(self, enforcer):
        result = enforcer.enforce(quality_score=40, task_type=TaskType.FEATURE)
        assert result.escalation_target is not None

    def test_rework_guidance_set_for_rework(self, enforcer):
        result = enforcer.enforce(quality_score=68, task_type=TaskType.FEATURE)
        if result.action == EnforcementAction.REWORK:
            assert result.rework_guidance is not None


# ---------------------------------------------------------------------------
# Task type inference tests
# ---------------------------------------------------------------------------

class TestTaskTypeInference:
    def test_infer_security_from_scope(self, enforcer):
        delegate = {"scope": "fix security vulnerability in auth module"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.SECURITY

    def test_infer_architecture_from_scope(self, enforcer):
        delegate = {"scope": "design new cross-service architecture"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.ARCHITECTURE

    def test_infer_testing_from_scope(self, enforcer):
        delegate = {"scope": "add test coverage for payment module"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.TESTING

    def test_infer_bugfix_from_scope(self, enforcer):
        delegate = {"scope": "fix the bug in user registration"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.BUGFIX

    def test_infer_refactor_from_scope(self, enforcer):
        delegate = {"scope": "refactor the payment service"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.REFACTOR

    def test_infer_feature_from_scope(self, enforcer):
        delegate = {"scope": "implement new user dashboard feature"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.FEATURE

    def test_infer_default_for_unknown(self, enforcer):
        delegate = {"scope": "do a general update to the codebase"}
        task_type = enforcer.infer_task_type(delegate)
        assert task_type == TaskType.DEFAULT


# ---------------------------------------------------------------------------
# Quality degradation detection tests
# ---------------------------------------------------------------------------

class TestDegradationDetection:
    def test_no_degradation_with_insufficient_data(self, enforcer):
        enforcer._record_quality("engineer", "feature", 85)
        enforcer._record_quality("engineer", "feature", 80)
        alert = enforcer.check_degradation("engineer", "feature")
        assert alert is None  # only 2 data points

    def test_degradation_detected(self, enforcer):
        # First half: high quality
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 90)
        # Second half: low quality
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 70)
        alert = enforcer.check_degradation("engineer", "feature")
        assert alert is not None
        assert alert.drop >= 10

    def test_no_degradation_stable_quality(self, enforcer):
        for _ in range(8):
            enforcer._record_quality("engineer", "feature", 85)
        alert = enforcer.check_degradation("engineer", "feature")
        assert alert is None

    def test_critical_degradation_level(self, enforcer):
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 95)
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 65)
        alert = enforcer.check_degradation("engineer", "feature")
        assert alert is not None
        assert alert.alert_level == "CRITICAL"

    def test_warning_degradation_level(self, enforcer):
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 85)
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 73)
        alert = enforcer.check_degradation("engineer", "feature")
        # Drop of 12 → WARNING
        if alert:
            assert alert.alert_level in ("WARNING", "CRITICAL")

    def test_all_alerts_accumulates(self, enforcer):
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 90)
        for _ in range(4):
            enforcer._record_quality("engineer", "feature", 70)
        enforcer.check_degradation("engineer", "feature")
        assert len(enforcer.all_alerts()) >= 1

    def test_quality_history_returns_list(self, enforcer):
        enforcer._record_quality("engineer", "feature", 85)
        history = enforcer.quality_history("engineer", "feature")
        assert history == [85]

    def test_get_threshold_returns_tuple(self, enforcer):
        thresholds = enforcer.get_threshold(TaskType.FEATURE)
        assert isinstance(thresholds, tuple)
        assert len(thresholds) == 4

    def test_custom_thresholds(self):
        custom = {TaskType.FEATURE: (95, 90, 80, 80)}
        enforcer = ThresholdEnforcer(custom_thresholds=custom)
        # Score of 92 should not proceed with custom threshold of 95
        result = enforcer.enforce(quality_score=92, task_type=TaskType.FEATURE)
        assert result.action != EnforcementAction.PROCEED
