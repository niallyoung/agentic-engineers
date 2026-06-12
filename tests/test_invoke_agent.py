"""
Test Suite for invoke_agent() SKILL (task 5106)

Tests the AgentInvoker class which handles:
1. Agent subprocess invocation with task context
2. HANDBACK file polling until timeout
3. HANDBACK format validation (required fields)
4. SPAN data capture for observability
5. Error handling (agent crash, invalid HANDBACK, missing fields)
6. Timeout handling per effort level

RED-GREEN-REFACTOR: Tests written first; initially fail.
"""

import os
import signal
import subprocess
import threading
import time
import uuid
import yaml
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict
from unittest.mock import patch, MagicMock, call


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temp directory structure for all tests."""
    processing = tmp_path / "processing"
    delegates = tmp_path / "delegates"
    spans = tmp_path / "spans"
    for d in [processing, delegates, spans]:
        d.mkdir(parents=True)
    return {
        "processing": processing,
        "delegates": delegates,
        "spans": spans,
        "base": tmp_path,
    }


def make_invoker(tmp_dirs, poll_interval=0.02, effort_timeouts=None):
    """Helper: create an AgentInvoker with fast settings for tests."""
    from src.orchestration.agents.invoke_agent import AgentInvoker
    return AgentInvoker(
        processing_dir=tmp_dirs["processing"],
        delegates_dir=tmp_dirs["delegates"],
        spans_dir=tmp_dirs["spans"],
        poll_interval=poll_interval,
        effort_timeouts=effort_timeouts or {
            "low": 0.2,
            "medium": 0.5,
            "high": 1.0,
            "max": 2.0,
            "epic": 2.0,
        },
    )


def make_delegate(
    task_id="2026-01-01-test-task",
    role="Engineer",
    effort="medium",
    model="claude-haiku-4.5",
) -> Dict:
    """Helper: create a minimal valid DELEGATE block."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": role,
        "model": model,
        "effort": effort,
        "scope": "Test scope; nothing out of scope",
        "context": ["File: test.py"],
        "plan": ["1. Write test", "2. Verify"],
        "success_criteria": ["Tests pass"],
    }


def make_valid_handback(task_id="2026-01-01-test-task", role="Engineer") -> Dict:
    """Helper: create a minimal valid HANDBACK block."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "complete",
        "deliverables": ["Modified: test.py"],
        "tests": [{"command": "make verify", "result": "PASS"}],
        "tokens_in": 1000,
        "tokens_out": 500,
        "model": "claude-haiku-4.5",
        "effort": "medium",
        "duration_minutes": 5,
        "escalations": 0,
    }


def write_handback_after_delay(handback_path: Path, handback: Dict, delay: float):
    """Helper: write HANDBACK file to path after a delay (in a thread).

    Uses an atomic write strategy: YAML is written to a sibling ``.tmp``
    file first, then ``os.replace()`` renames it to the final path.
    ``os.replace()`` is atomic on POSIX filesystems, so the poller will
    never observe an empty or partially-written HANDBACK file — the file
    either does not exist yet, or is complete.

    This prevents the TOCTOU race condition where:
      1. ``open(path, 'w')`` creates the file on disk (empty),
      2. the polling loop sees ``path.exists() == True``,
      3. ``read_text()`` returns ``""`` → ``yaml.safe_load("")`` → ``None``,
      4. ``isinstance(None, dict)`` is ``False`` → ``HandbackValidationError``.
    """
    def _write():
        time.sleep(delay)
        tmp_path = handback_path.with_suffix('.tmp')
        with open(tmp_path, 'w') as f:
            yaml.dump(handback, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, handback_path)  # atomic rename on POSIX
    t = threading.Thread(target=_write, daemon=True)
    t.start()
    return t


def mock_process(poll_return=None, returncode=None, stderr_text=""):
    """Helper: create a mock subprocess.Popen process."""
    proc = MagicMock()
    proc.poll.return_value = poll_return
    proc.returncode = returncode
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.stderr = MagicMock()
    proc.stderr.read.return_value = stderr_text
    proc.wait.return_value = None
    return proc


# ─── Imports Check ──────────────────────────────────────────────────────────

class TestImports:
    """Verify module imports correctly."""

    def test_module_importable(self):
        """invoke_agent module must be importable."""
        from src.orchestration.agents import invoke_agent  # noqa

    def test_agent_invoker_class_exists(self):
        """AgentInvoker class must exist."""
        from src.orchestration.agents.invoke_agent import AgentInvoker  # noqa

    def test_handback_validation_error_exists(self):
        """HandbackValidationError must exist."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError  # noqa


