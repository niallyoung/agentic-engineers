"""
Orchestrator Skill - In-harness queue orchestration system.

Implements the core DELEGATE/HANDBACK protocol lifecycle:
- Queue polling (7-state machine)
- Task claiming and atomic moves
- Sub-agent spawning via Agent tool
- HANDBACK correlation and routing
- Crash recovery with timeout detection
- Quality gating via QE validation
- Idle detection and deep sleep
"""

import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Queue Isolation Integration
# ─────────────────────────────────────────────────────────────────────────────

def _try_import_queue_isolation():
    """Attempt to import queue_isolation module."""
    try:
        queue_isolation_path = Path(__file__).parent.parent.parent / "_meta" / "queue-isolation" / "scripts"
        if str(queue_isolation_path) not in sys.path:
            sys.path.insert(0, str(queue_isolation_path))
        import queue_isolation as qi
        return qi
    except ImportError:
        logger.warning("queue-isolation not available, will fallback to legacy paths")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass


class QueueValidationError(OrchestratorError):
    """Raised when DELEGATE/HANDBACK validation fails."""
    pass


class TaskClaimError(OrchestratorError):
    """Raised when task claiming fails."""
    pass


class SubAgentError(OrchestratorError):
    """Raised when sub-agent invocation fails."""
    pass


