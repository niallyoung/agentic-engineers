"""
Orchestrator Agent - Continuous Queue Polling & Task Routing

Implements the canonical ORCHESTRATOR-FIRST EXECUTION MODEL:
1. Poll ~/.copilot/queue/incoming/ for new DELEGATE blocks
2. Route each task to appropriate agent per AGENTS.md
3. Process HANDBACK results
4. Move tasks through queue states: incoming → processing → done
5. Continue polling until queue is idle (60+ seconds with no tasks)

This is the ONLY way work flows through agentic-engineers.
"""

import os
import logging
import yaml
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from . import (
    Agent, ORCHESTRATOR_CONFIG, ENGINEER_CONFIG, SENIOR_ENGINEER_CONFIG,
    LEAD_ENGINEER_CONFIG, PRINCIPAL_ENGINEER_CONFIG, QUALITY_ENGINEER_CONFIG,
    MODEL_ENGINEER_CONFIG, SECURITY_ENGINEER_CONFIG
)
from .implementations import (
    GeneralOrchestrator, EngineerAgent, SeniorEngineerAgent,
    LeadEngineerAgent, PrincipalEngineerAgent, QualityEngineerAgent,
    ModelEngineerAgent, SecurityEngineerAgent
)
from .quality_validator import QualityValidator, RoutingDecision
from .delegate_validator import validate_delegate_pre_flight
from .metrics_writer import MetricsWriter
from .gray_zone_reviewer import analyze_handback_for_gray_zone
from ..monitoring.metrics import MetricsRegistry
from ..monitoring.token_tracker import TokenTracker
from ..monitoring.orchestrator_cli import OrchestratorCLI
from ..monitoring.budget_checker import BudgetStatus, BudgetResult

logger = logging.getLogger(__name__)

