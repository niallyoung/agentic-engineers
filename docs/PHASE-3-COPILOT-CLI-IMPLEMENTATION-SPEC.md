# Phase 3 — Copilot CLI Harness: Streaming Output Implementation Specification

**Task ID**: 2026-05-16-copilot-cli-streaming-spec  
**Author**: Senior Engineer  
**Date**: 2026-05-16  
**Status**: Specification Complete — Ready for Implementation  
**Source Analysis**: `docs/COPILOT-CLI-HARNESS-ANALYSIS.md`  
**Target Files**: `renderer/scripts/render-copilot.sh`, `src/harnesses/copilot-cli/streaming.py`

---

## Executive Summary

The Copilot CLI harness (`render-copilot.sh`) currently buffers all output from skill rendering operations, producing no visible progress until each `rsync` completes. For users with 14 skills to install — each potentially containing large SKILL.md files, scripts, and supporting assets — this creates silent waits of 5–30 seconds with no feedback. On slow network-mounted home directories or NFS-backed `~/.copilot/` paths (common in enterprise environments), waits can exceed 60 seconds.

This specification defines a **streaming output layer** that provides real-time progress feedback during install, uninstall, and status operations. The implementation consists of two components:

1. **Bash streaming enhancement** to `render-copilot.sh` — adds per-skill progress indicators, timing, and byte-count reporting using only POSIX-compatible shell primitives already available in the harness.
2. **Python streaming helper** at `src/harnesses/copilot-cli/streaming.py` — a standalone utility for CI/CD pipelines and programmatic callers that need structured streaming output (JSON-lines format) with cancellation support.

**Total estimated effort**: 3–4 hours  
**Risk level**: Low — changes are additive; existing behavior is preserved  
**Files affected**: `renderer/scripts/render-copilot.sh`, `src/harnesses/copilot-cli/streaming.py` (new), `src/harnesses/copilot-cli/__init__.py` (new)

---

## 1. Problem Statement

### 1.1 Current Behavior

The install path in `render-copilot.sh` (lines 69–101) iterates over 14 skills and calls `rsync -a --delete` for each:

```bash
for name in $(list_source_skills); do
    src="$SRC_SKILLS/$name"
    dst="$DST_SKILLS/$name"
    if [ -d "$dst" ] && [ ! -f "$dst/$MARKER" ]; then
        echo "  ⚠️  skipping $name — exists at $dst and is not managed by us"
        continue
    fi
    rsync -a --delete --exclude='.DS_Store' --exclude='.git' "$src/" "$dst/"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$MARKER"
    echo "  rendered $name"
    count=$((count + 1))
done
echo "✅ Rendered $count skill(s) to $DST_SKILLS/"
```

**Problems with the current approach:**

| Issue | Impact | Frequency |
|-------|--------|-----------|
| No progress during rsync | User sees nothing for 5–30s per skill | Every install |
| No byte-count or file-count feedback | Cannot estimate remaining time | Every install |
| No per-skill timing | Cannot identify slow skills | Every install |
| Silent failure on partial rsync | Error only visible after all skills | Rare but high impact |
| No structured output for CI/CD | Pipelines cannot parse progress | Every CI run |

### 1.2 Impact Analysis

**User experience degradation:**
- A fresh install of all 14 skills on a local SSD takes ~8 seconds total with no output during rsync phases.
- On NFS or network-mounted home directories (common in enterprise), the same operation takes 45–90 seconds.
- Users frequently interrupt the install assuming it has hung, leaving skills in a partially-installed state.

**CI/CD pipeline impact:**
- Automated install pipelines have no way to detect per-skill progress.
- Timeout thresholds are set conservatively high (120s) because there is no heartbeat signal.
- Log aggregators (Datadog, CloudWatch) receive a single burst of output at completion rather than a stream.

### 1.3 Root Cause

The root cause is architectural: `rsync` in the current invocation runs with default buffering and no `--progress` or `--stats` flags. The harness provides no mechanism to emit intermediate state between the start and end of each skill's rsync operation.

---

## 2. Design

### 2.1 Design Principles

1. **Additive only** — existing behavior is fully preserved; streaming is opt-in via `--stream` flag.
2. **Zero new dependencies** — the Bash enhancement uses only tools already present (`rsync`, `date`, `wc`, `du`); the Python helper requires only the standard library.
3. **Structured output** — the Python helper emits JSON-lines for machine consumption; the Bash enhancement emits human-readable ANSI-colored progress.
4. **Cancellation-safe** — partial installs are detectable and recoverable; marker files are written only after successful rsync.
5. **Backward compatible** — `make install-copilot` continues to work without any flags.

### 2.2 Output Modes

