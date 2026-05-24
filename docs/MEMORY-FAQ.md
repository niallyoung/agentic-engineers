# Memory System FAQ

## General Questions

### Q: Why not just use Copilot memory?

**A:** Copilot memory has several limitations:

1. **API-dependent** - Requires network access and Copilot API
2. **Limited control** - Copilot API controls schema and retention
3. **Cost** - Uses Copilot API quota
4. **Scalability** - Rate limits on API calls
5. **Auditability** - Limited visibility into data storage
6. **Offline capability** - Doesn't work without API

The artifact directory system provides:
- ✅ Complete control over data
- ✅ Offline-first operation
- ✅ Unlimited scale (local filesystem)
- ✅ Full audit trails
- ✅ Future database migration path
- ✅ No API costs

**For specific Copilot memory needs:** You can still use Copilot memory alongside artifact storage—they're complementary, not exclusive.

---

### Q: What if I need Copilot memory for something specific?

**A:** The memory system is designed to be complementary:

```python
# Use Copilot memory for specific needs
import os
from copilot_api import get_memory

copilot_data = get_memory("my-key")

# Also store in artifact system
from src.orchestration.memory import ArtifactMemoryStore
store = ArtifactMemoryStore(os.environ["SESSION_ID"])
store.write("my-key", copilot_data, subdir="copilot-exports")
```

The artifact directory is the primary/authoritative system, but Copilot memory can supplement it for specific use cases.

---

### Q: Where should I look if I can't find my data?

**A:** Check these locations in order:

```bash
# 1. Session memory (primary)
ls ~/.agentic-engineers/{session_id}/memory/

# 2. Original locations (might still exist)
ls ~/.agentic-engineers/{session_id}/delegates/
ls ~/.agentic-engineers/{session_id}/handbacks/

# 3. Archive (old sessions)
ls ~/.agentic-engineers/archive/

# 4. Copilot memory (legacy)
ls ~/.copilot/memory/

# 5. External storage (legacy)
ls ~/.claude/metrics
```

If still not found:
```bash
# Global search
find ~/ -name "*.yaml" -type f 2>/dev/null | grep -i delegate
find ~/ -name "*.json" -type f 2>/dev/null | grep -i handback
```

---

## Storage & Retention

### Q: How long is memory kept?

**A:** Current default is **indefinite** (stored forever). Configuration options:

```bash
# Set retention policy (keep only last 90 days)
export MEMORY_RETENTION_DAYS=90

# Or configure manually
python -c "
from src.orchestration.memory import GlobalMemoryManager
gm = GlobalMemoryManager()
gm.cleanup_old_sessions(days=90)
"
```

**Archival strategy:**
- **Active sessions** (< 2 weeks): `~/.agentic-engineers/{session_id}/`
- **Recent sessions** (2-12 weeks): `~/.agentic-engineers/archive/{session_id}/`
- **Old sessions** (> 3 months): External archive (S3, tape, etc.)

### Q: How much disk space does memory use?

**A:** Typical sizes:

- Small session (10 tasks): ~1 MB
- Medium session (50 tasks): ~5 MB
- Large session (500 tasks): ~20 MB

```bash
# Check current usage
du -sh ~/.agentic-engineers/

# Archive old sessions to reduce size
tar -czf ~/archive/session-001.tar.gz ~/.agentic-engineers/session-001/
rm -rf ~/.agentic-engineers/session-001/
```

### Q: Can I delete old session memory?

**A:** Yes, but always backup first:

```bash
# Backup before deletion
tar -czf ~/backups/session-001-$(date +%Y%m%d).tar.gz \
    ~/.agentic-engineers/session-001/

# Delete
rm -rf ~/.agentic-engineers/session-001/
```

**Note:** Deletion is permanent once backup is deleted. Use archival for long-term retention.

---

## Querying & Analysis

### Q: Can I query memory programmatically?

**A:** Yes, the SessionMemoryManager provides a rich query API:

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

# Query by task ID
task = manager.query_by_task_id("task-001")

# Query by role
engineers = manager.query_by_role("Engineer")

# Filter
completed = manager.get_handbacks(status="complete")
failed = manager.get_handbacks(status="failed")

# Metrics
metrics = manager.get_metrics()
print(f"Completion rate: {metrics['completed_tasks']}/{metrics['total_delegates']}")
```

See [MEMORY-DEVELOPER-REFERENCE.md](MEMORY-DEVELOPER-REFERENCE.md) for complete API.

---

### Q: How do I export all session memory?

**A:** Several export options:

```bash
# 1. Export as archive
tar -czf session-001-export.tar.gz \
    ~/.agentic-engineers/session-001/memory/

# 2. Copy to external location
cp -r ~/.agentic-engineers/session-001/memory ~/exports/

# 3. Export index as JSON
cat ~/.agentic-engineers/session-001/memory/index.json | jq . > index.json

# 4. Export as CSV for analysis
python -c "
from src.orchestration.memory import SessionMemoryManager
import csv

manager = SessionMemoryManager('session-001')
manager.initialize()
manager.aggregate_memory()

