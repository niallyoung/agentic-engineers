# Memory System Usage Guide

## What is the Memory System?

The agentic-engineers memory system provides a centralized, portable, file-based storage for all session data. Every task executed—from DELEGATEs (task assignments) to HANDBACKs (task completions)—is automatically captured and organized for analysis, debugging, and auditing.

**Key benefits:**
- **Centralized**: All session data in one structured location
- **Portable**: Move entire sessions between machines or environments
- **Auditable**: Complete history of task lifecycle and decisions
- **Queryable**: Search and analyze memory programmatically
- **Offline-capable**: Works without external APIs or cloud dependencies
- **Persistent**: Survives session restarts and machine reboots

The memory system operates transparently—you don't need to manually save anything. Every DELEGATE, HANDBACK, log, and metric is automatically collected and aggregated at session end.

---

## Where is Memory Stored?

All session memory is stored in the artifact directory:

```
~/.agentic-engineers/
├── {session_id}/
│   ├── memory/
│   │   ├── delegates/         # DELEGATE task assignments (copies)
│   │   ├── handbacks/         # HANDBACK task completions (copies)
│   │   ├── logs/              # Execution logs from agents
│   │   ├── thinking/          # Agent reasoning output
│   │   ├── metrics/           # Token usage, timing, quality scores
│   │   │   └── daily/         # Daily aggregated metrics
│   │   ├── usage/             # Token usage tracking
│   │   ├── tokenadvisor/      # Analysis results
│   │   ├── index.json         # Machine-readable session index
│   │   ├── index.md           # Human-readable index
│   │   └── summary.md         # Session summary report
│   ├── delegates/             # Original DELEGATE files
│   └── handbacks/             # Original HANDBACK files
└── archive/                   # Archived old sessions
```

**Environment Variables:**
- `AGENTIC_ENGINEERS_HOME`: Override default location (default: `~/.agentic-engineers`)
- `SESSION_ID`: Current session ID (automatically set by orchestrator)

**Finding your session:**
```bash
# List all sessions
ls ~/.agentic-engineers/

# View memory for specific session
ls ~/.agentic-engineers/session-001/memory/

# Find most recent session
ls -lt ~/.agentic-engineers/ | head -5
```

---

## Accessing Session Memory Files

### View Memory Index (Machine-Readable)

The `index.json` file contains complete aggregated metadata:

```bash
# View full index
cat ~/.agentic-engineers/session-001/memory/index.json | jq .

# View delegates only
cat ~/.agentic-engineers/session-001/memory/index.json | jq '.delegates'

# View handbacks only
cat ~/.agentic-engineers/session-001/memory/index.json | jq '.handbacks'

# View metrics summary
cat ~/.agentic-engineers/session-001/memory/index.json | jq '.summary'
```

### View Memory Index (Human-Readable)

The `index.md` file provides a formatted summary:

```bash
# View summary in Markdown
cat ~/.agentic-engineers/session-001/memory/index.md

# View with pager
less ~/.agentic-engineers/session-001/memory/index.md
```

### View Session Summary Report

```bash
# View comprehensive summary
cat ~/.agentic-engineers/session-001/memory/summary.md
```

### Access Individual Records

```bash
# List all DELEGATEs
ls ~/.agentic-engineers/session-001/memory/delegates/

# View specific DELEGATE
cat ~/.agentic-engineers/session-001/memory/delegates/task-001.yaml

# List all HANDBACKs
ls ~/.agentic-engineers/session-001/memory/handbacks/

# View specific HANDBACK
cat ~/.agentic-engineers/session-001/memory/handbacks/task-001-handback.yaml

# View execution logs
ls ~/.agentic-engineers/session-001/memory/logs/
cat ~/.agentic-engineers/session-001/memory/logs/agent-001.log

# View metrics
ls ~/.agentic-engineers/session-001/memory/metrics/
cat ~/.agentic-engineers/session-001/memory/metrics/session-metrics.jsonl
```

---

## Querying Memory Programmatically

The SessionMemoryManager API provides typed queries for accessing memory:

### Python API

```python
from src.orchestration.memory import SessionMemoryManager

# Initialize manager for a session
manager = SessionMemoryManager(session_id="session-001")
manager.initialize()

# Aggregate all memory (call once per session)
manager.aggregate_memory()

# Query delegates
delegates = manager.get_delegates()
for delegate in delegates:
    print(f"Task: {delegate['task_id']}, Role: {delegate['role']}")

# Query handbacks
handbacks = manager.get_handbacks()
for handback in handbacks:
    print(f"Task: {handback['task_id']}, Status: {handback['status']}")

# Query by task ID
task_info = manager.query_by_task_id("task-001")
print(f"Delegates: {len(task_info['delegates'])}")
print(f"Handbacks: {len(task_info['handbacks'])}")

# Query by role
role_info = manager.query_by_role("Engineer")
print(f"Engineer tasks: {role_info['count']}")

# Get metrics
metrics = manager.get_metrics()
print(f"Total tokens: {metrics['total_tokens']:,}")
print(f"Avg quality: {metrics['average_quality_score']:.1f}/100")
print(f"Completed tasks: {metrics['completed_tasks']}")
```