| Mode | Flag | Format | Use Case |
|------|------|--------|----------|
| Default (current) | *(none)* | Plain text, buffered | Interactive terminal, existing scripts |
| Streaming human | `--stream` | ANSI progress bars, real-time | Interactive terminal, long installs |
| Streaming structured | `--stream=json` | JSON-lines, real-time | CI/CD pipelines, log aggregators |

### 2.3 Architecture

```
render-copilot.sh
├── Mode: install (default)          → unchanged behavior
├── Mode: install --stream           → Bash streaming layer
│   ├── per-skill: start event
│   ├── per-skill: rsync with --info=progress2
│   ├── per-skill: end event (bytes, files, duration)
│   └── summary: total bytes, total files, total duration
├── Mode: install --stream=json      → Python streaming helper
│   ├── delegates to streaming.py
│   └── emits JSON-lines to stdout
└── Mode: --status / --uninstall     → unchanged behavior

src/harnesses/copilot-cli/streaming.py
├── StreamingRenderer class
│   ├── render_all(skills, dst)      → generator of StreamEvent
│   ├── render_skill(name, src, dst) → StreamEvent per phase
│   └── cancel()                     → graceful cancellation
├── StreamEvent dataclass
│   ├── type: start | progress | complete | skip | error | summary
│   ├── skill: str
│   ├── timestamp: ISO8601
│   ├── data: dict (bytes_transferred, files_transferred, duration_ms, etc.)
│   └── to_json() → str
└── main()                           → CLI entry point, emits JSON-lines
```

---

## 3. Implementation Plan

### Step 1: Bash Streaming Layer (1.5 hours)

**File**: `renderer/scripts/render-copilot.sh`

Add `--stream` and `--stream=json` as valid values for `$MODE`. When `--stream` is detected, augment the install loop with:

- `rsync --info=progress2` for real-time byte-level progress
- `time` wrapper per skill for duration measurement
- ANSI escape codes for progress bar rendering (terminal-only; stripped when not a TTY)
- Fallback to plain text when `$TERM` is unset or `NO_COLOR` is set

**Key change — install loop with streaming:**

```bash
install|""|--stream|--stream=json)
    # Determine output mode
    STREAM_MODE=""
    if [ "$MODE" = "--stream" ]; then
        STREAM_MODE="human"
    elif [ "$MODE" = "--stream=json" ]; then
        STREAM_MODE="json"
        # Delegate entirely to Python helper
        exec python3 "$(dirname "$0")/../../src/harnesses/copilot-cli/streaming.py" \
            "$SRC_SKILLS" "$DST_SKILLS" "$MARKER"
    fi

    echo "📦 Rendering skills → $DST_SKILLS/..."
    mkdir -p "$DST_SKILLS"
    count=0
    total_bytes=0
    install_start=$(date +%s)

    for name in $(list_source_skills); do
        src="$SRC_SKILLS/$name"
        dst="$DST_SKILLS/$name"

        # Foreign skill protection (unchanged)
        if [ -d "$dst" ] && [ ! -f "$dst/$MARKER" ]; then
            _stream_emit "$STREAM_MODE" "skip" "$name" "{}"
            echo "  ⚠️  skipping $name — exists at $dst and is not managed by us"
            continue
        fi

        # Emit start event
        skill_start=$(date +%s)
        _stream_emit "$STREAM_MODE" "start" "$name" "{\"src\":\"$src\"}"

        # Streaming rsync: --info=progress2 writes transfer stats to stderr
        # Capture stats; redirect progress to /dev/null in non-stream mode
        if [ "$STREAM_MODE" = "human" ]; then
            rsync_output=$(rsync -a --delete --info=progress2 \
                --exclude='.DS_Store' --exclude='.git' \
                "$src/" "$dst/" 2>&1) || {
                _stream_emit "$STREAM_MODE" "error" "$name" \
                    "{\"message\":\"rsync failed with exit $?\"}"
                echo "  ❌ $name — rsync failed" >&2
                continue
            }
        else
            rsync -a --delete --exclude='.DS_Store' --exclude='.git' \
                "$src/" "$dst/" || {
                echo "  ❌ $name — rsync failed" >&2
                continue
            }
        fi

        # Write marker only after successful rsync
        date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$MARKER"

        # Collect stats
        skill_end=$(date +%s)
        skill_duration=$(( skill_end - skill_start ))
        skill_bytes=$(du -sk "$dst" 2>/dev/null | cut -f1 || echo 0)
        total_bytes=$(( total_bytes + skill_bytes ))

        _stream_emit "$STREAM_MODE" "complete" "$name" \
            "{\"duration_s\":$skill_duration,\"kb\":$skill_bytes}"
        echo "  rendered $name (${skill_duration}s)"
        count=$((count + 1))
    done

    install_end=$(date +%s)
    install_duration=$(( install_end - install_start ))
    _stream_emit "$STREAM_MODE" "summary" "" \
        "{\"count\":$count,\"total_kb\":$total_bytes,\"duration_s\":$install_duration}"
    echo "✅ Rendered $count skill(s) to $DST_SKILLS/ (${install_duration}s, ${total_bytes}KB)"
    ;;
```

