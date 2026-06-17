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

import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
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

    Thread-safe: Uses per-skill lock files to prevent concurrent rsync
    operations on the same skill directory, and atomic marker writes
    to prevent data races.

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
        self._lock_dir = Path(tempfile.gettempdir()) / "copilot-renderer-locks"
        self._lock_dir.mkdir(exist_ok=True, parents=True)

    def cancel(self) -> None:
        """Request graceful cancellation after the current skill completes."""
        self._cancelled = True

    def _now(self) -> str:
        """Return current UTC timestamp in ISO 8601 format."""
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _get_skill_lock_path(self, skill_name: str) -> Path:
        """Return path to lock file for a skill (prevents concurrent rsync on same skill)."""
        # Use sanitized skill name as lock file name
        safe_name = skill_name.replace("/", "_").replace("\\", "_")
        return self._lock_dir / f"{safe_name}.lock"

    def _acquire_skill_lock(self, skill_name: str) -> object:
        """
        Acquire an exclusive lock for a skill to prevent concurrent rsync operations.

        Returns a file object that must be closed to release the lock.
        This uses fcntl.flock on Unix systems (macOS, Linux, etc.).
        """
        lock_path = self._get_skill_lock_path(skill_name)
        lock_file = open(lock_path, "w")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            return lock_file
        except Exception:
            lock_file.close()
            raise

    def _release_skill_lock(self, lock_file: object) -> None:
        """Release a skill lock."""
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                lock_file.close()

    def _write_marker_atomic(self, marker_path: Path) -> None:
        """
        Write marker file atomically (write to temp file then rename).

        This prevents partial writes and ensures the marker is either
        fully present or fully absent—no in-between states that could
        cause another thread to see a corrupted marker.
        """
        content = time.strftime("%Y-%m-%dT%H:%M:%SZ\n", time.gmtime())

        # Ensure parent directory exists
        marker_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temporary file in the same directory
        # (ensures same filesystem for atomic rename)
        fd, temp_path = tempfile.mkstemp(dir=str(marker_path.parent), text=True)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            # Atomic rename (on POSIX systems)
            os.replace(temp_path, str(marker_path))
        except Exception:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

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
        Falls back to regular rsync if --info=progress2 is not available.
        Parses rsync stderr for byte-count and file-count updates.
        """
        # Try with --info=progress2 first (rsync 3.1+)
        cmd_with_progress = [
            "rsync", "-a", "--delete",
            "--info=progress2",
            "--exclude=.DS_Store",
            "--exclude=.git",
            f"{src}/",
            f"{dst}/",
        ]
        
        # Fallback command without progress (for older rsync)
        cmd_without_progress = [
            "rsync", "-a", "--delete",
            "--exclude=.DS_Store",
            "--exclude=.git",
            f"{src}/",
            f"{dst}/",
        ]

        start_ms = int(time.time() * 1000)

        # Try with progress first
        try:
            proc = subprocess.Popen(
                cmd_with_progress,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # line-buffered
            )
        except (FileNotFoundError, OSError) as exc:
            yield StreamEvent(
                type="error",
                skill=name,
                timestamp=self._now(),
                data={"message": f"rsync not available: {exc}"},
            )
            return

        files_done = 0
        bytes_transferred = 0
        fallback_used = False

        # Stream rsync output line by line
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            # Check if we got an error about unrecognized option
            if "unrecognized option" in line and "info" in line:
                # Fall back to rsync without progress
                proc.terminate()
                proc.wait()
                fallback_used = True
                break
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

        if fallback_used:
            # Run rsync without progress
            proc = subprocess.Popen(
                cmd_without_progress,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            proc.wait()
        else:
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

        Thread-safe: Uses per-skill locks to prevent concurrent rsync
        operations on the same skill directory.
        """
        src = self.src_dir / name
        dst = self.dst_dir / name
        marker_path = dst / self.marker

        yield StreamEvent(type="start", skill=name, timestamp=self._now(), data={})

        # Acquire exclusive lock for this skill to prevent concurrent rsync
        lock_file = None
        try:
            lock_file = self._acquire_skill_lock(name)

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

            # Write marker atomically after successful rsync
            if (dst / self.marker).parent.exists():
                self._write_marker_atomic(marker_path)

        finally:
            # Always release the lock
            if lock_file:
                self._release_skill_lock(lock_file)

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
