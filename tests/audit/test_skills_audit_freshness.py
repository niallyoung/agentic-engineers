"""Test that the SKILLS-AUDIT.md report exists and is recent.

This freshness test ensures the audit report is regenerated regularly and does
not silently go stale. A stale audit report means the skill inventory is out
of sync with the actual codebase state.

The 7-day freshness threshold is intentionally lenient enough to survive normal
development pauses while still catching cases where the report was forgotten.

Note: SKILLS-AUDIT.md is listed in .gitignore because it is a regenerable artifact.
      Tests that require the file content skip gracefully in CI where the file is absent.
      To regenerate locally: python3 -m src.audit.run_audit
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta


AUDIT_REPORT_PATH = Path(__file__).resolve().parents[2] / "docs" / "archive" / "audits" / "SKILLS-AUDIT.md"
MAX_STALENESS_DAYS = 7

# Mark all content-dependent tests to skip when the file does not exist.
# The audit report is .gitignored (regenerable). CI does not have it; local
# developer runs do (after running python3 -m src.audit.run_audit).
requires_audit_report = pytest.mark.skipif(
    not AUDIT_REPORT_PATH.exists(),
    reason=(
        "SKILLS-AUDIT.md is not present (it is .gitignored and must be regenerated locally). "
        "Run: python3 -m src.audit.run_audit"
    ),
)


class TestSkillsAuditFreshness:
    """Verify SKILLS-AUDIT.md exists and contains a recent generation timestamp.

    The audit report is .gitignored (it is a regenerable artifact). Tests that
    inspect file content are skipped in CI via the @requires_audit_report mark.
    The structural tests (audit module imports, run_audit module loadable) always
    run regardless of whether the report file is present.
    """

    def test_audit_runner_module_importable(self) -> None:
        """The run_audit module must be importable (auditor infrastructure health check)."""
        from src.audit.run_audit import main  # noqa: F401 — import-only test

    def test_audit_skills_dir_has_expected_structure(self) -> None:
        """Skills directory must exist and have at least 20 top-level skill directories."""
        skills_dir = AUDIT_REPORT_PATH.parents[3] / "src" / "skills"
        assert skills_dir.exists(), f"Skills directory not found at {skills_dir}"
        exclude = {
            "_meta", "__pycache__", "shared", "patterns",
            "architecture", "security", "testing", "monitoring",
            "orchestration", "review", "roles", "optimization",
            "spec-extract",
        }
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and d.name not in exclude]
        assert len(skill_dirs) >= 20, (
            f"Expected at least 20 top-level skill directories, found {len(skill_dirs)}"
        )

    def test_meta_skills_dir_has_expected_structure(self) -> None:
        """_Meta skills directory must exist with governance skills."""
        meta_dir = AUDIT_REPORT_PATH.parents[3] / "src" / "skills" / "_meta"
        assert meta_dir.exists(), f"_Meta skills directory not found at {meta_dir}"
        meta_skill_dirs = [
            d for d in meta_dir.iterdir()
            if d.is_dir() and d.name not in {"__pycache__", "skill-template"}
        ]
        assert len(meta_skill_dirs) >= 10, (
            f"Expected at least 10 _meta skill directories, found {len(meta_skill_dirs)}"
        )

    @requires_audit_report
    def test_audit_report_is_not_empty(self) -> None:
        """SKILLS-AUDIT.md must be non-trivial in size (>1 KB)."""
        size = AUDIT_REPORT_PATH.stat().st_size
        assert size > 1024, (
            f"SKILLS-AUDIT.md is suspiciously small ({size} bytes). "
            "Expected a full audit report (>1 KB). "
            "Regenerate: python3 -m src.audit.run_audit"
        )

    @requires_audit_report
    def test_audit_report_contains_generation_timestamp(self) -> None:
        """SKILLS-AUDIT.md must contain a **Generated:** timestamp line."""
        content = AUDIT_REPORT_PATH.read_text()
        assert "**Generated:**" in content, (
            "SKILLS-AUDIT.md does not contain a generation timestamp. "
            "The report may be hand-edited or corrupted. "
            "Regenerate: python3 -m src.audit.run_audit"
        )

    @requires_audit_report
    def test_audit_report_is_recent(self) -> None:
        """SKILLS-AUDIT.md must have been generated within the last 7 days.

        The timestamp is parsed from the **Generated:** line written by
        AuditReporter.generate_markdown_report() in the format:
            **Generated:** 2026-06-14 11:46:17
        """
        content = AUDIT_REPORT_PATH.read_text()

        # Parse the generation timestamp
        generated_line = None
        for line in content.splitlines():
            if line.startswith("**Generated:**"):
                generated_line = line
                break

        assert generated_line is not None, (
            "Could not find **Generated:** line in SKILLS-AUDIT.md. "
            "Regenerate: python3 -m src.audit.run_audit"
        )

        # Extract timestamp string: "**Generated:** 2026-06-14 11:46:17"
        timestamp_str = generated_line.replace("**Generated:**", "").strip()
        try:
            generated_at = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            pytest.fail(
                f"Could not parse timestamp '{timestamp_str}' from SKILLS-AUDIT.md: {exc}. "
                "Regenerate: python3 -m src.audit.run_audit"
            )

        age = datetime.now() - generated_at
        max_age = timedelta(days=MAX_STALENESS_DAYS)

        assert age <= max_age, (
            f"SKILLS-AUDIT.md is stale: generated {age.days} day(s) ago "
            f"(max allowed: {MAX_STALENESS_DAYS} days). "
            "Regenerate: python3 -m src.audit.run_audit"
        )

    @requires_audit_report
    def test_audit_report_covers_all_skill_tiers(self) -> None:
        """SKILLS-AUDIT.md must cover both top-level and _meta skills."""
        content = AUDIT_REPORT_PATH.read_text()

        assert "_Meta Skills Audit" in content, (
            "SKILLS-AUDIT.md does not include the '_Meta Skills Audit' section. "
            "The report only covers top-level skills. "
            "Regenerate: python3 -m src.audit.run_audit and append _meta section."
        )
        assert "Redundancy Clusters" in content, (
            "SKILLS-AUDIT.md does not include the 'Redundancy Clusters' section. "
            "The consolidation analysis is missing."
        )

    @requires_audit_report
    def test_audit_report_covers_minimum_skill_count(self) -> None:
        """SKILLS-AUDIT.md must report on at least 20 top-level skills."""
        content = AUDIT_REPORT_PATH.read_text()

        # The header line reads "**Total Skills Audited:** N"
        skills_audited = 0
        for line in content.splitlines():
            if "**Total Skills Audited:**" in line:
                try:
                    skills_audited = int(line.split("**Total Skills Audited:**")[1].strip())
                except (ValueError, IndexError):
                    pass
                break

        assert skills_audited >= 20, (
            f"SKILLS-AUDIT.md reports only {skills_audited} skills audited. "
            "Expected at least 20 top-level skills. "
            "Regenerate: python3 -m src.audit.run_audit"
        )
