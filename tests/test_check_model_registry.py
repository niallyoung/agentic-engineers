#!/usr/bin/env python3
"""
tests/test_check_model_registry.py — Advisory model-registry drift checker tests.

Tests:
1. Parsing of real LOCKED_MODELS.sh
2. Drift detection against fixtures
3. --offline flag handling
4. --json output shape
5. Normalization of model ids
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_model_registry.py"


# Fixture: models.dev-like registry data
FIXTURE_REGISTRY_DATA = {
    "models": [
        {
            "id": "claude-haiku-4.5",
            "name": "Claude Haiku 4.5",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 8192},
            "cost": {"input": 0.80, "output": 4.00},
        },
        {
            "id": "claude-sonnet-5",
            "name": "Claude Sonnet 5",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 16384},
            "cost": {"input": 3.00, "output": 15.00},
        },
        {
            "id": "claude-sonnet-4.5",
            "name": "Claude Sonnet 4.5",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 8192},
            "cost": {"input": 3.00, "output": 15.00},
        },
        {
            "id": "claude-opus-5",
            "name": "Claude Opus 5",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 16384},
            "cost": {"input": 15.00, "output": 75.00},
        },
        {
            "id": "claude-fable-5",
            "name": "Claude Fable 5",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 4096},
            "cost": {"input": 0.30, "output": 1.50},
        },
        # Deprecated model for testing
        {
            "id": "claude-opus-4.8",
            "name": "Claude Opus 4.8",
            "provider": "anthropic",
            "status": "deprecated",
            "limit": {"output": 16384},
            "cost": {"input": 15.00, "output": 75.00},
        },
        # Model that exists but isn't in our LOCKED_MODELS
        {
            "id": "claude-sonnet-4.6",
            "name": "Claude Sonnet 4.6",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 8192},
            "cost": {"input": 3.00, "output": 15.00},
        },
        {
            "id": "claude-opus-4.6",
            "name": "Claude Opus 4.6",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 16384},
            "cost": {"input": 15.00, "output": 75.00},
        },
        {
            "id": "claude-opus-4.7",
            "name": "Claude Opus 4.7",
            "provider": "anthropic",
            "status": None,
            "limit": {"output": 16384},
            "cost": {"input": 15.00, "output": 75.00},
        },
    ]
}


@pytest.fixture
def script():
    """Return path to the check_model_registry.py script."""
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"
    return SCRIPT_PATH


def test_script_exists(script):
    """Verify the script file exists."""
    assert script.exists()
    assert script.suffix == ".py"


def test_script_is_executable(script):
    """Verify the script is executable."""
    import os
    assert os.access(script, os.X_OK), f"Script not executable: {script}"


def test_parse_locked_models(script):
    """Test parsing LOCKED_MODELS from real .githooks/LOCKED_MODELS.sh."""
    # Import and test directly
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import _parse_locked_models

    models = _parse_locked_models()

    # Should have the expected locked models
    expected = {
        "claude-haiku-4.5",
        "claude-sonnet-4.5",
        "claude-sonnet-4.6",
        "claude-sonnet-5",
        "claude-opus-4.6",
        "claude-opus-4.7",
        "claude-opus-4.8",
        "claude-opus-5",
        "claude-fable-5",
    }

    assert set(models) == expected, f"Parsed models {set(models)} != expected {expected}"


def test_parse_agent_assignments(script):
    """Test parsing AGENT_MODEL_ASSIGNMENTS from real LOCKED_MODELS.sh."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import _parse_agent_assignments

    assignments = _parse_agent_assignments()

    # Should have expected agents
    assert "engineer-agent" in assignments
    assert assignments["engineer-agent"] == "claude-haiku-4.5"

    assert "orchestrator-agent" in assignments
    assert assignments["orchestrator-agent"] == "claude-sonnet-5"

    assert "security-engineer-agent" in assignments
    assert assignments["security-engineer-agent"] == "claude-fable-5"