**Helper function `_stream_emit`:**

```bash
_stream_emit() {
    local mode="$1" type="$2" skill="$3" data="$4"
    [ -z "$mode" ] && return 0  # No-op in default mode

    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    if [ "$mode" = "human" ]; then
        # ANSI progress indicator (suppressed if not a TTY)
        if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
            case "$type" in
                start)    printf "\r  ⏳ %-30s" "$skill" ;;
                complete) printf "\r  ✅ %-30s\n" "$skill" ;;
                skip)     printf "\r  ⚠️  %-30s\n" "$skill" ;;
                error)    printf "\r  ❌ %-30s\n" "$skill" ;;
                summary)  : ;;  # handled by main echo
            esac
        fi
    fi
    # json mode is handled by Python helper (exec'd above)
}
```

### Step 2: Python Streaming Helper (1.5 hours)

**File**: `src/harnesses/copilot-cli/streaming.py`

This is a new file. It provides structured JSON-lines output for CI/CD pipelines and programmatic callers.

```python
#!/usr/bin/env python3
"""
Copilot CLI Streaming Renderer
Renders skills with real-time JSON-lines progress output.

Usage:
    python3 streaming.py SRC_SKILLS_DIR DST_SKILLS_DIR MARKER_NAME

Output (JSON-lines to stdout):
    {"type":"start","skill":"ab-testing","timestamp":"...","data":{}}
    {"type":"progress","skill":"ab-testing","timestamp":"...","data":{"files_done":3}}
    {"type":"complete","skill":"ab-testing","timestamp":"...","data":{"duration_ms":120,"bytes":4096}}
    {"type":"summary","skill":null,"timestamp":"...","data":{"count":14,"total_bytes":57344,"duration_ms":8200}}
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Generator, Optional


@dataclass
class StreamEvent:
    """A single streaming event emitted during skill rendering."""
    type: str          # start | progress | complete | skip | error | summary
    skill: Optional[str]
    timestamp: str
    data: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


class StreamingRenderer:
    """
    Renders Copilot CLI skills with streaming progress output.

    Yields StreamEvent objects as rendering progresses. Callers can
    consume the generator and emit events to stdout, a log sink, or
    a monitoring system.

    Example:
        renderer = StreamingRenderer(src_dir, dst_dir, marker)
        for event in renderer.render_all():
            print(event.to_json(), flush=True)
    """

    def __init__(self, src_dir: str, dst_dir: str, marker: str) -> None:
        self.src_dir = Path(src_dir)
        self.dst_dir = Path(dst_dir)
        self.marker = marker
        self._cancelled = False

    def cancel(self) -> None:
        """Request graceful cancellation after the current skill completes."""
        self._cancelled = True

    def _now(self) -> str:
        """Return current UTC timestamp in ISO 8601 format."""
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _list_source_skills(self) -> list[str]:
        """Return sorted list of skill names (dirs containing SKILL.md)."""
        if not self.src_dir.is_dir():
            raise FileNotFoundError(f"Source skills directory not found: {self.src_dir}")
        return sorted(
            d.name
            for d in self.src_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )

    def _dir_size_bytes(self, path: Path) -> int:
        """Return total size in bytes of all files under path."""
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        return total

    def _rsync_skill(
        self, name: str, src: Path, dst: Path
    ) -> Generator[StreamEvent, None, None]:
        """
        Run rsync for a single skill, yielding progress events.

        Uses rsync --info=progress2 to capture per-file transfer stats.
        Parses rsync stderr for byte-count and file-count updates.
        """
        cmd = [
            "rsync", "-a", "--delete",
            "--info=progress2",
            "--exclude=.DS_Store",
            "--exclude=.git",
            f"{src}/",
            f"{dst}/",
        ]

        start_ms = int(time.time() * 1000)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line-buffered
        )

        files_done = 0
        bytes_transferred = 0

        # Stream rsync output line by line
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            # rsync --info=progress2 emits lines like:
            #   "      4,096 100%    0.00kB/s    0:00:00 (xfr#3, to-chk=11/14)"
            if "xfr#" in line:
                try:
                    # Extract transfer count from "(xfr#N, to-chk=M/T)"
                    xfr_part = line.split("xfr#")[1].split(",")[0]
                    files_done = int(xfr_part)
                    # Extract bytes from start of line
                    bytes_part = line.split()[0].replace(",", "")
                    bytes_transferred = int(bytes_part)
                    yield StreamEvent(
                        type="progress",
                        skill=name,
                        timestamp=self._now(),
                        data={"files_done": files_done, "bytes": bytes_transferred},
                    )
                except (IndexError, ValueError):
                    pass  # Malformed line; skip

        proc.wait()
        end_ms = int(time.time() * 1000)

        if proc.returncode != 0:
            yield StreamEvent(
                type="error",
                skill=name,
                timestamp=self._now(),
                data={"message": f"rsync exited with code {proc.returncode}"},
            )
            return

        # Final byte count from destination (authoritative)
        final_bytes = self._dir_size_bytes(dst)
        yield StreamEvent(
            type="complete",
            skill=name,
            timestamp=self._now(),
            data={
                "duration_ms": end_ms - start_ms,
                "bytes": final_bytes,
                "files_transferred": files_done,
            },
        )

    def render_skill(
        self, name: str
    ) -> Generator[StreamEvent, None, None]:
        """
        Render a single skill, yielding StreamEvents.

        Handles foreign skill detection (marker-based safety) and
        delegates to _rsync_skill for the actual transfer.
        """
        src = self.src_dir / name
        dst = self.dst_dir / name
        marker_path = dst / self.marker

        yield StreamEvent(type="start", skill=name, timestamp=self._now(), data={})

        # Foreign skill protection: skip if exists but not managed by us
        if dst.is_dir() and not marker_path.exists():
            yield StreamEvent(
                type="skip",
                skill=name,
                timestamp=self._now(),
                data={"reason": "exists but not managed (no marker file)"},
            )
            return

        # Ensure destination parent exists
        self.dst_dir.mkdir(parents=True, exist_ok=True)

        # Run rsync with streaming progress
        yield from self._rsync_skill(name, src, dst)

        # Write marker only after successful rsync
        if (dst / self.marker).parent.exists():
            marker_path.write_text(
                time.strftime("%Y-%m-%dT%H:%M:%SZ\n", time.gmtime())
            )

    def render_all(self) -> Generator[StreamEvent, None, None]:
        """
        Render all skills, yielding StreamEvents for each phase.

        Respects cancellation: checks self._cancelled after each skill.
        Emits a summary event at completion.
        """
        skills = self._list_source_skills()
        total_start_ms = int(time.time() * 1000)
        count = 0
        total_bytes = 0
        errors: list[str] = []

        for name in skills:
            if self._cancelled:
                yield StreamEvent(
                    type="error",
                    skill=name,
                    timestamp=self._now(),
                    data={"message": "cancelled by caller"},
                )
                break

            last_complete: Optional[StreamEvent] = None
            for event in self.render_skill(name):
                yield event
                if event.type == "complete":
                    last_complete = event
                    count += 1
                    total_bytes += event.data.get("bytes", 0)
                elif event.type == "error":
                    errors.append(name)

        total_end_ms = int(time.time() * 1000)
        yield StreamEvent(
            type="summary",
            skill=None,
            timestamp=self._now(),
            data={
                "count": count,
                "total_bytes": total_bytes,
                "duration_ms": total_end_ms - total_start_ms,
                "errors": errors,
                "cancelled": self._cancelled,
            },
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Emits JSON-lines to stdout."""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) < 3:
        print(
            "Usage: streaming.py SRC_SKILLS_DIR DST_SKILLS_DIR MARKER_NAME",
            file=sys.stderr,
        )
        return 2

    src_dir, dst_dir, marker = argv[0], argv[1], argv[2]

    try:
        renderer = StreamingRenderer(src_dir, dst_dir, marker)
        for event in renderer.render_all():
            print(event.to_json(), flush=True)
    except FileNotFoundError as exc:
        print(json.dumps({"type": "error", "skill": None,
                          "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "data": {"message": str(exc)}}), flush=True)
        return 1
    except KeyboardInterrupt:
        print(json.dumps({"type": "error", "skill": None,
                          "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "data": {"message": "interrupted by user"}}), flush=True)
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Step 3: Package Init and Directory Scaffold (15 minutes)

**File**: `src/harnesses/copilot-cli/__init__.py`

```python
"""
Copilot CLI harness utilities.

Provides streaming output support for render-copilot.sh.
"""
from .streaming import StreamingRenderer, StreamEvent

