# -*- coding: utf-8 -*-
"""Utility scorer: Score scripts for valuableness (0-10)."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from . import script_analyzer  # noqa: F401 – available for import  # type: ignore[attr-defined]
from .script_analyzer import ScriptMetadata


@dataclass
class UtilityScore:
    """Result of scoring a script."""

    score: float
    category: str  # HIGH_VALUE | MEDIUM | LOW | DEAD
    reasons: List[str] = field(default_factory=list)


class UtilityScorer:
    """Score scripts for valuableness (0-10)."""

    # Category thresholds
    _HIGH_VALUE_THRESHOLD = 7.0
    _MEDIUM_THRESHOLD = 4.0
    # Development markers that fatally cap the score (matched case-insensitively)
    _DEV_MARKERS = {"debug", "test", "_test", "experimental"}

    def __init__(self, repo_root: Path) -> None:
        """Initialize scorer with repository root."""
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(self, metadata: ScriptMetadata) -> Tuple[float, List[str], List[str]]:
        """Score script and return (score, reasons, warnings).

        Returns:
            (score, reasons, warnings)
        """
        reasons: List[str] = []
        warnings: List[str] = []

        quality, quality_reasons = self._quality_signals(metadata)
        maturity, maturity_reasons = self._maturity_signals(metadata)
        relevance, relevance_reasons = self._relevance_signals(metadata)
        deps, deps_reasons = self._dependency_signals(metadata)

        reasons.extend(quality_reasons)
        reasons.extend(maturity_reasons)
        reasons.extend(relevance_reasons)
        reasons.extend(deps_reasons)

        # Check for fatal development markers (case-insensitive)
        is_dev = any(marker in metadata.name.lower() or marker in metadata.docstring.lower()
                     for marker in self._DEV_MARKERS)
        if is_dev:
            warnings.append("Development marker found — score capped at 3")
            final_score = min(3.0, quality + maturity + relevance + deps)
        else:
            final_score = quality + maturity + relevance + deps

        # Clamp to [0, 10]
        final_score = max(0.0, min(10.0, final_score))

        # Categorize
        if final_score >= self._HIGH_VALUE_THRESHOLD:
            category = "HIGH_VALUE"
        elif final_score >= self._MEDIUM_THRESHOLD:
            category = "MEDIUM"
        elif final_score > 0.0:
            category = "LOW"
        else:
            category = "DEAD"

        return final_score, reasons, warnings

    # ------------------------------------------------------------------
    # Scoring sub-dimensions
    # ------------------------------------------------------------------

    def _quality_signals(self, metadata: ScriptMetadata) -> Tuple[float, List[str]]:
        """Docstring, type hints, error handling."""
        score = 0.0
        reasons: List[str] = []

        docstring_len = len(metadata.docstring)
        if docstring_len > 50:
            score += 2.0
            reasons.append("Comprehensive docstring (+2)")
        elif docstring_len > 0:
            score += 1.0
            reasons.append("Has docstring (+1)")

        if metadata.cli_signature.get("has_type_hints"):
            score += 0.5
            reasons.append("Type hints (+0.5)")

        if metadata.cli_signature.get("has_error_handling"):
            score += 0.5
            reasons.append("Error handling (+0.5)")

        return score, reasons

    def _maturity_signals(self, metadata: ScriptMetadata) -> Tuple[float, List[str]]:
        """Filename clarity, LOC, dev markers."""
        score = 0.0
        reasons: List[str] = []

        dev_markers = ["debug", "test", "_test", "experimental"]
        is_dev = any(marker in metadata.name.lower() or marker in metadata.docstring.lower()
                     for marker in dev_markers)

        if not is_dev:
            score += 1.5
            reasons.append("Clean naming, no dev markers (+1.5)")

        # LOC bonus: prefer small focused scripts
        if 0 < metadata.lines_of_code < 200:
            score += 1.0
            reasons.append("Small focused script (+1)")
        elif metadata.lines_of_code >= 1000:
            score -= 0.5
            reasons.append("Very large script (-0.5)")

        return score, reasons

    def _relevance_signals(self, metadata: ScriptMetadata) -> Tuple[float, List[str]]:
        """Referenced in docs, core domains."""
        score = 0.0
        reasons: List[str] = []

        # Check CONTRIBUTING.md reference
        contributing_path = self.repo_root / "CONTRIBUTING.md"
        doc_referenced = False
        if contributing_path.exists():
            try:
                content = contributing_path.read_text(encoding="utf-8", errors="ignore")
                if metadata.name in content or metadata.path.name in content:
                    score += 1.5
                    reasons.append("Referenced in CONTRIBUTING.md (+1.5)")
                    doc_referenced = True
            except OSError:
                pass

        # Core domain match
        core_domains = ["validate", "render", "version", "deploy", "test", "lint", "build"]
        has_core_domain = any(domain in metadata.name.lower() for domain in core_domains)
        if has_core_domain:
            score += 1.0
            reasons.append("Core workflow domain (+1)")

        # Has CLI interface
        has_cli = metadata.cli_signature.get("has_cli", False)
        if has_cli:
            score += 0.5
            reasons.append("CLI interface (+0.5)")

        return score, reasons

    def _dependency_signals(self, metadata: ScriptMetadata) -> Tuple[float, List[str]]:
        """Dependency counts."""
        score = 0.0
        reasons: List[str] = []

        dep_count = len(metadata.dependencies)
        if dep_count <= 2:
            score += 0.5
            reasons.append("Minimal dependencies <=2 (+0.5)")
        elif dep_count > 10:
            score -= 0.5
            reasons.append("High external deps >10 (-0.5)")

        return score, reasons
