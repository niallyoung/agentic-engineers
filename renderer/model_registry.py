from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.orchestration.agents.model_resolver import ModelResolver, ModelNotFoundError


AGENT_ROLE_MAPPING = {
    "orchestrator": "general_orchestrator",
}

HARNESS_PROVIDER_MAPPING = {
    "copilot": "copilot",
    "claude": "claude",
    "pi": "claude",
    "opencode": "claude",
}

OPENCODE_PROVIDER_PREFIX = "github-copilot"


@dataclass(frozen=True)
class ModelTarget:
    agent_name: str
    registry_role: str
    model: str


class HarnessModelRegistry:
    """Shared harness-facing model registry backed by src/config/models.yaml."""

    def __init__(self, repo_root: Path | None = None, models_yaml_path: Path | None = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent
        self.models_yaml_path = models_yaml_path or self.repo_root / "src" / "config" / "models.yaml"
        self.resolver = ModelResolver(str(self.models_yaml_path), fallback_to_defaults=False)
        config = yaml.safe_load(self.models_yaml_path.read_text(encoding="utf-8")) or {}
        self.model_catalog: dict[str, list[str]] = config.get("provider_model_catalog", {})

    @staticmethod
    def normalize_agent_name(name: str) -> str:
        return name.strip().replace("_", "-")

    def agent_name_to_role(self, agent_name: str) -> str:
        normalized = self.normalize_agent_name(agent_name)
        mapped = AGENT_ROLE_MAPPING.get(normalized)
        if mapped:
            return mapped
        return normalized.replace("-", "_")

    def role_to_agent_name(self, role: str) -> str:
        for agent_name, mapped_role in AGENT_ROLE_MAPPING.items():
            if mapped_role == role:
                return agent_name
        return role.replace("_", "-")

    def harness_provider(self, harness: str) -> str:
        normalized = harness.strip().lower()
        if normalized not in HARNESS_PROVIDER_MAPPING:
            raise KeyError(f"Unknown harness '{harness}'")
        return HARNESS_PROVIDER_MAPPING[normalized]

    def source_model(self, agent_name: str) -> str:
        role = self.agent_name_to_role(agent_name)
        model = self.resolver.get_provider_specific(role, "claude")
        if not model:
            raise ModelNotFoundError(f"No claude model mapping found for role '{role}'")
        return model

    def render_model(self, agent_name: str, harness: str) -> str:
        normalized_harness = harness.strip().lower()
        role = self.agent_name_to_role(agent_name)
        provider = self.harness_provider(normalized_harness)
        model = self.resolver.get_provider_specific(role, provider)
        if not model:
            raise ModelNotFoundError(
                f"No provider mapping found for role '{role}' on harness '{normalized_harness}'"
            )
        if normalized_harness == "opencode":
            return f"{OPENCODE_PROVIDER_PREFIX}/{model}"
        return model

    def model_targets(self, harness: str) -> list[ModelTarget]:
        targets: list[ModelTarget] = []
        for role in self.resolver.models_config:
            agent_name = self.role_to_agent_name(role)
            try:
                model = self.render_model(agent_name, harness)
            except ModelNotFoundError:
                continue
            targets.append(ModelTarget(agent_name=agent_name, registry_role=role, model=model))
        return sorted(targets, key=lambda target: target.agent_name)

    def source_targets(self) -> list[ModelTarget]:
        targets: list[ModelTarget] = []
        for role in self.resolver.models_config:
            agent_name = self.role_to_agent_name(role)
            try:
                model = self.source_model(agent_name)
            except ModelNotFoundError:
                continue
            targets.append(ModelTarget(agent_name=agent_name, registry_role=role, model=model))
        return sorted(targets, key=lambda target: target.agent_name)

    def known_models(self, include_aliases: bool = True) -> set[str]:
        models: set[str] = set()
        for catalog_models in self.model_catalog.values():
            models.update(catalog_models)
        for role in self.resolver.models_config:
            role_config = self.resolver.models_config[role]
            models.update(role_config.get("providers", {}).values())
            canonical = role_config.get("canonical")
            if canonical:
                models.add(canonical)
                if include_aliases and canonical.startswith("claude-"):
                    models.add(canonical[len("claude-"):])
        models.update(self.render_model(target.agent_name, "opencode") for target in self.source_targets())
        return {model for model in models if model}

    def allowed_copilot_models(self) -> set[str]:
        return {target.model for target in self.model_targets("copilot")}


def detect_harness_from_agents_dir(agents_dir: Path, src_dir: Path | None = None) -> str:
    resolved = agents_dir.resolve()
    parts = set(resolved.parts)

    if src_dir and resolved == (src_dir / "agents").resolve():
        return "claude"
    if "copilot" in parts:
        return "copilot"
    if "opencode" in parts:
        return "opencode"
    if "claude" in parts:
        return "claude"
    if "pi" in parts:
        return "pi"
    return "claude"


def has_registry(repo_root: Path) -> bool:
    return (repo_root / "src" / "config" / "models.yaml").exists()
