"""
Model Configuration Loader — Runtime Model Selection & Experimentation.

Loads model-config.yaml at startup and applies runtime overrides:
- Per-agent model selection
- Per-task-type model selection
- Experiment (A/B test) variant assignment
- Cost-based model downgrades

Supports hot-reload without restart via reload() method.
"""

from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "model-config.yaml"


@dataclass
class ExperimentVariant:
    """Single variant in an A/B test experiment."""
    name: str
    model: str
    traffic_allocation: int
    notes: str = ""


@dataclass
class ExperimentSelector:
    """Criteria for selecting which tasks match an experiment."""
    agent: Optional[str] = None
    task_types: List[str] = field(default_factory=list)  # empty = all
    min_complexity: int = 0  # 0-10 scale; 0 = applies to all
    min_scope_words: int = 0  # 0 = applies to all


@dataclass
class Experiment:
    """A/B test configuration with traffic allocation."""
    exp_id: str
    enabled: bool = True
    name: str = ""
    description: str = ""
    selector: Optional[ExperimentSelector] = None
    variants: Dict[str, ExperimentVariant] = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    early_stop_threshold: float = 0.80
    notes: str = ""

    def should_apply(self, agent: str, task_type: Optional[str] = None, scope_words: int = 0) -> bool:
        """Check if this experiment should be applied to the given task."""
        if not self.enabled:
            return False

        if self.selector is None:
            return False

        # Check agent
        if self.selector.agent and self.selector.agent != agent:
            return False

        # Check task type
        if self.selector.task_types and task_type not in self.selector.task_types:
            return False

        # Check scope word count
        if scope_words < self.selector.min_scope_words:
            return False

        return True

    def select_variant(self, variant_seed: str) -> str:
        """
        Select a variant deterministically based on seed.

        Uses hash-based assignment to ensure consistent variant assignment
        for the same seed (idempotent). Respects traffic_allocation percentages.
        """
        if not self.variants:
            return ""

        # Create deterministic variant selection using seed
        hash_val = int(hashlib.md5(variant_seed.encode()).hexdigest(), 16)
        bucket = hash_val % 100

        cumulative = 0
        for variant_name, variant in self.variants.items():
            cumulative += variant.traffic_allocation
            if bucket < cumulative:
                return variant_name

        # Fallback: return first variant if rounding issues
        return list(self.variants.keys())[0]


