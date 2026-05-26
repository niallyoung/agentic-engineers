# -*- coding: utf-8 -*-
"""Integration suggester: Recommend integration points."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .script_analyzer import ScriptMetadata
from .reference_detector import Reference


@dataclass
class IntegrationSuggestion:
    """Suggestion for integrating a script."""

    target: str          # Where to add the integration (e.g., "Makefile", "CI")
    action: str          # What to do (e.g., "add-target", "add-step")
    reasoning: str       # Why this integration makes sense
    effort_minutes: int = 15
    risk: str = "low"    # low | medium | high
    example: str = ""    # Concrete code snippet


class IntegrationSuggester:
    """Suggest integration points for scripts."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize suggester with repository root."""
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def suggest_integration_points(
        self, script: ScriptMetadata, references: List[Reference]
    ) -> List[IntegrationSuggestion]:
        """Suggest integration points for a script."""
        suggestions: List[IntegrationSuggestion] = []
        already_in = {ref.file_path.name for ref in references}

        has_cli = script.cli_signature.get("has_argparse") or script.cli_signature.get("has_click")
        is_validator = any(keyword in script.name.lower()
                           for keyword in ["validate", "check", "verify", "lint"])

        # Makefile suggestion for CLI scripts
        if has_cli and "Makefile" not in already_in:
            suggestions.append(IntegrationSuggestion(
                target="Makefile",
                action="add-target",
                reasoning=f"`{script.name}` has a CLI interface — add a Makefile target for easy invocation.",
                effort_minutes=10,
                risk="low",
                example=f"{script.name.replace('.py', '')}:\n\tpython scripts/{script.path.name}",
            ))

        # CI suggestion for validation scripts
        if is_validator:
            suggestions.append(IntegrationSuggestion(
                target=".github/workflows/ci.yml",
                action="add-step",
                reasoning=f"`{script.name}` validates outputs — run it in CI to catch regressions.",
                effort_minutes=20,
                risk="low",
                example=f"- name: Run {script.name}\n  run: python scripts/{script.path.name}",
            ))

        # Python import suggestion for library-style scripts (entry_points but no CLI)
        if script.entry_points and not has_cli:
            suggestions.append(IntegrationSuggestion(
                target="Python module",
                action="add-import",
                reasoning=f"`{script.name}` exposes public functions — import it where needed.",
                effort_minutes=15,
                risk="medium",
                example=f"from scripts.{script.name.replace('.py', '')} import {', '.join(script.entry_points[:2])}",
            ))

        # Documentation suggestion for all unintegrated scripts
        suggestions.append(IntegrationSuggestion(
            target="CONTRIBUTING.md",
            action="add-documentation",
            reasoning=f"Document `{script.name}` in CONTRIBUTING.md so team members know it exists.",
            effort_minutes=5,
            risk="low",
            example=f"- `scripts/{script.path.name}` — {script.purpose}",
        ))

        return suggestions
