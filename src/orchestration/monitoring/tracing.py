"""
Distributed Tracing — OpenTelemetry-style span tracking.

Provides lightweight span-based tracing for tracking request flow
through the Orchestrator pipeline without requiring an external
OpenTelemetry collector (though compatible with one).

Usage:
    tracer = Tracer("orchestrator")

    with tracer.start_span("route_task", task_id="task-001") as span:
        span.set_attribute("role", "engineer")
        # ... do work ...
        span.set_status("ok")

    # Export spans
    spans = tracer.get_completed_spans()
"""

import time
import uuid
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional


@dataclass
class Span:
    """A single tracing span representing a unit of work."""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    start_time: float  # Unix timestamp (seconds)
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "unset"  # unset | ok | error
    error_message: Optional[str] = None
    end_time: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds, or None if not ended."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, **attributes) -> None:
        """Add a timestamped event to the span."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes,
        })

    def set_status(self, status: str, message: str = None) -> None:
        """Set span status: 'ok' or 'error'."""
        if status not in ("ok", "error", "unset"):
            raise ValueError(f"Invalid span status: {status}")
        self.status = status
        if message:
            self.error_message = message

    def end(self) -> None:
        """Mark span as ended."""
        self.end_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize span to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "attributes": self.attributes,
            "events": self.events,
        }


class Tracer:
    """
    Lightweight distributed tracer.

    Manages active spans per thread and collects completed spans
    for export to Jaeger, Zipkin, or OpenTelemetry collector.
    """

    def __init__(self, service_name: str, max_completed: int = 1000):
        self.service_name = service_name
        self._max_completed = max_completed
        self._completed_spans: List[Span] = []
        self._active_spans: Dict[int, List[Span]] = {}  # thread_id -> stack
        self._lock = threading.Lock()

    def _thread_id(self) -> int:
        return threading.get_ident()

    def start_span(
        self,
        name: str,
        trace_id: str = None,
        parent_span: Span = None,
        **attributes,
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name (e.g. "route_task", "validate_delegate")
            trace_id: Existing trace ID to join, or None to create new
            parent_span: Parent span for nesting, or None
            **attributes: Initial span attributes
        """
        tid = self._thread_id()

        # Determine trace_id and parent
        if trace_id is None:
            # Check if there's an active span on this thread
            with self._lock:
                stack = self._active_spans.get(tid, [])
                if stack:
                    trace_id = stack[-1].trace_id
                    parent_id = stack[-1].span_id
                else:
                    trace_id = str(uuid.uuid4()).replace("-", "")
                    parent_id = None
        else:
            parent_id = parent_span.span_id if parent_span else None

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=str(uuid.uuid4()).replace("-", "")[:16],
            parent_span_id=parent_id,
            start_time=time.time(),
            attributes={"service": self.service_name, **attributes},
        )

        with self._lock:
            if tid not in self._active_spans:
                self._active_spans[tid] = []
            self._active_spans[tid].append(span)

        return span

    def end_span(self, span: Span) -> None:
        """End a span and move it to completed."""
        span.end()
        tid = self._thread_id()
        with self._lock:
            stack = self._active_spans.get(tid, [])
            if span in stack:
                stack.remove(span)
            # Evict oldest if over limit
            if len(self._completed_spans) >= self._max_completed:
                self._completed_spans.pop(0)
            self._completed_spans.append(span)

    @contextmanager
    def trace(self, name: str, **attributes) -> Generator[Span, None, None]:
        """Context manager for automatic span lifecycle."""
        span = self.start_span(name, **attributes)
        try:
            yield span
            if span.status == "unset":
                span.set_status("ok")
        except Exception as e:
            span.set_status("error", str(e))
            raise
        finally:
            self.end_span(span)

    def get_completed_spans(self) -> List[Span]:
        """Return all completed spans."""
        with self._lock:
            return list(self._completed_spans)

    def get_active_spans(self) -> List[Span]:
        """Return all currently active spans."""
        with self._lock:
            result = []
            for stack in self._active_spans.values():
                result.extend(stack)
            return result

    def clear(self) -> None:
        """Clear all spans (for testing)."""
        with self._lock:
            self._completed_spans.clear()
            self._active_spans.clear()
