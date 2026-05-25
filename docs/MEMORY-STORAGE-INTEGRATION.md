# Memory Storage Integration Guide

**Status**: Design Specification  
**Version**: 1.0  
**Purpose**: How agents, skills, and orchestrator interact with unified memory

---

## 1. Integration Overview

### 1.1 Architecture Layers

```
┌─────────────────────────────────────────────┐
│ Agents (engineer, senior_engineer, etc)     │ ← Read/Write THINKING
│ Skills (skill-creator, repo-init, etc)      │ ← Read memory for context
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│ Orchestrator (task routing)                  │ ← Write DELEGATE/HANDBACK
│ Queue Manager (lifecycle)                    │ ← Manage queue states
│ Memory Manager (new layer)                   │ ← Centralized memory ops
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│ File System (~/.agentic-engineers/)          │ ← Storage
│ - delegates/                                 │
│ - handbacks/                                 │
│ - logs/                                      │
│ - thinking/                                  │
│ - metadata.json                              │
└─────────────────────────────────────────────┘
```

### 1.2 Memory Manager (NEW)

Central service for all memory operations:

```python
class MemoryManager:
    """Unified interface for memory storage and retrieval."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.memory_root = Path.home() / ".agentic-engineers" / session_id / "memory"
        self.delegates = DelegateStore(self.memory_root / "delegates")
        self.handbacks = HandbackStore(self.memory_root / "handbacks")
        self.logs = LogStore(self.memory_root / "logs")
        self.thinking = ThinkingStore(self.memory_root / "thinking")
        self.metadata = MetadataStore(self.memory_root / "metadata.json")
        self.timeline = TimelineStore(self.memory_root / "timeline.jsonl")
        self.audit = AuditLog(self.memory_root / "audit.log")
```

---

## 2. Agent Integration Points

### 2.1 How Orchestrator Writes DELEGATEs

**Location**: `src/orchestration/agents/orchestrator.py`

**Current Code** (DELEGATE creation):
```python
def route_task(delegate: Dict) -> str:
    """Route DELEGATE to appropriate agent."""
    task_id = delegate["task_id"]
    queue_dir = self.get_delegates_dir()
    
    delegate_path = queue_dir / f"{task_id}-delegate.yaml"
    with open(delegate_path, "w") as f:
        yaml.dump(delegate, f)
    
    return task_id
```

**New Code** (integrate with memory):
```python
def route_task(delegate: Dict) -> str:
    """Route DELEGATE to appropriate agent and write to memory."""
    task_id = delegate["task_id"]
    session_id = self.session_id
    
    # 1. Write to queue (existing)
    queue_dir = self.get_delegates_dir()
    delegate_path = queue_dir / f"{task_id}-delegate.yaml"
    with open(delegate_path, "w") as f:
        yaml.dump(delegate, f)
    
    # 2. Write to memory (NEW)
    memory = MemoryManager(session_id)
    memory.delegates.write(task_id, delegate)
    
    # 3. Update timeline (NEW)
    memory.timeline.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "delegate_created",
        "task_id": task_id,
        "agent": delegate["role"],
        "details": f"DELEGATE queued for {delegate['role']}"
    })
    
    # 4. Audit (NEW)
    memory.audit.log(f"DELEGATE_WRITE | task_id={task_id} | role={delegate['role']}")
    
    return task_id
```

### 2.2 How Orchestrator Receives HANDBACKs

**Location**: `src/orchestration/agents/orchestrator.py`

**Current Code** (HANDBACK processing):
```python
def process_handback(handback: Dict, task_id: str):
    """Process returned HANDBACK."""
    # Validate
    validate_handback(handback)
    
    # Move to done queue
    done_path = self.get_done_queue_dir() / f"{task_id}-handback.yaml"
    with open(done_path, "w") as f:
        yaml.dump(handback, f)
```

**New Code** (integrate with memory):
```python
def process_handback(handback: Dict, task_id: str):
    """Process returned HANDBACK and write to memory."""
    # Validate
    validate_handback(handback)
    
    session_id = self.session_id
    
    # 1. Move to done queue (existing)
    done_path = self.get_done_queue_dir() / f"{task_id}-handback.yaml"
    with open(done_path, "w") as f:
        yaml.dump(handback, f)
    
    # 2. Write to memory (NEW)
    memory = MemoryManager(session_id)
    memory.handbacks.write(task_id, handback)
    
    # 3. Update metrics (NEW)
    memory.update_metrics(handback)
    
    # 4. Update timeline (NEW)
    memory.timeline.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "handback_received",
        "task_id": task_id,
        "agent": handback.get("delegated_to", "unknown"),
        "details": f"HANDBACK received with status={handback['status']}"
    })
    
    # 5. Audit (NEW)
    memory.audit.log(
        f"HANDBACK_WRITE | task_id={task_id} | status={handback['status']} | "
        f"quality_score={handback.get('quality_score', 'N/A')}"
    )
```

