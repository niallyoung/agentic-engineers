# -*- coding: utf-8 -*-
"""File sync orchestrator: Main entry point for script analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .script_analyzer import ScriptAnalyzer, ScriptMetadata
from .utility_scorer import UtilityScorer, UtilityScore
from .reference_detector import ReferenceDetector, Reference
from .integration_suggester import IntegrationSuggester, IntegrationSuggestion


@dataclass
class ScriptResult:
    """Analysis result for a single script."""

    metadata: ScriptMetadata
    utility_score: UtilityScore
    references: List[Reference] = field(default_factory=list)
    integration_suggestions: List[IntegrationSuggestion] = field(default_factory=list)

    @property
    def is_integrated(self) -> bool:
        return len(self.references) > 0


@dataclass
class SyncReport:
    """Complete report from file-sync analysis."""

    timestamp: str
    scripts_analyzed: int
    high_value_unintegrated: List[ScriptResult] = field(default_factory=list)
    high_value_integrated: List[ScriptResult] = field(default_factory=list)
    medium_value_unintegrated: List[ScriptResult] = field(default_factory=list)
    medium_value_integrated: List[ScriptResult] = field(default_factory=list)
    dead_code: List[ScriptResult] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class FileSyncOrchestrator:
    """Orchestrate complete file-sync analysis."""

    REPORT_FILENAME = "SYNC_REPORT.md"

    def __init__(self, repo_root: Path) -> None:
        """Initialize orchestrator with repository root."""
        self.repo_root = Path(repo_root)
        self._analyzer = ScriptAnalyzer(self.repo_root)
        self._scorer = UtilityScorer(self.repo_root)
        self._detector = ReferenceDetector(self.repo_root)
        self._suggester = IntegrationSuggester(self.repo_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_analysis(self) -> SyncReport:
        """Run complete analysis and return report."""
        timestamp = datetime.utcnow().isoformat()
        script_paths = self._analyzer.discover_scripts()

        results: List[ScriptResult] = []
        for script_path in script_paths:
            metadata = self._analyzer.analyze(script_path)
            score_val, reasons, warnings = self._scorer.score(metadata)
            score_int = int(round(score_val))
            category = "LOW"
            if score_val >= 7.0:
                category = "HIGH_VALUE"
            elif score_val >= 4.0:
                category = "MEDIUM"
            elif score_val <= 0.0:
                category = "DEAD"

            utility_score = UtilityScore(
                score=score_val,
                category=category,
                reasons=reasons,
            )

            references = self._detector.find_references(metadata.path.name)
            suggestions = []
            if not references or category in ("HIGH_VALUE", "MEDIUM"):
                suggestions = self._suggester.suggest_integration_points(metadata, references)

            results.append(ScriptResult(
                metadata=metadata,
                utility_score=utility_score,
                references=references,
                integration_suggestions=suggestions,
            ))

        # Segment results
        high_value_unintegrated = [r for r in results if r.utility_score.category == "HIGH_VALUE" and not r.is_integrated]
        high_value_integrated   = [r for r in results if r.utility_score.category == "HIGH_VALUE" and r.is_integrated]
        medium_value_unintegrated = [r for r in results if r.utility_score.category == "MEDIUM" and not r.is_integrated]
        medium_value_integrated   = [r for r in results if r.utility_score.category == "MEDIUM" and r.is_integrated]
        dead_code = [r for r in results if r.utility_score.category in ("LOW", "DEAD")]

        summary = (
            f"Analyzed {len(results)} scripts: "
            f"{len(high_value_integrated)} high-value integrated, "
            f"{len(high_value_unintegrated)} high-value unintegrated, "
            f"{len(medium_value_integrated)} medium integrated, "
            f"{len(medium_value_unintegrated)} medium unintegrated, "
            f"{len(dead_code)} low/dead."
        )

        recommendations: List[str] = []
        if high_value_unintegrated:
            recommendations.append(
                f"Integrate {len(high_value_unintegrated)} high-value scripts (priority action)."
            )
        if dead_code:
            recommendations.append(
                f"Clean up {len(dead_code)} low/dead scripts."
            )

        return SyncReport(
            timestamp=timestamp,
            scripts_analyzed=len(results),
            high_value_unintegrated=high_value_unintegrated,
            high_value_integrated=high_value_integrated,
            medium_value_unintegrated=medium_value_unintegrated,
            medium_value_integrated=medium_value_integrated,
            dead_code=dead_code,
            summary=summary,
            recommendations=recommendations,
        )

    def output_report(self, report: SyncReport, output_path: Optional[Path] = None) -> str:
        """Generate markdown report."""
        lines: List[str] = []
        lines.append("# File-Sync Report")
        lines.append(f"\nGenerated: {report.timestamp}")
        lines.append(f"\n{report.summary}")

        if report.recommendations:
            lines.append("\n## Recommendations\n")
            for rec in report.recommendations:
                lines.append(f"- {rec}")

        if report.high_value_unintegrated:
            lines.append("\n## High-Value Unintegrated Scripts\n")
            for r in report.high_value_unintegrated:
                metadata = r.metadata
                score = r.utility_score
                lines.append(f"### {metadata.path.name}")
                lines.append(f"- **Score**: {score.score:.1f}/10 ({score.category})")
                lines.append(f"- **Purpose**: {metadata.purpose}")
                if r.integration_suggestions:
                    lines.append("- **Suggestions**:")
                    for sugg in r.integration_suggestions:
                        lines.append(f"  - {sugg.target}: {sugg.action} ({sugg.effort_minutes}min)")

        if report.high_value_integrated:
            lines.append("\n## High-Value Integrated Scripts\n")
            for r in report.high_value_integrated:
                lines.append(f"### {r.metadata.path.name}")
                lines.append(f"- **Score**: {r.utility_score.score:.1f}/10 ✅")

        if report.medium_value_unintegrated or report.medium_value_integrated:
            lines.append("\n## Medium-Value Scripts\n")
            for r in report.medium_value_unintegrated + report.medium_value_integrated:
                tag = "✅" if r.is_integrated else "⚠️"
                lines.append(f"- {r.metadata.path.name} ({r.utility_score.score:.1f}/10) {tag}")

        if report.dead_code:
            lines.append("\n## Low-Value / Cleanup Candidates\n")
            for r in report.dead_code:
                lines.append(f"- {r.metadata.path.name} ({r.utility_score.score:.1f}/10) 🗑️")

        content = "\n".join(lines) + "\n"

        if output_path is not None:
            output_file = Path(output_path)
            output_file.write_text(content, encoding="utf-8")

        return content


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Analyze repository scripts")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--output", type=Path, default=None, help="Output path for report")
    args = parser.parse_args()

    orchestrator = FileSyncOrchestrator(repo_root=args.root)
    report = orchestrator.run_analysis()

    output_path = args.output or (args.root / FileSyncOrchestrator.REPORT_FILENAME)
    orchestrator.output_report(report, output_path)
    print(f"Report written to {output_path}")
    print(report.summary)


if __name__ == "__main__":
    main()
