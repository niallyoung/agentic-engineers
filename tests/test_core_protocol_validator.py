"""
Tests for CoreProtocolValidator / ExtensionValidator.

Covers CoreProtocolValidator (validate_delegate_core, validate_handback_core)
and ExtensionValidator (validate_extensions, validate_handback_extensions), as
implemented by the protocol-validator skill (the single source of truth for
DELEGATE/HANDBACK schema validation — see src/skills/protocol-validator/).

Historical note: this file originally targeted a near-duplicate
core_protocol_validator.py that lived in queue-management/scripts/. That
module's unguarded import was a latent bug in installed harnesses and it was
deleted as part of the framework slimdown; this file was retargeted to the
surviving, canonical protocol_validator.py, whose
CoreProtocolValidator/ExtensionValidator API is identical. queue-management
itself was later deleted entirely (queue-removal, task-2026-08-13-queue-removal-code)
now that dispatch is a direct sub-agent spawn and the harness session
transcript is the durable audit record.

TDD red-phase style: written to validate real behaviour of existing implementation.
Target: >=90% branch coverage of protocol_validator.py's core/extension validators.
"""
import sys
import time
from pathlib import Path
import pytest

# ── Path setup ─────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PV_SCRIPTS = _REPO_ROOT / "src" / "skills" / "protocol-validator" / "scripts"
if str(_PV_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_PV_SCRIPTS))

