#!/usr/bin/env python3
"""
Tests for the canonical ModelResolver (single source of truth).

Covers:
- FALLBACK_DEFAULTS is derived from models.yaml (drift prevention via asserting test)
- fable-5 unconditional default for security_engineer
- backwards-compatible wrapper import path
- agent→model assignments unchanged vs canonical config
"""

import importlib.util
import logging
from pathlib import Path

import yaml
import pytest

from src.orchestration.models.canonical_resolver import (
    ModelResolver,
    ModelNotFoundError,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_YAML = REPO_ROOT / "src" / "config" / "models.yaml"


@pytest.fixture
def resolver():
    return ModelResolver(str(CANONICAL_YAML), fallback_to_defaults=True)


@pytest.fixture
def canonical_config():
    with open(CANONICAL_YAML) as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# AC2: FALLBACK_DEFAULTS derived from models.yaml with asserting test
# ---------------------------------------------------------------------------

class TestFallbackDefaultsDerivedFromYaml:
    def test_fallback_defaults_match_canonical_claude_models(self, resolver, canonical_config):
        """Every role's fallback default must equal its claude-provider model
        from models.yaml. This asserting test prevents future drift."""
        role_models = canonical_config["role_models"]
        for role, cfg in role_models.items():
            expected = cfg["providers"]["claude"]
            assert resolver.FALLBACK_DEFAULTS[role] == expected, (
                f"FALLBACK_DEFAULTS[{role}]={resolver.FALLBACK_DEFAULTS[role]!r} "
                f"drifted from canonical claude model {expected!r}"
            )

    def test_senior_engineer_default_is_canonical_not_drifted(self, resolver):
        """Regression: the default must come from models.yaml, not a hardcoded
        constant that drifts from canonical policy."""
        assert resolver.FALLBACK_DEFAULTS["senior_engineer"] == "claude-sonnet-5"

    def test_from_defaults_derives_same_values(self, canonical_config):
        """from_defaults() (no explicit path) must derive identical values."""
        derived = ModelResolver.from_defaults()
        role_models = canonical_config["role_models"]
        for role, cfg in role_models.items():
            assert derived.FALLBACK_DEFAULTS[role] == cfg["providers"]["claude"]

    def test_no_hardcoded_drift_for_all_eight_agents(self, resolver, canonical_config):
        """All 8 canonical agents resolve to their canonical claude model."""
        for role in canonical_config["role_models"]:
            assert resolver.resolve(role, provider="claude") == \
                canonical_config["role_models"][role]["providers"]["claude"]


# ---------------------------------------------------------------------------
# AC4: fable-5 is unconditional default for security_engineer
# ---------------------------------------------------------------------------

class TestFable5Routing:
    def test_security_engineer_default_is_fable5(self, resolver):
        """Security Engineer unconditionally routes to fable-5."""
        assert resolver.resolve("security_engineer", provider="claude") == "claude-fable-5"

    def test_fable5_in_locked_models(self):
        """LOCKED_MODELS.sh must contain the fable-5 entry."""
        locked = (REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh").read_text()
        assert "claude-fable-5" in locked

    def test_fable5_in_canonical_model_selection(self, canonical_config):
        assert "claude-fable-5" in canonical_config["model_selection"]["models"]


# ---------------------------------------------------------------------------
# AC3: backwards-compatible wrapper import path
# ---------------------------------------------------------------------------

class TestWrapperCompatibility:
    def test_old_agents_path_reexports_canonical(self):
        from src.orchestration.agents.model_resolver import ModelResolver as WrappedResolver
        assert WrappedResolver is ModelResolver

    def test_models_package_exports_resolver(self):
        from src.orchestration.models import ModelResolver as PkgResolver
        assert PkgResolver is ModelResolver


# ---------------------------------------------------------------------------
# AC6: assignments unchanged (logic migration only)
# ---------------------------------------------------------------------------

class TestAssignmentsUnchanged:
    EXPECTED_CLAUDE_ASSIGNMENTS = {
        "engineer": "claude-haiku-4.5",
        "senior_engineer": "claude-sonnet-5",
        "quality_engineer": "claude-sonnet-5",
        "lead_engineer": "claude-sonnet-5",
        # Unconditional fable-5 for highest-capability security analysis
        "security_engineer": "claude-fable-5",
        "principal_engineer": "claude-opus-5",
        "model_engineer": "claude-sonnet-5",
        "general_orchestrator": "claude-haiku-4.5",
    }

    def test_all_claude_assignments(self, resolver):
        for role, model in self.EXPECTED_CLAUDE_ASSIGNMENTS.items():
            assert resolver.resolve(role, provider="claude") == model

    def test_unknown_role_raises(self, resolver):
        with pytest.raises(ModelNotFoundError):
            resolver.resolve("does_not_exist")


# ---------------------------------------------------------------------------
# Custom-YAML fixtures for edge-case coverage
# ---------------------------------------------------------------------------

# A deliberately "messy" registry that exercises rarely-hit branches:
# - canonical-only role (no providers dict)              -> derive/resolve via canonical
# - non-dict role config                                 -> skipped during derivation
# - role with providers but no claude entry & no canonical -> resolve() error path
CUSTOM_REGISTRY = {
    "role_models": {
        "weird_role": {
            "canonical": "claude-weird",
            # no providers key at all
        },
        "broken_role": "not-a-dict",  # non-dict config, must be skipped
        "no_canonical_role": {
            # no canonical, no claude provider -> resolve() must raise ValueError
            "providers": {"openai": "gpt-x"},
        },
    },
    "provider_features": {
        "claude": {"thinking": True, "structured_output": True},
        "google": {"thinking": False, "structured_output": False},
    },
}


@pytest.fixture
def custom_yaml(tmp_path):
    """Write the messy CUSTOM_REGISTRY to a temp models.yaml and return its path."""
    p = tmp_path / "models.yaml"
    p.write_text(yaml.safe_dump(CUSTOM_REGISTRY))
    return p


@pytest.fixture
def custom_resolver(custom_yaml):
    """Resolver backed by the messy custom registry."""
    return ModelResolver(str(custom_yaml), fallback_to_defaults=True)


# ---------------------------------------------------------------------------
# __init__ loading: error paths and fallbacks (lines 122-129, 162, 168)
# ---------------------------------------------------------------------------

class TestInitErrorPaths:
    def test_missing_path_without_fallback_raises_filenotfound(self):
        """A specified-but-missing path with fallback disabled must raise
        FileNotFoundError (covers the explicit not-found guard)."""
        with pytest.raises(FileNotFoundError):
            ModelResolver("/nonexistent/models.yaml", fallback_to_defaults=False)

    def test_missing_path_with_fallback_uses_derived_defaults(self):
        """A missing path with fallback enabled must NOT raise; it derives
        defaults from the canonical registry instead (covers warn-and-continue)."""
        r = ModelResolver("/nonexistent/models.yaml", fallback_to_defaults=True)
        # Defaults derived from the canonical file are still populated.
        assert r.FALLBACK_DEFAULTS["engineer"] == "claude-haiku-4.5"

    def test_empty_yaml_without_fallback_reraises(self, tmp_path):
        """An empty models.yaml raises ValueError in _load_yaml; with fallback
        disabled the exception must propagate out of __init__."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        with pytest.raises(ValueError):
            ModelResolver(str(empty), fallback_to_defaults=False)

    def test_empty_yaml_with_fallback_is_swallowed(self, tmp_path):
        """An empty models.yaml with fallback enabled is logged and swallowed;
        the resolver still constructs using derived defaults."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        r = ModelResolver(str(empty), fallback_to_defaults=True)
        assert r.models_config == {}
        # FALLBACK_DEFAULTS derived from the canonical file as a backstop.
        assert "engineer" in r.FALLBACK_DEFAULTS

    def test_missing_role_models_section_raises(self, tmp_path):
        """A models.yaml lacking the 'role_models' section must raise ValueError."""
        bad = tmp_path / "noroles.yaml"
        bad.write_text(yaml.safe_dump({"provider_features": {"claude": {}}}))
        with pytest.raises(ValueError):
            ModelResolver(str(bad), fallback_to_defaults=False)


# ---------------------------------------------------------------------------
# _find_models_yaml auto-detection (line 154)
# ---------------------------------------------------------------------------

class TestFindModelsYaml:
    def test_find_returns_none_when_no_candidate_exists(self, monkeypatch):
        """When none of the candidate locations exist, auto-detection returns None."""
        monkeypatch.setattr(Path, "exists", lambda self: False)
        assert ModelResolver._find_models_yaml() is None


# ---------------------------------------------------------------------------
# _derive_fallback_defaults edge branches (lines 189-198, 203, 214)
# ---------------------------------------------------------------------------

class TestDeriveFallbackDefaults:
    def test_derive_from_canonical_when_no_registry_loaded(self):
        """With an unloadable path + fallback and a cold cache, defaults are
        derived by reading the canonical file directly (file-read branch)."""
        ModelResolver._fallback_cache.clear()  # force the cache-miss / file-read path
        r = ModelResolver("/nonexistent/models.yaml", fallback_to_defaults=True)
        assert r.FALLBACK_DEFAULTS["senior_engineer"] == "claude-sonnet-5"

    def test_no_registry_uses_fallback_cache_on_second_call(self):
        """Priming the class-level cache with a canonical-backed resolver lets a
        subsequent no-registry resolver hit the cached defaults branch."""
        # Prime: a normal resolver loading the canonical file populates the cache.
        ModelResolver(str(CANONICAL_YAML), fallback_to_defaults=True)
        # No-registry resolver should now read derived defaults from the cache.
        r = ModelResolver("/nonexistent/models.yaml", fallback_to_defaults=True)
        assert r.FALLBACK_DEFAULTS["engineer"] == "claude-haiku-4.5"

    def test_no_registry_and_no_canonical_file_yields_empty_defaults(self, monkeypatch):
        """If the registry is empty AND no canonical file can be auto-detected,
        derivation falls back to an empty role set (covers the final else branch)."""
        ModelResolver._fallback_cache.clear()
        monkeypatch.setattr(ModelResolver, "_find_models_yaml", staticmethod(lambda: None))
        r = ModelResolver("/nonexistent/models.yaml", fallback_to_defaults=True)
        assert r.FALLBACK_DEFAULTS == {}

    def test_canonical_only_role_and_nondict_role(self, custom_resolver):
        """A canonical-only role derives its canonical value; a non-dict role
        config is skipped entirely during derivation."""
        assert custom_resolver.FALLBACK_DEFAULTS["weird_role"] == "claude-weird"
        assert "broken_role" not in custom_resolver.FALLBACK_DEFAULTS


# ---------------------------------------------------------------------------
# resolve(): override, fallback, provider-miss, canonical & error (259,272,281,291-295)
# ---------------------------------------------------------------------------

class TestResolveBranches:
    def test_override_takes_highest_precedence(self, resolver):
        """An explicit override short-circuits all registry lookups."""
        assert resolver.resolve("engineer", override="my-model") == "my-model"

    def test_alias_role_resolves_via_fallback_defaults(self, resolver):
        """An alias role absent from role_models but present in FALLBACK_DEFAULTS
        resolves to its inherited default (covers the fallback-default branch)."""
        # 'orchestrator' is an alias of general_orchestrator (claude-haiku-4.5).
        assert resolver.resolve("orchestrator") == "claude-haiku-4.5"

    def test_unknown_provider_falls_back_to_claude(self, resolver):
        """Requesting an unregistered provider falls back to the claude model."""
        assert resolver.resolve("engineer", provider="nope") == "claude-haiku-4.5"

    def test_canonical_only_role_resolves_to_canonical(self, custom_resolver):
        """A role with no claude provider resolves to its canonical alias."""
        assert custom_resolver.resolve("weird_role") == "claude-weird"

    def test_role_without_canonical_or_claude_raises_valueerror(self, custom_resolver):
        """A role lacking both a claude provider and a canonical value raises
        ValueError when resolved with no usable provider."""
        with pytest.raises(ValueError):
            custom_resolver.resolve("no_canonical_role")

    def test_unknown_provider_on_canonical_only_role_raises(self, custom_resolver):
        """An unknown provider on a role with no claude/canonical falls through
        and raises ValueError (covers the provider-miss debug branch)."""
        with pytest.raises(ValueError):
            custom_resolver.resolve("no_canonical_role", provider="google")


# ---------------------------------------------------------------------------
# resolve_with_env precedence + tier resolution (308-324, 328-337)
# ---------------------------------------------------------------------------

class TestResolveWithEnv:
    def test_agent_override_env_wins(self, resolver, monkeypatch):
        """AGENT_MODEL_OVERRIDE_<ROLE> has the highest env precedence."""
        monkeypatch.setenv("AGENT_MODEL_OVERRIDE_ENGINEER", "env-model")
        assert resolver.resolve_with_env("engineer") == "env-model"

    def test_model_tier_env_maps_to_family(self, resolver, monkeypatch):
        """A valid MODEL_TIER maps the role to the canonical model family."""
        monkeypatch.delenv("AGENT_MODEL_OVERRIDE_ENGINEER", raising=False)
        monkeypatch.setenv("MODEL_TIER", "opus")
        assert resolver.resolve_with_env("engineer") == "claude-opus"

    def test_unknown_model_tier_falls_through(self, resolver, monkeypatch):
        """An unrecognised MODEL_TIER is ignored (warns, returns None) and normal
        resolution proceeds."""
        monkeypatch.delenv("AGENT_MODEL_OVERRIDE_ENGINEER", raising=False)
        monkeypatch.setenv("MODEL_TIER", "platinum")
        assert resolver.resolve_with_env("engineer", provider="claude") == "claude-haiku-4.5"

    def test_preferred_provider_env_applied(self, resolver, monkeypatch):
        """PREFERRED_PROVIDER overrides the provider argument when no higher-prec
        env var is set."""
        for k in ("AGENT_MODEL_OVERRIDE_ENGINEER", "MODEL_TIER"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("PREFERRED_PROVIDER", "openai")
        assert resolver.resolve_with_env("engineer") == "gpt-4o-mini"

    def test_no_env_uses_plain_resolution(self, resolver, monkeypatch):
        """With no relevant env vars, resolve_with_env defers to resolve()."""
        for k in ("AGENT_MODEL_OVERRIDE_ENGINEER", "MODEL_TIER", "PREFERRED_PROVIDER"):
            monkeypatch.delenv(k, raising=False)
        assert resolver.resolve_with_env("engineer", provider="claude") == "claude-haiku-4.5"


# ---------------------------------------------------------------------------
# Metadata accessors (343-389)
# ---------------------------------------------------------------------------

class TestMetadataAccessors:
    def test_get_canonical_found(self, resolver):
        assert resolver.get_canonical("engineer") == "claude-haiku"

    def test_get_canonical_missing_raises(self, resolver):
        with pytest.raises(ModelNotFoundError):
            resolver.get_canonical("nope")

    def test_get_canonical_without_canonical_field_raises(self, custom_resolver):
        """A role config without a 'canonical' field raises ValueError."""
        with pytest.raises(ValueError):
            custom_resolver.get_canonical("no_canonical_role")

    def test_get_effort_found_and_default(self, resolver, custom_resolver):
        """get_effort returns the configured effort, or 'medium' when absent."""
        assert resolver.get_effort("security_engineer") == "max"
        assert custom_resolver.get_effort("weird_role") == "medium"

    def test_get_effort_missing_raises(self, resolver):
        with pytest.raises(ModelNotFoundError):
            resolver.get_effort("nope")

    def test_is_thinking_supported(self, resolver):
        """thinking flag is read from the registry; unknown roles report False."""
        assert resolver.is_thinking_supported("senior_engineer") is True
        assert resolver.is_thinking_supported("engineer") is False
        assert resolver.is_thinking_supported("nope") is False

    def test_get_provider_specific(self, resolver):
        assert resolver.get_provider_specific("engineer", "claude") == "claude-haiku-4.5"
        assert resolver.get_provider_specific("engineer", "nope") is None

    def test_get_provider_specific_missing_role_raises(self, resolver):
        with pytest.raises(ModelNotFoundError):
            resolver.get_provider_specific("nope", "claude")

    def test_get_all_providers(self, resolver):
        providers = resolver.get_all_providers("engineer")
        assert providers["claude"] == "claude-haiku-4.5"
        assert "openai" in providers

    def test_get_all_providers_missing_raises(self, resolver):
        with pytest.raises(ModelNotFoundError):
            resolver.get_all_providers("nope")

    def test_validate(self, resolver):
        """validate() is True for registry roles and fallback aliases, False otherwise."""
        assert resolver.validate("engineer") is True
        assert resolver.validate("orchestrator") is True  # fallback alias
        assert resolver.validate("nope") is False


# ---------------------------------------------------------------------------
# get_capability_deltas (393-413)
# ---------------------------------------------------------------------------

CAP_REGISTRY = {
    "role_models": {
        "thinky": {
            "canonical": "c",
            "thinking": True,
            "structured_output": True,
            "effort": "high",
            "providers": {"claude": "x"},
        },
    },
    "provider_features": {
        "claude": {"thinking": True, "structured_output": True},
        "weakprov": {"thinking": False, "structured_output": False},
    },
}


@pytest.fixture
def cap_resolver(tmp_path):
    p = tmp_path / "cap.yaml"
    p.write_text(yaml.safe_dump(CAP_REGISTRY))
    return ModelResolver(str(p), fallback_to_defaults=False)


class TestCapabilityDeltas:
    def test_no_deltas_when_provider_matches(self, cap_resolver):
        assert cap_resolver.get_capability_deltas("thinky", "claude") == []

    def test_thinking_and_structured_output_deltas(self, cap_resolver):
        """A capable role on a weak provider reports both thinking and
        structured-output gaps."""
        deltas = cap_resolver.get_capability_deltas("thinky", "weakprov")
        assert any("thinking" in d for d in deltas)
        assert any("structured output" in d for d in deltas)

    def test_unknown_role_delta(self, cap_resolver):
        deltas = cap_resolver.get_capability_deltas("nope", "claude")
        assert deltas == ["Role 'nope' not found in registry"]

    def test_unknown_provider_delta(self, cap_resolver):
        deltas = cap_resolver.get_capability_deltas("thinky", "nope")
        assert deltas == ["Provider 'nope' not found in registry"]


# ---------------------------------------------------------------------------
# Listing + validate_all (415-470)
# ---------------------------------------------------------------------------

class TestListingAndValidateAll:
    def test_list_all_roles_includes_fallback_aliases(self, resolver):
        roles = resolver.list_all_roles()
        assert "engineer" in roles
        assert "orchestrator" in roles  # fallback alias
        assert roles == sorted(roles)

    def test_list_all_providers(self, resolver):
        providers = resolver.list_all_providers()
        assert "claude" in providers
        assert providers == sorted(providers)

    def test_validate_all_canonical_registry(self, resolver):
        """The canonical registry validates without errors; alias-only roles and
        provider-coverage gaps surface as warnings."""
        report = resolver.validate_all()
        assert report["valid"] is True
        assert report["errors"] == []
        # alias roles (orchestrator, metrics, ...) only-in-defaults -> warnings
        assert any("only in defaults" in w for w in report["warnings"])
        assert report["coverage"]["total_roles"] > 8

    def test_validate_all_flags_missing_fields_and_coverage(self, tmp_path):
        """validate_all surfaces missing canonical/thinking/effort as errors,
        no-provider and partial-provider roles as warnings, and counts a
        fully-covered role under roles_with_all_providers."""
        registry = {
            "role_models": {
                "full_role": {
                    "canonical": "m",
                    "thinking": True,
                    "effort": "high",
                    "providers": {"claude": "claude-x", "google": "g-x"},
                },
                "missing_fields_role": {
                    "providers": {"claude": "c"},
                },
                "no_providers_role": {
                    "canonical": "m2",
                    "thinking": False,
                    "effort": "low",
                },
                "partial_providers_role": {
                    "canonical": "m3",
                    "thinking": False,
                    "effort": "low",
                    "providers": {"claude": "c3"},
                },
            },
            "provider_features": {
                "claude": {"thinking": True, "structured_output": True},
                "google": {"thinking": False, "structured_output": False},
            },
        }
        p = tmp_path / "validate.yaml"
        p.write_text(yaml.safe_dump(registry))
        r = ModelResolver(str(p), fallback_to_defaults=False)
        report = r.validate_all()

        assert report["valid"] is False
        joined = " ".join(report["errors"])
        assert "missing 'canonical'" in joined
        assert "missing 'thinking'" in joined
        assert "missing 'effort'" in joined
        # full_role has exactly the 2 known providers -> counted as fully covered.
        assert report["coverage"]["roles_with_all_providers"] >= 1
        # no_providers_role + partial_providers_role appear as missing-provider roles.
        assert "no_providers_role" in report["coverage"]["roles_missing_providers"]
        assert "partial_providers_role" in report["coverage"]["roles_missing_providers"]


# ---------------------------------------------------------------------------
# Module-level debug logging toggle (35-40)
# ---------------------------------------------------------------------------

class TestDebugLogging:
    def test_debug_env_enables_debug_logger(self, monkeypatch):
        """Executing the module with MODEL_RESOLVER_DEBUG set configures its
        logger at DEBUG level with a stream handler.

        The module is loaded under a throwaway name via a fresh spec rather than
        importlib.reload(): reload() would mutate the shared module object in
        place (swapping the exception classes other already-imported test modules
        hold by reference), causing cross-file failures. A separate module object
        exercises lines 35-40 against the same source file (so coverage still
        counts them) without disturbing sys.modules.
        """
        import src.orchestration.models.canonical_resolver as cr

        monkeypatch.setenv("MODEL_RESOLVER_DEBUG", "1")
        spec = importlib.util.spec_from_file_location(
            "canonical_resolver_debug_probe", cr.__file__
        )
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        assert probe.logger.level == logging.DEBUG
        assert probe.logger.handlers  # a stream handler was attached


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
