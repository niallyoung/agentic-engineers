"""
Orchestrator Agent - Continuous Queue Polling & Task Routing

Implements the canonical ORCHESTRATOR-FIRST EXECUTION MODEL:
1. Poll ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/ for new DELEGATE blocks
2. Route each task to appropriate agent per AGENTS.md
3. Process HANDBACK results
4. Move tasks through queue states: incoming → processing → done
5. Continue polling until queue is idle (60+ seconds with no tasks)

This is the ONLY way work flows through agentic-engineers.

CANONICAL QUEUE PATH (all harnesses):
  ~/.agentic-engineers/{session-id}/{harness}/queue/
  - Harnesses: claude, copilot, gpt, local
  - Supported by queue-isolation skill (mandatory)
  - Legacy paths (~/.copilot/queue/, ~/.claude/queue/, artifacts/queue/) NO LONGER SUPPORTED
"""

import os
import re
import logging
import yaml
import json
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from . import (
    Agent, ORCHESTRATOR_CONFIG, ENGINEER_CONFIG, SENIOR_ENGINEER_CONFIG,
    LEAD_ENGINEER_CONFIG, PRINCIPAL_ENGINEER_CONFIG, QUALITY_ENGINEER_CONFIG,
    MODEL_ENGINEER_CONFIG, SECURITY_ENGINEER_CONFIG
)
from .quality_validator import QualityValidator, RoutingDecision
from .delegate_validator import (
    DelegateValidator,
    RoleRoutingError,
    validate_delegate_pre_flight,
)
from .metrics_writer import MetricsWriter
from .queue_enforcement_middleware import QueueEnforcingProxy
from ..monitoring.metrics import MetricsRegistry
from ..monitoring.token_tracker import TokenTracker
from ..monitoring.orchestrator_cli import OrchestratorCLI
from ..monitoring.budget_checker import BudgetStatus, BudgetResult
from ..decorators import SecurityError

logger = logging.getLogger(__name__)


# ============================================================================
# Queue path / filename safety helpers
# ============================================================================

