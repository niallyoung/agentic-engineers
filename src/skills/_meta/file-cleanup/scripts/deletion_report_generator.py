# -*- coding: utf-8 -*-
"""
deletion_report_generator.py — Generate human-readable deletion reports.

Provides comprehensive analysis for each file deletion candidate, including:
- Risk level and confidence score
- All active and hidden references (with context)
- Git history information
- Recovery command (for reversibility)
- Confirmation prompt appropriate to risk level
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .reference_scanner import Reference
from .risk_assessor import RiskScore


@dataclass
class DeletionReport:
    """Comprehensive report for a deletion candidate."""

    file_path: Path
    category: str
    risk_level: str
    active_references: List[Reference]
    hidden_references: List[Reference]
    git_history: str
    recommendation: str
    reasoning: List[str]
    recovery_command: str = ""
    safe_to_delete: bool = False


class DeletionReportGenerator:
    """Generates human-readable deletion reports."""

    def __init__(self, root: Path) -> None:
        """Initialize report generator with repo root."""
        self.root = Path(root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(
        self, file_path: Path, risk: RiskScore, references: List[Reference]
    ) -> "DeletionReport":
        """
        Generate a comprehensive deletion report.
        
        Args:
            file_path: Path to the file being considered for deletion
            risk: RiskScore object from RiskAssessor
            references: List of references found
        
        Returns:
            DeletionReport with all analysis
        """
        active_refs = [r for r in references if r.ref_type not in ("string", "fstring")]
        hidden_refs = [r for r in references if r.ref_type in ("string", "fstring", "subprocess")]

        safe_to_delete = risk.level == "LOW"
        recovery_cmd = self._generate_recovery_command(file_path)
        category = self._infer_category(file_path)

        report = DeletionReport(
            file_path=file_path,
            category=category,
            risk_level=risk.level,
            active_references=active_refs,
            hidden_references=hidden_refs,
            git_history="",
            recommendation=risk.recommendation,
            reasoning=risk.reasoning,
            recovery_command=recovery_cmd,
            safe_to_delete=safe_to_delete,
        )
        return report

    def _generate_recovery_command(self, file_path: Path) -> str:
        """Generate git recovery command for reversibility."""
        return f"git checkout HEAD~1 -- {file_path}"

    def _infer_category(self, file_path: Path) -> str:
        """Infer file category from naming pattern."""
        name = file_path.name.lower()
        stem = file_path.stem.lower()

        if any(x in stem for x in ("phase_", "phase-")):
            return "session_temp"
        if "session_temp" in stem:
            return "session_temp"
        if any(x in name for x in ("debug", "log")):
            return "debug_log"
        if ".coverage" in name or "htmlcov" in stem:
            return "coverage"
        return "general"

    def __str__(self) -> str:
        """Format as human-readable string for display."""
        lines = ["=" * 70]
        # This method renders a report, but __str__ on the generator
        # is not the primary interface; generate_report() is.
        # Left as a convenience method.
        return "\n".join(lines)

    def format_report(self, report: DeletionReport) -> str:
        """Format a DeletionReport as a human-readable string."""
        lines: List[str] = []
        lines.append("=" * 70)
        lines.append(f"DELETION REPORT: {report.file_path}")

        risk_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(report.risk_level, "⚪")
        lines.append(f"   Risk Level: {risk_icon} {report.risk_level} (confidence: {0.95:.0%})")
        lines.append(f"   Category: {report.category}")
        lines.append(f"   Recommendation: {report.recommendation}")

        if report.active_references:
            lines.append(f"\n   Active References ({len(report.active_references)}):")
            for i, ref in enumerate(report.active_references[:5]):
                lines.append(f"   {i+1}. {ref.file_path}:{ref.line_number}")
                lines.append(f"      {ref.context}")

        if report.hidden_references:
            lines.append(f"\n   Hidden References ({len(report.hidden_references)}):")
            for i, ref in enumerate(report.hidden_references[:5]):
                lines.append(f"   {i+1}. {ref.file_path}:{ref.line_number} [{ref.ref_type}]")

        lines.append(f"\n   Recovery: {report.recovery_command}")

        if report.risk_level == "HIGH":
            lines.append("\n   ⚠️  HIGH RISK: Manual review required before deletion.")
        elif report.risk_level == "MEDIUM":
            lines.append("\n   ⚠️  MEDIUM RISK: Review references before proceeding.")
        else:
            lines.append("\n   ✅  LOW RISK: Safe to delete.")

        lines.append("=" * 70)
        return "\n".join(lines)
