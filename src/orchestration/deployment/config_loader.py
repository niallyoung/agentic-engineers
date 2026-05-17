"""
Deployment Configuration Loader.

Loads and validates deployment.yaml, providing typed access to all
deployment configuration values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "deployment.yaml"


@dataclass
class RolloutStage:
    traffic_pct: int
    duration_hours: int


@dataclass
class DeploymentConfig:
    """Typed representation of config/deployment.yaml."""
    mode: str = "production"
    dry_run_enabled: bool = False
    dry_run_collect_metrics: bool = True
    shadow_enabled: bool = False
    shadow_traffic_pct: int = 10
    rollout_enabled: bool = False
    rollout_stages: List[RolloutStage] = field(default_factory=lambda: [
        RolloutStage(10, 24),
        RolloutStage(25, 24),
        RolloutStage(50, 24),
        RolloutStage(75, 24),
        RolloutStage(100, 0),
    ])
    monitoring_enabled: bool = True
    alert_on_errors: bool = True
    alert_on_performance_degradation: bool = True
    rollback_enabled: bool = True
    auto_rollback_on_critical_error: bool = True

    def is_valid(self) -> bool:
        """Basic validation of config values."""
        if self.mode not in ("dry_run", "shadow", "gradual_rollout", "production"):
            return False
        if not (0 <= self.shadow_traffic_pct <= 100):
            return False
        for stage in self.rollout_stages:
            if not (0 <= stage.traffic_pct <= 100):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment": {
                "mode": self.mode,
                "dry_run": {
                    "enabled": self.dry_run_enabled,
                    "collect_metrics": self.dry_run_collect_metrics,
                },
                "shadow": {
                    "enabled": self.shadow_enabled,
                    "traffic_pct": self.shadow_traffic_pct,
                },
                "gradual_rollout": {
                    "enabled": self.rollout_enabled,
                    "stages": [
                        {"traffic_pct": s.traffic_pct, "duration_hours": s.duration_hours}
                        for s in self.rollout_stages
                    ],
                },
                "monitoring": {
                    "enabled": self.monitoring_enabled,
                    "alert_on_errors": self.alert_on_errors,
                    "alert_on_performance_degradation": self.alert_on_performance_degradation,
                },
                "rollback": {
                    "enabled": self.rollback_enabled,
                    "auto_rollback_on_critical_error": self.auto_rollback_on_critical_error,
                },
            }
        }


def load_deployment_config(config_path: Optional[Path] = None) -> DeploymentConfig:
    """Load deployment config from YAML file."""
    path = config_path or DEFAULT_CONFIG_PATH
    cfg = DeploymentConfig()

    try:
        if path.exists():
            with path.open() as fh:
                raw = yaml.safe_load(fh) or {}
            dep = raw.get("deployment", {})

            cfg.mode = dep.get("mode", cfg.mode)

            dr = dep.get("dry_run", {})
            cfg.dry_run_enabled = bool(dr.get("enabled", cfg.dry_run_enabled))
            cfg.dry_run_collect_metrics = bool(dr.get("collect_metrics", cfg.dry_run_collect_metrics))

            sh = dep.get("shadow", {})
            cfg.shadow_enabled = bool(sh.get("enabled", cfg.shadow_enabled))
            cfg.shadow_traffic_pct = int(sh.get("traffic_pct", cfg.shadow_traffic_pct))

            ro = dep.get("gradual_rollout", {})
            cfg.rollout_enabled = bool(ro.get("enabled", cfg.rollout_enabled))
            if "stages" in ro:
                cfg.rollout_stages = [
                    RolloutStage(s.get("traffic_pct", 10), s.get("duration_hours", 24))
                    for s in ro["stages"]
                ]

            mon = dep.get("monitoring", {})
            cfg.monitoring_enabled = bool(mon.get("enabled", cfg.monitoring_enabled))
            cfg.alert_on_errors = bool(mon.get("alert_on_errors", cfg.alert_on_errors))
            cfg.alert_on_performance_degradation = bool(
                mon.get("alert_on_performance_degradation", cfg.alert_on_performance_degradation)
            )

            rb = dep.get("rollback", {})
            cfg.rollback_enabled = bool(rb.get("enabled", cfg.rollback_enabled))
            cfg.auto_rollback_on_critical_error = bool(
                rb.get("auto_rollback_on_critical_error", cfg.auto_rollback_on_critical_error)
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load deployment config %s: %s", path, exc)

    return cfg
