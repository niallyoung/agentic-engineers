"""Main script to run the skills audit."""

import sys
import os
from pathlib import Path
from src.audit.skills_auditor import SkillsAuditor
from src.audit.audit_reporter import AuditReporter


def main() -> int:
    """Run the complete skills audit.
    
    Returns:
        Exit code (0 for success)
    """
    try:
        # Set up paths
        repo_root = Path(__file__).resolve().parents[2]
        skills_dir = repo_root / "src" / "skills"
        audit_dir = repo_root / "docs" / "archive" / "audits"
        audit_dir.mkdir(parents=True, exist_ok=True)
        output_file = audit_dir / "SKILLS-AUDIT.md"
        
        print("🔍 Starting Skills Audit Framework...")
        print(f"📁 Skills directory: {skills_dir}")
        print("")
        
        # Run audit
        print("⏳ Auditing all skills...")
        auditor = SkillsAuditor(skills_dir)
        scorecards = auditor.audit_all_skills()
        
        print(f"✓ Audited {len(scorecards)} skills")
        print("")
        
        # Get statistics
        stats = auditor.get_summary_statistics()
        
        print("📊 Audit Statistics:")
        print(f"  - Total Skills: {stats.get('total_skills', 0)}")
        print(f"  - Average Score: {stats.get('avg_score', 0):.1f}/100")
        print(f"  - Best Score: {stats.get('max_score', 0):.1f}/100")
        print(f"  - Worst Score: {stats.get('min_score', 0):.1f}/100")
        print("")
        
        # Category breakdown
        categories = stats.get('category_breakdown', {})
        print("📋 Category Breakdown:")
        for category in ["CORE", "UTILITY", "EXPERIMENTAL"]:
            count = categories.get(category, 0)
            pct = (count / stats.get('total_skills', 1)) * 100
            print(f"  - {category}: {count} ({pct:.1f}%)")
        print("")
        
        # Skills needing improvement
        weak = stats.get('skills_needing_improvement', [])
        if weak:
            print(f"⚠️  Skills Needing Improvement ({len(weak)}):")
            for skill in weak[:5]:
                sc = auditor.scorecards[skill]
                print(f"  - {skill}: {sc.overall_score():.1f}/100")
            if len(weak) > 5:
                print(f"  ... and {len(weak) - 5} more")
            print("")
        
        # Dimension averages
        dims = stats.get('dimension_averages', {})
        print("📈 Dimension Averages:")
        for dim in ["value", "usage", "maintenance", "tests", "docs", "quality"]:
            avg = dims.get(dim, 0)
            print(f"  - {dim.upper()}: {avg:.2f}/10")
        print("")
        
        # Generate report
        print("📝 Generating audit report...")
        reporter = AuditReporter(auditor)
        report = reporter.generate_markdown_report(output_file)
        
        print(f"✓ Report generated: {output_file}")
        print(f"  - File size: {len(report)} bytes")
        print(f"  - Lines: {len(report.split(chr(10)))}")
        print("")
        
        print("✅ Skills Audit Complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if os.environ.get("AE_DEBUG"):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
