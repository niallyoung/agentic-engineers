"""
Span Capture for the Claude Code harness.

Captures OpenTelemetry-style spans from harness operations (dispatch, render,
validation) and writes them as newline-delimited JSON for observability.

Usage::

    from src.harnesses.claude_code.span_capture import HarnessSpanCapture

    capture = HarnessSpanCapture()
    span = capture.capture_dispatch(dispatch_result, duration_ms=150)
    capture.flush()  # Write to JSONL file

    recent = capture.recent_spans(n=10)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class HarnessSpan:
    """A single tracing span from harness operations."""

    span_id: str
    span_type: str  # "dispatch" | "render" | "validation"
    agent: Optional[str] = None
    skill_name: Optional[str] = None
    model: Optional[str] = None
    duration_ms: float = 0.0
    status: str = "ok"  # "ok" | "error"
    attributes: Dict[str, Any] = None
    timestamp: str = ""  # ISO 8601

    def __post_init__(self) -> None:
        """Initialize defaults."""
        if self.attributes is None:
            self.attributes = {}
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class HarnessSpanCapture:
    """Capture and persist harness operation spans.

    Writes spans as newline-delimited JSON to ``artifacts/spans/harness/``.

    Parameters
    ----------
    spans_dir:
        Directory to write spans. Defaults to
        ``<repo_root>/artifacts/spans/harness/``.
    repo_root:
        Repository root used to resolve default spans_dir.
        Defaults to directory three levels above this file.
    """

    def __init__(
        self,
        spans_dir: Optional[Path] = None,
        repo_root: Optional[Path] = None,
    ) -> None:
        if repo_root is None:
            # src/harnesses/claude_code/ -> src/harnesses -> src -> repo_root
            repo_root = Path(__file__).resolve().parents[3]

        if spans_dir is None:
            spans_dir = repo_root / "artifacts" / "spans" / "harness"

        self.spans_dir = spans_dir
        self._pending_spans: List[HarnessSpan] = []

    def capture_dispatch(
        self, result: Any, duration_ms: float
    ) -> HarnessSpan:
        """Capture a dispatch result as a span.

        Args:
            result: DispatchResult object with agent, model, tier attributes.
            duration_ms: Duration in milliseconds.

        Returns:
            HarnessSpan representing the dispatch operation.
        """
        span = HarnessSpan(
            span_id=str(uuid.uuid4()),
            span_type="dispatch",
            agent=getattr(result, "agent", None),
            model=getattr(result, "model", None),
            duration_ms=duration_ms,
            status="ok",
            attributes={
                "tier": getattr(result, "tier", None).value
                if hasattr(result, "tier")
                else None,
                "pinned": getattr(result, "pinned", False),
                "explanation": getattr(result, "explanation", ""),
            },
        )
        self._pending_spans.append(span)
        logger.debug(
            "span.capture_dispatch",
            extra={
                "span_id": span.span_id,
                "agent": span.agent,
                "duration_ms": duration_ms,
            },
        )
        return span

    def capture_render(self, result: Any) -> HarnessSpan:
        """Capture a skill render result as a span.

        Args:
            result: SkillRenderOutput object with skill_name, success,
                render_time_ms attributes.

        Returns:
            HarnessSpan representing the render operation.
        """
        span = HarnessSpan(
            span_id=str(uuid.uuid4()),
            span_type="render",
            skill_name=getattr(result, "skill_name", None),
            duration_ms=getattr(result, "render_time_ms", 0.0),
            status="ok" if getattr(result, "success", False) else "error",
            attributes={
                "success": getattr(result, "success", False),
                "error": getattr(result, "error", None),
                "metadata_keys": (
                    list(getattr(result, "metadata", {}).keys())
                    if getattr(result, "metadata")
                    else []
                ),
            },
        )
        self._pending_spans.append(span)
        logger.debug(
            "span.capture_render",
            extra={
                "span_id": span.span_id,
                "skill_name": span.skill_name,
                "status": span.status,
                "duration_ms": span.duration_ms,
            },
        )
        return span

    def capture_validation(
        self, result: Any, duration_ms: float
    ) -> HarnessSpan:
        """Capture a HANDBACK validation result as a span.

        Args:
            result: HandbackValidationResult object with task_id, valid, status
                attributes.
            duration_ms: Duration in milliseconds.

        Returns:
            HarnessSpan representing the validation operation.
        """
        span = HarnessSpan(
            span_id=str(uuid.uuid4()),
            span_type="validation",
            duration_ms=duration_ms,
            status="ok" if getattr(result, "valid", False) else "error",
            attributes={
                "task_id": getattr(result, "task_id", ""),
                "valid": getattr(result, "valid", False),
                "status": getattr(result, "status", None),
                "quality_score": getattr(result, "quality_score", None),
                "missing_fields_count": len(
                    getattr(result, "missing_fields", [])
                ),
                "warnings_count": len(getattr(result, "warnings", [])),
            },
        )
        self._pending_spans.append(span)
        logger.debug(
            "span.capture_validation",
            extra={
                "span_id": span.span_id,
                "task_id": span.attributes.get("task_id"),
                "valid": span.attributes.get("valid"),
                "duration_ms": duration_ms,
            },
        )
        return span

    def flush(self) -> int:
        """Write all pending spans to JSONL file.

        Creates directory if needed. Returns number of spans written.

        Returns:
            Number of spans written to file.
        """
        if not self._pending_spans:
            return 0

        self.spans_dir.mkdir(parents=True, exist_ok=True)

        # Use date-based filename
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = self.spans_dir / f"spans-{date_str}.jsonl"

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                for span in self._pending_spans:
                    span_dict = asdict(span)
                    json_line = json.dumps(span_dict, default=str)
                    f.write(json_line + "\n")

            count = len(self._pending_spans)
            logger.info(
                "span.flush",
                extra={
                    "file": str(file_path),
                    "spans_written": count,
                },
            )
            self._pending_spans.clear()
            return count
        except OSError as exc:
            logger.error(
                "span.flush_failed",
                extra={
                    "file": str(file_path),
                    "error": str(exc),
                },
            )
            return 0

    def recent_spans(self, n: int = 20) -> List[HarnessSpan]:
        """Return the most recent n spans (from pending buffer).

        Note: Only includes spans not yet flushed. Flushed spans must be
        read from the JSONL file.

        Args:
            n: Number of spans to return.

        Returns:
            List of up to n most recent HarnessSpan objects.
        """
        return self._pending_spans[-n:]
