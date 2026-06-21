#!/usr/bin/env python3
"""
Orchestrator Scheduler: Harness-native queue polling.

Invokes OrchestratorSkill.poll_queue() on a schedule.
Uses environment variables (read at runtime) for session/harness detection.

No external daemons, no cron jobs—purely a SKILL that can be re-invoked as needed.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s — %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class OrchestratorScheduler:
    """
    Scheduler that polls the queue for DELEGATEs and invokes Orchestrator.

    Session and harness are detected from environment variables at runtime,
    ensuring fresh detection on each invocation (no cached state).
    """

    def __init__(self):
        """Initialize scheduler with runtime environment detection."""
        self.session_id = self._detect_session_id()
        self.harness = self._detect_harness()
        self.orchestrator = None

        logger.info(f"OrchestratorScheduler initialized: session={self.session_id}, harness={self.harness}")

    def _detect_session_id(self) -> str:
        """
        Detect session ID from environment variables (runtime).

        Priority:
        1. CLAUDE_SESSION_ID (Claude harness)
        2. COPILOT_SESSION_ID (Copilot harness)
        3. AGENTIC_SESSION_ID (generic override)
        4. CLAUDE_CODE_SESSION_ID (Claude Code CLI)

        Raises:
            RuntimeError: If no session ID found
        """
        session_id = (
            os.environ.get('CLAUDE_SESSION_ID') or
            os.environ.get('COPILOT_SESSION_ID') or
            os.environ.get('AGENTIC_SESSION_ID') or
            os.environ.get('CLAUDE_CODE_SESSION_ID')
        )

        if not session_id:
            msg = (
                "No session ID found in environment. Set one of:\n"
                "  - CLAUDE_SESSION_ID (for Claude harness)\n"
                "  - COPILOT_SESSION_ID (for Copilot harness)\n"
                "  - AGENTIC_SESSION_ID (generic override)\n"
                "  - CLAUDE_CODE_SESSION_ID (Claude Code CLI)"
            )
            logger.error(msg)
            raise RuntimeError(msg)

        logger.debug(f"Detected session ID: {session_id}")
        return session_id

    def _detect_harness(self) -> str:
        """
        Detect harness from environment variables (runtime).

        Priority:
        1. AGENTIC_HARNESS (explicit override)
        2. Check which session ID env var is set
        3. Default to "claude"
        """
        # Explicit harness override
        if os.environ.get('AGENTIC_HARNESS'):
            harness = os.environ.get('AGENTIC_HARNESS')
            logger.debug(f"Detected harness from AGENTIC_HARNESS: {harness}")
            return harness

        # Infer from session ID env var
        if os.environ.get('COPILOT_SESSION_ID'):
            logger.debug("Detected harness from COPILOT_SESSION_ID: copilot")
            return 'copilot'

        if os.environ.get('CLAUDE_SESSION_ID') or os.environ.get('CLAUDE_CODE_SESSION_ID'):
            logger.debug("Detected harness: claude (default)")
            return 'claude'

        logger.debug("Using default harness: claude")
        return 'claude'

    def _load_orchestrator(self) -> None:
        """
        Lazy-load OrchestratorSkill to avoid circular imports.
        """
        if self.orchestrator is not None:
            return

        try:
            # Add src/ to path if not already there
            repo_root = Path(__file__).parent.parent.parent.parent
            if str(repo_root / 'src') not in sys.path:
                sys.path.insert(0, str(repo_root / 'src'))

            from skills.orchestrator.scripts.orchestrator_skill import OrchestratorSkill

            # Initialize with detected session/harness
            self.orchestrator = OrchestratorSkill(
                session_id=self.session_id,
                harness=self.harness
            )
            logger.info(f"OrchestratorSkill loaded: {self.orchestrator.queue_root}")

        except Exception as e:
            logger.error(f"Failed to load OrchestratorSkill: {e}", exc_info=True)
            raise

    def run(self) -> Tuple[int, int]:
        """
        Poll queue and process DELEGATEs.

        Returns:
            Tuple[int, int]: (processed_count, failed_count)
        """
        try:
            self._load_orchestrator()

            logger.info("Starting queue poll...")
            result = self.orchestrator.poll_queue()

            if isinstance(result, tuple):
                processed, failed = result
            else:
                processed = result
                failed = 0

            logger.info(f"Queue poll complete: processed={processed}, failed={failed}")
            return (processed, failed)

        except Exception as e:
            logger.error(f"Error during queue polling: {e}", exc_info=True)
            raise

    def run_with_retry(self, max_retries: int = 3) -> Tuple[int, int]:
        """
        Run queue polling with retry logic.

        Args:
            max_retries: Number of times to retry on failure

        Returns:
            Tuple[int, int]: (processed_count, failed_count)
        """
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_retries}")
                return self.run()

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {e}")

                if attempt < max_retries:
                    logger.info(f"Retrying in 5 seconds...")
                    import time
                    time.sleep(5)

        # All retries exhausted
        logger.error(f"All {max_retries} attempts failed. Last error: {last_error}")
        raise last_error


def main():
    """CLI entry point for orchestrator-scheduler."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Harness-native queue polling scheduler for agentic-engineers"
    )
    parser.add_argument(
        '--retry',
        type=int,
        default=1,
        help="Number of retry attempts on failure (default: 1)"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        scheduler = OrchestratorScheduler()

        if args.retry > 1:
            processed, failed = scheduler.run_with_retry(max_retries=args.retry)
        else:
            processed, failed = scheduler.run()

        # Exit with status code
        sys.exit(0 if failed == 0 else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
