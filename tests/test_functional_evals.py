"""
Tests for the functional evals backend (harness_invoker + FunctionalEvalRunner).

These exercise the real-invocation backend's pure logic (DELEGATE construction,
HANDBACK extraction, protocol validation, grading, HANDBACK storage) WITHOUT
spawning real CLIs or making API calls — the harness invocation itself is
monkeypatched to return canned output.
"""

import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parents[1] / "src" / "skills" / "_meta" / "evaluation_framework"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import harness_invoker as hi  # noqa: E402
import framework as fw  # noqa: E402
from test_case import TestCase  # noqa: E402


# ---------------------------------------------------------------------------
# DELEGATE construction
# ---------------------------------------------------------------------------

def test_build_delegate_has_required_fields():
    d = hi.build_delegate("test-x-001", "Do a thing.", "copilot", "engineer", "sonnet")
    assert d["handoff_type"] == "DELEGATE"
    assert d["task_id"] == "test-x-001"
    assert d["agent"] == "engineer"
    assert d["prompt"] == "Do a thing."


def test_build_prompt_payload_includes_handback_instructions():
    d = hi.build_delegate("test-x-001", "Do a thing.", "copilot", "engineer", "sonnet")
    payload = hi.build_prompt_payload(d)
    assert "HANDBACK" in payload
    assert "```yaml" in payload
    assert "test-x-001" in payload


# ---------------------------------------------------------------------------
# HANDBACK extraction
# ---------------------------------------------------------------------------

VALID_HANDBACK_OUTPUT = """Here is my result.

```yaml
handoff_type: HANDBACK
task_id: test-x-001
status: success
output: Did the thing.
metrics:
  quality: 0.95
  tokens: 120
  cost: 0.01
  duration_seconds: 3
```
"""


def test_extract_valid_handback():
    hb, err = hi.extract_handback(VALID_HANDBACK_OUTPUT)
    assert err is None
    assert hb["task_id"] == "test-x-001"
    valid, errors = hi.validate_handback_block(hb)
    assert valid is True, errors


def test_extract_handback_invalid_schema():
    out = """```yaml
handoff_type: HANDBACK
task_id: test-x-001
status: done
output: x
metrics: {quality: 2.0, tokens: -1, cost: 0, duration_seconds: 0}
```"""
    hb, err = hi.extract_handback(out)
    assert err is None
    valid, errors = hi.validate_handback_block(hb)
    assert valid is False
    assert len(errors) >= 2


def test_extract_handback_missing():
    hb, err = hi.extract_handback("just prose, no yaml")
    assert hb is None
    assert err


def test_extract_handback_without_handoff_type_falls_back():
    out = """```yaml
task_id: test-x-001
status: success
output: ok
metrics: {quality: 0.9, tokens: 1, cost: 0, duration_seconds: 1}
```"""
    hb, err = hi.extract_handback(out)
    assert hb is not None
    assert hb["status"] == "success"


# ---------------------------------------------------------------------------
# Harness availability + cost
# ---------------------------------------------------------------------------

def test_harness_available_unknown():
    ok, reason = hi.harness_available("nope")
    assert ok is False
    assert "unknown" in reason


def test_estimate_cost_known_and_default():
    assert hi.estimate_cost_usd("haiku") < hi.estimate_cost_usd("opus")
    assert hi.estimate_cost_usd("mystery-model") == hi.DEFAULT_COST_ESTIMATE_USD


# ---------------------------------------------------------------------------
# invoke() dry-run does not execute anything
# ---------------------------------------------------------------------------

def test_invoke_dry_run_is_skipped():
    res = hi.invoke(
        test_id="t", prompt="p", harness="copilot", agent="engineer",
        model="sonnet", dry_run=True,
    )
    assert res.dry_run is True
    assert res.skipped is True
    assert res.output_text == ""


# ---------------------------------------------------------------------------
# FunctionalEvalRunner grading (harness monkeypatched)
# ---------------------------------------------------------------------------

def _test_case() -> TestCase:
    return TestCase(
        id="test-func-001",
        name="Functional test",
        harnesses=["copilot"],
        models=["sonnet"],
        prompt="Produce a HANDBACK.",
        expected_contains=["HANDBACK"],
        expected_not_contains=["ERROR"],
        timeout_seconds=10,
    )