### 2.3 How Agents Write Logs

**Location**: Each agent (engineer, senior_engineer, etc.)

**Pattern**:
```python
from src.orchestration.memory import LogWriter

class EngineerAgent:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.log_writer = LogWriter(session_id, agent_type="engineer")
    
    def execute_task(self, task_id: str):
        self.log_writer.info("Starting task execution", context={"step": 1})
        
        try:
            # Do work
            self.log_writer.info("Completed step 1")
        except Exception as e:
            self.log_writer.error("Task failed", context={"error": str(e)})
            raise
```

**Implementation**:
```python
class LogWriter:
    def __init__(self, session_id: str, agent_type: str, phase: str = "default"):
        self.session_id = session_id
        self.agent_type = agent_type
        self.phase = phase
        self.log_path = (
            Path.home() / ".agentic-engineers" / session_id / "memory" / "logs" /
            f"{agent_type}-{phase}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def info(self, message: str, context: Dict = None):
        self._write("INFO", message, context)
    
    def error(self, message: str, context: Dict = None):
        self._write("ERROR", message, context)
    
    def _write(self, level: str, message: str, context: Dict = None):
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "phase": self.phase,
            "level": level,
            "message": message,
            "context": context or {}
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event) + "\n")
```

### 2.4 How Agents Write Thinking Output

**Location**: Each agent (after analysis, before implementation)

**Pattern**:
```python
class SeniorEngineerAgent:
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    def analyze_and_plan(self, delegate: Dict) -> Dict:
        """Analyze problem, write thinking, return plan."""
        task_id = delegate["task_id"]
        
        # Agent does analysis (using Claude or other model)
        thinking = self._do_analysis(delegate)
        
        # Write to memory
        self._store_thinking(task_id, thinking)
        
        # Return plan
        return self._extract_plan(thinking)
    
    def _store_thinking(self, task_id: str, thinking_md: str):
        memory = MemoryManager(self.session_id)
        memory.thinking.write(task_id, thinking_md)
        memory.audit.log(f"THINKING_WRITE | task_id={task_id}")
```

---

## 3. Skill Integration

### 3.1 Skills that Read Memory

**Example**: `skill-creator` (creates new skills)

**How it reads context**:
```python
from src.orchestration.memory import MemoryManager

class SkillCreator:
    def __init__(self, session_id: str):
        self.memory = MemoryManager(session_id)
    
    def create_skill(self, spec: Dict) -> str:
        """Create a new skill with full session context."""
        
        # 1. Read recent decisions from session
        decisions = self.memory.metadata.get_decisions()
        
        # 2. Read related task completions
        related_tasks = self.memory.handbacks.query(
            status="complete",
            quality_score_min=80,
            limit=5
        )
        
        # 3. Read agent feedback
        feedback = self.memory.feedback.list()
        
        # 4. Create skill informed by context
        skill = self._generate_skill(spec, decisions, related_tasks, feedback)
        
        return skill
```

### 3.2 Skills that Write Back

**Example**: `skill-creator` writing feedback after QE review

```python
class QualityEngineer:
    def review_handback(self, task_id: str) -> Dict:
        """Review completed task and write feedback."""
        memory = MemoryManager(self.session_id)
        
        # 1. Read HANDBACK
        handback = memory.handbacks.get(task_id)
        
        # 2. Review against success criteria
        delegate = memory.delegates.get(task_id)
        feedback_dict = self._conduct_review(delegate, handback)
        
        # 3. Write feedback to memory
        memory.feedback.write(task_id, feedback_dict)
        
        # 4. Update metadata with decision
        memory.metadata.append_decision({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "decision": f"Review of {task_id}: {'APPROVED' if feedback_dict['approve'] else 'REWORK'}",
            "rationale": feedback_dict['reviewer_notes']
        })
        
        return feedback_dict
```

---

## 4. Orchestrator Integration

### 4.1 Session Lifecycle

