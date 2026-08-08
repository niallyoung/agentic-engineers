"""
Tests for DelegateValidator — pre-flight validation of DELEGATE blocks.

Covers Groups A (structure), B (content quality), C (routing sanity),
and all static helper methods.
"""

import pytest
from src.orchestration.agents.delegate_validator import DelegateValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_delegate(**overrides) -> dict:
    """Return a minimally valid DELEGATE block, optionally overriding fields."""
    delegate = {
        "task_id": "2025-01-01-add-retry-logic-abc123",
        "role": "senior_engineer",
        "model": "claude-sonnet-5",
        "effort": "high",
        "scope": (
            "Implement exponential back-off retry logic for all outbound HTTP "
            "requests in the data-pipeline service so that transient network "
            "failures do not cause cascading task failures or data loss in "
            "production systems with real customer impact."
        ),
        "plan": [
            {"action": "Audit all requests.get/post calls in data_pipeline/client.py"},
            {"action": "Implement RetryAdapter with exponential back-off"},
            {"action": "Write unit tests for retry logic in tests/test_client.py"},
        ],
        "success_criteria": [
            "All existing tests pass (pytest tests/ → 0 failures)",
            "New retry tests achieve 95% branch coverage",
            "HTTP 5xx triggers at least 3 retry attempts before raising",
        ],
        "context": (
            "The data-pipeline service uses the requests library to call "
            "three external APIs: authentication, payments, and inventory. "
            "Transient network failures at the auth API caused twelve incidents "
            "in the past month. The current implementation has no retry logic "
            "whatsoever. We require exponential back-off with jitter following "
            "RFC 8707 recommendations. The engineering team agreed on a maximum "
            "of five retries, a thirty-second ceiling, and a jitter factor of "
            "zero-point-five. No third-party retry library such as tenacity is "
            "permitted; the implementation must be native Python only. The change "
            "is scoped exclusively to data_pipeline/client.py and does not touch "
            "any other modules in the service architecture at all."
        ),
        "out_of_scope": ["Rate limiting", "Circuit breaker pattern"],
    }
    delegate.update(overrides)
    return delegate


# ---------------------------------------------------------------------------
# Group A: Structure (hard gates)
# ---------------------------------------------------------------------------

class TestGroupAStructure:
    def test_valid_delegate_passes_all_checks(self):
        """A fully valid DELEGATE block passes all checks with no failures."""
        ok, failures = DelegateValidator.validate_delegate_pre_flight(_valid_delegate())
        assert ok is True
        group_a_failures = [f for f in failures if f.startswith("A")]
        assert group_a_failures == []

    def test_a1_missing_task_id_fails(self):
        """A1: Missing task_id triggers a validation failure."""
        delegate = _valid_delegate()
        del delegate["task_id"]
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A1" in f for f in failures)

    def test_a1_invalid_task_id_format_fails(self):
        """A1: task_id must match YYYY-MM-DD-kebab-case format."""
        delegate = _valid_delegate(task_id="not-a-valid-id")
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A1" in f for f in failures)

    def test_a3_missing_role_fails(self):
        """A3: Missing role triggers an A3 validation failure."""
        delegate = _valid_delegate()
        del delegate["role"]
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A3" in f for f in failures)

    def test_a3_invalid_role_fails(self):
        """A3: Unrecognised role triggers an A3 validation failure."""
        delegate = _valid_delegate(role="wizard_engineer")
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A3" in f for f in failures)

    def test_a5_high_effort_with_engineer_role_fails(self):
        """A5: effort=high with role=engineer triggers A5 failure (role too low)."""
        delegate = _valid_delegate(role="engineer", effort="high",
                                   model="claude-haiku-4.5")
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A5" in f for f in failures)

    def test_a6_missing_scope_fails(self):
        """A6: Missing scope triggers an A6 validation failure."""
        delegate = _valid_delegate()
        del delegate["scope"]
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A6" in f for f in failures)

    def test_a6_empty_scope_fails(self):
        """A6: Empty scope string triggers an A6 validation failure."""
        delegate = _valid_delegate(scope="")
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert ok is False
        assert any("A6" in f for f in failures)

    def test_empty_success_criteria_no_a_group_failure(self):
        """Empty success_criteria doesn't trigger hard-gate A-group failures."""
        delegate = _valid_delegate(success_criteria=[])
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        a_failures = [f for f in failures if f.startswith("A")]
        assert a_failures == []


# ---------------------------------------------------------------------------
# Group B: Content Quality
# ---------------------------------------------------------------------------

