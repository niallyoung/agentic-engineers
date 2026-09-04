"""
Tests for the low-level CoreProtocolValidator / ExtensionValidator API in
protocol_validator.py -- the strict/fast validators that the high-level
ProtocolValidator wrapper (see test_protocol_validator.py) delegates to
internally for validate_delegate()/validate_handback().

Consolidated from tests/test_core_protocol_validator.py (WP-R3-05, batch 4,
task-2026-08-13-r3-wp05-test-consolidation): same field/boundary/type
coverage, parametrized to replace dozens of near-identical one-assertion
test methods and avoid re-testing scenarios already covered end-to-end by
test_protocol_validator.py's ProtocolValidator-level suite.

TDD red-phase style: written to validate real behaviour of existing
implementation. Target: >=90% branch coverage of protocol_validator.py's
core/extension validators.
"""
import sys
import time
from pathlib import Path

import pytest

_PV_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_PV_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_PV_SCRIPTS))

from protocol_validator import (
    CoreProtocolValidator,
    ExtensionValidator,
    VALID_AGENTS,
    VALID_STATUSES,
    TASK_ID_PATTERN,
    _count_words,
    _skill_exists,
)

# Sentinel meaning "delete this field from the fixture" in parametrize tables
# below (a real value of this exact string is never a case under test).
_DEL = "__DEL__"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def core_validator():
    return CoreProtocolValidator()


@pytest.fixture
def ext_validator():
    return ExtensionValidator()


@pytest.fixture
def valid_delegate():
    """Minimal valid DELEGATE for core validation."""
    return {
        "task_id": "valid-task-01",
        "skill": "protocol-validator",
        "agent": "engineer",
        "scope": (
            "Implement the feature with proper testing and documentation "
            "to ensure all edge cases are covered in production"
        ),  # >15 words
        "success_criteria": ["All tests pass", "Coverage >= 90%"],
        "plan": [
            "Analyse existing code and identify gaps in coverage",
            "Write unit tests for each public method and edge case",
        ],
        "context": (
            "This task is part of the TIER1 coverage initiative. "
            "The module has zero coverage currently and needs comprehensive "
            "tests written to validate all branches and error conditions."
        ),  # >20 words
    }


@pytest.fixture
def valid_handback():
    """Minimal valid HANDBACK for core validation."""
    return {
        "task_id": "valid-task-01",
        "status": "success",
        "output": "All tests written and passing.",
        "metrics": {
            "quality": 0.95,
            "tokens": 5000,
            "cost": 0.25,
            "duration_seconds": 120.0,
        },
    }


# ---------------------------------------------------------------------------
# Helper / utility functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("hello world foo", 3),
    ("", 0),
    ("hello", 1),
    ("  hello   world  ", 2),  # split() ignores extra whitespace
    ("one two three four five six seven eight nine ten", 10),
])
def test_count_words(text, expected):
    assert _count_words(text) == expected


@pytest.mark.parametrize("skill,expected", [
    ("protocol-validator", True),
    ("", False),
    (None, False),
    (42, False),
    ("nonexistent-skill-xyz-abc-999", False),
])
def test_skill_exists(skill, expected):
    assert _skill_exists(skill) is expected


@pytest.mark.parametrize("task_id,expected", [
    ("valid-task-01", True),
    ("abc123def", True),
    ("abc", True),  # exactly 3 chars (minimum)
    ("a", False),  # too short
    ("ab", False),  # too short
    ("Invalid-Task", False),  # uppercase rejected
    ("invalid_task", False),  # underscore rejected
    ("-task-01", False),  # leading hyphen
    ("task-01-", False),  # trailing hyphen
])
def test_task_id_pattern(task_id, expected):
    assert (TASK_ID_PATTERN.match(task_id) is not None) is expected


# ---------------------------------------------------------------------------
# CoreProtocolValidator — validate_delegate_core
# ---------------------------------------------------------------------------