### Common Query Patterns

**Pattern 1: Find all tasks by a specific role**
```python
manager.initialize()
manager.aggregate_memory()

role_info = manager.query_by_role("Senior Engineer")
for delegate in role_info['delegates']:
    print(f"Task ID: {delegate['task_id']}")
    print(f"  Scope: {delegate['scope']}")
    print(f"  Model: {delegate['model']}")
```

**Pattern 2: Analyze task completion rates**
```python
manager.initialize()
manager.aggregate_memory()

delegates = manager.get_delegates()
handbacks = manager.get_handbacks()

completion_rate = len(handbacks) / len(delegates) * 100 if delegates else 0
print(f"Completion rate: {completion_rate:.1f}%")
```

**Pattern 3: Find failed or escalated tasks**
```python
manager.initialize()
manager.aggregate_memory()

handbacks = manager.get_handbacks(status="escalated")
for handback in handbacks:
    task_info = manager.query_by_task_id(handback['task_id'])
    delegate = task_info['delegates'][0]
    print(f"Task: {handback['task_id']}")
    print(f"  Role: {delegate['role']}")
    print(f"  Reason: {handback.get('notes', 'N/A')}")
```

**Pattern 4: Calculate token efficiency by role**
```python
manager.initialize()
manager.aggregate_memory()

roles = set()
for delegate in manager.get_delegates():
    roles.add(delegate['role'])

for role in roles:
    role_info = manager.query_by_role(role)
    total_tokens = sum(
        h.get('tokens_used', 0) 
        for h in role_info.get('handbacks', [])
    )
    count = role_info['count']
    avg_tokens = total_tokens / count if count > 0 else 0
    print(f"{role}: {avg_tokens:.0f} tokens/task")
```

---

## Exporting Memory for Analysis

### Export to JSON

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
manager.initialize()
manager.aggregate_memory()

# Get full index as JSON
import json
index = manager.memory_manager.load_index()
with open("session-export.json", "w") as f:
    json.dump(index, f, indent=2)
```

### Export to CSV

```python
import csv
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
manager.initialize()
manager.aggregate_memory()

