# -*- coding: utf-8 -*-
"""
generate_spec.py — Phase 2: SPEC.md generation for repo-init skill.

Renders the project-specific SPEC.md from assets/spec-template.md with
values derived from Phase 1 analysis and Phase 6 compatibility results.

Author: Senior Engineer
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import List, Optional

# Asset template is relative to this file's location
_SKILL_ROOT = Path(__file__).parent.parent
_SPEC_TEMPLATE = _SKILL_ROOT / "assets" / "spec-template.md"


def generate_spec(cfg, analysis, dry_run: bool = False) -> List[Path]:
    """
    Phase 2: Render and write docs/SPEC.md.

    Args:
        cfg: RepoInitConfig
        analysis: AnalysisResult from Phase 1
        dry_run: If True, validate template but don't write.

    Returns:
        List of Path objects written (empty if dry_run or file already exists).
    """
    spec_path = cfg.repo_root / "docs" / "SPEC.md"

    if spec_path.exists() and not cfg.force_reinit:
        return []  # Idempotent — don't overwrite existing SPEC.md

    template = _SPEC_TEMPLATE.read_text(encoding="utf-8")
    rendered = _render_template(template, cfg, analysis)

    if dry_run:
        return []

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(rendered, encoding="utf-8")
    return [spec_path]


def _render_template(template: str, cfg, analysis) -> str:
    """Substitute all {placeholders} in the template."""
    today = datetime.date.today().isoformat()

    # Size-aware quality threshold
    quality_threshold = _quality_threshold(cfg.model_harness, analysis.size_class)

    # Tool icons (populated with "✅" by default — updated by Phase 6 if available)
    tool_icons = {
        "git": "✅", "python3": "✅", "bash": "✅", "jq": "✅",
    }

    substitutions = {
        "project_name": cfg.project_name,
        "project_description": cfg.project_description or f"The {cfg.project_name} project.",
        "primary_language": analysis.primary_language,
        "package_manager": analysis.package_manager,
        "test_framework": analysis.test_framework,
        "ci_provider": analysis.ci_provider,
        "license": analysis.license,
        "git_remote": analysis.git_remote or "(not set)",
        "framework_version": cfg.framework_version,
        "model_harness": cfg.model_harness,
        "date": today,
        "engineer_model": _model_for("engineer", cfg.model_harness),
        "senior_model": _model_for("senior-engineer", cfg.model_harness),
        "lead_model": _model_for("lead-engineer", cfg.model_harness),
        "principal_model": _model_for("principal-engineer", cfg.model_harness),
        "quality_threshold": str(quality_threshold),
        "tool_git": tool_icons["git"],
        "tool_python": tool_icons["python3"],
        "tool_bash": tool_icons["bash"],
        "tool_jq": tool_icons["jq"],
    }

    result = template
    for key, value in substitutions.items():
        result = result.replace("{" + key + "}", str(value))
    return result


_HARNESS_MODELS: dict[str, dict[str, str]] = {
    "claude": {
        "engineer":           "claude-haiku-4.5",
        "senior-engineer":    "claude-sonnet-4.6",
        "lead-engineer":      "claude-sonnet-4.6",
        "quality-engineer":   "claude-sonnet-4.6",
        "security-engineer":  "claude-opus-4.7",
        "principal-engineer": "claude-opus-4.7",
        "orchestrator":       "claude-sonnet-4.6",
    },
    "gpt5": {
        "engineer":           "gpt-4o-mini",
        "senior-engineer":    "gpt-4o",
        "lead-engineer":      "gpt-4o",
        "quality-engineer":   "gpt-4o",
        "security-engineer":  "gpt-4",
        "principal-engineer": "gpt-4",
        "orchestrator":       "gpt-4o",
    },
    "local": {
        "engineer":           "ollama/llama3.2",
        "senior-engineer":    "ollama/llama3.2",
        "lead-engineer":      "ollama/llama3.2",
        "quality-engineer":   "ollama/llama3.2",
        "security-engineer":  "ollama/llama3.1:70b",
        "principal-engineer": "ollama/llama3.1:70b",
        "orchestrator":       "ollama/llama3.2",
    },
    "copilot": {
        "engineer":           "claude-haiku-4.5",
        "senior-engineer":    "claude-sonnet-4.6",
        "lead-engineer":      "claude-sonnet-4.6",
        "quality-engineer":   "claude-sonnet-4.6",
        "security-engineer":  "claude-opus-4.7",
        "principal-engineer": "claude-opus-4.7",
        "orchestrator":       "claude-sonnet-4.6",
    },
}


def _model_for(role: str, harness: str) -> str:
    return _HARNESS_MODELS.get(harness, _HARNESS_MODELS["claude"]).get(
        role, "claude-haiku-4.5"
    )


def _quality_threshold(harness: str, size_class: str) -> int:
    matrix = {
        "claude":  {"small": 85, "medium": 85, "large": 70},
        "gpt5":    {"small": 85, "medium": 85, "large": 70},
        "local":   {"small": 70, "medium": 70, "large": 60},
        "copilot": {"small": 85, "medium": 85, "large": 70},
    }
    return matrix.get(harness, matrix["claude"]).get(size_class, 85)
