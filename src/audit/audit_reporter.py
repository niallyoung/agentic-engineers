"""Generates comprehensive audit reports from skill scorecards."""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from src.audit.skills_auditor import SkillScorecard, SkillsAuditor


class AuditReporter:
    """Generates audit reports from skill scorecards."""

    def __init__(self, auditor: SkillsAuditor) -> None:
        """Initialize reporter.
        
        Args:
            auditor: Completed SkillsAuditor instance
        """
        self.auditor = auditor
        self.scorecards = auditor.scorecards

    def generate_markdown_report(self, output_path: Path) -> str:
        """Generate comprehensive Markdown audit report.
        
        Args:
            output_path: Path where report will be written
            
        Returns:
            Generated report content
        """
        summary = self.auditor.get_summary_statistics()
        lines = []

        # Header
        lines.append("# Skills Audit Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Skills Audited:** {summary.get('total_skills', 0)}")
        lines.append("")

        # Executive Summary
        lines.extend(self._generate_executive_summary(summary))
        lines.append("")

        # Category Breakdown
        lines.extend(self._generate_category_breakdown(summary))
        lines.append("")

        # Dimension Analysis
        lines.extend(self._generate_dimension_analysis(summary))
        lines.append("")

        # Skills Needing Improvement
        lines.extend(self._generate_improvement_needed(summary))
        lines.append("")

        # Individual Skill Scorecards
        lines.extend(self._generate_scorecards())
        lines.append("")

        # Redundancy Clusters (cross-skill overlap analysis)
        lines.extend(self._generate_redundancy_clusters())
        lines.append("")

        # _Meta Skills Audit
        lines.extend(self._generate_meta_skills_audit(output_path))
        lines.append("")

        # Recommendations
        lines.extend(self._generate_recommendations())
        lines.append("")

        # Audit Methodology
        lines.extend(self._generate_methodology())
        
        report_content = "\n".join(lines)
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        return report_content

    def _generate_executive_summary(self, summary: Dict) -> List[str]:
        """Generate executive summary section.
        
        Args:
            summary: Summary statistics
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Executive Summary")
        lines.append("")
        
        avg_score = summary.get('avg_score', 0)
        min_score = summary.get('min_score', 0)
        max_score = summary.get('max_score', 0)
        
        # Quality assessment
        if avg_score >= 75:
            quality = "**Excellent** - Framework is well-maintained"
        elif avg_score >= 65:
            quality = "**Good** - Framework is stable with some improvements needed"
        elif avg_score >= 50:
            quality = "**Fair** - Framework needs attention to quality"
        else:
            quality = "**Poor** - Framework requires significant improvements"
        
        lines.append(f"**Overall Framework Quality:** {quality}")
        lines.append("")
        
        lines.append("### Key Metrics")
        lines.append(f"- **Average Skill Score:** {avg_score:.1f}/100")
        lines.append(f"- **Highest Scoring Skill:** {max_score:.1f}/100")
        lines.append(f"- **Lowest Scoring Skill:** {min_score:.1f}/100")
        lines.append("")
        
        return lines

    def _generate_category_breakdown(self, summary: Dict) -> List[str]:
        """Generate category breakdown section.
        
        Args:
            summary: Summary statistics
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Category Breakdown")
        lines.append("")
        
        categories = summary.get('category_breakdown', {})
        total = sum(categories.values())
        
        for category in ["CORE", "UTILITY", "EXPERIMENTAL"]:
            count = categories.get(category, 0)
            if total > 0:
                pct = (count / total) * 100
            else:
                pct = 0
            
            lines.append(f"### {category}")
            lines.append(f"**Count:** {count} ({pct:.1f}%)")
            
            # Skills in this category
            skills_in_category = [
                name for name, sc in self.scorecards.items()
                if sc.category_assigned == category
            ]
            
            if skills_in_category:
                lines.append("**Skills:**")
                for skill in sorted(skills_in_category):
                    sc = self.scorecards[skill]
                    lines.append(f"- {skill} ({sc.overall_score():.1f})")
            
            lines.append("")
        
        return lines

    def _generate_dimension_analysis(self, summary: Dict) -> List[str]:
        """Generate dimension analysis section.
        
        Args:
            summary: Summary statistics
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Dimension Analysis")
        lines.append("")
        
        dim_avgs = summary.get('dimension_averages', {})
        
        dimension_descriptions = {
            "value": "Strategic importance and priority",
            "usage": "Integration and utilization frequency",
            "maintenance": "Code quality and maintainability",
            "tests": "Test coverage and quality",
            "docs": "Documentation completeness",
            "quality": "Overall code quality",
        }
        
        for dim in ["value", "usage", "maintenance", "tests", "docs", "quality"]:
            avg = dim_avgs.get(dim, 0)
            
            # Assess dimension
            if avg >= 7.5:
                assessment = "Excellent"
            elif avg >= 6.5:
                assessment = "Good"
            elif avg >= 5.0:
                assessment = "Fair"
            elif avg >= 3.5:
                assessment = "Poor"
            else:
                assessment = "Critical"
            
            desc = dimension_descriptions.get(dim, "")
            lines.append(f"### {dim.upper()}")
            lines.append(f"**Average Score:** {avg:.2f}/10")
            lines.append(f"**Assessment:** {assessment}")
            lines.append(f"**Description:** {desc}")
            
            # Find highest and lowest in this dimension
            all_dims = [(name, getattr(sc, dim).value) 
                       for name, sc in self.scorecards.items()]
            all_dims.sort(key=lambda x: x[1], reverse=True)
            
            if all_dims:
                lines.append(f"**Highest:** {all_dims[0][0]} ({all_dims[0][1]}/10)")
                lines.append(f"**Lowest:** {all_dims[-1][0]} ({all_dims[-1][1]}/10)")
            
            lines.append("")
        
        return lines

    def _generate_improvement_needed(self, summary: Dict) -> List[str]:
        """Generate skills needing improvement section.
        
        Args:
            summary: Summary statistics
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Skills Needing Improvement")
        lines.append("")
        
        needs_improvement = summary.get('skills_needing_improvement', [])
        
        if not needs_improvement:
            lines.append("✓ All skills are meeting quality standards (≥65/100)")
            return lines
        
        lines.append(f"**Count:** {len(needs_improvement)} skills")
        lines.append("")
        
        for skill in sorted(needs_improvement):
            sc = self.scorecards.get(skill)
            if sc:
                lines.append(f"### {skill}")
                lines.append(f"**Current Score:** {sc.overall_score():.1f}/100")
                lines.append(f"**Category:** {sc.category_assigned}")
                lines.append("")
                
                if sc.weaknesses:
                    lines.append("**Weaknesses:**")
                    for weakness in sc.weaknesses:
                        lines.append(f"- {weakness}")
                    lines.append("")
                
                if sc.recommendations:
                    lines.append("**Recommendations:**")
                    for rec in sc.recommendations:
                        lines.append(f"- {rec}")
                    lines.append("")
        
        return lines

    def _generate_scorecards(self) -> List[str]:
        """Generate detailed individual skill scorecards.
        
        Args:
            (none - uses self.scorecards)
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Individual Skill Scorecards")
        lines.append("")
        
        # Sort by overall score descending
        sorted_skills = sorted(
            self.scorecards.items(),
            key=lambda x: x[1].overall_score(),
            reverse=True
        )
        
        for skill_name, sc in sorted_skills:
            lines.append(f"### {skill_name}")
            lines.append("")
            
            # Score
            lines.append(f"**Overall Score:** {sc.overall_score():.1f}/100")
            lines.append(f"**Category:** {sc.category_assigned}")
            lines.append("")
            
            # Description
            if sc.description:
                lines.append(f"**Description:** {sc.description}")
                lines.append("")
            
            # Dimension Scores
            lines.append("**Dimension Scores:**")
            lines.append(f"| Dimension | Score |")
            lines.append(f"|-----------|-------|")
            lines.append(f"| Value | {sc.value.value}/10 |")
            lines.append(f"| Usage | {sc.usage.value}/10 |")
            lines.append(f"| Maintenance | {sc.maintenance.value}/10 |")
            lines.append(f"| Tests | {sc.tests.value}/10 |")
            lines.append(f"| Docs | {sc.docs.value}/10 |")
            lines.append(f"| Quality | {sc.quality.value}/10 |")
            lines.append("")
            
            # Metadata
            if sc.author or sc.role or sc.model or sc.effort:
                lines.append("**Metadata:**")
                if sc.author:
                    lines.append(f"- Author: {sc.author}")
                if sc.role:
                    lines.append(f"- Required Role: {sc.role}")
                if sc.model:
                    lines.append(f"- Model: {sc.model}")
                if sc.effort:
                    lines.append(f"- Effort: {sc.effort}")
                lines.append("")
            
            # Strengths
            if sc.strengths:
                lines.append("**Strengths:**")
                for strength in sc.strengths:
                    lines.append(f"- {strength}")
                lines.append("")
            
            # Weaknesses
            if sc.weaknesses:
                lines.append("**Weaknesses:**")
                for weakness in sc.weaknesses:
                    lines.append(f"- {weakness}")
                lines.append("")
            
            # Recommendations
            if sc.recommendations:
                lines.append("**Recommendations:**")
                for rec in sc.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return lines

    def _generate_redundancy_clusters(self) -> List[str]:
        """Identify skill clusters with overlapping responsibilities.

        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Redundancy Clusters")
        lines.append("")
        lines.append(
            "Skills with overlapping purposes that are candidates for "
            "consolidation, deprecation, or clearer separation of concerns."
        )
        lines.append("")

        # Static cluster definitions derived from framework inventory analysis.
        # These reflect known overlap areas; update as the skill roster evolves.
        clusters = [
            {
                "name": "Cost / Token Analytics",
                "skills": ["usage-tracking", "cost-aggregation"],
                "overlap": (
                    "`cost-aggregation` handles consolidated cost tracking across providers; "
                    "`usage-tracking` handles real-time session-scoped capture. "
                    "(Archived 2026-08-08: `tokenadvisor` and `metrics-etl` have been consolidated.)"
                ),
                "recommendation": (
                    "Retain `cost-aggregation` as primary consolidation tool. "
                    "`usage-tracking` provides session-level instrumentation. "
                    "No further consolidation needed."
                ),
            },
            {
                "name": "Queue Operations",
                "skills": ["queue-management", "queue-query", "queue-monitor", "queue-todo-sync"],
                "overlap": (
                    "`queue-management` (131 tests) covers atomic operations and full "
                    "lifecycle. `queue-query`, `queue-monitor`, and `queue-todo-sync` "
                    "each address a narrow slice already reachable via `queue-management`."
                ),
                "recommendation": (
                    "Evaluate whether `queue-query` and `queue-monitor` can be "
                    "thin wrappers or sub-commands of `queue-management` rather "
                    "than independent skills."
                ),
            },
            {
                "name": "Protocol / Spec Validation",
                "skills": ["protocol-validator", "spec-validator", "consistency-checker"],
                "overlap": (
                    "All three validate aspects of the DELEGATE/HANDBACK protocol and "
                    "SPEC.md compliance. `consistency-checker` (21 tests) performs "
                    "cross-queue validation; `protocol-validator` (55 tests) validates "
                    "individual messages; `spec-validator` (3 tests) validates SPEC.md "
                    "structure."
                ),
                "recommendation": (
                    "Boundaries are reasonably distinct. Improve `spec-validator` "
                    "test coverage to ≥20 tests. Document the layered validation "
                    "model to prevent future duplication."
                ),
            },
        ]

        for cluster in clusters:
            present = [s for s in cluster["skills"] if s in self.scorecards]
            lines.append(f"### Cluster: {cluster['name']}")
            lines.append("")
            lines.append(f"**Skills:** {', '.join(cluster['skills'])}")
            lines.append(f"**Present in inventory:** {', '.join(present) if present else 'none'}")
            lines.append("")
            lines.append(f"**Overlap:** {cluster['overlap']}")
            lines.append("")
            lines.append(f"**Recommendation:** {cluster['recommendation']}")
            lines.append("")

        return lines

    def _generate_meta_skills_audit(self, output_path: Path) -> List[str]:
        """Audit _meta (governance / infrastructure) skills.

        Args:
            output_path: Used to derive the repo root.

        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## _Meta Skills Audit")
        lines.append("")
        lines.append(
            "Governance and infrastructure skills live under `src/skills/_meta/`. "
            "They are not user-facing and are excluded from the main skills roster, "
            "but require their own health assessment."
        )
        lines.append("")

        # Derive _meta directory relative to the report output path.
        # output_path is typically docs/archive/audits/SKILLS-AUDIT.md so
        # repo_root is 3 levels up.
        try:
            repo_root = output_path.resolve().parents[3]
            meta_dir = repo_root / "src" / "skills" / "_meta"
        except IndexError:
            meta_dir = Path("/nonexistent")

        if not meta_dir.is_dir():
            lines.append("_Meta skills directory not found. Skipping.")
            return lines

        # Enumerate _meta skills (directories containing SKILL.md).
        meta_skills = sorted(
            d.name for d in meta_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )

        if not meta_skills:
            lines.append("No SKILL.md files found in `_meta/`. Nothing to report.")
            return lines

        lines.append(f"**Total _Meta Skills:** {len(meta_skills)}")
        lines.append("")

        # Per-skill summary: name, tests present?, scripts present?
        lines.append("| Skill | Scripts | Tests | SKILL.md |")
        lines.append("|-------|---------|-------|----------|")
        for name in meta_skills:
            skill_path = meta_dir / name
            has_scripts = (skill_path / "scripts").is_dir()
            has_tests = (skill_path / "tests").is_dir()
            lines.append(
                f"| {name} "
                f"| {'Yes' if has_scripts else 'No'} "
                f"| {'Yes' if has_tests else 'No'} "
                f"| Yes |"
            )
        lines.append("")

        # Summary counts
        with_tests = sum(
            1 for n in meta_skills
            if (meta_dir / n / "tests").is_dir()
        )
        lines.append(f"**Skills with test directories:** {with_tests}/{len(meta_skills)}")
        lines.append("")
        lines.append(
            "**Recommendation:** Each _meta skill should have at least one test "
            "covering its primary behaviour. Skills lacking a `tests/` directory "
            "are audit gaps."
        )
        lines.append("")

        return lines

    def _generate_recommendations(self) -> List[str]:
        """Generate framework-wide recommendations.
        
        Args:
            (none - uses self.scorecards)
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Framework-Wide Recommendations")
        lines.append("")
        
        # Aggregate recommendations by category
        test_recs = []
        doc_recs = []
        maintenance_recs = []
        quality_recs = []
        
        for skill_name, sc in self.scorecards.items():
            if sc.tests.value < 7:
                test_recs.append((skill_name, sc.tests.value))
            if sc.docs.value < 7:
                doc_recs.append((skill_name, sc.docs.value))
            if sc.maintenance.value < 6:
                maintenance_recs.append((skill_name, sc.maintenance.value))
            if sc.quality.value < 7:
                quality_recs.append((skill_name, sc.quality.value))
        
        # Generate recommendations
        if test_recs:
            lines.append("### Test Coverage Improvements Needed")
            lines.append(f"{len(test_recs)} skills need better test coverage:")
            for skill, score in sorted(test_recs, key=lambda x: x[1]):
                lines.append(f"- {skill} (current: {score}/10)")
            lines.append("")
        
        if doc_recs:
            lines.append("### Documentation Enhancements")
            lines.append(f"{len(doc_recs)} skills need improved documentation:")
            for skill, score in sorted(doc_recs, key=lambda x: x[1]):
                lines.append(f"- {skill} (current: {score}/10)")
            lines.append("")
        
        if maintenance_recs:
            lines.append("### Code Maintainability Improvements")
            lines.append(f"{len(maintenance_recs)} skills could benefit from refactoring:")
            for skill, score in sorted(maintenance_recs, key=lambda x: x[1]):
                lines.append(f"- {skill} (current: {score}/10)")
            lines.append("")
        
        if quality_recs:
            lines.append("### Code Quality Issues")
            lines.append(f"{len(quality_recs)} skills have quality concerns:")
            for skill, score in sorted(quality_recs, key=lambda x: x[1]):
                lines.append(f"- {skill} (current: {score}/10)")
            lines.append("")
        
        # Overall recommendations
        lines.append("### Priority Actions")
        lines.append("")
        lines.append("1. **Improve Test Coverage** - Aim for ≥90% across all CORE skills")
        lines.append("2. **Enhance Documentation** - Ensure all skills have comprehensive SKILL.md")
        lines.append("3. **Code Quality** - Refactor EXPERIMENTAL skills before deprecation")
        lines.append("4. **Maintenance** - Schedule quarterly code reviews for CORE skills")
        lines.append("")
        
        return lines

    def _generate_methodology(self) -> List[str]:
        """Generate audit methodology section.
        
        Args:
            (none)
            
        Returns:
            List of markdown lines
        """
        lines = []
        lines.append("## Audit Methodology")
        lines.append("")
        
        lines.append("### 6-Dimension Scoring Framework")
        lines.append("")
        lines.append("Each skill is evaluated across 6 critical dimensions:")
        lines.append("")
        
        lines.append("#### VALUE (1-10)")
        lines.append("**Strategic importance to the framework**")
        lines.append("- 9-10: Essential, central to framework mission")
        lines.append("- 7-8: Core strategic capability")
        lines.append("- 5-6: Important capability")
        lines.append("- 3-4: Limited utility")
        lines.append("- 1-2: Rarely used")
        lines.append("")
        
        lines.append("#### USAGE (1-10)")
        lines.append("**Integration frequency and adoption**")
        lines.append("- 9-10: Ubiquitous, integrated everywhere")
        lines.append("- 7-8: Very frequent, multiple integrations")
        lines.append("- 5-6: Regular usage")
        lines.append("- 3-4: Limited usage")
        lines.append("- 1-2: Rarely used")
        lines.append("")
        
        lines.append("#### MAINTENANCE (1-10)")
        lines.append("**Code quality and maintainability**")
        lines.append("- 9-10: Exemplary, industry-leading practices")
        lines.append("- 7-8: Well maintained, modern best practices")
        lines.append("- 5-6: Adequate code quality")
        lines.append("- 3-4: Below average, needs refactoring")
        lines.append("- 1-2: Very poor, significant tech debt")
        lines.append("")
        
        lines.append("#### TESTS (1-10)")
        lines.append("**Test coverage and quality**")
        lines.append("- 9-10: Outstanding (>95% coverage)")
        lines.append("- 7-8: Excellent (~90% coverage)")
        lines.append("- 5-6: Moderate (~65% coverage)")
        lines.append("- 3-4: Low (<60% coverage)")
        lines.append("- 1-2: Minimal/no tests")
        lines.append("")
        
        lines.append("#### DOCS (1-10)")
        lines.append("**Documentation completeness**")
        lines.append("- 9-10: Perfect, exemplary documentation")
        lines.append("- 7-8: Excellent docs")
        lines.append("- 5-6: Adequate documentation")
        lines.append("- 3-4: Basic/incomplete docs")
        lines.append("- 1-2: Minimal/no documentation")
        lines.append("")
        
        lines.append("#### QUALITY (1-10)")
        lines.append("**Overall code quality**")
        lines.append("- 9-10: Production-grade, no known issues")
        lines.append("- 7-8: Very high quality")
        lines.append("- 5-6: Average quality")
        lines.append("- 3-4: Works but with issues")
        lines.append("- 1-2: Barely functional")
        lines.append("")
        
        lines.append("### Overall Score Calculation")
        lines.append("")
        lines.append("Overall Score = (VALUE + USAGE + MAINTENANCE + TESTS + DOCS + QUALITY) / 6 * 100 / 10")
        lines.append("")
        lines.append("**Range:** 0-100")
        lines.append("")
        
        lines.append("### Skill Categories")
        lines.append("")
        lines.append("Based on overall score:")
        lines.append("")
        lines.append("- **CORE** (≥75): Essential skills requiring high standards")
        lines.append("- **UTILITY** (55-75): Important supporting skills")
        lines.append("- **EXPERIMENTAL** (<55): Trial/prototype skills")
        lines.append("")
        
        lines.append("### Quality Standards")
        lines.append("")
        lines.append("- **Minimum acceptable:** ≥65/100")
        lines.append("- **CORE skill minimum:** ≥80/100")
        lines.append("- **Excellent:** ≥85/100")
        lines.append("- **Outstanding:** ≥90/100")
        lines.append("")
        
        return lines
