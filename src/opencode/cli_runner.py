"""CLI tool for TaskRunner - Real-time task monitoring and management.

Provides commands for task submission, status monitoring, listing, cancellation,
and retry management with JSON and human-readable output formats.

Commands:
    run       - Submit and run a task
    status    - Get status of a specific task
    list      - List all tasks (with optional filtering)
    cancel    - Cancel a task
    retry     - Retry a failed task
    init      - Initialize queue structure

Examples::

    # Initialize queue structure
    opencode-runner init

    # Submit a task
    opencode-runner run --role engineer --description "Fix bug in auth"

    # Check task status
    opencode-runner status TASK-ABC123

    # List all tasks
    opencode-runner list --state done

    # Cancel a task
    opencode-runner cancel TASK-ABC123

    # Retry a failed task
    opencode-runner retry TASK-ABC123
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .runner import TaskRunner, TaskState

logger = logging.getLogger(__name__)


class CLIRunner:
    """Command-line interface for TaskRunner."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        base_dir: Optional[Path] = None,
        output_format: str = "text",
    ) -> None:
        """Initialize CLI runner.

        Args:
            session_id: Session ID (auto-detected if None)
            harness: Harness name (auto-detected if None)
            base_dir: Base directory for queue root
            output_format: Output format ("text" or "json")
        """
        self.runner = TaskRunner.from_session(
            session_id=session_id,
            harness=harness,
            base_dir=base_dir,
        )
        self.output_format = output_format

    def run_init(self, args: argparse.Namespace) -> int:
        """Initialize queue structure.

        Args:
            args: Parsed arguments

        Returns:
            Exit code
        """
        result = self.runner.initialize()

        if self.output_format == "json":
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"✓ Queue initialized at: {result['queue_root']}")
                print(f"  Session: {result['session_id']}")
                print(f"  Harness: {result['harness']}")
                for name, path in result["directories"].items():
                    print(f"  - {name}: {path}")
                return 0
            else:
                print(f"✗ Initialization failed: {result['error']}", file=sys.stderr)
                return 1

    def run_run(self, args: argparse.Namespace) -> int:
        """Submit and run a task.

        Args:
            args: Parsed arguments (requires --role and --description)

        Returns:
            Exit code
        """
        try:
            # Build task data
            task_data = {
                "role": args.role,
                "description": args.description,
            }

            if args.metadata:
                task_data["metadata"] = json.loads(args.metadata)

            # Submit task
            task_id = self.runner.submit_task(task_data)

            result = {
                "task_id": task_id,
                "status": "submitted",
                "submitted_at": datetime.utcnow().isoformat(),
            }

            if self.output_format == "json":
                print(json.dumps(result, indent=2))
            else:
                print(f"✓ Task submitted: {task_id}")

            return 0

        except Exception as e:
            error_result = {
                "error": str(e),
            }

            if self.output_format == "json":
                print(json.dumps(error_result, indent=2), file=sys.stderr)
            else:
                print(f"✗ Error: {e}", file=sys.stderr)

            return 1

    def run_status(self, args: argparse.Namespace) -> int:
        """Get status of a task.

        Args:
            args: Parsed arguments (requires --task-id or positional task_id)

        Returns:
            Exit code
        """
        task_id = args.task_id or args.positional_task_id

        try:
            status = self.runner.get_task_status(task_id)

            if status is None:
                result = {
                    "error": f"Task {task_id} not found",
                }

                if self.output_format == "json":
                    print(json.dumps(result, indent=2), file=sys.stderr)
                else:
                    print(f"✗ Task not found: {task_id}", file=sys.stderr)

                return 1

            if self.output_format == "json":
                print(json.dumps(status, indent=2))
            else:
                self._print_task_status_text(status)

            return 0

        except Exception as e:
            if self.output_format == "json":
                print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
            else:
                print(f"✗ Error: {e}", file=sys.stderr)

            return 1

    def run_list(self, args: argparse.Namespace) -> int:
        """List tasks.

        Args:
            args: Parsed arguments (optional --state filter)

        Returns:
            Exit code
        """
        try:
            state = None
            if args.state:
                state = TaskState(args.state)

            task_ids = self.runner.list_tasks(state=state)

            if self.output_format == "json":
                result = {
                    "count": len(task_ids),
                    "state_filter": args.state or "all",
                    "tasks": task_ids,
                }
                print(json.dumps(result, indent=2))
            else:
                if args.state:
                    print(f"Tasks ({args.state}): {len(task_ids)}")
                else:
                    print(f"All tasks: {len(task_ids)}")

                if task_ids:
                    for task_id in task_ids:
                        print(f"  - {task_id}")
                else:
                    print("  (none)")

            return 0

        except Exception as e:
            if self.output_format == "json":
                print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
            else:
                print(f"✗ Error: {e}", file=sys.stderr)

            return 1

    def run_cancel(self, args: argparse.Namespace) -> int:
        """Cancel a task.

        Args:
            args: Parsed arguments (requires --task-id or positional task_id)

        Returns:
            Exit code
        """
        task_id = args.task_id or args.positional_task_id

        try:
            success = self.runner.cancel_task(task_id)

            result = {
                "task_id": task_id,
                "cancelled": success,
            }

            if self.output_format == "json":
                print(json.dumps(result, indent=2))
            else:
                if success:
                    print(f"✓ Task cancelled: {task_id}")
                    return 0
                else:
                    print(f"✗ Task not found or already complete: {task_id}", file=sys.stderr)
                    return 1

            return 0 if success else 1

        except Exception as e:
            if self.output_format == "json":
                print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
            else:
                print(f"✗ Error: {e}", file=sys.stderr)

            return 1

    def run_retry(self, args: argparse.Namespace) -> int:
        """Retry a failed task.

        Args:
            args: Parsed arguments (requires --task-id or positional task_id)

        Returns:
            Exit code
        """
        task_id = args.task_id or args.positional_task_id

        try:
            success = self.runner.retry_task(task_id)

            result = {
                "task_id": task_id,
                "retry_initiated": success,
            }

            if self.output_format == "json":
                print(json.dumps(result, indent=2))
            else:
                if success:
                    print(f"✓ Retry initiated for task: {task_id}")
                    return 0
                else:
                    print(f"✗ Task not found in failed/dead-letter queue: {task_id}", file=sys.stderr)
                    return 1

            return 0 if success else 1

        except Exception as e:
            if self.output_format == "json":
                print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
            else:
                print(f"✗ Error: {e}", file=sys.stderr)

            return 1

    def _print_task_status_text(self, status: dict[str, Any]) -> None:
        """Print task status in human-readable format.

        Args:
            status: Task status dictionary
        """
        print(f"Task: {status['task_id']}")
        print(f"State: {status['state']}")
        print(f"Created: {status['created_at']}")
        print(f"Updated: {status['updated_at']}")
        print(f"Retries: {status['retry_count']}/{status['max_retries']}")

        if status.get("error_message"):
            print(f"Error: {status['error_message']}")

        if status.get("result"):
            print(f"Result: {json.dumps(status['result'], indent=2)}")


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="OpenCode TaskRunner CLI - Queue-based task management",
        prog="opencode-runner",
    )

    # Global options
    parser.add_argument(
        "--session",
        help="Session ID (auto-detected if not provided)",
    )
    parser.add_argument(
        "--harness",
        help="Harness name (auto-detected if not provided)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base directory for queue root (default: ~/.agentic-engineers)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init
    subparsers.add_parser("init", help="Initialize queue structure")

    # run
    run_parser = subparsers.add_parser("run", help="Submit and run a task")
    run_parser.add_argument("--role", required=True, help="Task role")
    run_parser.add_argument("--description", required=True, help="Task description")
    run_parser.add_argument("--metadata", help="Additional metadata (JSON)")

    # status
    status_parser = subparsers.add_parser("status", help="Get task status")
    status_parser.add_argument("--task-id", help="Task ID")
    status_parser.add_argument("positional_task_id", nargs="?", help="Task ID (positional)")

    # list
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "--state",
        choices=["incoming", "processing", "done", "failed", "dead-letter"],
        help="Filter by state",
    )

    # cancel
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a task")
    cancel_parser.add_argument("--task-id", help="Task ID")
    cancel_parser.add_argument("positional_task_id", nargs="?", help="Task ID (positional)")

    # retry
    retry_parser = subparsers.add_parser("retry", help="Retry a failed task")
    retry_parser.add_argument("--task-id", help="Task ID")
    retry_parser.add_argument("positional_task_id", nargs="?", help="Task ID (positional)")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
        )

    # Create CLI runner
    cli = CLIRunner(
        session_id=args.session,
        harness=args.harness,
        base_dir=args.base_dir,
        output_format=args.format,
    )

    # Dispatch command
    if args.command == "init":
        return cli.run_init(args)
    elif args.command == "run":
        return cli.run_run(args)
    elif args.command == "status":
        return cli.run_status(args)
    elif args.command == "list":
        return cli.run_list(args)
    elif args.command == "cancel":
        return cli.run_cancel(args)
    elif args.command == "retry":
        return cli.run_retry(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