# Protocol constants
MAX_RETRIES = 2  # Maximum number of retries before escalation to Principal Engineer
TASK_STATE_KEYS = {'retry_count', 'quality_score', 'last_failure_reasons', 'retry_context'}


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
        # Detect session-id early
        try:
            self.session_id = self.detect_session_id()
        except RuntimeError as e:
            print(f"   ⚠️  Warning: {e}. Falling back to generic session handling.")
            # Fallback: use a placeholder for testing/migration purposes
            self.session_id = "default"
        
        # Use explicit queue_dir, or auto-detect based on agent context
        if queue_dir:
            base_queue_dir = Path(queue_dir).expanduser()
            self.agent_context = agent_context or self.detect_agent_context()
        else:
            # Auto-detect agent context
            self.agent_context = agent_context or self.detect_agent_context()
            
            # Build queue path based on context
            if self.agent_context == 'claude':
                claude_queue = Path("~/.claude/queue").expanduser()
                repo_queue = Path("artifacts/queue")
                if claude_queue.exists():
                    base_queue_dir = claude_queue
                elif repo_queue.exists():
                    base_queue_dir = repo_queue
                else:
                    base_queue_dir = claude_queue
            else:  # copilot
                copilot_queue = Path("~/.copilot/queue").expanduser()
                repo_queue = Path("artifacts/queue")
                if copilot_queue.exists():
                    base_queue_dir = copilot_queue
                elif repo_queue.exists():
                    base_queue_dir = repo_queue
                else:
                    base_queue_dir = copilot_queue
        
        # Store the base queue directory (for migrations)
        self.base_dir = base_queue_dir
        
        # Now set the session-id partitioned queue directory BEFORE migration
        self.session_queue_dir = self.base_dir / self.session_id
        self.incoming_dir = self.session_queue_dir / "incoming"
        self.processing_dir = self.session_queue_dir / "processing"
        self.done_dir = self.session_queue_dir / "done"
        
        # Migrate legacy queue structure if needed
        self.migrate_legacy_queue()
        
        # Ensure queue structure exists after migration
        self._ensure_queue_structure()
        print(f"   Queue Manager initialized: {self.session_queue_dir} (session_id={self.session_id}, agent_context={self.agent_context})")
    
    
    def _ensure_queue_structure(self):
        """Ensure all queue directories exist."""
        for dir_path in [self.incoming_dir, self.processing_dir, self.done_dir]:
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
        done_filename = f"{task_id}-{status}.yaml"
        done_path = self.done_dir / done_filename
        
        # Write HANDBACK to done directory
        with open(done_path, 'w') as f:
            yaml.dump(handback, f, default_flow_style=False, sort_keys=False)
        
        # Remove from processing
        if processing_path.exists():
            processing_path.unlink()
        
        return str(done_path)
    
    def archive_task(self, filename: str) -> str:
        """Archive failed task (for debugging)."""
        incoming_path = self.incoming_dir / filename
        archive_dir = self.base_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        archive_path = archive_dir / f"{datetime.now().isoformat()}_{filename}"
        shutil.move(str(incoming_path), str(archive_path))
        return str(archive_path)
    
    def move_task(
        self,
        task_id: str,
        from_state: str,
        to_state: str,
        metadata: Optional[Dict] = None
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
            "processing": ["done"],
            "done": []
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
            else:
                raise ValueError(f"Unknown from_state: {from_state}")
            
            # Get destination directory
            if to_state == "incoming":
                to_dir = self.incoming_dir
            elif to_state == "processing":
                to_dir = self.processing_dir
            elif to_state == "done":
                to_dir = self.done_dir
            else:
                raise ValueError(f"Unknown to_state: {to_state}")
            
            # Find task file containing task_id
            task_filename = None
            from_state_tasks = sorted([f.name for f in from_dir.glob("*.yaml")])
            for task_file in from_state_tasks:
                if task_id in task_file:
                    task_filename = task_file
                    break
            
            if not task_filename:
                raise FileNotFoundError(f"Task '{task_id}' not found in '{from_state}' state")
            
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
                to_filename = f"{task_id}-{decision}.yaml"
            else:
                # For processing, keep same filename
                to_filename = task_filename
            
            # Atomic write to destination (write to temp file first, then move)
            to_path = to_dir / to_filename
            temp_path = to_dir / f".tmp_{to_filename}"
            
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
    """Route tasks to appropriate agents based on AGENTS.md decision tree."""
    
    # Agent routing map
    AGENT_CLASSES = {
        "orchestrator": GeneralOrchestrator,
        "engineer": EngineerAgent,
        "senior_engineer": SeniorEngineerAgent,
        "lead_engineer": LeadEngineerAgent,
        "principal_engineer": PrincipalEngineerAgent,
        "quality_engineer": QualityEngineerAgent,
        "model_engineer": ModelEngineerAgent,
        "security_engineer": SecurityEngineerAgent,
    }
    
    def route_task(self, delegate: Dict) -> Tuple[str, Agent]:
        """
        Route task to appropriate agent.
        
        Returns:
            (agent_name, agent_instance)
        """
        # Priority 1: Explicit role in DELEGATE
        if "role" in delegate:
            role = delegate.get("role", "").lower()
            if role in self.AGENT_CLASSES:
                agent_class = self.AGENT_CLASSES[role]
                return (role, agent_class())
        
        # Priority 2: Apply AGENTS.md decision tree
        scope = delegate.get("scope", "").lower()
        complexity = delegate.get("complexity", "medium").lower()
        has_plan = delegate.get("plan", False) is not None
        is_security = delegate.get("is_security_scoped", False)
        
        if is_security:
            agent_class = self.AGENT_CLASSES["security_engineer"]
            return ("security_engineer", agent_class())
        
        if "cross" in scope or "architecture" in scope:
            agent_class = self.AGENT_CLASSES["principal_engineer"]
            return ("principal_engineer", agent_class())
        
        if complexity == "high" and not has_plan:
            agent_class = self.AGENT_CLASSES["senior_engineer"]
            return ("senior_engineer", agent_class())
        
        # Code review and validation tasks route to Quality Engineer (post-implementation review)
        if delegate.get("is_code_review", False) or delegate.get("requires_quality_review", False):
            agent_class = self.AGENT_CLASSES["quality_engineer"]
            return ("quality_engineer", agent_class())
        
        # Architecture guidance and refinement route to Lead Engineer
        if "review" in scope and "architecture" in scope.lower():
            agent_class = self.AGENT_CLASSES["lead_engineer"]
            return ("lead_engineer", agent_class())
        
        if has_plan and complexity in ("low", "medium"):
            agent_class = self.AGENT_CLASSES["engineer"]
            return ("engineer", agent_class())
        
        # Default to engineer for well-scoped tasks
        agent_class = self.AGENT_CLASSES["engineer"]
        return ("engineer", agent_class())


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
        self.queue_manager = QueueManager(queue_dir, agent_context)
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
                    "model": "claude-sonnet-4-6",
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
                # Execute Quality Engineer review
                qe_agent_class = self.task_router.AGENT_CLASSES["quality_engineer"]
                qe_agent = qe_agent_class()
                qe_review = qe_agent.execute(escalation_delegate)
                print(f"   ✓ Quality Engineer review: {qe_review.get('decision', 'PENDING')}")
                # Merge QE feedback into handback
                handback["quality_engineer_review"] = qe_review
                decision = qe_review.get("decision", "ESCALATE")
            
            # 7. Move to done queue using move_task (atomic with audit trail and decision)
            move_done_result = self.queue_manager.move_task(
                task_id=task_id,
                from_state="processing",
                to_state="done",
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

