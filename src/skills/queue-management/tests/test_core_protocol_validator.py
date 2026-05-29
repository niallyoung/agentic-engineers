"""
Tests for Phase 3 Core Protocol Validator.

Tests cover:
  ✅ Core delegate validation (valid minimal delegate passes)
  ✅ Extensions do NOT affect core validation (unknown extensions allowed)
  ✅ task_id format validation (valid/invalid patterns)
  ✅ skill validation (exists/not-exists)
  ✅ agent validation (valid/invalid)
  ✅ scope word count validation (>=15 words)
  ✅ success_criteria validation (non-empty array)
  ✅ plan validation (>=2 steps, >=3 words each)
  ✅ context validation (>=20 words string or non-empty list)
  ✅ Core handback validation (valid minimal handback passes)
  ✅ Handback status enum validation
  ✅ Handback metrics validation (quality 0-1, tokens int, cost/duration float)
  ✅ Extension validation: effort enum check
  ✅ Extension validation: priority range 1-10
  ✅ Extension validation: model is string (any value allowed)
  ✅ Extension validation: budget numeric
  ✅ Backward compatibility: old-style delegates with effort/model still pass core
  ✅ Performance: core validation <50ms
  ✅ Performance: extension validation <10ms
  ✅ Extensions loose: unknown fields ignored by core validator
"""

import sys
import time
from pathlib import Path
import pytest

# Path setup
REPO_ROOT = Path(__file__).resolve().parents[3]
QM_SCRIPTS = REPO_ROOT / "skills" / "queue-management" / "scripts"
if str(QM_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(QM_SCRIPTS))

from core_protocol_validator import CoreProtocolValidator, ExtensionValidator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_delegate():
    """Valid minimal delegate with all 7 core fields."""
    return {
        "task_id": "my-test-task-001",
        "skill": "queue-management",
        "agent": "engineer",
        "scope": "Review the authentication module for security issues and test coverage gaps in the OAuth2 flow implementation",
        "success_criteria": [
            "No high-severity security issues found",
            "Test coverage >=85%"
        ],
        "plan": [
            "Read auth module source code",
            "Identify security vulnerabilities",
            "Check test coverage gaps"
        ],
        "context": "The auth module handles OAuth2 login token refresh and session management. Recent changes added a new provider integration that needs security review"
    }


@pytest.fixture
def valid_handback():
    """Valid minimal handback with all 4 core fields."""
    return {
        "task_id": "my-test-task-001",
        "status": "success",
        "output": {
            "findings": [],
            "recommendations": []
        },
        "metrics": {
            "quality": 0.95,
            "tokens": 4500,
            "cost": 0.023,
            "duration_seconds": 45.2
        }
    }


@pytest.fixture
def core_validator():
    """Core protocol validator instance."""
    return CoreProtocolValidator()


@pytest.fixture
def ext_validator():
    """Extension validator instance."""
    return ExtensionValidator()


# ============================================================================
# TESTS: CORE DELEGATE VALIDATION
# ============================================================================