# Export delegates to CSV
delegates = manager.get_delegates()
with open("delegates.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["task_id", "role", "model", "effort"])
    writer.writeheader()
    writer.writerows(delegates)

# Export handbacks to CSV
handbacks = manager.get_handbacks()
with open("handbacks.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f, 
        fieldnames=["task_id", "status", "quality_score", "tokens_used"]
    )
    writer.writeheader()
    writer.writerows(handbacks)
```

### Export to Archive

```bash
# Copy entire session memory to external location
cp -r ~/.agentic-engineers/session-001/memory ~/session-exports/session-001-backup/

# Create compressed archive
tar -czf ~/session-exports/session-001.tar.gz \
    ~/.agentic-engineers/session-001/memory/

# Export to cloud (example: S3)
aws s3 cp ~/.agentic-engineers/session-001/memory/ \
    s3://my-bucket/session-archives/session-001/ \
    --recursive
```

---

## Common Use Cases

### Use Case 1: Debugging a Failed Task

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
manager.initialize()
manager.aggregate_memory()

# Find the failed task
task_info = manager.query_by_task_id("task-001")

# Get the DELEGATE
delegate = task_info['delegates'][0]
print(f"Task: {delegate['task_id']}")
print(f"Role: {delegate['role']}")
print(f"Scope: {delegate['scope']}")

# Get the HANDBACK
if task_info['handbacks']:
    handback = task_info['handbacks'][0]
    print(f"Status: {handback['status']}")
    print(f"Notes: {handback.get('notes', 'N/A')}")
    
    # Find related logs
    import glob
    logs = glob.glob(
        f"~/.agentic-engineers/session-001/memory/logs/*task-001*"
    )
    for log_file in logs:
        print(f"\nLog: {log_file}")
        with open(log_file) as f:
            print(f.read()[-1000:])  # Last 1000 chars
```

### Use Case 2: Performance Analysis

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
manager.initialize()
manager.aggregate_memory()

# Get metrics
metrics = manager.get_metrics()

print(f"=== Session Performance ===")
print(f"Total tasks: {metrics['total_delegates']}")
print(f"Completed: {metrics['completed_tasks']}")
print(f"Failed: {metrics['failed_tasks']}")
print(f"Success rate: {metrics['completed_tasks']/metrics['total_delegates']*100:.1f}%")
print(f"\nTotal tokens: {metrics['total_tokens']:,}")
print(f"Avg quality: {metrics['average_quality_score']:.1f}/100")
print(f"Tokens/task: {metrics['total_tokens']/metrics['total_delegates']:.0f}")
```

### Use Case 3: Audit Trail

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
manager.initialize()
manager.aggregate_memory()

# Generate audit trail
print("=== Audit Trail ===")
delegates = manager.get_delegates()
for delegate in sorted(delegates, key=lambda d: d['timestamp']):
    task_info = manager.query_by_task_id(delegate['task_id'])
    handback = task_info['handbacks'][0] if task_info['handbacks'] else None
    
    print(f"\n{delegate['timestamp']}: DELEGATE task-{delegate['task_id']}")
    print(f"  Role: {delegate['role']}")
    print(f"  Scope: {delegate['scope'][:80]}...")
    
    if handback:
        print(f"\n{handback['timestamp']}: HANDBACK task-{delegate['task_id']}")
        print(f"  Status: {handback['status']}")
        print(f"  Quality: {handback['quality_score']}/100")
```

### Use Case 4: Model/Cost Analysis

```python
from collections import defaultdict
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
manager.initialize()
manager.aggregate_memory()

# Analyze by model
model_stats = defaultdict(lambda: {"count": 0, "total_tokens": 0, "quality": []})

for delegate in manager.get_delegates():
    model = delegate['model']
    model_stats[model]["count"] += 1
    
    task_info = manager.query_by_task_id(delegate['task_id'])
    if task_info['handbacks']:
        handback = task_info['handbacks'][0]
        model_stats[model]["total_tokens"] += handback.get('tokens_used', 0)
        model_stats[model]["quality"].append(handback.get('quality_score', 0))

print("=== Model Analysis ===")
for model, stats in sorted(model_stats.items()):
    avg_tokens = stats["total_tokens"] / stats["count"]
    avg_quality = sum(stats["quality"]) / len(stats["quality"]) if stats["quality"] else 0
    print(f"\n{model}")
    print(f"  Tasks: {stats['count']}")
    print(f"  Avg tokens: {avg_tokens:.0f}")
    print(f"  Avg quality: {avg_quality:.1f}/100")
```

---

## Environment Variables

Control memory behavior via environment variables:

```bash
# Set custom memory root
export AGENTIC_ENGINEERS_HOME=/custom/path/.agentic-engineers

# Set session ID
export SESSION_ID=my-session-001

# Enable debug logging
export MEMORY_DEBUG=1

# Override metrics directory
export MEMORY_METRICS_DIR=/custom/metrics/path

# Configure retention (days, default: indefinite)
export MEMORY_RETENTION_DAYS=90
```

---

## Best Practices

1. **Initialize at session start**
   ```python
   manager = SessionMemoryManager("session-001")
   manager.initialize(metadata={"user": "alice", "project": "api"})
   ```

2. **Aggregate at session end**
   ```python
   manager.aggregate_memory()
   manager.export_summary()
   ```

3. **Query after aggregation**
   - Always call `aggregate_memory()` before querying
   - Queries are read-only and don't modify memory

4. **Archive old sessions**
   ```bash
   # Move completed sessions to archive
   mv ~/.agentic-engineers/old-session-001 ~/.agentic-engineers/archive/
   ```

5. **Export for sharing**
   - Memory is file-based and portable
   - Safe to copy or share entire session directory
   - No authentication or credentials in memory files

---

## Troubleshooting

**Q: Memory directory not found**
```bash
# Create if missing
mkdir -p ~/.agentic-engineers/{session_id}/memory/{delegates,handbacks,logs,thinking,metrics}
```

**Q: Index.json is empty**
```python
# Make sure to call aggregate_memory()
manager.initialize()
manager.aggregate_memory()  # Required before querying
```

**Q: Queries return no results**
- Check task IDs are correct (case-sensitive)
- Verify role names match exactly
- Ensure aggregate_memory() was called

**Q: Memory files too large**
```bash
# Check size
du -sh ~/.agentic-engineers/session-001/memory/

# Archive old sessions to reduce size
tar -czf ~/archive/session-001.tar.gz ~/.agentic-engineers/session-001/
rm -rf ~/.agentic-engineers/session-001/
```

---

## See Also

- [MEMORY-ARCHITECTURE-OVERVIEW.md](MEMORY-ARCHITECTURE-OVERVIEW.md) — System design and data flow
- [MEMORY-DEVELOPER-REFERENCE.md](MEMORY-DEVELOPER-REFERENCE.md) — API reference for developers
- [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md) — How to migrate existing data
- [MEMORY-FAQ.md](MEMORY-FAQ.md) — Frequently asked questions