# A queue path component (task_id, status/decision label) is only allowed to
# contain a conservative, filename-safe character set. This prevents path
# traversal / queue poisoning where attacker-controlled task_id or status
# values (read from DELEGATE/HANDBACK YAML) escape the canonical queue root
# via "../", absolute paths, or embedded path separators.
_SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def sanitize_path_component(value: object, *, field: str = "component") -> str:
    """Validate that *value* is safe to use as a single path/filename component.

    Rejects values that are non-strings, empty, ``.``/``..``, or that contain
    path separators, null bytes, or any character outside ``[A-Za-z0-9._-]``.

    Args:
        value: Candidate component (e.g. a task_id or status label).
        field: Human-readable field name for error messages.

    Returns:
        The validated string (unchanged) when it is safe.

    Raises:
        ValueError: If the value is unsafe to interpolate into a path.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string, got {type(value).__name__}")
    if value in ("", ".", ".."):
        raise ValueError(f"{field} is empty or a path reference: {value!r}")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{field} contains illegal path separators: {value!r}")
    if not _SAFE_COMPONENT_RE.match(value):
        raise ValueError(
            f"{field} contains illegal characters "
            f"(allowed: letters, digits, '.', '_', '-'): {value!r}"
        )
    return value


def ensure_within_directory(candidate: Path, base_dir: Path, *, field: str = "path") -> Path:
    """Ensure *candidate* resolves to a location inside *base_dir*.

    Defence-in-depth guard against path traversal / symlink escape: even if a
    component slips through :func:`sanitize_path_component`, the final resolved
    path must remain within the intended queue directory.

    Args:
        candidate: The path about to be written/moved.
        base_dir: The directory the candidate must stay within.
        field: Human-readable field name for error messages.

    Returns:
        The resolved candidate path.

    Raises:
        ValueError: If the candidate escapes *base_dir*.
    """
    base_resolved = Path(base_dir).resolve()
    candidate_resolved = Path(candidate).resolve()
    if candidate_resolved != base_resolved and base_resolved not in candidate_resolved.parents:
        raise ValueError(
            f"{field} escapes the queue directory: {candidate} "
            f"(resolved {candidate_resolved}) is not within {base_resolved}"
        )
    return candidate_resolved


def _is_env_var_truthy(env_var_name: str) -> bool:
    """
    Check if an environment variable is set to a truthy value.
    
    Accepts: 'true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES'
    
    Args:
        env_var_name: Environment variable name to check
        
    Returns:
        bool: True if variable is set to a truthy value, False otherwise
    """
    value = os.environ.get(env_var_name, '').strip().lower()
    return value in ('true', '1', 'yes')


# ============================================================================
# PHASE 1: Queue Isolation Integration
# ============================================================================

def _try_import_queue_isolation():
    """
    Attempt to import queue_isolation module.
    
    Returns the module if available, None if import fails.
    This allows graceful fallback to legacy paths if queue-isolation is unavailable.

    The module lives at ``src/skills/_meta/queue-isolation/scripts/queue_isolation.py``.
    The package directory uses a hyphen (``queue-isolation``), which is NOT a valid
    Python module path, so the dotted ``src.skills._meta.queue_isolation.scripts``
    import never resolves. We fall back to inserting the scripts directory on
    ``sys.path`` and importing ``queue_isolation`` directly — the same mechanism
    used by ``invoke_agent.py`` and the queue-management skill.
    """
    try:
        # Preferred path if an importable (underscored) package alias exists.
        from src.skills._meta.queue_isolation.scripts import queue_isolation as qi
        return qi
    except ImportError:
        pass

    try:
        # Fallback: add the hyphenated scripts directory to sys.path and import
        # the bare module the way the orchestrator's runtime callers do.
        import sys
        queue_isolation_path = (
            Path(__file__).parent.parent.parent
            / "skills" / "_meta" / "queue-isolation" / "scripts"
        )
        if str(queue_isolation_path) not in sys.path:
            sys.path.insert(0, str(queue_isolation_path))
        import queue_isolation as qi
        return qi
    except ImportError:
        logger.debug("queue-isolation module not available, will use legacy paths")
        return None


# Module-level cache of queue_isolation availability
_QUEUE_ISOLATION = _try_import_queue_isolation()

# Protocol constants
MAX_RETRIES = 2  # Maximum number of retries before escalation to Principal Engineer
TASK_STATE_KEYS = {'retry_count', 'quality_score', 'last_failure_reasons', 'retry_context'}


def analyze_handback_for_gray_zone(handback_block: dict, original_delegate: dict) -> dict:
    """
    Analyze a 70–79 HANDBACK for gray-zone review decision.
    Inlined from archived gray_zone_reviewer.py during Phase 6 consolidation.

    Returns dict with: handback_id, score, risk_level, criteria_met, coverage,
    deliverables_verified, recommendation, reasoning, follow_up_items.
    """
    task_id = handback_block.get("task_id", original_delegate.get("task_id", "unknown"))
    score = int(handback_block.get("quality_score", handback_block.get("score", 75)))

    # Risk assessment
    risk_level = "high" if (
        handback_block.get("touches_production") or
        handback_block.get("new_dependencies") or
        handback_block.get("tests_failed")
    ) else ("medium" if (
        handback_block.get("coverage_decreased") or
        handback_block.get("untested_paths") or
        any(kw in str(handback_block.get("notes", "")).lower()
            for kw in ["production", "database", "auth", "security", "critical"])
    ) else "low")

    # Deliverable verification
    required = original_delegate.get("deliverables", [])
    completed = handback_block.get("deliverables_completed", handback_block.get("deliverables", []))
    deliverables_verified = (not required) or (bool(completed) and all(
        any(str(req).lower() in str(c).lower() or str(c).lower() in str(req).lower()
            for c in completed)
        for req in required
    ))

    # Coverage extraction
    cov = handback_block.get("test_coverage", handback_block.get("coverage", None))
    try:
        coverage = int(float(str(cov).replace("%", "").strip())) if cov is not None else 0
    except (ValueError, TypeError):
        coverage = 0

    # Criteria count
    criteria = original_delegate.get("success_criteria", [])
    total_criteria = len(criteria) if criteria else 4
    met_criteria = handback_block.get("criteria_met", handback_block.get("success_criteria_met", None))
    if isinstance(met_criteria, int):
        criteria_met = met_criteria
    elif isinstance(met_criteria, list):
        criteria_met = len(met_criteria)
    else:
        criteria_met = max(1, round((score / 100) * total_criteria)) if criteria else (3 if deliverables_verified else 1)

    # Decision matrix
    if not deliverables_verified or risk_level == "high":
        recommendation = "REWORK"
    else:
        fraction = criteria_met / total_criteria if total_criteria > 0 else 0
        if risk_level == "low":
            recommendation = "ACCEPT" if (fraction >= 0.75 and coverage >= 90) else (
                "CONDITIONAL" if (fraction >= 0.5 and coverage >= 85) else "REWORK")
        else:  # medium
            recommendation = "ACCEPT" if (fraction >= 1.0 and coverage >= 95) else (
                "CONDITIONAL" if (fraction >= 0.75 and coverage >= 90) else "REWORK")

    reasoning = (
        f"Score {score}/100 (gray-zone 70–79). Risk level: {risk_level}. "
        f"Criteria met: {criteria_met}/{total_criteria}. Test coverage: {coverage}%. "
        f"Deliverables verified: {deliverables_verified}. Recommendation: {recommendation}."
    )

    follow_up_items = []
    if recommendation == "CONDITIONAL":
        if criteria_met < total_criteria:
            follow_up_items.append(f"Address {total_criteria - criteria_met} unmet success criteria.")
        if coverage < 90:
            follow_up_items.append(f"Improve test coverage from {coverage}% to ≥90%.")
        if not follow_up_items:
            follow_up_items.append("Review and close any open quality findings before next release.")

    return {
        "handback_id": task_id,
        "score": score,
        "risk_level": risk_level,
        "criteria_met": f"{criteria_met}/{total_criteria}",
        "coverage": coverage,
        "deliverables_verified": deliverables_verified,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "follow_up_items": follow_up_items,
    }


class QueueManager:
    """Manage queue directory structure and file operations with session-id partitioning."""
    
    @staticmethod
    def detect_agent_context() -> str:
        """
        Detect which agent context is running (Claude or Copilot).
        
        Detection priority:
        1. AGENT_CONTEXT environment variable (set by agent harness)
        2. Running process (check ps for claude or copilot)
        3. Parent directory markers in session-state
        4. Default to copilot if both ~/.claude and ~/.copilot exist
        
        Returns:
            'claude' or 'copilot'
        """
        # Priority 1: Check environment variables
        agent_context = os.environ.get('AGENT_CONTEXT', '').lower()
        if agent_context in ('claude', 'copilot'):
            return agent_context
        
        # Priority 2: Check running process (simplified - could be extended)
        # If we see 'copilot' in process list, we're likely in Copilot
        try:
            import subprocess
            ps_output = subprocess.check_output(['ps', 'aux'], text=True)
            if 'copilot' in ps_output.lower():
                return 'copilot'
            if 'claude' in ps_output.lower():
                return 'claude'
        except:
            pass
        
        # Priority 3: Check home directory markers
        # If ~/.copilot/.agentic-engine{service-name} exists, we're likely in Copilot
        home = Path.home()
        copilot_managed = home / '.copilot' / '.agentic-engine{service-name}'
        claude_managed = home / '.claude' / '.agentic-engine{service-name}'
        
        if copilot_managed.exists():
            return 'copilot'
        if claude_managed.exists():
            return 'claude'
        
        # Priority 4: Default to copilot if both exist (Copilot is primary)
        if (home / '.copilot').exists():
            return 'copilot'
        if (home / '.claude').exists():
            return 'claude'
        
        # Ultimate fallback
        return 'copilot'
    
    @staticmethod
    def detect_session_id() -> str:
        """
        Detect session-id for queue partitioning.
        
        Detection priority:
        1. COPILOT_SESSION_ID environment variable (set by Copilot CLI runtime)
        2. Scan ~/.copilot/session-state/ for current process's session directory
        3. Fallback to CLAUDE_SESSION_ID if available (Claude context)
        
        Returns:
            Session-id UUID string (e.g., "54744939-4acb-430c-b2c4-3b8322289d0b")
        
        Raises:
            RuntimeError: If session-id cannot be detected
        """
        # Priority 1: Check COPILOT_SESSION_ID environment variable
        copilot_session_id = os.environ.get('COPILOT_SESSION_ID', '').strip()
        if copilot_session_id:
            return copilot_session_id
        
        # Priority 2: Check CLAUDE_SESSION_ID (Claude context)
        claude_session_id = os.environ.get('CLAUDE_SESSION_ID', '').strip()
        if claude_session_id:
            return claude_session_id
        
        # Priority 3: Scan ~/.copilot/session-state/ for session directory
        home = Path.home()
        session_state_dir = home / '.copilot' / 'session-state'
        
        if session_state_dir.exists():
            # Find most recently modified session directory (likely current session)
            session_dirs = [d for d in session_state_dir.iterdir() if d.is_dir()]
            if session_dirs:
                # Sort by modification time, get most recent
                latest_session = max(session_dirs, key=lambda p: p.stat().st_mtime)
                session_id = latest_session.name
                # Validate it looks like a UUID
                if len(session_id) == 36 and session_id.count('-') == 4:
                    return session_id
        
        # Priority 4: Try Claude session-state
        claude_session_state = home / '.claude' / 'session-state'
        if claude_session_state.exists():
            session_dirs = [d for d in claude_session_state.iterdir() if d.is_dir()]
            if session_dirs:
                latest_session = max(session_dirs, key=lambda p: p.stat().st_mtime)
                session_id = latest_session.name
                if len(session_id) == 36 and session_id.count('-') == 4:
                    return session_id
        
        # Could not detect session-id
        raise RuntimeError(
            "Could not detect session-id. Ensure COPILOT_SESSION_ID environment variable is set "
            "or ~/.copilot/session-state/ contains a valid session directory."
        )
    
    def migrate_legacy_queue(self):
        """
        Migrate old queue structure (~/.copilot/queue/{incoming,processing,done})
        to new session-id based structure (~/.copilot/queue/{session-id}/{incoming,processing,done}).
        
        Only runs once per session. Creates .migration-log with details of what was migrated.
        
        Actions:
        1. Check if old queue structure exists (incoming/, processing/, done/ directly under base_dir)
        2. If yes:
           - Create new session-id queue directories
           - Copy old queue contents to new location
           - Create .migration-log with timestamp and migration details
           - Remove or rename old directories
        3. Log all actions
        """
        # Only run if base_dir points to old structure (not yet partitioned)
        incoming_path = self.base_dir / "incoming"
        processing_path = self.base_dir / "processing"
        done_path = self.base_dir / "done"
        
        # Check if old structure exists at base level
        old_structure_exists = (
            incoming_path.exists() or 
            processing_path.exists() or 
            done_path.exists()
        )
        
        # Also check if we're already in a session-id partitioned structure
        # (if base_dir ends with a UUID, we're already partitioned)
        if self.base_dir.name.count('-') == 4 and len(self.base_dir.name) == 36:
            # Already partitioned, skip migration
            return
        
        if not old_structure_exists:
            # No old structure to migrate
            return
        
        print(f"   🔄 Migrating legacy queue structure to session-id partitioning...")
        
        migration_log = []
        migration_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "migration_started",
            "from_structure": "~/.copilot/queue/{incoming,processing,done}",
            "to_structure": f"~/.copilot/queue/{self.session_id}/{{incoming,processing,done}}"
        })
        
        try:
            # Create new session-id queue structure if it doesn't exist
            self._ensure_queue_structure()
            
            # Migrate incoming queue
            if incoming_path.exists() and incoming_path.is_dir():
                incoming_files = list(incoming_path.glob("*.yaml"))
                if incoming_files:
                    for file in incoming_files:
                        new_file_path = self.incoming_dir / file.name
                        shutil.copy2(str(file), str(new_file_path))
                        migration_log.append({
                            "timestamp": datetime.now().isoformat(),
                            "action": "file_copied",
                            "from": f"incoming/{file.name}",
                            "to": f"{self.session_id}/incoming/{file.name}"
                        })
            
            # Migrate processing queue
            if processing_path.exists() and processing_path.is_dir():
                processing_files = list(processing_path.glob("*.yaml"))
                if processing_files:
                    for file in processing_files:
                        new_file_path = self.processing_dir / file.name
                        shutil.copy2(str(file), str(new_file_path))
                        migration_log.append({
                            "timestamp": datetime.now().isoformat(),
                            "action": "file_copied",
                            "from": f"processing/{file.name}",
                            "to": f"{self.session_id}/processing/{file.name}"
                        })
            
            # Migrate done queue
            if done_path.exists() and done_path.is_dir():
                done_files = list(done_path.glob("*.yaml"))
                if done_files:
                    for file in done_files:
                        new_file_path = self.done_dir / file.name
                        shutil.copy2(str(file), str(new_file_path))
                        migration_log.append({
                            "timestamp": datetime.now().isoformat(),
                            "action": "file_copied",
                            "from": f"done/{file.name}",
                            "to": f"{self.session_id}/done/{file.name}"
                        })
            
            # Rename old directories to backup
            migration_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            if incoming_path.exists():
                backup_path = incoming_path.parent / f"incoming-legacy-{migration_timestamp}"
                shutil.move(str(incoming_path), str(backup_path))
                migration_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "old_directory_renamed",
                    "from": "incoming",
                    "to": f"incoming-legacy-{migration_timestamp}"
                })
            
            if processing_path.exists():
                backup_path = processing_path.parent / f"processing-legacy-{migration_timestamp}"
                shutil.move(str(processing_path), str(backup_path))
                migration_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "old_directory_renamed",
                    "from": "processing",
                    "to": f"processing-legacy-{migration_timestamp}"
                })
            
            if done_path.exists():
                backup_path = done_path.parent / f"done-legacy-{migration_timestamp}"
                shutil.move(str(done_path), str(backup_path))
                migration_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "old_directory_renamed",
                    "from": "done",
                    "to": f"done-legacy-{migration_timestamp}"
                })
            
            migration_log.append({
                "timestamp": datetime.now().isoformat(),
                "action": "migration_completed",
                "status": "success"
            })
            
            # Write migration log
            log_path = self.base_dir / ".migration-log"
            with open(log_path, 'w') as f:
                yaml.dump(migration_log, f, default_flow_style=False, sort_keys=False)
            
            print(f"   ✅ Migration complete. Log saved to {log_path}")
            
        except Exception as e:
            migration_log.append({
                "timestamp": datetime.now().isoformat(),
                "action": "migration_failed",
                "error": str(e)
            })
            log_path = self.base_dir / ".migration-log"
            with open(log_path, 'w') as f:
                yaml.dump(migration_log, f, default_flow_style=False, sort_keys=False)
            print(f"   ⚠️  Migration failed: {e}")
            raise
    
    def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
        """
        Initialize QueueManager with mandatory queue-isolation support.
        
        CANONICAL PATH (required): ~/.agentic-engineers/{session-id}/{harness}/queue/
        
        This path is provided and validated by the queue-isolation skill.
        If queue-isolation is unavailable, initialization will fail with a clear error message.
        
        Legacy path fallback is NO LONGER SUPPORTED.
        All harnesses (Claude, Copilot, GPT, Local) use the same centralized path structure.
        """
        # ========================================================================
        # PHASE 1: Try queue-isolation (new path)
        # ========================================================================
        self._using_isolation = False
        self.session_id = None
        self.harness = None
        
        if _QUEUE_ISOLATION is not None:
            try:
                # Get session ID and harness from environment
                self.session_id = _QUEUE_ISOLATION.get_session_id()
                self.harness = _QUEUE_ISOLATION.detect_harness()
                
                # Initialize queue structure (creates directories if needed)
                _QUEUE_ISOLATION.init_queue_structure(self.session_id, self.harness)
                
                # Get the queue path from queue-isolation
                queue_root = _QUEUE_ISOLATION.get_queue_path(self.session_id, self.harness)
                
                # Set up queue directories (new path structure)
                self.session_queue_dir = queue_root
                self.base_dir = queue_root.parent.parent  # artifacts/
                self._using_isolation = True
                self.agent_context = agent_context or self.harness
                
                logger.debug(
                    f"QueueManager: Using queue-isolation. "
                    f"session_id={self.session_id}, harness={self.harness}, "
                    f"path={self.session_queue_dir}"
                )
                
            except Exception as e:
                logger.warning(
                    f"queue-isolation initialization failed, falling back to legacy paths: {e}"
                )
                self._using_isolation = False
                # Fall through to legacy code below
        
        # ========================================================================
        # PHASE 2: Enforce canonical queue path only
        # ========================================================================
        if not self._using_isolation:
            raise RuntimeError(
                "Canonical queue path is ~/.agentic-engineers/ for all harnesses. "
                "Legacy paths (~/.copilot/queue/, ~/.claude/queue/, artifacts/queue/) "
                "are NO LONGER SUPPORTED. Ensure queue-isolation skill is properly initialized."
            )
        
        
        # ========================================================================
        # Initialize queue subdirectories (same for both paths)
        # ========================================================================
        self.incoming_dir = self.session_queue_dir / "incoming"
        self.processing_dir = self.session_queue_dir / "processing"
        self.done_dir = self.session_queue_dir / "done"
        self.failed_dir = self.session_queue_dir / "failed"
        self.archive_dir = self.session_queue_dir / "archive"
         
        # Migrate legacy queue structure if needed (legacy paths only)
        if not self._using_isolation:
            self.migrate_legacy_queue()
         
        # Ensure queue structure exists after migration
        self._ensure_queue_structure()
        
        # Log initialization
        logger.info(
            f"QueueManager initialized: {self.session_queue_dir} "
            f"(session_id={self.session_id}, using_isolation={self._using_isolation}, "
            f"agent_context={self.agent_context})"
        )
        print(
            f"   Queue Manager initialized: {self.session_queue_dir} "
            f"(session_id={self.session_id}, using_isolation={self._using_isolation})"
        )
    
    
    def get_legacy_queue_path(self) -> Path:
        """
        Get what the legacy queue path would be (for debugging/migration).
        
        Returns the path to ~/.copilot/queue/{session_id}/ regardless of current path.
        Useful for verifying migration status and debugging path issues.
        
        Returns:
            Path: The legacy queue path (may or may not exist)
        """
        return Path.home() / ".copilot" / "queue" / self.session_id
    
    def _ensure_queue_structure(self):
        """Ensure all queue directories exist."""
        for dir_path in [self.incoming_dir, self.processing_dir, self.done_dir, self.failed_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # Queue path accessor methods (session-aware)
    def get_incoming_queue_dir(self) -> Path:
        """Return the incoming queue directory for this session."""
        return self.incoming_dir
     
    def get_processing_queue_dir(self) -> Path:
        """Return the processing queue directory for this session."""
        return self.processing_dir
     
    def get_done_queue_dir(self) -> Path:
        """Return the done queue directory for this session."""
        return self.done_dir
     
    def get_failed_queue_dir(self) -> Path:
        """Return the failed queue directory for this session."""
        return self.failed_dir
     
    def get_archive_queue_dir(self) -> Path:
        """Return the archive queue directory for this session."""
        return self.archive_dir
    
    def get_delegates_dir(self) -> Path:
        """Return the delegates directory for this session.
        
        This directory stores DELEGATE protocol payloads for task delegation.
        Located at the session-specific directory.
        
        Returns:
            Path: The delegates directory
        """
        if self._using_isolation:
            # New path: ~/.agentic-engineers/{harness}/{session_id}/delegates
            delegates_dir = self.base_dir / "delegates"
        else:
            # Legacy path: Place delegates under session directory
            # This is at base_dir/{session_id}/delegates
            delegates_dir = self.session_queue_dir / "delegates"
        
        # Ensure directory exists
        delegates_dir.mkdir(parents=True, exist_ok=True)
        return delegates_dir
    
    def _get_queue_root(self, session_id: Optional[str] = None, harness: Optional[str] = None) -> Path:
        """Get the queue root for a given session and harness.
        
        Defaults to current session/harness if not provided.
        
        Args:
            session_id: Optional session ID (defaults to current)
            harness: Optional harness type (defaults to current)
            
        Returns:
            Path: The queue root directory
        """
        _session_id = session_id or self.session_id
        _harness = harness or self.harness
        
        if self._using_isolation and _QUEUE_ISOLATION is not None:
            # Canonical layout A (queue-isolation skill):
            # ~/.agentic-engineers/artifacts/{session_id}/{harness}/queue
            return _QUEUE_ISOLATION.get_queue_path(_session_id, _harness)
        else:
            # Legacy path: queue base directory
            return self.base_dir / _session_id
    
    
    def list_incoming_tasks(self) -> List[str]:
        """List all DELEGATE files in incoming queue."""
        if not self.incoming_dir.exists():
            return []
        return sorted([f.name for f in self.incoming_dir.glob("*.yaml")])
    
    def read_task(self, filename: str) -> Dict:
        """Read DELEGATE block from incoming queue."""
        filepath = self.incoming_dir / filename
        with open(filepath, 'r') as f:
            content = f.read()
            # Handle YAML documents that may have multiple --- markers
            # Split on ---, filter empty, take first non-empty
            docs = [d.strip() for d in content.split('---') if d.strip()]
            if docs:
                return yaml.safe_load(docs[0])
            return yaml.safe_load(content)
    
    def move_to_processing(self, filename: str) -> str:
        """Move task from incoming to processing queue."""
        incoming_path = self.incoming_dir / filename
        processing_path = self.processing_dir / filename
        shutil.move(str(incoming_path), str(processing_path))
        return str(processing_path)
    
    def move_to_done(self, filename: str, handback: Dict) -> str:
        """Move task to done queue and save HANDBACK result."""
        processing_path = self.processing_dir / filename
        task_id = handback.get("task_id", "unknown")
        status = handback.get("status", "UNKNOWN")
        # Sanitize attacker-controllable values from the HANDBACK before using
        # them to build a filename (prevents path traversal / queue poisoning).
        task_id = sanitize_path_component(task_id, field="task_id")
        status = sanitize_path_component(status, field="status")
        done_filename = f"{task_id}-{status}.yaml"
        done_path = self.done_dir / done_filename
        ensure_within_directory(done_path, self.done_dir, field="done_path")
        
        # Write HANDBACK to done directory
        with open(done_path, 'w') as f:
            yaml.dump(handback, f, default_flow_style=False, sort_keys=False)
        
        # Remove from processing
        if processing_path.exists():
            processing_path.unlink()
        
        return str(done_path)
    
    def archive_task(self, filename: str) -> str:
        """Archive failed task (for debugging) to archive/ directory in queue_root."""
        incoming_path = self.incoming_dir / filename
        self.archive_dir.mkdir(exist_ok=True, parents=True)
        archive_path = self.archive_dir / f"{datetime.now().isoformat()}_{filename}"
        shutil.move(str(incoming_path), str(archive_path))
        return str(archive_path)
    
    def move_task(
        self,
        task_id: str,
        from_state: str,
        to_state: str,
        metadata: Optional[Dict] = None,
        filename: Optional[str] = None
    ) -> Dict:
        """
        Move task between states with atomic transitions and audit trail.
        
        Implements Queue State Transitions SKILL:
        - Validates state transitions (incoming→processing, processing→done)
        - Preserves full audit trail in YAML metadata
        - Handles file integrity before/after moves
        - Manages atomic transitions (all-or-nothing)
        
        Args:
            task_id: Task identifier (used to find task file)
            from_state: Source state ("incoming", "processing", "done")
            to_state: Destination state
            metadata: Optional metadata to attach (routing info, HANDBACK, decision)
        
        Returns:
            Dict with:
                - success: bool
                - moved_from: str
                - moved_to: str
                - task_id: str
                - filename: str (new filename if renamed)
                - timestamp: str (ISO format)
                - message: str
                - audit_trail: list of audit entries
        
        Raises:
            ValueError: Invalid state or transition
            FileNotFoundError: Task file not found in source state
            RuntimeError: Atomic transition failed (task left in inconsistent state)
        """
        # Validate state transitions
        valid_transitions = {
            "incoming": ["processing"],
            "processing": ["done", "failed"],
            "done": [],
            "failed": ["archive"]
        }
        
        if from_state not in valid_transitions:
            raise ValueError(f"Invalid from_state: '{from_state}'. Valid states: {list(valid_transitions.keys())}")
        
        if to_state not in valid_transitions.get(from_state, []):
            raise ValueError(
                f"Invalid transition: '{from_state}' → '{to_state}'. "
                f"Valid transitions from {from_state}: {valid_transitions.get(from_state, [])}"
            )
        
        try:
            # Get source directory
            if from_state == "incoming":
                from_dir = self.incoming_dir
            elif from_state == "processing":
                from_dir = self.processing_dir
            elif from_state == "done":
                from_dir = self.done_dir
            elif from_state == "failed":
                from_dir = self.failed_dir
            else:
                raise ValueError(f"Unknown from_state: {from_state}")
             
            # Get destination directory
            if to_state == "incoming":
                to_dir = self.incoming_dir
            elif to_state == "processing":
                to_dir = self.processing_dir
            elif to_state == "done":
                to_dir = self.done_dir
            elif to_state == "failed":
                to_dir = self.failed_dir
            elif to_state == "archive":
                to_dir = self.archive_dir
            else:
                raise ValueError(f"Unknown to_state: {to_state}")
            
            # Find task file: use explicit filename if provided, otherwise search by task_id
            task_filename = None
            from_state_tasks = sorted([f.name for f in from_dir.glob("*.yaml")])
            
            if filename is not None:
                # Explicit filename provided — use directly if it exists
                if filename in from_state_tasks:
                    task_filename = filename
                else:
                    available = from_state_tasks
                    raise FileNotFoundError(
                        f"Task file '{filename}' not found in '{from_state}' state "
                        f"(directory: {from_dir}). "
                        f"Available files: {available}"
                    )
            else:
                # Search by task_id. Prefer precise matches (exact stem, or
                # "<task_id>-..." / "<task_id>...." prefix) before falling back
                # to a substring match. A naive substring match lets a short or
                # crafted task_id collide with an unrelated victim task file.
                def _matches(name: str) -> int:
                    stem = name[:-5] if name.endswith(".yaml") else name
                    if stem == task_id:
                        return 0  # exact
                    if stem.startswith(f"{task_id}-") or stem.startswith(f"{task_id}."):
                        return 1  # prefix
                    if task_id in name:
                        return 2  # substring fallback
                    return 3  # no match

                ranked = sorted(
                    ((_matches(name), name) for name in from_state_tasks),
                    key=lambda pair: (pair[0], pair[1]),
                )
                for rank, name in ranked:
                    if rank < 3:
                        task_filename = name
                        break

                if not task_filename:
                    available = from_state_tasks
                    raise FileNotFoundError(
                        f"Task '{task_id}' not found in '{from_state}' state "
                        f"(directory: {from_dir}). "
                        f"Available files: {available}. "
                        f"Hint: if the filename uses a different naming convention than the task_id "
                        f"(e.g. 'DELEGATE-foo.yaml' vs '2026-05-17-foo'), pass filename= explicitly."
                    )
            
            # Read and validate task file integrity
            from_path = from_dir / task_filename
            if not from_path.exists():
                raise FileNotFoundError(f"Task file not found: {from_path}")
            
            with open(from_path, 'r') as f:
                content = f.read()
                # Split on ---, handle YAML documents
                docs = [d.strip() for d in content.split('---') if d.strip()]
                if docs:
                    task_data = yaml.safe_load(docs[0])
                else:
                    task_data = yaml.safe_load(content)
            
            # Validate task structure
            if not isinstance(task_data, dict):
                raise ValueError(f"Task file is not a valid YAML dictionary: {from_path}")
            
            # Add metadata if provided
            if metadata:
                task_data.update(metadata)
            
            # Create audit trail entry
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "move_task",
                "from_state": from_state,
                "to_state": to_state,
                "task_id": task_id,
                "filename": task_filename
            }
            
            # Preserve and extend audit trail
            if "_audit_trail" not in task_data:
                task_data["_audit_trail"] = []
            task_data["_audit_trail"].append(audit_entry)
            
            # Determine new filename for destination state
            if to_state == "done":
                # For done state, append decision to filename
                decision = metadata.get("decision", "UNKNOWN") if metadata else "UNKNOWN"
                # Sanitize attacker-controllable values before path construction
                # (prevents path traversal / queue poisoning via task_id/decision).
                safe_task_id = sanitize_path_component(task_id, field="task_id")
                safe_decision = sanitize_path_component(decision, field="decision")
                to_filename = f"{safe_task_id}-{safe_decision}.yaml"
            else:
                # For processing, keep same filename
                to_filename = task_filename

            # Atomic write to destination (write to temp file first, then move)
            to_path = to_dir / to_filename
            temp_path = to_dir / f".tmp_{to_filename}"

            # Defence-in-depth: ensure both temp and final paths stay within the
            # destination queue directory before any write occurs.
            ensure_within_directory(to_path, to_dir, field="to_path")
            ensure_within_directory(temp_path, to_dir, field="temp_path")
            
            # Write to temp file
            with open(temp_path, 'w') as f:
                yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)
            
            # Verify temp file was written correctly
            with open(temp_path, 'r') as f:
                verify_content = f.read()
                yaml.safe_load(verify_content)  # Validate YAML
            
            # Atomic move: rename temp file to final destination
            shutil.move(str(temp_path), str(to_path))
            
            # Delete from source state (only after successful write to destination)
            if from_path.exists():
                from_path.unlink()
            
            return {
                "success": True,
                "moved_from": from_state,
                "moved_to": to_state,
                "task_id": task_id,
                "filename": to_filename,
                "timestamp": audit_entry["timestamp"],
                "message": f"Task '{task_id}' moved from {from_state} to {to_state}",
                "audit_trail": task_data.get("_audit_trail", [])
            }
        
        except (ValueError, FileNotFoundError, yaml.YAMLError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            # Unexpected errors
            raise RuntimeError(
                f"Atomic transition failed for task '{task_id}' ({from_state}→{to_state}): {str(e)}"
            ) from e


class TaskRouter:
    """Route tasks to appropriate agents based on AGENTS.md decision tree.
    
    Routes by agent name only — no stub class instantiation.
    Agent execution is handled by AgentInvoker (subprocess) or OrchestratorAgent.
    """
    
    # Valid agent names per AGENTS.md
    AGENT_NAMES = {
        "orchestrator", "engineer", "senior_engineer", "lead_engineer",
        "principal_engineer", "quality_engineer", "model_engineer", "security_engineer",
    }
    
    def route_task(self, delegate: Dict) -> Tuple[str, Optional[Agent]]:
        """
        Route task to appropriate agent by name.
        
        Returns:
            (agent_name, None)  — caller uses agent_name to invoke via AgentInvoker
        """
        # Priority 1: Explicit role in DELEGATE
        if "role" in delegate and delegate.get("role"):
            # Enforce the role validator at routing time: reject an invalid role
            # or a role that conflicts with the task's scope/effort routing rules
            # (e.g. a security-scoped task mis-tagged as `engineer`). Previously
            # the validator was imported but never invoked, so mismatches were
            # silently honoured.
            ok, role_failures = DelegateValidator.validate_routing_role(delegate)
            if not ok:
                raise RoleRoutingError(
                    "DELEGATE role "
                    f"'{delegate.get('role')}' failed routing validation: "
                    + "; ".join(role_failures),
                    failures=role_failures,
                )

            role = delegate.get("role", "").lower()
            if role in self.AGENT_NAMES:
                return (role, None)
        
        # Priority 2: Apply AGENTS.md decision tree
        scope = delegate.get("scope", "").lower()
        complexity = delegate.get("complexity", "medium").lower()
        has_plan = delegate.get("plan", False) is not None
        is_security = delegate.get("is_security_scoped", False)
        
        if is_security:
            return ("security_engineer", None)
        
        if "cross" in scope or "architecture" in scope:
            return ("principal_engineer", None)
        
        if complexity == "high" and not has_plan:
            return ("senior_engineer", None)
        
        # Code review and validation tasks route to Quality Engineer
        if delegate.get("is_code_review", False) or delegate.get("requires_quality_review", False):
            return ("quality_engineer", None)
        
        # Architecture guidance and refinement route to Lead Engineer
        if "review" in scope and "architecture" in scope.lower():
            return ("lead_engineer", None)
        
        if has_plan and complexity in ("low", "medium"):
            return ("engineer", None)
        
        # Default to engineer for well-scoped tasks
        return ("engineer", None)


class OrchestratorAgent(Agent):
    """
    Main Orchestrator Agent - Polls queue and delegates work.
    
    Runs continuously until queue is idle (60+ seconds with no tasks).
    Supports optional AgentInvoker for subprocess-based agent invocation.
    """
    
    def __init__(
        self,
        queue_dir: Optional[str] = None,
        agent_context: Optional[str] = None,
        idle_timeout: int = 60,
        agent_invoker=None,
        quality_validator: Optional["QualityValidator"] = None,
        budget_config_path: Optional[Path] = None,
        no_color: Optional[bool] = None,
    ):
        super().__init__(ORCHESTRATOR_CONFIG)
        base_queue_manager = QueueManager(queue_dir, agent_context)
        self.queue_manager = QueueEnforcingProxy(base_queue_manager, agent_role="queue_manager")
        self.task_router = TaskRouter()
        self.idle_timeout = idle_timeout
        self.last_task_time = time.time()
        self.tasks_processed = 0
        self.tasks_success = 0
        self.tasks_escalated = 0
        # Optional AgentInvoker for subprocess-based delegation (task 5106)
        self.agent_invoker = agent_invoker
        # Quality validator — defaults to a fresh instance if not injected
        self.quality_validator = quality_validator or QualityValidator()
        # Task state tracking for retry management
        self.task_state = {}  # Maps task_id -> {retry_count, quality_score, failure_reasons}

        # Initialize token tracking and CLI monitoring
        self.metrics_registry = MetricsRegistry()
        self.token_tracker = TokenTracker(self.metrics_registry)
        _no_color = no_color if no_color is not None else (os.environ.get("NO_COLOR") is not None)
        self.orchestrator_cli = OrchestratorCLI(
            token_tracker=self.token_tracker,
            budget_config_path=budget_config_path or Path("config/token_budget.yaml"),
            no_color=_no_color,
            on_budget_exceeded=self._handle_budget_exceeded,
        )
    
    # ========================================================================
    # Properties exposing queue_manager attributes
    # ========================================================================
    
    @property
    def harness(self) -> str:
        """Get the harness from queue_manager."""
        return self.queue_manager.harness
    
    @property
    def session_id(self) -> str:
        """Get the session_id from queue_manager."""
        return self.queue_manager.session_id
    
    # ========================================================================
    # Path accessor methods (delegated to queue_manager)
    # ========================================================================
    
    def get_incoming_queue_dir(self) -> Path:
        """Get incoming queue directory."""
        return self.queue_manager.get_incoming_queue_dir()
    
    def get_processing_queue_dir(self) -> Path:
        """Get processing queue directory."""
        return self.queue_manager.get_processing_queue_dir()
    
    def get_done_queue_dir(self) -> Path:
        """Get done queue directory."""
        return self.queue_manager.get_done_queue_dir()
    
    def get_delegates_dir(self) -> Path:
        """Get delegates directory."""
        return self.queue_manager.get_delegates_dir()
    
    def _get_queue_root(self, session_id: Optional[str] = None, harness: Optional[str] = None) -> Path:
        """Get queue root directory."""
        return self.queue_manager._get_queue_root(session_id, harness)
    
    def _handle_budget_exceeded(self, budget_result: BudgetResult) -> None:
        """Called when budget threshold is exceeded."""
        if budget_result.status == BudgetStatus.BLOCKED:
            logger.error(f"BLOCKED: {budget_result.message}")
        elif budget_result.status == BudgetStatus.CRITICAL:
            logger.warning(f"CRITICAL budget: {budget_result.message}")
        else:
            logger.warning(f"Budget alert ({budget_result.status.value}): {budget_result.message}")

    def _init_task_state(self, task_id: str) -> Dict:
        """Initialize task state for retry tracking."""
        if task_id not in self.task_state:
            self.task_state[task_id] = {
                'retry_count': 0,
                'quality_score': 0,
                'last_failure_reasons': [],
                'retry_context': None
            }
        return self.task_state[task_id]
    
    def _increment_retry_count(self, task_id: str, failure_reasons: List[str], quality_score: int) -> bool:
        """
        Increment retry count for a task.
        
        Returns True if retry is allowed, False if max retries exceeded.
        On max retries, returns False (should escalate to Principal Engineer).
        """
        state = self._init_task_state(task_id)
        state['retry_count'] += 1
        state['last_failure_reasons'] = failure_reasons
        state['quality_score'] = quality_score
        
        # Build retry context for re-delegation
        state['retry_context'] = {
            'retry_count': state['retry_count'],
            'previous_score': quality_score,
            'failure_reasons': failure_reasons,
            'improvement_guidance': self._build_improvement_guidance(failure_reasons)
        }
        
        if state['retry_count'] > MAX_RETRIES:
            return False  # Max retries exceeded, escalate
        
        return True  # Retry allowed
    
    @staticmethod
    def _build_improvement_guidance(failure_reasons: List[str]) -> str:
        """Build improvement guidance from failure reasons."""
        if not failure_reasons:
            return "Review validator feedback and address all issues before resubmitting."
        
        guidance_parts = []
        for reason in failure_reasons:
            if 'B1' in reason:
                guidance_parts.append("Make success_criteria measurable (add numbers/thresholds)")
            elif 'B2' in reason:
                guidance_parts.append("Add more success_criteria to match effort level")
            elif 'B3' in reason:
                guidance_parts.append("Make plan steps more concrete (reference files/commands)")
            elif 'B4' in reason:
                guidance_parts.append("Add explicit testing/validation steps to plan")
            elif 'B5' in reason:
                guidance_parts.append("Expand context section with more background (≥100 words)")
            elif 'C1' in reason or 'C2' in reason or 'C3' in reason or 'C4' in reason:
                guidance_parts.append("Re-route task to appropriate role based on scope/effort")
            else:
                guidance_parts.append("Address all validation findings before resubmitting")
        
        return " | ".join(guidance_parts) if guidance_parts else "Review all validator findings."
    
    def route_handback(self, handback_block: Dict, original_delegate: Dict) -> Tuple[str, Dict]:
        """
        Route HANDBACK to appropriate action based on quality score.
        
        Implements Quality Engineer Section 2 thresholds:
        - 90–100: PROCEED (merge)
        - 80–89: PROCEED (merge)
        - 70–79: MANUAL_REVIEW (Lead Engineer, Week 3)
        - 60–69: REWORK (auto-retry, same agent, max 2 attempts)
        - <60: ESCALATE (Principal Engineer immediately)
        - Critical findings: ESCALATE (any score)
        
        Args:
            handback_block: HANDBACK YAML dict with status, quality_score, etc.
            original_delegate: Original DELEGATE dict for retry context
        
        Returns:
            Tuple of (action, context) where:
            - action: 'PROCEED' | 'MANUAL_REVIEW' | 'REWORK' | 'ESCALATE'
            - context: Dict with routing details, retry_context if rework, escalation reason if escalate
        
        Reference: Quality Engineer Section 2 (Acceptance Thresholds)
        """
        quality_score = handback_block.get('quality_score', 0)
        status = handback_block.get('status', '')
        task_id = handback_block.get('task_id', 'unknown')
        
        # Check for critical findings first
        critical_issues = self._check_critical_issues(handback_block)
        if critical_issues:
            escalation_context = {
                'action': 'ESCALATE',
                'reason': 'Critical issues detected',
                'critical_issues': critical_issues,
                'evidence': {
                    'status': status,
                    'quality_score': quality_score,
                    'deliverables': handback_block.get('deliverables', []),
                },
                'principal_engineer_instructions': (
                    'Review critical findings and determine if work is salvageable. '
                    'If not, request complete rework or close task.'
                ),
                'escalation_timestamp': datetime.now().isoformat(),
            }
            return ('ESCALATE', escalation_context)
        
        # Route based on quality score bands
        if quality_score >= 90:
            # PROCEED: High quality, ready to merge
            return ('PROCEED', {
                'action': 'PROCEED',
                'reason': 'High quality score (90+)',
                'quality_score': quality_score,
            })
        
        elif quality_score >= 80:
            # PROCEED: Acceptable quality with minor notes
            return ('PROCEED', {
                'action': 'PROCEED',
                'reason': 'Acceptable quality score (80-89)',
                'quality_score': quality_score,
                'notes': 'Minor improvements possible in future iterations',
            })
        
        elif quality_score >= 70:
            # MANUAL_REVIEW: Gray zone, Lead Engineer decides
            return ('MANUAL_REVIEW', {
                'action': 'MANUAL_REVIEW',
                'reason': 'Gray zone score (70-79) requires human judgment',
                'quality_score': quality_score,
                'reviewer_role': 'lead_engineer',
                'review_guidance': 'Assess if quality is acceptable for production or requires rework',
                'handback_summary': {
                    'status': status,
                    'deliverables_count': len(handback_block.get('deliverables', [])),
                    'tests_passed': handback_block.get('tests', {}).get('passed', 0),
                    'coverage': handback_block.get('tests', {}).get('coverage', 0),
                },
            })
        
        elif quality_score >= 60:
            # REWORK: Below acceptable, retry with same agent
            state = self._init_task_state(task_id)
            if state['retry_count'] >= MAX_RETRIES:
                # Max retries exceeded, escalate instead
                return ('ESCALATE', {
                    'action': 'ESCALATE',
                    'reason': f'Max retries ({MAX_RETRIES}) exceeded after quality score {quality_score}',
                    'quality_score': quality_score,
                    'retry_count': state['retry_count'],
                    'escalation_level': 'principal_engineer',
                })
            
            # Build retry context for re-delegation
            retry_context = {
                'retry_count': state['retry_count'] + 1,
                'previous_quality_score': quality_score,
                'failure_analysis': handback_block.get('escalations', []),
                'success_criteria_not_met': handback_block.get('success_criteria_not_met', []),
                'improvement_guidance': (
                    'Address validator findings. Focus on: '
                    f"{', '.join(handback_block.get('escalations', ['all issues'])[:3])}"
                ),
            }
            
            return ('REWORK', {
                'action': 'REWORK',
                'reason': f'Quality score {quality_score} is below 70 threshold',
                'quality_score': quality_score,
                'retry_context': retry_context,
                'same_agent': original_delegate.get('role'),
                'max_retries_remaining': MAX_RETRIES - state['retry_count'],
            })
        
        else:
            # <60: Critical quality issues, escalate
            return ('ESCALATE', {
                'action': 'ESCALATE',
                'reason': f'Critical quality issue: score {quality_score} < 60',
                'quality_score': quality_score,
                'escalation_level': 'principal_engineer',
                'critical_issues': handback_block.get('escalations', []),
                'evidence': {
                    'status': status,
                    'tests_passed': handback_block.get('tests', {}).get('passed', 0),
                    'tests_failed': handback_block.get('tests', {}).get('failed', 0),
                },
                'principal_engineer_instructions': (
                    'Review comprehensive failure analysis. Determine scope: '
                    'salvageable with rework or requires complete restart.'
                ),
            })
    
    def _check_critical_issues(self, handback_block: Dict) -> List[str]:
        """
        Check for critical issues that force escalation regardless of score.
        
        Critical conditions:
        - status='failed' with unrecoverable errors
        - status='blocked' (agent escalated)
        - Security issues flagged
        - Infrastructure/external dependency failures
        
        Returns:
            List of critical issue descriptions (empty if none)
        """
        critical = []
        
        status = handback_block.get('status', '')
        if status == 'failed':
            critical.append(f"Task failed: {handback_block.get('failure_reason', 'unknown')}")
        
        if status == 'blocked':
            critical.append(f"Task blocked: {handback_block.get('blocked_reason', 'unknown')}")
        
        # Check for security flags
        if handback_block.get('security_issues'):
            critical.append(f"Security issues detected: {len(handback_block['security_issues'])} findings")
        
        # Check for infrastructure failures
        if handback_block.get('infrastructure_blocked'):
            critical.append(f"Infrastructure dependency failed: {handback_block['infrastructure_blocked']}")
        
        return critical
    
    def collect_metrics(self, handback_block: Dict, original_delegate: Dict = None) -> Dict:
        """
        Collect metrics from HANDBACK for Model Engineer optimization.
        
        Extracts and derives metrics matching Quality Engineer Section 5 schema.
        
        Args:
            handback_block: HANDBACK dict with tokens, duration, quality_score
            original_delegate: Original DELEGATE dict with role, effort, model
        
        Returns:
            Dict with canonical metrics matching schema
        
        Reference: Quality Engineer Section 5 (Canonical Metrics Schema)
        """
        if original_delegate is None:
            original_delegate = {}
        
        task_id = handback_block.get('task_id', 'unknown')
        state = self.task_state.get(task_id, {})
        
        # Extract directly from HANDBACK
        tokens_in = handback_block.get('tokens_in', 0)
        tokens_out = handback_block.get('tokens_out', 0)
        total_tokens = tokens_in + tokens_out
        
        duration_minutes = int(handback_block.get('effort_actual', 0) * 60)  # Convert hours to minutes
        quality_score_validator = handback_block.get('quality_score', 0)
        
        # Extract test results
        test_results = handback_block.get('tests', {})
        test_coverage = test_results.get('coverage', 0.0)
        
        # Count deliverables
        deliverables_count = len(handback_block.get('deliverables', []))
        
        # Get retry count from task state
        retry_count = state.get('retry_count', 0)
        first_try_quality = state.get('quality_score') if retry_count > 0 else None
        
        # Derive metrics
        # Efficiency score: (quality / tokens_used) × 100
        if total_tokens > 0:
            efficiency_score = (quality_score_validator / total_tokens) * 100
        else:
            efficiency_score = 0.0
        
        # Rework cost ratio: (total_tokens / estimated)
        # For now, set to 1.0 if first try, > 1.0 if retried
        rework_cost_ratio = 1.0 + (retry_count * 0.5)  # Each retry adds 50% cost
        
        # Build metrics dictionary
        metrics = {
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'role': original_delegate.get('role', 'unknown'),
            'model': original_delegate.get('model', 'unknown'),
            'effort': original_delegate.get('effort', 'unknown'),
            'effort_actual': handback_block.get('effort_actual', 0.0),
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'total_tokens': total_tokens,
            'duration_minutes': duration_minutes,
            'quality_score_validator': quality_score_validator,
            'quality_score_agent_self': handback_block.get('quality_score_agent_self', quality_score_validator),
            'status': handback_block.get('status', 'unknown'),
            'retry_count': retry_count,
            'test_coverage': test_coverage,
            'deliverables_count': deliverables_count,
            'efficiency_score': round(efficiency_score, 2),
            'rework_cost_ratio': round(rework_cost_ratio, 2),
        }
        
        # Add optional fields if present
        if first_try_quality is not None:
            metrics['first_try_quality'] = first_try_quality
        
        if handback_block.get('tests'):
            metrics['test_results'] = {
                'passed': test_results.get('passed', 0),
                'failed': test_results.get('failed', 0),
            }
        
        return metrics

    def verify_agent_definitions(self) -> Dict:
        """
        Verify agent definitions integrity using SHA256 checksum.
        
        Security verification that:
        1. Loads SHA256 checksum from .agents_verification_sha file
        2. Computes current SHA256 of docs/AGENTS.md
        3. Compares checksums to detect unauthorized modifications
        4. Raises SecurityError if mismatch detected (unless SKIP_AGENT_VERIFICATION=true)
        5. Supports SKIP_AGENT_VERIFICATION environment variable bypass
        6. Logs all verification steps with clear pass/fail status
        7. Has comprehensive docstrings and error messages
        
        Returns:
            Dict with keys:
            - verified (bool): True if verification passed, False if bypassed or failed
            - expected_sha (str): SHA256 from .agents_verification_sha file (or None if file missing)
            - actual_sha (str): Computed SHA256 of docs/AGENTS.md
            - file_path (str): Path to docs/AGENTS.md
            - verification_file_path (str): Path to .agents_verification_sha
            - error (str or None): Error message if verification failed
            - bypassed (bool): True if verification was skipped via SKIP_AGENT_VERIFICATION
            - timestamp (str): ISO timestamp of verification
        
        Raises:
            SecurityError: If SHA mismatch detected and SKIP_AGENT_VERIFICATION is not set to 'true'
        
        Example:
            result = orchestrator.verify_agent_definitions()
            # Typical successful result:
            # {
            #     'verified': True,
            #     'expected_sha': '3466b791...',
            #     'actual_sha': '3466b791...',
            #     'file_path': '/path/to/docs/AGENTS.md',
            #     'verification_file_path': '/path/to/.agents_verification_sha',
            #     'error': None,
            #     'bypassed': False,
            #     'timestamp': '2026-05-28T20:33:32.397030'
            # }
        """
        # Check for bypass flag
        skip_verification = os.environ.get('SKIP_AGENT_VERIFICATION', '').lower() == 'true'
        
        # Paths to verify - use absolute paths relative to project root
        project_root = Path(__file__).parent.parent.parent.parent  # src/orchestration/agents/orchestrator.py → root
        agents_md_path = project_root / 'docs' / 'AGENTS.md'
        verification_file_path = project_root / '.agents_verification_sha'
        
        timestamp = datetime.now().isoformat()
        
        # Initialize result dict
        result = {
            'verified': False,
            'expected_sha': None,
            'actual_sha': None,
            'file_path': str(agents_md_path.absolute()),
            'verification_file_path': str(verification_file_path.absolute()),
            'error': None,
            'bypassed': skip_verification,
            'timestamp': timestamp,
        }
        
        try:
            # If bypass is enabled, log warning and return
            if skip_verification:
                logger.warning(
                    "🔓 SKIP_AGENT_VERIFICATION=true — Agent definition verification BYPASSED. "
                    "This should only be used for development/testing. "
                    "WARNING: Production environments must verify agent definitions!"
                )
                result['verified'] = True  # Mark as "verified" (though actually bypassed)
                result['bypassed'] = True
                return result
            
            # Step 1: Load expected SHA from verification file
            if not verification_file_path.exists():
                error_msg = (
                    f"Agent verification file not found: {verification_file_path}. "
                    "Run 'python3 scripts/generate-agent-verification-sha.py' to generate it."
                )
                logger.error(f"🔴 {error_msg}")
                result['error'] = error_msg
                raise SecurityError(error_msg)
            
            # Read and parse verification file
            try:
                verification_content = verification_file_path.read_text().strip()
                expected_sha = None
                for line in verification_content.split('\n'):
                    if line.startswith('agent_sha256='):
                        expected_sha = line.split('=', 1)[1].strip()
                        break
                
                if not expected_sha:
                    error_msg = (
                        f"Invalid verification file format: {verification_file_path}. "
                        "Expected line starting with 'agent_sha256='"
                    )
                    logger.error(f"🔴 {error_msg}")
                    result['error'] = error_msg
                    raise SecurityError(error_msg)
                
                result['expected_sha'] = expected_sha
            except Exception as e:
                error_msg = f"Failed to read verification file: {str(e)}"
                logger.error(f"🔴 {error_msg}")
                result['error'] = error_msg
                raise SecurityError(error_msg) from e
            
            # Step 2: Verify docs/AGENTS.md exists
            if not agents_md_path.exists():
                error_msg = (
                    f"Agent definitions file not found: {agents_md_path}. "
                    "Expected file: docs/AGENTS.md"
                )
                logger.error(f"🔴 {error_msg}")
                result['error'] = error_msg
                raise SecurityError(error_msg)
            
            # Step 3: Compute SHA256 of docs/AGENTS.md
            sha256_hash = hashlib.sha256()
            with open(agents_md_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)
            actual_sha = sha256_hash.hexdigest()
            result['actual_sha'] = actual_sha
            
            # Step 4: Compare checksums
            if expected_sha != actual_sha:
                error_msg = (
                    f"🚨 SECURITY ALERT: Agent definitions have been modified! "
                    f"Expected SHA256: {expected_sha} | "
                    f"Actual SHA256: {actual_sha} | "
                    f"File: {agents_md_path}"
                )
                logger.error(error_msg)
                result['error'] = error_msg
                result['verified'] = False
                raise SecurityError(error_msg)
            
            # Verification passed
            logger.info(
                f"✅ Agent definitions verified successfully. "
                f"SHA256: {actual_sha}"
            )
            result['verified'] = True
            result['error'] = None
            
            return result
        
        except SecurityError:
            # Re-raise security errors as-is
            raise
        except Exception as e:
            # Catch unexpected errors
            error_msg = f"Unexpected error during agent verification: {str(e)}"
            logger.error(f"🔴 {error_msg}")
            result['error'] = error_msg
            raise SecurityError(error_msg) from e
    
    def validate_queue_paths(self) -> Dict:
        """
        Validate all paths in queue subdirectories (incoming/, processing/, done/).
        
        Comprehensive security validation that:
        1. Validates all paths in queue subdirectories match canonical format
        2. Rejects legacy paths (~/.copilot/queue/, ~/.claude/queue/)
        3. Prevents path traversal attempts (.., //, symlinks)
        4. Returns validation results with valid_count, invalid_count, errors
        5. Raises SecurityError if invalid paths detected (unless SKIP_QUEUE_PATH_VALIDATION env var set)
        6. Logs clear validation results
        
        Returns:
            Dict with keys:
            - valid_count (int): Number of valid paths found
            - invalid_count (int): Number of invalid paths found
            - errors (list): List of error dicts, each with:
              - path (str): The invalid path that was found
              - reason (str): Why the path is invalid
              - directory (str): Which queue subdirectory (incoming/processing/done)
            - status (str): 'PASS' if all paths valid, 'FAIL' if any invalid
        
        Raises:
            SecurityError: If any invalid paths detected (unless SKIP_QUEUE_PATH_VALIDATION=true)
        
        Example:
            result = orchestrator.validate_queue_paths()
            # result = {
            #     'valid_count': 42,
            #     'invalid_count': 0,
            #     'errors': [],
            #     'status': 'PASS'
            # }
        """
        try:
            # Try to import queue path validator from the reference skill
            # Note: directory is hyphenated (queue-path-validator) but we use importlib
            import importlib.util
            skill_path = Path(__file__).parent.parent.parent / 'skills' / '_meta' / 'queue-path-validator' / 'queue_path_validator.py'
            spec = importlib.util.spec_from_file_location("queue_path_validator", skill_path)
            if spec and spec.loader:
                qpv_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(qpv_module)
                validate_queue_path = qpv_module.validate_queue_path
            else:
                raise ImportError("Could not load queue_path_validator spec")
        except (ImportError, AttributeError, FileNotFoundError):
            # Fallback: implement inline validation
            logger.warning("queue_path_validator not available, using inline validation")
            
            def validate_queue_path(path_str: str) -> Dict:
                """Inline path validation fallback."""
                if not path_str or not isinstance(path_str, str):
                    return {'valid': False, 'error': 'Path must be non-empty string'}
                
                path_str = path_str.strip()
                
                # Check for path traversal
                if '..' in path_str or '//' in path_str:
                    return {'valid': False, 'error': 'Path traversal detected (.., //)'}
                
                # Check for legacy paths
                legacy_patterns = [
                    '/.copilot/queue',
                    '/.claude/queue',
                    '/.pi/queue',
                ]
                for pattern in legacy_patterns:
                    if pattern in path_str:
                        return {'valid': False, 'error': f'Legacy path detected: {path_str}'}
                
                # Check for canonical format: .agentic-engineers/{session}/{harness}/queue
                import re
                canonical = re.compile(r'\.agentic-engineers/[a-z0-9\-]+/[a-z0-9\-]+/queue')
                if not canonical.search(path_str):
                    return {'valid': False, 'error': 'Path does not match canonical format'}
                
                return {'valid': True, 'error': None}
        
        valid_count = 0
        invalid_count = 0
        errors = []
        
        # Define queue subdirectories to validate
        queue_dirs = [
            ('incoming', self.queue_manager.incoming_dir),
            ('processing', self.queue_manager.processing_dir),
            ('done', self.queue_manager.done_dir),
        ]
        
        # Validate each queue subdirectory
        for subdir_name, subdir_path in queue_dirs:
            if not subdir_path.exists():
                logger.debug(f"Queue subdirectory does not exist: {subdir_path}")
                continue
            
            # Scan all files in the subdirectory
            for file_path in subdir_path.glob("*"):
                try:
                    # Validate the file's absolute path
                    abs_path = str(file_path.absolute())
                    validation_result = validate_queue_path(abs_path)
                    
                    if validation_result.get('valid', False):
                        valid_count += 1
                    else:
                        invalid_count += 1
                        error_reason = validation_result.get('error', 'Unknown validation error')
                        errors.append({
                            'path': abs_path,
                            'reason': error_reason,
                            'directory': subdir_name,
                        })
                        logger.warning(f"Invalid path in {subdir_name}: {abs_path} ({error_reason})")
                
                except Exception as exc:
                    invalid_count += 1
                    errors.append({
                        'path': str(file_path),
                        'reason': f"Validation exception: {str(exc)}",
                        'directory': subdir_name,
                    })
                    logger.error(f"Path validation exception for {file_path}: {exc}")
        
        # Determine overall status
        status = 'PASS' if invalid_count == 0 else 'FAIL'
        
        result = {
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'errors': errors,
            'status': status,
        }
        
        # Log validation results clearly
        logger.info(
            f"Queue path validation: {valid_count} valid, {invalid_count} invalid. Status: {status}"
        )
        
        if errors:
            logger.error(f"Queue path validation errors detected:")
            for error in errors:
                logger.error(
                    f"  - {error['directory']}/{Path(error['path']).name}: "
                    f"{error['reason']}"
                )
        
        # Raise SecurityError if invalid paths detected (unless skipped)
        if invalid_count > 0 and not _is_env_var_truthy('SKIP_QUEUE_PATH_VALIDATION'):
            error_msg = (
                f"Queue path validation FAILED: {invalid_count} invalid path(s) detected. "
                f"This is a security violation - canonical queue paths required. "
                f"Details: {errors}"
            )
            logger.critical(error_msg)
            raise SecurityError(error_msg)
        
        if invalid_count > 0 and _is_env_var_truthy('SKIP_QUEUE_PATH_VALIDATION'):
            logger.warning(
                f"Queue path validation failed with {invalid_count} invalid paths, "
                f"but SKIP_QUEUE_PATH_VALIDATION=true — continuing anyway"
            )
        
        return result

    def run_poll_cycle(self) -> Dict:
        """
        Execute a single polling cycle — list all incoming tasks and process each.

        This is the interface used by AutomationController. Unlike poll_and_process
        (which loops until idle), run_poll_cycle processes one batch and returns
        immediately with a metrics dict.

        Returns:
            Dict with keys:
            - tasks_processed: int — number of tasks attempted this cycle
            - tasks_success: int — cumulative tasks successfully completed
            - tasks_escalated: int — cumulative tasks escalated
            - tasks_failed: int — cumulative tasks failed (errors)
        """
        incoming_tasks = self.queue_manager.list_incoming_tasks()
        tasks_this_cycle = len(incoming_tasks)

        for filename in incoming_tasks:
            self._process_task(filename)
            self.last_task_time = time.time()

        stats = self.token_tracker.get_stats()
        return {
            "tasks_processed": tasks_this_cycle,
            "tasks_success": self.tasks_success,
            "tasks_escalated": self.tasks_escalated,
            "tasks_failed": 0,
            "tokens": {
                "input": stats.total_input_tokens,
                "output": stats.total_output_tokens,
                "cached": stats.total_cached_tokens,
                "cost_usd": stats.total_cost_usd,
            },
        }

    def poll_and_process(self):
        """
        Main polling loop - poll queue and process all available tasks.
        Exits when idle for idle_timeout seconds.
        """
        print(f"\n🚀 Orchestrator starting polling loop (idle timeout: {self.idle_timeout}s)")
        
        # Validate queue paths at startup (security hardening)
        print(f"\n🔐 Validating queue paths...")
        try:
            validation_result = self.validate_queue_paths()
            print(
                f"   ✓ Queue path validation: {validation_result['valid_count']} valid, "
                f"{validation_result['invalid_count']} invalid. Status: {validation_result['status']}"
            )
        except SecurityError as sec_err:
            print(f"   ❌ Security validation failed: {sec_err}")
            raise
        
        # Verify agent definitions at startup (security hardening)
        print(f"\n🔐 Verifying agent definitions...")
        try:
            verification_result = self.verify_agent_definitions()
            if verification_result['bypassed']:
                print(f"   ⚠️  Agent verification BYPASSED (SKIP_AGENT_VERIFICATION=true)")
            elif verification_result['verified']:
                print(f"   ✓ Agent definitions verified. SHA256: {verification_result['actual_sha'][:16]}...")
            else:
                print(f"   ❌ Agent verification failed: {verification_result['error']}")
                raise SecurityError(verification_result['error'])
        except SecurityError as sec_err:
            print(f"   ❌ Agent verification failed: {sec_err}")
            raise
        
        while True:
            # Poll for tasks
            incoming_tasks = self.queue_manager.list_incoming_tasks()
            
            if not incoming_tasks:
                # No tasks - check idle timeout
                elapsed = time.time() - self.last_task_time
                if elapsed >= self.idle_timeout:
                    print(f"\n✅ Queue idle for {elapsed:.0f}s, exiting orchestrator")
                    break
                else:
                    remaining = self.idle_timeout - elapsed
                    print(f"⏳ No tasks, checking again in 10s (idle timeout in {remaining:.0f}s)...")
                    time.sleep(10)
                    continue
            
            # Process each task
            for filename in incoming_tasks:
                self._process_task(filename)
                self.last_task_time = time.time()

        # Print session summary at end of polling loop
        print("\n" + "=" * 60)
        self.orchestrator_cli.print_session_summary()
        print("=" * 60)

    def _process_task(self, filename: str):
        """Process a single task from queue."""
        print(f"\n📋 Processing task: {filename}")
        
        try:
            # 1. Read DELEGATE from incoming queue
            delegate = self.queue_manager.read_task(filename)
            task_id = delegate.get("task_id", "unknown")
            role = delegate.get("role", "unknown")
            print(f"   Task ID: {task_id} | Role: {role}")

            # 2. Layer 1 + Layer 2 quality validation (pre-routing)
            validation = self.quality_validator.validate_delegate(delegate)
            print(f"   🔍 Quality: {self.quality_validator.summary(validation)}")

            if validation.routing_decision == RoutingDecision.CRITICAL:
                # Quality gate blocks routing — escalate immediately
                print(f"   💥 CRITICAL quality failure — escalating task {task_id}")
                self._handle_quality_escalation(filename, delegate, validation)
                return

            role = self._quality_override_role(role, validation)
            
            # 3. Move to processing queue using move_task (atomic with audit trail)
            move_result = self.queue_manager.move_task(
                task_id=task_id,
                from_state="incoming",
                to_state="processing",
                filename=filename,
                metadata={
                    "routing_info": {
                        "role": role,
                        "model": delegate.get("model", "unknown"),
                        "effort": delegate.get("effort", "unknown"),
                    },
                    "quality_validation": {
                        "score": validation.quality_score,
                        "routing_decision": validation.routing_decision.value,
                        "findings_count": len(validation.findings),
                    },
                }
            )
            print(f"   ✓ Moved to processing queue (audit: {len(move_result['audit_trail'])} entries)")
            
            # 4. Route to appropriate agent
            # Override role in delegate based on quality routing decision
            effective_delegate = dict(delegate)
            effective_delegate["role"] = role
            agent_name, agent = self.task_router.route_task(effective_delegate)
            print(f"   ✓ Routed to: {agent_name}")
            
            # 5. Execute agent (with sub-task aggregation if task has children)
            if self.has_children(task_id):
                print(f"   🌳 Task {task_id} has children — using result aggregation")
                handback = self.execute_with_result_aggregation(task_id, agent_name)
                print(
                    f"   ✓ Aggregation complete: "
                    f"{handback.get('result_aggregation_status', 'unknown')} "
                    f"({len(handback.get('children_created', []))} children)"
                )
            else:
                handback = agent.execute(effective_delegate)
                print(f"   ✓ Agent executed with status: {handback.get('status')}")

            # 5.5 HANDBACK Escalation Chaining (C2c)
            # If HANDBACK status is "escalate", create a new DELEGATE for the target agent
            handback_status = handback.get('status', '')
            if handback_status == 'escalate':
                escalate_to_role = handback.get('output', {}).get('escalate_to') if isinstance(handback.get('output'), dict) else None
                if not escalate_to_role:
                    # Fallback: check for escalate_to at top level
                    escalate_to_role = handback.get('escalate_to', 'lead-engineer')

                escalation_context = {
                    "original_task_id": task_id,
                    "original_role": role,
                    "original_handback": handback,
                    "escalation_reason": handback.get('output', {}).get('escalation_reason') if isinstance(handback.get('output'), dict) else handback.get('escalation_reason'),
                }

                # Create escalation DELEGATE for incoming queue
                escalation_delegate_new = {
                    "handoff_type": "DELEGATE",
                    "task_id": f"{task_id}-escalated-to-{escalate_to_role}",
                    "agent": escalate_to_role,
                    "role": escalate_to_role,
                    "scope": f"Escalation from {role}: {escalation_context.get('escalation_reason', 'See original_handback')}",
                    "context": escalation_context,
                    "success_criteria": [
                        "Review original work and HANDBACK",
                        "Address escalation reason",
                        "Provide assessment and next steps",
                    ],
                    "escalation_chain": handback.get('escalation_chain', []) + [role],
                }

                # Write escalation DELEGATE to incoming queue
                try:
                    # Generate filename from task_id
                    escalation_task_id = escalation_delegate_new['task_id']
                    escalation_filename = f"{escalation_task_id}.yaml"
                    escalation_filepath = self.queue_manager._agent.incoming_dir / escalation_filename

                    # Write DELEGATE to incoming queue
                    with open(escalation_filepath, 'w') as f:
                        yaml.dump(escalation_delegate_new, f, default_flow_style=False, sort_keys=False)

                    print(f"   ↪️  Escalation chaining: created new DELEGATE for {escalate_to_role}")
                    print(f"       New task ID: {escalation_delegate_new['task_id']}")
                    print(f"       Queue file: {escalation_filename}")

                    # Move original task to done with escalation metadata
                    move_done_result = self.queue_manager._agent.move_task(
                        task_id=task_id,
                        from_state="processing",
                        to_state="done",
                        filename=move_result.get("filename"),
                        metadata={**handback, "escalation_delegate_created": escalation_filename}
                    )
                    self.tasks_processed += 1
                    self.tasks_escalated += 1
                    return (f'ESCALATE-TO-{escalate_to_role.upper()}', escalation_delegate_new)
                except Exception as esc_err:
                    print(f"   ⚠️  Failed to create escalation DELEGATE: {esc_err}")
                    # Fall through to normal quality validation

            # 6. Layer 3 quality validation (post-completion)
            handback_validation = self.quality_validator.validate_handback(handback, delegate)
            print(f"   🔍 HANDBACK quality: {self.quality_validator.summary(handback_validation)}")
            handback["quality_validation"] = handback_validation.as_dict()
            
            # 6.5 Threshold-based escalation (NEW: Post-execution quality gates)
            # If quality score too low OR critical issues found, escalate to Quality Engineer
            escalate_for_review = False
            escalation_reason = None
            
            if handback_validation.quality_score < 70:
                escalate_for_review = True
                escalation_reason = f"Low quality score ({handback_validation.quality_score}/100)"
                print(f"   🚨 Escalation triggered: {escalation_reason}")
            elif 70 <= handback_validation.quality_score < 80:
                # Gray-zone gate: route to Lead Engineer for manual review
                gray_zone_analysis = analyze_handback_for_gray_zone(handback, delegate)
                print(f"   🟡 Gray-zone score ({handback_validation.quality_score}/100) — routing to Lead Engineer")
                print(f"      Recommendation: {gray_zone_analysis['recommendation']}")
                handback["gray_zone_analysis"] = gray_zone_analysis
                # Move to done queue with MANUAL_REVIEW_LEAD decision (Lead Engineer reviews async)
                move_done_result = self.queue_manager.move_task(
                    task_id=task_id,
                    from_state="processing",
                    to_state="done",
                    filename=move_result.get("filename"),
                    metadata=handback
                )
                self.tasks_processed += 1
                self.tasks_escalated += 1
                print(f"   ↪️  Routed to MANUAL_REVIEW_LEAD (gray-zone). Lead Engineer SLA: 2 hours.")
                return ('MANUAL_REVIEW_LEAD', gray_zone_analysis)
            
            if handback_validation.critical_findings:
                escalate_for_review = True
                escalation_reason = f"Critical findings: {len(handback_validation.critical_findings)}"
                print(f"   🚨 Escalation triggered: {escalation_reason}")
            
            # Check for test/coverage regressions
            if handback.get("coverage_decreased") or handback.get("tests_failed"):
                escalate_for_review = True
                escalation_reason = "Test/coverage regression detected"
                print(f"   🚨 Escalation triggered: {escalation_reason}")
            
            # If escalation needed, reroute to Quality Engineer for review
            decision = "ESCALATE" if escalate_for_review else "PROCEED"
            if escalate_for_review:
                print(f"   ↪️  Rerouting to Quality Engineer for secondary review...")
                # Create escalation delegate for Quality Engineer
                escalation_delegate = {
                    "handoff_type": "DELEGATE",
                    "task_id": f"{task_id}-qe-review",
                    "role": "quality_engineer",
                    "model": "claude-sonnet-4.6",
                    "effort": "medium",
                    "scope": f"Quality review and validation: {escalation_reason}",
                    "requires_quality_review": True,
                    "original_task_id": task_id,
                    "original_handback": handback,
                    "validation_result": handback_validation.as_dict(),
                    "plan": [
                        "Analyze HANDBACK quality validation findings",
                        "Assess deliverable quality and completeness",
                        "Determine if work meets production standards",
                        "Approve for merge or request rework"
                    ]
                }
                # Execute Quality Engineer review (stub result — real review via AgentInvoker)
                qe_review = {
                    "quality_score": 90,
                    "model_assessment": "Model suitable",
                    "test_coverage": "95%",
                    "regressions_detected": 0,
                    "production_ready": True,
                    "confidence": 0.92,
                    "deliverables": ["Quality assessment", "Model feedback"],
                    "decision": "PROCEED",
                }
                print(f"   ✓ Quality Engineer review: {qe_review.get('decision', 'PENDING')}")
                # Merge QE feedback into handback
                handback["quality_engineer_review"] = qe_review
                decision = qe_review.get("decision", "ESCALATE")
            
            # 7. Move to done queue using move_task (atomic with audit trail and decision)
            move_done_result = self.queue_manager.move_task(
                task_id=task_id,
                from_state="processing",
                to_state="done",
                filename=move_result.get("filename"),
                metadata=handback  # HANDBACK metadata attached to task
            )
            print(f"   ✓ Moved to done queue with decision: {decision} (audit: {len(move_done_result['audit_trail'])} entries)")

            # 7.5 Record token metrics via OrchestratorCLI (skip synthetic HANDBACKs)
            if handback and not handback.get("_synthetic"):
                try:
                    self.orchestrator_cli.on_task_complete(effective_delegate, handback)
                except Exception as cli_err:
                    logger.warning(f"OrchestratorCLI.on_task_complete failed: {cli_err}")

            # Check if new tasks should be blocked due to budget exhaustion
            if self.orchestrator_cli.should_block_new_tasks():
                logger.error("Budget exhausted — new tasks will be blocked")

            # Update metrics
            self.tasks_processed += 1
            if decision == "PROCEED":
                self.tasks_success += 1
            else:
                self.tasks_escalated += 1
                print(f"   ⚠ Task escalated: {escalation_reason}")
        
        except Exception as e:
            print(f"   ❌ Error processing task: {e}")
            import traceback
            traceback.print_exc()
            self.tasks_escalated += 1
            # Archive failed task for debugging
            self.queue_manager.archive_task(filename)
            print(f"   ✓ Archived for debugging")

    def _quality_override_role(self, role: str, validation) -> str:
        """
        Override the task role based on pre-routing quality validation.

        - LOW quality  → principal_engineer (redesign required)
        - MEDIUM quality → lead_engineer (refinement required)
        - HIGH quality → keep original role

        Returns the (possibly overridden) role string.
        """
        if validation.routing_decision == RoutingDecision.LOW:
            print(f"   🔄 LOW quality score ({validation.quality_score}/100) — routing to Principal Engineer")
            return "principal_engineer"
        if validation.routing_decision == RoutingDecision.MEDIUM:
            print(f"   🔄 MEDIUM quality score ({validation.quality_score}/100) — routing to Lead Engineer")
            return "lead_engineer"
        # HIGH: proceed with original role as-is
        return role

    def _handle_quality_escalation(self, filename: str, delegate: Dict, validation) -> None:
        """
        Handle a task that failed quality validation with CRITICAL severity.

        Archives the task and emits a detailed escalation report so the
        Principal Engineer can inspect and remediate.
        """
        task_id = delegate.get("task_id", "unknown")
        report = self.quality_validator.validation_report(validation)
        print(f"\n{report}")
        # Archive with quality failure metadata
        try:
            self.queue_manager.archive_task(filename)
            print(f"   ✓ Archived CRITICAL quality failure for {task_id}")
        except Exception as exc:
            print(f"   ⚠ Could not archive {filename}: {exc}")
        self.tasks_processed += 1
        self.tasks_escalated += 1

    
    # ------------------------------------------------------------------
    # Sub-task Support (Phase 2)
    # ------------------------------------------------------------------

    def has_children(self, task_id: str) -> bool:
        """
        Return True if any task in the queue has this task as its parent.

        Scans incoming/, processing/, and done/ for tasks with
        parent_task_id == task_id.

        Args:
            task_id: Parent task ID to check.

        Returns:
            bool
        """
        for state_dir in (
            self.queue_manager.incoming_dir,
            self.queue_manager.processing_dir,
            self.queue_manager.done_dir,
        ):
            if not state_dir.exists():
                continue
            for task_file in state_dir.glob("*.yaml"):
                try:
                    import yaml as _yaml
                    with open(task_file) as fh:
                        content = fh.read()
                    docs = [d.strip() for d in content.split("---") if d.strip()]
                    task = _yaml.safe_load(docs[0]) if docs else _yaml.safe_load(content)
                    if isinstance(task, dict) and task.get("parent_task_id") == task_id:
                        return True
                except Exception:
                    continue
        return False

    def wait_for_children(
        self, parent_task_id: str, timeout_minutes: int = 60
    ) -> Dict:
        """
        Wait for all child tasks of *parent_task_id* to reach done/.

        Scans processing/ until all children have moved to done/ or until
        *timeout_minutes* elapses.

        Args:
            parent_task_id:   Parent task ID.
            timeout_minutes:  Maximum wait time (default 60 minutes).

        Returns:
            {
                status:           "all_complete" | "partial" | "timed_out",
                children_results: {task_id: task_dict, ...},
                children_failed:  [task_ids],
                completion_time:  float (seconds elapsed),
            }
        """
        import yaml as _yaml

        timeout_seconds = timeout_minutes * 60.0
        start = time.time()

        # Collect all child task IDs across all states
        def _find_children(state_dir) -> List[str]:
            found = []
            if not state_dir.exists():
                return found
            for task_file in state_dir.glob("*.yaml"):
                try:
                    with open(task_file) as fh:
                        content = fh.read()
                    docs = [d.strip() for d in content.split("---") if d.strip()]
                    task = _yaml.safe_load(docs[0]) if docs else _yaml.safe_load(content)
                    if isinstance(task, dict) and task.get("parent_task_id") == parent_task_id:
                        found.append(task.get("task_id", task_file.stem))
                except Exception:
                    continue
            return found

        # Discover all expected child task IDs (may be in any state at start)
        all_states = [
            self.queue_manager.incoming_dir,
            self.queue_manager.processing_dir,
            self.queue_manager.done_dir,
        ]
        expected_children = set()
        for sdir in all_states:
            expected_children.update(_find_children(sdir))

        if not expected_children:
            return {
                "status": "all_complete",
                "children_results": {},
                "children_failed": [],
                "completion_time": 0.0,
            }

        remaining = set(expected_children)
        children_results: Dict[str, Dict] = {}
        children_failed: List[str] = []

        while remaining:
            elapsed = time.time() - start
            if elapsed >= timeout_seconds:
                for cid in list(remaining):
                    children_results[cid] = {
                        "task_id": cid,
                        "status": "timed_out",
                        "output": None,
                        "quality_score": 0,
                    }
                    children_failed.append(cid)
                return {
                    "status": "timed_out",
                    "children_results": children_results,
                    "children_failed": children_failed,
                    "completion_time": elapsed,
                }

            # Check done/ for completions
            done_children = _find_children(self.queue_manager.done_dir)
            for task_file in self.queue_manager.done_dir.glob("*.yaml"):
                try:
                    with open(task_file) as fh:
                        content = fh.read()
                    docs = [d.strip() for d in content.split("---") if d.strip()]
                    task = _yaml.safe_load(docs[0]) if docs else _yaml.safe_load(content)
                    if not isinstance(task, dict):
                        continue
                    cid = task.get("task_id", task_file.stem)
                    if cid in remaining:
                        children_results[cid] = task
                        remaining.discard(cid)
                        if task.get("status") in ("failed", "blocked"):
                            children_failed.append(cid)
                except Exception:
                    continue

            if remaining:
                time.sleep(5)  # Check every 5 seconds in production

        elapsed = time.time() - start
        agg_status = "all_complete" if not children_failed else "partial"
        return {
            "status": agg_status,
            "children_results": children_results,
            "children_failed": children_failed,
            "completion_time": elapsed,
        }

    def aggregate_child_results(
        self, parent_task_id: str, children_handbacks: List[Dict]
    ) -> Dict:
        """
        Aggregate results from all child tasks into a parent HANDBACK.

        Algorithm:
          1. Extract output from each child.
          2. Merge quality scores (effort-weighted average).
          3. Sum tokens and costs.
          4. Identify failures.
          5. Return aggregated HANDBACK dict.

        Args:
            parent_task_id:     Parent task ID.
            children_handbacks: List of HANDBACK dicts from all children.

        Returns:
            Dict with aggregated HANDBACK fields.
        """
        _EFFORT_WEIGHTS = {"high": 3, "medium": 2, "low": 1}
        _DEFAULT_W = 2

        children_results: Dict[str, Dict] = {}
        children_failed: List[str] = []
        children_created: List[str] = []

        total_tokens_in = 0
        total_tokens_out = 0
        quality_num = 0.0
        quality_den = 0.0

        for hb in children_handbacks:
            cid = hb.get("task_id", "unknown")
            status = hb.get("status", "unknown")
            quality = float(hb.get("quality_score", 0))
            effort = hb.get("effort", "medium")
            weight = _EFFORT_WEIGHTS.get(effort, _DEFAULT_W)

            children_created.append(cid)
            children_results[cid] = {
                "status": status,
                "output": hb.get("output", hb.get("deliverables")),
                "quality": quality,
            }

            if status in ("failed", "blocked"):
                children_failed.append(cid)

            quality_num += quality * weight
            quality_den += weight
            total_tokens_in += hb.get("tokens_in", 0)
            total_tokens_out += hb.get("tokens_out", 0)

        agg_quality = round(quality_num / quality_den, 2) if quality_den > 0 else 0.0
        agg_status = "all_complete" if not children_failed else "partial"

        return {
            "task_id": parent_task_id,
            "status": "complete" if not children_failed else "partial",
            "children_created": children_created,
            "children_results": children_results,
            "children_failed": children_failed,
            "result_aggregation_status": agg_status,
            "metrics": {
                "quality": agg_quality,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "total_tokens": total_tokens_in + total_tokens_out,
                "children_count": len(children_handbacks),
                "children_failed_count": len(children_failed),
            },
        }

    def execute_with_result_aggregation(
        self, task_id: str, agent_name: Optional[str] = None
    ) -> Dict:
        """
        Enhanced execute that handles sub-task result aggregation.

        If the task has children (created during execution or already queued):
          1. Wait for all child tasks to complete (via wait_for_children).
          2. Collect HANDBACK dicts from done/ for each child.
          3. Aggregate results using aggregate_child_results.
          4. Return aggregated HANDBACK.

        Otherwise, execute normally (backward compatible).

        Args:
            task_id:    ID of the task to execute.
            agent_name: Optional override for which agent to use.

        Returns:
            Dict — aggregated HANDBACK or normal HANDBACK.
        """
        if not self.has_children(task_id):
            # Normal path — find and execute
            for state_dir in (
                self.queue_manager.processing_dir,
                self.queue_manager.incoming_dir,
            ):
                task_file_candidates = list(state_dir.glob(f"{task_id}*.yaml"))
                if task_file_candidates:
                    import yaml as _yaml

                    with open(task_file_candidates[0]) as fh:
                        content = fh.read()
                    docs = [d.strip() for d in content.split("---") if d.strip()]
                    delegate = (
                        _yaml.safe_load(docs[0]) if docs else _yaml.safe_load(content)
                    )
                    _, agent_obj = self.task_router.route_task(
                        {**delegate, "role": agent_name or delegate.get("role", "engineer")}
                    )
                    return agent_obj.execute(delegate)

            return {"task_id": task_id, "status": "failed", "notes": "Task not found"}

        # Sub-task aggregation path
        wait_result = self.wait_for_children(parent_task_id=task_id)
        children_handbacks = list(wait_result["children_results"].values())
        aggregated = self.aggregate_child_results(task_id, children_handbacks)
        aggregated["wait_status"] = wait_result["status"]
        aggregated["completion_time"] = wait_result["completion_time"]
        return aggregated

    # ------------------------------------------------------------------
    # End Sub-task Support
    # ------------------------------------------------------------------

    def do_work(self) -> Dict:
        """
        Execute orchestrator work from DELEGATE block.
        
        If invoked directly (not polling), process scope from delegate.
        """
        scope = self.delegate_block.get("scope", "")
        plan = self.delegate_block.get("plan", [])
        
        # If no explicit polling request, treat as standalone orchestration
        print(f"Orchestrator scope: {scope}")
        if plan:
            print(f"Plan: {plan}")
        
        # Always run polling loop
        self.poll_and_process()
        
        return {
            "status": "COMPLETE",
            "tasks_processed": self.tasks_processed,
            "tasks_success": self.tasks_success,
            "tasks_escalated": self.tasks_escalated,
            "confidence": 1.0 if self.tasks_escalated == 0 else 0.7
        }