class TestValidateDelegateCore:
    """Tests for CoreProtocolValidator.validate_delegate_core."""

    def test_valid_delegate_passes(self, core_validator, valid_delegate):
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert ok is True
        assert errors == []

    def test_empty_dict_fails_with_all_required_field_errors(self, core_validator):
        """Empty dict fails with an error per missing required field, all
        reported in a single call (multi-error reporting, not fail-fast)."""
        ok, errors = core_validator.validate_delegate_core({})
        assert not ok
        assert len(errors) >= 5

    @pytest.mark.parametrize("field,value", [
        ("task_id", _DEL),
        ("task_id", 123),
        ("task_id", None),
        ("task_id", "Invalid-Task"),
        ("task_id", "invalid_task"),
        ("task_id", "ab"),
        ("task_id", "-bad-id"),
        # ("skill", _DEL) removed: `skill` is an optional extension now, so its
        # ABSENCE is valid. The cases below still hold — when skill IS present it
        # must be a non-empty string naming a real skill.
        ("skill", None),
        ("skill", 42),
        ("skill", "nonexistent-skill-xyz-123"),
        ("agent", _DEL),
        ("agent", None),
        ("agent", "random-person"),
        ("scope", _DEL),
        ("scope", None),
        ("scope", "Too short scope here"),  # 4 words
        ("scope", ["list", "instead", "of", "string"]),
        ("success_criteria", _DEL),
        ("success_criteria", []),
        ("success_criteria", "just a string"),
        ("plan", _DEL),
        ("plan", None),
        ("plan", ["Only one step provided"]),  # needs >=2
        ("plan", "just a string plan"),
        ("plan", []),
        ("context", _DEL),
        ("context", None),
        ("context", "Too short context string here"),  # 5 words
        ("context", []),
        ("context", {"key": "value"}),
    ])
    def test_invalid_field_rejected(self, core_validator, valid_delegate, field, value):
        if value == _DEL:
            del valid_delegate[field]
        else:
            valid_delegate[field] = value
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any(field in e for e in errors)

    def test_plan_step_too_short_reports_index(self, core_validator, valid_delegate):
        valid_delegate["plan"] = [
            "Short step",  # 2 words
            "Another valid step with enough words for the plan",
        ]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan[0]" in e for e in errors)

    @pytest.mark.parametrize("field,value", [
        ("scope", "one two three four five six seven eight nine ten "
                  "eleven twelve thirteen fourteen fifteen"),  # exactly 15 words
        ("success_criteria", ["Single criterion"]),
        ("plan", ["Step one with enough words here", "Step two with enough words here"]),
        ("context", "one two three four five six seven eight nine ten eleven "
                     "twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"),  # exactly 20 words
        ("context", ["Context item one", "Context item two"]),
    ])
    def test_boundary_and_alternate_values_accepted(self, core_validator, valid_delegate, field, value):
        valid_delegate[field] = value
        _, errors = core_validator.validate_delegate_core(valid_delegate)
        assert [e for e in errors if field in e] == []

    def test_all_valid_agents_accepted(self, core_validator, valid_delegate):
        for agent in VALID_AGENTS:
            valid_delegate["agent"] = agent
            _, errors = core_validator.validate_delegate_core(valid_delegate)
            agent_errors = [e for e in errors if "agent" in e]
            assert agent_errors == [], f"Agent '{agent}' unexpectedly rejected: {agent_errors}"

    def test_unknown_extensions_ignored_by_core(self, core_validator, valid_delegate):
        """Extra keys not in the 7 core fields must not cause core validation
        to fail (backward/forward compatibility)."""
        valid_delegate["effort"] = "high"
        valid_delegate["model"] = "gpt-5.5"
        valid_delegate["unknown_field"] = "some_value"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert ok is True, f"Unexpected errors: {errors}"


# ---------------------------------------------------------------------------
# CoreProtocolValidator — validate_handback_core
# ---------------------------------------------------------------------------

