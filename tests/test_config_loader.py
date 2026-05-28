"""
Tests for orchestration/deployment/config_loader.py

Targets: DeploymentConfig.is_valid(), DeploymentConfig.to_dict(),
         load_deployment_config() — all missing from existing coverage.

Coverage target: 42% → 90%+
"""

import pytest
import yaml
from pathlib import Path

from src.orchestration.deployment.config_loader import (
    DeploymentConfig,
    RolloutStage,
    load_deployment_config,
)


class TestDeploymentConfigIsValid:
    """Tests for DeploymentConfig.is_valid()."""

    def test_default_config_is_valid(self):
        """Default config values should pass validation."""
        cfg = DeploymentConfig()
        assert cfg.is_valid() is True

    def test_valid_production_mode(self):
        """'production' is a valid mode."""
        cfg = DeploymentConfig(mode="production")
        assert cfg.is_valid() is True

    def test_valid_dry_run_mode(self):
        """'dry_run' is a valid mode."""
        cfg = DeploymentConfig(mode="dry_run")
        assert cfg.is_valid() is True

    def test_valid_shadow_mode(self):
        """'shadow' is a valid mode."""
        cfg = DeploymentConfig(mode="shadow")
        assert cfg.is_valid() is True

    def test_valid_gradual_rollout_mode(self):
        """'gradual_rollout' is a valid mode."""
        cfg = DeploymentConfig(mode="gradual_rollout")
        assert cfg.is_valid() is True

    def test_invalid_mode_returns_false(self):
        """Unknown deployment mode should fail validation."""
        cfg = DeploymentConfig(mode="experimental")
        assert cfg.is_valid() is False

    def test_shadow_traffic_pct_zero_is_valid(self):
        """Shadow traffic at 0% is valid."""
        cfg = DeploymentConfig(shadow_traffic_pct=0)
        assert cfg.is_valid() is True

    def test_shadow_traffic_pct_100_is_valid(self):
        """Shadow traffic at 100% is valid."""
        cfg = DeploymentConfig(shadow_traffic_pct=100)
        assert cfg.is_valid() is True

    def test_shadow_traffic_pct_negative_is_invalid(self):
        """Shadow traffic below 0% should fail."""
        cfg = DeploymentConfig(shadow_traffic_pct=-1)
        assert cfg.is_valid() is False

    def test_shadow_traffic_pct_over_100_is_invalid(self):
        """Shadow traffic above 100% should fail."""
        cfg = DeploymentConfig(shadow_traffic_pct=101)
        assert cfg.is_valid() is False

    def test_rollout_stage_with_invalid_traffic_pct_is_invalid(self):
        """A rollout stage with traffic_pct > 100 should fail."""
        cfg = DeploymentConfig(
            rollout_stages=[RolloutStage(traffic_pct=150, duration_hours=24)]
        )
        assert cfg.is_valid() is False

    def test_rollout_stage_with_negative_traffic_pct_is_invalid(self):
        """A rollout stage with traffic_pct < 0 should fail."""
        cfg = DeploymentConfig(
            rollout_stages=[RolloutStage(traffic_pct=-5, duration_hours=24)]
        )
        assert cfg.is_valid() is False

    def test_empty_rollout_stages_is_valid(self):
        """Empty rollout_stages list should be valid."""
        cfg = DeploymentConfig(rollout_stages=[])
        assert cfg.is_valid() is True


class TestDeploymentConfigToDict:
    """Tests for DeploymentConfig.to_dict()."""

    def test_to_dict_returns_dict(self):
        """to_dict() should return a dict."""
        cfg = DeploymentConfig()
        result = cfg.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_has_deployment_key(self):
        """to_dict() should have top-level 'deployment' key."""
        cfg = DeploymentConfig()
        result = cfg.to_dict()
        assert "deployment" in result

    def test_to_dict_mode(self):
        """to_dict() should include the mode."""
        cfg = DeploymentConfig(mode="shadow")
        result = cfg.to_dict()
        assert result["deployment"]["mode"] == "shadow"

    def test_to_dict_dry_run(self):
        """to_dict() should include dry_run settings."""
        cfg = DeploymentConfig(dry_run_enabled=True, dry_run_collect_metrics=False)
        result = cfg.to_dict()
        dr = result["deployment"]["dry_run"]
        assert dr["enabled"] is True
        assert dr["collect_metrics"] is False

    def test_to_dict_shadow(self):
        """to_dict() should include shadow settings."""
        cfg = DeploymentConfig(shadow_enabled=True, shadow_traffic_pct=25)
        result = cfg.to_dict()
        sh = result["deployment"]["shadow"]
        assert sh["enabled"] is True
        assert sh["traffic_pct"] == 25

    def test_to_dict_gradual_rollout(self):
        """to_dict() should include gradual rollout stages."""
        stages = [RolloutStage(10, 24), RolloutStage(50, 12)]
        cfg = DeploymentConfig(rollout_enabled=True, rollout_stages=stages)
        result = cfg.to_dict()
        ro = result["deployment"]["gradual_rollout"]
        assert ro["enabled"] is True
        assert len(ro["stages"]) == 2
        assert ro["stages"][0]["traffic_pct"] == 10
        assert ro["stages"][1]["traffic_pct"] == 50

    def test_to_dict_monitoring(self):
        """to_dict() should include monitoring settings."""
        cfg = DeploymentConfig(
            monitoring_enabled=False,
            alert_on_errors=False,
            alert_on_performance_degradation=False,
        )
        result = cfg.to_dict()
        mon = result["deployment"]["monitoring"]
        assert mon["enabled"] is False
        assert mon["alert_on_errors"] is False
        assert mon["alert_on_performance_degradation"] is False

    def test_to_dict_rollback(self):
        """to_dict() should include rollback settings."""
        cfg = DeploymentConfig(rollback_enabled=False, auto_rollback_on_critical_error=False)
        result = cfg.to_dict()
        rb = result["deployment"]["rollback"]
        assert rb["enabled"] is False
        assert rb["auto_rollback_on_critical_error"] is False