def test_functional_runner_pass(monkeypatch, tmp_path):
    # Redirect HANDBACK storage to a temp dir.
    monkeypatch.setattr(fw, "HANDBACKS_DIR", tmp_path / "handbacks")

    def fake_invoke(**kwargs):
        hb, _ = hi.extract_handback(VALID_HANDBACK_OUTPUT)
        return hi.InvocationResult(
            harness=kwargs["harness"], agent=kwargs["agent"], model=kwargs["model"],
            output_text=VALID_HANDBACK_OUTPUT, handback=hb, valid=True, errors=[],
        )

    monkeypatch.setattr(hi, "invoke", fake_invoke)

    runner = fw.FunctionalEvalRunner(harness="copilot", agent="engineer", model="sonnet")
    res = runner.run_test(_test_case())

    assert res.passed is True
    assert res.valid_handback is True
    assert res.skipped is False
    # A HANDBACK artifact was written.
    assert Path(res.handback_path).exists()


def test_functional_runner_fail_on_invalid_handback(monkeypatch, tmp_path):
    monkeypatch.setattr(fw, "HANDBACKS_DIR", tmp_path / "handbacks")

    def fake_invoke(**kwargs):
        return hi.InvocationResult(
            harness=kwargs["harness"], agent=kwargs["agent"], model=kwargs["model"],
            output_text="HANDBACK but no valid block",
            handback={}, valid=False, errors=["status: required"],
        )

    monkeypatch.setattr(hi, "invoke", fake_invoke)

    runner = fw.FunctionalEvalRunner(harness="copilot")
    res = runner.run_test(_test_case())
    assert res.passed is False
    assert res.valid_handback is False


def test_functional_runner_fail_on_missing_assertion(monkeypatch, tmp_path):
    monkeypatch.setattr(fw, "HANDBACKS_DIR", tmp_path / "handbacks")

    def fake_invoke(**kwargs):
        # Valid HANDBACK, but output lacks the expected "HANDBACK" substring.
        hb = {
            "task_id": "test-func-001", "status": "success", "output": "ok",
            "metrics": {"quality": 0.9, "tokens": 1, "cost": 0.0, "duration_seconds": 1},
        }
        return hi.InvocationResult(
            harness=kwargs["harness"], agent=kwargs["agent"], model=kwargs["model"],
            output_text="no marker here", handback=hb, valid=True, errors=[],
        )

    monkeypatch.setattr(hi, "invoke", fake_invoke)

    runner = fw.FunctionalEvalRunner(harness="copilot")
    res = runner.run_test(_test_case())
    assert res.passed is False
    assert res.missing_assertions == ["HANDBACK"]


def test_functional_runner_skipped_when_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(fw, "HANDBACKS_DIR", tmp_path / "handbacks")

    def fake_invoke(**kwargs):
        return hi.InvocationResult(
            harness=kwargs["harness"], agent=kwargs["agent"], model=kwargs["model"],
            skipped=True, skipped_reason="CLI not found on PATH",
        )

    monkeypatch.setattr(hi, "invoke", fake_invoke)

    runner = fw.FunctionalEvalRunner(harness="copilot")
    res = runner.run_test(_test_case())
    assert res.skipped is True
    assert res.passed is False


# ---------------------------------------------------------------------------
# run_functional_evals end-to-end (dry run, no invocation)
# ---------------------------------------------------------------------------

def test_run_functional_evals_dry_run(capsys):
    tests_dir = Path(__file__).resolve().parents[1] / "tests" / "evals"
    rc = fw.run_functional_evals(
        tests_path=tests_dir, harness="copilot", model="sonnet",
        max_tests=1, dry_run=True,
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "Dry run complete" in out


# ---------------------------------------------------------------------------
# Legacy TestRunner stays hermetic (no real CLI) unless live
# ---------------------------------------------------------------------------

def test_legacy_invoke_harness_non_live_is_hermetic():
    runner = fw.TestRunner(live=False)
    output, error, tokens = runner._invoke_harness("copilot", "sonnet", "anything")
    assert "non-live" in output
    assert error == ""
    assert tokens == 0
