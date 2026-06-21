"""
Regression tests for Claude Code harness HarnessSpanCapture.

Tests for span creation, capture from various operation types,
and JSONL file persistence.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from src.harnesses.claude_code.span_capture import (
    HarnessSpan,
    HarnessSpanCapture,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def capture() -> HarnessSpanCapture:
    """Fresh HarnessSpanCapture instance with temp directory."""
    with TemporaryDirectory() as tmpdir:
        capture_obj = HarnessSpanCapture(spans_dir=Path(tmpdir))
        yield capture_obj


@pytest.fixture
def mock_dispatch_result() -> Any:
    """Mock DispatchResult object."""
    class MockDispatchResult:
        def __init__(self):
            self.agent = "engineer"
            self.model = "claude-haiku-4.5"
            self.tier = MockTier()
            self.pinned = False
            self.explanation = "Engineer selected for low-effort task"

    class MockTier:
        value = "haiku"

    return MockDispatchResult()


@pytest.fixture
def mock_render_result() -> Any:
    """Mock SkillRenderOutput object."""
    class MockRenderResult:
        def __init__(self):
            self.skill_name = "test-skill"
            self.success = True
            self.render_time_ms = 150.5
            self.error = None
            self.metadata = {"version": "1.0", "category": "orchestration"}

    return MockRenderResult()


@pytest.fixture
def mock_validation_result() -> Any:
    """Mock HandbackValidationResult object."""
    class MockValidationResult:
        def __init__(self):
            self.task_id = "task-001"
            self.valid = True
            self.status = "success"
            self.quality_score = 0.87
            self.missing_fields = []
            self.warnings = []

    return MockValidationResult()


# ---------------------------------------------------------------------------
# D4.1-D4.3: Span capture from various operations
# ---------------------------------------------------------------------------


class TestSpanCapture:
    """Span creation and capture from harness operations."""

    def test_capture_dispatch_creates_span(
        self, capture: HarnessSpanCapture, mock_dispatch_result: Any
    ) -> None:
        """capture_dispatch() creates a dispatch span."""
        span = capture.capture_dispatch(mock_dispatch_result, duration_ms=150)

        assert isinstance(span, HarnessSpan)
        assert span.span_type == "dispatch"
        assert span.agent == "engineer"
        assert span.model == "claude-haiku-4.5"
        assert span.duration_ms == 150
        assert span.status == "ok"

    def test_capture_dispatch_includes_attributes(
        self, capture: HarnessSpanCapture, mock_dispatch_result: Any
    ) -> None:
        """capture_dispatch() span includes tier, pinned, and explanation."""
        span = capture.capture_dispatch(mock_dispatch_result, duration_ms=100)

        assert span.attributes["tier"] == "haiku"
        assert span.attributes["pinned"] is False
        assert "low-effort" in span.attributes["explanation"]

    def test_capture_dispatch_generates_span_id(
        self, capture: HarnessSpanCapture, mock_dispatch_result: Any
    ) -> None:
        """capture_dispatch() generates a unique span_id."""
        span1 = capture.capture_dispatch(mock_dispatch_result, duration_ms=100)
        span2 = capture.capture_dispatch(mock_dispatch_result, duration_ms=100)

        assert span1.span_id != span2.span_id
        # Should be valid UUID format (simple check)
        assert len(span1.span_id) > 20

    def test_capture_render_creates_span(
        self, capture: HarnessSpanCapture, mock_render_result: Any
    ) -> None:
        """capture_render() creates a render span."""
        span = capture.capture_render(mock_render_result)

        assert isinstance(span, HarnessSpan)
        assert span.span_type == "render"
        assert span.skill_name == "test-skill"
        assert span.duration_ms == 150.5
        assert span.status == "ok"

    def test_capture_render_error_status(
        self, capture: HarnessSpanCapture
    ) -> None:
        """capture_render() with success=False sets status=error."""
        class FailedRender:
            skill_name = "failed-skill"
            success = False
            render_time_ms = 50.0
            error = "File not found"
            metadata = None

        span = capture.capture_render(FailedRender())
        assert span.status == "error"
        assert span.attributes["error"] == "File not found"

    def test_capture_render_metadata_keys(
        self, capture: HarnessSpanCapture, mock_render_result: Any
    ) -> None:
        """capture_render() includes metadata keys in attributes."""
        span = capture.capture_render(mock_render_result)

        metadata_keys = span.attributes["metadata_keys"]
        assert "version" in metadata_keys
        assert "category" in metadata_keys

    def test_capture_validation_creates_span(
        self, capture: HarnessSpanCapture, mock_validation_result: Any
    ) -> None:
        """capture_validation() creates a validation span."""
        span = capture.capture_validation(mock_validation_result, duration_ms=50)

        assert isinstance(span, HarnessSpan)
        assert span.span_type == "validation"
        assert span.duration_ms == 50
        assert span.status == "ok"

    def test_capture_validation_error_status(
        self, capture: HarnessSpanCapture
    ) -> None:
        """capture_validation() with valid=False sets status=error."""
        class InvalidResult:
            task_id = "task-bad"
            valid = False
            status = "failure"
            quality_score = None
            missing_fields = ["notes", "status"]
            warnings = ["Invalid format"]

        span = capture.capture_validation(InvalidResult, duration_ms=100)
        assert span.status == "error"

    def test_capture_validation_attributes(
        self, capture: HarnessSpanCapture, mock_validation_result: Any
    ) -> None:
        """capture_validation() includes validation details in attributes."""
        span = capture.capture_validation(mock_validation_result, duration_ms=50)

        assert span.attributes["task_id"] == "task-001"
        assert span.attributes["valid"] is True
        assert span.attributes["status"] == "success"
        assert span.attributes["quality_score"] == 0.87
        assert span.attributes["missing_fields_count"] == 0
        assert span.attributes["warnings_count"] == 0


# ---------------------------------------------------------------------------
# D4: HarnessSpan initialization and ISO8601 timestamp
# ---------------------------------------------------------------------------


class TestHarnessSpan:
    """HarnessSpan dataclass behavior."""

    def test_harness_span_initialization(self) -> None:
        """HarnessSpan can be initialized with basic fields."""
        span = HarnessSpan(
            span_id="span-123",
            span_type="dispatch",
            agent="engineer",
            duration_ms=100.0,
        )
        assert span.span_id == "span-123"
        assert span.span_type == "dispatch"
        assert span.agent == "engineer"
        assert span.duration_ms == 100.0

    def test_harness_span_timestamp_is_iso8601(self) -> None:
        """HarnessSpan.timestamp is ISO8601 format (when not provided)."""
        span = HarnessSpan(
            span_id="span-123",
            span_type="dispatch",
        )
        # ISO8601 format: YYYY-MM-DDTHH:MM:SS.ssssssZ
        assert "T" in span.timestamp
        assert "Z" in span.timestamp
        # Check basic format with regex
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, span.timestamp)

    def test_harness_span_default_attributes(self) -> None:
        """HarnessSpan defaults attributes to empty dict."""
        span = HarnessSpan(span_id="test", span_type="dispatch")
        assert isinstance(span.attributes, dict)
        assert len(span.attributes) == 0

    def test_harness_span_default_status(self) -> None:
        """HarnessSpan defaults status to 'ok'."""
        span = HarnessSpan(span_id="test", span_type="dispatch")
        assert span.status == "ok"

    def test_harness_span_with_custom_timestamp(self) -> None:
        """HarnessSpan can use a custom timestamp."""
        custom_ts = "2024-06-20T12:30:45Z"
        span = HarnessSpan(
            span_id="test",
            span_type="dispatch",
            timestamp=custom_ts,
        )
        assert span.timestamp == custom_ts


# ---------------------------------------------------------------------------
# D4.4: Flushing spans to JSONL
# ---------------------------------------------------------------------------


class TestSpanPersistence:
    """Writing spans to JSONL files."""

    def test_flush_writes_jsonl_file(
        self, capture: HarnessSpanCapture
    ) -> None:
        """flush() writes pending spans to a JSONL file."""
        # Create a few spans
        span1 = HarnessSpan(
            span_id="span-1",
            span_type="dispatch",
            agent="engineer",
        )
        span2 = HarnessSpan(
            span_id="span-2",
            span_type="render",
            skill_name="test-skill",
        )
        capture._pending_spans.append(span1)
        capture._pending_spans.append(span2)

        count = capture.flush()
        assert count == 2

        # Verify file was created
        spans_dir = capture.spans_dir
        files = list(spans_dir.glob("spans-*.jsonl"))
        assert len(files) > 0

    def test_flush_writes_valid_jsonl(
        self, capture: HarnessSpanCapture
    ) -> None:
        """flush() writes valid newline-delimited JSON."""
        span = HarnessSpan(
            span_id="span-test",
            span_type="dispatch",
            agent="orchestrator",
        )
        capture._pending_spans.append(span)

        capture.flush()

        # Read and verify JSONL
        files = list(capture.spans_dir.glob("spans-*.jsonl"))
        assert len(files) > 0

        with open(files[0], "r") as f:
            lines = f.readlines()
            assert len(lines) > 0
            # Each line should be valid JSON
            for line in lines:
                data = json.loads(line.strip())
                assert "span_id" in data
                assert "span_type" in data

    def test_flush_clears_pending_spans(
        self, capture: HarnessSpanCapture
    ) -> None:
        """flush() clears the pending spans buffer."""
        capture._pending_spans.append(
            HarnessSpan(span_id="span-1", span_type="dispatch")
        )
        capture._pending_spans.append(
            HarnessSpan(span_id="span-2", span_type="render")
        )

        capture.flush()

        assert len(capture._pending_spans) == 0

    def test_flush_empty_returns_zero(
        self, capture: HarnessSpanCapture
    ) -> None:
        """flush() with no pending spans returns 0."""
        count = capture.flush()
        assert count == 0

    def test_flush_creates_spans_directory(
        self, capture: HarnessSpanCapture
    ) -> None:
        """flush() creates the spans directory if it doesn't exist."""
        # Verify directory exists after flush
        capture._pending_spans.append(
            HarnessSpan(span_id="span-1", span_type="dispatch")
        )
        capture.flush()

        assert capture.spans_dir.exists()
        assert capture.spans_dir.is_dir()

    def test_flush_appends_to_existing_file(
        self, capture: HarnessSpanCapture
    ) -> None:
        """Multiple flush() calls append to the same file."""
        # First flush
        capture._pending_spans.append(
            HarnessSpan(span_id="span-1", span_type="dispatch")
        )
        capture.flush()

        # Second flush (same day)
        capture._pending_spans.append(
            HarnessSpan(span_id="span-2", span_type="render")
        )
        capture.flush()

        # Read file and count lines
        files = list(capture.spans_dir.glob("spans-*.jsonl"))
        assert len(files) > 0

        with open(files[0], "r") as f:
            lines = f.readlines()
            # Should have both spans
            assert len(lines) >= 2