# ─── Happy Path ──────────────────────────────────────────────────────────────

class TestSuccessfulInvocation:
    """Tests for normal successful agent invocation."""

    def test_returns_handback_dict(self, tmp_dirs):
        """invoke_agent() returns a dict when HANDBACK file appears."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate()
        handback = make_valid_handback()

        # Normalized role in filename
        hb_path = tmp_dirs["processing"] / f"{delegate['task_id']}-HANDBACK-engineer.yaml"
        write_handback_after_delay(hb_path, handback, delay=0.05)

        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=None, returncode=None)
            mock_popen.return_value = proc

            result = invoker.invoke_agent(delegate, ["echo", "test"])

        assert isinstance(result, dict)
        assert result["task_id"] == delegate["task_id"]
        assert result["status"] == "complete"

    def test_returns_original_handback_fields(self, tmp_dirs):
        """All fields from HANDBACK file are returned."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate()
        handback = make_valid_handback()

        hb_path = tmp_dirs["processing"] / f"{delegate['task_id']}-HANDBACK-engineer.yaml"
        write_handback_after_delay(hb_path, handback, delay=0.05)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        for field in ["handoff_type", "task_id", "status", "tokens_in", "tokens_out", "model"]:
            assert field in result, f"Field '{field}' missing from result"

    def test_delegate_written_to_file(self, tmp_dirs):
        """DELEGATE YAML is written to delegates_dir."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-file-write-test")
        handback = make_valid_handback(task_id="2026-01-01-file-write-test")

        hb_path = (
            tmp_dirs["processing"]
            / f"2026-01-01-file-write-test-HANDBACK-engineer.yaml"
        )
        write_handback_after_delay(hb_path, handback, delay=0.05)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        delegate_file = tmp_dirs["delegates"] / "DELEGATE-2026-01-01-file-write-test.yaml"
        assert delegate_file.exists(), "DELEGATE file should be written to delegates_dir"

        with open(delegate_file) as f:
            data = yaml.safe_load(f)
        assert data["task_id"] == "2026-01-01-file-write-test"

    def test_delegate_path_env_var_set(self, tmp_dirs):
        """DELEGATE_PATH env var is passed to subprocess."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-env-test")
        handback = make_valid_handback(task_id="2026-01-01-env-test")

        hb_path = tmp_dirs["processing"] / "2026-01-01-env-test-HANDBACK-engineer.yaml"
        write_handback_after_delay(hb_path, handback, delay=0.05)

        captured_env = {}

        def capture_popen(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return mock_process(poll_return=None)

        with patch("subprocess.Popen", side_effect=capture_popen):
            invoker.invoke_agent(delegate, ["echo"])

        assert "DELEGATE_PATH" in captured_env
        assert "2026-01-01-env-test" in captured_env["DELEGATE_PATH"]

    def test_delegate_yaml_passed_via_stdin(self, tmp_dirs):
        """DELEGATE YAML content is written to process stdin."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-stdin-test")
        handback = make_valid_handback(task_id="2026-01-01-stdin-test")

        hb_path = tmp_dirs["processing"] / "2026-01-01-stdin-test-HANDBACK-engineer.yaml"
        write_handback_after_delay(hb_path, handback, delay=0.05)

        stdin_writes = []

        def capture_popen(cmd, **kwargs):
            proc = mock_process(poll_return=None)
            proc.stdin.write = lambda data: stdin_writes.append(data)
            proc.stdin.close = lambda: None
            return proc

        with patch("subprocess.Popen", side_effect=capture_popen):
            invoker.invoke_agent(delegate, ["echo"])

        assert len(stdin_writes) > 0, "DELEGATE YAML should be written to stdin"
        written_content = "".join(stdin_writes)
        parsed = yaml.safe_load(written_content)
        assert parsed["task_id"] == "2026-01-01-stdin-test"

    def test_role_with_spaces_normalized_in_filename(self, tmp_dirs):
        """Role like 'Senior Engineer' is normalized to 'senior-engineer' in HANDBACK filename."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(role="Senior Engineer", task_id="2026-01-01-senior-test")
        handback = make_valid_handback(task_id="2026-01-01-senior-test")

        # Filename should use 'senior-engineer' (lowercase, hyphenated)
        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-senior-test-HANDBACK-senior-engineer.yaml"
        )
        write_handback_after_delay(hb_path, handback, delay=0.05)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["status"] == "complete"

    def test_process_exit_zero_with_handback(self, tmp_dirs):
        """Process exits 0 and HANDBACK file exists → success."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-exit-zero")
        handback = make_valid_handback(task_id="2026-01-01-exit-zero")

        hb_path = tmp_dirs["processing"] / "2026-01-01-exit-zero-HANDBACK-engineer.yaml"
        # Write HANDBACK before process exits
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        # Process returns exit code 0
        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=0, returncode=0)
            mock_popen.return_value = proc
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["status"] == "complete"
        assert result.get("_synthetic") is not True


# ─── Error Handling: Agent Crash ─────────────────────────────────────────────

class TestAgentCrash:
    """Tests for agent subprocess crash scenarios."""

    def test_nonzero_exit_returns_synthetic_handback(self, tmp_dirs):
        """Non-zero exit code with no HANDBACK file → synthetic HANDBACK returned."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-crash-test")

        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=1, returncode=1, stderr_text="Fatal error")
            mock_popen.return_value = proc
            result = invoker.invoke_agent(delegate, ["false"])

        assert result["handoff_type"] == "HANDBACK"
        assert result["task_id"] == "2026-01-01-crash-test"
        assert result["status"] == "blocked"
        assert result.get("_synthetic") is True

    def test_crash_handback_includes_exit_code_info(self, tmp_dirs):
        """Synthetic HANDBACK blockers include exit code information."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-exit-code")

        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=127, returncode=127, stderr_text="command not found")
            mock_popen.return_value = proc
            result = invoker.invoke_agent(delegate, ["nonexistent"])

        blockers = result.get("blockers", [])
        assert len(blockers) > 0
        # Should mention exit code
        blocker_text = " ".join(str(b) for b in blockers)
        assert "127" in blocker_text or "crash" in blocker_text.lower()

    def test_crash_synthetic_has_all_required_fields(self, tmp_dirs):
        """Synthetic HANDBACK on crash has all required structure fields."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-crash-fields")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=2, returncode=2)
            result = invoker.invoke_agent(delegate, ["false"])

        # Synthetic HANDBACK must have these fields
        for field in ["handoff_type", "task_id", "status", "deliverables", "tests",
                      "tokens_in", "tokens_out", "model", "effort", "duration_minutes"]:
            assert field in result, f"Synthetic HANDBACK missing field: {field}"

    def test_command_not_found_returns_synthetic(self, tmp_dirs):
        """OSError (command not found) → synthetic HANDBACK returned."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-oserror")

        with patch("subprocess.Popen", side_effect=OSError("No such file or directory")):
            result = invoker.invoke_agent(delegate, ["nonexistent-command-xyz"])

        assert result["status"] == "blocked"
        assert result.get("_synthetic") is True
        blockers = result.get("blockers", [])
        assert len(blockers) > 0
        blocker_text = " ".join(str(b) for b in blockers)
        assert "invocation" in blocker_text.lower() or "failed" in blocker_text.lower()

    def test_command_not_found_writes_span(self, tmp_dirs):
        """OSError on invocation still writes SPAN with error status."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-oserror-span")

        with patch("subprocess.Popen", side_effect=OSError("No such file")):
            invoker.invoke_agent(delegate, ["nonexistent-xyz"])

        # SPAN files should exist in spans directory
        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        assert len(span_files) > 0, "SPAN file should be written even on OSError"