with open('delegates.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=['task_id', 'role', 'status'])
    writer.writeheader()
    writer.writerows(manager.get_delegates())
"
```

### Q: Can I query across multiple sessions?

**A:** Not directly, but you can:

```python
from pathlib import Path
from src.orchestration.memory import SessionMemoryManager

# Query all sessions in a date range
sessions_dir = Path.home() / ".agentic-engineers"
all_metrics = {}

for session_dir in sessions_dir.glob("session-*"):
    session_id = session_dir.name
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    manager.aggregate_memory()
    
    metrics = manager.get_metrics()
    all_metrics[session_id] = metrics

# Analyze
total_tokens = sum(m["total_tokens"] for m in all_metrics.values())
print(f"Total tokens across all sessions: {total_tokens:,}")
```

**Future:** Database backend will support cross-session queries natively.

---

### Q: How do I find failed or escalated tasks?

**A:** Query by status:

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

# Get escalated tasks
escalated = manager.get_handbacks(status="escalated")
for handback in escalated:
    task_info = manager.query_by_task_id(handback["task_id"])
    delegate = task_info["delegates"][0]
    
    print(f"Escalated task: {handback['task_id']}")
    print(f"  Role: {delegate['role']}")
    print(f"  Reason: {handback.get('notes', 'N/A')}")
```

---

## Data Integrity

### Q: What happens if session is interrupted?

**A:** Memory is resilient to interruptions:

1. **Uncommitted events** - Lost (events not yet collected)
2. **Files written** - Persisted (delegates, handbacks, logs safe)
3. **index.json** - Stale (rebuild by calling aggregate_memory())

**Recovery:**

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("interrupted-session")
manager.initialize()

# Force re-aggregation (rebuilds index)
index = manager.aggregate_memory()

# Export summary
manager.export_summary()

# Verify recovered
print(f"Recovered: {len(index['delegates'])} delegates")
```

### Q: Is memory encrypted?

**A:** Currently:
- **At rest**: Uses filesystem permissions (same as user data)
- **In transit**: N/A (local filesystem, no network)
- **In memory**: Python objects (unencrypted)

**Future options:**
```python
# Planned: Encryption at rest
from src.orchestration.memory import EncryptedMemoryStore
store = EncryptedMemoryStore(
    session_id="session-001",
    cipher="AES-256",
    key_file="~/.agentic-engineers/keys/session-001.key"
)
```

**For sensitive data:** Store in encrypted filesystem or use OS-level encryption.

### Q: Can I share session memory?

**A:** Yes! All memory files are portable:

```bash
# Share entire session
tar -czf session-001.tar.gz \
    ~/.agentic-engineers/session-001/memory/
    
# Send via email, cloud storage, etc.
# Recipient can extract:
tar -xzf session-001.tar.gz -C ~/.agentic-engineers/

# Query shared memory
python -c "
from src.orchestration.memory import SessionMemoryManager
manager = SessionMemoryManager('session-001')
manager.initialize()
manager.aggregate_memory()
print(manager.get_metrics())
"
```

**Security note:** Memory contains full task details and outputs. Review before sharing.

---

## Integration & Migration

### Q: How do I add memory to a new agent?

**A:** Three steps:

1. **Log to memory**
   ```python
   from src.orchestration.memory import ArtifactMemoryStore
   import logging
   
   store = ArtifactMemoryStore(os.environ["SESSION_ID"])
   handler = logging.FileHandler(
       store.memory_dir / "logs" / "my-agent.log"
   )
   logger.addHandler(handler)
   ```

2. **Write thinking output**
   ```python
   store.write(f"thinking-{task_id}", {
       "reasoning": "...",
       "decision": "...",
   }, subdir="thinking")
   ```

3. **Record metrics**
   ```python
   store.append_metric("execution", {
       "task_id": task_id,
       "duration": elapsed_time,
       "success": True,
   }, subdir="metrics")
   ```

See [MEMORY-DEVELOPER-REFERENCE.md](MEMORY-DEVELOPER-REFERENCE.md) for full examples.

---

### Q: How do I migrate from old memory system?

**A:** Step-by-step:

```bash
# 1. Backup
mkdir ~/backup && cp -r ~/.copilot/memory ~/backup/

# 2. Migrate
python -c "
from pathlib import Path
import shutil

src = Path.home() / '.copilot' / 'memory'
dest = Path.home() / '.agentic-engineers' / 'session-001' / 'memory'
dest.mkdir(parents=True, exist_ok=True)

for subdir in ['delegates', 'handbacks', 'logs']:
    (dest / subdir).mkdir(exist_ok=True)
    for file in (src / subdir).glob('*'):
        shutil.copy2(file, dest / subdir / file.name)
"

# 3. Verify
python -c "
from src.orchestration.memory import SessionMemoryManager
manager = SessionMemoryManager('session-001')
manager.initialize()
manager.aggregate_memory()
print(manager.get_metrics())
"
```

See [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md) for detailed migration steps.

---

### Q: What if migration fails?

**A:** Rollback to previous state:

```bash
# Restore from backup
rm -rf ~/.agentic-engineers/
tar -xzf ~/backup-before-migration.tar.gz -C ~/

# Or restore specific session
rm -rf ~/.agentic-engineers/session-001/
tar -xzf session-001-backup.tar.gz -C ~/.agentic-engineers/
```

See [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md#rollback-procedure) for rollback procedures.

---

## Future Development

### Q: What's the future of memory?

**A:** Planned phases:

**Phase 3: REST API Layer**
```python
# Future: Access memory via HTTP
GET /api/sessions/{session_id}/delegates
GET /api/sessions/{session_id}/handbacks?role=Engineer
GET /api/sessions/{session_id}/metrics
```

**Phase 4: Database Backend**
```python
# Same Python API, database backend
manager = SessionMemoryManager("session-001")
# Transparently uses PostgreSQL instead of files
delegates = manager.get_delegates()
```

**Phase 5: Cross-Session Analytics**
```python
# Query across all sessions
results = GlobalMemoryManager.query(
    role="Engineer",
    date_range=("2025-05-01", "2025-05-31"),
)
```

### Q: Will file API break when DB is added?

**A:** No! Backward compatibility is guaranteed:

```python
# This code works today with files
# and will work with database tomorrow
manager = SessionMemoryManager("session-001")
manager.aggregate_memory()
delegates = manager.get_delegates()
```

The API stays the same; storage backend changes transparently.

---

## Troubleshooting

### Q: Memory index is empty

**Cause:** `aggregate_memory()` not called

**Solution:**
```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()  # ← Required!
delegates = manager.get_delegates()
```

---

### Q: Queries return no results

**Cause:** 
- Role name mismatch
- Task ID case sensitivity
- Memory not aggregated

**Solution:**
```python
# Check available data
manager.aggregate_memory()

# List all roles
for delegate in manager.get_delegates():
    print(delegate["role"])

# Exact case-sensitive search
result = manager.query_by_task_id("task-001")
assert result is not None
```

---

### Q: "Permission denied" errors

**Cause:** File permissions not set correctly

**Solution:**
```bash
# Fix permissions
chmod -R u+rwX ~/.agentic-engineers/

# For group access
chmod -R g+rX ~/.agentic-engineers/
```

---

### Q: Memory directory not found

**Cause:** Not initialized

**Solution:**
```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")
manager.initialize()  # ← Creates directories
```

---

### Q: Disk space exceeded

**Cause:** Large sessions or many sessions

**Solution:**
```bash
# Check usage
du -sh ~/.agentic-engineers/

# Archive old sessions
mkdir -p ~/.agentic-engineers/archive/
mv ~/.agentic-engineers/old-session-* ~/.agentic-engineers/archive/

# Compress archive
tar -czf ~/backups/archive-$(date +%Y%m%d).tar.gz \
    ~/.agentic-engineers/archive/

# Delete uncompressed
rm -rf ~/.agentic-engineers/archive/
```

---

## Performance

### Q: How fast are queries?

**A:** Typical query times:

- Query by task ID: **1-5 ms**
- Query by role: **10-50 ms**
- Full aggregation (50 tasks): **100-500 ms**
- Full aggregation (500 tasks): **1-5 seconds**

For large sessions, consider caching:

```python
# Cache aggregation results
index = manager.aggregate_memory()
delegates = index["delegates"]  # No re-aggregation
```

---

### Q: How can I speed up queries?

**A:** Best practices:

1. **Aggregate once**
   ```python
   index = manager.aggregate_memory()
   # Reuse index instead of re-querying
   delegates = index["delegates"]
   ```

2. **Use filters**
   ```python
   # Efficient: filters applied during aggregation
   engineers = manager.get_delegates(role="Engineer")
   ```

3. **Archive old sessions**
   ```bash
   # Reduces active memory size
   mv ~/.agentic-engineers/old-session ~/.agentic-engineers/archive/
   ```

---

## Getting Help

### Q: Where can I find more information?

**A:** Documentation:

- **User Guide**: [MEMORY-USAGE-GUIDE.md](MEMORY-USAGE-GUIDE.md)
- **Architecture**: [MEMORY-ARCHITECTURE-OVERVIEW.md](MEMORY-ARCHITECTURE-OVERVIEW.md)
- **API Reference**: [MEMORY-DEVELOPER-REFERENCE.md](MEMORY-DEVELOPER-REFERENCE.md)
- **Migration**: [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md)
- **Source Code**: `src/orchestration/memory/`
- **Tests**: `tests/test_artifact_memory.py`

---

### Q: How do I report bugs or request features?

**A:** Contact your team or create an issue:

```bash
# Check if issue exists
gh issue list --search "memory"

# Create new issue
gh issue create --title "Memory system bug" --body "..."

# Reference documentation
# Include: error message, session ID, steps to reproduce
```

---

## See Also

- [MEMORY-USAGE-GUIDE.md](MEMORY-USAGE-GUIDE.md) — How to use memory
- [MEMORY-ARCHITECTURE-OVERVIEW.md](MEMORY-ARCHITECTURE-OVERVIEW.md) — System design
- [MEMORY-DEVELOPER-REFERENCE.md](MEMORY-DEVELOPER-REFERENCE.md) — API reference
- [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md) — Migration from old systems
