"""
Agent Invocation SKILL — invoke_agent() implementation (task 5106)

Handles:
1. Agent subprocess invocation with task context
2. HANDBACK file polling until timeout
3. HANDBACK format validation (required fields)
4. SPAN data capture for observability
5. Error handling (agent crash, invalid HANDBACK, missing fields)
6. Timeout handling per effort level
7. Integration with Orchestrator.run_poll_cycle()

Design references:
- orchestration/SKILLS.md: SKILL: Agent Delegation (DELEGATE Transmission)
- orchestration/HANDOFF.md: HANDBACK block format and mandatory fields
- orchestration/SPAN-CAPTURE-INTEGRATION.md: OpenTelemetry SPAN schema
"""

import os
import signal
import subprocess
import time
import uuid
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.orchestration.monitoring.token_tracker import TokenTracker


# ─── Exceptions ──────────────────────────────────────────────────────────────


class HandbackValidationError(Exception):
    """
    Raised when a HANDBACK file is malformed or missing required fields.

    Attributes:
        missing_fields: List of field names absent from the HANDBACK.
    """

    def __init__(self, message: str, missing_fields: Optional[List[str]] = None):
        super().__init__(message)
        self.missing_fields: List[str] = missing_fields or []


# ─── AgentInvoker ────────────────────────────────────────────────────────────


