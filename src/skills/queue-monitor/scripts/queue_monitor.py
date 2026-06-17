#!/usr/bin/env python3
"""
Queue Monitor Dashboard — Live curses-based TUI for agentic-engineers queue.

Displays real-time DELEGATE/HANDBACK status across incoming, processing, and done states.
Features: 3-column layout, metrics aggregation, auto-refresh polling (5s interval).
"""

import argparse
import curses
import json
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class TaskMetadata:
    """Parsed DELEGATE or HANDBACK task metadata."""

    task_id: str
    agent: Optional[str] = None
    status: Optional[str] = None  # success | failure | processing
    duration_seconds: Optional[int] = None
    file_mtime: float = 0.0
    file_path: str = ""
    task_type: str = "unknown"  # DELEGATE or HANDBACK


@dataclass
class QueueState:
    """Current queue state snapshot."""

    incoming: List[TaskMetadata] = field(default_factory=list)
    processing: List[TaskMetadata] = field(default_factory=list)
    done: List[TaskMetadata] = field(default_factory=list)
    failed: List[TaskMetadata] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class QueueMonitor:
    """Filesystem-backed queue monitor; handles polling and metrics."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        base_dir: Optional[str] = None,
        auto_detect: bool = True,
    ):
        """Initialize monitor with session, harness, and optional base directory."""
        self.session_id = session_id
        self.harness = harness
        self.base_dir = Path(base_dir) if base_dir else Path.home() / ".agentic-engineers"
        self.queue_root: Optional[Path] = None
        if auto_detect:
            self._detect_queue_path()
        self.state = QueueState()
        self.poll_count = 0

    def _detect_queue_path(self) -> None:
        """Auto-detect queue root from session_id and harness, or scan for latest."""
        if self.session_id and self.harness:
            queue_path = (
                self.base_dir / self.harness / self.session_id / "queue"
            )
            if queue_path.exists():
                self.queue_root = queue_path
                return

        # Fall back: find latest session in harness
        if self.harness:
            harness_dir = self.base_dir / self.harness
            if harness_dir.exists():
                sessions = sorted(
                    [d for d in harness_dir.iterdir() if d.is_dir()],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if sessions:
                    queue_path = sessions[0] / "queue"
                    if queue_path.exists():
                        self.queue_root = queue_path
                        self.session_id = sessions[0].name
                        return

        # Fall back: scan all harnesses for latest session
        if self.base_dir.exists():
            latest_queue = None
            latest_mtime = 0
            for harness_dir in self.base_dir.iterdir():
                if not harness_dir.is_dir():
                    continue
                for session_dir in harness_dir.iterdir():
                    if not session_dir.is_dir():
                        continue
                    queue_path = session_dir / "queue"
                    if queue_path.exists():
                        mtime = queue_path.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_queue = queue_path
                            self.session_id = session_dir.name
                            self.harness = harness_dir.name

            if latest_queue:
                self.queue_root = latest_queue

        if not self.queue_root:
            raise RuntimeError(
                f"Could not locate queue. Check --session-id and --harness flags."
            )

    def poll(self) -> None:
        """Refresh queue state from filesystem."""
        self.state = QueueState()

        if not self.queue_root:
            return

        for state_dir in ["incoming", "processing", "done", "failed"]:
            state_path = self.queue_root / state_dir
            if not state_path.exists():
                continue

            for file_path in sorted(state_path.iterdir()):
                if file_path.suffix not in [".yaml", ".json"]:
                    continue

                task = self._parse_task_file(file_path, state_dir)
                if task:
                    state_list = getattr(self.state, state_dir)
                    state_list.append(task)

        self.state.last_updated = datetime.now(timezone.utc)
        self.poll_count += 1

    def _parse_task_file(self, file_path: Path, state: str) -> Optional[TaskMetadata]:
        """Parse DELEGATE or HANDBACK YAML/JSON file."""
        try:
            content = file_path.read_text()

            # Try YAML first
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError:
                # Fall back to JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    return None

            if not isinstance(data, dict):
                return None

            task_id = data.get("task_id", file_path.stem)
            handoff_type = data.get("handoff_type", "UNKNOWN")
            agent = data.get("agent")
            status = data.get("status")
            mtime = file_path.stat().st_mtime

            # Calculate duration if HANDBACK with metrics
            duration_seconds = None
            if handoff_type == "HANDBACK" and data.get("metrics"):
                metrics = data["metrics"]
                if isinstance(metrics, dict):
                    duration_seconds = metrics.get("duration_seconds")

            # For processing tasks, estimate from file mtime
            if state == "processing" and duration_seconds is None:
                now = time.time()
                duration_seconds = int(now - mtime)

            return TaskMetadata(
                task_id=task_id,
                agent=agent,
                status=status if handoff_type == "HANDBACK" else None,
                duration_seconds=duration_seconds,
                file_mtime=mtime,
                file_path=str(file_path),
                task_type=handoff_type,
            )

        except Exception:
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """Return aggregated queue metrics."""
        done_tasks = self.state.done
        succeeded = sum(1 for t in done_tasks if t.status == "success")
        failed = sum(1 for t in done_tasks if t.status == "failure")
        total_done = len(done_tasks)

        durations = [t.duration_seconds for t in done_tasks if t.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0

        success_rate = (succeeded / total_done * 100) if total_done > 0 else 0

        return {
            "incoming_count": len(self.state.incoming),
            "processing_count": len(self.state.processing),
            "done_count": total_done,
            "failed_count": failed,
            "succeeded_count": succeeded,
            "success_rate": success_rate,
            "avg_duration_seconds": int(avg_duration),
            "last_updated": self.state.last_updated.isoformat(),
        }


class QueueMonitorUI:
    """Curses-based TUI for queue monitor."""

    COLORS = {
        "success": 1,
        "failure": 2,
        "processing": 3,
        "header": 4,
        "normal": 5,
    }

    def __init__(self, monitor: QueueMonitor):
        """Initialize UI with monitor instance."""
        self.monitor = monitor
        self.running = True
        self.last_poll = 0.0
        self.poll_interval = 5.0  # seconds
        self.help_visible = False
        signal.signal(signal.SIGWINCH, self._on_resize)

    def _on_resize(self, signum, frame):
        """Handle terminal resize."""
        # Trigger screen redraw on resize
        pass

    def run(self) -> None:
        """Run the curses TUI event loop."""
        try:
            curses.wrapper(self._main_loop)
        except KeyboardInterrupt:
            self.running = False

    def _main_loop(self, stdscr: Any) -> None:
        """Main curses event loop."""
        self._setup_colors(stdscr)
        stdscr.nodelay(True)
        stdscr.timeout(100)  # 100ms timeout on getch

        while self.running:
            try:
                # Poll at interval
                now = time.time()
                if now - self.last_poll >= self.poll_interval:
                    self.monitor.poll()
                    self.last_poll = now

                # Handle input (non-blocking)
                try:
                    ch = stdscr.getch()
                    if ch != curses.ERR:
                        self._handle_input(ch)
                except curses.error:
                    pass

                # Render
                stdscr.erase()
                self._render(stdscr)
                stdscr.refresh()

            except curses.error:
                # Handle terminal resize or other curses errors
                pass

    def _setup_colors(self, stdscr: Any) -> None:
        """Initialize color pairs."""
        if curses.has_colors():
            curses.init_pair(self.COLORS["success"], curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(self.COLORS["failure"], curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(self.COLORS["processing"], curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(self.COLORS["header"], curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(self.COLORS["normal"], curses.COLOR_WHITE, curses.COLOR_BLACK)

    def _handle_input(self, ch: int) -> None:
        """Handle keyboard input."""
        if ch == ord("q"):
            self.running = False
        elif ch == ord("r"):
            self.last_poll = 0  # Force refresh
        elif ch == ord("?"):
            self.help_visible = not self.help_visible

    def _render(self, stdscr: Any) -> None:
        """Render dashboard to screen."""
        height, width = stdscr.getmaxyx()

        # Header
        header = "QUEUE MONITOR — agentic-engineers"
        self._render_line(stdscr, 0, header, self.COLORS["header"])

        # Status line
        metrics = self.monitor.get_metrics()
        status = (
            f"Status: {metrics['incoming_count']} incoming, "
            f"{metrics['processing_count']} processing, "
            f"{metrics['done_count']} done"
        )
        self._render_line(stdscr, 1, status, self.COLORS["normal"])

        # Column headers and separators
        col_width = width // 3
        y = 3
        self._render_three_columns(stdscr, y, col_width, "INCOMING", "PROCESSING", "DONE")

        # Task lists
        y = 5
        self._render_task_columns(stdscr, y, col_width, height - y - 4)

        # Metrics footer
        footer_y = height - 3
        self._render_metrics_footer(stdscr, footer_y, metrics)

        # Help/status line
        if self.help_visible:
            help_text = "q: quit  r: refresh  ?: toggle help"
        else:
            help_text = f"Poll #{self.monitor.poll_count}  Last update: {datetime.now().strftime('%H:%M:%S')}  Press ? for help"
        self._render_line(stdscr, height - 1, help_text, self.COLORS["normal"])

    def _render_line(self, stdscr: Any, y: int, text: str, color_pair: int) -> None:
        """Render a single line with color."""
        try:
            if curses.has_colors():
                stdscr.addstr(y, 0, text, curses.color_pair(color_pair))
            else:
                stdscr.addstr(y, 0, text)
        except curses.error:
            pass

    def _render_three_columns(
        self, stdscr: Any, y: int, col_width: int, h1: str, h2: str, h3: str
    ) -> None:
        """Render three column headers."""
        try:
            h1_text = h1.ljust(col_width)[:col_width]
            h2_text = h2.ljust(col_width)[:col_width]
            h3_text = h3.ljust(col_width)[:col_width]
            line = h1_text + h2_text + h3_text
            self._render_line(stdscr, y, line, self.COLORS["header"])
        except curses.error:
            pass

    def _render_task_columns(self, stdscr: Any, start_y: int, col_width: int, max_rows: int) -> None:
        """Render task lists in three columns."""
        try:
            # Get tasks for each state
            incoming = self.monitor.state.incoming[:max_rows]
            processing = self.monitor.state.processing[:max_rows]
            done = self.monitor.state.done[:max_rows]

            for i in range(max_rows):
                y = start_y + i

                # Incoming column
                if i < len(incoming):
                    task = incoming[i]
                    text = f"{task.task_id[:col_width-2]}"
                    stdscr.addstr(y, 0, text.ljust(col_width)[:col_width])

                # Processing column
                if i < len(processing):
                    task = processing[i]
                    duration_text = f"{task.duration_seconds}s" if task.duration_seconds else "?"
                    text = f"{task.task_id[:col_width-8]} {duration_text}"
                    if curses.has_colors():
                        stdscr.addstr(y, col_width, text.ljust(col_width)[:col_width], curses.color_pair(self.COLORS["processing"]))
                    else:
                        stdscr.addstr(y, col_width, text.ljust(col_width)[:col_width])

                # Done column
                if i < len(done):
                    task = done[i]
                    status_icon = "✓" if task.status == "success" else "✗" if task.status == "failure" else "?"
                    text = f"{task.task_id[:col_width-6]} {status_icon}"
                    color = self.COLORS["success"] if task.status == "success" else self.COLORS["failure"]
                    if curses.has_colors():
                        stdscr.addstr(y, 2 * col_width, text.ljust(col_width)[:col_width], curses.color_pair(color))
                    else:
                        stdscr.addstr(y, 2 * col_width, text.ljust(col_width)[:col_width])

        except curses.error:
            pass

    def _render_metrics_footer(self, stdscr: Any, y: int, metrics: Dict) -> None:
        """Render metrics summary footer."""
        try:
            success_pct = f"{metrics['success_rate']:.0f}%" if metrics['done_count'] > 0 else "N/A"
            metrics_text = (
                f"Incoming: {metrics['incoming_count']}  Processing: {metrics['processing_count']}  "
                f"Done: {metrics['done_count']} (success: {metrics['succeeded_count']}, failure: {metrics['failed_count']})  "
                f"Avg duration: {metrics['avg_duration_seconds']}s  Success rate: {success_pct}"
            )
            self._render_line(stdscr, y, metrics_text, self.COLORS["header"])
        except curses.error:
            pass


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Live queue monitoring dashboard for agentic-engineers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python queue_monitor.py                                    # auto-detect
  python queue_monitor.py --session-id wave1-2026-06-15 --harness claude
  python queue_monitor.py --base-dir /custom --harness local

Controls:
  q         Quit
  r         Refresh now
  ?         Toggle help
        """,
    )
    parser.add_argument(
        "--session-id",
        help="Session ID (auto-detect if omitted)",
        default=None,
    )
    parser.add_argument(
        "--harness",
        help="Harness name (auto-detect if omitted)",
        default=None,
    )
    parser.add_argument(
        "--base-dir",
        help="Base directory for queue (default: ~/.agentic-engineers)",
        default=None,
    )

    args = parser.parse_args()

    try:
        monitor = QueueMonitor(
            session_id=args.session_id,
            harness=args.harness,
            base_dir=args.base_dir,
        )
        print(f"Starting queue monitor...")
        print(f"  Session: {monitor.session_id}")
        print(f"  Harness: {monitor.harness}")
        print(f"  Queue root: {monitor.queue_root}")
        print()

        ui = QueueMonitorUI(monitor)
        ui.run()

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nQueue monitor stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