class ModelConfigLoader:
    """Load and manage runtime model configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize loader with optional config path."""
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.agents: Dict[str, str] = {}  # agent role → model
        self.tasks: Dict[str, str] = {}  # task type → model
        self.experiments: Dict[str, Experiment] = {}  # exp_id → Experiment
        self.global_default: str = "claude-haiku-4.5"
        self.debug_mode: bool = False
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        self.config = {}
        self.agents = {}
        self.tasks = {}
        self.experiments = {}

        if not self.config_path.exists():
            logger.warning("Model config file not found: %s; using defaults", self.config_path)
            return

        try:
            with self.config_path.open() as fh:
                self.config = yaml.safe_load(fh) or {}

            # Load global settings
            global_cfg = self.config.get("global", {})
            self.global_default = global_cfg.get("default_model", "claude-haiku-4.5")
            self.debug_mode = global_cfg.get("debug_mode", False)

            # Load per-agent overrides
            for agent_role, agent_cfg in self.config.get("agents", {}).items():
                if isinstance(agent_cfg, dict) and "model" in agent_cfg:
                    self.agents[agent_role] = agent_cfg["model"]
                    if self.debug_mode:
                        logger.debug("Agent %s → %s", agent_role, agent_cfg["model"])

            # Load per-task-type overrides
            for task_type, task_cfg in self.config.get("tasks", {}).items():
                if isinstance(task_cfg, dict) and "model" in task_cfg:
                    self.tasks[task_type] = task_cfg["model"]
                    if self.debug_mode:
                        logger.debug("Task type %s → %s", task_type, task_cfg["model"])

            # Load experiments
            for exp_id, exp_cfg in self.config.get("experiments", {}).items():
                if not isinstance(exp_cfg, dict):
                    continue

                # Parse selector
                selector_cfg = exp_cfg.get("selector", {})
                selector = ExperimentSelector(
                    agent=selector_cfg.get("agent"),
                    task_types=selector_cfg.get("task_types", []),
                    min_complexity=selector_cfg.get("min_complexity", 0),
                    min_scope_words=selector_cfg.get("min_scope_words", 0),
                )

                # Parse variants
                variants = {}
                for variant_name, variant_cfg in exp_cfg.get("variants", {}).items():
                    if isinstance(variant_cfg, dict):
                        variants[variant_name] = ExperimentVariant(
                            name=variant_name,
                            model=variant_cfg.get("model", ""),
                            traffic_allocation=variant_cfg.get("traffic_allocation", 0),
                            notes=variant_cfg.get("notes", ""),
                        )

                exp = Experiment(
                    exp_id=exp_id,
                    enabled=exp_cfg.get("enabled", False),
                    name=exp_cfg.get("name", ""),
                    description=exp_cfg.get("description", ""),
                    selector=selector,
                    variants=variants,
                    start_date=exp_cfg.get("start_date", ""),
                    end_date=exp_cfg.get("end_date", ""),
                    early_stop_threshold=exp_cfg.get("early_stop_threshold", 0.80),
                    notes=exp_cfg.get("notes", ""),
                )

                self.experiments[exp_id] = exp
                if self.debug_mode:
                    logger.debug("Experiment %s (enabled=%s)", exp_id, exp.enabled)

        except Exception as exc:
            logger.warning("Error loading model config %s: %s", self.config_path, exc)

    def reload(self) -> None:
        """Hot-reload configuration without restart."""
        logger.info("Reloading model config from %s", self.config_path)
        self._load_config()

    def get_model_for_agent(self, agent: str) -> str:
        """
        Get model for a given agent role.

        Returns: Agent-specific model, or global default if not configured.
        """
        if agent in self.agents:
            return self.agents[agent]
        return self.global_default

    def get_model_for_task(
        self,
        task_type: str,
    ) -> Optional[str]:
        """
        Get model for a given task type.

        Returns: Task-specific model, or None if not configured.
        """
        return self.tasks.get(task_type)

    def get_model_for_delegate(
        self,
        agent: str,
        task_type: Optional[str] = None,
        task_id: Optional[str] = None,
        scope_word_count: int = 0,
    ) -> str:
        """
        Determine the best model for a DELEGATE using the full precedence chain.

        Precedence (highest to lowest):
        1. Experiment variant (if task matches experiment selector)
        2. Task-type override
        3. Agent-specific override
        4. Global default

        Args:
            agent: Agent role (e.g., "engineer")
            task_type: Task type (e.g., "code_review")
            task_id: Task ID (used for deterministic variant assignment)
            scope_word_count: Word count in scope (used for experiment selector)

        Returns: Selected model name
        """
        # 1. Check experiments (highest precedence)
        if task_id:
            for exp in self.experiments.values():
                if exp.should_apply(agent, task_type, scope_word_count):
                    variant_name = exp.select_variant(task_id)
                    if variant_name in exp.variants:
                        model = exp.variants[variant_name].model
                        if self.debug_mode:
                            logger.debug(
                                "DELEGATE %s: experiment %s → variant %s → %s",
                                task_id,
                                exp.exp_id,
                                variant_name,
                                model,
                            )
                        return model

        # 2. Check task-type override
        if task_type:
            task_model = self.get_model_for_task(task_type)
            if task_model:
                if self.debug_mode:
                    logger.debug(
                        "DELEGATE %s: task type %s → %s",
                        task_id,
                        task_type,
                        task_model,
                    )
                return task_model

        # 3. Check agent-specific override
        agent_model = self.get_model_for_agent(agent)
        if self.debug_mode:
            logger.debug(
                "DELEGATE %s: agent %s → %s",
                task_id,
                agent,
                agent_model,
            )
        return agent_model

    def validate_config(self) -> bool:
        """
        Validate configuration consistency.

        Checks:
        - All model names are non-empty strings
        - Traffic allocations sum to 100 per experiment
        - Required fields present

        Returns: True if config is valid
        """
        # Check agents
        for agent, model in self.agents.items():
            if not isinstance(model, str) or not model.strip():
                logger.error("Invalid model for agent %s: %s", agent, model)
                return False

        # Check tasks
        for task_type, model in self.tasks.items():
            if not isinstance(model, str) or not model.strip():
                logger.error("Invalid model for task %s: %s", task_type, model)
                return False

        # Check experiments
        for exp_id, exp in self.experiments.items():
            if not exp.variants:
                logger.error("Experiment %s has no variants", exp_id)
                return False

            total_traffic = sum(v.traffic_allocation for v in exp.variants.values())
            if total_traffic != 100:
                logger.error(
                    "Experiment %s variants don't sum to 100%% traffic: %d%%",
                    exp_id,
                    total_traffic,
                )
                return False

            for variant_name, variant in exp.variants.items():
                if not isinstance(variant.model, str) or not variant.model.strip():
                    logger.error(
                        "Experiment %s variant %s has invalid model: %s",
                        exp_id,
                        variant_name,
                        variant.model,
                    )
                    return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Export config as dictionary (for debugging/logging)."""
        return {
            "global": {
                "default_model": self.global_default,
                "debug_mode": self.debug_mode,
            },
            "agents": self.agents,
            "tasks": self.tasks,
            "experiments": {
                exp_id: {
                    "enabled": exp.enabled,
                    "name": exp.name,
                    "variants": {
                        v_name: {
                            "model": v.model,
                            "traffic_allocation": v.traffic_allocation,
                        }
                        for v_name, v in exp.variants.items()
                    },
                }
                for exp_id, exp in self.experiments.items()
            },
        }


def load_model_config(config_path: Optional[Path] = None) -> ModelConfigLoader:
    """Factory function to load model config."""
    return ModelConfigLoader(config_path)
