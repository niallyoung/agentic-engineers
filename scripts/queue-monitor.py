#!/usr/bin/env python3
"""
Queue Monitor Dashboard — Live curses TUI for monitoring DELEGATE/HANDBACK queue state.

Usage:
    python3 scripts/queue-monitor.py [--harness HARNESS] [--session SESSION]

Default harness: claude
Default session: 2026-06-14-111501

Displays:
  - Queue state counts (incoming/processing/done/failed)
  - Active processing tasks with agent, elapsed time
  - Rolling 5-item activity log
  - Polls queue every 5 seconds

Exit: Press 'q' or Ctrl-C to exit cleanly
"""

import curses
import argparse
import sys
import os
import time
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class QueueMonitor:
    """Curses TUI for monitoring queue state."""

    def __init__(self, harness: str = "claude", session: str = "2026-06-14-111501"):
        """
        Initialize queue monitor.

        Args:
            harness: Harness name (default: claude)
            session: Session ID (default: 2026-06-14-111501)
        """
        self.harness = harness
        self.session = session
        self.queue_path = Path.home() / ".agentic-engineers" / harness / session / "queue"
        self.running = True
        self.last_poll_time = 0
        self.poll_interval = 5  # seconds
        self.activity_log: List[str] = []
        self.max_log_items = 5

    def poll_queue(self) -> Dict[str, int]:
        """
        Poll queue directory and return counts per state.

        Returns:
            Dict with keys: incoming, processing, done, failed
        """
        counts = {"incoming": 0, "processing": 0, "done": 0, "failed": 0}

        if not self.queue_path.exists():
            self.add_log(f"Queue path not found: {self.queue_path}")
            return counts

        for state in counts.keys():
            state_dir = self.queue_path / state
            if state_dir.exists() and state_dir.is_dir():
                yaml_files = list(state_dir.glob("*.yaml"))
                counts[state] = len(yaml_files)

        return counts

    def get_processing_tasks(self) -> List[Tuple[str, str, float]]:
        """
        Get processing tasks with task_id, agent, and elapsed time.

        Returns:
            List of tuples: (task_id, agent, elapsed_seconds)
        """
        tasks = []
        processing_dir = self.queue_path / "processing"

        if not processing_dir.exists():
            return tasks

        for yaml_file in processing_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                    task_id = data.get("task_id", "unknown")
                    agent = data.get("agent", "unknown")

                    # Calculate elapsed time from file mtime
                    mtime = yaml_file.stat().st_mtime
                    elapsed = time.time() - mtime

                    tasks.append((task_id, agent, elapsed))
            except Exception:
                pass

        # Sort by elapsed time (oldest first)
        tasks.sort(key=lambda x: x[2], reverse=True)
        return tasks[:5]  # Limit to 5 active tasks

    def add_log(self, message: str) -> None:
        """Add message to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")
        if len(self.activity_log) > self.max_log_items:
            self.activity_log.pop(0)

    def format_elapsed(self, seconds: float) -> str:
        """Format elapsed time as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def draw_ui(self, stdscr) -> None:
        """Draw the curses UI."""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(100)  # 100ms timeout for getch()

        # Color pairs
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Active
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Pending
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)  # Failed
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Info

        last_counts = None

        while self.running:
            try:
                stdscr.clear()
                height, width = stdscr.getmaxyx()

                # Current time
                now = time.time()
                if now - self.last_poll_time >= self.poll_interval:
                    counts = self.poll_queue()
                    if counts != last_counts:
                        self.add_log("Queue updated")
                    last_counts = counts
                    self.last_poll_time = now

                row = 0

                # Header: Title
                title = " Queue Monitor Dashboard "
                stdscr.addstr(row, 0, title, curses.color_pair(1) | curses.A_BOLD)
                row += 1

                # Queue counts
                counts = self.poll_queue()
                counts_line = (
                    f"Incoming: {counts['incoming']:3d}  |  "
                    f"Processing: {counts['processing']:3d}  |  "
                    f"Done: {counts['done']:3d}  |  "
                    f"Failed: {counts['failed']:3d}"
                )
                stdscr.addstr(row, 0, counts_line, curses.color_pair(5))
                row += 2

                # Processing tasks
                stdscr.addstr(row, 0, "Active Processing Tasks:", curses.A_BOLD)
                row += 1

                tasks = self.get_processing_tasks()
                if tasks:
                    # Header row
                    header = f"{'Task ID':<30} | {'Agent':<20} | {'Elapsed':<10}"
                    stdscr.addstr(row, 0, header, curses.A_UNDERLINE)
                    row += 1

                    for task_id, agent, elapsed in tasks:
                        elapsed_str = self.format_elapsed(elapsed)
                        task_line = f"{task_id:<30} | {agent:<20} | {elapsed_str:<10}"
                        if row < height - 10:  # Leave space for log
                            stdscr.addstr(row, 0, task_line, curses.color_pair(2))
                            row += 1
                else:
                    stdscr.addstr(row, 0, "  (none)", curses.color_pair(3))
                    row += 1

                row += 1

                # Activity log
                stdscr.addstr(row, 0, "Activity Log:", curses.A_BOLD)
                row += 1

                for log_msg in self.activity_log[-self.max_log_items :]:
                    if row < height - 2:
                        stdscr.addstr(row, 0, f"  {log_msg}")
                        row += 1

                # Footer: Help text
                if height > row + 1:
                    footer = "Press 'q' or Ctrl-C to exit"
                    stdscr.addstr(
                        height - 1, 0, footer, curses.color_pair(3) | curses.A_DIM
                    )

                stdscr.refresh()

                # Check for input
                try:
                    ch = stdscr.getch()
                    if ch == ord("q") or ch == ord("Q"):
                        self.running = False
                except KeyboardInterrupt:
                    self.running = False

            except curses.error:
                # Handle curses errors (e.g., screen too small)
                pass
            except Exception:
                pass

    def run(self) -> None:
        """Run the monitor."""
        # Check if we're in a TTY
        if not sys.stdout.isatty():
            print("Error: Not running in a terminal (TTY). queue-monitor requires an interactive terminal.")
            sys.exit(1)

        # Check if queue path exists
        if not self.queue_path.exists():
            print(f"Error: Queue path not found: {self.queue_path}")
            sys.exit(1)

        try:
            curses.wrapper(self.draw_ui)
        except KeyboardInterrupt:
            pass
        finally:
            # Ensure cursor is shown on exit
            try:
                curses.curs_set(1)
            except:
                pass


def main():
    """Entry point for queue monitor."""
    parser = argparse.ArgumentParser(
        description="Monitor DELEGATE/HANDBACK queue state in real-time."
    )
    parser.add_argument(
        "--harness",
        default="claude",
        help="Harness name (default: claude)",
    )
    parser.add_argument(
        "--session",
        default="2026-06-14-111501",
        help="Session ID (default: 2026-06-14-111501)",
    )

    args = parser.parse_args()

    monitor = QueueMonitor(harness=args.harness, session=args.session)
    monitor.run()


if __name__ == "__main__":
    main()
