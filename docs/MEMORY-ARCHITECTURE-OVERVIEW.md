# Memory System Architecture Overview

## Executive Summary

The agentic-engineers memory system provides centralized, file-based storage for all session events (DELEGATEs, HANDBACKs, logs, metrics). Data is stored in `~/.agentic-engineers/{session_id}/memory/` and aggregated at session end for querying, analysis, and auditing. The system is designed for portability, auditability, and future database migration.

**Key characteristics:**
- ✅ Centralized: Single directory per session
- ✅ Persistent: Survives session restarts
- ✅ Queryable: JSON index enables rich analysis
- ✅ Auditable: Complete timestamp history
- ✅ Portable: Works offline, no external dependencies
- ✅ Scalable: Efficient structure supports large sessions (1000+ tasks)

---

## System Architecture

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Task Routing & Lifecycle Management                 │    │
│  │  - Assign DELEGATEs to agents                        │    │
│  │  - Receive and process HANDBACKs                     │    │
│  │  - Collect metrics                                  │    │
│  └────────────────┬────────────────────────────────────┘    │
└─────────────────┼────────────────────────────────────────────┘
                  │
                  ├─→ SessionMemoryManager (collects events)
                  │
┌─────────────────┴────────────────────────────────────────────┐
│                     Memory Layer                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ SessionMemoryManager (Lifecycle)                     │    │
│  │  - initialize()           → Set up directories       │    │
│  │  - collect_memory_event() → Record DELEGATE/HANDBACK │    │
│  │  - aggregate_memory()     → Build session index      │    │
│  │  - get_delegates()        → Query delegates          │    │
│  │  - query_by_task_id()     → Find specific task      │    │
│  └────────────────┬────────────────────────────────────┘    │
│                   │                                           │
│  ┌────────────────┴────────────────────────────────────┐    │
│  │ SessionMemoryAggregator (Collection)                 │    │
│  │  - collect_delegates()   → From queue/artifacts      │    │
│  │  - collect_handbacks()   → From queue/artifacts      │    │
│  │  - collect_logs()        → From log directories      │    │
│  │  - aggregate_all()       → Comprehensive indexing    │    │
│  └────────────────┬────────────────────────────────────┘    │
│                   │                                           │
│  ┌────────────────┴────────────────────────────────────┐    │
│  │ ArtifactMemoryStore (Storage Engine)                 │    │
│  │  - write()      → Write JSON to disk                 │    │
│  │  - read()       → Read JSON from disk                │    │
│  │  - append()     → Append JSONL metrics               │    │
│  │  - list_all()   → Enumerate memory files             │    │
│  └────────────────┬────────────────────────────────────┘    │
└─────────────────┼────────────────────────────────────────────┘
                  │
┌─────────────────┴────────────────────────────────────────────┐
│              Filesystem (~/.agentic-engineers/)               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ {session_id}/memory/                                 │    │
│  │  ├── delegates/           DELEGATE records            │    │
│  │  ├── handbacks/           HANDBACK records            │    │
│  │  ├── logs/                Execution logs              │    │
│  │  ├── thinking/            Agent reasoning             │    │
│  │  ├── metrics/             Token usage & quality       │    │
│  │  ├── index.json           Machine-readable index      │    │
│  │  └── summary.md           Human-readable summary      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
~/.agentic-engineers/
├── {session_id}/
│   ├── memory/                    ← Primary session memory
│   │   ├── delegates/             (DELEGATE copies)
│   │   │   ├── task-001.yaml
│   │   │   ├── task-002.yaml
│   │   │   └── ...
│   │   ├── handbacks/             (HANDBACK copies)
│   │   │   ├── task-001-handback.yaml
│   │   │   ├── task-002-handback.yaml
│   │   │   └── ...
│   │   ├── logs/                  (Execution logs)
│   │   │   ├── agent-engineer-001.log
│   │   │   ├── orchestrator.log
│   │   │   └── ...
│   │   ├── thinking/              (Agent reasoning)
│   │   │   ├── task-001-thinking.md
│   │   │   └── ...
│   │   ├── metrics/               (Token usage, quality)
│   │   │   ├── daily/
│   │   │   │   ├── 2025-05-24.jsonl
│   │   │   │   └── 2025-05-25.jsonl
│   │   │   ├── session-metrics.jsonl
│   │   │   └── quality-scores.jsonl
│   │   ├── usage/                 (Token tracking)
│   │   │   └── usage_history.jsonl
│   │   ├── tokenadvisor/          (Cost analysis)
│   │   │   ├── daily-report.json
│   │   │   └── optimization.json
│   │   ├── index.json             ← Complete index
│   │   ├── index.md               ← Human-readable index
│   │   └── summary.md             ← Session summary
│   ├── delegates/                 (Original DELEGATEs)
│   └── handbacks/                 (Original HANDBACKs)
├── archive/                       (Old session backups)
└── MEMORY_INDEX.json              (Global index)
```

### Data Flow

```
Agent Execution Timeline
─────────────────────────

