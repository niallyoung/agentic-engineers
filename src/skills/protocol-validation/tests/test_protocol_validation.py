"""
Tests for the canonical protocol-validation skill.

Covers the public functional API:
    validate_delegate(dict) -> (bool, list[str])
    validate_handback(dict) -> (bool, list[str])

Both valid and invalid cases are exercised for DELEGATE and HANDBACK, including
core-field failures and extension-field failures.
"""

import sys
from pathlib import Path

import pytest

# Path setup: add the skill's scripts/ dir so we can import the module directly.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from protocol_validation import (  # noqa: E402
    validate_delegate,
    validate_handback,
    CoreProtocolValidator,
    ExtensionValidator,
)


# ---------------------------------------------------------------------------
# Fixtures: known-good blocks. The skill name must exist in the repo's skills
# tree; we use this very skill ("protocol-validation") so the check passes.
# ---------------------------------------------------------------------------

def _valid_delegate() -> dict:
    return {
        "task_id": "fix-type-annotation-error",
        "skill": "protocol-validation",
        "agent": "engineer",
        "scope": (
            "Fix the broken type annotation in the user service module so that "
            "mypy passes cleanly and the public API signatures remain unchanged."
        ),
        "success_criteria": ["mypy passes", "no API change"],
        "plan": [
            "Read the offending module carefully",
            "Correct the annotation and run mypy",
        ],
        "context": (
            "The user service module currently fails type checking because a "
            "function returns Optional but is annotated as a plain string which "
            "breaks the continuous integration pipeline for the whole team here."
        ),
    }


def _valid_handback() -> dict:
    return {
        "task_id": "fix-type-annotation-error",
        "status": "success",
        "output": "Fixed annotation; mypy passes.",
        "metrics": {
            "quality": 0.95,
            "tokens": 1200,
            "cost": 0.03,
            "duration_seconds": 42,
        },
    }


# ---------------------------------------------------------------------------
# DELEGATE — valid cases
# ---------------------------------------------------------------------------

def test_valid_delegate_passes():
    valid, errors = validate_delegate(_valid_delegate())
    assert valid is True, errors
    assert errors == []


def test_valid_delegate_with_context_list():
    d = _valid_delegate()
    d["context"] = ["line one of context", "line two of context"]
    valid, errors = validate_delegate(d)
    assert valid is True, errors


def test_valid_delegate_with_optional_extensions():
    d = _valid_delegate()
    d.update({"effort": "high", "priority": 5, "model": "claude-sonnet-4.6", "budget": 1.5})
    valid, errors = validate_delegate(d)
    assert valid is True, errors


# ---------------------------------------------------------------------------
# DELEGATE — invalid cases (core)
# ---------------------------------------------------------------------------

def test_delegate_missing_task_id():
    d = _valid_delegate()
    del d["task_id"]
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("task_id" in e for e in errors)


def test_delegate_bad_task_id_format():
    d = _valid_delegate()
    d["task_id"] = "Bad_Task_ID"  # uppercase + underscores
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("task_id" in e for e in errors)


def test_delegate_unknown_skill():
    d = _valid_delegate()
    d["skill"] = "this-skill-does-not-exist-xyz"
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("skill" in e for e in errors)


def test_delegate_invalid_agent():
    d = _valid_delegate()
    d["agent"] = "wizard"
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("agent" in e for e in errors)


def test_delegate_scope_too_short():
    d = _valid_delegate()
    d["scope"] = "too short"
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("scope" in e for e in errors)


def test_delegate_empty_success_criteria():
    d = _valid_delegate()
    d["success_criteria"] = []
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("success_criteria" in e for e in errors)


def test_delegate_plan_too_few_steps():
    d = _valid_delegate()
    d["plan"] = ["only one detailed step here"]
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("plan" in e for e in errors)


def test_delegate_context_too_short():
    d = _valid_delegate()
    d["context"] = "short context"
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("context" in e for e in errors)


def test_delegate_not_a_dict():
    valid, errors = validate_delegate("not a dict")  # type: ignore[arg-type]
    assert valid is False
    assert errors


# ---------------------------------------------------------------------------
# DELEGATE — invalid cases (extension)
# ---------------------------------------------------------------------------

def test_delegate_invalid_effort():
    d = _valid_delegate()
    d["effort"] = "extreme"
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("effort" in e for e in errors)


def test_delegate_invalid_priority():
    d = _valid_delegate()
    d["priority"] = 99
    valid, errors = validate_delegate(d)
    assert valid is False
    assert any("priority" in e for e in errors)


# ---------------------------------------------------------------------------
# HANDBACK — valid cases
# ---------------------------------------------------------------------------

def test_valid_handback_passes():
    valid, errors = validate_handback(_valid_handback())
    assert valid is True, errors
    assert errors == []


def test_valid_handback_with_extensions():
    h = _valid_handback()
    h.update({"retry_count": 1, "model_used": "claude-haiku-4.5", "effort_actual": "low"})
    valid, errors = validate_handback(h)
    assert valid is True, errors


@pytest.mark.parametrize("status", ["success", "failure", "partial", "blocked", "escalate"])
def test_valid_handback_all_statuses(status):
    h = _valid_handback()
    h["status"] = status
    valid, errors = validate_handback(h)
    assert valid is True, errors


# ---------------------------------------------------------------------------
# HANDBACK — invalid cases (core)
# ---------------------------------------------------------------------------

def test_handback_missing_task_id():
    h = _valid_handback()
    del h["task_id"]
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("task_id" in e for e in errors)


def test_handback_invalid_status():
    h = _valid_handback()
    h["status"] = "done"  # not a valid status
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("status" in e for e in errors)


def test_handback_missing_output():
    h = _valid_handback()
    del h["output"]
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("output" in e for e in errors)


def test_handback_missing_metrics():
    h = _valid_handback()
    del h["metrics"]
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("metrics" in e for e in errors)


def test_handback_quality_out_of_range():
    h = _valid_handback()
    h["metrics"]["quality"] = 1.5
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("quality" in e for e in errors)


def test_handback_negative_tokens():
    h = _valid_handback()
    h["metrics"]["tokens"] = -5
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("tokens" in e for e in errors)


def test_handback_metrics_not_object():
    h = _valid_handback()
    h["metrics"] = "not an object"
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("metrics" in e for e in errors)


def test_handback_not_a_dict():
    valid, errors = validate_handback(["not", "a", "dict"])  # type: ignore[arg-type]
    assert valid is False
    assert errors


# ---------------------------------------------------------------------------
# HANDBACK — invalid cases (extension)
# ---------------------------------------------------------------------------

def test_handback_invalid_retry_count():
    h = _valid_handback()
    h["retry_count"] = -1
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("retry_count" in e for e in errors)


def test_handback_children_results_wrong_type():
    h = _valid_handback()
    h["children_results"] = ["should", "be", "a", "dict"]
    valid, errors = validate_handback(h)
    assert valid is False
    assert any("children_results" in e for e in errors)


# ---------------------------------------------------------------------------
# Class-based API still available (backward compatibility)
# ---------------------------------------------------------------------------

def test_core_validator_class_available():
    core = CoreProtocolValidator()
    valid, errors = core.validate_delegate_core(_valid_delegate())
    assert valid is True, errors


def test_extension_validator_class_available():
    ext = ExtensionValidator()
    valid, errors = ext.validate_handback_extensions({"retry_count": 2})
    assert valid is True, errors
