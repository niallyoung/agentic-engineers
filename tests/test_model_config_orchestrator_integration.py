"""
Integration test for model config with OrchestratorAgent.

Tests that:
- OrchestratorAgent loads model-config.yaml at startup
- Model selection works through full precedence chain
- Task routing can use model-based decisions
- Config is accessible throughout orchestrator lifecycle
"""

import tempfile
from pathlib import Path

import pytest

from src.orchestration.agents.orchestrator import OrchestratorAgent


class TestModelConfigIntegration:
    """Test model config integration with OrchestratorAgent."""

    def test_orchestrator_loads_model_config(self):
        """Test that OrchestratorAgent loads model config at initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Verify model_config is initialized
            assert hasattr(orch, "model_config")
            assert orch.model_config is not None
            assert orch.model_config.global_default == "claude-haiku-4.5"

    def test_orchestrator_model_selection_per_agent(self):
        """Test per-agent model selection through orchestrator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Engineer should get Haiku
            model = orch.model_config.get_model_for_delegate(agent="engineer")
            assert model == "claude-haiku-4.5"

            # Principal engineer should get Opus-5
            model = orch.model_config.get_model_for_delegate(
                agent="principal_engineer"
            )
            assert model == "claude-opus-5"

            # Security engineer should get Fable-5 (unconditional default)
            model = orch.model_config.get_model_for_delegate(
                agent="security_engineer"
            )
            assert model == "claude-fable-5"

    def test_orchestrator_model_selection_per_task(self):
        """Test per-task-type model override through orchestrator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Security audit task should upgrade to Fable-5
            model = orch.model_config.get_model_for_delegate(
                agent="engineer", task_type="security_audit"
            )
            assert model == "claude-fable-5"

            # Documentation should stay with Haiku
            model = orch.model_config.get_model_for_delegate(
                agent="engineer", task_type="documentation"
            )
            assert model == "claude-haiku-4.5"

    def test_orchestrator_precedence_chain(self):
        """Test full precedence: experiment > task > agent > global."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Task override should take precedence over agent
            # (unless experiment applies, which it shouldn't since not enabled)
            model = orch.model_config.get_model_for_delegate(
                agent="engineer",
                task_type="code_review",  # Has task override
            )
            assert model == "claude-sonnet-5"

            # No override = agent default
            model = orch.model_config.get_model_for_delegate(
                agent="quality_engineer",
                task_type="unknown_task",  # No override for this task
            )
            assert model == "claude-sonnet-5"  # agent default

    def test_orchestrator_fallback_to_global(self):
        """Test fallback to global default for unconfigured agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Unknown agent should use global default
            model = orch.model_config.get_model_for_delegate(
                agent="nonexistent_agent"
            )
            assert model == "claude-haiku-4.5"

    def test_orchestrator_config_validation(self):
        """Test that loaded config passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Config should be valid
            assert orch.model_config.validate_config()

    def test_orchestrator_config_export(self):
        """Test config export for debugging/logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            config_dict = orch.model_config.to_dict()

            # Should have all sections
            assert "global" in config_dict
            assert "agents" in config_dict
            assert "tasks" in config_dict
            assert "experiments" in config_dict

            # Should have content
            assert config_dict["global"]["default_model"] == "claude-haiku-4.5"
            assert "engineer" in config_dict["agents"]
            assert "security_audit" in config_dict["tasks"]

    def test_model_selection_for_delegate_block(self):
        """Test realistic scenario: selecting model for a DELEGATE block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Scenario 1: Engineer with implementation task (no special overrides)
            model = orch.model_config.get_model_for_delegate(
                agent="engineer",
                task_type="implementation",
                task_id="task-001",
                scope_word_count=100,
            )
            assert model == "claude-haiku-4.5"  # Engineer default

            # Scenario 2: Engineer with security audit (task override)
            model = orch.model_config.get_model_for_delegate(
                agent="engineer",
                task_type="security_audit",
                task_id="task-002",
                scope_word_count=200,
            )
            assert model == "claude-fable-5"  # Upgraded by task override

            # Scenario 3: Principal engineer with architecture design
            model = orch.model_config.get_model_for_delegate(
                agent="principal_engineer",
                task_type="architecture_design",
                task_id="task-003",
                scope_word_count=500,
            )
            # No task override for "architecture_design" -> falls through to agent default
            assert model == "claude-opus-5"  # Agent default

    def test_provider_registry_available(self):
        """Test that provider registry is accessible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Provider preference should be available
            provider_pref = orch.model_config.config.get("provider_preference", {})
            assert provider_pref.get("primary") == "anthropic"

            # Provider models should be available
            provider_models = provider_pref.get("provider_models", {})
            assert "anthropic" in provider_models
            assert "openai" in provider_models
            assert "google" in provider_models

            # Anthropic should have role mappings
            anthropic = provider_models.get("anthropic", {})
            assert "engineer" in anthropic
            assert anthropic["engineer"] == "claude-haiku-4.5"

    def test_experiments_defined(self):
        """Test that experiments are defined in the config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = OrchestratorAgent(queue_dir=tmpdir)

            # Should have experiments defined
            assert len(orch.model_config.experiments) > 0

            # Check that at least one experiment exists
            exp_ids = list(orch.model_config.experiments.keys())
            assert "experiment_2026_06_13_haiku_vs_sonnet" in exp_ids or len(exp_ids) > 0
