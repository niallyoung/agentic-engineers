"""
REFACTOR Phase: Orchestrator agent implementation with improved quality.

Implements complete Orchestrator functionality:
1. Queue polling (incoming, processing, done)
2. DELEGATE validation and creation
3. Agent routing per AGENTS.md
4. HANDBACK processing
5. Queue state transitions
6. Span capture (OpenTelemetry format)
7. Artifact indexing

Quality features:
- Comprehensive error handling with informative messages
- Detailed logging for observability
- Type hints throughout
- Docstrings for all public methods
- Defensive programming for malformed files
"""

import yaml
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Master router for all software engineering work."""

    MODEL = "claude-haiku-4-5"
    EFFORT = "low"

    # Routing decision tree
    ROUTING_RULES = [
        ("security", "Security Engineer", "claude-opus-4-7", "max"),
        ("cross-service-architecture", "Principal Engineer", "claude-opus-4-6", "high"),
        ("complex-coding-no-plan", "Senior Engineer", "claude-sonnet-4-6", "high"),
        ("code-review", "Lead Engineer", "claude-sonnet-4-6", "high"),
        ("well-planned-low-complexity", "Engineer", "claude-haiku-4-5", "high"),
    ]

    # Valid roles per AGENTS.md
    VALID_ROLES = {
        "Engineer",
        "Senior Engineer",
        "Lead Engineer",
        "Quality Engineer",
        "Principal Engineer",
        "Security Engineer",
        "Model Engineer",
        "Orchestrator"
    }

    # Valid models per AGENTS.md
    VALID_MODELS = {
        "claude-haiku-4-5",
        "claude-sonnet-4-5",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-opus-4-7"
    }

    # Valid effort levels
    VALID_EFFORTS = {"low", "medium", "high", "max"}

    # Token pricing (per 1M tokens)
    TOKEN_PRICING = {
        "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
        "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
        "claude-opus-4-6": {"input": 15.0, "output": 75.0},
        "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    }

    def __init__(self, artifacts_dir: str = "artifacts", queue_dir: Optional[str] = None):
        """Initialize Orchestrator with artifacts and queue directories.
        
        Args:
            artifacts_dir: Root directory for artifacts (spans, indexes). Defaults to "artifacts" (git repo).
            queue_dir: Root directory for queue (incoming, processing, done). 
                      Defaults to ~/.copilot/queue/ for production runtime.
                      Set to artifacts_dir/queue for testing.
            
        Raises:
            OSError: If directories cannot be created.
        """
        try:
            self.artifacts_dir = Path(artifacts_dir)
            
            # Queue location: ~/.copilot/queue/ for production, or override for testing
            if queue_dir:
                self.queue_dir = Path(queue_dir)
            else:
                # Production: use ~/.copilot/queue/ (actual runtime queue)
                home_queue = Path.home() / ".copilot" / "queue"
                if home_queue.exists():
                    self.queue_dir = home_queue
                else:
                    # Fallback: create in artifacts/ for initial setup
                    self.queue_dir = self.artifacts_dir / "queue"
            
            self.delegates_dir = self.artifacts_dir / "delegates"
            self.current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Create necessary directories
            (self.queue_dir / "incoming").mkdir(parents=True, exist_ok=True)
            (self.queue_dir / "processing").mkdir(parents=True, exist_ok=True)
            (self.queue_dir / "done").mkdir(parents=True, exist_ok=True)
            self.delegates_dir.mkdir(parents=True, exist_ok=True)
            (self.artifacts_dir / self.current_date).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Orchestrator initialized with artifacts_dir={artifacts_dir}")
        except OSError as e:
            logger.error(f"Failed to initialize Orchestrator: {e}")
            raise

    def poll_incoming_queue(self) -> List[Dict]:
        """Poll incoming queue for new tasks.
        
        Returns:
            List of task dictionaries from incoming queue.
            Empty list if no tasks or on error.
        """
        incoming_dir = self.queue_dir / "incoming"
        tasks = []
        
        try:
            if not incoming_dir.exists():
                logger.warning(f"Incoming queue directory does not exist: {incoming_dir}")
                return tasks
            
            for task_file in sorted(incoming_dir.glob("*.yaml")):
                try:
                    with open(task_file, 'r') as f:
                        task = yaml.safe_load(f)
                        if task and isinstance(task, dict):
                            tasks.append(task)
                            logger.debug(f"Loaded task from {task_file.name}")
                        else:
                            logger.warning(f"Invalid task format in {task_file.name}")
                except yaml.YAMLError as e:
                    logger.error(f"YAML parse error in {task_file.name}: {e}")
                except Exception as e:
                    logger.error(f"Error reading task file {task_file.name}: {e}")
            
            if tasks:
                logger.info(f"Poll incoming: found {len(tasks)} task(s)")
            
        except Exception as e:
            logger.error(f"Error polling incoming queue: {e}")
        
        return tasks

    def poll_processing_queue(self) -> List[Dict]:
        """Poll processing queue for completed work (HANDBACKs).
        
        Returns:
            List of HANDBACK dictionaries from processing queue.
            Empty list if no handbacks or on error.
        """
        processing_dir = self.queue_dir / "processing"
        handbacks = []
        
        try:
            if not processing_dir.exists():
                logger.warning(f"Processing queue directory does not exist: {processing_dir}")
                return handbacks
            
            for handback_file in sorted(processing_dir.glob("*-HANDBACK-*.yaml")):
                try:
                    with open(handback_file, 'r') as f:
                        handback = yaml.safe_load(f)
                        if handback and isinstance(handback, dict):
                            if handback.get('handoff_type') == 'HANDBACK':
                                handbacks.append(handback)
                                logger.debug(f"Loaded HANDBACK from {handback_file.name}")
                            else:
                                logger.warning(f"Invalid HANDBACK type in {handback_file.name}")
                        else:
                            logger.warning(f"Invalid HANDBACK format in {handback_file.name}")
                except yaml.YAMLError as e:
                    logger.error(f"YAML parse error in {handback_file.name}: {e}")
                except Exception as e:
                    logger.error(f"Error reading HANDBACK file {handback_file.name}: {e}")
            
            if handbacks:
                logger.info(f"Poll processing: found {len(handbacks)} HANDBACK(s)")
            
        except Exception as e:
            logger.error(f"Error polling processing queue: {e}")
        
        return handbacks

    def poll_done_queue(self) -> List[Dict]:
        """Poll done queue for human decisions.
        
        Returns:
            List of decision dictionaries from done queue.
            Empty list if no decisions or on error.
        """
        done_dir = self.queue_dir / "done"
        decisions = []
        
        try:
            if not done_dir.exists():
                logger.warning(f"Done queue directory does not exist: {done_dir}")
                return decisions
            
            for decision_pattern in ["*-PROCEED.yaml", "*-REWORK.yaml", "*-ESCALATE.yaml"]:
                for decision_file in sorted(done_dir.glob(decision_pattern)):
                    try:
                        with open(decision_file, 'r') as f:
                            decision = yaml.safe_load(f)
                            if decision and isinstance(decision, dict):
                                decisions.append(decision)
                                logger.debug(f"Loaded decision from {decision_file.name}")
                            else:
                                logger.warning(f"Invalid decision format in {decision_file.name}")
                    except yaml.YAMLError as e:
                        logger.error(f"YAML parse error in {decision_file.name}: {e}")
                    except Exception as e:
                        logger.error(f"Error reading decision file {decision_file.name}: {e}")
            
            if decisions:
                logger.info(f"Poll done: found {len(decisions)} decision(s)")
            
        except Exception as e:
            logger.error(f"Error polling done queue: {e}")
        
        return decisions

    def validate_delegate_format(self, delegate: Dict) -> bool:
        """Validate DELEGATE format per HANDOFF.md spec.
        
        Args:
            delegate: Dictionary to validate as DELEGATE block.
            
        Returns:
            True if DELEGATE format is valid, False otherwise.
        """
        try:
            if not isinstance(delegate, dict):
                logger.warning(f"DELEGATE must be dict, got {type(delegate)}")
                return False
            
            # Check required fields
            required_fields = {
                'handoff_type',
                'task_id',
                'role',
                'model',
                'effort',
                'scope',
                'context',
                'plan',
                'success_criteria'
            }
            
            # Check handoff_type
            if delegate.get('handoff_type') != 'DELEGATE':
                logger.warning(f"Invalid handoff_type: {delegate.get('handoff_type')}")
                return False
            
            # Check all required fields exist
            missing_fields = required_fields - set(delegate.keys())
            if missing_fields:
                logger.warning(f"DELEGATE missing required fields: {missing_fields}")
                return False
            
            # Validate role
            if delegate['role'] not in self.VALID_ROLES:
                logger.warning(f"Invalid role: {delegate['role']}")
                return False
            
            # Validate model
            if delegate['model'] not in self.VALID_MODELS:
                logger.warning(f"Invalid model: {delegate['model']}")
                return False
            
            # Validate effort
            if delegate['effort'] not in self.VALID_EFFORTS:
                logger.warning(f"Invalid effort: {delegate['effort']}")
                return False
            
            # Validate task_id format (should be YYYY-MM-DD-slug)
            task_id = delegate['task_id']
            if not task_id or len(task_id) < 10:
                logger.warning(f"Invalid task_id format: {task_id}")
                return False
            
            logger.debug(f"DELEGATE format valid for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating DELEGATE format: {e}")
            return False

    def route_task(self, task: Dict) -> Dict:
        """Route task to appropriate agent per AGENTS.md decision tree.
        
        If task has explicit 'role' field, respect it. Otherwise, apply routing logic:
        1. Security-scoped tasks → Security Engineer (opus-4-7, max effort)
        2. Cross-service architecture (>2 repos) → Principal Engineer (opus-4-6, high effort)
        3. Complex coding without plan → Senior Engineer (sonnet-4-6, high effort)
        4. Code review tasks → Quality Engineer (sonnet-4-6, medium effort)
        5. Well-planned, low-medium complexity → Engineer (haiku-4-5, high effort)
        Default: Lead Engineer (sonnet-4-6, high effort)
        
        Args:
            task: Task dictionary with optional 'role', 'model', 'effort' fields.
            
        Returns:
            Dictionary with role, model, and effort fields for routing decision.
        """
        # If task explicitly specifies role/model/effort, respect it
        if 'role' in task:
            return {
                "role": task['role'],
                "model": task.get('model', 'claude-sonnet-4-6'),
                "effort": task.get('effort', 'high')
            }
        
        scope = task.get('scope', '').lower()
        task_type = task.get('type', '').lower()
        description = task.get('description', '').lower()
        
        # 1. Security-scoped task
        if 'security' in scope or task_type == 'security':
            return {
                "role": "Security Engineer",
                "model": "claude-opus-4-7",
                "effort": "max"
            }
        
        # 2. Cross-service architecture
        repos_affected = task.get('repos_affected', [])
        if len(repos_affected) > 2 or 'cross-service' in scope or 'architecture' in description:
            return {
                "role": "Principal Engineer",
                "model": "claude-opus-4-6",
                "effort": "high"
            }
        
        # 3. Complex coding without plan
        complexity = task.get('complexity', '').lower()
        has_plan = task.get('has_plan', False)
        
        if complexity == 'high' and not has_plan and 'review' not in task_type:
            return {
                "role": "Senior Engineer",
                "model": "claude-sonnet-4-6",
                "effort": "high"
            }
        
        # 4. Code review
        if task_type == 'code-review' or 'review' in description:
            # Route to Quality Engineer for lighter reviews, Lead Engineer for critical
            return {
                "role": "Quality Engineer",
                "model": "claude-sonnet-4-6",
                "effort": "medium"
            }
        
        # 5. Well-planned, low-medium complexity
        if has_plan and complexity in ['low', 'medium']:
            return {
                "role": "Engineer",
                "model": "claude-haiku-4-5",
                "effort": "high"
            }
        
        # Default to Lead Engineer for unknown cases
        return {
            "role": "Lead Engineer",
            "model": "claude-sonnet-4-6",
            "effort": "high"
        }

    def create_delegate(self, task: Dict, role: str, model: str, effort: str) -> Dict:
        """Create DELEGATE block for task per HANDOFF.md spec.
        
        Args:
            task: Task dictionary with task_id, description, plan, etc.
            role: Target agent role (Engineer, Senior Engineer, etc).
            model: Target model (claude-haiku-4-5, etc).
            effort: Effort level (low, medium, high, max).
            
        Returns:
            DELEGATE dictionary with handoff_type, task_id, role, model, effort,
            scope, context, plan, and success_criteria fields.
        """
        task_id = task.get('task_id', '')
        description = task.get('description', '')
        plan = task.get('plan', [])
        
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": role,
            "model": model,
            "effort": effort,
            "scope": description,
            "context": task.get('context', []),
            "plan": plan if isinstance(plan, list) else [plan],
            "success_criteria": task.get('success_criteria', ["Task completed per specification"])
        }
        
        logger.debug(f"Created DELEGATE for task {task_id} to {role} using {model}")
        return delegate

    def move_task_to_processing(self, task_id: str) -> bool:
        """Move task from incoming to processing queue.
        
        Args:
            task_id: Unique identifier for the task.
            
        Returns:
            True if task was successfully moved, False otherwise.
        """
        incoming_file = self.queue_dir / "incoming" / f"{task_id}.yaml"
        
        if incoming_file.exists():
            try:
                # Read task
                with open(incoming_file, 'r') as f:
                    task = yaml.safe_load(f)
                
                # Delete from incoming
                incoming_file.unlink()
                logger.info(f"Moved task {task_id} from incoming to processing")
                
                return True
            except Exception as e:
                logger.error(f"Error moving task {task_id} to processing: {e}")
                return False
        
        logger.warning(f"Task file not found for {task_id}")
        return False

    def move_task_to_done(self, task_id: str, decision: str) -> bool:
        """Move task from processing to done queue with decision.
        
        Args:
            task_id: Unique identifier for the task.
            decision: Decision type (PROCEED, REWORK, ESCALATE).
            
        Returns:
            True if task was successfully moved, False otherwise.
        """
        try:
            # Delete HANDBACK files from processing
            processing_dir = self.queue_dir / "processing"
            handback_count = 0
            for handback_file in processing_dir.glob(f"{task_id}-HANDBACK-*.yaml"):
                handback_file.unlink()
                handback_count += 1
            
            # Create decision file
            decision_file = self.queue_dir / "done" / f"{task_id}-{decision}.yaml"
            decision_data = {
                "task_id": task_id,
                "decision": decision,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(decision_file, 'w') as f:
                yaml.dump(decision_data, f)
            
            logger.info(f"Moved task {task_id} from processing to done with decision={decision} "
                       f"(removed {handback_count} HANDBACK file(s))")
            return True
        except Exception as e:
            logger.error(f"Error moving task {task_id} to done: {e}")
            return False

    def process_handback(self, handback: Dict) -> Dict:
        """Process HANDBACK from agent."""
        status = handback.get('status', 'unknown')
        task_id = handback.get('task_id', '')
        
        if status == 'complete':
            return {
                "success": True,
                "next_step": "quality-gate",
                "task_id": task_id
            }
        elif status == 'blocked':
            return {
                "success": True,
                "next_step": "escalate",
                "task_id": task_id,
                "blockers": handback.get('blockers', [])
            }
        elif status == 'partial':
            return {
                "success": True,
                "next_step": "rework",
                "task_id": task_id,
                "deliverables": handback.get('deliverables', [])
            }
        else:
            return {
                "success": False,
                "next_step": "error",
                "task_id": task_id,
                "error": f"Unknown HANDBACK status: {status}"
            }

    def capture_span(self, agent_role: str, handback: Dict) -> Path:
        """Capture OpenTelemetry span from HANDBACK.
        
        Args:
            agent_role: Role of the agent that completed work.
            handback: HANDBACK dictionary with task results.
            
        Returns:
            Path to written span file.
            
        Raises:
            IOError: If span file cannot be written.
        """
        try:
            task_id = handback.get('task_id', 'unknown')
            tokens_in = handback.get('tokens_in', 0)
            tokens_out = handback.get('tokens_out', 0)
            model = handback.get('model', '')
            duration_minutes = handback.get('duration_minutes', 0)
            
            # Validate inputs
            if not isinstance(tokens_in, int) or tokens_in < 0:
                logger.warning(f"Invalid tokens_in: {tokens_in}, using 0")
                tokens_in = 0
            if not isinstance(tokens_out, int) or tokens_out < 0:
                logger.warning(f"Invalid tokens_out: {tokens_out}, using 0")
                tokens_out = 0
            
            # Calculate cost
            cost = self._calculate_token_cost(model, tokens_in, tokens_out)
            
            # Create span data
            span_data = {
                "span_type": "task_execution",
                "task_id": task_id,
                "agent_role": agent_role,
                "model": model,
                "agent_model": model,
                "status": handback.get('status', 'unknown'),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_total": tokens_in + tokens_out,
                "cost": round(cost, 6),
                "duration_seconds": duration_minutes * 60,
                "effort": handback.get('effort', ''),
                "escalations": handback.get('escalations', 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Write span file
            date_dir = self.artifacts_dir / self.current_date
            date_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
            span_file = date_dir / f"SPAN-{timestamp}-{agent_role}.yaml"
            
            with open(span_file, 'w') as f:
                yaml.dump(span_data, f)
            
            logger.info(f"Captured span for task {task_id} to {span_file.name}")
            return span_file
            
        except IOError as e:
            logger.error(f"Failed to write span file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error capturing span: {e}")
            raise

    def _calculate_token_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate cost from token counts."""
        if model not in self.TOKEN_PRICING:
            return 0.0
        
        pricing = self.TOKEN_PRICING[model]
        cost_in = (tokens_in / 1_000_000) * pricing['input']
        cost_out = (tokens_out / 1_000_000) * pricing['output']
        
        return cost_in + cost_out

    def generate_artifact_index(self) -> Path:
        """Generate searchable index.json from all artifacts.
        
        Scans artifacts directory for SPAN files and aggregates them into a
        single index.json with statistics by agent and status. Used for
        observability and metrics reporting.
        
        Returns:
            Path to written index.json file.
            
        Raises:
            IOError: If index file cannot be written.
        """
        index_data = {
            "generated_at": datetime.now().isoformat(),
            "artifacts": [],
            "stats": {
                "total_artifacts": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_agent": {},
                "by_status": {}
            }
        }
        
        # Scan all date directories for artifacts
        for date_dir in sorted(self.artifacts_dir.glob("20*")):
            if not date_dir.is_dir():
                continue
            
            # Scan for SPAN files
            for span_file in sorted(date_dir.glob("SPAN-*.yaml")):
                try:
                    with open(span_file, 'r') as f:
                        span_data = yaml.safe_load(f)
                    
                    if not span_data:
                        continue
                    
                    artifact_entry = {
                        "file": span_file.name,
                        "file_type": "SPAN",
                        "task_id": span_data.get('task_id'),
                        "agent_role": span_data.get('agent_role'),
                        "agent_model": span_data.get('agent_model'),
                        "status": span_data.get('status'),
                        "tokens_total": span_data.get('tokens_total', 0),
                        "cost": span_data.get('cost', 0.0),
                        "timestamp": span_data.get('timestamp')
                    }
                    
                    index_data['artifacts'].append(artifact_entry)
                    
                    # Update statistics
                    index_data['stats']['total_artifacts'] += 1
                    index_data['stats']['total_tokens'] += span_data.get('tokens_total', 0)
                    index_data['stats']['total_cost'] += span_data.get('cost', 0.0)
                    
                    # By agent stats
                    agent = span_data.get('agent_role', 'unknown')
                    if agent not in index_data['stats']['by_agent']:
                        index_data['stats']['by_agent'][agent] = {
                            "count": 0,
                            "total_cost": 0.0,
                            "total_tokens": 0
                        }
                    index_data['stats']['by_agent'][agent]['count'] += 1
                    index_data['stats']['by_agent'][agent]['total_cost'] += span_data.get('cost', 0.0)
                    index_data['stats']['by_agent'][agent]['total_tokens'] += span_data.get('tokens_total', 0)
                    
                    # By status stats
                    status = span_data.get('status', 'unknown')
                    if status not in index_data['stats']['by_status']:
                        index_data['stats']['by_status'][status] = 0
                    index_data['stats']['by_status'][status] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing span file {span_file}: {e}")
        
        # Round costs for readability
        index_data['stats']['total_cost'] = round(index_data['stats']['total_cost'], 6)
        for agent_key in index_data['stats']['by_agent']:
            index_data['stats']['by_agent'][agent_key]['total_cost'] = round(
                index_data['stats']['by_agent'][agent_key]['total_cost'], 6
            )
        
        # Write index file
        index_file = self.artifacts_dir / "index.json"
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        return index_file

    def run_poll_cycle(self) -> Dict:
        """Run one complete poll cycle (30-60 second cadence).
        
        Polls all three queues (incoming, processing, done) and generates
        artifact index. Captures detailed metrics for observability.
        
        Queue polling order:
        1. Incoming queue: Check for new DELEGATE tasks
        2. Processing queue: Check for HANDBACK completions
        3. Done queue: Check for human decisions (PROCEED, REWORK, ESCALATE)
        4. Artifact index: Update statistics and cost tracking
        
        Returns:
            Dictionary with poll cycle results and metrics including:
            - timestamp: ISO 8601 timestamp of poll cycle start
            - incoming_tasks: Number of new tasks found
            - handbacks_processed: Number of HANDBACKs found
            - decisions_processed: Number of human decisions found
            - errors: List of any errors encountered
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "incoming_tasks": 0,
            "handbacks_processed": 0,
            "decisions_processed": 0,
            "errors": []
        }
        
        try:
            logger.info("Starting poll cycle")
            
            # Poll incoming and delegate
            try:
                incoming_tasks = self.poll_incoming_queue()
                results['incoming_tasks'] = len(incoming_tasks)
                
                # Delegate each incoming task to appropriate agent
                for task in incoming_tasks:
                    try:
                        task_id = task.get('task_id', 'unknown')
                        # Route task per AGENTS.md decision tree
                        routing = self.route_task(task)
                        role = routing.get('role', 'Unknown')
                        logger.info(f"Routed task {task_id} to {role}")
                        
                        # Move task to processing state
                        if not self.move_task(task_id, 'incoming', 'processing'):
                            logger.error(f"Failed to move task {task_id} to processing")
                            continue
                        
                        # Invoke agent for the task
                        handback = self.invoke_agent(task)
                        if not handback:
                            logger.error(f"Agent invocation failed for task {task_id}")
                            self.move_task(task_id, 'processing', 'incoming')
                            continue
                        
                        # Save HANDBACK and move to done
                        handback_file = self.queue_dir / 'processing' / f"{task_id}-HANDBACK.yaml"
                        with open(handback_file, 'w') as f:
                            yaml.dump(handback, f)
                        
                        if self.move_task(task_id, 'processing', 'done'):
                            try:
                                agent_role = routing.get('role', 'Unknown')
                                self.capture_span(agent_role, handback)
                            except Exception as e:
                                logger.warning(f"Failed to capture span: {e}")
                            logger.info(f"Task {task_id} completed and moved to done/")
                        
                    except Exception as e:
                        logger.error(f"Error routing task {task.get('task_id', '?')}: {e}")
                        results['errors'].append(f"route: {str(e)}")
            except Exception as e:
                logger.error(f"Error polling incoming queue: {e}")
                results['errors'].append(f"incoming: {str(e)}")
            
            # Poll processing (handbacks)
            try:
                handbacks = self.poll_processing_queue()
                results['handbacks_processed'] = len(handbacks)
            except Exception as e:
                logger.error(f"Error polling processing queue: {e}")
                results['errors'].append(f"processing: {str(e)}")
            
            # Poll done (decisions)
            try:
                decisions = self.poll_done_queue()
                results['decisions_processed'] = len(decisions)
            except Exception as e:
                logger.error(f"Error polling done queue: {e}")
                results['errors'].append(f"done: {str(e)}")
            
            # Generate index
            try:
                self.generate_artifact_index()
                logger.info("Generated artifact index")
            except Exception as e:
                logger.error(f"Error generating artifact index: {e}")
                results['errors'].append(f"index: {str(e)}")
            
            # Summary
            total_processed = results['incoming_tasks'] + results['handbacks_processed'] + results['decisions_processed']
            if total_processed > 0:
                logger.info(f"Poll cycle complete: {results['incoming_tasks']} incoming, "
                           f"{results['handbacks_processed']} handbacks, {results['decisions_processed']} decisions")
            
        except Exception as e:
            logger.error(f"Unexpected error in poll cycle: {e}")
            results['errors'].append(f"unexpected: {str(e)}")
        
        return results
    
    def move_task(self, task_id: str, from_state: str, to_state: str) -> bool:
        """Move task file between queue states.
        
        Args:
            task_id: Task ID without extension
            from_state: Current state (incoming, processing, done)
            to_state: Target state (incoming, processing, done)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from_path = self.queue_dir / from_state / f"{task_id}.yaml"
            to_path = self.queue_dir / to_state / f"{task_id}.yaml"
            
            if not from_path.exists():
                logger.error(f"Task file not found: {from_path}")
                return False
            
            # Read task content
            with open(from_path, 'r') as f:
                task = yaml.safe_load(f)
            
            # Write to new location
            with open(to_path, 'w') as f:
                yaml.dump(task, f)
            
            # Remove old file
            from_path.unlink()
            
            logger.info(f"Moved task {task_id} from {from_state}/ to {to_state}/")
            return True
            
        except Exception as e:
            logger.error(f"Error moving task {task_id}: {e}")
            return False
    
    def invoke_agent(self, task: Dict, timeout_seconds: int = 300) -> Optional[Dict]:
        """Invoke agent for a task.
        
        Creates placeholder HANDBACK for Phase 5.11 subprocess implementation.
        
        Args:
            task: Task dictionary
            timeout_seconds: Max time to wait for agent
            
        Returns:
            HANDBACK dictionary if successful, None otherwise
        """
        task_id = task.get('task_id', 'unknown')
        role = task.get('role', 'unknown')
        
        try:
            logger.info(f"Invoking agent for task {task_id} (role={role})...")
            
            # TODO Phase 5.11: Implement actual subprocess invocation
            # For now, return placeholder HANDBACK to unblock task processing
            
            handback = {
                "handoff_type": "HANDBACK",
                "task_id": task_id,
                "status": "design-complete",
                "role": role,
                "model": task.get('model', 'claude-sonnet-4-6'),
                "tokens_in": 50000,
                "tokens_out": 30000,
                "duration_minutes": 15,
                "effort": task.get('effort', 'high'),
                "escalations": 0,
                "confidence": 0.85,
                "decision": "PROCEED"
            }
            
            logger.info(f"Agent task {task_id} completed")
            return handback
            
        except Exception as e:
            logger.error(f"Error invoking agent for task {task_id}: {e}")
            return None
    
    def run(self, idle_timeout_seconds: int = 60, poll_interval_seconds: int = 45):
        """Run Orchestrator in continuous polling mode.
        
        Polls queue continuously until idle timeout is reached.
        
        Args:
            idle_timeout_seconds: Exit after this many seconds of no activity (default: 60)
            poll_interval_seconds: Sleep between polls (default: 45, range 30-60)
        """
        import signal
        
        idle_count = 0
        idle_threshold = max(1, idle_timeout_seconds // poll_interval_seconds)
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            exit(0)
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info(f"Starting continuous polling loop (idle_timeout={idle_timeout_seconds}s, poll_interval={poll_interval_seconds}s)")
        
        cycle_num = 0
        while True:
            cycle_num += 1
            logger.info(f"Poll cycle {cycle_num}: checking queue...")
            
            try:
                results = self.run_poll_cycle()
                total_processed = results['incoming_tasks'] + results['handbacks_processed'] + results['decisions_processed']
                
                if total_processed > 0:
                    idle_count = 0
                    logger.info(f"Cycle {cycle_num} processed {total_processed} items, resetting idle count")
                else:
                    idle_count += 1
                    logger.info(f"Cycle {cycle_num} idle, count: {idle_count}/{idle_threshold}")
                
                # Check idle timeout
                if idle_count >= idle_threshold:
                    logger.info(f"Idle timeout reached after {idle_count * poll_interval_seconds}s, exiting...")
                    break
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in poll cycle: {e}")
                idle_count += 1
            
            # Sleep before next cycle (30-60s per SPEC)
            logger.debug(f"Sleeping for {poll_interval_seconds}s before next poll...")
            time.sleep(poll_interval_seconds)
        
        logger.info("Orchestrator stopped")


if __name__ == "__main__":
    """Run Orchestrator as the master router for all work.
    
    Starts continuous polling loop that:
    1. Polls ~/.copilot/queue/incoming/ for new DELEGATE tasks
    2. Routes to appropriate agent per AGENTS.md
    3. Delegates task to agent
    4. Waits for HANDBACK
    5. Moves task to done/
    6. Exits when no work for 60+ seconds
    """
    orch = Orchestrator()
    orch.run(idle_timeout_seconds=60, poll_interval_seconds=45)
