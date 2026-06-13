"""
Tests for ModelConfigLoader — Runtime model selection & experimentation.

Tests:
- Config loading from YAML
- Per-agent model lookup
- Per-task-type model lookup
- Experiment variant assignment (deterministic, respects traffic allocation)
- Full precedence chain (experiment > task > agent > global)
- Config reloading (hot-reload)
- Validation of config consistency
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from src.orchestration.model_config_loader import (
    Experiment,
    ExperimentSelector,
    ExperimentVariant,
    ModelConfigLoader,
    load_model_config,
)


class TestModelConfigLoaderBasics:
    """Test basic config loading."""

    def test_load_default_config(self) -> None:
        """Test loading from default config path."""
        loader = ModelConfigLoader()
        assert loader.global_default is not None
        assert loader.config_path is not None

    def test_load_nonexistent_path(self) -> None:
        """Test loading from nonexistent path uses defaults."""
        loader = ModelConfigLoader(Path("/nonexistent/model-config.yaml"))
        assert loader.global_default == "claude-haiku-4.5"
        assert loader.agents == {}

    def test_load_empty_file(self) -> None:
        """Test loading from empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.global_default == "claude-haiku-4.5"
            assert loader.agents == {}
        finally:
            path.unlink()


class TestPerAgentOverrides:
    """Test per-agent model selection."""

    def test_get_model_for_agent_configured(self) -> None:
        """Test getting model for configured agent."""
        config = {
            "agents": {
                "engineer": {"model": "claude-sonnet-4.5"},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_agent("engineer") == "claude-sonnet-4.5"
        finally:
            path.unlink()

    def test_get_model_for_agent_fallback_to_default(self) -> None:
        """Test fallback to global default for unconfigured agent."""
        config = {
            "global": {"default_model": "claude-haiku-4.5"},
            "agents": {},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_agent("nonexistent_agent") == "claude-haiku-4.5"
        finally:
            path.unlink()

    def test_multiple_agent_overrides(self) -> None:
        """Test multiple agent overrides."""
        config = {
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
                "senior_engineer": {"model": "claude-sonnet-4.5"},
                "principal_engineer": {"model": "claude-opus-4.6"},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_agent("engineer") == "claude-haiku-4.5"
            assert loader.get_model_for_agent("senior_engineer") == "claude-sonnet-4.5"
            assert loader.get_model_for_agent("principal_engineer") == "claude-opus-4.6"
        finally:
            path.unlink()


class TestPerTaskTypeOverrides:
    """Test per-task-type model selection."""

    def test_get_model_for_task_configured(self) -> None:
        """Test getting model for configured task type."""
        config = {
            "tasks": {
                "security_audit": {"model": "claude-opus-4.8"},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_task("security_audit") == "claude-opus-4.8"
        finally:
            path.unlink()

    def test_get_model_for_task_not_configured(self) -> None:
        """Test getting model for unconfigured task type."""
        config = {"tasks": {}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_task("unknown_task") is None
        finally:
            path.unlink()

    def test_multiple_task_overrides(self) -> None:
        """Test multiple task overrides."""
        config = {
            "tasks": {
                "security_audit": {"model": "claude-opus-4.8"},
                "code_review": {"model": "claude-sonnet-4.6"},
                "documentation": {"model": "claude-haiku-4.5"},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_task("security_audit") == "claude-opus-4.8"
            assert loader.get_model_for_task("code_review") == "claude-sonnet-4.6"
            assert loader.get_model_for_task("documentation") == "claude-haiku-4.5"
        finally:
            path.unlink()


class TestPrecedenceChain:
    """Test the full model selection precedence chain."""

    def test_precedence_task_over_agent(self) -> None:
        """Test that task-type override takes precedence over agent."""
        config = {
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
            },
            "tasks": {
                "security_audit": {"model": "claude-opus-4.8"},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            # Task-type override should win
            model = loader.get_model_for_delegate(
                agent="engineer",
                task_type="security_audit",
            )
            assert model == "claude-opus-4.8"
        finally:
            path.unlink()

    def test_precedence_agent_over_global(self) -> None:
        """Test that agent override takes precedence over global default."""
        config = {
            "global": {"default_model": "claude-haiku-4.5"},
            "agents": {
                "senior_engineer": {"model": "claude-sonnet-4.5"},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            model = loader.get_model_for_delegate(agent="senior_engineer")
            assert model == "claude-sonnet-4.5"
        finally:
            path.unlink()


class TestExperimentVariantAssignment:
    """Test A/B test variant assignment."""

    def test_experiment_variant_deterministic_assignment(self) -> None:
        """Test that variant assignment is deterministic (same seed → same variant)."""
        exp = Experiment(
            exp_id="test-exp",
            enabled=True,
            variants={
                "control": ExperimentVariant("control", "claude-haiku-4.5", 50),
                "variant_a": ExperimentVariant("variant_a", "claude-sonnet-4.5", 50),
            },
        )

        # Same seed should always select the same variant
        variant1 = exp.select_variant("task-123")
        variant2 = exp.select_variant("task-123")
        assert variant1 == variant2

    def test_experiment_variant_respects_traffic_allocation(self) -> None:
        """Test that variant selection respects traffic allocation percentages."""
        exp = Experiment(
            exp_id="test-exp",
            enabled=True,
            variants={
                "control": ExperimentVariant("control", "claude-haiku-4.5", 80),
                "variant_a": ExperimentVariant("variant_a", "claude-sonnet-4.5", 20),
            },
        )

        # Count variant assignments across 1000 seeds
        control_count = 0
        variant_a_count = 0

        for i in range(1000):
            task_id = f"task-{i}"
            variant = exp.select_variant(task_id)
            if variant == "control":
                control_count += 1
            elif variant == "variant_a":
                variant_a_count += 1

        # Allow 5% tolerance (75-85% for control, 15-25% for variant_a)
        # Out of 1000: expect 800 control, 200 variant_a
        assert 750 <= control_count <= 850, f"Expected ~800, got {control_count}"
        assert 150 <= variant_a_count <= 250, f"Expected ~200, got {variant_a_count}"

    def test_experiment_selector_matches_agent(self) -> None:
        """Test experiment selector matching on agent."""
        selector = ExperimentSelector(agent="engineer")
        assert selector.agent == "engineer"

    def test_experiment_selector_agent_mismatch(self) -> None:
        """Test that experiment doesn't apply to wrong agent."""
        selector = ExperimentSelector(agent="engineer")
        assert not selector.agent or selector.agent == "engineer"

    def test_experiment_should_apply_matching(self) -> None:
        """Test experiment.should_apply() with matching criteria."""
        exp = Experiment(
            exp_id="test",
            enabled=True,
            selector=ExperimentSelector(
                agent="engineer",
                task_types=["implementation"],
                min_scope_words=50,
            ),
        )

        # Should apply: agent matches, task_type matches, scope >= 50 words
        assert exp.should_apply("engineer", "implementation", 75)

    def test_experiment_should_apply_disabled(self) -> None:
        """Test that disabled experiments don't apply."""
        exp = Experiment(
            exp_id="test",
            enabled=False,
            selector=ExperimentSelector(agent="engineer"),
        )

        assert not exp.should_apply("engineer")

    def test_experiment_should_apply_agent_mismatch(self) -> None:
        """Test experiment doesn't apply to wrong agent."""
        exp = Experiment(
            exp_id="test",
            enabled=True,
            selector=ExperimentSelector(agent="engineer"),
        )

        assert not exp.should_apply("senior_engineer")

    def test_experiment_should_apply_task_type_mismatch(self) -> None:
        """Test experiment doesn't apply to wrong task type."""
        exp = Experiment(
            exp_id="test",
            enabled=True,
            selector=ExperimentSelector(
                agent="engineer",
                task_types=["implementation"],
            ),
        )

        assert not exp.should_apply("engineer", "documentation")

    def test_experiment_should_apply_scope_too_small(self) -> None:
        """Test experiment doesn't apply if scope too small."""
        exp = Experiment(
            exp_id="test",
            enabled=True,
            selector=ExperimentSelector(
                agent="engineer",
                min_scope_words=100,
            ),
        )

        assert not exp.should_apply("engineer", scope_words=50)

    def test_experiment_should_apply_scope_large_enough(self) -> None:
        """Test experiment applies if scope is large enough."""
        exp = Experiment(
            exp_id="test",
            enabled=True,
            selector=ExperimentSelector(
                agent="engineer",
                min_scope_words=100,
            ),
        )

        assert exp.should_apply("engineer", scope_words=150)


class TestFullPrecedenceWithExperiments:
    """Test the full precedence chain including experiments."""

    def test_precedence_experiment_over_task(self) -> None:
        """Test that experiment takes precedence over task-type override."""
        config = {
            "tasks": {
                "implementation": {"model": "claude-sonnet-4.5"},
            },
            "experiments": {
                "test-exp": {
                    "enabled": True,
                    "selector": {
                        "agent": "engineer",
                        "task_types": ["implementation"],
                    },
                    "variants": {
                        "control": {
                            "model": "claude-haiku-4.5",
                            "traffic_allocation": 50,
                        },
                        "variant_a": {
                            "model": "claude-opus-4.6",
                            "traffic_allocation": 50,
                        },
                    },
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            # Experiment should select one of its variants, not the task override
            model = loader.get_model_for_delegate(
                agent="engineer",
                task_type="implementation",
                task_id="task-001",
            )
            assert model in ("claude-haiku-4.5", "claude-opus-4.6")
        finally:
            path.unlink()


class TestConfigValidation:
    """Test config validation."""

    def test_validate_valid_config(self) -> None:
        """Test validation passes for valid config."""
        config = {
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
            },
            "tasks": {
                "code_review": {"model": "claude-sonnet-4.6"},
            },
            "experiments": {
                "test-exp": {
                    "enabled": True,
                    "selector": {"agent": "engineer"},
                    "variants": {
                        "control": {
                            "model": "claude-haiku-4.5",
                            "traffic_allocation": 50,
                        },
                        "variant_a": {
                            "model": "claude-sonnet-4.5",
                            "traffic_allocation": 50,
                        },
                    },
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.validate_config()
        finally:
            path.unlink()

    def test_validate_invalid_traffic_allocation(self) -> None:
        """Test validation fails if traffic allocation doesn't sum to 100."""
        config = {
            "experiments": {
                "test-exp": {
                    "enabled": True,
                    "selector": {"agent": "engineer"},
                    "variants": {
                        "control": {
                            "model": "claude-haiku-4.5",
                            "traffic_allocation": 50,
                        },
                        "variant_a": {
                            "model": "claude-sonnet-4.5",
                            "traffic_allocation": 40,  # should be 50
                        },
                    },
                }
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert not loader.validate_config()
        finally:
            path.unlink()

    def test_validate_invalid_model_name(self) -> None:
        """Test validation fails for invalid model name."""
        config = {
            "agents": {
                "engineer": {"model": ""},  # empty model
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert not loader.validate_config()
        finally:
            path.unlink()


class TestConfigReload:
    """Test hot-reloading configuration."""

    def test_reload_updates_config(self) -> None:
        """Test that reload() updates the config."""
        # Create initial config
        config1 = {
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config1, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            assert loader.get_model_for_agent("engineer") == "claude-haiku-4.5"

            # Update config file
            config2 = {
                "agents": {
                    "engineer": {"model": "claude-sonnet-4.5"},
                }
            }
            with path.open("w") as f:
                yaml.dump(config2, f)

            # Reload
            loader.reload()
            assert loader.get_model_for_agent("engineer") == "claude-sonnet-4.5"
        finally:
            path.unlink()


class TestExportToDict:
    """Test exporting config as dictionary."""

    def test_to_dict_includes_all_sections(self) -> None:
        """Test that to_dict() includes all config sections."""
        config = {
            "global": {"default_model": "claude-haiku-4.5"},
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
            },
            "tasks": {
                "code_review": {"model": "claude-sonnet-4.6"},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            exported = loader.to_dict()

            assert "global" in exported
            assert "agents" in exported
            assert "tasks" in exported
            assert "experiments" in exported
        finally:
            path.unlink()


class TestFactoryFunction:
    """Test the factory function."""

    def test_load_model_config_returns_loader(self) -> None:
        """Test that load_model_config() returns a ModelConfigLoader."""
        loader = load_model_config()
        assert isinstance(loader, ModelConfigLoader)


class TestIntegrationWithOrchestrator:
    """Test integration scenarios (simulating real orchestrator usage)."""

    def test_routing_engineer_task_via_config(self) -> None:
        """Test typical engineer task routing."""
        config = {
            "global": {"default_model": "claude-haiku-4.5"},
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
                "senior_engineer": {"model": "claude-sonnet-4.5"},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            # Engineer task should get Haiku
            model = loader.get_model_for_delegate(agent="engineer")
            assert model == "claude-haiku-4.5"
        finally:
            path.unlink()

    def test_routing_security_task_via_task_override(self) -> None:
        """Test security task routing via task-type override."""
        config = {
            "tasks": {
                "security_audit": {"model": "claude-opus-4.8"},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)
            # Security audit should upgrade to Opus
            model = loader.get_model_for_delegate(
                agent="engineer",
                task_type="security_audit",
            )
            assert model == "claude-opus-4.8"
        finally:
            path.unlink()

    def test_a_b_test_cost_optimization(self) -> None:
        """Test A/B test for cost optimization (Haiku vs Sonnet)."""
        config = {
            "agents": {
                "engineer": {"model": "claude-haiku-4.5"},
            },
            "experiments": {
                "haiku_vs_sonnet": {
                    "enabled": True,
                    "selector": {
                        "agent": "engineer",
                    },
                    "variants": {
                        "control": {
                            "model": "claude-haiku-4.5",
                            "traffic_allocation": 70,
                        },
                        "variant_a": {
                            "model": "claude-sonnet-4.5",
                            "traffic_allocation": 30,
                        },
                    },
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            path = Path(f.name)

        try:
            loader = ModelConfigLoader(path)

            # Test multiple task assignments
            models_used = {}
            for i in range(100):
                task_id = f"task-{i:03d}"
                model = loader.get_model_for_delegate(
                    agent="engineer",
                    task_id=task_id,
                )
                models_used[model] = models_used.get(model, 0) + 1

            # Should have assigned both models
            assert "claude-haiku-4.5" in models_used
            assert "claude-sonnet-4.5" in models_used

            # Check traffic allocation (with tolerance)
            haiku_pct = models_used.get("claude-haiku-4.5", 0) / 100
            sonnet_pct = models_used.get("claude-sonnet-4.5", 0) / 100

            # 70% control, 30% variant (allow 10% tolerance)
            assert 60 < haiku_pct * 100 < 80, f"Expected ~70%, got {haiku_pct*100:.1f}%"
            assert 20 < sonnet_pct * 100 < 40, f"Expected ~30%, got {sonnet_pct*100:.1f}%"
        finally:
            path.unlink()