# ─── Timeout Handling ─────────────────────────────────────────────────────────

class TestTimeoutHandling:
    """Tests for timeout handling per effort level."""

    def test_timeout_returns_synthetic_handback(self, tmp_dirs):
        """Timeout with no HANDBACK file → synthetic HANDBACK returned."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-timeout", effort="medium")

        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=None, returncode=None)
            mock_popen.return_value = proc
            result = invoker.invoke_agent(delegate, ["sleep", "999"])

        assert result["status"] == "blocked"
        assert result.get("_synthetic") is True

    def test_timeout_synthetic_mentions_timeout(self, tmp_dirs):
        """Timeout synthetic HANDBACK blockers mention timeout."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-timeout-msg", effort="medium")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["sleep", "999"])

        blockers = result.get("blockers", [])
        assert len(blockers) > 0
        blocker_text = " ".join(str(b) for b in blockers)
        assert "timeout" in blocker_text.lower() or "medium" in blocker_text.lower()

    def test_timeout_sends_sigterm(self, tmp_dirs):
        """On timeout, SIGTERM is sent to process."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"low": 0.1})
        delegate = make_delegate(task_id="2026-01-01-sigterm", effort="low")

        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=None)
            # After wait(), process is considered done
            proc.wait.return_value = None
            mock_popen.return_value = proc
            invoker.invoke_agent(delegate, ["sleep", "999"])

        proc.send_signal.assert_called()
        # SIGTERM should be called
        sigterm_calls = [c for c in proc.send_signal.call_args_list
                         if c == call(signal.SIGTERM)]
        assert len(sigterm_calls) > 0, "SIGTERM should be sent on timeout"

    def test_timeout_escalates_to_sigkill(self, tmp_dirs):
        """If process doesn't exit after SIGTERM, SIGKILL is sent."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"low": 0.1})
        delegate = make_delegate(task_id="2026-01-01-sigkill", effort="low")

        with patch("subprocess.Popen") as mock_popen:
            proc = mock_process(poll_return=None)
            # First wait() times out (process ignores SIGTERM)
            proc.wait.side_effect = [
                subprocess.TimeoutExpired(cmd="test", timeout=5),
                None,  # Second wait() succeeds after SIGKILL
                None,  # Cleanup at end
            ]
            mock_popen.return_value = proc
            invoker.invoke_agent(delegate, ["sleep", "999"])

        # Verify both signals were sent
        # c[0][0] is the first positional arg (Python 3.7 compatible mock access)
        sent_signals = [c[0][0] for c in proc.send_signal.call_args_list]
        assert signal.SIGTERM in sent_signals, "SIGTERM should be sent"
        assert signal.SIGKILL in sent_signals, "SIGKILL should be sent after SIGTERM timeout"

    def test_effort_level_low_timeout(self, tmp_dirs):
        """Low effort = 30s timeout by default."""
        from src.orchestration.agents.invoke_agent import AgentInvoker
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
        )
        assert invoker.effort_timeouts["low"] == 30

    def test_effort_level_medium_timeout(self, tmp_dirs):
        """Medium effort = 120s timeout by default."""
        from src.orchestration.agents.invoke_agent import AgentInvoker
        invoker = AgentInvoker(processing_dir=tmp_dirs["processing"])
        assert invoker.effort_timeouts["medium"] == 120

    def test_effort_level_high_timeout(self, tmp_dirs):
        """High effort = 600s timeout by default."""
        from src.orchestration.agents.invoke_agent import AgentInvoker
        invoker = AgentInvoker(processing_dir=tmp_dirs["processing"])
        assert invoker.effort_timeouts["high"] == 600

    def test_effort_level_max_timeout(self, tmp_dirs):
        """Max effort = 3600s timeout by default."""
        from src.orchestration.agents.invoke_agent import AgentInvoker
        invoker = AgentInvoker(processing_dir=tmp_dirs["processing"])
        assert invoker.effort_timeouts["max"] == 3600

    def test_effort_level_epic_timeout(self, tmp_dirs):
        """Epic effort = 3600s timeout (alias for max)."""
        from src.orchestration.agents.invoke_agent import AgentInvoker
        invoker = AgentInvoker(processing_dir=tmp_dirs["processing"])
        assert invoker.effort_timeouts["epic"] == 3600

    def test_unknown_effort_uses_medium_default(self, tmp_dirs):
        """Unknown effort level falls back to medium timeout."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-unknown-effort", effort="unknown-effort-level")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        # Should not raise; should return synthetic HANDBACK
        assert result["status"] == "blocked"
        assert result.get("_synthetic") is True

    def test_timeout_span_has_deadline_exceeded_status(self, tmp_dirs):
        """SPAN written on timeout has 'deadline_exceeded' status."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-timeout-span", effort="medium")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["sleep", "999"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        assert len(span_files) > 0

        for span_file in span_files:
            with open(span_file) as f:
                span = yaml.safe_load(f)
            if span.get("attributes", {}).get("task_id") == "2026-01-01-timeout-span":
                assert span["status"] == "deadline_exceeded"
                break
        else:
            pytest.fail("No SPAN found for this task_id")


# ─── HANDBACK Validation ──────────────────────────────────────────────────────

class TestHandbackValidation:
    """Tests for HANDBACK file format validation."""

    def test_missing_field_raises_validation_error(self, tmp_dirs):
        """HANDBACK missing a required field raises HandbackValidationError."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-missing-field")

        # Create HANDBACK missing 'status'
        bad_handback = make_valid_handback(task_id="2026-01-01-missing-field")
        del bad_handback["status"]

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-missing-field-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(bad_handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError) as exc_info:
                invoker.invoke_agent(delegate, ["echo"])

        assert "status" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    def test_missing_field_error_lists_missing_fields(self, tmp_dirs):
        """HandbackValidationError.missing_fields lists the missing field names."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-list-missing")

        bad_handback = make_valid_handback(task_id="2026-01-01-list-missing")
        del bad_handback["tokens_in"]
        del bad_handback["tokens_out"]

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-list-missing-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(bad_handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError) as exc_info:
                invoker.invoke_agent(delegate, ["echo"])

        assert "tokens_in" in exc_info.value.missing_fields
        assert "tokens_out" in exc_info.value.missing_fields

    def test_invalid_status_raises_validation_error(self, tmp_dirs):
        """HANDBACK with invalid status (not complete/blocked/partial) raises error."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-bad-status")

        bad_handback = make_valid_handback(task_id="2026-01-01-bad-status")
        bad_handback["status"] = "completed"  # Invalid! (should be "complete")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-bad-status-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(bad_handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError):
                invoker.invoke_agent(delegate, ["echo"])

    def test_wrong_task_id_raises_validation_error(self, tmp_dirs):
        """HANDBACK with mismatched task_id raises HandbackValidationError."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-correct-id")

        # HANDBACK has a different task_id
        bad_handback = make_valid_handback(task_id="2026-01-01-WRONG-ID")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-correct-id-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(bad_handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError) as exc_info:
                invoker.invoke_agent(delegate, ["echo"])

        assert "task_id" in str(exc_info.value).lower() or "match" in str(exc_info.value).lower()

    def test_wrong_handoff_type_raises_validation_error(self, tmp_dirs):
        """HANDBACK with wrong handoff_type raises HandbackValidationError."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-wrong-type")

        bad_handback = make_valid_handback(task_id="2026-01-01-wrong-type")
        bad_handback["handoff_type"] = "DELEGATE"  # Wrong!

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-wrong-type-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(bad_handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError):
                invoker.invoke_agent(delegate, ["echo"])

    def test_invalid_yaml_raises_validation_error(self, tmp_dirs):
        """HANDBACK file with invalid YAML raises HandbackValidationError."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-bad-yaml")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-bad-yaml-HANDBACK-engineer.yaml"
        )
        hb_path.write_text("this: is: not: valid: yaml: {{{")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError):
                invoker.invoke_agent(delegate, ["echo"])

    def test_tokens_validated_as_integers(self, tmp_dirs):
        """tokens_in and tokens_out must be integers (or coercible to int)."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-token-int")

        handback = make_valid_handback(task_id="2026-01-01-token-int")
        handback["tokens_in"] = "1000"   # String that can be coerced
        handback["tokens_out"] = "500"

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-token-int-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["tokens_in"] == 1000
        assert result["tokens_out"] == 500

    def test_invalid_token_values_raise_error(self, tmp_dirs):
        """Non-numeric tokens_in raises HandbackValidationError."""
        from src.orchestration.agents.invoke_agent import HandbackValidationError
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-bad-tokens")

        handback = make_valid_handback(task_id="2026-01-01-bad-tokens")
        handback["tokens_in"] = "not-a-number"

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-bad-tokens-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            with pytest.raises(HandbackValidationError):
                invoker.invoke_agent(delegate, ["echo"])

    def test_all_valid_statuses_accepted(self, tmp_dirs):
        """All valid statuses (complete, blocked, partial, escalate) are accepted."""
        for status in ["complete", "blocked", "partial", "escalate"]:
            invoker = make_invoker(tmp_dirs)
            task_id = f"2026-01-01-status-{status}"
            delegate = make_delegate(task_id=task_id)

            handback = make_valid_handback(task_id=task_id)
            handback["status"] = status

            hb_path = (
                tmp_dirs["processing"]
                / f"{task_id}-HANDBACK-engineer.yaml"
            )
            with open(hb_path, 'w') as f:
                yaml.dump(handback, f)

            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = mock_process(poll_return=None)
                result = invoker.invoke_agent(delegate, ["echo"])

            assert result["status"] == status, f"Status '{status}' should be accepted"


# ─── SPAN Capture ─────────────────────────────────────────────────────────────

class TestSpanCapture:
    """Tests for SPAN data capture for observability."""

    def test_span_file_written_on_success(self, tmp_dirs):
        """SPAN file is written on successful HANDBACK."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-span-success")
        handback = make_valid_handback(task_id="2026-01-01-span-success")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-span-success-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        assert len(span_files) > 0, "SPAN file should be written on success"

    def test_span_file_written_on_crash(self, tmp_dirs):
        """SPAN file is written on agent crash with 'error' status."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-span-crash")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=1, returncode=1)
            invoker.invoke_agent(delegate, ["false"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        assert len(span_files) > 0

        span = yaml.safe_load(span_files[0].read_text())
        assert span.get("status") == "error"

    def test_span_has_required_fields(self, tmp_dirs):
        """SPAN file contains required OpenTelemetry fields."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-span-fields")
        handback = make_valid_handback(task_id="2026-01-01-span-fields")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-span-fields-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        assert len(span_files) > 0

        span = yaml.safe_load(span_files[0].read_text())
        for field in ["trace_id", "span_id", "span_name", "start_time", "end_time",
                      "duration_ms", "status", "attributes"]:
            assert field in span, f"SPAN missing required field: {field}"

    def test_span_attributes_include_task_metadata(self, tmp_dirs):
        """SPAN attributes include task_id, agent_type, model, tokens."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(
            task_id="2026-01-01-span-attrs",
            role="Senior Engineer",
            model="claude-sonnet-4.6",
        )
        handback = make_valid_handback(task_id="2026-01-01-span-attrs")
        handback["tokens_in"] = 2000
        handback["tokens_out"] = 800

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-span-attrs-HANDBACK-senior-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        span = yaml.safe_load(span_files[0].read_text())
        attrs = span["attributes"]

        assert attrs["task_id"] == "2026-01-01-span-attrs"
        assert attrs["agent_type"] == "Senior Engineer"
        assert attrs["agent_model"] == "claude-sonnet-4.6"
        assert attrs["tokens_in"] == 2000
        assert attrs["tokens_out"] == 800
        assert attrs["total_tokens"] == 2800

    def test_span_duration_ms_is_positive(self, tmp_dirs):
        """SPAN duration_ms is a positive integer."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-span-duration")
        handback = make_valid_handback(task_id="2026-01-01-span-duration")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-span-duration-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        span = yaml.safe_load(span_files[0].read_text())
        assert span["duration_ms"] >= 0
        assert isinstance(span["duration_ms"], int)

    def test_span_success_status_on_valid_handback(self, tmp_dirs):
        """SPAN has 'success' status when valid HANDBACK received."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-span-ok")
        handback = make_valid_handback(task_id="2026-01-01-span-ok")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-span-ok-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        span = yaml.safe_load(span_files[0].read_text())
        assert span["status"] == "success"

    def test_span_filename_includes_role(self, tmp_dirs):
        """SPAN filename includes normalized role name."""
        invoker = make_invoker(tmp_dirs)
        delegate = make_delegate(task_id="2026-01-01-span-role", role="Lead Engineer")
        handback = make_valid_handback(task_id="2026-01-01-span-role")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-span-role-HANDBACK-lead-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            invoker.invoke_agent(delegate, ["echo"])

        span_files = list(tmp_dirs["spans"].glob("**/*.yaml"))
        assert any("lead-engineer" in f.name for f in span_files), (
            "SPAN filename should include 'lead-engineer'"
        )


# ─── Synthetic HANDBACK Structure ────────────────────────────────────────────

class TestSyntheticHandback:
    """Tests for synthetic HANDBACK generated on error/timeout."""

    def test_synthetic_has_correct_task_id(self, tmp_dirs):
        """Synthetic HANDBACK has the correct task_id."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-synthetic-id", effort="medium")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["task_id"] == "2026-01-01-synthetic-id"

    def test_synthetic_has_correct_effort(self, tmp_dirs):
        """Synthetic HANDBACK preserves effort level."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"high": 0.1})
        delegate = make_delegate(task_id="2026-01-01-synthetic-effort", effort="high")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["effort"] == "high"

    def test_synthetic_duration_minutes_is_positive(self, tmp_dirs):
        """Synthetic HANDBACK duration_minutes is positive."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-synthetic-dur", effort="medium")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["duration_minutes"] >= 0

    def test_synthetic_marked_as_synthetic(self, tmp_dirs):
        """Synthetic HANDBACK has _synthetic=True marker."""
        invoker = make_invoker(tmp_dirs, effort_timeouts={"medium": 0.1})
        delegate = make_delegate(task_id="2026-01-01-synthetic-marker", effort="medium")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result.get("_synthetic") is True

    def test_synthetic_handback_type_is_handback(self, tmp_dirs):
        """Synthetic HANDBACK has handoff_type == 'HANDBACK'."""
        invoker = make_invoker(tmp_dirs)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=1, returncode=1)
            result = invoker.invoke_agent(
                make_delegate(task_id="2026-01-01-synthetic-type"), ["false"]
            )

        assert result["handoff_type"] == "HANDBACK"