1. SESSION START
   ├─ Orchestrator calls manager.initialize()
   ├─ Memory directories created
   └─ index.json initialized (empty)

2. TASK ASSIGNMENT
   ├─ Orchestrator creates DELEGATE
   ├─ Copies to memory/delegates/task-001.yaml
   ├─ Calls manager.collect_memory_event("delegate", {...})
   └─ Event recorded in memory

3. AGENT EXECUTION
   ├─ Agent processes task
   ├─ Agent writes thinking output → memory/thinking/
   ├─ Agent writes logs → memory/logs/
   └─ Metrics collected → memory/metrics/

4. TASK COMPLETION
   ├─ Agent returns HANDBACK
   ├─ Copies to memory/handbacks/task-001-handback.yaml
   ├─ Calls manager.collect_memory_event("handback", {...})
   └─ Event recorded in memory

5. SESSION AGGREGATION
   ├─ Orchestrator calls manager.aggregate_memory()
   ├─ SessionMemoryAggregator scans all subdirectories
   ├─ Builds comprehensive index.json
   ├─ Exports index.md (human-readable)
   └─ Exports summary.md (full report)

6. SESSION END
   ├─ Memory exported/archived
   ├─ index.json contains complete session history
   └─ All data persisted and portable
```

### Index Structure (index.json)

```json
{
  "session_id": "session-001",
  "created_at": "2025-05-24T11:00:00Z",
  "updated_at": "2025-05-24T12:30:00Z",
  "delegates": [
    {
      "task_id": "task-001",
      "timestamp": "2025-05-24T11:05:00Z",
      "role": "Engineer",
      "model": "claude-haiku-4.5",
      "effort": "high",
      "scope": "Implement authentication module",
      "status": "complete"
    },
    ...
  ],
  "handbacks": [
    {
      "task_id": "task-001",
      "timestamp": "2025-05-24T11:25:00Z",
      "status": "complete",
      "quality_score": 95,
      "tokens_used": 1200,
      "deliverables": ["src/auth.py", "tests/test_auth.py"]
    },
    ...
  ],
  "metrics": {
    "total_delegates": 10,
    "total_handbacks": 9,
    "completed_tasks": 9,
    "failed_tasks": 0,
    "escalated_tasks": 1,
    "total_tokens": 45000,
    "average_quality_score": 92.3,
    "total_logs": 15,
    "total_thinking_files": 10
  }
}
```

---

## Design Decisions

### 1. Why Artifact Directory (Not Copilot Memory)?

| Factor | Artifact Directory | Copilot Memory |
|--------|---|---|
| Control | ✅ Complete control | ❌ Limited by Copilot API |
| Portability | ✅ Copy any time | ❌ Tied to Copilot API |
| Offline | ✅ Works offline | ❌ Requires API |
| Scalability | ✅ Unlimited scale | ❌ API rate limits |
| Cost | ✅ Free (local storage) | ❌ Copilot API costs |
| Auditability | ✅ Full file access | ❌ Limited audit trail |
| Future | ✅ DB migration path | ❌ No clear roadmap |

### 2. Why File-Based (Not Database)?

**Current: File-Based (Phase 1-2)**
- Simple to understand and implement
- No database setup required
- Easy to backup and version control
- Works offline
- Great for development and testing

**Future: Database-Based (Phase 3+)**
- Better query performance (1000+ sessions)
- Cross-session analysis queries
- Advanced indexing and full-text search
- Streaming analytics support
- REST API for integration

**Migration path:** File API → DB backend (same interface)

### 3. Why Per-Session Isolation?

Each session has its own memory directory:

```
~/.agentic-engineers/
├── session-001/memory/    ← Isolated
├── session-002/memory/    ← Isolated
└── session-003/memory/    ← Isolated
```

**Rationale:**
- Clear ownership and boundaries
- Easy to archive/delete individual sessions
- No cross-session contamination
- Simple backup and recovery
- Clear audit trails per session

### 4. Why Separate Delegates and Handbacks?

```
memory/
├── delegates/   ← Task assignments
└── handbacks/   ← Task completions
```

**Rationale:**
- Different schemas (input vs. output)
- Different retention policies possible
- Clear separation of concerns
- Easy to query by phase
- Natural lifecycle mapping

---

## Integration Points

### How Agents Integrate

Agents write thinking output and logs to memory:

```python
# In agent code
import logging
from src.orchestration.memory import ArtifactMemoryStore

