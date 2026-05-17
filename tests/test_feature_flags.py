"""
Feature Flag System — Tests.

Validates FeatureFlags loading from defaults, YAML config, and
environment variable overrides.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.orchestration.deployment.feature_flags import (
    DeploymentMode,
    FeatureFlags,
    get_feature_flags,
)


# ─────────────────────────────────────────────────────────────────────────── #
# Helpers
# ─────────────────────────────────────────────────────────────────────────── #

def _write_config(tmp_path: Path, data: dict) -> Path:
    cfg_file = tmp_path / "deployment.yaml"
    cfg_file.write_text(yaml.dump({"deployment": data}))
    return cfg_file


# ─────────────────────────────────────────────────────────────────────────── #
# 1. Default flags
# ─────────────────────────────────────────────────────────────────────────── #

class TestFeatureFlagsDefaults:
    def test_default_mode_is_production(self, tmp_path):
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.mode == DeploymentMode.PRODUCTION

    def test_dry_run_disabled_by_default(self, tmp_path):
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.dry_run.enabled is False

    def test_shadow_disabled_by_default(self, tmp_path):
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.shadow.enabled is False

    def test_rollout_disabled_by_default(self, tmp_path):
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.gradual_rollout.enabled is False

    def test_monitoring_enabled_by_default(self, tmp_path):
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.monitoring.enabled is True

    def test_rollback_enabled_by_default(self, tmp_path):
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.rollback.enabled is True


# ─────────────────────────────────────────────────────────────────────────── #
# 2. YAML config loading
# ─────────────────────────────────────────────────────────────────────────── #

class TestFeatureFlagsYamlLoading:
    def test_mode_loaded_from_yaml(self, tmp_path):
        cfg = _write_config(tmp_path, {"mode": "shadow"})
        flags = get_feature_flags(config_path=cfg)
        assert flags.mode == DeploymentMode.SHADOW

    def test_dry_run_enabled_from_yaml(self, tmp_path):
        cfg = _write_config(tmp_path, {"dry_run": {"enabled": True}})
        flags = get_feature_flags(config_path=cfg)
        assert flags.dry_run.enabled is True

    def test_shadow_traffic_pct_from_yaml(self, tmp_path):
        cfg = _write_config(tmp_path, {"shadow": {"enabled": True, "traffic_pct": 25}})
        flags = get_feature_flags(config_path=cfg)
        assert flags.shadow.traffic_pct == 25

    def test_rollout_stages_from_yaml(self, tmp_path):
        cfg = _write_config(tmp_path, {
            "gradual_rollout": {
                "enabled": True,
                "stages": [
                    {"traffic_pct": 10, "duration_hours": 12},
                    {"traffic_pct": 50, "duration_hours": 6},
                ],
            }
        })
        flags = get_feature_flags(config_path=cfg)
        assert len(flags.gradual_rollout.stages) == 2
        assert flags.gradual_rollout.stages[0].traffic_pct == 10

    def test_invalid_yaml_falls_back_to_defaults(self, tmp_path):
        bad_cfg = tmp_path / "bad.yaml"
        bad_cfg.write_text(":::invalid yaml:::")
        flags = get_feature_flags(config_path=bad_cfg)
        # Should fall back to defaults without raising
        assert flags.mode == DeploymentMode.PRODUCTION


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Environment variable overrides
# ─────────────────────────────────────────────────────────────────────────── #

class TestFeatureFlagsEnvOverrides:
    def test_deploy_mode_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEPLOY_MODE", "dry_run")
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.mode == DeploymentMode.DRY_RUN

    def test_deploy_dry_run_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEPLOY_DRY_RUN", "true")
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.dry_run.enabled is True

    def test_deploy_shadow_pct_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEPLOY_SHADOW_PCT", "50")
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.shadow.traffic_pct == 50

    def test_deploy_rollout_stage_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEPLOY_ROLLOUT_STAGE", "75")
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.gradual_rollout.current_stage == 75

    def test_env_overrides_yaml(self, monkeypatch, tmp_path):
        """Env var must win over YAML."""
        cfg = _write_config(tmp_path, {"mode": "shadow"})
        monkeypatch.setenv("DEPLOY_MODE", "production")
        flags = get_feature_flags(config_path=cfg)
        assert flags.mode == DeploymentMode.PRODUCTION

    def test_unknown_deploy_mode_ignored(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEPLOY_MODE", "unknown_mode")
        # Should not raise; falls back to default
        flags = get_feature_flags(config_path=tmp_path / "nonexistent.yaml")
        assert flags.mode == DeploymentMode.PRODUCTION


# ─────────────────────────────────────────────────────────────────────────── #
# 4. Convenience properties
# ─────────────────────────────────────────────────────────────────────────── #

class TestFeatureFlagsProperties:
    def test_is_dry_run_via_mode(self):
        flags = FeatureFlags(mode=DeploymentMode.DRY_RUN)
        assert flags.is_dry_run is True

    def test_is_dry_run_via_flag(self):
        flags = FeatureFlags()
        flags.dry_run.enabled = True
        assert flags.is_dry_run is True

    def test_is_shadow_via_mode(self):
        flags = FeatureFlags(mode=DeploymentMode.SHADOW)
        assert flags.is_shadow is True

    def test_is_production(self):
        flags = FeatureFlags(mode=DeploymentMode.PRODUCTION)
        assert flags.is_production is True
        assert flags.is_dry_run is False
        assert flags.is_shadow is False

    def test_to_dict_serialisable(self):
        import json
        flags = FeatureFlags()
        json.dumps(flags.to_dict())

    def test_to_dict_has_all_keys(self):
        flags = FeatureFlags()
        d = flags.to_dict()
        assert {"mode", "dry_run", "shadow", "gradual_rollout", "monitoring", "rollback"}.issubset(d.keys())
