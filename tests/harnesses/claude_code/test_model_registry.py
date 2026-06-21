"""
Regression tests for Claude Code harness ModelRegistry.

Tests for model lifecycle tracking: known/unknown models, deprecation
status, canonical name resolution, tier lookup, and validation.
"""

from __future__ import annotations

import pytest

from src.harnesses.claude_code.model_registry import (
    MODEL_VERSIONS,
    ModelRegistry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def registry() -> ModelRegistry:
    """Shared ModelRegistry instance."""
    return ModelRegistry()


# ---------------------------------------------------------------------------
# M1.1-M1.4: is_known() lookup
# ---------------------------------------------------------------------------


class TestIsKnown:
    """Model membership checks."""

    def test_known_active_model(self, registry: ModelRegistry) -> None:
        """claude-haiku-4.5 is a known model."""
        assert registry.is_known("claude-haiku-4.5") is True

    def test_known_sonnet_model(self, registry: ModelRegistry) -> None:
        """claude-sonnet-4.5 is a known model."""
        assert registry.is_known("claude-sonnet-4.5") is True

    def test_known_alias_haiku(self, registry: ModelRegistry) -> None:
        """Short alias 'haiku' is a known model."""
        assert registry.is_known("haiku") is True

    def test_known_alias_sonnet(self, registry: ModelRegistry) -> None:
        """Short alias 'sonnet' is a known model."""
        assert registry.is_known("sonnet") is True

    def test_known_alias_opus(self, registry: ModelRegistry) -> None:
        """Short alias 'opus' is a known model."""
        assert registry.is_known("opus") is True

    def test_unknown_model_returns_false(
        self, registry: ModelRegistry
    ) -> None:
        """Unregistered model name returns False."""
        assert registry.is_known("gpt-4o") is False

    def test_unknown_empty_string_returns_false(
        self, registry: ModelRegistry
    ) -> None:
        """Empty string returns False."""
        assert registry.is_known("") is False

    def test_unknown_random_string_returns_false(
        self, registry: ModelRegistry
    ) -> None:
        """Arbitrary string returns False."""
        assert registry.is_known("not-a-real-model") is False


# ---------------------------------------------------------------------------
# M1.5-M1.7: is_deprecated() status
# ---------------------------------------------------------------------------


class TestIsDeprecated:
    """Deprecation status checks."""

    def test_active_model_not_deprecated(
        self, registry: ModelRegistry
    ) -> None:
        """Active model is not deprecated."""
        assert registry.is_deprecated("claude-haiku-4.5") is False

    def test_alias_not_deprecated(self, registry: ModelRegistry) -> None:
        """Alias model is not deprecated (deprecated != alias)."""
        assert registry.is_deprecated("haiku") is False

    def test_unknown_model_not_deprecated(
        self, registry: ModelRegistry
    ) -> None:
        """Unknown model returns False (not deprecated)."""
        assert registry.is_deprecated("completely-unknown") is False

    def test_deprecated_model_returns_true(self) -> None:
        """Deprecated model entry returns True."""
        # Inject a deprecated model for this test
        custom_registry = ModelRegistry()
        custom_registry._models["claude-old-2.0"] = {
            "tier": "haiku",
            "status": "deprecated",
        }
        assert custom_registry.is_deprecated("claude-old-2.0") is True


# ---------------------------------------------------------------------------
# M1.8-M1.12: canonical() name resolution
# ---------------------------------------------------------------------------


class TestCanonical:
    """Canonical model name resolution."""

    def test_canonical_full_name_returns_self(
        self, registry: ModelRegistry
    ) -> None:
        """Full active model name resolves to itself."""
        assert registry.canonical("claude-haiku-4.5") == "claude-haiku-4.5"

    def test_canonical_sonnet_full_name(
        self, registry: ModelRegistry
    ) -> None:
        """Full sonnet name resolves to itself."""
        canonical = registry.canonical("claude-sonnet-4.5")
        assert canonical == "claude-sonnet-4.5"

    def test_canonical_haiku_alias_resolves(
        self, registry: ModelRegistry
    ) -> None:
        """'haiku' alias resolves to a known haiku active model."""
        canonical = registry.canonical("haiku")
        assert canonical is not None
        assert "haiku" in canonical
        assert registry.is_known(canonical)

    def test_canonical_sonnet_alias_resolves(
        self, registry: ModelRegistry
    ) -> None:
        """'sonnet' alias resolves to a known sonnet active model."""
        canonical = registry.canonical("sonnet")
        assert canonical is not None
        assert "sonnet" in canonical

    def test_canonical_opus_alias_resolves(
        self, registry: ModelRegistry
    ) -> None:
        """'opus' alias resolves to a known opus active model."""
        canonical = registry.canonical("opus")
        assert canonical is not None
        assert "opus" in canonical

    def test_canonical_unknown_returns_none(
        self, registry: ModelRegistry
    ) -> None:
        """Unknown model returns None from canonical()."""
        assert registry.canonical("does-not-exist") is None

    def test_canonical_returns_active_not_alias(
        self, registry: ModelRegistry
    ) -> None:
        """Resolved canonical name has status 'active', not 'alias'."""
        canonical = registry.canonical("haiku")
        assert canonical is not None
        meta = registry._models.get(canonical, {})
        assert meta.get("status") == "active"


# ---------------------------------------------------------------------------
# M1.13-M1.15: tier() lookup
# ---------------------------------------------------------------------------


class TestTier:
    """Model tier classification."""

    def test_tier_haiku_model(self, registry: ModelRegistry) -> None:
        """claude-haiku-4.5 is in the haiku tier."""
        assert registry.tier("claude-haiku-4.5") == "haiku"

    def test_tier_sonnet_model(self, registry: ModelRegistry) -> None:
        """claude-sonnet-4.5 is in the sonnet tier."""
        assert registry.tier("claude-sonnet-4.5") == "sonnet"

    def test_tier_opus_model(self, registry: ModelRegistry) -> None:
        """claude-opus-4.8 is in the opus tier."""
        assert registry.tier("claude-opus-4.8") == "opus"

    def test_tier_haiku_alias(self, registry: ModelRegistry) -> None:
        """'haiku' alias returns the haiku tier."""
        assert registry.tier("haiku") == "haiku"

    def test_tier_unknown_returns_none(self, registry: ModelRegistry) -> None:
        """Unknown model returns None from tier()."""
        assert registry.tier("unknown-model") is None


# ---------------------------------------------------------------------------
# M1.16-M1.20: validate() combined status
# ---------------------------------------------------------------------------


class TestValidate:
    """Validation combining known status, deprecation, and alias resolution."""

    def test_validate_active_model_returns_valid_no_warning(
        self, registry: ModelRegistry
    ) -> None:
        """Active full-name model is valid with no warning."""
        valid, warning = registry.validate("claude-haiku-4.5")
        assert valid is True
        assert warning is None

    def test_validate_alias_returns_valid_with_warning(
        self, registry: ModelRegistry
    ) -> None:
        """Alias resolves but returns a warning about using the alias."""
        valid, warning = registry.validate("haiku")
        assert valid is True
        assert warning is not None
        assert "alias" in warning.lower() or "resolves" in warning.lower()

    def test_validate_unknown_model_returns_invalid(
        self, registry: ModelRegistry
    ) -> None:
        """Unknown model is not valid."""
        valid, warning = registry.validate("gpt-4-turbo")
        assert valid is False
        assert "not recognized" in warning.lower()

    def test_validate_deprecated_model_returns_invalid(self) -> None:
        """Deprecated model is invalid with deprecation warning."""
        custom_registry = ModelRegistry()
        custom_registry._models["claude-old-model"] = {
            "tier": "haiku",
            "status": "deprecated",
        }
        # Also add the active replacement
        custom_registry._models["claude-haiku-4.5"] = {
            "tier": "haiku",
            "status": "active",
        }
        valid, warning = custom_registry.validate("claude-old-model")
        assert valid is False
        assert "deprecated" in warning.lower()

    def test_validate_returns_tuple_of_two(
        self, registry: ModelRegistry
    ) -> None:
        """validate() always returns a 2-tuple."""
        result = registry.validate("claude-haiku-4.5")
        assert len(result) == 2

    def test_validate_sonnet_4_6_active(
        self, registry: ModelRegistry
    ) -> None:
        """claude-sonnet-4.6 is active and validates cleanly."""
        valid, warning = registry.validate("claude-sonnet-4.6")
        assert valid is True
        assert warning is None


# ---------------------------------------------------------------------------
# M1.21: MODEL_VERSIONS constant
# ---------------------------------------------------------------------------


class TestModelVersionsConstant:
    """MODEL_VERSIONS module-level constant structure."""

    def test_model_versions_is_dict(self) -> None:
        """MODEL_VERSIONS is a dictionary."""
        assert isinstance(MODEL_VERSIONS, dict)

    def test_model_versions_has_required_keys(self) -> None:
        """All entries have 'tier' and 'status' keys."""
        for model, meta in MODEL_VERSIONS.items():
            assert "tier" in meta, f"{model} missing 'tier'"
            assert "status" in meta, f"{model} missing 'status'"

    def test_model_versions_status_values_valid(self) -> None:
        """All status values are from the expected set."""
        valid_statuses = {"active", "alias", "deprecated"}
        for model, meta in MODEL_VERSIONS.items():
            assert meta["status"] in valid_statuses, (
                f"{model} has invalid status '{meta['status']}'"
            )

    def test_model_versions_has_active_haiku(self) -> None:
        """At least one active haiku model exists."""
        active_haiku = [
            m for m, meta in MODEL_VERSIONS.items()
            if meta.get("tier") == "haiku" and meta.get("status") == "active"
        ]
        assert len(active_haiku) > 0

    def test_model_versions_has_active_sonnet(self) -> None:
        """At least one active sonnet model exists."""
        active_sonnet = [
            m for m, meta in MODEL_VERSIONS.items()
            if meta.get("tier") == "sonnet" and meta.get("status") == "active"
        ]
        assert len(active_sonnet) > 0

    def test_registry_is_independent_copy(self) -> None:
        """ModelRegistry uses a copy of MODEL_VERSIONS (mutations are isolated)."""
        r1 = ModelRegistry()
        r2 = ModelRegistry()
        r1._models["test-isolation-model"] = {"tier": "haiku", "status": "active"}
        assert "test-isolation-model" not in r2._models