# ─── Polling Mechanics ────────────────────────────────────────────────────────

class TestPollingMechanics:
    """Tests for HANDBACK file polling behavior."""

    def test_polls_for_handback_file(self, tmp_dirs):
        """Invoker actively polls for HANDBACK file until it appears."""
        invoker = make_invoker(tmp_dirs, poll_interval=0.02,
                               effort_timeouts={"medium": 5.0})
        delegate = make_delegate(task_id="2026-01-01-poll-test", effort="medium")
        handback = make_valid_handback(task_id="2026-01-01-poll-test")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-poll-test-HANDBACK-engineer.yaml"
        )
        # Write HANDBACK after 0.1s (invoker polls every 0.02s so will find it quickly)
        write_handback_after_delay(hb_path, handback, delay=0.1)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["status"] == "complete"

    def test_handback_found_before_process_exits(self, tmp_dirs):
        """HANDBACK can be found while process is still running."""
        invoker = make_invoker(tmp_dirs, poll_interval=0.02,
                               effort_timeouts={"medium": 5.0})
        delegate = make_delegate(task_id="2026-01-01-early-hb", effort="medium")
        handback = make_valid_handback(task_id="2026-01-01-early-hb")

        hb_path = (
            tmp_dirs["processing"]
            / "2026-01-01-early-hb-HANDBACK-engineer.yaml"
        )
        with open(hb_path, 'w') as f:
            yaml.dump(handback, f)

        # Process is still running (poll returns None)
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            result = invoker.invoke_agent(delegate, ["echo"])

        assert result["status"] == "complete"
        assert not result.get("_synthetic")