class TestGroupBContentQuality:
    def test_b_scope_with_fewer_than_15_words_fails(self):
        """B1: Scope with < 15 words triggers B failure."""
        delegate = _valid_delegate(scope="Fix the authentication service bug now.")
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        # Scope should be flagged as too short
        b_failures = [f for f in failures if f.startswith("B")]
        # Short scope without action verb → B failure
        assert not ok or b_failures  # either way, it's flagged

    def test_b_success_criteria_aspirational_fails(self):
        """B: Aspirational/vague criteria (no numbers) should be flagged."""
        delegate = _valid_delegate(success_criteria=["Works well", "Looks nice"])
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        b_failures = [f for f in failures if f.startswith("B")]
        assert len(b_failures) > 0

    def test_b_plan_with_no_test_step_flagged(self):
        """B4: plan must include at least one step covering testing."""
        delegate = _valid_delegate(plan=[
            {"action": "Implement the retry adapter class"},
            {"action": "Update all HTTP call sites"},
        ])
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        b4_failures = [f for f in failures if "B4" in f]
        assert len(b4_failures) > 0

    def test_b_context_under_100_words_fails(self):
        """B5: context < 100 words triggers B5 failure."""
        delegate = _valid_delegate(context="Short context with fewer than one hundred words total.")
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        b5_failures = [f for f in failures if "B5" in f]
        assert len(b5_failures) > 0

    def test_b6_high_effort_without_out_of_scope_fails(self):
        """B6: effort=high without out_of_scope list triggers B6 failure."""
        delegate = _valid_delegate(effort="high")
        del delegate["out_of_scope"]
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        b6_failures = [f for f in failures if "B6" in f]
        assert len(b6_failures) > 0

    def test_b_medium_effort_without_out_of_scope_fails(self):
        """B6: effort=medium also requires out_of_scope."""
        delegate = _valid_delegate(effort="medium", role="engineer")
        del delegate["out_of_scope"]
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        b6_failures = [f for f in failures if "B6" in f]
        assert len(b6_failures) > 0


# ---------------------------------------------------------------------------
# Group C: Routing Sanity
# ---------------------------------------------------------------------------

class TestGroupCRoutingSanity:
    def test_c1_high_effort_with_engineer_role_fails(self):
        """C1: effort=high routed to engineer triggers C1 failure."""
        delegate = _valid_delegate(effort="high", role="engineer")
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        c1_failures = [f for f in failures if "C1" in f]
        assert len(c1_failures) > 0

    def test_c1_high_effort_with_senior_engineer_passes(self):
        """C1: effort=high with senior_engineer passes routing sanity."""
        delegate = _valid_delegate(effort="high", role="senior_engineer")
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        c1_failures = [f for f in failures if "C1" in f]
        assert len(c1_failures) == 0

    def test_c2_security_scope_requires_security_engineer(self):
        """C2: Security-scoped task must be routed to security_engineer."""
        delegate = _valid_delegate(
            scope=(
                "Audit SSL/TLS configuration in all microservices to ensure "
                "security certificates are valid and no weak ciphers are used "
                "across the entire authentication and payment service fleet."
            ),
            role="engineer",
        )
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        c2_failures = [f for f in failures if "C2" in f]
        assert len(c2_failures) > 0

    def test_c3_cross_service_architecture_requires_principal_engineer(self):
        """C3: Cross-service architecture task must route to principal_engineer."""
        delegate = _valid_delegate(
            scope=(
                "Design cross-service architecture for the event bus to support "
                "high-throughput message passing between twelve microservices "
                "while maintaining backward compatibility with existing consumers."
            ),
            role="engineer",
        )
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        c3_failures = [f for f in failures if "C3" in f]
        assert len(c3_failures) > 0

    def test_c4_code_review_task_must_route_to_lead_or_quality_engineer(self):
        """C4: Code review / audit task must go to lead_engineer or quality_engineer."""
        delegate = _valid_delegate(
            scope=(
                "Perform a thorough code review and audit of the payment module "
                "to identify structural issues and ensure clean code standards "
                "are followed throughout the entire payment processing pipeline."
            ),
            role="engineer",
        )
        _ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        c4_failures = [f for f in failures if "C4" in f]
        assert len(c4_failures) > 0


# ---------------------------------------------------------------------------
# Static helper methods
# ---------------------------------------------------------------------------