# Initialize logging to memory
store = ArtifactMemoryStore(session_id=os.environ["SESSION_ID"])
handler = logging.FileHandler(
    store.memory_dir / "logs" / f"{agent_name}.log"
)
logger.addHandler(handler)

# Write thinking output
store.write(f"thinking-{task_id}", thinking_output, subdir="thinking")
```

### How Skills Integrate

Skills that manage state write to memory:

```python
# In skill code
from src.orchestration.memory import ArtifactMemoryStore

store = ArtifactMemoryStore(session_id=os.environ.get("SESSION_ID", "default"))

# Record skill execution
store.write(f"skill-{task_id}", {
    "inputs": {...},
    "outputs": {...},
    "duration": elapsed_time,
}, subdir="metrics")
```

### How Orchestrator Integrates

```python
# In orchestrator
from src.orchestration.memory import SessionMemoryManager

class Orchestrator:
    def __init__(self, session_id):
        self.memory = SessionMemoryManager(session_id)
        self.memory.initialize(metadata={
            "started_at": datetime.utcnow().isoformat()
        })
    
    def delegate_task(self, task):
        # Route task...
        self.memory.collect_memory_event("delegate", {
            "task_id": task.id,
            "role": task.role,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def process_handback(self, handback):
        # Process result...
        self.memory.collect_memory_event("handback", {
            "task_id": handback.task_id,
            "status": handback.status,
            "quality_score": handback.quality_score,
        })
    
    def finalize_session(self):
        # End session
        self.memory.aggregate_memory()
        self.memory.export_summary()
```

---

## Performance Characteristics

### Disk Usage

| Item | Size | Count | Total |
|------|------|-------|-------|
| DELEGATE (avg) | 3 KB | 50 | 150 KB |
| HANDBACK (avg) | 5 KB | 50 | 250 KB |
| Logs | 100 KB | 10 | 1 MB |
| Thinking output | 50 KB | 5 | 250 KB |
| Metrics | 200 KB | 1 | 200 KB |
| **Total (typical)** | | | **2 MB** |

**Large session (500 tasks):** ~10-20 MB
**Archive (100 sessions):** ~200-400 MB

### Time Performance

| Operation | Typical Time |
|-----------|---|
| Initialize memory | <10ms |
| Collect event | <5ms |
| Aggregate (50 tasks) | 100-500ms |
| Aggregate (500 tasks) | 1-5s |
| Query by task_id | 1-5ms |
| Query by role | 10-50ms |

### Scalability

- ✅ Supports 1000+ tasks per session
- ✅ Supports 1000+ sessions total
- ✅ Queries remain fast (<100ms)
- ⚠️ Global index queries may slow at 10,000+ sessions (future: DB migration)

---

## Future Roadmap

### Phase 3: REST API Layer

```python
# Future: Access memory via HTTP API
GET /api/sessions/{session_id}/delegates
GET /api/sessions/{session_id}/handbacks?role=Engineer
GET /api/sessions/{session_id}/metrics
```

### Phase 4: Database Backend

```python
# Same API, database backend
# Seamless migration from file-based
store = SessionMemoryManager(session_id)  # Same interface
# Queries now use PostgreSQL
```

### Phase 5: Cross-Session Analytics

```python
# Query across all sessions
results = GlobalMemoryManager.query(
    role="Engineer",
    model="claude-haiku-4.5",
    date_range=("2025-05-01", "2025-05-31"),
)
```

---

## Best Practices

1. **Initialize at session start**
   ```python
   manager.initialize(metadata={"user": "alice"})
   ```

2. **Aggregate at session end**
   ```python
   manager.aggregate_memory()
   manager.export_summary()
   ```

3. **Query after aggregation**
   ```python
   # Always call aggregate_memory() first
   manager.aggregate_memory()
   delegates = manager.get_delegates()
   ```

4. **Archive old sessions**
   ```bash
   # Move to archive after 2 weeks
   mv ~/.agentic-engineers/old-session ~/.agentic-engineers/archive/
   ```

5. **Export for external analysis**
   ```bash
   # Copy memory for analysis or sharing
   cp -r ~/.agentic-engineers/session-001/memory ~/my-analysis/
   ```

---

## See Also

- [MEMORY-USAGE-GUIDE.md](MEMORY-USAGE-GUIDE.md) — How to use the system
- [MEMORY-DEVELOPER-REFERENCE.md](MEMORY-DEVELOPER-REFERENCE.md) — API reference
- [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md) — Migration from old systems
- [MEMORY-FAQ.md](MEMORY-FAQ.md) — Frequently asked questions
- `src/orchestration/memory/` — Implementation source code
- `tests/test_session_memory_integration.py` — Integration tests