# ---------------------------------------------------------------------------
# D4.5-D4.6: Recent spans and timestamp verification
# ---------------------------------------------------------------------------


class TestRecentSpans:
    """Querying recently captured spans."""

    def test_recent_spans_returns_n(
        self, capture: HarnessSpanCapture
    ) -> None:
        """recent_spans(n) returns up to n most recent spans."""
        for i in range(5):
            span = HarnessSpan(
                span_id=f"span-{i}",
                span_type="dispatch",
                agent="engineer",
            )
            capture._pending_spans.append(span)

        recent = capture.recent_spans(n=3)
        assert len(recent) == 3
        # Should be the last 3 spans
        assert recent[-1].span_id == "span-4"
        assert recent[-2].span_id == "span-3"
        assert recent[-3].span_id == "span-2"

    def test_recent_spans_fewer_available(
        self, capture: HarnessSpanCapture
    ) -> None:
        """recent_spans(n) returns all spans if fewer than n available."""
        for i in range(2):
            capture._pending_spans.append(
                HarnessSpan(span_id=f"span-{i}", span_type="dispatch")
            )

        recent = capture.recent_spans(n=10)
        assert len(recent) == 2

    def test_recent_spans_empty(self, capture: HarnessSpanCapture) -> None:
        """recent_spans(n) with no pending spans returns empty list."""
        recent = capture.recent_spans(n=5)
        assert recent == []

    def test_span_timestamp_is_iso8601(
        self, capture: HarnessSpanCapture, mock_dispatch_result: Any
    ) -> None:
        """Captured span has ISO8601 timestamp."""
        span = capture.capture_dispatch(mock_dispatch_result, duration_ms=100)

        # Verify ISO8601 format
        assert "T" in span.timestamp
        assert "Z" in span.timestamp

        # Verify it parses as a valid datetime (approximately)
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, span.timestamp)

    def test_recent_spans_after_flush_not_included(
        self, capture: HarnessSpanCapture
    ) -> None:
        """recent_spans() does not include flushed spans (only pending)."""
        span1 = HarnessSpan(span_id="span-1", span_type="dispatch")
        capture._pending_spans.append(span1)
        capture.flush()

        # After flush, pending is empty
        recent = capture.recent_spans(n=10)
        assert len(recent) == 0

        # Now add a new span
        span2 = HarnessSpan(span_id="span-2", span_type="dispatch")
        capture._pending_spans.append(span2)
        recent = capture.recent_spans(n=10)
        assert len(recent) == 1
        assert recent[0].span_id == "span-2"


# ---------------------------------------------------------------------------
# Custom spans directory
# ---------------------------------------------------------------------------


class TestCustomSpansDir:
    """Custom spans directory initialization."""

    def test_harness_span_capture_with_custom_dir(self) -> None:
        """HarnessSpanCapture accepts custom spans_dir."""
        with TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "my-spans"
            capture = HarnessSpanCapture(spans_dir=custom_dir)
            assert capture.spans_dir == custom_dir

    def test_harness_span_capture_default_dir(self) -> None:
        """HarnessSpanCapture resolves default directory."""
        capture = HarnessSpanCapture()
        # Default should point to artifacts/spans/harness/
        assert "artifacts" in str(capture.spans_dir)
        assert "spans" in str(capture.spans_dir)
        assert "harness" in str(capture.spans_dir)
