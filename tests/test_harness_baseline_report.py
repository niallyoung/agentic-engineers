"""
AC4 gate: Baseline report presence and schema test.

Asserts that docs/archive/audits/harness-compatibility-baseline.md:
  1. Exists on disk.
  2. Is non-empty.
  3. Contains every required section header.
  4. Contains the compatibility matrix table header.
  5. Contains the sign-off checklist with all four ACs.
  6. Records data for the three target harnesses: copilot, opencode, claude.

This test must stay green from the moment the baseline is committed.  Any PR that
removes or structurally degrades the baseline report will fail here, acting as a
regression gate for the m2-harness-eval-baseline dependency chain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Location of the baseline report
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BASELINE_PATH = _REPO_ROOT / "docs" / "archive" / "audits" / "harness-compatibility-baseline.md"

# ---------------------------------------------------------------------------
# Required schema: section headers that must be present
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS = [
    "## 1. Environment",
    "## 2. Test Suite Results",
    "## 3. Compatibility Matrix (harness x model x feature)",
    "## 4. Per-Harness Success Rate Against 95% Target",
    "## 5. P50 / P99 Latency and Cost",
    "## 6. Important Notes on Framework Architecture",
    "## 7. Baseline Sign-Off Checklist",
    "## 8. Recommended Next Steps",
]

# Required acceptance-criteria entries in the sign-off checklist.
_REQUIRED_ACS = [
    "AC1",
    "AC2",
    "AC3",
    "AC4",
]

# The three target harnesses must each appear in the report.
_REQUIRED_HARNESSES = [
    "copilot",
    "opencode",
    "claude",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def baseline_text() -> str:
    """Read the baseline report once for all tests in this module."""
    assert _BASELINE_PATH.exists(), (
        f"Baseline report not found at {_BASELINE_PATH}. "
        "The m2-harness-eval-baseline task must be completed before this gate passes."
    )
    return _BASELINE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBaselineReportPresence:
    """Gate: baseline report file exists and is readable."""

    def test_baseline_file_exists(self):
        """AC4: The baseline report file must exist."""
        assert _BASELINE_PATH.exists(), (
            f"Baseline report missing: {_BASELINE_PATH}"
        )

    def test_baseline_file_is_non_empty(self, baseline_text: str):
        """Baseline report must not be an empty file."""
        assert len(baseline_text.strip()) > 100, (
            "Baseline report appears to be empty or trivially short."
        )

    def test_baseline_is_markdown(self):
        """Baseline report must be a .md file."""
        assert _BASELINE_PATH.suffix == ".md", (
            f"Expected .md extension, got: {_BASELINE_PATH.suffix}"
        )


class TestBaselineReportSchema:
    """Gate: baseline report contains all required structural sections."""

    @pytest.mark.parametrize("section", _REQUIRED_SECTIONS)
    def test_required_section_present(self, baseline_text: str, section: str):
        """Each required section header must appear in the report."""
        assert section in baseline_text, (
            f"Required section missing from baseline report: {section!r}"
        )

    def test_compatibility_matrix_table_present(self, baseline_text: str):
        """The harness x model compatibility matrix table must be present."""
        assert "| Harness |" in baseline_text, (
            "Compatibility matrix table (| Harness | ...) not found in baseline report."
        )

    @pytest.mark.parametrize("ac", _REQUIRED_ACS)
    def test_acceptance_criteria_present(self, baseline_text: str, ac: str):
        """Each acceptance criterion (AC1-AC4) must appear in the sign-off checklist."""
        assert ac in baseline_text, (
            f"Acceptance criterion {ac} missing from baseline report sign-off checklist."
        )

    def test_sign_off_checklist_has_checkboxes(self, baseline_text: str):
        """Sign-off checklist must use markdown checkbox syntax."""
        assert "- [x]" in baseline_text, (
            "Baseline sign-off checklist must contain checked markdown checkboxes (- [x])."
        )


class TestBaselineReportContent:
    """Gate: baseline report captures data for all three target harnesses."""

    @pytest.mark.parametrize("harness", _REQUIRED_HARNESSES)
    def test_harness_mentioned(self, baseline_text: str, harness: str):
        """Each of the three target harnesses must be mentioned in the report."""
        assert harness in baseline_text.lower(), (
            f"Target harness {harness!r} not mentioned in baseline report."
        )

    def test_95_percent_target_mentioned(self, baseline_text: str):
        """The 95% success-rate target must be referenced in the report."""
        assert "95%" in baseline_text or "95 percent" in baseline_text.lower(), (
            "The 95% success-rate target must be documented in the baseline report."
        )

    def test_latency_metrics_present(self, baseline_text: str):
        """P50 / P99 latency must be documented."""
        assert "P50" in baseline_text and "P99" in baseline_text, (
            "P50 and P99 latency metrics must be recorded in the baseline report."
        )

    def test_cost_estimates_present(self, baseline_text: str):
        """Cost estimates must appear in the report."""
        # The report records cost in USD format
        assert "cost" in baseline_text.lower() and "$" in baseline_text, (
            "Cost estimates (in USD) must be recorded in the baseline report."
        )

    def test_hardening_candidates_section_present(self, baseline_text: str):
        """Sub-95% / skip harnesses must be explicitly listed as hardening candidates."""
        assert "Hardening" in baseline_text or "hardening" in baseline_text, (
            "Hardening candidates section must be present in the baseline report."
        )

    def test_generated_date_present(self, baseline_text: str):
        """The report must record the generation date."""
        assert "Generated" in baseline_text or "generated" in baseline_text, (
            "Baseline report must record its generation date."
        )
