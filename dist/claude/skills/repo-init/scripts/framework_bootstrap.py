# -*- coding: utf-8 -*-
"""
framework_bootstrap.py — Phase 5: Copy core agents and skills from framework.

Detects installed agentic-engineers framework location and copies:
- Core agent definitions (engineer.md, senior-engineer.md, etc.)
- Essential skills (usage-tracking/)
- Model config (models.yaml)

Author: Senior Engineer
"""

from __future__ import annotations

import importlib
import os
import shutil
from pathlib import Path
from typing import List, Optional

_CORE_AGENTS = [
    "engineer.md",
    "senior-engineer.md",
    "lead-engineer.md",
    "quality-engineer.md",
    "security-engineer.md",
    "principal-engineer.md",
    "orchestrator.md",
]

_ESSENTIAL_SKILLS = [
    "usage-tracking",
]

_CONFIG_FILES = [
    ("src/config/models.yaml", ".agentic-engineers/models.yaml"),
]


def framework_bootstrap(cfg, dry_run: bool = False) -> List[Path]:
    """
    Phase 5: Copy framework core artifacts to target repo.

    Returns:
        List of Paths created.
    """
    framework_root = _find_framework_root()
    created: List[Path] = []

    if framework_root is None:
        # Non-fatal: emit a warning and return empty
        # Warning is added to result in the main orchestrator
        return []

    # Copy agent definitions
    agents_src = framework_root / "src" / "agents"
    agents_dst = cfg.repo_root / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    for agent_file in _CORE_AGENTS:
        src = agents_src / agent_file
        dst = agents_dst / agent_file
        if src.exists() and not dst.exists() and not dry_run:
            shutil.copy2(str(src), str(dst))
            created.append(dst)

    # Copy essential skills
    for skill_name in _ESSENTIAL_SKILLS:
        skill_src = framework_root / "src" / "skills" / skill_name
        skill_dst = cfg.repo_root / "skills" / skill_name
        if skill_src.exists() and not skill_dst.exists() and not dry_run:
            shutil.copytree(str(skill_src), str(skill_dst))
            created.append(skill_dst)

    # Copy config files
    for rel_src, rel_dst in _CONFIG_FILES:
        src = framework_root / rel_src
        dst = cfg.repo_root / rel_dst
        if src.exists() and not dst.exists() and not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            created.append(dst)

    # Write .agentic-engineers/config.yaml
    config_path = cfg.repo_root / ".agentic-engineers" / "config.yaml"
    if not config_path.exists() and not dry_run:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(_config_yaml(cfg), encoding="utf-8")
        created.append(config_path)

    return created


def _find_framework_root() -> Optional[Path]:
    """
    Detect installed agentic-engineers framework.

    Resolution order:
    1. AGENTIC_ENGINEERS_HOME env var
    2. ~/.agentic-engineers/
    3. ../agentic-engineers/ (adjacent repo)
    4. pip package agentic_engineers

    Returns None if not found.
    """
    # 1. Environment variable
    env_home = os.environ.get("AGENTIC_ENGINEERS_HOME", "")
    if env_home:
        path = Path(env_home).resolve()
        if _is_valid_framework(path):
            return path

    # 2. Global install at ~/.agentic-engineers/
    global_path = Path.home() / ".agentic-engineers"
    if _is_valid_framework(global_path):
        return global_path

    # 3. Adjacent repository
    # Walk up from this file's location to find the framework
    this_file = Path(__file__).resolve()
    for parent in this_file.parents:
        if parent.name == "agentic-engineers" and _is_valid_framework(parent):
            return parent
        # Check sibling
        sibling = parent.parent / "agentic-engineers"
        if sibling.exists() and _is_valid_framework(sibling):
            return sibling

    # 4. pip package
    try:
        spec = importlib.util.find_spec("agentic_engineers")
        if spec and spec.origin:
            pkg_path = Path(spec.origin).parent.parent
            if _is_valid_framework(pkg_path):
                return pkg_path
    except Exception:
        pass

    return None


def _is_valid_framework(path: Path) -> bool:
    """Check that path looks like a valid agentic-engineers installation."""
    return (
        path.is_dir()
        and (path / "src" / "agents").is_dir()
        and (path / "src" / "skills").is_dir()
    )


def _config_yaml(cfg) -> str:
    """Generate .agentic-engineers/config.yaml content."""
    import datetime

    harness = cfg.model_harness

    # Model assignments by harness
    models = {
        "claude": {
            "engineer": "claude-haiku-4.5",
            "senior-engineer": "claude-sonnet-4.6",
            "lead-engineer": "claude-sonnet-4.6",
            "quality-engineer": "claude-sonnet-4.6",
            "security-engineer": "claude-opus-4.7",
            "principal-engineer": "claude-opus-4.7",
            "orchestrator": "claude-sonnet-4.6",
        },
        "gpt5": {
            "engineer": "gpt-4o-mini",
            "senior-engineer": "gpt-4o",
            "lead-engineer": "gpt-4o",
            "quality-engineer": "gpt-4o",
            "security-engineer": "gpt-4",
            "principal-engineer": "gpt-4",
            "orchestrator": "gpt-4o",
        },
        "local": {
            "engineer": "ollama/llama3.2",
            "senior-engineer": "ollama/llama3.2",
            "lead-engineer": "ollama/llama3.2",
            "quality-engineer": "ollama/llama3.2",
            "security-engineer": "ollama/llama3.1:70b",
            "principal-engineer": "ollama/llama3.1:70b",
            "orchestrator": "ollama/llama3.2",
        },
    }.get(harness, {
        "engineer": "claude-haiku-4.5",
        "senior-engineer": "claude-sonnet-4.6",
        "lead-engineer": "claude-sonnet-4.6",
        "quality-engineer": "claude-sonnet-4.6",
        "security-engineer": "claude-opus-4.7",
        "principal-engineer": "claude-opus-4.7",
        "orchestrator": "claude-sonnet-4.6",
    })

    quality_threshold = 70 if harness == "local" else 85

    now = datetime.datetime.utcnow().isoformat() + "Z"

    agent_lines = []
    for role, model in models.items():
        agent_lines.append(
            f"  {role}:\n"
            f"    model: {model}\n"
            f"    effort: {'high' if 'principal' in role else 'medium' if 'senior' in role or 'lead' in role or 'quality' in role or 'security' in role else 'low'}\n"
            f"    enabled: true"
        )

    return f"""# .agentic-engineers/config.yaml
# Generated by repo-init v1.0 — do not edit manually
# To change settings, use the spec-management skill
schema_version: "1.0"
framework_version: "{cfg.framework_version}"
project_name: "{cfg.project_name}"
model_harness: "{harness}"
initialized_at: "{now}"
initialized_by: "repo-init v1.0"

agents:
{chr(10).join(agent_lines)}

quality_gate:
  min_coverage: {quality_threshold}
  require_handback: true
  require_spec_compliance: {'false' if harness == 'local' else 'true'}
  require_code_review: false

queue:
  location: "~/.agentic-engineers/"
  session_partitioned: true
"""