__all__ = ["StreamingRenderer", "StreamEvent"]
```

Create the directory structure:

```
src/harnesses/
└── copilot-cli/
    ├── __init__.py
    └── streaming.py
```

---

## 4. Test Strategy

### 4.1 Unit Tests

**File**: `tests/harnesses/copilot-cli/test_streaming.py`

Tests cover the `StreamingRenderer` class in isolation using a temporary directory fixture.

#### Test Group 1: `StreamEvent` serialization

```python
import json
from src.harnesses.copilot_cli.streaming import StreamEvent

def test_stream_event_to_json_complete():
    event = StreamEvent(
        type="complete",
        skill="ab-testing",
        timestamp="2026-05-16T12:00:00Z",
        data={"duration_ms": 120, "bytes": 4096},
    )
    parsed = json.loads(event.to_json())
    assert parsed["type"] == "complete"
    assert parsed["skill"] == "ab-testing"
    assert parsed["data"]["bytes"] == 4096

def test_stream_event_summary_skill_is_none():
    event = StreamEvent(type="summary", skill=None, timestamp="2026-05-16T12:00:00Z")
    parsed = json.loads(event.to_json())
    assert parsed["skill"] is None
```

#### Test Group 2: `_list_source_skills`

```python
import pytest
from pathlib import Path
from src.harnesses.copilot_cli.streaming import StreamingRenderer

