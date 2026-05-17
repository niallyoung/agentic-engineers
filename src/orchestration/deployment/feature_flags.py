"""
Feature Flag System for Production Deployment.

Provides dynamic enable/disable of deployment modes (dry-run, shadow,
gradual rollout) without code changes. Flags are read from environment
variables and/or a YAML config file.

Environment Variable Overrides (highest priority):
    DEPLOY_MODE           — dry_run | shadow | gradual_rollout | production
    DEPLOY_DRY_RUN        — true | false
    DEPLOY_SHADOW         — true | false
    DEPLOY_SHADOW_PCT     — 1-100 (traffic percentage for shadow)
    DEPLOY_ROLLOUT        — true | false
    DEPLOY_ROLLOUT_STAGE  — 10 | 25 | 50 | 75 | 100

CLI usage:
    python -m src.orchestration.deployment.feature_flags --list
    python -m src.orchestration.deployment.feature_flags --set dry_run true
    python -m src.orchestration.deployment.feature_flags --set shadow_pct 25
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Default config path (can be overridden via DEPLOY_CONFIG env var)
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "deployment.yaml"


class DeploymentMode(str, Enum):
    """Top-level deployment mode."""
    DRY_RUN = "dry_run"
    SHADOW = "shadow"
    GRADUAL_ROLLOUT = "gradual_rollout"
    PRODUCTION = "production"


@dataclass
class DryRunFlags:
    enabled: bool = False
    collect_metrics: bool = True


@dataclass
class ShadowFlags:
    enabled: bool = False
    traffic_pct: int = 10


@dataclass
class RolloutStageConfig:
    traffic_pct: int
    duration_hours: int


@dataclass
class GradualRolloutFlags:
    enabled: bool = False
    current_stage: int = 10  # active traffic pct (10/25/50/75/100)
    stages: list = field(default_factory=lambda: [
        RolloutStageConfig(10, 24),
        RolloutStageConfig(25, 24),
        RolloutStageConfig(50, 24),
        RolloutStageConfig(75, 24),
        RolloutStageConfig(100, 0),
    ])


@dataclass
class MonitoringFlags:
    enabled: bool = True
    alert_on_errors: bool = True
    alert_on_performance_degradation: bool = True


@dataclass
class RollbackFlags:
    enabled: bool = True
    auto_rollback_on_critical_error: bool = True


@dataclass
class FeatureFlags:
    """
    Consolidated feature flags for deployment modes.

    Priority (highest → lowest):
      1. Environment variables
      2. YAML config file
      3. Hardcoded defaults
    """
    mode: DeploymentMode = DeploymentMode.PRODUCTION
    dry_run: DryRunFlags = field(default_factory=DryRunFlags)
    shadow: ShadowFlags = field(default_factory=ShadowFlags)
    gradual_rollout: GradualRolloutFlags = field(default_factory=GradualRolloutFlags)
    monitoring: MonitoringFlags = field(default_factory=MonitoringFlags)
    rollback: RollbackFlags = field(default_factory=RollbackFlags)

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #

    @property
    def is_dry_run(self) -> bool:
        return self.dry_run.enabled or self.mode == DeploymentMode.DRY_RUN

    @property
    def is_shadow(self) -> bool:
        return self.shadow.enabled or self.mode == DeploymentMode.SHADOW

    @property
    def is_gradual_rollout(self) -> bool:
        return self.gradual_rollout.enabled or self.mode == DeploymentMode.GRADUAL_ROLLOUT

    @property
    def is_production(self) -> bool:
        return self.mode == DeploymentMode.PRODUCTION

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "dry_run": asdict(self.dry_run),
            "shadow": asdict(self.shadow),
            "gradual_rollout": {
                "enabled": self.gradual_rollout.enabled,
                "current_stage": self.gradual_rollout.current_stage,
                "stages": [asdict(s) for s in self.gradual_rollout.stages],
            },
            "monitoring": asdict(self.monitoring),
            "rollback": asdict(self.rollback),
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FeatureFlags(mode={self.mode.value}, dry_run={self.is_dry_run}, "
            f"shadow={self.is_shadow}@{self.shadow.traffic_pct}%, "
            f"rollout={self.is_gradual_rollout}@stage{self.gradual_rollout.current_stage}%)"
        )


# ──────────────────────────────────────────────────────────────────────────── #
# Loader
# ──────────────────────────────────────────────────────────────────────────── #

def _load_yaml_flags(config_path: Path) -> Dict[str, Any]:
    """Load raw YAML deployment config, return empty dict on any error."""
    try:
        if config_path.exists():
            with config_path.open() as fh:
                data = yaml.safe_load(fh) or {}
            return data.get("deployment", {})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load deployment config %s: %s", config_path, exc)
    return {}


def _apply_env_overrides(flags: FeatureFlags) -> None:
    """Mutate *flags* in-place based on environment variables."""
    mode_env = os.environ.get("DEPLOY_MODE", "").strip().lower()
    if mode_env:
        try:
            flags.mode = DeploymentMode(mode_env)
        except ValueError:
            logger.warning("Unknown DEPLOY_MODE=%r — ignoring", mode_env)

    # Dry-run
    if "DEPLOY_DRY_RUN" in os.environ:
        flags.dry_run.enabled = os.environ["DEPLOY_DRY_RUN"].lower() in ("1", "true", "yes")

    # Shadow
    if "DEPLOY_SHADOW" in os.environ:
        flags.shadow.enabled = os.environ["DEPLOY_SHADOW"].lower() in ("1", "true", "yes")
    if "DEPLOY_SHADOW_PCT" in os.environ:
        try:
            flags.shadow.traffic_pct = int(os.environ["DEPLOY_SHADOW_PCT"])
        except ValueError:
            logger.warning("Invalid DEPLOY_SHADOW_PCT — ignoring")

    # Rollout
    if "DEPLOY_ROLLOUT" in os.environ:
        flags.gradual_rollout.enabled = os.environ["DEPLOY_ROLLOUT"].lower() in ("1", "true", "yes")
    if "DEPLOY_ROLLOUT_STAGE" in os.environ:
        try:
            flags.gradual_rollout.current_stage = int(os.environ["DEPLOY_ROLLOUT_STAGE"])
        except ValueError:
            logger.warning("Invalid DEPLOY_ROLLOUT_STAGE — ignoring")


def get_feature_flags(config_path: Optional[Path] = None) -> FeatureFlags:
    """
    Build and return a :class:`FeatureFlags` instance.

    Resolution order:
      1. Defaults
      2. YAML config file (``config_path`` or ``DEPLOY_CONFIG`` env var or default path)
      3. Environment variable overrides
    """
    # Resolve config file path
    if config_path is None:
        env_path = os.environ.get("DEPLOY_CONFIG", "")
        config_path = Path(env_path) if env_path else DEFAULT_CONFIG_PATH

    raw = _load_yaml_flags(config_path)

    flags = FeatureFlags()

    # Apply YAML values
    if raw.get("mode"):
        try:
            flags.mode = DeploymentMode(raw["mode"])
        except ValueError:
            pass

    dr = raw.get("dry_run", {})
    flags.dry_run.enabled = bool(dr.get("enabled", flags.dry_run.enabled))
    flags.dry_run.collect_metrics = bool(dr.get("collect_metrics", flags.dry_run.collect_metrics))

    sh = raw.get("shadow", {})
    flags.shadow.enabled = bool(sh.get("enabled", flags.shadow.enabled))
    flags.shadow.traffic_pct = int(sh.get("traffic_pct", flags.shadow.traffic_pct))

    ro = raw.get("gradual_rollout", {})
    flags.gradual_rollout.enabled = bool(ro.get("enabled", flags.gradual_rollout.enabled))
    if "stages" in ro:
        flags.gradual_rollout.stages = [
            RolloutStageConfig(
                traffic_pct=s.get("traffic_pct", 10),
                duration_hours=s.get("duration_hours", 24),
            )
            for s in ro["stages"]
        ]

    mon = raw.get("monitoring", {})
    flags.monitoring.enabled = bool(mon.get("enabled", flags.monitoring.enabled))
    flags.monitoring.alert_on_errors = bool(mon.get("alert_on_errors", flags.monitoring.alert_on_errors))
    flags.monitoring.alert_on_performance_degradation = bool(
        mon.get("alert_on_performance_degradation", flags.monitoring.alert_on_performance_degradation)
    )

    rb = raw.get("rollback", {})
    flags.rollback.enabled = bool(rb.get("enabled", flags.rollback.enabled))
    flags.rollback.auto_rollback_on_critical_error = bool(
        rb.get("auto_rollback_on_critical_error", flags.rollback.auto_rollback_on_critical_error)
    )

    # Env overrides (highest priority)
    _apply_env_overrides(flags)

    logger.debug("FeatureFlags loaded: %s", flags)
    return flags


# ──────────────────────────────────────────────────────────────────────────── #
# CLI
# ──────────────────────────────────────────────────────────────────────────── #

def _cli() -> None:  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Manage deployment feature flags")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List current flag values")

    set_p = sub.add_parser("set", help="Set a flag value")
    set_p.add_argument("key", help="Flag key (e.g. dry_run, shadow_pct, rollout_stage)")
    set_p.add_argument("value", help="Value to set")

    args = parser.parse_args()

    flags = get_feature_flags()

    if args.cmd == "list" or args.cmd is None:
        print(json.dumps(flags.to_dict(), indent=2))
    elif args.cmd == "set":
        _KEY_TO_ENV = {
            "mode": "DEPLOY_MODE",
            "dry_run": "DEPLOY_DRY_RUN",
            "shadow": "DEPLOY_SHADOW",
            "shadow_pct": "DEPLOY_SHADOW_PCT",
            "rollout": "DEPLOY_ROLLOUT",
            "rollout_stage": "DEPLOY_ROLLOUT_STAGE",
        }
        env_key = _KEY_TO_ENV.get(args.key)
        if env_key:
            print(f"Set environment variable: {env_key}={args.value}")
            print(f"(export {env_key}={args.value})")
        else:
            print(f"Unknown flag key: {args.key!r}")
            print(f"Valid keys: {list(_KEY_TO_ENV)}")


if __name__ == "__main__":  # pragma: no cover
    _cli()
