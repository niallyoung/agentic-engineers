# -*- coding: utf-8 -*-
"""
Tests for the opencode_sync sub-module in harness-integration-tracker.

Ported from harness-opencode-feature-sync during Wave 3 consolidation
(m3-skills-deprecation, 2026-06-14). opencode_feature_sync.py is now
scripts/opencode_sync.py inside harness-integration-tracker.
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — point at harness-integration-tracker skill root
# ---------------------------------------------------------------------------
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.opencode_sync import (  # noqa: E402
    build_parser,
    build_report,
    detect_drift,
    detect_permission_uniformity,
    discover_candidates,
    extract_emitted_keys,
    extract_known_keys_from_text,
    load_registry,
    update_registry,
    write_registry,
)

# Use the registry from the archived source skill's references dir.
# harness-opencode-feature-sync was archived to docs/archive/deprecated-skills/
# during Wave 3 consolidation.
_REPO_ROOT = Path(__file__).parents[4]
_ORIGINAL_SKILL = _REPO_ROOT / "docs" / "archive" / "deprecated-skills" / "harness-opencode-feature-sync"
_REGISTRY = _ORIGINAL_SKILL / "references" / "integration-points.yaml"


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def agent_ts_text() -> str:
    """A minimal agent.ts snippet containing a KNOWN_KEYS set."""
    return (
        'const KNOWN_KEYS = new Set([\n'
        '  "name",\n'
        '  "model",\n'
        '  "variant",\n'
        '  "mode",\n'
        '  "description",\n'
        '  "permission",\n'
        '  "temperature",\n'
        '])\n'
    )


@pytest.fixture()
def renderer_text_defective() -> str:
    """Renderer snippet reproducing the two real defects."""
    return (
        'echo "---"\n'
        'printf \'description: "%s"\\n\' "$desc"\n'
        'echo "mode: $agent_mode"\n'
        'echo "model: $model_full"\n'
        'echo "temperature: $temp"\n'
        'echo "permission:"\n'
        'echo "  read: allow"\n'
        'echo "  edit: allow"\n'
        'echo "  bash: allow"\n'
        'echo "thinking:"\n'
        'echo "  enabled: true"\n'
        'echo "  budget_tokens: 5000"\n'
        'echo "---"\n'
    )


@pytest.fixture()
def renderer_text_fixed() -> str:
    """Renderer snippet with the defects remediated."""
    return (
        'echo "---"\n'
        'printf \'description: "%s"\\n\' "$desc"\n'
        'echo "mode: $agent_mode"\n'
        'echo "model: $model_full"\n'
        'echo "variant: high"\n'
        'echo "permission:"\n'
        'echo "  \\"*\\": deny"\n'
        'echo "  read: allow"\n'
        'echo "  edit: allow"\n'
        'echo "---"\n'
    )


# ===========================================================================
# Registry loader
# ===========================================================================

@pytest.mark.skipif(not _REGISTRY.exists(), reason="Registry file not found (source skill not present)")
def test_registry_loads_and_has_points():
    registry = load_registry(_REGISTRY)
    assert "integration_points" in registry
    assert len(registry["integration_points"]) >= 8


@pytest.mark.skipif(not _REGISTRY.exists(), reason="Registry file not found")
def test_registry_entries_have_required_fields():
    registry = load_registry(_REGISTRY)
    required = {"id", "opencode_path", "what_to_check", "last_verified", "status"}
    for entry in registry["integration_points"]:
        assert required.issubset(entry.keys()), entry


@pytest.mark.skipif(not _REGISTRY.exists(), reason="Registry file not found")
def test_registry_ids_unique():
    registry = load_registry(_REGISTRY)
    ids = [e["id"] for e in registry["integration_points"]]
    assert len(ids) == len(set(ids))


# ===========================================================================
# KNOWN_KEYS extraction
# ===========================================================================

def test_extract_known_keys(agent_ts_text: str):
    keys = extract_known_keys_from_text(agent_ts_text)
    assert "variant" in keys
    assert "permission" in keys
    assert "thinking" not in keys


def test_extract_known_keys_empty_on_missing():
    assert extract_known_keys_from_text("no set here") == set()


# ===========================================================================
# Emitted-key extraction
# ===========================================================================

def test_extract_emitted_keys_finds_top_level(renderer_text_defective: str):
    keys = extract_emitted_keys(renderer_text_defective)
    assert "description" in keys
    assert "mode" in keys
    assert "permission" in keys
    assert "thinking" in keys


def test_extract_emitted_keys_excludes_nested(renderer_text_defective: str):
    keys = extract_emitted_keys(renderer_text_defective)
    # Nested permission entries are indented and must not appear as top-level keys.
    assert "read" not in keys
    assert "edit" not in keys
    assert "budget_tokens" not in keys


# ===========================================================================
# Drift detection
# ===========================================================================

def test_detect_drift_flags_noop_key(agent_ts_text: str, renderer_text_defective: str):
    known = extract_known_keys_from_text(agent_ts_text)
    emitted = extract_emitted_keys(renderer_text_defective)
    findings = detect_drift(known, emitted, renderer_text_defective)
    kinds = {f["kind"] for f in findings}
    assert "noop-key" in kinds
    noop = next(f for f in findings if f["kind"] == "noop-key")
    assert "thinking" in noop["detail"]
    assert noop["severity"] == "error"


def test_detect_drift_flags_missing_variant(agent_ts_text: str, renderer_text_defective: str):
    known = extract_known_keys_from_text(agent_ts_text)
    emitted = extract_emitted_keys(renderer_text_defective)
    findings = detect_drift(known, emitted, renderer_text_defective)
    assert any(f["kind"] == "missing-supported-key" for f in findings)


def test_detect_drift_flags_permission_uniformity(agent_ts_text: str, renderer_text_defective: str):
    known = extract_known_keys_from_text(agent_ts_text)
    emitted = extract_emitted_keys(renderer_text_defective)
    findings = detect_drift(known, emitted, renderer_text_defective)
    assert any(f["kind"] == "permission-uniformity" for f in findings)


def test_detect_drift_clean_on_fixed(agent_ts_text: str, renderer_text_fixed: str):
    known = extract_known_keys_from_text(agent_ts_text)
    emitted = extract_emitted_keys(renderer_text_fixed)
    findings = detect_drift(known, emitted, renderer_text_fixed)
    kinds = {f["kind"] for f in findings}
    assert "noop-key" not in kinds
    assert "missing-supported-key" not in kinds
    assert "permission-uniformity" not in kinds


def test_permission_uniformity_true_when_all_allow(renderer_text_defective: str):
    assert detect_permission_uniformity(renderer_text_defective) is True


def test_permission_uniformity_false_when_wildcard_deny(renderer_text_fixed: str):
    assert detect_permission_uniformity(renderer_text_fixed) is False


# ===========================================================================
# Discovery
# ===========================================================================

def test_discover_candidates_on_fixture(tmp_path: Path):
    cfg = tmp_path / "packages" / "opencode" / "src" / "config"
    cfg.mkdir(parents=True)
    (cfg / "permission.ts").write_text("export const permission = {}\n")
    (cfg / "unrelated.ts").write_text("export const x = 1\n")
    registry = {"integration_points": []}
    candidates = discover_candidates(tmp_path, registry)
    paths = {c["opencode_path"] for c in candidates}
    assert any("permission.ts" in p for p in paths)
    assert not any("unrelated.ts" in p for p in paths)


def test_discover_skips_registered(tmp_path: Path):
    cfg = tmp_path / "packages" / "opencode" / "src" / "config"
    cfg.mkdir(parents=True)
    rel = "packages/opencode/src/config/permission.ts"
    (cfg / "permission.ts").write_text("permission reasoning variant\n")
    registry = {"integration_points": [{"id": "x", "opencode_path": rel}]}
    candidates = discover_candidates(tmp_path, registry)
    assert not any(c["opencode_path"] == rel for c in candidates)


# ===========================================================================
# Self-update
# ===========================================================================

def test_update_registry_appends_and_refreshes(tmp_path: Path):
    reg_path = tmp_path / "registry.yaml"
    registry = {
        "schema_version": 1,
        "integration_points": [
            {
                "id": "agent-known-keys",
                "opencode_path": "packages/opencode/src/config/agent.ts",
                "anchor": "KNOWN_KEYS",
                "what_to_check": "x",
                "last_verified": "2000-01-01",
                "status": "verified",
            }
        ],
    }
    write_registry(registry, reg_path)

    verifications = [{"id": "agent-known-keys", "exists": True, "anchor_found": True, "status": "verified"}]
    candidates = [
        {
            "id": "candidate-new",
            "opencode_path": "packages/opencode/src/config/new.ts",
            "anchor": "",
            "what_to_check": "discovered",
            "last_verified": "2026-05-31",
            "status": "candidate",
        }
    ]
    update_registry(registry, verifications, candidates, set(), reg_path)

    reloaded = load_registry(reg_path)
    ids = {e["id"] for e in reloaded["integration_points"]}
    assert "candidate-new" in ids
    refreshed = next(e for e in reloaded["integration_points"] if e["id"] == "agent-known-keys")
    assert refreshed["last_verified"] != "2000-01-01"
