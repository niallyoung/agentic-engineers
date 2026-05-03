"""
Continuous Polling Loop Automation - Phase 1

AutomationController: Main continuous polling loop for autonomous Orchestrator operation.

Implements:
1. While-True polling loop with configurable interval
2. Signal handling (SIGTERM → graceful, SIGINT → clean)
3. Environment variable configuration (POLL_INTERVAL, LOG_LEVEL, etc.)
4. Comprehensive logging and metrics emission
5. Graceful shutdown without data loss
6. Integration with OrchestratorAgent.run_poll_cycle() and AgentInvoker

Architecture:
    AutomationController wraps OrchestratorAgent to run continuous polling.
    - Polls queue every N seconds (default 5s, configurable)
    - Emits metrics after each cycle (tasks processed, duration, success rate)
    - Listens for SIGTERM (graceful shutdown after current cycle)
    - Listens for SIGINT (clean exit immediately)
    - Logs all state transitions and errors
    - Preserves queue state across restarts

Design reference: docs/implementation-roadmap-continuous-polling-5102.md
"""

import os
import sys
import signal
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from .orchestrator import OrchestratorAgent, QueueManager


# ─── Configuration & Constants ───────────────────────────────────────────────


class ShutdownSignal(Enum):
    """Enumeration of shutdown signals."""
    NONE = "none"
    SIGTERM = "sigterm"  # Graceful: finish current cycle
    SIGINT = "sigint"    # Clean: exit immediately


@dataclass
class AutomationMetrics:
    """Metrics collected during automation run."""
    
    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    
    # Cycles
    cycles_completed: int = 0
    cycle_duration_avg_seconds: float = 0.0
    cycle_duration_min_seconds: float = float('inf')
    cycle_duration_max_seconds: float = 0.0
    
    # Tasks
    tasks_processed: int = 0
    tasks_success: int = 0
    tasks_escalated: int = 0
    tasks_failed: int = 0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    error_count: int = 0
    
    # Shutdown
    shutdown_reason: str = "none"  # none, idle, sigterm, sigint, error
    shutdown_signal: Optional[ShutdownSignal] = None
    
    def record_cycle(self, duration_seconds: float, cycle_result: Dict):
        """Record metrics from a single polling cycle."""
        self.cycles_completed += 1
        self.cycle_duration_avg_seconds = (
            self.cycle_duration_avg_seconds * (self.cycles_completed - 1) +
            duration_seconds
        ) / self.cycles_completed
        self.cycle_duration_min_seconds = min(
            self.cycle_duration_min_seconds, duration_seconds
        )
        self.cycle_duration_max_seconds = max(
            self.cycle_duration_max_seconds, duration_seconds
        )
        
        self.tasks_processed += cycle_result.get("tasks_processed", 0)
        self.tasks_success += cycle_result.get("tasks_success", 0)
        self.tasks_escalated += cycle_result.get("tasks_escalated", 0)
        self.tasks_failed += cycle_result.get("tasks_failed", 0)
    
    def record_error(self, error_msg: str):
        """Record an error."""
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "message": error_msg
        })
        self.error_count += 1
    
    def finalize(self):
        """Finalize metrics at end of run."""
        self.end_time = datetime.now()
        self.total_duration_seconds = (
            self.end_time - self.start_time
        ).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": self.total_duration_seconds,
            "cycles_completed": self.cycles_completed,
            "cycle_duration_avg_seconds": round(self.cycle_duration_avg_seconds, 3),
            "cycle_duration_min_seconds": round(self.cycle_duration_min_seconds, 3) if self.cycle_duration_min_seconds != float('inf') else 0,
            "cycle_duration_max_seconds": round(self.cycle_duration_max_seconds, 3),
            "tasks_processed": self.tasks_processed,
            "tasks_success": self.tasks_success,
            "tasks_escalated": self.tasks_escalated,
            "tasks_failed": self.tasks_failed,
            "error_count": self.error_count,
            "errors": self.errors,
            "shutdown_reason": self.shutdown_reason,
            "shutdown_signal": self.shutdown_signal.value if self.shutdown_signal else None,
        }


# ─── AutomationController ────────────────────────────────────────────────────


