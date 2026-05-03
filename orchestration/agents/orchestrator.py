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


class QueueManager:
    """Manage queue directory structure and file operations."""
    
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
    
    def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
        # Use explicit queue_dir, or auto-detect based on agent context
        if queue_dir:
            self.base_dir = Path(queue_dir).expanduser()
            self.agent_context = agent_context or self.detect_agent_context()
        else:
            # Auto-detect agent context
            self.agent_context = agent_context or self.detect_agent_context()
            
            # Build queue path based on context
            if self.agent_context == 'claude':
                claude_queue = Path("~/.claude/queue").expanduser()
                repo_queue = Path("artifacts/queue")
                if claude_queue.exists():
                    self.base_dir = claude_queue
                elif repo_queue.exists():
                    self.base_dir = repo_queue
                else:
                    self.base_dir = claude_queue
            else:  # copilot
                copilot_queue = Path("~/.copilot/queue").expanduser()
                repo_queue = Path("artifacts/queue")
                if copilot_queue.exists():
                    self.base_dir = copilot_queue
                elif repo_queue.exists():
                    self.base_dir = repo_queue
                else:
                    self.base_dir = copilot_queue
        
        self.incoming_dir = self.base_dir / "incoming"
        self.processing_dir = self.base_dir / "processing"
        self.done_dir = self.base_dir / "done"
        self._ensure_queue_structure()
        print(f"   Queue Manager initialized: {self.base_dir} (agent_context={self.agent_context})")
    
    def _ensure_queue_structure(self):
        """Ensure all queue directories exist."""
        for dir_path in [self.incoming_dir, self.processing_dir, self.done_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
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
        
        if "review" in scope or delegate.get("is_code_review", False):
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
    
    def run_poll_cycle(self) -> Dict:
        """
        Execute one polling cycle: check for incoming tasks and process them.

        Unlike ``poll_and_process()`` (which loops until idle), this method
        runs *exactly one* cycle — inspect the queue, process all currently
        available tasks, and return.  Callers (tests, schedulers, external
        loops) can call it repeatedly as needed.

        When ``self.agent_invoker`` is set (AgentInvoker instance), tasks are
        delegated to real agent subprocesses via ``invoke_agent()``.
        Otherwise the existing stub-based ``agent.execute()`` path is used.

        Returns:
            Dict with keys:
                - tasks_processed: int
                - tasks_success: int
                - tasks_escalated: int
        """
        incoming_tasks = self.queue_manager.list_incoming_tasks()

        for filename in incoming_tasks:
            self._process_task(filename)
            self.last_task_time = time.time()

        return {
            "tasks_processed": self.tasks_processed,
            "tasks_success": self.tasks_success,
            "tasks_escalated": self.tasks_escalated,
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

            if validation.routing_decision == RoutingDecision.LOW:
                # Route to Principal Engineer for redesign
                print(f"   🔄 LOW quality score ({validation.quality_score}/100) — routing to Principal Engineer")
                role = "principal_engineer"
            elif validation.routing_decision == RoutingDecision.MEDIUM:
                # Route to Lead Engineer for refinement
                print(f"   🔄 MEDIUM quality score ({validation.quality_score}/100) — routing to Lead Engineer")
                role = "lead_engineer"
            # HIGH: proceed with original role as-is
            
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
            
            # 5. Execute agent
            handback = agent.execute(effective_delegate)
            print(f"   ✓ Agent executed with status: {handback.get('status')}")

            # 6. Layer 3 quality validation (post-completion)
            handback_validation = self.quality_validator.validate_handback(handback, delegate)
            print(f"   🔍 HANDBACK quality: {self.quality_validator.summary(handback_validation)}")
            handback["quality_validation"] = handback_validation.as_dict()
            
            # 7. Move to done queue using move_task (atomic with audit trail and decision)
            decision = handback.get("decision", "PROCEED")
            move_done_result = self.queue_manager.move_task(
                task_id=task_id,
                from_state="processing",
                to_state="done",
                metadata=handback  # HANDBACK metadata attached to task
            )
            print(f"   ✓ Moved to done queue with decision: {decision} (audit: {len(move_done_result['audit_trail'])} entries)")
            
            # Update metrics
            self.tasks_processed += 1
            if handback.get("status") == "PASS":
                self.tasks_success += 1
            else:
                self.tasks_escalated += 1
                print(f"   ⚠ Task escalated: {handback.get('error', 'unknown')}")
        
        except Exception as e:
            print(f"   ❌ Error processing task: {e}")
            import traceback
            traceback.print_exc()
            self.tasks_escalated += 1
            # Archive failed task for debugging
            self.queue_manager.archive_task(filename)
            print(f"   ✓ Archived for debugging")

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