class TestValidateHandbackCore:
    """Tests for CoreProtocolValidator.validate_handback_core."""

    def test_valid_handback_passes(self, core_validator, valid_handback):
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert ok is True
        assert errors == []

    @pytest.mark.parametrize("field,value", [
        ("task_id", _DEL),
        ("task_id", 99),
        ("task_id", None),
        ("status", _DEL),
        ("status", "unknown"),
        ("output", _DEL),
        ("metrics", _DEL),
        ("metrics", None),
        ("metrics", "not a dict"),
    ])
    def test_invalid_field_rejected(self, core_validator, valid_handback, field, value):
        if value == _DEL:
            del valid_handback[field]
        else:
            valid_handback[field] = value
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok

    @pytest.mark.parametrize("value", [None, {"files": ["a.py", "b.py"]}])
    def test_output_accepts_any_present_value(self, core_validator, valid_handback, value):
        """The `output` key just needs to be present; its value is free-form."""
        valid_handback["output"] = value
        _, errors = core_validator.validate_handback_core(valid_handback)
        assert [e for e in errors if "output" in e] == []

    def test_all_valid_statuses_accepted(self, core_validator, valid_handback):
        for status in VALID_STATUSES:
            valid_handback["status"] = status
            _, errors = core_validator.validate_handback_core(valid_handback)
            status_errors = [e for e in errors if "status" in e]
            assert status_errors == [], f"Status '{status}' rejected: {status_errors}"

    @pytest.mark.parametrize("metric,bad_value", [
        ("quality", 1.5), ("quality", -0.1), ("quality", "high"),
        ("tokens", -1), ("tokens", 1.5),
        ("cost", -0.01), ("cost", "cheap"),
        ("duration_seconds", -1.0), ("duration_seconds", "fast"),
    ])
    def test_metrics_field_out_of_range_or_wrong_type_rejected(self, core_validator, valid_handback, metric, bad_value):
        valid_handback["metrics"][metric] = bad_value
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any(metric in e for e in errors)

    @pytest.mark.parametrize("metric", ["quality", "tokens", "cost", "duration_seconds"])
    def test_metrics_field_missing_rejected(self, core_validator, valid_handback, metric):
        del valid_handback["metrics"][metric]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any(metric in e for e in errors)

    @pytest.mark.parametrize("metric,boundary_value", [
        ("quality", 0.0), ("quality", 1.0),
        ("tokens", 0), ("cost", 0), ("duration_seconds", 0),
    ])
    def test_metrics_field_boundary_accepted(self, core_validator, valid_handback, metric, boundary_value):
        valid_handback["metrics"][metric] = boundary_value
        _, errors = core_validator.validate_handback_core(valid_handback)
        assert [e for e in errors if metric in e] == []


# ---------------------------------------------------------------------------
# ExtensionValidator — validate_extensions (DELEGATE)
# ---------------------------------------------------------------------------

class TestExtensionValidatorDelegate:
    """Tests for ExtensionValidator.validate_extensions."""

    def test_no_extensions_passes(self, ext_validator):
        ok, errors = ext_validator.validate_extensions({})
        assert ok is True
        assert errors == []

    @pytest.mark.parametrize("extensions,expect_ok,error_field", [
        ({"effort": "low"}, True, None),
        ({"effort": "medium"}, True, None),
        ({"effort": "high"}, True, None),
        ({"effort": "extreme"}, False, "effort"),
        ({"model": 42}, False, "model"),
        ({"model": "any-model-name"}, True, None),  # soft validation: any string ok
        ({"budget": -1}, False, "budget"),
        ({"budget": 0}, True, None),
        ({"budget": 10.0}, True, None),
        ({"budget": "free"}, False, "budget"),
        ({"priority": 0}, False, "priority"),
        ({"priority": 11}, False, "priority"),
        ({"priority": 1}, True, None),
        ({"priority": 10}, True, None),
        ({"priority": 5.5}, False, "priority"),
        ({"deadline": 12345}, False, "deadline"),
        ({"deadline": "2024-12-31T00:00:00Z"}, True, None),
        ({"dependencies": "task-001"}, False, "dependencies"),
        ({"dependencies": ["task-001", "task-002"]}, True, None),
        ({"dependencies": []}, True, None),
        ({"parent_task_id": 99}, False, "parent_task_id"),
        ({"parent_task_id": "parent-01"}, True, None),
        ({"retry_context": "retry"}, False, "retry_context"),
        ({"retry_context": {"attempt": 2}}, True, None),
    ])
    def test_extension_field_matrix(self, ext_validator, extensions, expect_ok, error_field):
        ok, errors = ext_validator.validate_extensions(extensions)
        assert ok is expect_ok
        if error_field:
            assert any(error_field in e for e in errors)

    def test_all_valid_extensions_together(self, ext_validator):
        ok, errors = ext_validator.validate_extensions({
            "effort": "high",
            "model": "claude-sonnet-4.5",
            "budget": 5.0,
            "priority": 7,
            "deadline": "2025-01-01T00:00:00Z",
            "dependencies": ["task-a"],
            "parent_task_id": "parent-task-01",
            "retry_context": {"count": 1},
        })
        assert ok is True
        assert errors == []


