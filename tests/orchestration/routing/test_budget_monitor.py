"""Tests for monitor_budgets and cost_dashboard scripts."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


# Skill scripts have a hyphenated parent package — import via importlib
mon = importlib.import_module("src.skills.cost-aggregation.scripts.monitor_budgets")
dash = importlib.import_module("src.skills.cost-aggregation.scripts.cost_dashboard")

BudgetMonitor = mon.BudgetMonitor
BudgetLevel = mon.BudgetLevel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def monitor() -> "BudgetMonitor":
    return BudgetMonitor.from_default_config()


# ---------------------------------------------------------------------------
# BudgetMonitor
# ---------------------------------------------------------------------------

class TestBudgetMonitorThresholds:
    def test_ok_at_low_usage(self, monitor):
        # engineer budget=1500, warn at 80% → 1200
        s = monitor.check("engineer", 600)
        assert s.level == BudgetLevel.OK
        assert s.budget == 1500
        assert s.tokens_used == 600
        assert s.pct == 40.0

    def test_warn_at_80_pct(self, monitor):
        s = monitor.check("engineer", 1200)  # exactly 80%
        assert s.level == BudgetLevel.WARN

    def test_error_at_100_pct(self, monitor):
        s = monitor.check("engineer", 1500)
        assert s.level == BudgetLevel.ERROR

    def test_escalate_at_120_pct(self, monitor):
        s = monitor.check("engineer", 1800)  # 120%
        assert s.level == BudgetLevel.ESCALATE
        assert s.escalated is True

    def test_security_uses_override_escalate_pct(self, monitor):
        # security budget=5000, override escalate_pct=150 → 7500
        s = monitor.check("security_engineer", 6000)  # 120% — under override
        assert s.level == BudgetLevel.ERROR  # not escalated due to override
        s2 = monitor.check("security_engineer", 7500)  # 150%
        assert s2.level == BudgetLevel.ESCALATE


class TestBudgetMonitorContracts:
    def test_unknown_role_raises(self, monitor):
        with pytest.raises(KeyError):
            monitor.check("not-a-role", 100)

    def test_negative_tokens_raises(self, monitor):
        with pytest.raises(ValueError):
            monitor.check("engineer", -1)

    def test_empty_init_rejected(self):
        with pytest.raises(ValueError):
            BudgetMonitor({})

    def test_status_as_dict_roundtrip(self, monitor):
        s = monitor.check("engineer", 100)
        d = s.as_dict()
        assert d["role"] == "engineer"
        assert d["level"] == "ok"
        assert d["tokens_used"] == 100


class TestBudgetMonitorBatch:
    def test_skips_malformed_records(self, monitor):
        records = [
            {"role": "engineer", "tokens_used": 500},
            {"role": "unknown_role", "tokens_used": 100},
            {"role": "engineer", "tokens_used": "not-a-number"},
            {"tokens_used": 100},  # missing role
            {"role": "engineer", "tokens": 700},  # alternate key name
        ]
        out = monitor.check_batch(records)
        # Only 2 valid: 500 and 700
        assert len(out) == 2
        assert all(s.role == "engineer" for s in out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestMonitorCLI:
    def test_role_tokens_ok(self, capsys):
        rc = mon.main(["--role", "engineer", "--tokens", "500"])
        assert rc == 0
        assert "[OK]" in capsys.readouterr().out

    def test_role_tokens_escalate_exits_nonzero(self, capsys):
        rc = mon.main(["--role", "engineer", "--tokens", "2000"])
        assert rc == 1
        assert "[ESCALATE]" in capsys.readouterr().out

    def test_json_output(self, capsys):
        rc = mon.main(["--role", "engineer", "--tokens", "100", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data[0]["role"] == "engineer"
        assert data[0]["level"] == "ok"

    def test_report_mode(self, tmp_path, capsys):
        p = tmp_path / "m.jsonl"
        p.write_text(
            json.dumps({"role": "engineer", "tokens_used": 500}) + "\n"
            + json.dumps({"role": "engineer", "tokens_used": 2000}) + "\n"
        )
        rc = mon.main(["--report", str(p)])
        assert rc == 1  # has an escalation
        out = capsys.readouterr().out
        assert "[OK]" in out
        assert "[ESCALATE]" in out

    def test_requires_role_or_report(self, capsys):
        with pytest.raises(SystemExit):
            mon.main([])


# ---------------------------------------------------------------------------
# cost_dashboard
# ---------------------------------------------------------------------------

class TestDashboardAggregate:
    def test_aggregate_groups_by_role(self, monitor):
        records = [
            {"role": "engineer", "tokens_used": 500},
            {"role": "engineer", "tokens_used": 1500},   # ERROR
            {"role": "engineer", "tokens_used": 2000},   # ESCALATE
            {"role": "lead_engineer", "tokens_used": 1800},
        ]
        agg = dash.aggregate(records, monitor)
        assert agg["engineer"].task_count == 3
        assert agg["engineer"].avg_tokens == pytest.approx((500 + 1500 + 2000) / 3, rel=0.01)
        assert agg["engineer"].over_budget_count == 2  # ERROR + ESCALATE
        assert agg["engineer"].escalations == 1
        assert agg["lead_engineer"].task_count == 1
        assert agg["lead_engineer"].escalations == 0

    def test_render_table_handles_empty(self, monitor):
        assert "no task records" in dash.render_table({}, monitor)


class TestDashboardCLI:
    def test_runs_against_jsonl(self, tmp_path, capsys):
        p = tmp_path / "m.jsonl"
        p.write_text(
            json.dumps({"role": "engineer", "tokens_used": 500}) + "\n"
            + json.dumps({"role": "engineer", "tokens_used": 800}) + "\n"
        )
        rc = dash.main(["--metrics", str(p)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "engineer" in out
        assert "tasks" in out

    def test_json_output(self, tmp_path, capsys):
        p = tmp_path / "m.jsonl"
        p.write_text(json.dumps({"role": "engineer", "tokens_used": 500}) + "\n")
        rc = dash.main(["--metrics", str(p), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["engineer"]["task_count"] == 1

    def test_escalation_exits_nonzero(self, tmp_path, capsys):
        p = tmp_path / "m.jsonl"
        p.write_text(json.dumps({"role": "engineer", "tokens_used": 2500}) + "\n")
        rc = dash.main(["--metrics", str(p)])
        assert rc == 1