class AgentInvoker:
    """
    Invoke agent subprocesses and poll for HANDBACK results.

    Implements the SKILL: Agent Delegation (DELEGATE Transmission) from SKILLS.md.

    Workflow:
        1. Write DELEGATE YAML to delegates_dir for reference
        2. Spawn agent subprocess (non-blocking Popen)
        3. Pass DELEGATE YAML via subprocess stdin + DELEGATE_PATH env var
        4. Poll processing_dir for ``{task_id}-HANDBACK-{role}.yaml`` every
           ``poll_interval`` seconds until timeout
        5. Validate HANDBACK on discovery; raise HandbackValidationError if invalid
        6. On timeout or crash → terminate process (SIGTERM → SIGKILL) and return
           a synthetic HANDBACK with status "blocked"
        7. Write OpenTelemetry-style SPAN file to spans_dir after each invocation

    Timeout limits by effort level (overridable via ``effort_timeouts``):
        low=30s, medium=120s, high=600s, max=3600s, epic=3600s
    """

    # Default wall-clock timeouts per effort level (seconds)
    EFFORT_TIMEOUTS: Dict[str, int] = {
        "low": 30,
        "medium": 120,
        "high": 600,
        "max": 3600,
        "epic": 3600,   # alias for max
    }

    # Mandatory HANDBACK fields per HANDOFF.md
    HANDBACK_REQUIRED_FIELDS: List[str] = [
        "handoff_type",
        "task_id",
        "status",
        "deliverables",
        "tests",
        "tokens_in",
        "tokens_out",
        "model",
        "effort",
        "duration_minutes",
    ]

    # Valid HANDBACK status values per HANDOFF.md
    VALID_HANDBACK_STATUSES = {"complete", "blocked", "partial"}

    # Default polling interval (seconds)
    DEFAULT_POLL_INTERVAL: int = 30

    # Seconds to wait for process to respond to SIGTERM before sending SIGKILL
    SIGTERM_WAIT: int = 5

    def __init__(
        self,
        processing_dir: Path,
        delegates_dir: Optional[Path] = None,
        spans_dir: Optional[Path] = None,
        poll_interval: Optional[int] = None,
        effort_timeouts: Optional[Dict[str, int]] = None,
        token_tracker: Optional["TokenTracker"] = None,
    ):
        """
        Args:
            processing_dir: Queue processing directory; polled for HANDBACK files.
            delegates_dir: Where DELEGATE YAML files are written for reference.
                           Defaults to ``<processing_dir>/../delegates``.
            spans_dir: Root directory for SPAN files.
                       Defaults to ``artifacts/``.
            poll_interval: Seconds between HANDBACK file checks. Defaults to 30.
            effort_timeouts: Override default per-effort-level timeouts.
                             Useful for tests with short timeouts.
            token_tracker: Optional TokenTracker instance for recording token metrics.
                          If provided, token metrics will be recorded for each real HANDBACK.
        """
        self.processing_dir = Path(processing_dir)
        self.delegates_dir = (
            Path(delegates_dir) if delegates_dir
            else self.processing_dir.parent / "delegates"
        )
        self.spans_dir = Path(spans_dir) if spans_dir else Path("artifacts")
        self.poll_interval = (
            poll_interval if poll_interval is not None else self.DEFAULT_POLL_INTERVAL
        )
        self.effort_timeouts: Dict[str, int] = effort_timeouts or dict(self.EFFORT_TIMEOUTS)
        self._token_tracker = token_tracker

        # Ensure directories exist
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.delegates_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def invoke_agent(
        self,
        delegate: Dict,
        agent_command: List[str],
    ) -> Dict:
        """
        Invoke an agent subprocess and poll for its HANDBACK result.

        The DELEGATE block is:
        * Written to ``delegates_dir/DELEGATE-{task_id}.yaml``
        * Passed to the subprocess via stdin (YAML-encoded)
        * Made available via the ``DELEGATE_PATH`` environment variable

        Polling:
        * Checks ``processing_dir/{task_id}-HANDBACK-{normalized_role}.yaml``
          every ``poll_interval`` seconds.
        * Role is normalised: "Senior Engineer" → "senior-engineer".

        Returns a real HANDBACK dict on success, or a synthetic one on
        timeout/crash.  The synthetic dict always has ``_synthetic=True``.

        Args:
            delegate: DELEGATE block (must contain ``task_id``, ``role``,
                      ``effort``).
            agent_command: Command list to spawn, e.g. ``['python3', 'agent.py']``.

        Returns:
            HANDBACK dict.

        Raises:
            HandbackValidationError: HANDBACK file has missing/invalid fields.
        """
        task_id = delegate.get("task_id", "unknown")
        role = delegate.get("role", "unknown")
        effort = delegate.get("effort", "medium")
        timeout = self.effort_timeouts.get(effort, self.effort_timeouts.get("medium", 120))

        # 1. Write DELEGATE file for reference
        delegate_path = self._write_delegate_file(task_id, delegate)

        # 2. Record SPAN start time
        span_start = datetime.now()

        # 3. Build environment with DELEGATE_PATH
        env = os.environ.copy()
        env["DELEGATE_PATH"] = str(delegate_path)

        # 4. Spawn subprocess (non-blocking)
        try:
            process = subprocess.Popen(
                agent_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
        except OSError as exc:
            span_end = datetime.now()
            handback = self._make_synthetic_handback(
                task_id=task_id,
                role=role,
                effort=effort,
                span_start=span_start,
                span_end=span_end,
                error=f"Agent invocation failed: {exc}",
            )
            self._write_span(delegate, handback, span_start, span_end, span_status="error")
            return handback

        # 5. Pass DELEGATE YAML via stdin
        delegate_yaml = yaml.dump(delegate, default_flow_style=False, sort_keys=False)
        try:
            process.stdin.write(delegate_yaml)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass  # Process may have already exited

        # 6. Log invocation metadata
        self._log_invocation(
            task_id, role, delegate.get("model"), effort, delegate_path, span_start
        )

        # 7. Determine expected HANDBACK file path
        normalized_role = role.lower().replace(" ", "-")
        handback_path = self.processing_dir / f"{task_id}-HANDBACK-{normalized_role}.yaml"

        # 8. Poll for HANDBACK
        deadline = time.time() + timeout
        handback: Optional[Dict] = None
        timed_out = False
        crashed = False

        while True:
            remaining = deadline - time.time()

            # Timeout check (must be first)
            if remaining <= 0:
                timed_out = True
                break

            # Check for HANDBACK file (may raise HandbackValidationError)
            if handback_path.exists():
                handback = self._read_and_validate_handback(handback_path, task_id)
                break

            # Check process state
            exit_code = process.poll()
            if exit_code is not None:
                # Process has exited — do one final HANDBACK check
                if handback_path.exists():
                    handback = self._read_and_validate_handback(handback_path, task_id)
                    break
                if exit_code != 0:
                    crashed = True
                    break
                # Exit code 0 but no HANDBACK yet — wait out the timeout
                # (process may still be flushing file writes)

            # Sleep up to the next poll interval, or until the deadline
            sleep_time = min(self.poll_interval, remaining)
            if sleep_time > 0:
                time.sleep(sleep_time)

        span_end = datetime.now()

        # 9. Build result and SPAN
        if handback is not None:
            span_status = "success"
        elif timed_out:
            self._terminate_process(process)
            handback = self._make_synthetic_handback(
                task_id=task_id,
                role=role,
                effort=effort,
                span_start=span_start,
                span_end=span_end,
                error=f"Agent timeout after {timeout}s (effort={effort})",
            )
            span_status = "deadline_exceeded"
        else:
            # Crashed or exit 0 with no HANDBACK
            exit_code = process.returncode
            stderr_text = ""
            try:
                stderr_text = process.stderr.read()[:500] if process.stderr else ""
            except Exception:
                pass
            if crashed:
                msg = f"Agent crashed (exit code {exit_code}): {stderr_text}"
            else:
                msg = f"Agent exited without HANDBACK (exit code {exit_code}): {stderr_text}"
            handback = self._make_synthetic_handback(
                task_id=task_id,
                role=role,
                effort=effort,
                span_start=span_start,
                span_end=span_end,
                error=msg,
            )
            span_status = "error"

        # 10. Ensure process is cleaned up
        if process.poll() is None:
            self._terminate_process(process)

        # 11. Write SPAN
        self._write_span(delegate, handback, span_start, span_end, span_status=span_status)

        # 12. Record token metrics if tracker is available and HANDBACK is real
        if self._token_tracker and not handback.get("_synthetic"):
            self._record_token_metrics(delegate, handback)

        return handback

    # ── Private helpers ───────────────────────────────────────────────────────

    def _write_delegate_file(self, task_id: str, delegate: Dict) -> Path:
        """Write DELEGATE YAML to delegates_dir and return the path."""
        self.delegates_dir.mkdir(parents=True, exist_ok=True)
        delegate_path = self.delegates_dir / f"DELEGATE-{task_id}.yaml"
        with open(delegate_path, "w") as f:
            yaml.dump(delegate, f, default_flow_style=False, sort_keys=False)
        return delegate_path

    def _read_and_validate_handback(
        self,
        handback_path: Path,
        expected_task_id: str,
    ) -> Dict:
        """
        Read and validate a HANDBACK YAML file.

        Raises:
            HandbackValidationError: File has invalid YAML, missing required
                fields, wrong handoff_type, mismatched task_id, invalid status,
                or non-integer token counts.
        """
        # Parse YAML
        try:
            content = handback_path.read_text()
            # Handle YAML documents with leading/trailing --- markers
            docs = [d.strip() for d in content.split("---") if d.strip()]
            raw = docs[0] if docs else content
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise HandbackValidationError(f"Invalid YAML in HANDBACK file: {exc}")

        if not isinstance(data, dict):
            raise HandbackValidationError(
                "HANDBACK file does not contain a YAML mapping (dict)"
            )

        # Check mandatory fields
        missing = [f for f in self.HANDBACK_REQUIRED_FIELDS if f not in data]
        if missing:
            raise HandbackValidationError(
                f"HANDBACK missing required fields: {missing}",
                missing_fields=missing,
            )

        # Validate handoff_type
        if data.get("handoff_type") != "HANDBACK":
            raise HandbackValidationError(
                f"Expected handoff_type='HANDBACK', got '{data.get('handoff_type')}'"
            )

        # Validate task_id matches the DELEGATE
        if data.get("task_id") != expected_task_id:
            raise HandbackValidationError(
                f"HANDBACK task_id '{data.get('task_id')}' does not match "
                f"expected '{expected_task_id}' (cross-task contamination guard)"
            )

        # Validate status is one of the canonical values
        status = data.get("status")
        if status not in self.VALID_HANDBACK_STATUSES:
            raise HandbackValidationError(
                f"Invalid HANDBACK status '{status}'. "
                f"Must be one of: {sorted(self.VALID_HANDBACK_STATUSES)}"
            )

        # Validate and coerce token counts to integers
        for field in ("tokens_in", "tokens_out"):
            value = data.get(field)
            if not isinstance(value, int):
                try:
                    data[field] = int(value)
                except (TypeError, ValueError):
                    raise HandbackValidationError(
                        f"HANDBACK field '{field}' must be an integer, got: {value!r}"
                    )

        return data

    def _make_synthetic_handback(
        self,
        task_id: str,
        role: str,
        effort: str,
        span_start: datetime,
        span_end: datetime,
        error: str,
    ) -> Dict:
        """
        Build a synthetic HANDBACK dict for timeout / crash / invocation-error cases.

        The dict is structurally complete (all required fields present) and
        marked with ``_synthetic=True`` so callers can distinguish it from a
        real agent HANDBACK.
        """
        duration_s = (span_end - span_start).total_seconds()
        return {
            "handoff_type": "HANDBACK",
            "task_id": task_id,
            "status": "blocked",
            "deliverables": [],
            "tests": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "model": "unknown",
            "effort": effort,
            "duration_minutes": round(duration_s / 60, 4),
            "escalations": 0,
            "blockers": [error],
            "notes": f"Synthetic HANDBACK generated by Orchestrator (role={role})",
            "_synthetic": True,
        }

    def _terminate_process(self, process: subprocess.Popen) -> None:
        """
        Terminate a subprocess gracefully: SIGTERM → wait SIGTERM_WAIT → SIGKILL.

        Silently ignores errors if the process has already exited.
        """
        try:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=self.SIGTERM_WAIT)
            except subprocess.TimeoutExpired:
                # Process ignored SIGTERM — escalate to SIGKILL
                process.send_signal(signal.SIGKILL)
                process.wait(timeout=5)
        except (ProcessLookupError, OSError):
            pass  # Process already gone

    def _log_invocation(
        self,
        task_id: str,
        role: str,
        model: Optional[str],
        effort: str,
        delegate_path: Path,
        start_time: datetime,
    ) -> None:
        """Print invocation metadata to stdout for audit logging."""
        print(
            f"   [invoke_agent] task_id={task_id} role={role} "
            f"model={model} effort={effort} "
            f"delegate_path={delegate_path} "
            f"start_time={start_time.isoformat()}"
        )

    def _write_span(
        self,
        delegate: Dict,
        handback: Dict,
        span_start: datetime,
        span_end: datetime,
        span_status: str = "success",
    ) -> Optional[Path]:
        """
        Write an OpenTelemetry-style SPAN YAML file.

        Path: ``{spans_dir}/{YYYY-MM-DD}/SPAN-{YYYYMMDD-HHMMSS}-{role}.yaml``

        Follows the schema in SPAN-CAPTURE-INTEGRATION.md:
        trace_id, span_id, span_name, start_time, end_time, duration_ms,
        status, attributes (task_id, agent_type, agent_model, tokens, cost, …).

        SPAN write failures are logged but never propagate to callers.
        """
        try:
            task_id = delegate.get("task_id", "unknown")
            role = delegate.get("role", "unknown")
            model = delegate.get("model", "unknown")
            effort = delegate.get("effort", "unknown")

            duration_ms = int((span_end - span_start).total_seconds() * 1000)
            tokens_in = handback.get("tokens_in", 0)
            tokens_out = handback.get("tokens_out", 0)

            span = {
                "trace_id": uuid.uuid4().hex,
                "span_id": uuid.uuid4().hex[:16],
                "span_name": (
                    f"agent.{role.lower().replace(' ', '_')}.execution"
                ),
                "start_time": span_start.isoformat(),
                "end_time": span_end.isoformat(),
                "duration_ms": duration_ms,
                "status": span_status,
                "attributes": {
                    "task_id": task_id,
                    "agent_type": role,
                    "agent_model": model,
                    "effort": effort,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "total_tokens": tokens_in + tokens_out,
                    "handback_status": handback.get("status", "unknown"),
                    "service_name": "agentic-engineers",
                },
            }

            date_str = span_start.strftime("%Y-%m-%d")
            timestamp_str = span_start.strftime("%Y%m%d-%H%M%S")
            normalized_role = role.lower().replace(" ", "-")

            date_dir = self.spans_dir / date_str
            date_dir.mkdir(parents=True, exist_ok=True)

            span_path = date_dir / f"SPAN-{timestamp_str}-{normalized_role}.yaml"
            with open(span_path, "w") as f:
                yaml.dump(span, f, default_flow_style=False, sort_keys=False)

            return span_path

        except Exception as exc:
            print(f"   [invoke_agent] Warning: Failed to write SPAN: {exc}")
            return None

    def _record_token_metrics(self, delegate: Dict, handback: Dict) -> None:
        """
        Record token metrics from a real HANDBACK to the TokenTracker.

        Extracts task_id, agent/role, tokens_in, tokens_out, tokens_cached,
        and cost_usd from the HANDBACK and records them via the tracker.

        This method is only called for real (non-synthetic) HANDBACKs.

        Args:
            delegate: DELEGATE block (contains task_id, role)
            handback: HANDBACK block (contains tokens_in, tokens_out, cost_usd, etc.)
        """
        try:
            task_id = delegate.get("task_id", "unknown")
            role = delegate.get("role", "unknown")
            
            # Normalize agent name: "Senior Engineer" → "senior-engineer"
            agent = role.lower().replace(" ", "-")
            
            # Extract token counts (defaults to 0 if missing)
            tokens_in = handback.get("tokens_in", 0)
            tokens_out = handback.get("tokens_out", 0)
            tokens_cached = handback.get("tokens_cached", 0)
            cost_usd = handback.get("cost_usd", 0.0)
            
            # Record the metrics
            self._token_tracker.record_task_tokens(
                task_id=task_id,
                agent=agent,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                cached_tokens=tokens_cached,
                cost_usd=cost_usd,
            )
        except Exception as exc:
            # Log but don't propagate — token tracking failures should not block
            print(f"   [invoke_agent] Warning: Failed to record token metrics: {exc}")
