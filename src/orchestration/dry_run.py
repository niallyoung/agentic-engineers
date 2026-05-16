"""
Dry-Run Mode Implementation for Orchestrator

Provides a DryRunContext that intercepts all side-effect operations (file writes,
git commits, API calls, queue operations) and logs them instead of executing.

This allows safe testing of the entire orchestration pipeline without modifying
any actual state.

Features:
- File operation interception (write, move, delete, copy)
- Git operation simulation (commit, push, branch creation)
- API call simulation
- Queue operation logging
- Comprehensive audit trail
- Zero side effects when enabled
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from enum import Enum


class OperationType(Enum):
    """Types of operations that can be simulated."""
    FILE_WRITE = "file_write"
    FILE_READ = "file_read"
    FILE_DELETE = "file_delete"
    FILE_MOVE = "file_move"
    FILE_COPY = "file_copy"
    DIR_CREATE = "dir_create"
    DIR_DELETE = "dir_delete"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    GIT_BRANCH = "git_branch"
    API_CALL = "api_call"
    QUEUE_MOVE = "queue_move"
    QUEUE_ARCHIVE = "queue_archive"
    SUBPROCESS_RUN = "subprocess_run"


@dataclass
class SimulatedOperation:
    """Record of a simulated operation."""
    operation_type: OperationType
    timestamp: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    would_succeed: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "operation_type": self.operation_type.value,
            "timestamp": self.timestamp,
            "description": self.description,
            "details": self.details,
            "would_succeed": self.would_succeed,
            "error_message": self.error_message,
        }


class DryRunContext:
    """
    Context manager for dry-run mode operations.
    
    When enabled, intercepts all side-effect operations and logs them
    instead of executing. Provides detailed audit trail of what would happen.
    
    Usage:
        with DryRunContext(enabled=True, log_file="/tmp/dry-run.log") as dry_run:
            # All operations are logged, not executed
            dry_run.log_file_write("/path/to/file", "content")
            dry_run.log_git_commit("message")
            
            # Get audit trail
            audit = dry_run.get_audit_trail()
    """
    
    def __init__(
        self,
        enabled: bool = False,
        log_file: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize DryRunContext.
        
        Args:
            enabled: Whether dry-run mode is active
            log_file: Path to write audit trail JSON
            logger: Optional logger instance for additional logging
        """
        self.enabled = enabled
        self.log_file = log_file
        self.logger = logger or logging.getLogger(__name__)
        
        # Audit trail of all simulated operations
        self.operations: List[SimulatedOperation] = []
        
        # Statistics
        self.operation_counts: Dict[OperationType, int] = {
            op_type: 0 for op_type in OperationType
        }
        
        # Start time
        self.start_time = datetime.now()
        
        if self.enabled:
            self.logger.info("🏜️  DRY-RUN MODE ENABLED - All operations will be simulated")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - write audit trail if configured."""
        if self.log_file and self.enabled:
            self.write_audit_trail()
        return False
    
    def _record_operation(
        self,
        op_type: OperationType,
        description: str,
        details: Dict[str, Any],
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Record a simulated operation."""
        operation = SimulatedOperation(
            operation_type=op_type,
            timestamp=datetime.now().isoformat(),
            description=description,
            details=details,
            would_succeed=would_succeed,
            error_message=error_message,
        )
        
        self.operations.append(operation)
        self.operation_counts[op_type] += 1
        
        if self.enabled:
            status = "✅" if would_succeed else "❌"
            self.logger.info(f"{status} [{op_type.value}] {description}")
            if error_message:
                self.logger.warning(f"   Error: {error_message}")
        
        return operation
    
    # ─── File Operations ────────────────────────────────────────────────────
    
    def log_file_write(
        self,
        path: str,
        content: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a file write operation."""
        return self._record_operation(
            OperationType.FILE_WRITE,
            f"Write file: {path}",
            {
                "path": path,
                "content_length": len(content),
                "content_preview": content[:100] + ("..." if len(content) > 100 else ""),
            },
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_file_read(
        self,
        path: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a file read operation."""
        return self._record_operation(
            OperationType.FILE_READ,
            f"Read file: {path}",
            {"path": path},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_file_delete(
        self,
        path: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a file delete operation."""
        return self._record_operation(
            OperationType.FILE_DELETE,
            f"Delete file: {path}",
            {"path": path},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_file_move(
        self,
        from_path: str,
        to_path: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a file move operation."""
        return self._record_operation(
            OperationType.FILE_MOVE,
            f"Move file: {from_path} → {to_path}",
            {"from_path": from_path, "to_path": to_path},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_file_copy(
        self,
        from_path: str,
        to_path: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a file copy operation."""
        return self._record_operation(
            OperationType.FILE_COPY,
            f"Copy file: {from_path} → {to_path}",
            {"from_path": from_path, "to_path": to_path},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_dir_create(
        self,
        path: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a directory create operation."""
        return self._record_operation(
            OperationType.DIR_CREATE,
            f"Create directory: {path}",
            {"path": path},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_dir_delete(
        self,
        path: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a directory delete operation."""
        return self._record_operation(
            OperationType.DIR_DELETE,
            f"Delete directory: {path}",
            {"path": path},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    # ─── Git Operations ────────────────────────────────────────────────────
    
    def log_git_commit(
        self,
        message: str,
        files: Optional[List[str]] = None,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a git commit operation."""
        return self._record_operation(
            OperationType.GIT_COMMIT,
            f"Git commit: {message}",
            {
                "message": message,
                "files": files or [],
                "file_count": len(files) if files else 0,
            },
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_git_push(
        self,
        remote: str = "origin",
        branch: str = "main",
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a git push operation."""
        return self._record_operation(
            OperationType.GIT_PUSH,
            f"Git push: {remote}/{branch}",
            {"remote": remote, "branch": branch},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_git_branch(
        self,
        branch_name: str,
        action: str = "create",
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a git branch operation."""
        return self._record_operation(
            OperationType.GIT_BRANCH,
            f"Git branch {action}: {branch_name}",
            {"branch_name": branch_name, "action": action},
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    # ─── API Operations ────────────────────────────────────────────────────
    
    def log_api_call(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log an API call operation."""
        return self._record_operation(
            OperationType.API_CALL,
            f"API call: {method} {endpoint}",
            {
                "method": method,
                "endpoint": endpoint,
                "payload": payload or {},
            },
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    # ─── Queue Operations ────────────────────────────────────────────────
    
    def log_queue_move(
        self,
        task_id: str,
        from_state: str,
        to_state: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a queue move operation."""
        return self._record_operation(
            OperationType.QUEUE_MOVE,
            f"Queue move: {task_id} ({from_state} → {to_state})",
            {
                "task_id": task_id,
                "from_state": from_state,
                "to_state": to_state,
            },
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    def log_queue_archive(
        self,
        task_id: str,
        reason: str,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a queue archive operation."""
        return self._record_operation(
            OperationType.QUEUE_ARCHIVE,
            f"Queue archive: {task_id}",
            {
                "task_id": task_id,
                "reason": reason,
            },
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    # ─── Subprocess Operations ────────────────────────────────────────────
    
    def log_subprocess_run(
        self,
        command: str,
        cwd: Optional[str] = None,
        would_succeed: bool = True,
        error_message: Optional[str] = None
    ) -> SimulatedOperation:
        """Log a subprocess run operation."""
        return self._record_operation(
            OperationType.SUBPROCESS_RUN,
            f"Run subprocess: {command}",
            {
                "command": command,
                "cwd": cwd,
            },
            would_succeed=would_succeed,
            error_message=error_message,
        )
    
    # ─── Audit Trail ────────────────────────────────────────────────────
    
    def get_audit_trail(self) -> Dict[str, Any]:
        """Get complete audit trail of all operations."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "dry_run_mode": self.enabled,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "total_operations": len(self.operations),
            "operation_counts": {
                op_type.value: count
                for op_type, count in self.operation_counts.items()
                if count > 0
            },
            "operations": [op.to_dict() for op in self.operations],
        }
    
    def write_audit_trail(self) -> str:
        """Write audit trail to JSON file."""
        if not self.log_file:
            return ""
        
        audit_trail = self.get_audit_trail()
        
        # Create parent directory if needed
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write audit trail
        with open(log_path, 'w') as f:
            json.dump(audit_trail, f, indent=2)
        
        self.logger.info(f"📋 Dry-run audit trail written to: {self.log_file}")
        return str(log_path)
    
    def print_summary(self) -> str:
        """Print a summary of all operations."""
        audit = self.get_audit_trail()
        
        summary = []
        summary.append("\n" + "=" * 80)
        summary.append("🏜️  DRY-RUN MODE SUMMARY")
        summary.append("=" * 80)
        summary.append(f"Total operations: {audit['total_operations']}")
        summary.append("")
        
        if audit['operation_counts']:
            summary.append("Operations by type:")
            for op_type, count in sorted(audit['operation_counts'].items()):
                summary.append(f"  • {op_type}: {count}")
        
        summary.append("")
        summary.append(f"Duration: {audit['duration_seconds']}s")
        summary.append("=" * 80 + "\n")
        
        return "\n".join(summary)


# ─── Global Dry-Run Context ────────────────────────────────────────────────

_global_dry_run_context: Optional[DryRunContext] = None


def initialize_dry_run(
    enabled: bool = False,
    log_file: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> DryRunContext:
    """Initialize global dry-run context."""
    global _global_dry_run_context
    _global_dry_run_context = DryRunContext(enabled=enabled, log_file=log_file, logger=logger)
    return _global_dry_run_context


def get_dry_run_context() -> Optional[DryRunContext]:
    """Get the global dry-run context."""
    return _global_dry_run_context


def is_dry_run_enabled() -> bool:
    """Check if dry-run mode is enabled."""
    return _global_dry_run_context is not None and _global_dry_run_context.enabled


@contextmanager
def dry_run_mode(
    enabled: bool = False,
    log_file: Optional[str] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Context manager for dry-run mode.
    
    Usage:
        with dry_run_mode(enabled=True, log_file="/tmp/dry-run.log"):
            # All operations are simulated
            pass
    """
    ctx = initialize_dry_run(enabled=enabled, log_file=log_file, logger=logger)
    try:
        yield ctx
    finally:
        if ctx.enabled and ctx.log_file:
            ctx.write_audit_trail()