from protocol_validator import (
    CoreProtocolValidator,
    ExtensionValidator,
    VALID_AGENTS,
    VALID_STATUSES,
    VALID_EFFORTS,
    TASK_ID_PATTERN,
    _count_words,
    _skill_exists,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def core_validator():
    """Return a fresh CoreProtocolValidator instance."""
    return CoreProtocolValidator()


@pytest.fixture
def ext_validator():
    """Return a fresh ExtensionValidator instance."""
    return ExtensionValidator()


@pytest.fixture
def valid_delegate():
    """Return a minimal valid DELEGATE for core validation."""
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
    """Return a minimal valid HANDBACK for core validation."""
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

class TestCountWords:
    """Tests for _count_words helper."""

    def test_simple_sentence(self):
        """Count words in a simple sentence returns correct count."""
        assert _count_words("hello world foo") == 3

    def test_empty_string(self):
        """Empty string has zero words."""
        assert _count_words("") == 0

    def test_single_word(self):
        """Single word returns 1."""
        assert _count_words("hello") == 1

    def test_extra_spaces_ignored(self):
        """split() naturally ignores extra whitespace."""
        assert _count_words("  hello   world  ") == 2

    def test_longer_text(self):
        """Longer sentences count correctly."""
        text = "one two three four five six seven eight nine ten"
        assert _count_words(text) == 10


class TestSkillExists:
    """Tests for _skill_exists helper."""

    def test_known_skill_exists(self):
        """A skill directory that exists returns True."""
        assert _skill_exists("protocol-validator") is True

    def test_empty_string_returns_false(self):
        """Empty string returns False."""
        assert _skill_exists("") is False

    def test_none_returns_false(self):
        """None input returns False."""
        assert _skill_exists(None) is False

    def test_non_string_returns_false(self):
        """Non-string input returns False."""
        assert _skill_exists(42) is False

    def test_nonexistent_skill_returns_false(self):
        """A skill that doesn't exist returns False."""
        assert _skill_exists("nonexistent-skill-xyz-abc-999") is False


class TestTaskIdPattern:
    """Tests for TASK_ID_PATTERN regex."""

    def test_valid_kebab(self):
        """Simple kebab-case task ID matches."""
        assert TASK_ID_PATTERN.match("valid-task-01") is not None

    def test_valid_alphanumeric(self):
        """All-alphanumeric task ID matches."""
        assert TASK_ID_PATTERN.match("abc123def") is not None

    def test_too_short_one_char(self):
        """Single character task ID does not match."""
        assert TASK_ID_PATTERN.match("a") is None

    def test_two_chars(self):
        """Two char task ID is too short."""
        assert TASK_ID_PATTERN.match("ab") is None

    def test_uppercase_rejected(self):
        """Uppercase letters are rejected."""
        assert TASK_ID_PATTERN.match("Invalid-Task") is None

    def test_underscore_rejected(self):
        """Underscores are rejected."""
        assert TASK_ID_PATTERN.match("invalid_task") is None

    def test_starts_with_hyphen(self):
        """Leading hyphen is rejected."""
        assert TASK_ID_PATTERN.match("-task-01") is None

    def test_ends_with_hyphen(self):
        """Trailing hyphen is rejected."""
        assert TASK_ID_PATTERN.match("task-01-") is None

    def test_exactly_three_chars(self):
        """Exactly three chars (minimum) matches."""
        assert TASK_ID_PATTERN.match("abc") is not None


# ---------------------------------------------------------------------------
# CoreProtocolValidator — validate_delegate_core
# ---------------------------------------------------------------------------

class TestValidateDelegateCore:
    """Tests for CoreProtocolValidator.validate_delegate_core."""

    def test_valid_delegate_passes(self, core_validator, valid_delegate):
        """A fully-valid DELEGATE returns (True, [])."""
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert ok is True
        assert errors == []

    def test_empty_dict_fails_all_fields(self, core_validator):
        """Empty dict fails with errors for all 7 required fields."""
        ok, errors = core_validator.validate_delegate_core({})
        assert not ok
        assert len(errors) >= 5

    # ── task_id ──────────────────────────────────────────────────────────────

    def test_missing_task_id(self, core_validator, valid_delegate):
        """Missing task_id produces an error."""
        del valid_delegate["task_id"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("task_id" in e for e in errors)

    def test_task_id_not_a_string(self, core_validator, valid_delegate):
        """Non-string task_id is rejected."""
        valid_delegate["task_id"] = 123
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("task_id" in e for e in errors)

    def test_task_id_none_rejected(self, core_validator, valid_delegate):
        """None task_id is rejected."""
        valid_delegate["task_id"] = None
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("task_id" in e for e in errors)

    def test_task_id_uppercase_rejected(self, core_validator, valid_delegate):
        """Uppercase task_id fails kebab-case check."""
        valid_delegate["task_id"] = "Invalid-Task"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("task_id" in e for e in errors)

    def test_task_id_underscore_rejected(self, core_validator, valid_delegate):
        """Underscore in task_id fails kebab-case check."""
        valid_delegate["task_id"] = "invalid_task"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("task_id" in e for e in errors)

    def test_task_id_too_short(self, core_validator, valid_delegate):
        """task_id with 2 characters is too short."""
        valid_delegate["task_id"] = "ab"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok

    def test_task_id_leading_hyphen_rejected(self, core_validator, valid_delegate):
        """task_id starting with a hyphen is rejected."""
        valid_delegate["task_id"] = "-bad-id"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok

    # ── skill ─────────────────────────────────────────────────────────────────

    def test_missing_skill(self, core_validator, valid_delegate):
        """Missing skill field produces an error."""
        del valid_delegate["skill"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("skill" in e for e in errors)

    def test_skill_none_rejected(self, core_validator, valid_delegate):
        """None skill is rejected."""
        valid_delegate["skill"] = None
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("skill" in e for e in errors)

    def test_skill_not_a_string(self, core_validator, valid_delegate):
        """Non-string skill is rejected."""
        valid_delegate["skill"] = 42
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("skill" in e for e in errors)

    def test_unknown_skill_rejected(self, core_validator, valid_delegate):
        """A skill that doesn't exist in skills/ is rejected."""
        valid_delegate["skill"] = "nonexistent-skill-xyz-123"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("skill" in e for e in errors)

    # ── agent ─────────────────────────────────────────────────────────────────

    def test_missing_agent(self, core_validator, valid_delegate):
        """Missing agent field produces an error."""
        del valid_delegate["agent"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("agent" in e for e in errors)

    def test_agent_none_rejected(self, core_validator, valid_delegate):
        """None agent is rejected."""
        valid_delegate["agent"] = None
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("agent" in e for e in errors)

    def test_invalid_agent(self, core_validator, valid_delegate):
        """Agent not in VALID_AGENTS is rejected."""
        valid_delegate["agent"] = "random-person"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("agent" in e for e in errors)

    def test_all_valid_agents_accepted(self, core_validator, valid_delegate):
        """All VALID_AGENTS values pass agent validation."""
        for agent in VALID_AGENTS:
            valid_delegate["agent"] = agent
            _, errors = core_validator.validate_delegate_core(valid_delegate)
            agent_errors = [e for e in errors if "agent" in e]
            assert agent_errors == [], f"Agent '{agent}' unexpectedly rejected: {agent_errors}"

    # ── scope ─────────────────────────────────────────────────────────────────

    def test_missing_scope(self, core_validator, valid_delegate):
        """Missing scope field produces an error."""
        del valid_delegate["scope"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("scope" in e for e in errors)

    def test_scope_none_rejected(self, core_validator, valid_delegate):
        """None scope is rejected."""
        valid_delegate["scope"] = None
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("scope" in e for e in errors)

    def test_scope_too_short(self, core_validator, valid_delegate):
        """Scope with fewer than 15 words is rejected."""
        valid_delegate["scope"] = "Too short scope here"  # 4 words
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("scope" in e for e in errors)

    def test_scope_exactly_15_words(self, core_validator, valid_delegate):
        """Scope with exactly 15 words passes."""
        valid_delegate["scope"] = (
            "one two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen"
        )
        _, errors = core_validator.validate_delegate_core(valid_delegate)
        scope_errors = [e for e in errors if "scope" in e]
        assert scope_errors == []

    def test_scope_not_string(self, core_validator, valid_delegate):
        """Non-string scope is rejected."""
        valid_delegate["scope"] = ["list", "instead", "of", "string"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("scope" in e for e in errors)

    # ── success_criteria ──────────────────────────────────────────────────────

    def test_missing_success_criteria(self, core_validator, valid_delegate):
        """Missing success_criteria produces an error."""
        del valid_delegate["success_criteria"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("success_criteria" in e for e in errors)

    def test_empty_success_criteria(self, core_validator, valid_delegate):
        """Empty list for success_criteria is rejected."""
        valid_delegate["success_criteria"] = []
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("success_criteria" in e for e in errors)

    def test_success_criteria_not_list(self, core_validator, valid_delegate):
        """Non-list success_criteria is rejected."""
        valid_delegate["success_criteria"] = "just a string"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("success_criteria" in e for e in errors)

    def test_success_criteria_single_item_accepted(self, core_validator, valid_delegate):
        """Single-item success_criteria passes."""
        valid_delegate["success_criteria"] = ["Tests pass"]
        _, errors = core_validator.validate_delegate_core(valid_delegate)
        sc_errors = [e for e in errors if "success_criteria" in e]
        assert sc_errors == []

    # ── plan ─────────────────────────────────────────────────────────────────

    def test_missing_plan(self, core_validator, valid_delegate):
        """Missing plan field produces an error."""
        del valid_delegate["plan"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan" in e for e in errors)

    def test_plan_none_rejected(self, core_validator, valid_delegate):
        """None plan produces an error."""
        valid_delegate["plan"] = None
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan" in e for e in errors)

    def test_plan_with_one_step(self, core_validator, valid_delegate):
        """Plan with only 1 step is rejected (requires >= 2)."""
        valid_delegate["plan"] = ["Only one step provided"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan" in e for e in errors)

    def test_plan_step_too_short(self, core_validator, valid_delegate):
        """Plan step with fewer than 3 words is rejected."""
        valid_delegate["plan"] = [
            "Short step",  # 2 words
            "Another valid step with enough words for the plan",
        ]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan[0]" in e for e in errors)

    def test_plan_not_list(self, core_validator, valid_delegate):
        """Non-list plan is rejected."""
        valid_delegate["plan"] = "just a string plan"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan" in e for e in errors)

    def test_plan_with_valid_two_steps(self, core_validator, valid_delegate):
        """Plan with exactly 2 valid steps passes plan checks."""
        valid_delegate["plan"] = [
            "Step one with enough words here",
            "Step two with enough words here",
        ]
        _, errors = core_validator.validate_delegate_core(valid_delegate)
        plan_errors = [e for e in errors if "plan" in e]
        assert plan_errors == []

    def test_plan_empty_list(self, core_validator, valid_delegate):
        """Empty list plan is rejected."""
        valid_delegate["plan"] = []
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("plan" in e for e in errors)

    # ── context ───────────────────────────────────────────────────────────────

    def test_missing_context(self, core_validator, valid_delegate):
        """Missing context produces an error."""
        del valid_delegate["context"]
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("context" in e for e in errors)

    def test_context_none_rejected(self, core_validator, valid_delegate):
        """None context produces an error."""
        valid_delegate["context"] = None
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("context" in e for e in errors)

    def test_context_string_too_short(self, core_validator, valid_delegate):
        """String context with fewer than 20 words is rejected."""
        valid_delegate["context"] = "Too short context string here"  # 5 words
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("context" in e for e in errors)

    def test_context_string_exactly_20_words(self, core_validator, valid_delegate):
        """Context string with exactly 20 words passes."""
        valid_delegate["context"] = (
            "one two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
        )
        _, errors = core_validator.validate_delegate_core(valid_delegate)
        context_errors = [e for e in errors if "context" in e]
        assert context_errors == []

    def test_context_as_non_empty_list(self, core_validator, valid_delegate):
        """Context as a non-empty list is valid."""
        valid_delegate["context"] = ["Context item one", "Context item two"]
        _, errors = core_validator.validate_delegate_core(valid_delegate)
        context_errors = [e for e in errors if "context" in e]
        assert context_errors == []

    def test_context_as_empty_list(self, core_validator, valid_delegate):
        """Context as an empty list is rejected."""
        valid_delegate["context"] = []
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("context" in e for e in errors)

    def test_context_invalid_type_dict(self, core_validator, valid_delegate):
        """Context as a dict is rejected."""
        valid_delegate["context"] = {"key": "value"}
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        assert not ok
        assert any("context" in e for e in errors)

    def test_multiple_missing_fields_all_reported(self, core_validator):
        """All missing required fields are reported in a single call."""
        ok, errors = core_validator.validate_delegate_core({})
        assert not ok
        assert len(errors) >= 5


# ---------------------------------------------------------------------------
# CoreProtocolValidator — validate_handback_core
# ---------------------------------------------------------------------------

class TestValidateHandbackCore:
    """Tests for CoreProtocolValidator.validate_handback_core."""

    def test_valid_handback_passes(self, core_validator, valid_handback):
        """A fully-valid HANDBACK returns (True, [])."""
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert ok is True
        assert errors == []

    # ── task_id ──────────────────────────────────────────────────────────────

    def test_missing_task_id(self, core_validator, valid_handback):
        """Missing task_id produces an error."""
        del valid_handback["task_id"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("task_id" in e for e in errors)

    def test_task_id_not_string(self, core_validator, valid_handback):
        """Non-string task_id is rejected."""
        valid_handback["task_id"] = 99
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok

    def test_task_id_none_rejected(self, core_validator, valid_handback):
        """None task_id is rejected."""
        valid_handback["task_id"] = None
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok

    # ── status ────────────────────────────────────────────────────────────────

    def test_missing_status(self, core_validator, valid_handback):
        """Missing status produces an error."""
        del valid_handback["status"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("status" in e for e in errors)

    def test_invalid_status(self, core_validator, valid_handback):
        """Status not in VALID_STATUSES is rejected."""
        valid_handback["status"] = "unknown"
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("status" in e for e in errors)

    def test_all_valid_statuses_accepted(self, core_validator, valid_handback):
        """Every value in VALID_STATUSES passes status validation."""
        for status in VALID_STATUSES:
            valid_handback["status"] = status
            _, errors = core_validator.validate_handback_core(valid_handback)
            status_errors = [e for e in errors if "status" in e]
            assert status_errors == [], f"Status '{status}' rejected: {status_errors}"

    # ── output ────────────────────────────────────────────────────────────────

    def test_missing_output(self, core_validator, valid_handback):
        """Missing output key produces an error."""
        del valid_handback["output"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("output" in e for e in errors)

    def test_output_can_be_none(self, core_validator, valid_handback):
        """output key present with None value is acceptable."""
        valid_handback["output"] = None
        _, errors = core_validator.validate_handback_core(valid_handback)
        output_errors = [e for e in errors if "output" in e]
        assert output_errors == []

    def test_output_can_be_dict(self, core_validator, valid_handback):
        """output key present with dict value is acceptable."""
        valid_handback["output"] = {"files": ["a.py", "b.py"]}
        _, errors = core_validator.validate_handback_core(valid_handback)
        output_errors = [e for e in errors if "output" in e]
        assert output_errors == []

    # ── metrics ───────────────────────────────────────────────────────────────

    def test_missing_metrics(self, core_validator, valid_handback):
        """Missing metrics produces an error."""
        del valid_handback["metrics"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("metrics" in e for e in errors)

    def test_metrics_none_rejected(self, core_validator, valid_handback):
        """None metrics is rejected."""
        valid_handback["metrics"] = None
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok

    def test_metrics_not_dict(self, core_validator, valid_handback):
        """Non-dict metrics is rejected."""
        valid_handback["metrics"] = "not a dict"
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("metrics" in e for e in errors)

    def test_metrics_quality_missing(self, core_validator, valid_handback):
        """Missing metrics.quality produces an error."""
        del valid_handback["metrics"]["quality"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("quality" in e for e in errors)

    def test_metrics_quality_above_range(self, core_validator, valid_handback):
        """metrics.quality > 1.0 is rejected."""
        valid_handback["metrics"]["quality"] = 1.5
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("quality" in e for e in errors)

    def test_metrics_quality_below_range(self, core_validator, valid_handback):
        """metrics.quality < 0.0 is rejected."""
        valid_handback["metrics"]["quality"] = -0.1
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("quality" in e for e in errors)

    def test_metrics_quality_at_zero(self, core_validator, valid_handback):
        """metrics.quality == 0.0 is accepted (boundary)."""
        valid_handback["metrics"]["quality"] = 0.0
        _, errors = core_validator.validate_handback_core(valid_handback)
        quality_errors = [e for e in errors if "quality" in e]
        assert quality_errors == []

    def test_metrics_quality_at_one(self, core_validator, valid_handback):
        """metrics.quality == 1.0 is accepted (boundary)."""
        valid_handback["metrics"]["quality"] = 1.0
        _, errors = core_validator.validate_handback_core(valid_handback)
        quality_errors = [e for e in errors if "quality" in e]
        assert quality_errors == []

    def test_metrics_quality_not_number(self, core_validator, valid_handback):
        """String quality is rejected."""
        valid_handback["metrics"]["quality"] = "high"
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("quality" in e for e in errors)

    def test_metrics_tokens_negative(self, core_validator, valid_handback):
        """Negative tokens is rejected."""
        valid_handback["metrics"]["tokens"] = -1
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("tokens" in e for e in errors)

    def test_metrics_tokens_not_int(self, core_validator, valid_handback):
        """Float tokens is rejected (must be int)."""
        valid_handback["metrics"]["tokens"] = 1.5
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("tokens" in e for e in errors)

    def test_metrics_tokens_zero_accepted(self, core_validator, valid_handback):
        """tokens == 0 is accepted."""
        valid_handback["metrics"]["tokens"] = 0
        _, errors = core_validator.validate_handback_core(valid_handback)
        token_errors = [e for e in errors if "tokens" in e]
        assert token_errors == []

    def test_metrics_tokens_missing(self, core_validator, valid_handback):
        """Missing tokens produces an error."""
        del valid_handback["metrics"]["tokens"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("tokens" in e for e in errors)

    def test_metrics_cost_negative(self, core_validator, valid_handback):
        """Negative cost is rejected."""
        valid_handback["metrics"]["cost"] = -0.01
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("cost" in e for e in errors)

    def test_metrics_cost_missing(self, core_validator, valid_handback):
        """Missing cost produces an error."""
        del valid_handback["metrics"]["cost"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("cost" in e for e in errors)

    def test_metrics_cost_zero_accepted(self, core_validator, valid_handback):
        """cost == 0 is accepted."""
        valid_handback["metrics"]["cost"] = 0
        _, errors = core_validator.validate_handback_core(valid_handback)
        cost_errors = [e for e in errors if "cost" in e]
        assert cost_errors == []

    def test_metrics_cost_not_number(self, core_validator, valid_handback):
        """String cost is rejected."""
        valid_handback["metrics"]["cost"] = "cheap"
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("cost" in e for e in errors)

    def test_metrics_duration_negative(self, core_validator, valid_handback):
        """Negative duration_seconds is rejected."""
        valid_handback["metrics"]["duration_seconds"] = -1.0
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("duration_seconds" in e for e in errors)

    def test_metrics_duration_missing(self, core_validator, valid_handback):
        """Missing duration_seconds produces an error."""
        del valid_handback["metrics"]["duration_seconds"]
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("duration_seconds" in e for e in errors)

    def test_metrics_duration_zero_accepted(self, core_validator, valid_handback):
        """duration_seconds == 0 is accepted."""
        valid_handback["metrics"]["duration_seconds"] = 0
        _, errors = core_validator.validate_handback_core(valid_handback)
        dur_errors = [e for e in errors if "duration_seconds" in e]
        assert dur_errors == []

    def test_metrics_duration_not_number(self, core_validator, valid_handback):
        """String duration_seconds is rejected."""
        valid_handback["metrics"]["duration_seconds"] = "fast"
        ok, errors = core_validator.validate_handback_core(valid_handback)
        assert not ok
        assert any("duration_seconds" in e for e in errors)


# ---------------------------------------------------------------------------
# ExtensionValidator — validate_extensions (DELEGATE)
# ---------------------------------------------------------------------------

class TestExtensionValidatorDelegate:
    """Tests for ExtensionValidator.validate_extensions."""

    def test_no_extensions_passes(self, ext_validator):
        """DELEGATE with no optional fields passes extension validation."""
        ok, errors = ext_validator.validate_extensions({})
        assert ok is True
        assert errors == []

    def test_valid_effort_low(self, ext_validator):
        """effort='low' passes."""
        ok, errors = ext_validator.validate_extensions({"effort": "low"})
        assert ok is True

    def test_valid_effort_medium(self, ext_validator):
        """effort='medium' passes."""
        ok, errors = ext_validator.validate_extensions({"effort": "medium"})
        assert ok is True

    def test_valid_effort_high(self, ext_validator):
        """effort='high' passes."""
        ok, errors = ext_validator.validate_extensions({"effort": "high"})
        assert ok is True

    def test_invalid_effort(self, ext_validator):
        """Invalid effort value is rejected."""
        ok, errors = ext_validator.validate_extensions({"effort": "extreme"})
        assert not ok
        assert any("effort" in e for e in errors)

    def test_model_must_be_string(self, ext_validator):
        """Non-string model is rejected."""
        ok, errors = ext_validator.validate_extensions({"model": 42})
        assert not ok
        assert any("model" in e for e in errors)

    def test_model_string_accepted(self, ext_validator):
        """Any string model is accepted (soft validation)."""
        ok, errors = ext_validator.validate_extensions({"model": "any-model-name"})
        assert ok is True

    def test_budget_negative_rejected(self, ext_validator):
        """Negative budget is rejected."""
        ok, errors = ext_validator.validate_extensions({"budget": -1})
        assert not ok
        assert any("budget" in e for e in errors)

    def test_budget_zero_accepted(self, ext_validator):
        """Budget of 0 is accepted."""
        ok, errors = ext_validator.validate_extensions({"budget": 0})
        assert ok is True

    def test_budget_positive_float(self, ext_validator):
        """Positive float budget is accepted."""
        ok, errors = ext_validator.validate_extensions({"budget": 10.0})
        assert ok is True

    def test_budget_not_number(self, ext_validator):
        """String budget is rejected."""
        ok, errors = ext_validator.validate_extensions({"budget": "free"})
        assert not ok
        assert any("budget" in e for e in errors)

    def test_priority_zero_rejected(self, ext_validator):
        """Priority < 1 is rejected."""
        ok, errors = ext_validator.validate_extensions({"priority": 0})
        assert not ok
        assert any("priority" in e for e in errors)

    def test_priority_eleven_rejected(self, ext_validator):
        """Priority > 10 is rejected."""
        ok, errors = ext_validator.validate_extensions({"priority": 11})
        assert not ok
        assert any("priority" in e for e in errors)

    def test_priority_boundary_one(self, ext_validator):
        """Priority == 1 is accepted."""
        ok, errors = ext_validator.validate_extensions({"priority": 1})
        assert ok is True

    def test_priority_boundary_ten(self, ext_validator):
        """Priority == 10 is accepted."""
        ok, errors = ext_validator.validate_extensions({"priority": 10})
        assert ok is True

    def test_priority_not_int(self, ext_validator):
        """Float priority is rejected."""
        ok, errors = ext_validator.validate_extensions({"priority": 5.5})
        assert not ok
        assert any("priority" in e for e in errors)

    def test_deadline_not_string(self, ext_validator):
        """Non-string deadline is rejected."""
        ok, errors = ext_validator.validate_extensions({"deadline": 12345})
        assert not ok
        assert any("deadline" in e for e in errors)

    def test_deadline_string_accepted(self, ext_validator):
        """ISO 8601 string deadline is accepted."""
        ok, errors = ext_validator.validate_extensions({"deadline": "2024-12-31T00:00:00Z"})
        assert ok is True

    def test_dependencies_not_list(self, ext_validator):
        """Non-list dependencies is rejected."""
        ok, errors = ext_validator.validate_extensions({"dependencies": "task-001"})
        assert not ok
        assert any("dependencies" in e for e in errors)

    def test_dependencies_list_accepted(self, ext_validator):
        """List dependencies is accepted."""
        ok, errors = ext_validator.validate_extensions({"dependencies": ["task-001", "task-002"]})
        assert ok is True

    def test_dependencies_empty_list_accepted(self, ext_validator):
        """Empty list dependencies is accepted."""
        ok, errors = ext_validator.validate_extensions({"dependencies": []})
        assert ok is True

    def test_parent_task_id_not_string(self, ext_validator):
        """Non-string parent_task_id is rejected."""
        ok, errors = ext_validator.validate_extensions({"parent_task_id": 99})
        assert not ok
        assert any("parent_task_id" in e for e in errors)

    def test_parent_task_id_string_accepted(self, ext_validator):
        """String parent_task_id is accepted."""
        ok, errors = ext_validator.validate_extensions({"parent_task_id": "parent-01"})
        assert ok is True

    def test_retry_context_not_dict(self, ext_validator):
        """Non-dict retry_context is rejected."""
        ok, errors = ext_validator.validate_extensions({"retry_context": "retry"})
        assert not ok
        assert any("retry_context" in e for e in errors)

    def test_retry_context_dict_accepted(self, ext_validator):
        """Dict retry_context is accepted."""
        ok, errors = ext_validator.validate_extensions({"retry_context": {"attempt": 2}})
        assert ok is True

    def test_all_valid_extensions_together(self, ext_validator):
        """All valid extension fields together pass."""
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
        """HANDBACK with no extension fields passes."""
        ok, errors = ext_validator.validate_handback_extensions({})
        assert ok is True
        assert errors == []

    def test_retry_count_negative_rejected(self, ext_validator):
        """Negative retry_count is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"retry_count": -1})
        assert not ok
        assert any("retry_count" in e for e in errors)

    def test_retry_count_zero_accepted(self, ext_validator):
        """retry_count of 0 is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"retry_count": 0})
        assert ok is True

    def test_retry_count_not_int(self, ext_validator):
        """Float retry_count is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"retry_count": 1.5})
        assert not ok
        assert any("retry_count" in e for e in errors)

    def test_model_used_not_string(self, ext_validator):
        """Non-string model_used is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"model_used": 42})
        assert not ok
        assert any("model_used" in e for e in errors)

    def test_model_used_string_accepted(self, ext_validator):
        """String model_used is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"model_used": "claude-opus-4.7"})
        assert ok is True

    def test_effort_actual_invalid(self, ext_validator):
        """Invalid effort_actual is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"effort_actual": "extreme"})
        assert not ok
        assert any("effort_actual" in e for e in errors)

    def test_effort_actual_low(self, ext_validator):
        """effort_actual='low' is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"effort_actual": "low"})
        assert ok is True

    def test_effort_actual_medium(self, ext_validator):
        """effort_actual='medium' is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"effort_actual": "medium"})
        assert ok is True

    def test_effort_actual_high(self, ext_validator):
        """effort_actual='high' is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"effort_actual": "high"})
        assert ok is True

    def test_flags_not_list(self, ext_validator):
        """Non-list flags is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"flags": "flag1"})
        assert not ok
        assert any("flags" in e for e in errors)

    def test_flags_list_accepted(self, ext_validator):
        """List flags is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"flags": ["needs-review"]})
        assert ok is True

    def test_error_not_string(self, ext_validator):
        """Non-string error is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"error": {"msg": "oops"}})
        assert not ok
        assert any("error" in e for e in errors)

    def test_error_string_accepted(self, ext_validator):
        """String error is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"error": "Something went wrong"})
        assert ok is True

    def test_children_created_not_list(self, ext_validator):
        """Non-list children_created is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"children_created": "child-01"})
        assert not ok
        assert any("children_created" in e for e in errors)

    def test_children_created_list_accepted(self, ext_validator):
        """List children_created is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({"children_created": ["child-01"]})
        assert ok is True

    def test_children_results_not_dict(self, ext_validator):
        """Non-dict children_results is rejected."""
        ok, errors = ext_validator.validate_handback_extensions({"children_results": ["x"]})
        assert not ok
        assert any("children_results" in e for e in errors)

    def test_children_results_dict_accepted(self, ext_validator):
        """Dict children_results is accepted."""
        ok, errors = ext_validator.validate_handback_extensions({
            "children_results": {"child-01": {"status": "done"}}
        })
        assert ok is True

    def test_all_valid_handback_extensions_together(self, ext_validator):
        """All valid handback extension fields together pass."""
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
# Performance: core validation <50ms, extension <10ms
# ---------------------------------------------------------------------------

class TestPerformance:
    """Performance checks per spec: core <50ms, extensions <10ms."""

    def test_core_delegate_validation_under_50ms(self, core_validator, valid_delegate):
        """Core delegate validation completes in under 50ms."""
        start = time.monotonic()
        core_validator.validate_delegate_core(valid_delegate)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"Core validation took {elapsed_ms:.1f}ms, expected <50ms"

    def test_core_handback_validation_under_50ms(self, core_validator, valid_handback):
        """Core handback validation completes in under 50ms."""
        start = time.monotonic()
        core_validator.validate_handback_core(valid_handback)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"Core handback validation took {elapsed_ms:.1f}ms, expected <50ms"

    def test_extension_validation_under_10ms(self, ext_validator):
        """Extension validation completes in under 10ms."""
        extensions = {
            "effort": "medium",
            "model": "claude-sonnet-4.5",
            "budget": 5.0,
            "priority": 5,
        }
        start = time.monotonic()
        ext_validator.validate_extensions(extensions)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 10, f"Extension validation took {elapsed_ms:.1f}ms, expected <10ms"


# ---------------------------------------------------------------------------
# Backward-compat: unknown extensions ignored by core validator
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Ensure unknown extension fields do not affect core validation."""

    def test_unknown_extensions_ignored_by_core(self, core_validator, valid_delegate):
        """Extra keys not in core fields do not cause core validation errors."""
        valid_delegate["effort"] = "high"
        valid_delegate["model"] = "gpt-5.5"
        valid_delegate["unknown_field"] = "some_value"
        ok, errors = core_validator.validate_delegate_core(valid_delegate)
        # Core validator only checks 7 core fields; extras must not cause failures
        assert ok is True, f"Unexpected errors: {errors}"