class TestLoadDeploymentConfig:
    """Tests for load_deployment_config()."""

    def test_load_from_nonexistent_path_returns_defaults(self, tmp_path):
        """Missing config file should return default config."""
        nonexistent = tmp_path / "nonexistent.yaml"
        cfg = load_deployment_config(nonexistent)
        assert isinstance(cfg, DeploymentConfig)
        assert cfg.mode == "production"  # default

    def test_load_from_valid_yaml(self, tmp_path):
        """Config file with valid YAML should override defaults."""
        config_data = {
            "deployment": {
                "mode": "shadow",
                "shadow": {
                    "enabled": True,
                    "traffic_pct": 20,
                },
            }
        }
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_deployment_config(config_file)
        assert cfg.mode == "shadow"
        assert cfg.shadow_enabled is True
        assert cfg.shadow_traffic_pct == 20

    def test_load_dry_run_settings(self, tmp_path):
        """Config with dry_run section should populate fields."""
        config_data = {
            "deployment": {
                "mode": "dry_run",
                "dry_run": {
                    "enabled": True,
                    "collect_metrics": False,
                },
            }
        }
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_deployment_config(config_file)
        assert cfg.mode == "dry_run"
        assert cfg.dry_run_enabled is True
        assert cfg.dry_run_collect_metrics is False

    def test_load_gradual_rollout_stages(self, tmp_path):
        """Config with rollout stages should build RolloutStage list."""
        config_data = {
            "deployment": {
                "mode": "gradual_rollout",
                "gradual_rollout": {
                    "enabled": True,
                    "stages": [
                        {"traffic_pct": 10, "duration_hours": 24},
                        {"traffic_pct": 50, "duration_hours": 12},
                        {"traffic_pct": 100, "duration_hours": 0},
                    ],
                },
            }
        }
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_deployment_config(config_file)
        assert cfg.rollout_enabled is True
        assert len(cfg.rollout_stages) == 3
        assert cfg.rollout_stages[0].traffic_pct == 10
        assert cfg.rollout_stages[1].traffic_pct == 50
        assert cfg.rollout_stages[2].traffic_pct == 100

    def test_load_monitoring_settings(self, tmp_path):
        """Config with monitoring section should populate fields."""
        config_data = {
            "deployment": {
                "monitoring": {
                    "enabled": False,
                    "alert_on_errors": False,
                    "alert_on_performance_degradation": True,
                },
            }
        }
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_deployment_config(config_file)
        assert cfg.monitoring_enabled is False
        assert cfg.alert_on_errors is False
        assert cfg.alert_on_performance_degradation is True

    def test_load_rollback_settings(self, tmp_path):
        """Config with rollback section should populate fields."""
        config_data = {
            "deployment": {
                "rollback": {
                    "enabled": True,
                    "auto_rollback_on_critical_error": False,
                },
            }
        }
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_deployment_config(config_file)
        assert cfg.rollback_enabled is True
        assert cfg.auto_rollback_on_critical_error is False

    def test_load_empty_yaml_returns_defaults(self, tmp_path):
        """Empty YAML file should return defaults without crashing."""
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text("")

        cfg = load_deployment_config(config_file)
        assert isinstance(cfg, DeploymentConfig)
        assert cfg.mode == "production"

    def test_load_yaml_without_deployment_key_returns_defaults(self, tmp_path):
        """YAML without 'deployment' key should return defaults."""
        config_data = {"other": {"key": "value"}}
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_deployment_config(config_file)
        assert cfg.mode == "production"

    def test_load_invalid_yaml_returns_defaults(self, tmp_path):
        """Invalid YAML should return defaults without raising."""
        config_file = tmp_path / "deployment.yaml"
        config_file.write_text("{ invalid: yaml: content: [")

        cfg = load_deployment_config(config_file)
        assert isinstance(cfg, DeploymentConfig)

    def test_load_uses_default_path_when_none(self):
        """load_deployment_config(None) should use DEFAULT_CONFIG_PATH."""
        cfg = load_deployment_config(None)
        assert isinstance(cfg, DeploymentConfig)
        # Should not raise regardless of whether the default file exists
