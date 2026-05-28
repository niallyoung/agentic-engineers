"""
Tests for healer_metrics_analyzer module.

Covers HealerMetricsAnalyzer and AuditEntry from
src/skills/healer-metrics-analyzer.py.

TDD red-phase style: tests written to validate actual behaviour of the
existing implementation.
Target: >=90% branch coverage
"""
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# ── Import healer-metrics-analyzer via importlib (hyphenated filename) ──────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEALER_PATH = _REPO_ROOT / "src" / "skills" / "healer-metrics-analyzer.py"

_spec = importlib.util.spec_from_file_location("healer_metrics_analyzer", _HEALER_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

HealerMetricsAnalyzer = _mod.HealerMetricsAnalyzer
AuditEntry = _mod.AuditEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    """Return naive ISO 8601 string (no timezone) — matches analyzer's naive cutoff_date."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _recent_ts() -> str:
    """Return a naive ISO timestamp within the last 30 days."""
    return _iso(datetime.utcnow() - timedelta(days=1))


def _make_entry(session_id: str, phase: str, status: str, details: dict = None) -> dict:
    """Create an audit log entry dict."""
    return {
        "timestamp": _recent_ts(),
        "session_id": session_id,
        "phase": phase,
        "status": status,
        "details": details or {},
    }


def _write_audit_file(directory: Path, filename: str, entries: list) -> Path:
    """Write a JSONL audit log file with the given entries."""
    filepath = directory / filename
    lines = [json.dumps(e) for e in entries]
    filepath.write_text("\n".join(lines))
    return filepath


# ---------------------------------------------------------------------------
# AuditEntry tests
# ---------------------------------------------------------------------------

class TestAuditEntry:
    """Tests for AuditEntry dataclass and from_jsonl factory."""

    def test_from_jsonl_valid_line(self):
        """from_jsonl parses a valid JSONL line into an AuditEntry."""
        data = {
            "timestamp": _recent_ts(),
            "session_id": "sess-001",
            "phase": "1",
            "status": "PASS",
            "details": {"score": 95},
        }
        entry = AuditEntry.from_jsonl(json.dumps(data))
        assert entry.session_id == "sess-001"
        assert entry.phase == "1"
        assert entry.status == "PASS"
        assert entry.details == {"score": 95}
        assert entry.timestamp == data["timestamp"]

    def test_from_jsonl_missing_details_defaults_to_empty(self):
        """from_jsonl uses empty dict when details is absent."""
        data = {
            "timestamp": _recent_ts(),
            "session_id": "sess-002",
            "phase": "2",
            "status": "FAIL",
        }
        entry = AuditEntry.from_jsonl(json.dumps(data))
        assert entry.details == {}

    def test_from_jsonl_missing_fields_are_none(self):
        """from_jsonl returns None for missing non-details fields."""
        data = {}
        entry = AuditEntry.from_jsonl(json.dumps(data))
        assert entry.timestamp is None
        assert entry.session_id is None
        assert entry.phase is None
        assert entry.status is None

    def test_from_jsonl_whitespace_stripped(self):
        """from_jsonl handles lines with surrounding whitespace."""
        data = {"timestamp": _recent_ts(), "session_id": "s1", "phase": "3", "status": "PASS"}
        line = "  " + json.dumps(data) + "  \n"
        entry = AuditEntry.from_jsonl(line)
        assert entry.session_id == "s1"

    def test_audit_entry_service_defaults_none(self):
        """AuditEntry.service defaults to None when not provided."""
        data = {"timestamp": _recent_ts(), "session_id": "s1", "phase": "1", "status": "PASS"}
        entry = AuditEntry.from_jsonl(json.dumps(data))
        assert entry.service is None


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — constructor
# ---------------------------------------------------------------------------

class TestHealerMetricsAnalyzerInit:
    """Tests for HealerMetricsAnalyzer.__init__."""

    def test_default_init(self, tmp_path):
        """Analyser initialises with default parameters."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        assert analyzer.audit_dir == str(tmp_path)
        assert analyzer.days == 30

    def test_custom_days(self, tmp_path):
        """Analyser respects custom days parameter."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path), days=7)
        assert analyzer.days == 7

    def test_cutoff_date_computed(self, tmp_path):
        """cutoff_date is approximately (now - days) ago."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path), days=10)
        expected = datetime.utcnow() - timedelta(days=10)
        # Allow 5s tolerance
        diff = abs((analyzer.cutoff_date - expected).total_seconds())
        assert diff < 5

    def test_entries_initially_empty(self, tmp_path):
        """entries list is empty before loading."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        assert analyzer.entries == []


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — load_audit_logs
# ---------------------------------------------------------------------------

class TestLoadAuditLogs:
    """Tests for HealerMetricsAnalyzer.load_audit_logs."""

    def test_load_from_empty_directory(self, tmp_path):
        """load_audit_logs with no matching files produces empty entries."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        assert analyzer.entries == []

    def test_load_valid_audit_file(self, tmp_path):
        """load_audit_logs reads entries from a matching file."""
        entries = [
            _make_entry("sess-1", "1", "PASS"),
            _make_entry("sess-1", "2", "PASS"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        assert len(analyzer.entries) == 2

    def test_load_ignores_non_matching_files(self, tmp_path):
        """load_audit_logs ignores files not matching the pattern."""
        (tmp_path / "other-log.jsonl").write_text('{"timestamp": "2024-01-01T00:00:00+00:00"}\n')
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        assert len(analyzer.entries) == 0

    def test_load_skips_old_entries(self, tmp_path):
        """load_audit_logs skips entries older than the cutoff."""
        old_ts = _iso(datetime.utcnow() - timedelta(days=60))
        old_entry = {
            "timestamp": old_ts,
            "session_id": "old-sess",
            "phase": "1",
            "status": "PASS",
            "details": {},
        }
        _write_audit_file(tmp_path, "quality-gate-audit-old.jsonl", [old_entry])
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path), days=30)
        analyzer.load_audit_logs()
        assert len(analyzer.entries) == 0

    def test_load_handles_invalid_json_gracefully(self, tmp_path):
        """load_audit_logs warns on bad JSON but continues processing."""
        bad_file = tmp_path / "quality-gate-audit-bad.jsonl"
        bad_file.write_text("not valid json\n")
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        # Should not raise; just skip the bad line
        analyzer.load_audit_logs()
        assert len(analyzer.entries) == 0

    def test_load_groups_by_session_id(self, tmp_path):
        """load_audit_logs groups entries by session_id."""
        entries = [
            _make_entry("sess-a", "1", "PASS"),
            _make_entry("sess-b", "1", "FAIL"),
            _make_entry("sess-a", "2", "PASS"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        assert "sess-a" in analyzer.healer_sessions
        assert "sess-b" in analyzer.healer_sessions
        assert len(analyzer.healer_sessions["sess-a"]) == 2

    def test_load_multiple_files(self, tmp_path):
        """load_audit_logs reads from multiple matching files."""
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl",
                          [_make_entry("s1", "1", "PASS")])
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-02.jsonl",
                          [_make_entry("s2", "1", "PASS")])
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        assert len(analyzer.entries) == 2


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — calculate_healer_success_rate
# ---------------------------------------------------------------------------

class TestCalculateHealerSuccessRate:
    """Tests for HealerMetricsAnalyzer.calculate_healer_success_rate."""

    def test_no_healer_sessions_returns_zero(self, tmp_path):
        """Without healer invocations returns zeroed metrics."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer.calculate_healer_success_rate()
        assert result["healer_invocations"] == 0
        assert result["success_rate"] == 0
        assert "notes" in result

    def test_successful_healer_session(self, tmp_path):
        """Session with DELEGATE_HEALER and PROCEED in phase 4 is a success."""
        entries = [
            _make_entry("sess-1", "3", "DELEGATE_HEALER"),
            _make_entry("sess-1", "4", "PROCEED"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_healer_success_rate()
        assert result["healer_invocations"] == 1
        assert result["healer_fixes_passed"] == 1
        assert result["healer_fixes_failed"] == 0
        assert result["success_rate"] == 100.0

    def test_failed_healer_session(self, tmp_path):
        """Session with DELEGATE_HEALER and ESCALATE in phase 4 is a failure."""
        entries = [
            _make_entry("sess-2", "3", "DELEGATE_HEALER"),
            _make_entry("sess-2", "4", "ESCALATE"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_healer_success_rate()
        assert result["healer_invocations"] == 1
        assert result["healer_fixes_passed"] == 0
        assert result["healer_fixes_failed"] == 1
        assert result["success_rate"] == 0.0
        assert result["failure_rate"] == 100.0

    def test_mixed_healer_sessions(self, tmp_path):
        """Mixed healer sessions compute correct percentages."""
        entries = [
            _make_entry("pass-1", "3", "DELEGATE_HEALER"),
            _make_entry("pass-1", "4", "PROCEED"),
            _make_entry("fail-1", "3", "DELEGATE_HEALER"),
            _make_entry("fail-1", "4", "ESCALATE"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_healer_success_rate()
        assert result["healer_invocations"] == 2
        assert result["success_rate"] == 50.0
        assert result["failure_rate"] == 50.0

    def test_session_without_phase_4_not_counted(self, tmp_path):
        """Sessions with DELEGATE_HEALER but no phase 4 are invoked but uncounted."""
        entries = [
            _make_entry("sess-no-phase4", "3", "DELEGATE_HEALER"),
            # No phase 4 entry
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_healer_success_rate()
        assert result["healer_invocations"] == 1
        # Neither passed nor failed (no phase 4 outcome)
        assert result["healer_fixes_passed"] + result["healer_fixes_failed"] == 0


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — calculate_escalation_rate
# ---------------------------------------------------------------------------

class TestCalculateEscalationRate:
    """Tests for HealerMetricsAnalyzer.calculate_escalation_rate."""

    def test_no_sessions_returns_zero(self, tmp_path):
        """Without sessions, escalation rate is 0."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer.calculate_escalation_rate()
        assert result["total_checks"] == 0
        assert result["escalation_rate"] == 0
        assert "notes" in result

    def test_all_escalated(self, tmp_path):
        """Session ending in ESCALATE at phase 4 is counted as escalated."""
        entries = [_make_entry("sess-1", "4", "ESCALATE")]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_escalation_rate()
        assert result["escalated"] == 1
        assert result["escalation_rate"] == 100.0

    def test_auto_fixed_session(self, tmp_path):
        """Session with phase 3 DELEGATE_HEALER and phase 4 PROCEED is auto-fixed."""
        entries = [
            _make_entry("sess-2", "3", "DELEGATE_HEALER"),
            _make_entry("sess-2", "4", "PROCEED"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_escalation_rate()
        assert result["auto_fixed"] == 1
        assert result["escalated"] == 0
        assert result["escalation_rate"] == 0.0

    def test_mixed_escalation_and_auto_fix(self, tmp_path):
        """Calculates correct escalation rate for mixed sessions."""
        entries = [
            _make_entry("esc-sess", "4", "ESCALATE"),
            _make_entry("fix-sess", "3", "DELEGATE_HEALER"),
            _make_entry("fix-sess", "4", "PROCEED"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_escalation_rate()
        assert result["total_checks"] == 2
        assert result["escalated"] == 1
        assert result["escalation_rate"] == 50.0


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — calculate_phase_success_rates
# ---------------------------------------------------------------------------

class TestCalculatePhaseSuccessRates:
    """Tests for HealerMetricsAnalyzer.calculate_phase_success_rates."""

    def test_no_sessions_returns_empty(self, tmp_path):
        """No sessions returns empty dict."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer.calculate_phase_success_rates()
        assert result == {}

    def test_single_phase_pass(self, tmp_path):
        """Single PASS in phase 1 returns 100% pass rate."""
        entries = [_make_entry("s1", "1", "PASS")]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_phase_success_rates()
        assert "phase_1" in result
        assert result["phase_1"]["pass_rate"] == 100.0
        assert result["phase_1"]["pass_count"] == 1
        assert result["phase_1"]["fail_count"] == 0

    def test_single_phase_fail(self, tmp_path):
        """Single FAIL in phase 2 returns 0% pass rate."""
        entries = [_make_entry("s1", "2", "FAIL")]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_phase_success_rates()
        assert "phase_2" in result
        assert result["phase_2"]["pass_rate"] == 0.0

    def test_mixed_pass_fail(self, tmp_path):
        """3 PASS + 1 FAIL in same phase = 75% pass rate."""
        entries = [
            _make_entry("s1", "1", "PASS"),
            _make_entry("s2", "1", "PASS"),
            _make_entry("s3", "1", "PASS"),
            _make_entry("s4", "1", "FAIL"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_phase_success_rates()
        assert result["phase_1"]["pass_rate"] == 75.0
        assert result["phase_1"]["total"] == 4

    def test_multiple_phases(self, tmp_path):
        """Separate phases are tracked independently."""
        entries = [
            _make_entry("s1", "1", "PASS"),
            _make_entry("s1", "2", "FAIL"),
            _make_entry("s1", "3", "PASS"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_phase_success_rates()
        assert "phase_1" in result
        assert "phase_2" in result
        assert "phase_3" in result

    def test_non_pass_fail_statuses_ignored(self, tmp_path):
        """Statuses other than PASS/FAIL are ignored in phase stats."""
        entries = [
            _make_entry("s1", "1", "PROCEED"),
            _make_entry("s1", "1", "ESCALATE"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.calculate_phase_success_rates()
        assert result == {}


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — analyze_failure_patterns
# ---------------------------------------------------------------------------

class TestAnalyzeFailurePatterns:
    """Tests for HealerMetricsAnalyzer.analyze_failure_patterns."""

    def test_no_sessions_returns_notes(self, tmp_path):
        """With no data, returns notes dict."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer.analyze_failure_patterns()
        assert "notes" in result

    def test_failure_with_high_confidence(self, tmp_path):
        """FAIL with HIGH confidence is tracked in high_confidence_failures."""
        entries = [
            _make_entry("s1", "3", "FAIL", {"issue_type": "test_failure", "confidence": "HIGH"}),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.analyze_failure_patterns()
        assert "test_failure" in result
        assert result["test_failure"]["count"] == 1
        assert result["test_failure"]["high_confidence_failures"] == 1

    def test_failure_with_low_confidence(self, tmp_path):
        """FAIL with LOW confidence is tracked in low_confidence_failures."""
        entries = [
            _make_entry("s1", "3", "FAIL", {"issue_type": "flaky_test", "confidence": "LOW"}),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.analyze_failure_patterns()
        assert "flaky_test" in result
        assert result["flaky_test"]["low_confidence_failures"] == 1

    def test_failure_unknown_issue_type(self, tmp_path):
        """FAIL with no issue_type is categorised as 'unknown'."""
        entries = [_make_entry("s1", "3", "FAIL", {})]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.analyze_failure_patterns()
        assert "unknown" in result

    def test_non_phase3_failures_ignored(self, tmp_path):
        """FAILs in phases other than 3 are not tracked."""
        entries = [
            _make_entry("s1", "1", "FAIL", {"issue_type": "phase1_issue"}),
            _make_entry("s1", "2", "FAIL", {"issue_type": "phase2_issue"}),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        result = analyzer.analyze_failure_patterns()
        assert "notes" in result  # No phase-3 failures → empty → notes returned


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — _assess_level_3_readiness
# ---------------------------------------------------------------------------

class TestAssessLevel3Readiness:
    """Tests for HealerMetricsAnalyzer._assess_level_3_readiness."""

    def _build_analyzer_with_data(self, tmp_path, healer_pass=True, escalated=False):
        """Helper: build an analyser with sessions satisfying level-3 criteria."""
        entries = []
        session_id = "lvl3-sess"
        entries.append(_make_entry(session_id, "1", "PASS"))
        entries.append(_make_entry(session_id, "2", "PASS"))
        if healer_pass:
            entries.append(_make_entry(session_id, "3", "DELEGATE_HEALER"))
            entries.append(_make_entry(session_id, "4", "PROCEED"))
        elif escalated:
            entries.append(_make_entry(session_id, "4", "ESCALATE"))
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        analyzer.load_audit_logs()
        return analyzer

    def test_readiness_structure(self, tmp_path):
        """_assess_level_3_readiness returns correct keys."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer._assess_level_3_readiness()
        assert "ready_for_level_3" in result
        assert "criteria_met" in result
        assert "criteria_total" in result
        assert "details" in result

    def test_not_ready_with_no_data(self, tmp_path):
        """With no data, level 3 readiness is not met."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer._assess_level_3_readiness()
        assert result["ready_for_level_3"] is False

    def test_criteria_total_is_three(self, tmp_path):
        """There are always 3 criteria to evaluate."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer._assess_level_3_readiness()
        assert result["criteria_total"] == 3

    def test_criteria_details_keys(self, tmp_path):
        """details dict contains the three expected criteria keys."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        result = analyzer._assess_level_3_readiness()
        details = result["details"]
        assert "healer_success_rate_gte_70" in details
        assert "escalation_rate_lte_30" in details
        assert "all_phases_gt_90" in details


# ---------------------------------------------------------------------------
# HealerMetricsAnalyzer — generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    """Tests for HealerMetricsAnalyzer.generate_report."""

    def test_generate_report_no_data(self, tmp_path):
        """generate_report with no log files returns status=no_data."""
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        report = analyzer.generate_report()
        assert report["status"] == "no_data"
        assert "message" in report
        assert "timestamp" in report

    def test_generate_report_with_data(self, tmp_path):
        """generate_report with data returns full report structure."""
        entries = [
            _make_entry("s1", "1", "PASS"),
            _make_entry("s1", "2", "PASS"),
            _make_entry("s1", "3", "DELEGATE_HEALER"),
            _make_entry("s1", "4", "PROCEED"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        report = analyzer.generate_report()
        assert "timestamp" in report
        assert "period_days" in report
        assert "total_sessions" in report
        assert "healer_success" in report
        assert "escalation" in report
        assert "phase_success_rates" in report
        assert "failure_patterns" in report
        assert "level_3_readiness" in report

    def test_generate_report_period_days(self, tmp_path):
        """generate_report records the correct period_days."""
        entries = [_make_entry("s1", "1", "PASS")]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path), days=14)
        report = analyzer.generate_report()
        assert report["period_days"] == 14

    def test_generate_report_total_sessions(self, tmp_path):
        """generate_report records the total number of unique sessions."""
        entries = [
            _make_entry("s1", "1", "PASS"),
            _make_entry("s2", "1", "FAIL"),
            _make_entry("s3", "1", "PASS"),
        ]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        report = analyzer.generate_report()
        assert report["total_sessions"] == 3

    def test_generate_report_timestamp_format(self, tmp_path):
        """generate_report timestamp ends with 'Z'."""
        entries = [_make_entry("s1", "1", "PASS")]
        _write_audit_file(tmp_path, "quality-gate-audit-2024-01-01.jsonl", entries)
        analyzer = HealerMetricsAnalyzer(audit_dir=str(tmp_path))
        report = analyzer.generate_report()
        assert report["timestamp"].endswith("Z")


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------

class TestMain:
    """Tests for the module-level main() function."""

    def test_main_prints_json_to_stdout(self, tmp_path, capsys, monkeypatch):
        """main() prints JSON output when called with --audit-dir."""
        monkeypatch.setattr(
            "sys.argv",
            ["healer-metrics-analyzer", "--audit-dir", str(tmp_path), "--days", "30"],
        )
        _mod.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "timestamp" in data

    def test_main_with_pretty_flag(self, tmp_path, capsys, monkeypatch):
        """main() with --pretty flag produces indented JSON."""
        monkeypatch.setattr(
            "sys.argv",
            ["healer-metrics-analyzer", "--audit-dir", str(tmp_path), "--pretty"],
        )
        _mod.main()
        captured = capsys.readouterr()
        assert "\n" in captured.out  # Indented JSON has newlines

    def test_main_with_output_file(self, tmp_path, monkeypatch):
        """main() with --output writes JSON to file."""
        out_file = tmp_path / "report.json"
        monkeypatch.setattr(
            "sys.argv",
            [
                "healer-metrics-analyzer",
                "--audit-dir", str(tmp_path),
                "--output", str(out_file),
            ],
        )
        _mod.main()
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "timestamp" in data

    def test_main_returns_zero(self, tmp_path, monkeypatch):
        """main() returns 0 on success."""
        monkeypatch.setattr(
            "sys.argv",
            ["healer-metrics-analyzer", "--audit-dir", str(tmp_path)],
        )
        result = _mod.main()
        assert result == 0
