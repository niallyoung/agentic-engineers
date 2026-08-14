"""Tests for scripts/handback_rollup.py — the advisory HANDBACK cost/quality rollup.

Covers: happy path (single + multi-document), mixed roles, the `agent`/`role`
convention (including the "unknown" fallback), the deprecated `type: HANDBACK`
alias, malformed-input skip-with-warning behavior (invalid YAML, missing/invalid
required fields), DELEGATE blocks correctly ignored (not warned about), empty
input, --json output, CLI file + stdin handling, and a drift check that the
script's hardcoded Cost Target Distribution still matches docs/SPEC.md.
"""
from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.handback_rollup import (  # noqa: E402
    COST_TARGET_DISTRIBUTION,
    aggregate,
    iter_candidate_documents,
    main,
    parse_handbacks,
    render_json,
    render_table,
    validate_handback,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Fixtures — ~8+ representative HANDBACK inputs, including malformed ones.
# ---------------------------------------------------------------------------

FIXTURE_1_BARE_VALID = """
handoff_type: HANDBACK
task_id: fx1-engineer-task
status: success
agent: engineer
output: Implemented the thing.
metrics:
  quality: 0.92
  tokens: 1500
  cost: 0.04
  duration_seconds: 300
"""

FIXTURE_2_FENCED_VALID_ROLE_KEY = """
Some prose from a session transcript before the block.

```yaml
handoff_type: HANDBACK
task_id: fx2-senior-task
status: partial
role: senior-engineer
output: |
  Partially done, blocked on X.
metrics:
  quality: 0.6
  tokens: 4200
  cost: 0.15
  duration_seconds: 900
```

Some trailing prose after.
"""

FIXTURE_3_MULTI_DOC_MIXED_ROLES = """
---
handoff_type: HANDBACK
task_id: fx3-orch-task
status: success
agent: orchestrator
output: Routed correctly.
metrics:
  quality: 1.0
  tokens: 200
  cost: 0.01
  duration_seconds: 5
---
handoff_type: HANDBACK
task_id: fx3-qe-task
status: success
agent: quality-engineer
output: Verified success_criteria.
metrics:
  quality: 0.88
  tokens: 900
  cost: 0.03
  duration_seconds: 120
"""

FIXTURE_4_DEPRECATED_TYPE_ALIAS = """
type: HANDBACK
task_id: fx4-lead-task
status: success
agent: lead-engineer
output: Reviewed and approved.
metrics:
  quality: 0.95
  tokens: 600
  cost: 0.02
  duration_seconds: 60
"""

FIXTURE_5_MALFORMED_MISSING_METRICS = """
handoff_type: HANDBACK
task_id: fx5-broken-task
status: success
agent: engineer
output: Missing its metrics block entirely.
"""

FIXTURE_6_MALFORMED_INVALID_YAML = """
handoff_type: HANDBACK
task_id: fx6-broken-yaml
status: success
agent: engineer
output: [unterminated flow sequence
metrics:
  quality: 0.5
"""

FIXTURE_7_DELEGATE_MIXED_IN = """
---
handoff_type: DELEGATE
task_id: fx7-delegate-not-handback
agent: engineer
scope: >
  This is a DELEGATE block mixed into a transcript alongside HANDBACKs; it must
  be ignored by the rollup entirely, silently, with no warning raised about it.
plan:
  - "Step one of at least three words"
  - "Step two of at least three words"
success_criteria:
  - "AC1: done"
context: "Some context string that is at least twenty words long so it satisfies the DELEGATE context minimum word requirement here."
---
handoff_type: HANDBACK
task_id: fx7-handback-after
status: success
agent: engineer
output: Did the work described in the DELEGATE above.
metrics:
  quality: 0.85
  tokens: 800
  cost: 0.025
  duration_seconds: 90
"""

FIXTURE_8_NO_ROLE_FIELD = """
handoff_type: HANDBACK
task_id: fx8-no-role
status: blocked
output: No agent/role field present at all.
error: "budget: estimated 50000 exceeds limit 10000"
metrics:
  quality: 0.0
  tokens: 0
  cost: 0.0
  duration_seconds: 0
"""

FIXTURE_9_BAD_STATUS_ENUM = """
handoff_type: HANDBACK
task_id: fx9-bad-status
status: complete
agent: engineer
output: Uses a non-canonical status value.
metrics:
  quality: 0.9
  tokens: 100
  cost: 0.01
  duration_seconds: 10
"""

FIXTURE_10_QUALITY_OUT_OF_RANGE = """
handoff_type: HANDBACK
task_id: fx10-bad-quality
status: success
agent: engineer
output: Quality is out of the 0.0-1.0 range.
metrics:
  quality: 1.5
  tokens: 100
  cost: 0.01
  duration_seconds: 10
"""


# ---------------------------------------------------------------------------
# parse_handbacks / iter_candidate_documents
# ---------------------------------------------------------------------------

def test_bare_valid_handback_parsed():
    records, warnings = parse_handbacks(FIXTURE_1_BARE_VALID)
    assert warnings == []
    assert len(records) == 1
    r = records[0]
    assert r["task_id"] == "fx1-engineer-task"
    assert r["agent"] == "engineer"
    assert r["metrics"]["tokens"] == 1500
    assert r["metrics"]["cost"] == pytest.approx(0.04)


def test_fenced_valid_handback_with_role_key():
    records, warnings = parse_handbacks(FIXTURE_2_FENCED_VALID_ROLE_KEY)
    assert warnings == []
    assert len(records) == 1
    assert records[0]["agent"] == "senior-engineer"
    assert records[0]["status"] == "partial"


def test_multi_doc_mixed_roles():
    records, warnings = parse_handbacks(FIXTURE_3_MULTI_DOC_MIXED_ROLES)
    assert warnings == []
    assert len(records) == 2
    roles = {r["agent"] for r in records}
    assert roles == {"orchestrator", "quality-engineer"}


def test_deprecated_type_alias_recognized():
    records, warnings = parse_handbacks(FIXTURE_4_DEPRECATED_TYPE_ALIAS)
    assert warnings == []
    assert len(records) == 1
    assert records[0]["agent"] == "lead-engineer"


def test_malformed_missing_metrics_skipped_with_warning():
    records, warnings = parse_handbacks(FIXTURE_5_MALFORMED_MISSING_METRICS)
    assert records == []
    assert len(warnings) == 1
    assert "fx5-broken-task" in warnings[0]
    assert "metrics" in warnings[0]


def test_malformed_invalid_yaml_skipped_with_warning():
    records, warnings = parse_handbacks(FIXTURE_6_MALFORMED_INVALID_YAML, source="fixture6.yaml")
    assert records == []
    assert len(warnings) == 1
    assert "fixture6.yaml" in warnings[0]
    assert "invalid YAML" in warnings[0]


def test_delegate_block_ignored_silently():
    records, warnings = parse_handbacks(FIXTURE_7_DELEGATE_MIXED_IN)
    # Only the HANDBACK should be picked up; the DELEGATE produces no warning.
    assert len(records) == 1
    assert records[0]["task_id"] == "fx7-handback-after"
    assert warnings == []


def test_no_role_field_falls_back_to_unknown():
    records, warnings = parse_handbacks(FIXTURE_8_NO_ROLE_FIELD)
    assert warnings == []
    assert len(records) == 1
    assert records[0]["agent"] == "unknown"
    assert records[0]["status"] == "blocked"


def test_bad_status_enum_skipped_with_warning():
    records, warnings = parse_handbacks(FIXTURE_9_BAD_STATUS_ENUM)
    assert records == []
    assert len(warnings) == 1
    assert "status" in warnings[0]


def test_quality_out_of_range_skipped_with_warning():
    records, warnings = parse_handbacks(FIXTURE_10_QUALITY_OUT_OF_RANGE)
    assert records == []
    assert len(warnings) == 1
    assert "quality" in warnings[0]


def test_empty_input_produces_no_records_or_warnings():
    records, warnings = parse_handbacks("")
    assert records == []
    assert warnings == []


def test_prose_only_input_produces_no_records_or_warnings():
    records, warnings = parse_handbacks("Just some prose about handoff_type in general, no YAML at all.")
    assert records == []
    assert warnings == []


def test_iter_candidate_documents_finds_fenced_and_bare():
    combined = FIXTURE_1_BARE_VALID + "\n" + FIXTURE_2_FENCED_VALID_ROLE_KEY
    candidates = iter_candidate_documents(combined)
    assert len(candidates) == 2


# ---------------------------------------------------------------------------
# validate_handback
# ---------------------------------------------------------------------------

def test_validate_handback_accepts_well_formed():
    doc = {
        "task_id": "t1",
        "status": "success",
        "output": "done",
        "metrics": {"quality": 0.9, "tokens": 10, "cost": 0.01, "duration_seconds": 1},
    }
    assert validate_handback(doc) == []


def test_validate_handback_rejects_boolean_as_number():
    doc = {
        "task_id": "t1",
        "status": "success",
        "output": "done",
        "metrics": {"quality": True, "tokens": 10, "cost": 0.01, "duration_seconds": 1},
    }
    errors = validate_handback(doc)
    assert any("quality" in e for e in errors)


# ---------------------------------------------------------------------------
# aggregate / render_table / render_json
# ---------------------------------------------------------------------------

def test_aggregate_groups_by_role_and_computes_means():
    records, _ = parse_handbacks(FIXTURE_3_MULTI_DOC_MIXED_ROLES)
    stats = aggregate(records)
    assert set(stats.keys()) == {"orchestrator", "quality-engineer"}
    assert stats["orchestrator"]["count"] == 1
    assert stats["orchestrator"]["tokens"] == 200
    assert stats["orchestrator"]["quality_mean"] == pytest.approx(1.0)


def test_aggregate_multiple_records_same_role_means_correctly():
    records, _ = parse_handbacks(FIXTURE_1_BARE_VALID + "\n" + FIXTURE_7_DELEGATE_MIXED_IN)
    stats = aggregate(records)
    assert stats["engineer"]["count"] == 2
    assert stats["engineer"]["tokens"] == 1500 + 800
    assert stats["engineer"]["quality_mean"] == pytest.approx((0.92 + 0.85) / 2)


def test_render_table_empty_stats_does_not_crash():
    out = render_table({}, [])
    assert "no usable HANDBACK records found" in out


def test_render_table_includes_distribution_comparison():
    records, _ = parse_handbacks(FIXTURE_1_BARE_VALID)
    stats = aggregate(records)
    out = render_table(stats, [])
    assert "Cost Target Distribution comparison" in out
    assert "engineer" in out
    assert "18.0%" in out  # engineer's target share


def test_render_table_includes_warnings_section():
    records, warnings = parse_handbacks(FIXTURE_5_MALFORMED_MISSING_METRICS)
    out = render_table(aggregate(records), warnings)
    assert "Warnings" in out
    assert "fx5-broken-task" in out


def test_render_json_roundtrips_and_has_expected_shape():
    records, warnings = parse_handbacks(FIXTURE_3_MULTI_DOC_MIXED_ROLES)
    stats = aggregate(records)
    payload = json.loads(render_json(stats, warnings))
    assert payload["totals"]["count"] == 2
    assert "orchestrator" in payload["roles"]
    assert payload["roles"]["orchestrator"]["target_cost_pct"] == 55.0
    assert payload["warnings"] == []


# ---------------------------------------------------------------------------
# CLI (main)
# ---------------------------------------------------------------------------

def test_cli_reads_stdin_by_default(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(FIXTURE_1_BARE_VALID))
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "engineer" in out


def test_cli_reads_multiple_files(tmp_path, capsys):
    f1 = tmp_path / "a.yaml"
    f1.write_text(FIXTURE_1_BARE_VALID)
    f2 = tmp_path / "b.yaml"
    f2.write_text(FIXTURE_3_MULTI_DOC_MIXED_ROLES)
    rc = main([str(f1), str(f2)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "engineer" in out
    assert "orchestrator" in out
    assert "quality-engineer" in out


def test_cli_json_flag(tmp_path, capsys):
    f1 = tmp_path / "a.yaml"
    f1.write_text(FIXTURE_1_BARE_VALID)
    rc = main([str(f1), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "engineer" in payload["roles"]


def test_cli_missing_file_returns_nonzero(capsys):
    rc = main(["/nonexistent/path/does-not-exist.yaml"])
    assert rc == 2


def test_cli_never_exits_nonzero_for_malformed_content(tmp_path):
    f1 = tmp_path / "broken.yaml"
    f1.write_text(FIXTURE_6_MALFORMED_INVALID_YAML)
    rc = main([str(f1)])
    assert rc == 0  # advisory-only: bad content is reported, never gates


# ---------------------------------------------------------------------------
# Drift check: the script's hardcoded Cost Target Distribution must match
# docs/SPEC.md's live text, per the honesty requirement in the docstring.
# ---------------------------------------------------------------------------

def test_cost_target_distribution_matches_spec():
    spec_text = (REPO_ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")
    m = re.search(
        r"\*\*Cost Target Distribution:\*\*\s*(.+?)\.\s*\(Rebalanced",
        spec_text,
        re.DOTALL,
    )
    assert m is not None, (
        "docs/SPEC.md no longer contains a 'Cost Target Distribution' line in the "
        "expected format — scripts/handback_rollup.py's hardcoded "
        "COST_TARGET_DISTRIBUTION is now stale and should be updated (or the "
        "distribution comparison feature should be removed) to match."
    )
    pairs = re.findall(r"([A-Za-z ]+?)\s+(\d+(?:\.\d+)?)%", m.group(1))
    spec_distribution = {
        name.strip().lower().replace(" ", "-"): float(pct) for name, pct in pairs
    }
    assert spec_distribution == COST_TARGET_DISTRIBUTION
    assert sum(COST_TARGET_DISTRIBUTION.values()) == pytest.approx(100.0)