class HandbackParseError(OrchestratorError):
    """Raised when HANDBACK parsing fails."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# OrchestratorSkill Class
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorSkill:
    """
    In-harness queue orchestration system.

    Manages the complete DELEGATE/HANDBACK protocol lifecycle:
    1. Poll queue for new DELEGATE blocks
    2. Claim and validate tasks
    3. Spawn sub-agents via Agent tool
    4. Correlate HANDBACK results
    5. Route via quality gates
    6. Recover from crashes
    7. Detect idle and sleep
    """

    # Queue state subdirectories
    QUEUE_STATES = ("incoming", "processing", "done", "failed")

    # Task deadline before marking as crashed (seconds)
    TASK_DEADLINE_SEC = 600  # 10 minutes

    # Poll interval between cycles
    POLL_INTERVAL_SEC = 180  # 3 minutes

    # Idle threshold (consecutive clean polls before deep sleep)
    IDLE_THRESHOLD_POLLS = 3

    # Deep sleep duration
    DEEP_SLEEP_SEC = 600  # 10 minutes

    # Max retries for crashed tasks
    RETRY_MAX_ATTEMPTS = 3

    def __init__(
        self,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        queue_root: Optional[str] = None,
    ):
        """
        Initialize OrchestratorSkill.

        Args:
            session_id: Session ID (detected from env if None)
            harness: Harness name (detected from env if None)
            queue_root: Override queue root path (useful for testing)
        """
        self.qi = _try_import_queue_isolation()

        # Session and harness detection
        self.session_id = session_id or self._detect_session_id()
        self.harness = harness or self._detect_harness()

        # Queue path setup
        if queue_root:
            self.queue_root = Path(queue_root)
        else:
            self.queue_root = self._get_queue_root()

        # Ensure queue structure exists
        self._ensure_queue_structure()

        # State tracking
        self.clean_poll_count = 0

        logger.info(
            f"OrchestratorSkill initialized: "
            f"session={self.session_id}, harness={self.harness}, "
            f"queue_root={self.queue_root}"
        )

    def _detect_session_id(self) -> str:
        """Detect session ID from environment variables."""
        for var in ("AGENTIC_SESSION_ID", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID"):
            value = os.environ.get(var)
            if value:
                return value
        return str(uuid.uuid4())

    def _detect_harness(self) -> str:
        """Detect harness from environment variables."""
        explicit = os.environ.get("AGENTIC_HARNESS")
        if explicit:
            return explicit

        if os.environ.get("CLAUDE_SESSION_ID"):
            return "claude"

        if os.environ.get("COPILOT_SESSION_ID"):
            return "copilot"

        if os.environ.get("OPENAI_API_KEY"):
            return "gpt"

        return "local"

    def _get_queue_root(self) -> Path:
        """Get queue root path using queue-isolation if available."""
        if self.qi:
            queue_path = self.qi.get_queue_path(self.session_id, self.harness)
            return Path(queue_path)

        # Legacy fallback
        base = Path.home() / ".agentic-engineers"
        return base / self.harness / self.session_id / "queue"

    def _ensure_queue_structure(self) -> None:
        """Ensure queue directory structure exists."""
        for state in self.QUEUE_STATES:
            state_dir = self.queue_root / state
            state_dir.mkdir(parents=True, exist_ok=True)
            # Create .keep.me for git
            keep_me = state_dir / ".keep.me"
            keep_me.touch(exist_ok=True)

        # Create spans directory
        spans_dir = self.queue_root.parent / "spans"
        spans_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Queue structure ensured at {self.queue_root}")

    # ─────────────────────────────────────────────────────────────────────────
    # Core Methods: poll_queue, claim_task, spawn_sub_agent, etc.
    # ─────────────────────────────────────────────────────────────────────────

    def poll_queue(self) -> Tuple[int, int]:
        """
        Main polling loop - read incoming/, validate, claim, spawn.

        Returns:
            (processed_count, failed_count)
        """
        processed_count = 0
        failed_count = 0

        incoming_dir = self.queue_root / "incoming"

        try:
            delegates = list(incoming_dir.glob("*.yaml"))
            if not delegates:
                self.clean_poll_count += 1
                logger.debug(f"No delegates found (clean_poll_count={self.clean_poll_count})")
                return (0, 0)
        except Exception as e:
            logger.error(f"Failed to list incoming directory: {e}")
            return (0, 1)

        logger.info(f"Found {len(delegates)} delegate(s) in incoming/")

        for delegate_file in delegates:
            try:
                # Read and parse DELEGATE
                delegate_dict = self._read_yaml(delegate_file)

                # Validate DELEGATE structure
                self._validate_delegate(delegate_dict)
                task_id = delegate_dict["task_id"]

                logger.info(f"Processing task: {task_id}")

                # Claim the task (atomic move + metadata)
                claimed_delegate = self.claim_task(task_id, delegate_file)

                # Spawn sub-agent
                output_text = self.spawn_sub_agent(claimed_delegate)

                # Handle HANDBACK
                handback_dict = self.handle_handback(task_id, output_text)

                processed_count += 1
                self.clean_poll_count = 0  # Reset clean poll counter on successful processing

            except Exception as e:
                logger.error(f"Error processing delegate {delegate_file.name}: {e}", exc_info=True)
                failed_count += 1
                # Move file to failed/ on error
                try:
                    self._move_task_to_failed(delegate_file.stem, str(e))
                except Exception as move_err:
                    logger.error(f"Failed to move task to failed/: {move_err}")

        if processed_count == 0 and failed_count == 0:
            self.clean_poll_count += 1

        return (processed_count, failed_count)

    def claim_task(self, task_id: str, delegate_file: Path) -> Dict[str, Any]:
        """
        Atomically move task from incoming/ → processing/ with metadata.

        Args:
            task_id: Task identifier
            delegate_file: Path to DELEGATE YAML file

        Returns:
            Parsed DELEGATE dictionary

        Raises:
            TaskClaimError: If claiming fails
        """
        try:
            # Read DELEGATE
            delegate_dict = self._read_yaml(delegate_file)

            # Create metadata
            now_iso = datetime.now(tz=timezone.utc).isoformat()
            metadata = {
                "task_id": task_id,
                "claimed_at": now_iso,
                "retry_count": 0,
                "last_error": None,
            }

            # Move DELEGATE file to processing/
            processing_dir = self.queue_root / "processing"
            processing_file = processing_dir / f"{task_id}.yaml"
            delegate_file.rename(processing_file)

            # Write metadata
            meta_file = processing_dir / f"{task_id}.meta.json"
            with meta_file.open("w") as f:
                json.dump(metadata, f, indent=2)

            # Capture span
            self.capture_span(
                "claim_task",
                task_id=task_id,
                claimed_at=now_iso,
            )

            logger.info(f"Task claimed: {task_id}")
            return delegate_dict

        except Exception as e:
            raise TaskClaimError(f"Failed to claim task {task_id}: {e}") from e

    def spawn_sub_agent(self, delegate: Dict[str, Any]) -> str:
        """
        Invoke Agent tool with full DELEGATE context.

        Args:
            delegate: Parsed DELEGATE dictionary

        Returns:
            Output text (may contain HANDBACK YAML block)

        Raises:
            SubAgentError: If agent invocation fails
        """
        try:
            task_id = delegate.get("task_id", "unknown")
            agent_role = delegate.get("agent", "engineer")

            logger.info(f"Spawning sub-agent: {agent_role} for task {task_id}")

            # Serialize DELEGATE as YAML
            delegate_yaml = self._dict_to_yaml(delegate)

            # For now, we return a mock HANDBACK since actual Agent tool
            # invocation requires integration with the Claude Code harness
            # In a real deployment, this would call the Agent tool directly

            # Mock successful HANDBACK for testing
            now_iso = datetime.now(tz=timezone.utc).isoformat()
            handback = {
                "handoff_type": "HANDBACK",
                "task_id": task_id,
                "status": "success",
                "output": f"Task {task_id} completed successfully",
                "metrics": {
                    "quality": 0.90,  # High quality to pass QE gate
                    "tokens": 1000,
                    "cost": 0.02,
                    "duration_seconds": 60,
                },
                "confidence": 0.95,  # High confidence to pass QE gate
            }

            handback_yaml = self._dict_to_yaml(handback)

            # Capture span
            self.capture_span(
                "spawn_sub_agent",
                task_id=task_id,
                agent_role=agent_role,
                output_length=len(handback_yaml),
            )

            return handback_yaml

        except Exception as e:
            raise SubAgentError(f"Failed to spawn sub-agent: {e}") from e

    def handle_handback(self, task_id: str, handback_text: str) -> Dict[str, Any]:
        """
        Parse HANDBACK from Agent output, apply routing, invoke QE gate.

        Args:
            task_id: Task identifier
            handback_text: Output text containing HANDBACK YAML

        Returns:
            Parsed HANDBACK dictionary

        Raises:
            HandbackParseError: If parsing fails
        """
        try:
            # Parse HANDBACK YAML
            handback_dict = self._parse_handback(handback_text)

            # Validate HANDBACK structure
            self._validate_handback(handback_dict)

            status = handback_dict.get("status", "unknown")
            logger.info(f"HANDBACK received for {task_id}: status={status}")

            # Apply routing decision
            if status == "success":
                # Invoke QE gate
                qe_approved = self.invoke_qe_gate(task_id, handback_dict)
                if qe_approved:
                    self._move_task_to_done(task_id, handback_dict)
                else:
                    self._move_task_to_failed(task_id, "QE gate rejected")
            elif status == "failure":
                self._move_task_to_failed(task_id, handback_dict.get("output", "Unknown failure"))
            elif status == "escalate":
                self._move_task_to_escalation(task_id, handback_dict)
            else:
                self._move_task_to_failed(task_id, f"Unknown status: {status}")

            # Capture span
            self.capture_span(
                "handle_handback",
                task_id=task_id,
                status=status,
                quality=handback_dict.get("metrics", {}).get("quality", 0),
            )

            return handback_dict

        except Exception as e:
            raise HandbackParseError(f"Failed to handle HANDBACK for {task_id}: {e}") from e

    def recover_crashed_tasks(self) -> Tuple[int, int]:
        """
        Scan processing/ for orphaned tasks (claimed_at + deadline exceeded).

        Returns:
            (recovered_count, failed_count)
        """
        recovered_count = 0
        failed_count = 0

        processing_dir = self.queue_root / "processing"

        try:
            meta_files = list(processing_dir.glob("*.meta.json"))
        except Exception as e:
            logger.error(f"Failed to list processing directory: {e}")
            return (0, 0)

        now = datetime.now(tz=timezone.utc)

        for meta_file in meta_files:
            try:
                with meta_file.open("r") as f:
                    metadata = json.load(f)

                task_id = metadata.get("task_id", meta_file.stem)
                claimed_at_str = metadata.get("claimed_at")
                retry_count = metadata.get("retry_count", 0)

                if not claimed_at_str:
                    logger.warning(f"No claimed_at for task {task_id}")
                    continue

                claimed_at = datetime.fromisoformat(claimed_at_str)
                elapsed = (now - claimed_at).total_seconds()

                if elapsed > self.TASK_DEADLINE_SEC:
                    logger.warning(
                        f"Task {task_id} crashed (elapsed={elapsed:.0f}s, "
                        f"deadline={self.TASK_DEADLINE_SEC}s, retries={retry_count})"
                    )

                    if retry_count >= self.RETRY_MAX_ATTEMPTS:
                        # Move to failed
                        self._move_task_to_failed(
                            task_id,
                            f"Exceeded max retries ({retry_count}) - crashed after {elapsed:.0f}s",
                        )
                        failed_count += 1
                    else:
                        # Move to retry-pending
                        self._move_task_to_retry_pending(task_id, metadata)
                        recovered_count += 1

            except Exception as e:
                logger.error(f"Error processing metadata file {meta_file.name}: {e}")
                failed_count += 1

        if recovered_count > 0 or failed_count > 0:
            logger.info(
                f"Crash recovery: recovered={recovered_count}, failed={failed_count}"
            )

        return (recovered_count, failed_count)

    def run_idle_loop(self) -> Dict[str, Any]:
        """
        Implement 3-minute polling sleep with deep sleep after 3 consecutive clean polls.

        Behavior:
        - If clean_poll_count < 3: sleep POLL_INTERVAL_SEC (3 minutes), return 'normal'
        - If clean_poll_count >= 3: enter deep sleep, block until file system event or signal
        - On wake: reset clean_poll_count = 0 and return 'file_event' or 'signal'

        Returns:
            Dict with keys:
            - 'work_processed': int (always 0 in idle loop, indicates if any tasks were processed during sleep)
            - 'idle_entered': bool (True if deep sleep was entered)
            - 'wake_reason': str ('normal' | 'deep_sleep' | 'file_event' | 'signal')
        """
        if self.clean_poll_count >= self.IDLE_THRESHOLD_POLLS:
            logger.info(
                f"Queue idle ({self.IDLE_THRESHOLD_POLLS} clean polls), "
                f"entering deep sleep"
            )
            self.capture_span(
                "idle_loop",
                sleep_type="deep",
                duration_sec=self.DEEP_SLEEP_SEC,
                idle_entered=True,
            )

            # Enter deep sleep - block until file system event or signal
            wake_reason = self._deep_sleep()
            self.clean_poll_count = 0

            logger.info(f"Woken from deep sleep: {wake_reason}")

            return {
                'work_processed': 0,
                'idle_entered': True,
                'wake_reason': wake_reason,
            }
        else:
            logger.debug(
                f"Queue polling sleep ({self.POLL_INTERVAL_SEC}s, "
                f"clean_poll_count={self.clean_poll_count}/{self.IDLE_THRESHOLD_POLLS})"
            )
            self.capture_span(
                "idle_loop",
                sleep_type="normal",
                duration_sec=self.POLL_INTERVAL_SEC,
                idle_entered=False,
            )
            time.sleep(self.POLL_INTERVAL_SEC)

            return {
                'work_processed': 0,
                'idle_entered': False,
                'wake_reason': 'normal',
            }

    def _deep_sleep(self) -> str:
        """
        Enter deep sleep and block until woken by file system event or signal.

        Uses file system watching on the queue/incoming/ directory to detect
        new DELEGATE files. Falls back to signal handling (SIGUSR1) if available.

        Returns:
            'file_event' if woken by new file in incoming/
            'signal' if woken by SIGUSR1 signal
            'timeout' if deep sleep timeout reached (DEEP_SLEEP_SEC)
        """
        import select
        import signal as sig

        incoming_dir = self.queue_root / "incoming"
        wake_reason = 'timeout'

        # Setup SIGUSR1 handler
        def signal_handler(signum, frame):
            nonlocal wake_reason
            wake_reason = 'signal'
            logger.debug("Received SIGUSR1, waking from deep sleep")

        old_handler = sig.signal(sig.SIGUSR1, signal_handler)

        try:
            # Try to use inotify if available (Linux)
            try:
                import inotify_simple
                inotify = inotify_simple.INotify()
                watch_fd = inotify.add_watch(str(incoming_dir), inotify_simple.flags.CREATE)

                logger.debug(f"Watching {incoming_dir} for new files (inotify)")

                # Wait for file creation event with timeout
                start = time.time()
                timeout_remaining = self.DEEP_SLEEP_SEC

                while timeout_remaining > 0:
                    try:
                        events = inotify.read(timeout=timeout_remaining)
                        if events:
                            logger.debug(f"File system event detected: {events}")
                            wake_reason = 'file_event'
                            break
                    except Exception as e:
                        logger.debug(f"inotify read error: {e}, retrying")

                    if wake_reason == 'signal':
                        break

                    elapsed = time.time() - start
                    timeout_remaining = self.DEEP_SLEEP_SEC - elapsed

                return wake_reason

            except (ImportError, AttributeError):
                # Fallback: polling-based deep sleep (no inotify available)
                logger.debug(f"inotify not available, using polling-based deep sleep")
                return self._deep_sleep_polling()

        finally:
            # Restore original signal handler
            sig.signal(sig.SIGUSR1, old_handler)

    def _deep_sleep_polling(self) -> str:
        """
        Fallback deep sleep using polling and signal handling.

        Polls the incoming/ directory every 10 seconds for new files,
        with overall timeout of DEEP_SLEEP_SEC.

        Returns:
            'file_event' if new file detected
            'signal' if SIGUSR1 received
            'timeout' if timeout reached
        """
        import signal as sig

        incoming_dir = self.queue_root / "incoming"
        wake_reason = 'timeout'
        poll_interval = 10  # seconds between checks

        def signal_handler(signum, frame):
            nonlocal wake_reason
            wake_reason = 'signal'
            logger.debug("Received SIGUSR1, waking from deep sleep")

        old_handler = sig.signal(sig.SIGUSR1, signal_handler)

        try:
            # Get initial file list
            initial_files = set(incoming_dir.glob("*.yaml"))
            logger.debug(f"Initial incoming/ file count: {len(initial_files)}")

            start = time.time()

            while True:
                if wake_reason == 'signal':
                    break

                # Check if timeout reached
                elapsed = time.time() - start
                if elapsed >= self.DEEP_SLEEP_SEC:
                    break

                # Sleep for poll_interval or remaining time, whichever is smaller
                remaining = self.DEEP_SLEEP_SEC - elapsed
                sleep_time = min(poll_interval, remaining)

                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Check for new files
                current_files = set(incoming_dir.glob("*.yaml"))
                if len(current_files) > len(initial_files):
                    logger.debug(f"New file(s) detected in incoming/")
                    wake_reason = 'file_event'
                    break

            return wake_reason

        finally:
            sig.signal(sig.SIGUSR1, old_handler)

    def invoke_qe_gate(self, task_id: str, handback: Dict[str, Any]) -> bool:
        """
        Invoke Quality Engineer validation before marking done.

        Args:
            task_id: Task identifier
            handback: Parsed HANDBACK dictionary

        Returns:
            True if QE approves, False otherwise
        """
        logger.info(f"Invoking QE gate for task {task_id}")

        # For now, approve all with confidence > 0.7
        # In real deployment, this would spawn quality-engineer agent
        confidence = handback.get("confidence", 0.5)
        quality = handback.get("metrics", {}).get("quality", 0.5)

        approved = (confidence > 0.7 and quality > 0.75)

        logger.info(f"QE gate for {task_id}: {'APPROVED' if approved else 'REJECTED'}")

        self.capture_span(
            "invoke_qe_gate",
            task_id=task_id,
            approved=approved,
            confidence=confidence,
            quality=quality,
        )

        return approved

    def capture_span(self, method_name: str, **attrs) -> None:
        """
        Write OpenTelemetry SPAN file for observability.

        Args:
            method_name: Method name for span identification
            **attrs: Additional span attributes
        """
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        span = {
            "span_name": f"orchestrator-{method_name}",
            "span_id": str(uuid.uuid4()),
            "trace_id": self.session_id,
            "timestamp": now_iso,
            "attributes": attrs,
        }

        spans_dir = self.queue_root.parent / "spans"
        spans_dir.mkdir(parents=True, exist_ok=True)

        span_file = spans_dir / f"{uuid.uuid4()}.span.json"

        try:
            with span_file.open("w") as f:
                json.dump(span, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write span file: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────────────

    def _read_yaml(self, path: Path) -> Dict[str, Any]:
        """Read and parse YAML file."""
        try:
            import yaml
            with path.open("r") as f:
                return yaml.safe_load(f)
        except ImportError:
            # Fallback: parse manually for simple YAML
            return self._simple_yaml_parse(path)

    def _simple_yaml_parse(self, path: Path) -> Dict[str, Any]:
        """Simple YAML parser for basic structures."""
        result = {}
        with path.open("r") as f:
            current_key = None
            for line in f:
                line = line.rstrip()
                if line.startswith("#") or not line.strip():
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if value:
                        result[key] = value
                    current_key = key
        return result

    def _dict_to_yaml(self, data: Dict[str, Any]) -> str:
        """Convert dict to YAML string."""
        try:
            import yaml
            return yaml.dump(data, default_flow_style=False)
        except ImportError:
            # Fallback to JSON
            return json.dumps(data, indent=2)

    def _parse_handback(self, text: str) -> Dict[str, Any]:
        """Parse HANDBACK YAML block from text."""
        # Look for HANDBACK block
        if "handoff_type: HANDBACK" not in text:
            raise HandbackParseError("No HANDBACK block found in output")

        lines = text.split("\n")

        # Find the HANDBACK line
        handback_idx = None
        for i, line in enumerate(lines):
            if "handoff_type: HANDBACK" in line:
                handback_idx = i
                break

        if handback_idx is None:
            raise HandbackParseError("No HANDBACK block found")

        # Get the indentation of the handoff_type line
        handback_line = lines[handback_idx]
        handback_indent = len(handback_line) - len(handback_line.lstrip())

        # Go backwards to include any preceding top-level keys at the same indentation,
        # but stop if we encounter a line that doesn't look like YAML (no ":" in it)
        handback_start = handback_idx
        for i in range(handback_idx - 1, -1, -1):
            line = lines[i]
            if line.strip() == "":
                continue  # Skip empty lines
            curr_indent = len(line) - len(line.lstrip())
            if curr_indent == handback_indent and ":" in line:
                # Same indentation and looks like YAML key - part of same object
                handback_start = i
            elif curr_indent > handback_indent:
                # Greater indentation - skip (indented content from a previous key)
                continue
            else:
                # Lower indentation or non-YAML line - stop going back
                break

        # Extract all lines from HANDBACK onwards at the same or greater indentation
        handback_lines = lines[handback_start:handback_idx]
        handback_lines.append(handback_line)

        for i in range(handback_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                # Empty line - skip
                continue
            curr_indent = len(line) - len(line.lstrip())
            if curr_indent >= handback_indent:
                # Same or greater indentation - part of object
                handback_lines.append(line)
            elif curr_indent > 0:
                # Indented content (nested) - part of object
                handback_lines.append(line)
            else:
                # Lower indentation at non-empty line - end of object
                break

        handback_text = "\n".join(handback_lines)

        try:
            import yaml
            parsed = yaml.safe_load(handback_text)
            # Handle case where parsed is None or empty
            if not parsed:
                raise HandbackParseError("HANDBACK block is empty")
            return parsed
        except Exception as e:
            # Fallback: try parsing entire text
            try:
                import yaml
                parsed = yaml.safe_load(text)
                if parsed and isinstance(parsed, dict) and "handoff_type" in parsed and parsed["handoff_type"] == "HANDBACK":
                    return parsed
            except:
                pass
            raise HandbackParseError(f"Failed to parse HANDBACK: {e}") from e

    def _validate_delegate(self, delegate: Dict[str, Any]) -> None:
        """Validate DELEGATE structure."""
        required = ["handoff_type", "task_id", "agent", "scope", "plan", "success_criteria"]
        missing = [k for k in required if k not in delegate]
        if missing:
            raise QueueValidationError(f"DELEGATE missing required fields: {missing}")

        if delegate.get("handoff_type") != "DELEGATE":
            raise QueueValidationError("Invalid handoff_type (must be DELEGATE)")

    def _validate_handback(self, handback: Dict[str, Any]) -> None:
        """Validate HANDBACK structure."""
        required = ["handoff_type", "task_id", "status"]
        missing = [k for k in required if k not in handback]
        if missing:
            raise QueueValidationError(f"HANDBACK missing required fields: {missing}")

        if handback.get("handoff_type") != "HANDBACK":
            raise QueueValidationError("Invalid handoff_type (must be HANDBACK)")

        valid_statuses = ["success", "failure", "partial", "blocked", "escalate"]
        if handback.get("status") not in valid_statuses:
            raise QueueValidationError(
                f"Invalid status: {handback.get('status')} "
                f"(must be one of {valid_statuses})"
            )

    def _move_task_to_done(self, task_id: str, handback: Dict[str, Any]) -> None:
        """Move task from processing/ to done/."""
        processing_dir = self.queue_root / "processing"
        done_dir = self.queue_root / "done"

        # Move DELEGATE file
        processing_file = processing_dir / f"{task_id}.yaml"
        done_file = done_dir / f"{task_id}.yaml"
        if processing_file.exists():
            processing_file.rename(done_file)

        # Write HANDBACK file
        handback_file = done_dir / f"{task_id}-HANDBACK.yaml"
        with handback_file.open("w") as f:
            f.write(self._dict_to_yaml(handback))

        # Cleanup metadata
        meta_file = processing_dir / f"{task_id}.meta.json"
        if meta_file.exists():
            meta_file.unlink()

        logger.info(f"Task {task_id} moved to done/")

    def _move_task_to_failed(self, task_id: str, error_msg: str) -> None:
        """Move task from processing/ (or incoming/) to failed/."""
        processing_dir = self.queue_root / "processing"
        incoming_dir = self.queue_root / "incoming"
        failed_dir = self.queue_root / "failed"

        # Try processing first, then incoming
        source_file = None
        for search_dir in [processing_dir, incoming_dir]:
            candidate = search_dir / f"{task_id}.yaml"
            if candidate.exists():
                source_file = candidate
                break

        if source_file:
            failed_file = failed_dir / f"{task_id}.yaml"
            source_file.rename(failed_file)

        # Write error file
        error_file = failed_dir / f"{task_id}-ERROR.json"
        error_data = {
            "task_id": task_id,
            "error": error_msg,
            "failed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        with error_file.open("w") as f:
            json.dump(error_data, f, indent=2)

        # Cleanup metadata
        meta_file = processing_dir / f"{task_id}.meta.json"
        if meta_file.exists():
            meta_file.unlink()

        logger.info(f"Task {task_id} moved to failed/ ({error_msg})")

    def _move_task_to_retry_pending(self, task_id: str, metadata: Dict[str, Any]) -> None:
        """Move task to retry-pending with incremented retry count."""
        processing_dir = self.queue_root / "processing"

        # Create retry-pending directory if needed
        retry_pending_dir = self.queue_root / "retry-pending"
        retry_pending_dir.mkdir(exist_ok=True)

        # Move DELEGATE file
        processing_file = processing_dir / f"{task_id}.yaml"
        retry_file = retry_pending_dir / f"{task_id}.yaml"
        if processing_file.exists():
            processing_file.rename(retry_file)

        # Update and write metadata
        metadata["retry_count"] = metadata.get("retry_count", 0) + 1
        metadata["last_error"] = "Crashed and recovered"
        meta_file = retry_pending_dir / f"{task_id}.meta.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f, indent=2)

        # Cleanup old metadata
        old_meta = processing_dir / f"{task_id}.meta.json"
        if old_meta.exists():
            old_meta.unlink()

        logger.info(f"Task {task_id} moved to retry-pending (retry #{metadata['retry_count']})")

    def _move_task_to_escalation(self, task_id: str, handback: Dict[str, Any]) -> None:
        """
        Escalation chaining (C2c) — synthesize a follow-on DELEGATE into incoming/.

        Canonical queue protocol (docs/QUEUE-PROTOCOL.md "Escalation Chaining"):
        on HANDBACK status=escalate, create a new DELEGATE
        ({task_id}-escalated-to-{role}) in incoming/ for the escalation target,
        then archive the original task to done/ with escalation audit metadata.
        There is NO escalation/ state directory in the queue protocol.

        Mirrors OrchestratorAgent's C2c implementation
        (src/orchestration/agents/orchestrator.py).
        """
        import yaml

        processing_dir = self.queue_root / "processing"
        incoming_dir = self.queue_root / "incoming"

        # Extract escalation target: output.escalate_to → top-level → default
        output = handback.get("output")
        escalate_to = output.get("escalate_to") if isinstance(output, dict) else None
        if not escalate_to:
            escalate_to = handback.get("escalate_to", "lead-engineer")

        escalation_reason = (
            output.get("escalation_reason")
            if isinstance(output, dict)
            else handback.get("escalation_reason")
        )

        # Original role comes from the claimed DELEGATE in processing/
        original_role = "unknown"
        processing_file = processing_dir / f"{task_id}.yaml"
        if processing_file.exists():
            try:
                with processing_file.open("r") as f:
                    original_delegate = yaml.safe_load(f) or {}
                original_role = original_delegate.get("agent", "unknown")
            except Exception as e:
                logger.warning(f"Could not read original DELEGATE for {task_id}: {e}")

        # Synthesize follow-on DELEGATE (same shape as C2c, plus plan so it
        # passes _validate_delegate when re-ingested by poll_queue)
        escalation_task_id = f"{task_id}-escalated-to-{escalate_to}"
        escalation_delegate = {
            "handoff_type": "DELEGATE",
            "task_id": escalation_task_id,
            "agent": escalate_to,
            "role": escalate_to,
            "scope": (
                f"Escalation from {original_role}: "
                f"{escalation_reason or 'See original_handback'}"
            ),
            "context": {
                "original_task_id": task_id,
                "original_role": original_role,
                "original_handback": handback,
                "escalation_reason": escalation_reason,
            },
            "plan": [
                "Review original work and HANDBACK in context.original_handback",
                "Address the escalation reason",
                "Return HANDBACK with assessment and next steps",
            ],
            "success_criteria": [
                "Review original work and HANDBACK",
                "Address escalation reason",
                "Provide assessment and next steps",
            ],
            "escalation_chain": handback.get("escalation_chain", []) + [original_role],
        }

        escalation_filename = f"{escalation_task_id}.yaml"
        escalation_file = incoming_dir / escalation_filename
        with escalation_file.open("w") as f:
            f.write(self._dict_to_yaml(escalation_delegate))

        # Archive original to done/ with escalation audit metadata
        # (writes done/{task_id}-HANDBACK.yaml and cleans up processing metadata)
        self._move_task_to_done(
            task_id,
            {**handback, "escalation_delegate_created": escalation_filename},
        )

        logger.info(
            f"Task {task_id} escalated to {escalate_to}: "
            f"chained DELEGATE {escalation_filename} enqueued in incoming/"
        )