**Session Creation** (start of OpenCode session):
```python
class OpenCodeOrchestrator:
    def create_session(self) -> str:
        """Create new session with memory directory."""
        session_id = str(uuid.uuid4())
        
        # 1. Create memory directory
        memory_root = Path.home() / ".agentic-engineers" / session_id / "memory"
        memory_root.mkdir(parents=True, exist_ok=True)
        
        # 2. Create subdirectories
        for subdir in ["delegates", "handbacks", "logs", "thinking", "spans", "feedback", "metrics"]:
            (memory_root / subdir).mkdir(exist_ok=True)
        
        # 3. Initialize metadata
        memory = MemoryManager(session_id)
        memory.metadata.initialize({
            "session_id": session_id,
            "harness": self.harness,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "user": self.user,
            "repository": self.repo,
            "branch": self.branch,
            "config": {
                "log_retention_days": 90,
                "trace_retention_days": 30,
                "encryption_enabled": False
            }
        })
        
        # 4. Initialize audit log
        memory.audit.log(f"SESSION_CREATE | session_id={session_id} | harness={self.harness}")
        
        return session_id
```

**Session Cleanup** (at end of session):
```python
def cleanup_session(self, session_id: str):
    """Cleanup expired memory files."""
    memory = MemoryManager(session_id)
    
    # 1. Remove expired logs (if older than retention period)
    memory.logs.cleanup_expired()
    
    # 2. Remove expired spans
    memory.spans.cleanup_expired()
    
    # 3. Update metadata with completion time
    memory.metadata.update({
        "last_accessed_at": datetime.utcnow().isoformat() + "Z",
        "phase": "completed"
    })
    
    # 4. Audit
    memory.audit.log(f"SESSION_CLEANUP | session_id={session_id}")
```

### 4.2 Phase Transitions

```python
def transition_phase(self, session_id: str, from_phase: str, to_phase: str):
    """Record phase transition in memory."""
    memory = MemoryManager(session_id)
    
    # Update metadata
    memory.metadata.update_phase(to_phase)
    
    # Add timeline event
    memory.timeline.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "phase_transition",
        "details": f"Transitioning from {from_phase} to {to_phase}"
    })
    
    # Audit
    memory.audit.log(f"PHASE_TRANSITION | from={from_phase} | to={to_phase}")
```

---

## 5. Query Patterns (Agents/Skills Reading Memory)

### 5.1 Find All DELEGATEs for a Role

```python
memory = MemoryManager(session_id)

# Direct index query (fast)
delegates = memory.delegates.query(role="senior_engineer")

# Returns list of DELEGATE dicts
for d in delegates:
    print(f"{d['task_id']}: {d['effort']}")
```

### 5.2 Find HANDBACKs by Quality Score

```python
# Find all "good" completions (>= 80)
good_handbacks = memory.handbacks.query(
    quality_score_min=80,
    status="complete"
)

# Find tasks needing rework
rework_needed = memory.handbacks.query(
    quality_score_max=65
)
```

### 5.3 Find Logs for Debugging

```python
# Get all ERROR-level logs for a task
errors = memory.logs.query(
    task_id="2026-05-24-task1",
    level="ERROR"
)

for e in errors:
    print(f"{e['timestamp']}: {e['message']}")

# Get logs for a specific phase
phase1_logs = memory.logs.query(phase="phase1")
```

### 5.4 Get Thinking for Understanding

```python
# Read thinking output for a task (understand decision rationale)
thinking = memory.thinking.get("2026-05-24-task1")
print(thinking)  # Markdown content

# Search thinking for decision keywords
thinking_with_security = memory.thinking.search("security")
```

### 5.5 Get Metrics for Analysis

```python
# Get cost analysis
costs = memory.metrics.get_cost_analysis()
print(f"Total cost: ${costs['total_cost_usd']}")

# Get token timeline (for trending)
timeline = memory.metrics.get_token_timeline()

# Average quality by role
avg_quality = memory.metrics.get_average_quality_by_role()
```

---

## 6. Backward Compatibility (With Existing Queue)

### 6.1 Queue-to-Memory Migration

During a transition period, both paths will be used:

```python
def write_delegate(delegate: Dict):
    """Write to both queue (old) and memory (new)."""
    task_id = delegate["task_id"]
    
    # 1. Queue path (existing - required for orchestrator compatibility)
    queue_path = queue_dir / f"{task_id}-delegate.yaml"
    yaml.dump(delegate, open(queue_path, "w"))
    
    # 2. Memory path (new - for future queries)
    memory = MemoryManager(session_id)
    memory.delegates.write(task_id, delegate)
```

### 6.2 Cross-Session Queries (Future)

When multiple sessions need to be queried together:

```python
class SessionAnalyzer:
    def get_all_quality_scores(self) -> Dict[str, float]:
        """Aggregate quality scores across all sessions."""
        result = {}
        
        for session_dir in (Path.home() / ".agentic-engineers").iterdir():
            if session_dir.is_dir():
                session_id = session_dir.name
                try:
                    memory = MemoryManager(session_id)
                    avg = memory.metrics.get_average_quality()
                    result[session_id] = avg
                except:
                    pass
        
        return result
```