def test_build_model_index():
    """Test building model index from fixture data."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import _build_model_index

    index = _build_model_index(FIXTURE_REGISTRY_DATA)

    # Should have all fixture models
    assert "claude-haiku-4.5" in index
    assert "claude-sonnet-5" in index
    assert "claude-opus-5" in index

    # Check fields
    haiku_info = index["claude-haiku-4.5"]
    assert haiku_info.provider == "anthropic"
    assert haiku_info.cost_input == 0.80
    assert haiku_info.context_window == 8192


def test_model_id_normalization():
    """Test model ID normalization (e.g., claude-sonnet-5 vs claude-sonnet-5.0)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import _normalize_model_id

    # Exact match
    assert _normalize_model_id("claude-sonnet-5", "claude-sonnet-5")

    # With .0 variant
    assert _normalize_model_id("claude-sonnet-5.0", "claude-sonnet-5")
    assert _normalize_model_id("claude-sonnet-5", "claude-sonnet-5.0")

    # Different versions should not match
    assert not _normalize_model_id("claude-sonnet-5", "claude-sonnet-4")


def test_check_found_model():
    """Test checking a model that exists in registry."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import check_model_against_registry, _build_model_index

    index = _build_model_index(FIXTURE_REGISTRY_DATA)
    result = check_model_against_registry("claude-haiku-4.5", index)

    assert result.found
    assert result.in_registry_as == "claude-haiku-4.5"
    assert result.cost_input == 0.80
    assert result.context_window == 8192


def test_check_deprecated_model():
    """Test checking a deprecated model."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import check_model_against_registry, _build_model_index

    index = _build_model_index(FIXTURE_REGISTRY_DATA)
    result = check_model_against_registry("claude-opus-4.8", index)

    assert result.found
    assert result.status == "deprecated"
    assert "deprecated" in (result.notes or "").lower()


def test_check_missing_model():
    """Test checking a model not in registry."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_model_registry import check_model_against_registry, _build_model_index

    index = _build_model_index(FIXTURE_REGISTRY_DATA)
    # Use a model that's not in the fixture
    result = check_model_against_registry("claude-unknown-999", index)

    assert not result.found
    assert "unknown to registry" in result.notes.lower()


def test_offline_flag():
    """Test --offline flag skips network fetch."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--offline"],
        capture_output=True,
        text=True,
    )

    # Should exit 0 (advisory-only)
    assert result.returncode == 0
    # Should handle gracefully even with no registry data
    assert "Locked models" in result.stdout or "Model Registry" in result.stdout


def test_json_output_format():
    """Test --json output format."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json", "--offline"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Parse JSON
    data = json.loads(result.stdout)

    # Check structure
    assert "locked_models_count" in data
    assert "found_count" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert "assignments" in data
    assert isinstance(data["assignments"], dict)

    # Each result should have expected fields
    for result_item in data["results"]:
        assert "model" in result_item
        assert "found" in result_item


def test_json_output_with_fixture():
    """Test --json output with mocked network data."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

    # Import main function for testing
    from check_model_registry import (
        _parse_locked_models,
        _parse_agent_assignments,
        check_model_against_registry,
        _build_model_index,
    )

    locked_models = _parse_locked_models()
    assignments = _parse_agent_assignments()
    index = _build_model_index(FIXTURE_REGISTRY_DATA)

    results = []
    for model in locked_models:
        result = check_model_against_registry(model, index)
        results.append(result)

    # Build output structure
    output = {
        "locked_models_count": len(locked_models),
        "found_count": sum(1 for r in results if r.found),
        "results": [
            {
                "model": r.model,
                "found": r.found,
                "in_registry_as": r.in_registry_as,
                "status": r.status,
                "context_window": r.context_window,
                "cost_input": r.cost_input,
                "cost_output": r.cost_output,
                "notes": r.notes,
            }
            for r in results
        ],
    }

    # All our locked models should be found (they're in the fixture)
    assert output["found_count"] == len(locked_models)


def test_always_exits_zero_advisory():
    """Test that script exits 0 (advisory-only) even with drift."""
    # Run with --offline (no network)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--offline", "--json"],
        capture_output=True,
        text=True,
    )

    # Advisory: always exit 0
    assert result.returncode == 0


def test_py_compile():
    """Test that script is valid Python (compiles without syntax errors)."""
    import py_compile

    try:
        py_compile.compile(str(SCRIPT_PATH), doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(f"Script has syntax errors: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