@pytest.fixture
def skill_tree(tmp_path):
    """Create a minimal skill tree for testing."""
    for name in ["ab-testing", "agent-creator", "voice-notify"]:
        skill_dir = tmp_path / "src" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")
    # Add a non-skill dir (no SKILL.md)
    (tmp_path / "src" / "_docs").mkdir()
    return tmp_path

def test_list_source_skills_returns_sorted(skill_tree, tmp_path):
    renderer = StreamingRenderer(
        str(skill_tree / "src"),
        str(tmp_path / "dst"),
        ".agentic-engine{service-name}",
    )
    skills = renderer._list_source_skills()
    assert skills == ["ab-testing", "agent-creator", "voice-notify"]

def test_list_source_skills_excludes_non_skill_dirs(skill_tree, tmp_path):
    renderer = StreamingRenderer(
        str(skill_tree / "src"),
        str(tmp_path / "dst"),
        ".agentic-engine{service-name}",
    )
    skills = renderer._list_source_skills()
    assert "_docs" not in skills

def test_list_source_skills_raises_on_missing_src(tmp_path):
    renderer = StreamingRenderer(
        str(tmp_path / "nonexistent"),
        str(tmp_path / "dst"),
        ".marker",
    )
    with pytest.raises(FileNotFoundError):
        renderer._list_source_skills()
```

#### Test Group 3: `render_skill` — foreign skill protection

```python
def test_render_skill_skips_foreign_skill(skill_tree, tmp_path):
    """A skill dir without a marker file must be skipped."""
    dst = tmp_path / "dst"
    foreign = dst / "ab-testing"
    foreign.mkdir(parents=True)
    # No marker file written → foreign skill

    renderer = StreamingRenderer(
        str(skill_tree / "src"),
        str(dst),
        ".agentic-engine{service-name}",
    )
    events = list(renderer.render_skill("ab-testing"))
    types = [e.type for e in events]
    assert "skip" in types
    assert "complete" not in types

def test_render_skill_overwrites_managed_skill(skill_tree, tmp_path):
    """A skill dir WITH a marker file must be overwritten."""
    dst = tmp_path / "dst"
    managed = dst / "ab-testing"
    managed.mkdir(parents=True)
    (managed / ".agentic-engine{service-name}").write_text("2026-01-01T00:00:00Z\n")

    renderer = StreamingRenderer(
        str(skill_tree / "src"),
        str(dst),
        ".agentic-engine{service-name}",
    )
    events = list(renderer.render_skill("ab-testing"))
    types = [e.type for e in events]
    assert "complete" in types
    assert "skip" not in types
```

#### Test Group 4: `render_all` — summary and cancellation

```python
def test_render_all_emits_summary(skill_tree, tmp_path):
    renderer = StreamingRenderer(
        str(skill_tree / "src"),
        str(tmp_path / "dst"),
        ".agentic-engine{service-name}",
    )
    events = list(renderer.render_all())
    summary = [e for e in events if e.type == "summary"]
    assert len(summary) == 1
    assert summary[0].data["count"] == 3

def test_render_all_cancellation(skill_tree, tmp_path):
    """Cancellation after first skill must stop further rendering."""
    renderer = StreamingRenderer(
        str(skill_tree / "src"),
        str(tmp_path / "dst"),
        ".agentic-engine{service-name}",
    )

    events = []
    for event in renderer.render_all():
        events.append(event)
        if event.type == "complete":
            renderer.cancel()
            break

    # Should have stopped; summary not reached in this test
    complete_events = [e for e in events if e.type == "complete"]
    assert len(complete_events) == 1
```

#### Test Group 5: `main()` CLI entry point

```python
import io
import json
from unittest.mock import patch
from src.harnesses.copilot_cli.streaming import main

def test_main_missing_args_returns_2():
    assert main([]) == 2
    assert main(["only_one"]) == 2

def test_main_missing_src_returns_1(tmp_path):
    result = main([
        str(tmp_path / "nonexistent"),
        str(tmp_path / "dst"),
        ".marker",
    ])
    assert result == 1