# ─── Orchestrator Integration ─────────────────────────────────────────────────

@pytest.mark.skip(
    reason="Queue-isolation dependent tests (requires proper setup). "
           "See tests/test_queue_path_centralization.py for canonical path tests."
)
class TestOrchestratorIntegration:
    """Tests for integration with OrchestratorAgent.run_poll_cycle().
    
    ⚠️ DEPENDENT ON QUEUE-ISOLATION
    These tests require queue-isolation to be properly initialized. As of 2026-05-26,
    the queue infrastructure requires queue-isolation skill for canonical path support.
    """

    def test_orchestrator_has_run_poll_cycle_method(self):
        """OrchestratorAgent must have run_poll_cycle() method."""
        from src.orchestration.agents.orchestrator import OrchestratorAgent
        assert hasattr(OrchestratorAgent, "run_poll_cycle"), (
            "OrchestratorAgent must have run_poll_cycle() method"
        )

    def test_orchestrator_run_poll_cycle_returns_dict(self, tmp_dirs):
        """run_poll_cycle() returns a dict with metrics."""
        from src.orchestration.agents.orchestrator import OrchestratorAgent
        agent = OrchestratorAgent(queue_dir=str(tmp_dirs["base"]))
        result = agent.run_poll_cycle()
        assert isinstance(result, dict)

    def test_orchestrator_run_poll_cycle_empty_queue(self, tmp_dirs):
        """run_poll_cycle() with empty queue returns tasks_processed=0."""
        from src.orchestration.agents.orchestrator import OrchestratorAgent
        agent = OrchestratorAgent(queue_dir=str(tmp_dirs["base"]))
        result = agent.run_poll_cycle()
        assert result.get("tasks_processed", 0) == 0

    def test_orchestrator_accepts_agent_invoker(self, tmp_dirs):
        """OrchestratorAgent accepts optional AgentInvoker in constructor."""
        from src.orchestration.agents.orchestrator import OrchestratorAgent
        from src.orchestration.agents.invoke_agent import AgentInvoker
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
        )
        # Should not raise
        agent = OrchestratorAgent(
            queue_dir=str(tmp_dirs["base"]),
            agent_invoker=invoker,
        )
        assert agent.agent_invoker is invoker