# ---------------------------------------------------------------------------
# ExtensionValidator — validate_handback_extensions
# ---------------------------------------------------------------------------

class TestExtensionValidatorHandback:
    """Tests for ExtensionValidator.validate_handback_extensions."""

    def test_no_extensions_passes(self, ext_validator):
        ok, errors = ext_validator.validate_handback_extensions({})
        assert ok is True
        assert errors == []

    @pytest.mark.parametrize("extensions,expect_ok,error_field", [
        ({"retry_count": -1}, False, "retry_count"),
        ({"retry_count": 0}, True, None),
        ({"retry_count": 1.5}, False, "retry_count"),
        ({"model_used": 42}, False, "model_used"),
        ({"model_used": "claude-opus-4.7"}, True, None),
        ({"effort_actual": "extreme"}, False, "effort_actual"),
        ({"effort_actual": "low"}, True, None),
        ({"effort_actual": "medium"}, True, None),
        ({"effort_actual": "high"}, True, None),
        ({"flags": "flag1"}, False, "flags"),
        ({"flags": ["needs-review"]}, True, None),
        ({"error": {"msg": "oops"}}, False, "error"),
        ({"error": "Something went wrong"}, True, None),
        ({"children_created": "child-01"}, False, "children_created"),
        ({"children_created": ["child-01"]}, True, None),
        ({"children_results": ["x"]}, False, "children_results"),
        ({"children_results": {"child-01": {"status": "done"}}}, True, None),
    ])
    def test_extension_field_matrix(self, ext_validator, extensions, expect_ok, error_field):
        ok, errors = ext_validator.validate_handback_extensions(extensions)
        assert ok is expect_ok
        if error_field:
            assert any(error_field in e for e in errors)

    def test_all_valid_handback_extensions_together(self, ext_validator):
        ok, errors = ext_validator.validate_handback_extensions({
            "retry_count": 2,
            "model_used": "gpt-5.4",
            "effort_actual": "medium",
            "flags": ["reviewed"],
            "error": "minor warning",
            "children_created": ["child-task-01"],
            "children_results": {"child-task-01": {"status": "done"}},
        })
        assert ok is True
        assert errors == []


# ---------------------------------------------------------------------------
# Performance: core <50ms, extensions <10ms (per protocol_validator.py's
# module-level docstring targets for these two classes specifically -- a
# tighter <5ms end-to-end budget for the ProtocolValidator wrapper is
# covered separately in test_protocol_validator.py).
# ---------------------------------------------------------------------------

class TestPerformance:
    """One wall-clock check per validator method — avoids stacking multiple
    near-identical timing assertions that all exercise the same hot path."""

    def test_core_and_extension_validation_within_budget(
        self, core_validator, ext_validator, valid_delegate, valid_handback
    ):
        start = time.monotonic()
        core_validator.validate_delegate_core(valid_delegate)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"Core delegate validation took {elapsed_ms:.1f}ms, expected <50ms"

        start = time.monotonic()
        core_validator.validate_handback_core(valid_handback)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"Core handback validation took {elapsed_ms:.1f}ms, expected <50ms"

        start = time.monotonic()
        ext_validator.validate_extensions({
            "effort": "medium", "model": "claude-sonnet-4.5", "budget": 5.0, "priority": 5,
        })
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 10, f"Extension validation took {elapsed_ms:.1f}ms, expected <10ms"
