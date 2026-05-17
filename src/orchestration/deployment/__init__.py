"""
Deployment module for production rollout strategies.

Provides feature flags, monitoring, and deployment configuration
for dry-run, shadow, and gradual rollout modes.
"""

from .feature_flags import FeatureFlags, DeploymentMode, get_feature_flags
from .monitoring import DeploymentMonitor, AlertSeverity, MetricSnapshot
from .config_loader import DeploymentConfig, load_deployment_config

__all__ = [
    "FeatureFlags",
    "DeploymentMode",
    "get_feature_flags",
    "DeploymentMonitor",
    "AlertSeverity",
    "MetricSnapshot",
    "DeploymentConfig",
    "load_deployment_config",
]