---

## 7. Environment Variables

Agents and skills receive these environment variables:

```bash
SESSION_ID=771628bc-263c-4c9e-98c9-5f24a6418b95
MEMORY_ROOT=~/.agentic-engineers/771628bc-263c-4c9e-98c9-5f24a6418b95/memory
HARNESS=local
PHASE=phase1
```

---

## 8. Error Handling

### 8.1 Memory Write Failures

```python
def safe_write_delegate(delegate: Dict, session_id: str):
    """Write DELEGATE with fallback."""
    try:
        memory = MemoryManager(session_id)
        memory.delegates.write(delegate["task_id"], delegate)
    except Exception as e:
        logger.error(f"Failed to write DELEGATE to memory: {e}")
        # Still write to queue (fallback)
        queue_path = get_queue_dir() / f"{delegate['task_id']}-delegate.yaml"
        yaml.dump(delegate, open(queue_path, "w"))
        # Log the failure for later review
        memory.audit.log(f"DELEGATE_WRITE_FAILED | {e}")
```

### 8.2 Memory Read Failures

```python
def get_delegate_with_fallback(task_id: str, session_id: str) -> Dict:
    """Read DELEGATE with fallback to queue."""
    try:
        memory = MemoryManager(session_id)
        return memory.delegates.get(task_id)
    except:
        # Fallback to queue
        queue_path = get_queue_dir() / f"*{task_id}*.yaml"
        files = list(queue_path.parent.glob(queue_path.name))
        if files:
            return yaml.safe_load(open(files[0]))
        raise FileNotFoundError(f"DELEGATE {task_id} not found")
```

---

## 9. Testing Integration

### 9.1 Unit Tests

```python
def test_delegate_write_and_read(tmp_path):
    """Test DELEGATE write/read integration."""
    session_id = str(uuid.uuid4())
    
    # Redirect memory root to temp dir
    memory = MemoryManager(session_id)
    memory.memory_root = tmp_path
    
    # Write DELEGATE
    delegate = {"task_id": "2026-05-24-test", "role": "engineer"}
    memory.delegates.write(delegate["task_id"], delegate)
    
    # Read DELEGATE
    read_delegate = memory.delegates.get(delegate["task_id"])
    assert read_delegate["role"] == "engineer"
```

### 9.2 Integration Tests

```python
def test_full_delegate_handback_lifecycle(session_id):
    """Test complete DELEGATE→HANDBACK lifecycle."""
    memory = MemoryManager(session_id)
    
    # Create DELEGATE
    delegate = {...}
    memory.delegates.write(delegate["task_id"], delegate)
    assert memory.delegates.get(delegate["task_id"]) is not None
    
    # Create HANDBACK
    handback = {"task_id": delegate["task_id"], "status": "complete"}
    memory.handbacks.write(handback["task_id"], handback)
    
    # Verify timeline
    timeline_events = memory.timeline.query(task_id=delegate["task_id"])
    assert len(timeline_events) >= 2  # create + handback
```

---

## 10. Migration Checklist

- [ ] **Phase 1: MemoryManager implementation** (~2 days)
  - [ ] Create core MemoryManager class
  - [ ] Implement delegates, handbacks, logs, thinking stores
  - [ ] Add index management
  
- [ ] **Phase 2: Orchestrator integration** (~1 day)
  - [ ] Update route_task to write memory
  - [ ] Update process_handback to write memory
  - [ ] Add timeline and audit logging
  
- [ ] **Phase 3: Agent integration** (~2 days)
  - [ ] Add LogWriter to agents
  - [ ] Add thinking output to agents
  - [ ] Update all agents to use MemoryManager
  
- [ ] **Phase 4: Skill integration** (~1 day)
  - [ ] Update skills to read memory
  - [ ] Add query patterns to skills
  
- [ ] **Phase 5: Testing** (~2 days)
  - [ ] Unit tests for MemoryManager
  - [ ] Integration tests for full lifecycle
  - [ ] Backward compatibility verification
  
- [ ] **Phase 6: Documentation** (~1 day)
  - [ ] API documentation
  - [ ] Migration guide
  - [ ] Troubleshooting guide

---

## References

- `docs/MEMORY-ARCHITECTURE.md` — Architecture overview
- `docs/MEMORY-STORAGE-SCHEMA.yaml` — Storage specification
- `docs/MEMORY-API-DESIGN.md` — Future database API
- `src/orchestration/agents/orchestrator.py` — Orchestrator code
- `src/orchestration/queue_manager.py` — Queue manager code