class TestValidTaskId:
    def test_valid_task_id_format_passes(self):
        assert DelegateValidator._valid_task_id("2025-01-15-add-retry-logic") is True

    def test_valid_task_id_with_numbers_in_slug(self):
        assert DelegateValidator._valid_task_id("2025-12-31-fix-bug-123") is True

    def test_single_char_slug_passes(self):
        assert DelegateValidator._valid_task_id("2025-01-01-a") is True

    def test_invalid_task_id_no_date_fails(self):
        assert DelegateValidator._valid_task_id("fix-the-bug") is False

    def test_invalid_task_id_wrong_date_format(self):
        assert DelegateValidator._valid_task_id("25-01-01-task") is False

    def test_invalid_task_id_uppercase_slug(self):
        assert DelegateValidator._valid_task_id("2025-01-01-UpperCase") is False

    def test_invalid_task_id_trailing_hyphen(self):
        assert DelegateValidator._valid_task_id("2025-01-01-slug-") is False


class TestValidScope:
    def test_scope_with_15_words_and_action_verb_passes(self):
        scope = (
            "Implement retry logic for HTTP requests in the authentication "
            "service to handle transient network failures gracefully."
        )
        assert DelegateValidator._valid_scope(scope) is True

    def test_scope_under_15_words_fails(self):
        assert DelegateValidator._valid_scope("Fix the bug.") is False

    def test_scope_without_action_verb_fails(self):
        scope = (
            "The service has a problem with network connections that sometimes "
            "fail and cause the whole system to stop working properly."
        )
        assert DelegateValidator._valid_scope(scope) is False

    def test_empty_scope_fails(self):
        assert DelegateValidator._valid_scope("") is False

    def test_scope_with_various_action_verbs_passes(self):
        verbs = ["implement", "create", "fix", "refactor", "validate", "test",
                 "design", "optimize", "review", "audit", "integrate", "migrate",
                 "add", "remove", "update", "build", "deploy", "configure"]
        for verb in verbs:
            scope = f"{verb.capitalize()} the component to handle edge cases in " \
                    f"a reliable and well-tested manner using standard practices."
            assert DelegateValidator._valid_scope(scope) is True, \
                f"Verb '{verb}' should pass scope validation"


class TestContainsSecrets:
    def test_text_with_password_detected(self):
        assert DelegateValidator._contains_secrets("db_password=secret123") is True

    def test_text_with_api_key_detected(self):
        assert DelegateValidator._contains_secrets("Set the api_key to XYZ") is True

    def test_text_with_token_detected(self):
        assert DelegateValidator._contains_secrets("Use token for auth") is True

    def test_clean_text_not_detected(self):
        assert DelegateValidator._contains_secrets("Implement retry logic with backoff") is False

    def test_case_insensitive_detection(self):
        assert DelegateValidator._contains_secrets("AWS_SECRET=abc") is True

    def test_private_key_detected(self):
        assert DelegateValidator._contains_secrets("private_key: BEGIN RSA") is True


class TestIsMeasurable:
    def test_criterion_with_percentage_is_measurable(self):
        assert DelegateValidator._is_measurable("Tests pass with 95% coverage") is True

    def test_criterion_with_count_is_measurable(self):
        assert DelegateValidator._is_measurable("Zero failures in 100 test runs") is True

    def test_aspirational_criterion_is_not_measurable(self):
        assert DelegateValidator._is_measurable("Works well") is False

    def test_looks_nice_is_not_measurable(self):
        assert DelegateValidator._is_measurable("Looks nice to users") is False

    def test_criterion_with_feels_right_not_measurable(self):
        assert DelegateValidator._is_measurable("Feels right") is False


# ---------------------------------------------------------------------------
# Validate returns (bool, list) contract
# ---------------------------------------------------------------------------

class TestValidateReturnContract:
    def test_returns_tuple_of_two(self):
        result = DelegateValidator.validate_delegate_pre_flight(_valid_delegate())
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_bool(self):
        ok, _ = DelegateValidator.validate_delegate_pre_flight(_valid_delegate())
        assert isinstance(ok, bool)

    def test_second_element_is_list(self):
        _, failures = DelegateValidator.validate_delegate_pre_flight(_valid_delegate())
        assert isinstance(failures, list)

    def test_valid_delegate_returns_true_empty_failures(self):
        ok, failures = DelegateValidator.validate_delegate_pre_flight(_valid_delegate())
        assert ok is True
        assert failures == []

    def test_invalid_delegate_returns_false(self):
        ok, failures = DelegateValidator.validate_delegate_pre_flight({})
        assert ok is False
        assert len(failures) > 0