class AutomationController:
    """
    Continuous polling loop automation controller.
    
    Orchestrates continuous polling of the task queue, integrating with
    OrchestratorAgent to delegate tasks to appropriate agents.
    
    Features:
    - While-True polling loop with configurable interval
    - Signal handling (SIGTERM → graceful, SIGINT → clean)
    - Environment variable configuration
    - Comprehensive logging and metrics
    - Graceful shutdown without data loss
    
    Usage:
        controller = AutomationController()
        result = controller.run()
        print(f"Processed {result['metrics']['tasks_processed']} tasks")
    
    Environment Variables:
        POLL_INTERVAL_SECONDS: Seconds between polls (default: 5)
        LOG_LEVEL: Logging level (default: INFO)
        AUTOMATION_METRICS_FILE: Path to write metrics JSON (optional)
        ORCHESTRATOR_QUEUE_DIR: Override default queue directory (optional)
        AUTOMATION_IDLE_TIMEOUT: Idle timeout before exit in non-daemon mode (default: 300)
        AUTOMATION_MAX_CYCLES: Maximum cycles before exit (for testing, default: None/unlimited)
        AUTOMATION_DAEMON_MODE: Run as daemon (true/false, default: true)
    """
    
    def __init__(self, 
                 queue_dir: Optional[str] = None,
                 poll_interval: Optional[float] = None,
                 log_level: Optional[str] = None,
                 daemon_mode: Optional[bool] = None,
                 idle_timeout: Optional[int] = None,
                 max_cycles: Optional[int] = None,
                 metrics_file: Optional[str] = None):
        """
        Initialize AutomationController.
        
        Args:
            queue_dir: Override default queue directory
            poll_interval: Seconds between polls (default from env or 5)
            log_level: Logging level (default from env or INFO)
            daemon_mode: Run as daemon (default from env or True)
            idle_timeout: Idle timeout in seconds (default from env or 300)
            max_cycles: Maximum cycles before exit (for testing)
            metrics_file: Path to write final metrics JSON
        """
        # Configuration from environment variables with defaults
        self.poll_interval = (
            poll_interval or 
            float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
        )
        self.log_level = (
            log_level or 
            os.getenv("LOG_LEVEL", "INFO")
        ).upper()
        self.daemon_mode = (
            daemon_mode if daemon_mode is not None else
            os.getenv("AUTOMATION_DAEMON_MODE", "true").lower() == "true"
        )
        self.idle_timeout = (
            idle_timeout or 
            int(os.getenv("AUTOMATION_IDLE_TIMEOUT", "300"))
        )
        self.max_cycles = (
            max_cycles or 
            int(os.getenv("AUTOMATION_MAX_CYCLES", "0")) or None
        )
        self.metrics_file = (
            metrics_file or 
            os.getenv("AUTOMATION_METRICS_FILE")
        )
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            queue_dir=queue_dir or os.getenv("ORCHESTRATOR_QUEUE_DIR")
        )
        
        # Initialize state
        self.shutdown_requested = False
        self.shutdown_signal = ShutdownSignal.NONE
        self.metrics = AutomationMetrics()
        self.last_heartbeat_time = time.time()
        self.heartbeat_interval = 60  # seconds
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info(
            f"AutomationController initialized: "
            f"poll_interval={self.poll_interval}s, "
            f"daemon_mode={self.daemon_mode}, "
            f"idle_timeout={self.idle_timeout}s, "
            f"max_cycles={self.max_cycles}"
        )
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging."""
        logger = logging.getLogger("AutomationController")
        
        # Remove existing handlers
        logger.handlers = []
        
        # Set level
        log_level = getattr(logging, self.log_level, logging.INFO)
        logger.setLevel(log_level)
        
        # Create console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _validate_config(self):
        """Validate configuration values."""
        if self.poll_interval <= 0:
            raise ValueError(f"poll_interval must be positive, got {self.poll_interval}")
        if self.idle_timeout < 0:
            raise ValueError(f"idle_timeout must be non-negative, got {self.idle_timeout}")
        if self.max_cycles is not None and self.max_cycles <= 0:
            raise ValueError(f"max_cycles must be positive or None, got {self.max_cycles}")
        
        self.logger.debug("Configuration validated successfully")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def handle_sigterm(signum, frame):
            self.logger.warning("SIGTERM received - graceful shutdown after current cycle")
            self.shutdown_requested = True
            self.shutdown_signal = ShutdownSignal.SIGTERM
        
        def handle_sigint(signum, frame):
            self.logger.warning("SIGINT received - clean shutdown")
            self.shutdown_requested = True
            self.shutdown_signal = ShutdownSignal.SIGINT
        
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigint)
        
        self.logger.debug("Signal handlers installed (SIGTERM, SIGINT)")
    
    def _emit_heartbeat(self):
        """Emit heartbeat metrics at regular intervals."""
        current_time = time.time()
        if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
            heartbeat = {
                "timestamp": datetime.now().isoformat(),
                "cycles_completed": self.metrics.cycles_completed,
                "tasks_processed": self.metrics.tasks_processed,
                "tasks_success": self.metrics.tasks_success,
                "tasks_escalated": self.metrics.tasks_escalated,
                "errors": self.metrics.error_count,
            }
            self.logger.info(f"Heartbeat: {json.dumps(heartbeat)}")
            self.last_heartbeat_time = current_time
    
    def _should_exit(self) -> Optional[str]:
        """
        Check if automation should exit.
        
        Returns:
            None if continue, otherwise reason for exit
        """
        # Signal requested shutdown
        if self.shutdown_requested:
            return self.shutdown_signal.value
        
        # Reached max cycles (test mode)
        if self.max_cycles and self.metrics.cycles_completed >= self.max_cycles:
            return "max_cycles"
        
        # Idle timeout (non-daemon mode)
        if not self.daemon_mode:
            elapsed = time.time() - self.orchestrator.last_task_time
            if elapsed >= self.idle_timeout:
                return "idle_timeout"
        
        return None
    
    def run(self) -> Dict[str, Any]:
        """
        Run the continuous polling automation loop.
        
        Main entry point. Sets up signal handlers, enters polling loop,
        and returns metrics.
        
        Returns:
            Dict with:
                - status: "COMPLETE" | "INTERRUPTED" | "ERROR"
                - exit_reason: reason for exit
                - metrics: final metrics dict
                - error: error message if status is ERROR
        """
        self.logger.info("=" * 80)
        self.logger.info(f"🚀 AutomationController starting")
        self.logger.info(f"Mode: {'daemon' if self.daemon_mode else 'idle-timeout'}")
        self.logger.info(f"Poll interval: {self.poll_interval}s")
        self.logger.info("=" * 80)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        try:
            # Main polling loop
            while True:
                # Check exit conditions
                exit_reason = self._should_exit()
                if exit_reason:
                    self.logger.info(f"Exit condition met: {exit_reason}")
                    return self._build_result("COMPLETE", exit_reason)
                
                # Execute one polling cycle
                cycle_start = time.time()
                try:
                    cycle_result = self.orchestrator.run_poll_cycle()
                    cycle_duration = time.time() - cycle_start
                    
                    # Record metrics
                    self.metrics.record_cycle(cycle_duration, cycle_result)
                    
                    tasks_count = cycle_result.get("tasks_processed", 0)
                    self.logger.info(
                        f"[Cycle {self.metrics.cycles_completed}] "
                        f"Processed {tasks_count} tasks in {cycle_duration:.2f}s"
                    )
                    
                except Exception as e:
                    cycle_duration = time.time() - cycle_start
                    error_msg = f"Error in polling cycle: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.metrics.record_error(error_msg)
                    
                    # Decide whether to continue or exit
                    if self.shutdown_requested:
                        return self._build_result(
                            "INTERRUPTED", 
                            "error_during_shutdown"
                        )
                    # Otherwise continue polling
                
                # Emit periodic heartbeat
                self._emit_heartbeat()
                
                # Sleep before next cycle
                if not self.shutdown_requested:
                    self.logger.debug(f"Sleeping {self.poll_interval}s before next cycle...")
                    time.sleep(self.poll_interval)
        
        except KeyboardInterrupt:
            self.logger.warning("KeyboardInterrupt received")
            return self._build_result("INTERRUPTED", "keyboard_interrupt")
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.metrics.record_error(error_msg)
            return self._build_result("ERROR", "unexpected_error")
        
        finally:
            self._cleanup()
    
    def _build_result(self, status: str, exit_reason: str) -> Dict[str, Any]:
        """Build final result dictionary."""
        self.metrics.finalize()
        self.metrics.shutdown_reason = exit_reason
        self.metrics.shutdown_signal = self.shutdown_signal
        
        result = {
            "status": status,
            "exit_reason": exit_reason,
            "metrics": self.metrics.to_dict(),
        }
        
        # Write metrics to file if configured
        if self.metrics_file:
            try:
                metrics_path = Path(self.metrics_file)
                metrics_path.parent.mkdir(parents=True, exist_ok=True)
                with open(metrics_path, 'w') as f:
                    json.dump(result, f, indent=2)
                self.logger.info(f"Metrics written to {self.metrics_file}")
            except Exception as e:
                self.logger.error(f"Failed to write metrics file: {e}")
        
        return result
    
    def _cleanup(self):
        """Cleanup resources before exit."""
        self.logger.info("Cleaning up resources...")
        
        # Summary statistics
        self.metrics.finalize()
        summary = {
            "cycles": self.metrics.cycles_completed,
            "tasks": self.metrics.tasks_processed,
            "success": self.metrics.tasks_success,
            "escalated": self.metrics.tasks_escalated,
            "errors": self.metrics.error_count,
            "duration_seconds": round(self.metrics.total_duration_seconds, 2),
        }
        
        self.logger.info("=" * 80)
        self.logger.info(f"✅ AutomationController shutdown complete")
        self.logger.info(f"Summary: {json.dumps(summary)}")
        self.logger.info("=" * 80)


# ─── Entry Point ────────────────────────────────────────────────────────────


def main():
    """Command-line entry point for AutomationController."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Continuous Polling Loop Automation - Phase 1"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (loop indefinitely)"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Seconds between polls (default: 5)"
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=None,
        help="Idle timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Maximum cycles before exit (for testing)"
    )
    parser.add_argument(
        "--metrics-file",
        type=str,
        default=None,
        help="Path to write final metrics JSON"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Create and run controller
    controller = AutomationController(
        poll_interval=args.poll_interval,
        log_level=args.log_level,
        daemon_mode=args.daemon,
        idle_timeout=args.idle_timeout,
        max_cycles=args.max_cycles,
        metrics_file=args.metrics_file,
    )
    
    result = controller.run()
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] == "COMPLETE" else 1)


if __name__ == "__main__":
    main()