class TestCoreDelegateValidation:
    """Tests for core DELEGATE validation."""

    def test_valid_minimal_delegate_passes(self, valid_delegate, core_validator):
        """Valid minimal delegate with all 7 core fields passes."""
        valid, errors = core_validator.validate_delegate_core(valid_delegate)
        assert valid, f"Expected valid, got errors: {errors}"
        assert len(errors) == 0

    def test_task_id_valid_format(self, valid_delegate, core_validator):
        """task_id with valid kebab-case format passes."""
        test_cases = [
            "a-b",  # minimal 3 chars
            "my-task-001",
            "test-task-2026-05-13",
            "a0-b0-c0",
        ]
        for task_id in test_cases:
            delegate = {**valid_delegate, "task_id": task_id}
            valid, errors = core_validator.validate_delegate_core(delegate)
            assert valid, f"task_id '{task_id}' should be valid, got errors: {errors}"

    def test_task_id_invalid_format_uppercase(self, valid_delegate, core_validator):
        """task_id with uppercase letters fails."""
        delegate = {**valid_delegate, "task_id": "My-Task"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("task_id" in e for e in errors)

    def test_task_id_invalid_format_short(self, valid_delegate, core_validator):
        """task_id shorter than 3 chars fails."""
        delegate = {**valid_delegate, "task_id": "ab"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("task_id" in e for e in errors)

    def test_task_id_missing(self, valid_delegate, core_validator):
        """Missing task_id fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "task_id"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("task_id" in e for e in errors)

    def test_skill_valid(self, valid_delegate, core_validator):
        """Valid existing skill passes."""
        delegate = {**valid_delegate, "skill": "queue-management"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert valid, f"skill 'queue-management' should exist, got errors: {errors}"

    def test_skill_invalid_nonexistent(self, valid_delegate, core_validator):
        """Non-existent skill fails."""
        delegate = {**valid_delegate, "skill": "nonexistent-skill-xyz"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("skill" in e for e in errors)

    def test_skill_missing(self, valid_delegate, core_validator):
        """Missing skill fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "skill"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("skill" in e for e in errors)

    def test_agent_valid_values(self, valid_delegate, core_validator):
        """All valid agent values pass."""
        agents = ['orchestrator', 'engineer', 'senior-engineer', 'lead-engineer',
                  'principal-engineer', 'security-engineer', 'quality-engineer', 'model-engineer']
        for agent in agents:
            delegate = {**valid_delegate, "agent": agent}
            valid, errors = core_validator.validate_delegate_core(delegate)
            assert valid, f"agent '{agent}' should be valid, got errors: {errors}"

    def test_agent_invalid_value(self, valid_delegate, core_validator):
        """Invalid agent value fails."""
        delegate = {**valid_delegate, "agent": "unknown-agent"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("agent" in e for e in errors)

    def test_agent_missing(self, valid_delegate, core_validator):
        """Missing agent fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "agent"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("agent" in e for e in errors)

    def test_scope_valid_length(self, valid_delegate, core_validator):
        """Scope with >=15 words passes."""
        scope = " ".join(["word"] * 15)
        delegate = {**valid_delegate, "scope": scope}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert valid, f"scope with 15 words should be valid, got errors: {errors}"

    def test_scope_invalid_too_short(self, valid_delegate, core_validator):
        """Scope with <15 words fails."""
        scope = " ".join(["word"] * 10)
        delegate = {**valid_delegate, "scope": scope}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("scope" in e and ">=15 words" in e for e in errors)

    def test_scope_missing(self, valid_delegate, core_validator):
        """Missing scope fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "scope"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("scope" in e for e in errors)

    def test_success_criteria_valid_array(self, valid_delegate, core_validator):
        """Non-empty success_criteria array passes."""
        delegate = {**valid_delegate, "success_criteria": ["Criteria 1"]}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert valid, f"non-empty success_criteria should be valid, got errors: {errors}"

    def test_success_criteria_invalid_empty(self, valid_delegate, core_validator):
        """Empty success_criteria array fails."""
        delegate = {**valid_delegate, "success_criteria": []}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("success_criteria" in e for e in errors)

    def test_success_criteria_missing(self, valid_delegate, core_validator):
        """Missing success_criteria fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "success_criteria"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("success_criteria" in e for e in errors)

    def test_plan_valid_steps(self, valid_delegate, core_validator):
        """Plan with >=2 steps, each with >=3 words passes."""
        plan = ["First initial action", "Second important action", "Third critical action"]
        delegate = {**valid_delegate, "plan": plan}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert valid, f"valid plan should pass, got errors: {errors}"

    def test_plan_invalid_insufficient_steps(self, valid_delegate, core_validator):
        """Plan with <2 steps fails."""
        delegate = {**valid_delegate, "plan": ["Single step action"]}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("plan" in e and ">=2 steps" in e for e in errors)

    def test_plan_invalid_short_step(self, valid_delegate, core_validator):
        """Plan with a step having <3 words fails."""
        plan = ["First action", "Go"]
        delegate = {**valid_delegate, "plan": plan}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("plan" in e and ">=3 words" in e for e in errors)

    def test_plan_missing(self, valid_delegate, core_validator):
        """Missing plan fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "plan"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("plan" in e for e in errors)

    def test_context_valid_string(self, valid_delegate, core_validator):
        """Context as string with >=20 words passes."""
        context = " ".join(["word"] * 20)
        delegate = {**valid_delegate, "context": context}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert valid, f"context with >=20 words should be valid, got errors: {errors}"

    def test_context_valid_array(self, valid_delegate, core_validator):
        """Context as non-empty array passes."""
        context = ["First context item with enough words", "Second context item with enough words"]
        delegate = {**valid_delegate, "context": context}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert valid, f"context as non-empty array should be valid, got errors: {errors}"

    def test_context_invalid_string_too_short(self, valid_delegate, core_validator):
        """Context string with <20 words fails."""
        context = " ".join(["word"] * 10)
        delegate = {**valid_delegate, "context": context}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("context" in e and ">=20 words" in e for e in errors)

    def test_context_invalid_empty_array(self, valid_delegate, core_validator):
        """Context as empty array fails."""
        delegate = {**valid_delegate, "context": []}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("context" in e for e in errors)

    def test_context_missing(self, valid_delegate, core_validator):
        """Missing context fails."""
        delegate = {k: v for k, v in valid_delegate.items() if k != "context"}
        valid, errors = core_validator.validate_delegate_core(delegate)
        assert not valid
        assert any("context" in e for e in errors)


# ============================================================================
# TESTS: CORE HANDBACK VALIDATION
# ============================================================================

class TestCoreHandbackValidation:
    """Tests for core HANDBACK validation."""

    def test_valid_minimal_handback_passes(self, valid_handback, core_validator):
        """Valid minimal handback with all 4 core fields passes."""
        valid, errors = core_validator.validate_handback_core(valid_handback)
        assert valid, f"Expected valid, got errors: {errors}"
        assert len(errors) == 0

    def test_handback_task_id_missing(self, valid_handback, core_validator):
        """Missing task_id in handback fails."""
        handback = {k: v for k, v in valid_handback.items() if k != "task_id"}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("task_id" in e for e in errors)

    def test_handback_status_valid_values(self, valid_handback, core_validator):
        """All valid status values pass."""
        statuses = ['success', 'failure', 'partial', 'blocked', 'escalate']
        for status in statuses:
            handback = {**valid_handback, "status": status}
            valid, errors = core_validator.validate_handback_core(handback)
            assert valid, f"status '{status}' should be valid, got errors: {errors}"

    def test_handback_status_invalid_value(self, valid_handback, core_validator):
        """Invalid status value fails."""
        handback = {**valid_handback, "status": "unknown-status"}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("status" in e for e in errors)

    def test_handback_status_missing(self, valid_handback, core_validator):
        """Missing status fails."""
        handback = {k: v for k, v in valid_handback.items() if k != "status"}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("status" in e for e in errors)

    def test_handback_output_present(self, valid_handback, core_validator):
        """Output field present (any value) passes."""
        handback = {**valid_handback, "output": "any output"}
        valid, errors = core_validator.validate_handback_core(handback)
        assert valid, f"output field should be accepted, got errors: {errors}"

    def test_handback_output_missing(self, valid_handback, core_validator):
        """Missing output fails."""
        handback = {k: v for k, v in valid_handback.items() if k != "output"}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("output" in e for e in errors)

    def test_handback_metrics_quality_valid_range(self, valid_handback, core_validator):
        """Metrics quality in 0.0-1.0 range passes."""
        for quality in [0.0, 0.5, 1.0]:
            metrics = {**valid_handback["metrics"], "quality": quality}
            handback = {**valid_handback, "metrics": metrics}
            valid, errors = core_validator.validate_handback_core(handback)
            assert valid, f"quality {quality} should be valid, got errors: {errors}"

    def test_handback_metrics_quality_invalid_out_of_range(self, valid_handback, core_validator):
        """Metrics quality out of 0.0-1.0 range fails."""
        for quality in [-0.1, 1.1, 2.0]:
            metrics = {**valid_handback["metrics"], "quality": quality}
            handback = {**valid_handback, "metrics": metrics}
            valid, errors = core_validator.validate_handback_core(handback)
            assert not valid
            assert any("quality" in e for e in errors)

    def test_handback_metrics_tokens_valid(self, valid_handback, core_validator):
        """Metrics tokens as non-negative integer passes."""
        for tokens in [0, 100, 5000]:
            metrics = {**valid_handback["metrics"], "tokens": tokens}
            handback = {**valid_handback, "metrics": metrics}
            valid, errors = core_validator.validate_handback_core(handback)
            assert valid, f"tokens {tokens} should be valid, got errors: {errors}"

    def test_handback_metrics_tokens_invalid_negative(self, valid_handback, core_validator):
        """Metrics tokens as negative fails."""
        metrics = {**valid_handback["metrics"], "tokens": -1}
        handback = {**valid_handback, "metrics": metrics}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("tokens" in e for e in errors)

    def test_handback_metrics_cost_valid(self, valid_handback, core_validator):
        """Metrics cost as non-negative number passes."""
        for cost in [0, 0.05, 100.5]:
            metrics = {**valid_handback["metrics"], "cost": cost}
            handback = {**valid_handback, "metrics": metrics}
            valid, errors = core_validator.validate_handback_core(handback)
            assert valid, f"cost {cost} should be valid, got errors: {errors}"

    def test_handback_metrics_cost_invalid_negative(self, valid_handback, core_validator):
        """Metrics cost as negative fails."""
        metrics = {**valid_handback["metrics"], "cost": -0.01}
        handback = {**valid_handback, "metrics": metrics}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("cost" in e for e in errors)

    def test_handback_metrics_duration_valid(self, valid_handback, core_validator):
        """Metrics duration_seconds as non-negative number passes."""
        for duration in [0, 30.5, 3600]:
            metrics = {**valid_handback["metrics"], "duration_seconds": duration}
            handback = {**valid_handback, "metrics": metrics}
            valid, errors = core_validator.validate_handback_core(handback)
            assert valid, f"duration {duration} should be valid, got errors: {errors}"

    def test_handback_metrics_duration_invalid_negative(self, valid_handback, core_validator):
        """Metrics duration_seconds as negative fails."""
        metrics = {**valid_handback["metrics"], "duration_seconds": -1}
        handback = {**valid_handback, "metrics": metrics}
        valid, errors = core_validator.validate_handback_core(handback)
        assert not valid
        assert any("duration_seconds" in e for e in errors)


# ============================================================================
# TESTS: EXTENSION VALIDATION
# ============================================================================

class TestExtensionValidation:
    """Tests for extension field validation."""

    def test_extensions_effort_valid_values(self, valid_delegate, ext_validator):
        """All valid effort values pass extension validation."""
        efforts = ['low', 'medium', 'high']
        for effort in efforts:
            delegate = {**valid_delegate, "effort": effort}
            valid, errors = ext_validator.validate_extensions(delegate)
            assert valid, f"effort '{effort}' should be valid, got errors: {errors}"

    def test_extensions_effort_invalid_value(self, valid_delegate, ext_validator):
        """Invalid effort value fails."""
        delegate = {**valid_delegate, "effort": "extreme"}
        valid, errors = ext_validator.validate_extensions(delegate)
        assert not valid
        assert any("effort" in e for e in errors)

    def test_extensions_model_any_string_allowed(self, valid_delegate, ext_validator):
        """Any string value for model passes."""
        models = ['claude-opus-4.7', 'gpt-4', 'my-custom-model', '']
        for model in models:
            delegate = {**valid_delegate, "model": model}
            valid, errors = ext_validator.validate_extensions(delegate)
            assert valid, f"model '{model}' should be accepted, got errors: {errors}"

    def test_extensions_budget_valid_values(self, valid_delegate, ext_validator):
        """Valid budget values pass."""
        budgets = [0, 1.5, 100, 0.01]
        for budget in budgets:
            delegate = {**valid_delegate, "budget": budget}
            valid, errors = ext_validator.validate_extensions(delegate)
            assert valid, f"budget {budget} should be valid, got errors: {errors}"

    def test_extensions_budget_invalid_negative(self, valid_delegate, ext_validator):
        """Negative budget fails."""
        delegate = {**valid_delegate, "budget": -1}
        valid, errors = ext_validator.validate_extensions(delegate)
        assert not valid
        assert any("budget" in e for e in errors)

    def test_extensions_priority_valid_range(self, valid_delegate, ext_validator):
        """Priority 1-10 passes."""
        for priority in [1, 5, 10]:
            delegate = {**valid_delegate, "priority": priority}
            valid, errors = ext_validator.validate_extensions(delegate)
            assert valid, f"priority {priority} should be valid, got errors: {errors}"

    def test_extensions_priority_invalid_out_of_range(self, valid_delegate, ext_validator):
        """Priority outside 1-10 fails."""
        for priority in [0, 11, -1]:
            delegate = {**valid_delegate, "priority": priority}
            valid, errors = ext_validator.validate_extensions(delegate)
            assert not valid
            assert any("priority" in e for e in errors)

    def test_extensions_unknown_fields_ignored(self, valid_delegate, ext_validator):
        """Unknown extension fields are ignored."""
        delegate = {
            **valid_delegate,
            "unknown_field": "some value",
            "another_unknown": 123
        }
        valid, errors = ext_validator.validate_extensions(delegate)
        assert valid, f"unknown fields should be ignored, got errors: {errors}"

    def test_extensions_dependencies_as_list(self, valid_delegate, ext_validator):
        """Dependencies as list passes."""
        delegate = {**valid_delegate, "dependencies": ["task-1", "task-2"]}
        valid, errors = ext_validator.validate_extensions(delegate)
        assert valid, f"dependencies list should be valid, got errors: {errors}"

    def test_extensions_dependencies_not_list_fails(self, valid_delegate, ext_validator):
        """Dependencies not as list fails."""
        delegate = {**valid_delegate, "dependencies": "task-1"}
        valid, errors = ext_validator.validate_extensions(delegate)
        assert not valid
        assert any("dependencies" in e for e in errors)


# ============================================================================
# TESTS: BACKWARD COMPATIBILITY
# ============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility with old protocol."""

    def test_old_format_delegate_with_effort_model_passes_core(self, valid_delegate, core_validator):
        """Old-format delegate with effort and model fields still passes core validation."""
        old_delegate = {
            **valid_delegate,
            "effort": "high",
            "model": "claude-opus-4.8",
            "estimated_hours": 24
        }
        valid, errors = core_validator.validate_delegate_core(old_delegate)
        assert valid, f"old-format delegate should pass core validation, got errors: {errors}"

    def test_old_format_delegate_extensions_validated(self, valid_delegate, ext_validator):
        """Old-format delegate extensions are validated loosely."""
        old_delegate = {
            **valid_delegate,
            "effort": "high",
            "model": "claude-opus-4.8"
        }
        valid, errors = ext_validator.validate_extensions(old_delegate)
        assert valid, f"old-format delegate extensions should pass, got errors: {errors}"


# ============================================================================
# TESTS: PERFORMANCE
# ============================================================================

class TestPerformance:
    """Performance tests for validators."""

    def test_core_validation_performance(self, valid_delegate, core_validator):
        """Core validation should complete in <50ms average over 100 iterations."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            core_validator.validate_delegate_core(valid_delegate)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 50, f"Average core validation time {avg_time:.2f}ms exceeds 50ms limit"

    def test_extension_validation_performance(self, valid_delegate, ext_validator):
        """Extension validation should complete in <10ms average over 100 iterations."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            ext_validator.validate_extensions(valid_delegate)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 10, f"Average extension validation time {avg_time:.2f}ms exceeds 10ms limit"

    def test_core_handback_validation_performance(self, valid_handback, core_validator):
        """Core handback validation should complete in <50ms average over 100 iterations."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            core_validator.validate_handback_core(valid_handback)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 50, f"Average handback validation time {avg_time:.2f}ms exceeds 50ms limit"