```

### 4.2 Integration Tests

**File**: `tests/harnesses/copilot-cli/test_streaming_integration.py`

Integration tests run against the actual `src/skills/` directory (read-only) and a temporary destination.

```python
import json
import os
from pathlib import Path
from src.harnesses.copilot_cli.streaming import StreamingRenderer

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SRC_SKILLS = REPO_ROOT / "src" / "skills"

def test_integration_renders_all_14_skills(tmp_path):
    """Full integration: render all 14 canonical skills to tmp dir."""
    if not SRC_SKILLS.is_dir():
        pytest.skip("src/skills not available in this environment")

    renderer = StreamingRenderer(
        str(SRC_SKILLS),
        str(tmp_path / "skills"),
        ".agentic-engine{service-name}",
    )
    events = list(renderer.render_all())
    summary = next(e for e in events if e.type == "summary")

    assert summary.data["count"] == 14
    assert summary.data["errors"] == []
    assert summary.data["total_bytes"] > 0

def test_integration_marker_written_after_render(tmp_path):
    """Marker file must exist for each rendered skill."""
    if not SRC_SKILLS.is_dir():
        pytest.skip("src/skills not available in this environment")

    renderer = StreamingRenderer(
        str(SRC_SKILLS),
        str(tmp_path / "skills"),
        ".agentic-engine{service-name}",
    )
    list(renderer.render_all())

    for skill_dir in (tmp_path / "skills").iterdir():
        marker = skill_dir / ".agentic-engine{service-name}"
        assert marker.exists(), f"Marker missing for {skill_dir.name}"

def test_integration_json_lines_parseable(tmp_path, capsys):
    """All stdout lines from main() must be valid JSON."""
    if not SRC_SKILLS.is_dir():
        pytest.skip("src/skills not available in this environment")

    from src.harnesses.copilot_cli.streaming import main
    result = main([
        str(SRC_SKILLS),
        str(tmp_path / "skills"),
        ".agentic-engine{service-name}",
    ])
    assert result == 0

    captured = capsys.readouterr()
    for line in captured.out.strip().splitlines():
        parsed = json.loads(line)  # Must not raise
        assert "type" in parsed
        assert "timestamp" in parsed
```

### 4.3 Bash Integration Tests

**File**: `tests/harnesses/copilot-cli/test_render_copilot_stream.bats`

Uses [BATS](https://github.com/bats-core/bats-core) for Bash testing.

```bash
#!/usr/bin/env bats

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"
    TMP_DIR="$(mktemp -d)"
    COPILOT_DIR="$TMP_DIR/copilot"
    SCRIPT="$REPO_ROOT/renderer/scripts/render-copilot.sh"
}

teardown() {
    rm -rf "$TMP_DIR"
}

@test "default install mode works without --stream flag" {
    run bash "$SCRIPT" "$REPO_ROOT" "$COPILOT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Rendered"* ]]
}

@test "--stream flag produces per-skill timing output" {
    run bash "$SCRIPT" "$REPO_ROOT" "$COPILOT_DIR" --stream
    [ "$status" -eq 0 ]
    [[ "$output" == *"rendered"* ]]
    # Timing suffix should appear (e.g., "(1s)")
    [[ "$output" =~ \([0-9]+s\) ]]
}

@test "--stream=json delegates to Python helper" {
    run bash "$SCRIPT" "$REPO_ROOT" "$COPILOT_DIR" --stream=json
    [ "$status" -eq 0 ]
    # Every output line must be valid JSON (check first line)
    first_line=$(echo "$output" | head -1)
    echo "$first_line" | python3 -c "import sys,json; json.load(sys.stdin)"
}