# ─── Concurrent Invocations ───────────────────────────────────────────────────

class TestConcurrentInvocations:
    """Tests for concurrent agent invocations."""

    def test_concurrent_invocations_independent_files(self, tmp_dirs):
        """Multiple concurrent invocations work with separate HANDBACK files.

        NOTE: patch("subprocess.Popen") is applied at the method scope (not
        inside threads) to prevent mock-stack corruption.  unittest.mock.patch
        mutates global state; using it concurrently inside threads produces
        non-deterministic un-patching that leaks the mock into later tests.
        """
        invoker = make_invoker(tmp_dirs, poll_interval=0.02,
                               effort_timeouts={"medium": 5.0})
        results = []
        errors = []

        def invoke_one(task_id):
            try:
                delegate = make_delegate(task_id=task_id, effort="medium")
                handback = make_valid_handback(task_id=task_id)

                hb_path = (
                    tmp_dirs["processing"]
                    / f"{task_id}-HANDBACK-engineer.yaml"
                )
                write_handback_after_delay(hb_path, handback, delay=0.05)

                # subprocess.Popen is already patched at the outer scope —
                # do NOT nest another patch() inside a thread.
                result = invoker.invoke_agent(delegate, ["echo"])
                results.append(result)
            except Exception as e:
                errors.append(e)

        task_ids = [f"2026-01-01-concurrent-{i}" for i in range(3)]

        # Patch once at the method level so the mock stack is restored
        # cleanly after *all* threads have finished.
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process(poll_return=None)
            threads = [threading.Thread(target=invoke_one, args=(tid,))
                       for tid in task_ids]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert len(errors) == 0, f"Concurrent invocations raised errors: {errors}"
        assert len(results) == 3
        for r in results:
            assert r["status"] == "complete"
