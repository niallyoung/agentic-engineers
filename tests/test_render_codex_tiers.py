"""Test that Codex model tiers are derived from registry families.

TDD: Write test first, show it failing, then implement the feature.
"""

import tempfile
import subprocess
from pathlib import Path
import sys
import yaml

# Import the models registry loader
scripts_dir = Path(__file__).parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
from models import load_registry


def test_orchestrator_on_sonnet_tier():
    """Orchestrator should render on the standard (Sonnet-class) tier with effort low."""
    repo_root = Path(__file__).parent.parent
    registry = load_registry(repo_root)

    # Verify orchestrator is Sonnet-class
    orch_model = registry.get("roles", {}).get("orchestrator", {}).get("model")
    models = registry.get("models", {})
    orch_info = models.get(orch_model)
    family = orch_info.get("family")

    assert family == "sonnet", f"Orchestrator should be Sonnet-class, got {family}"

    # Verify it renders to the standard Codex model (should be same as other Sonnet roles)
    orch_codex = _get_codex_model_for_role(repo_root, "orchestrator")
    other_sonnet = _get_codex_model_for_role(repo_root, "lead-engineer")  # Also Sonnet-class

    assert orch_codex == other_sonnet, (
        f"Orchestrator (Sonnet) should use same Codex model as other Sonnet roles: "
        f"orch={orch_codex}, lead={other_sonnet}"
    )

    # Verify effort is low
    orch_effort = _get_codex_effort_for_role(repo_root, "orchestrator")
    assert orch_effort == "low", f"Orchestrator Codex effort should be low, got {orch_effort}"


def test_engineer_on_haiku_tier():
    """Engineer should render on the mini (Haiku-class) tier."""
    repo_root = Path(__file__).parent.parent
    codex_model = _get_codex_model_for_role(repo_root, "engineer")
    assert codex_model == "gpt-5.4-mini", f"Engineer should render to gpt-5.4-mini, got {codex_model}"


def test_senior_engineer_on_sonnet_tier():
    """Senior engineer should render on the standard (Sonnet-class) tier."""
    repo_root = Path(__file__).parent.parent
    registry = load_registry(repo_root)

    # Verify senior-engineer is Sonnet-class
    se_model = registry.get("roles", {}).get("senior-engineer", {}).get("model")
    models = registry.get("models", {})
    se_info = models.get(se_model)
    family = se_info.get("family")
    assert family == "sonnet"

    # Should render to gpt-5.5
    codex_model = _get_codex_model_for_role(repo_root, "senior-engineer")
    assert codex_model == "gpt-5.5", f"Senior engineer should render to gpt-5.5, got {codex_model}"


def test_effort_capping():
    """Security engineer's max effort should be capped to high in Codex."""
    repo_root = Path(__file__).parent.parent
    registry = load_registry(repo_root)

    # Verify security engineer has effort max in registry
    security_effort = registry.get("roles", {}).get("security-engineer", {}).get("effort")
    assert security_effort == "max", f"Security engineer should have effort max, got {security_effort}"

    # Verify it renders to high in Codex (capped)
    codex_effort = _get_codex_effort_for_role(repo_root, "security-engineer")
    assert codex_effort == "high", f"Security engineer Codex effort should be capped to high, got {codex_effort}"


def test_codex_models_by_family():
    """Test that Codex models are properly derived from registry families."""
    repo_root = Path(__file__).parent.parent
    registry = load_registry(repo_root)

    # Map families to expected Codex models
    FAMILY_TO_CODEX = {
        "haiku": "gpt-5.4-mini",
        "sonnet": "gpt-5.5",
        "opus": "gpt-5.5",
        "fable": "gpt-5.5",
    }

    models = registry.get("models", {})
    roles = registry.get("roles", {})

    # For each role, verify its Codex model matches its family
    for role, role_cfg in roles.items():
        model_id = role_cfg.get("model")
        model_info = models.get(model_id)
        family = model_info.get("family")
        expected_codex = FAMILY_TO_CODEX.get(family)

        actual_codex = _get_codex_model_for_role(repo_root, role)
        assert actual_codex == expected_codex, (
            f"Role '{role}' (family {family}, model {model_id}): "
            f"expected Codex {expected_codex}, got {actual_codex}"
        )


def _get_codex_model_for_role(repo_root: Path, role: str) -> str:
    """Helper: get the Codex model that would be rendered for a role via the renderer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        codex_home = Path(tmpdir)

        # Run the renderer to install
        result = subprocess.run(
            ["python3", "renderer/scripts/render-codex.py", str(repo_root), str(codex_home)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Renderer failed: {result.stderr}")

        # Read the generated agent TOML file
        agent_file = codex_home / "agents" / (role.replace("_", "-") + ".toml")
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")

        content = agent_file.read_text()

        # Extract the model line
        for line in content.split("\n"):
            if line.startswith("model ="):
                # Extract the quoted model ID
                match = line.split('=')[1].strip().strip('"')
                return match

        raise ValueError(f"Could not find model in {agent_file}")


def _get_codex_effort_for_role(repo_root: Path, role: str) -> str:
    """Helper: get the Codex reasoning_effort that would be rendered for a role."""
    with tempfile.TemporaryDirectory() as tmpdir:
        codex_home = Path(tmpdir)

        # Run the renderer to install
        result = subprocess.run(
            ["python3", "renderer/scripts/render-codex.py", str(repo_root), str(codex_home)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Renderer failed: {result.stderr}")

        # Read the generated agent TOML file
        agent_file = codex_home / "agents" / (role.replace("_", "-") + ".toml")
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")

        content = agent_file.read_text()

        # Extract the model_reasoning_effort line
        for line in content.split("\n"):
            if line.startswith("model_reasoning_effort ="):
                # Extract the quoted effort value
                match = line.split('=')[1].strip().strip('"')
                return match

        raise ValueError(f"Could not find model_reasoning_effort in {agent_file}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