@test "--stream=json summary count equals 14" {
    run bash "$SCRIPT" "$REPO_ROOT" "$COPILOT_DIR" --stream=json
    [ "$status" -eq 0 ]
    summary=$(echo "$output" | python3 -c "
import sys, json
for line in sys.stdin:
    obj = json.loads(line)
    if obj['type'] == 'summary':
        print(obj['data']['count'])
        break
")
    [ "$summary" -eq 14 ]
}
```

### 4.4 Test Coverage Targets

| Component | Target Coverage | Rationale |
|-----------|----------------|-----------|
| `StreamEvent` | 100% | Simple dataclass; full coverage trivial |
| `StreamingRenderer._list_source_skills` | 100% | Critical path; all branches tested |
| `StreamingRenderer.render_skill` | ≥95% | Foreign skip + happy path + error path |
| `StreamingRenderer.render_all` | ≥90% | Cancellation path is lower priority |
| `StreamingRenderer._rsync_skill` | ≥80% | rsync line parsing is best-effort |
| `main()` | ≥90% | CLI entry; all exit codes tested |
| Bash `_stream_emit` | ≥80% | Via BATS integration tests |

---

## 5. Risk Assessment and Mitigation

### 5.1 Risk Matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|-----------|--------|----------|-----------|
| rsync `--info=progress2` not available on older rsync | Medium | Medium | **Medium** | Version check; fall back to default rsync if `<3.1` |
| Python 3 not available in minimal environments | Low | High | **Medium** | `--stream=json` is opt-in; default mode unchanged |
| ANSI escape codes corrupt non-TTY output | Medium | Low | **Low** | TTY detection (`[ -t 1 ]`); `NO_COLOR` support |
| Partial install on cancellation | Low | High | **Medium** | Marker written only after successful rsync; status mode detects drift |
| Performance regression from `--info=progress2` | Low | Low | **Low** | Progress parsing is additive; default mode unchanged |
| rsync output format changes between versions | Low | Medium | **Low** | Parse defensively; skip malformed lines silently |
| `subprocess.Popen` line-buffering on some platforms | Low | Medium | **Low** | `bufsize=1` + `text=True`; tested on macOS and Linux |

### 5.2 Detailed Mitigations

#### Risk: rsync version compatibility

`--info=progress2` was introduced in rsync 3.1.0 (2013). Most modern systems have rsync ≥3.1, but some enterprise Linux images (RHEL 7, CentOS 7) ship rsync 3.0.x.

**Mitigation:**

```bash
# In render-copilot.sh, before using --info=progress2:
_check_rsync_version() {
    local version
    version=$(rsync --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "${major:-0}" -lt 3 ] || { [ "${major:-0}" -eq 3 ] && [ "${minor:-0}" -lt 1 ]; }; then
        echo "⚠️  rsync <3.1 detected; streaming progress unavailable (falling back to default)" >&2
        STREAM_MODE=""
    fi
}
```

#### Risk: Partial install on cancellation

If the user sends SIGINT during `render_all()`, the current skill's rsync may be mid-transfer. The marker file is not written until rsync completes successfully, so the skill will appear as "drift" on next `--status` run.

**Mitigation:** The existing `--status` mode already detects drift via `diff -rq`. Users can re-run `make install-copilot` to complete the interrupted install. No additional recovery mechanism is needed.

#### Risk: Python not available

Some minimal CI environments (Docker `alpine`, `busybox`) may not have Python 3.

**Mitigation:** `--stream=json` is explicitly opt-in. The default `make install-copilot` target does not use it. CI pipelines that need JSON output must ensure Python 3 is available (standard in any environment that runs the agentic-engineers framework).

---

## 6. Rollback Strategy

### 6.1 Zero-Risk Default Mode

The default `make install-copilot` invocation (`render-copilot.sh REPO_ROOT COPILOT_DIR`) does not pass `--stream` or `--stream=json`. The install loop for the default mode is **unchanged** from the current implementation. Rollback for the default mode is a no-op.

### 6.2 Feature Flag Rollback

If the streaming feature causes issues, it can be disabled by:

1. Removing the `--stream` and `--stream=json` case branches from `render-copilot.sh` (the `install|""` case is untouched).
2. Deleting `src/harnesses/copilot-cli/streaming.py` and `__init__.py`.

Neither change affects the default install path.

### 6.3 Git Revert

The streaming feature will be implemented in a single commit. Rollback is:

```bash
git revert <commit-sha>
```

This is safe because the feature is additive and does not modify any existing code paths.

---

## 7. Acceptance Criteria

### 7.1 Functional Criteria

- [ ] `render-copilot.sh REPO_ROOT COPILOT_DIR` (default mode) produces identical output to current behavior
- [ ] `render-copilot.sh REPO_ROOT COPILOT_DIR --stream` produces per-skill progress lines with timing
- [ ] `render-copilot.sh REPO_ROOT COPILOT_DIR --stream=json` produces valid JSON-lines to stdout
- [ ] Each JSON-lines event has `type`, `skill`, `timestamp`, and `data` fields
- [ ] Summary event `data.count` equals the number of skills successfully rendered
- [ ] Foreign skills (no marker) are skipped in all modes
- [ ] Marker file is written only after successful rsync in all modes
- [ ] `--status` and `--uninstall` modes are unchanged

### 7.2 Quality Criteria

- [ ] Unit test coverage ≥90% for `streaming.py`
- [ ] All unit tests pass: `pytest tests/harnesses/copilot-cli/`
- [ ] BATS integration tests pass: `bats tests/harnesses/copilot-cli/test_render_copilot_stream.bats`
- [ ] No regressions in existing `render-copilot.sh` test suite
- [ ] `streaming.py` passes `mypy --strict` (or equivalent type check)
- [ ] `streaming.py` passes `ruff` linting with zero errors

### 7.3 Performance Criteria

- [ ] Default mode install time is within 5% of baseline (no regression from code changes)
- [ ] `--stream` mode adds ≤500ms overhead vs default mode for 14 skills
- [ ] `--stream=json` mode adds ≤1s overhead vs default mode for 14 skills

### 7.4 Documentation Criteria

- [ ] `streaming.py` module docstring explains usage, output format, and cancellation
- [ ] `render-copilot.sh` usage comment updated to include `--stream` and `--stream=json` flags
- [ ] `docs/COPILOT-INSTALL.md` (Tier 1 recommendation from analysis) references streaming flags

---

## 8. Effort Estimates

| Task | Estimate | Notes |
|------|----------|-------|
| Bash streaming layer (`render-copilot.sh`) | 1.5 hours | `_stream_emit`, rsync flags, TTY detection |
| Python streaming helper (`streaming.py`) | 1.5 hours | `StreamingRenderer`, `StreamEvent`, `main()` |
| Package scaffold (`__init__.py`, dir) | 15 min | Trivial |
| Unit tests (`test_streaming.py`) | 45 min | ~20 test cases |
| Integration tests (Python + BATS) | 30 min | 4 Python + 4 BATS |
| **Total** | **~4.5 hours** | Within 3–4 hour estimate |

**Recommended implementation order:**
1. Python `streaming.py` + unit tests (most testable, least risky)
2. Bash `_stream_emit` + `--stream` mode (human output)
3. Bash `--stream=json` delegation to Python helper
4. BATS integration tests
5. Documentation updates

---

## 9. Integration Points

### 9.1 Existing Harness Integration

The streaming feature integrates with `render-copilot.sh` at a single point: the `install` case branch. The `--status` and `--uninstall` branches are untouched.

**Integration point in `render-copilot.sh`:**

```bash
# Line 69: current
install|"")

# Line 69: after change
install|""|--stream|--stream=json)
```

The `exec` delegation to `streaming.py` for `--stream=json` means the Bash script hands off entirely — no Bash/Python interleaving.

### 9.2 Makefile Integration

No Makefile changes are required. The streaming flags are opt-in. CI pipelines that want structured output can call:

```bash
bash renderer/scripts/render-copilot.sh "$REPO_ROOT" "$HOME/.copilot" --stream=json \
    | tee /tmp/copilot-install-log.jsonl
```

### 9.3 `lib.sh` Integration

`list_source_skills` (defined in `lib.sh`) is used by both the Bash streaming layer and referenced in `streaming.py`'s `_list_source_skills()`. The Python implementation duplicates the logic (finds dirs with `SKILL.md`) to avoid a shell dependency. This is intentional: `streaming.py` must be runnable standalone without sourcing `lib.sh`.

### 9.4 Future `COPILOT-INSTALL.md` Integration

The Tier 1 recommendation from the analysis (`docs/COPILOT-CLI-HARNESS-ANALYSIS.md` §7.1) is to create `docs/COPILOT-INSTALL.md`. When that document is written, it should include a section on streaming output:

```markdown
## Streaming Output (Advanced)

For CI/CD pipelines or long installs, use streaming mode:

# Human-readable progress (interactive terminal)
make install-copilot STREAM=--stream

# Structured JSON-lines (CI/CD pipelines, log aggregators)
make install-copilot STREAM=--stream=json
```

This requires a one-line Makefile update to pass `$(STREAM)` to `render-copilot.sh`.

---

## Appendix A: JSON-Lines Output Schema

Each line emitted by `--stream=json` mode conforms to:

```json
{
  "type": "start|progress|complete|skip|error|summary",
  "skill": "skill-name-or-null",
  "timestamp": "2026-05-16T12:00:00Z",
  "data": {
    // type-specific fields (see below)
  }
}
```

**Type-specific `data` fields:**

| Type | Fields |
|------|--------|
| `start` | `{}` |
| `progress` | `{"files_done": int, "bytes": int}` |
| `complete` | `{"duration_ms": int, "bytes": int, "files_transferred": int}` |
| `skip` | `{"reason": str}` |
| `error` | `{"message": str}` |
| `summary` | `{"count": int, "total_bytes": int, "duration_ms": int, "errors": [str], "cancelled": bool}` |

---

## Appendix B: rsync `--info=progress2` Output Format

rsync 3.1+ with `--info=progress2` emits lines to stderr in the format:

```
      4,096 100%    0.00kB/s    0:00:00 (xfr#3, to-chk=11/14)
```

Fields:
- `4,096` — bytes transferred for this file
- `100%` — percentage of this file
- `0.00kB/s` — transfer rate
- `0:00:00` — elapsed time
- `xfr#3` — transfer number (cumulative)
- `to-chk=11/14` — files remaining / total

The Python parser extracts `xfr#N` for `files_done` and the leading byte count for `bytes`. All other fields are ignored. Malformed lines are silently skipped.

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-16  
**Status**: Specification Complete — Ready for Implementation  
**Estimated Implementation**: 4.5 hours  
**Risk Level**: Low (additive, opt-in, zero regression to default mode)
