# Memory System Migration Guide

## Why Migrate?

The agentic-engineers memory system provides several advantages over previous approaches:

### Benefits of the New System

| Aspect | Copilot Memory | External Storage | **New Artifact System** |
|--------|---|---|---|
| **Centralized** | Scattered across API | Multiple locations | Single directory |
| **Portable** | API-dependent | Manual exports | Filesystem (trivial to move) |
| **Auditable** | Limited history | Partial logs | Complete audit trail |
| **Offline** | Requires API | Requires API | Works offline |
| **Queryable** | Limited API | Manual queries | Rich JSON/SQL |
| **Reliable** | Cloud dependent | Dependency varies | Local filesystem |
| **Cost** | Copilot API costs | Varies | Free (local storage) |
| **Future-proof** | Fixed schema | Rigid | DB migration path |

### Common Pain Points Solved

1. **Lost execution history** → Complete DELEGATE/HANDBACK archive
2. **Hard to debug failures** → Structured logs and reasoning output
3. **No audit trail** → Full timestamp history and state tracking
4. **Metrics scattered** → Centralized token usage and quality scores
5. **Session isolation issues** → Per-session isolated memory
6. **Cross-session analysis impossible** → Unified indexing and aggregation

---

## Migration Scenarios

### Scenario 1: New Installation (No Legacy Data)

If you're starting fresh, no migration needed:

```bash
# Memory is automatically created at first session
# No action required!
```

### Scenario 2: Migrating from Copilot Memory

If existing DELEGATEs/HANDBACKs are in Copilot memory, migrate to artifact dir:

```python
from pathlib import Path
import json
import yaml

# Find existing Copilot memory
copilot_memory_dir = Path("~/.copilot/memory").expanduser()
if not copilot_memory_dir.exists():
    print("No Copilot memory found")
    exit(1)

# Create new artifact directory
new_memory_dir = Path("~/.agentic-engineers/session-001/memory").expanduser()
new_memory_dir.mkdir(parents=True, exist_ok=True)

# Migrate delegate files
old_delegates = copilot_memory_dir / "delegates"
new_delegates = new_memory_dir / "delegates"
if old_delegates.exists():
    new_delegates.mkdir(exist_ok=True)
    for file in old_delegates.glob("*.yaml"):
        dest = new_delegates / file.name
        shutil.copy2(file, dest)
        print(f"Migrated: {file.name}")

# Migrate handback files
old_handbacks = copilot_memory_dir / "handbacks"
new_handbacks = new_memory_dir / "handbacks"
if old_handbacks.exists():
    new_handbacks.mkdir(exist_ok=True)
    for file in old_handbacks.glob("*.yaml"):
        dest = new_handbacks / file.name
        shutil.copy2(file, dest)
        print(f"Migrated: {file.name}")

print(f"\nMigration complete: {new_memory_dir}")
```

### Scenario 3: Migrating from External Storage

If metrics/logs are stored externally (`~/.claude/metrics`, database, etc.):

```python
from pathlib import Path
import shutil

# Map source to destination
migrations = [
    ("~/.claude/metrics", "~/.agentic-engineers/session-001/memory/metrics"),
    ("~/.claude/logs", "~/.agentic-engineers/session-001/memory/logs"),
    ("~/Documents/session-exports", "~/.agentic-engineers/archive"),
]

for src, dest in migrations:
    src_path = Path(src).expanduser()
    dest_path = Path(dest).expanduser()
    
    if src_path.exists():
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        print(f"Migrated: {src} → {dest}")
```

### Scenario 4: Incremental Migration (Dual System)

Run both systems in parallel until confident in new system:

```bash
# Keep old system running
export MEMORY_LEGACY_MODE=1

# Also write to new system
export MEMORY_NEW_LOCATION=~/.agentic-engineers/{session_id}/memory

# After validation period, disable legacy mode
export MEMORY_LEGACY_MODE=0
```

---

## Step-by-Step Migration Procedure

### Step 1: Backup Current Data

```bash
# Create full backup before migrating
mkdir -p ~/backups
DATE=$(date +%Y%m%d-%H%M%S)

# Backup Copilot memory
if [ -d ~/.copilot/memory ]; then
    tar -czf ~/backups/copilot-memory-$DATE.tar.gz ~/.copilot/memory
    echo "Backed up Copilot memory"
fi

# Backup other data sources
for location in ~/.claude/metrics ~/.claude/logs; do
    if [ -d "$location" ]; then
        tar -czf ~/backups/$(basename $location)-$DATE.tar.gz "$location"
        echo "Backed up $(basename $location)"
    fi
done
```

### Step 2: Initialize New Memory Structure

```bash
# Create artifact directories for all existing sessions
SESSION_IDS="session-001 session-002 session-003"

for sid in $SESSION_IDS; do
    mkdir -p ~/.agentic-engineers/$sid/memory/{delegates,handbacks,logs,thinking,metrics,usage}
    echo "Created memory dirs for $sid"
done
```

### Step 3: Migrate Data Files

```python
#!/usr/bin/env python3
"""Migrate memory from old locations to new artifact structure."""

from pathlib import Path
import shutil
import json
from typing import Dict, List

class MemoryMigrator:
    def __init__(self, session_ids: List[str]):
        self.session_ids = session_ids
        self.artifact_root = Path.home() / ".agentic-engineers"
        self.stats = {"migrated": 0, "skipped": 0, "errors": 0}
    
    def migrate_session(self, session_id: str):
        """Migrate all data for a single session."""
        print(f"\n=== Migrating {session_id} ===")
        
        # Try Copilot memory
        self._migrate_copilot(session_id)
        
        # Try legacy locations
        self._migrate_legacy(session_id)
        
        # Try database exports (if applicable)
        self._migrate_db_exports(session_id)
    
    def _migrate_copilot(self, session_id: str):
        """Migrate from ~/.copilot/memory"""
        src = Path.home() / ".copilot" / "memory"
        if not src.exists():
            return
        
        dest_root = self.artifact_root / session_id / "memory"
        
        # Migrate delegates
        delegates_src = src / "delegates"
        if delegates_src.exists():
            dest = dest_root / "delegates"
            dest.mkdir(parents=True, exist_ok=True)
            for file in delegates_src.glob("**/*.yaml"):
                shutil.copy2(file, dest / file.name)
                self.stats["migrated"] += 1
        
        # Migrate handbacks
        handbacks_src = src / "handbacks"
        if handbacks_src.exists():
            dest = dest_root / "handbacks"
            dest.mkdir(parents=True, exist_ok=True)
            for file in handbacks_src.glob("**/*.yaml"):
                shutil.copy2(file, dest / file.name)
                self.stats["migrated"] += 1
    
    def _migrate_legacy(self, session_id: str):
        """Migrate from ~/.claude/metrics, ~/.claude/logs, etc."""
        legacy_locations = {
            "~/.claude/metrics": "metrics",
            "~/.claude/logs": "logs",
            "~/.claude/thinking": "thinking",
        }
        
        dest_root = self.artifact_root / session_id / "memory"
        
        for src_pattern, dest_subdir in legacy_locations.items():
            src = Path(src_pattern).expanduser()
            if not src.exists():
                continue
            
            dest = dest_root / dest_subdir
            dest.mkdir(parents=True, exist_ok=True)
            
            for file in src.glob("**/*"):
                if file.is_file():
                    rel_path = file.relative_to(src)
                    dest_file = dest / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, dest_file)
                    self.stats["migrated"] += 1
    
    def _migrate_db_exports(self, session_id: str):
        """Migrate from database exports or JSON backups."""
        export_dir = Path.home() / "session-exports"
        if not export_dir.exists():
            return
        
        session_export = export_dir / f"{session_id}.json"
        if session_export.exists():
            dest = self.artifact_root / session_id / "memory" / "export.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(session_export, dest)
            self.stats["migrated"] += 1
    
    def run(self):
        """Run migration for all sessions."""
        print("Starting memory migration...\n")
        
        for session_id in self.session_ids:
            try:
                self.migrate_session(session_id)
            except Exception as e:
                print(f"ERROR migrating {session_id}: {e}")
                self.stats["errors"] += 1
        
        print(f"\n=== Migration Summary ===")
        print(f"Migrated: {self.stats['migrated']}")
        print(f"Skipped: {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")

if __name__ == "__main__":
    sessions = ["session-001", "session-002"]  # Update as needed
    migrator = MemoryMigrator(sessions)
    migrator.run()
```

### Step 4: Verify Migration

```bash
# Check all files migrated
for sid in session-001 session-002; do
    echo "=== $sid ==="
    find ~/.agentic-engineers/$sid/memory -type f | wc -l
    du -sh ~/.agentic-engineers/$sid/memory
done

# Compare with old locations
echo "=== Old Locations ==="
[ -d ~/.copilot/memory ] && du -sh ~/.copilot/memory
[ -d ~/.claude/metrics ] && du -sh ~/.claude/metrics
```

---

## Verification Steps

### Verify All Data Moved

```python
from pathlib import Path
from src.orchestration.memory import SessionMemoryManager

def verify_migration(session_id: str) -> bool:
    """Verify migration was successful."""
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    
    memory_dir = manager.memory_manager.memory_dir
    
    # Check directory exists
    if not memory_dir.exists():
        print(f"❌ Memory directory not found: {memory_dir}")
        return False
    
    # Check subdirectories
    required_dirs = ["delegates", "handbacks", "logs", "metrics"]
    for subdir in required_dirs:
        subdir_path = memory_dir / subdir
        if not subdir_path.exists():
            print(f"⚠️ Missing subdirectory: {subdir}")
        else:
            count = len(list(subdir_path.glob("*")))
            print(f"✅ {subdir}: {count} files")
    
    # Try aggregation
    try:
        index = manager.aggregate_memory()
        print(f"✅ Aggregation successful")
        print(f"   - Delegates: {index['summary']['total_delegates']}")
        print(f"   - Handbacks: {index['summary']['total_handbacks']}")
        return True
    except Exception as e:
        print(f"❌ Aggregation failed: {e}")
        return False

# Verify each session
for session_id in ["session-001", "session-002"]:
    print(f"\n=== Verifying {session_id} ===")
    success = verify_migration(session_id)
    if success:
        print("✅ Migration verified successfully")
    else:
        print("❌ Migration verification failed")
```

### Validate Data Integrity

```bash
# Check for duplicate files
find ~/.agentic-engineers -name "*.yaml" -o -name "*.json" | \
  while read file; do
    if [ -f "$file" ]; then
      # Verify valid YAML/JSON
      case "$file" in
        *.yaml) python3 -c "import yaml; yaml.safe_load(open('$file'))" ;;
        *.json) python3 -c "import json; json.load(open('$file'))" ;;
      esac
      [ $? -eq 0 ] && echo "✅ $file" || echo "❌ $file"
    fi
  done

# Compare file counts
echo "=== File Count Comparison ==="
echo "Old location:"
find ~/.copilot/memory -type f 2>/dev/null | wc -l
echo "New location:"
find ~/.agentic-engineers -type f 2>/dev/null | wc -l
```

---

## Rollback Procedure

If migration fails or causes issues, rollback to previous state:

### Quick Rollback (Within Same Session)

```bash
# If you just migrated, restore from backup
DATE=$(date +%Y%m%d)
BACKUP=~/backups/copilot-memory-$DATE*.tar.gz

# Stop current session
pkill orchestrator  # Stop any running processes

# Restore from backup
tar -xzf $BACKUP -C ~/

# Verify restoration
ls ~/.copilot/memory/

echo "✅ Rollback complete"
```

### Full Rollback (System-Wide)

```bash
#!/bin/bash
# Comprehensive rollback script

ARTIFACT_ROOT=~/.agentic-engineers
BACKUP_DATE=$1

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: ./rollback.sh YYYYMMDD"
    echo "Example: ./rollback.sh 20250524"
    exit 1
fi

# Backup new memory (for later inspection)
tar -czf ~/backups/new-memory-$BACKUP_DATE.tar.gz $ARTIFACT_ROOT

# Restore old memory
for backup in ~/backups/*-$BACKUP_DATE*.tar.gz; do
    tar -xzf "$backup" -C ~/
    echo "Restored: $backup"
done

# Verify restoration
if [ -d ~/.copilot/memory ]; then
    echo "✅ Rollback successful - old memory restored"
else
    echo "❌ Rollback failed - no old memory backup found"
    exit 1
fi
```

### Selective Rollback (Single Session)

```bash
# If only one session had issues
SESSION_ID=session-001
BACKUP_DATE=20250524

# Remove migrated data
rm -rf ~/.agentic-engineers/$SESSION_ID/memory

# Restore specific session from backup
tar -xzf ~/backups/copilot-memory-$BACKUP_DATE.tar.gz \
    -C ~/ \
    --wildcards "*/session-001/*"

echo "✅ Selective rollback complete for $SESSION_ID"
```

---

## Troubleshooting Migration Issues

### Issue: Migration script hangs or is slow

**Cause**: Large number of files or slow disk I/O

**Solution**:
```bash
# Increase buffer size for copy operations
export DD_BUFFER=16M

# Use parallel copy for faster migration
find ~/.copilot/memory -type f | \
  parallel --jobs 4 cp {} ~/.agentic-engineers/session-001/memory/{/}
```

### Issue: "Permission denied" errors during migration

**Cause**: File permissions not preserved

**Solution**:
```bash
# Ensure proper permissions
chmod -R u+rw ~/.agentic-engineers/

# For group access
chmod -R g+r ~/.agentic-engineers/

# Recursive fix for all files
find ~/.agentic-engineers -type f -exec chmod 644 {} \;
find ~/.agentic-engineers -type d -exec chmod 755 {} \;
```

### Issue: Migrated data not appearing in queries

**Cause**: Need to re-aggregate memory after migration

**Solution**:
```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")
manager.initialize()

# Force re-aggregation
import shutil
index_file = manager.memory_manager.memory_dir / "index.json"
if index_file.exists():
    index_file.unlink()  # Delete stale index

# Re-aggregate
manager.aggregate_memory()
manager.export_summary()
```

### Issue: Disk space exceeded during migration

**Cause**: Not enough free space for both old and new copies

**Solution**:
```bash
# Check available space
df -h ~/.

# Migrate in batches instead of all at once
# Or delete old location after successful verification
rm -rf ~/.copilot/memory  # After backup and verification!
```

---

## Environment Configuration After Migration

Update your environment to use new memory system:

```bash
# .bashrc or .zshrc
export AGENTIC_ENGINEERS_HOME=~/.agentic-engineers

# Optional: disable old Copilot memory
export COPILOT_MEMORY_DISABLED=1

# Optional: set default session ID
export SESSION_ID=session-001
```

---

## Testing Migration

Create a test session to verify the new system works:

```python
from src.orchestration.memory import SessionMemoryManager
from datetime import datetime

# Create test session
test_session = f"test-migration-{datetime.now().isoformat()}"

# Initialize
manager = SessionMemoryManager(test_session)
manager.initialize(metadata={"migrated": True})

# Simulate a task
manager.collect_memory_event("delegate", {
    "task_id": "test-001",
    "role": "Engineer",
    "timestamp": datetime.utcnow().isoformat(),
})

manager.collect_memory_event("handback", {
    "task_id": "test-001",
    "status": "complete",
    "quality_score": 100,
    "timestamp": datetime.utcnow().isoformat(),
})

# Aggregate and verify
index = manager.aggregate_memory()

print(f"✅ Test session created: {test_session}")
print(f"✅ Delegates: {len(index['delegates'])}")
print(f"✅ Handbacks: {len(index['handbacks'])}")
print(f"✅ Migration test successful!")
```

---

## Post-Migration Tasks

1. **Update documentation** - Point users to new memory location
2. **Update scripts** - Change any hardcoded paths to old locations
3. **Train team** - Ensure everyone knows about new system
4. **Monitor** - Watch for issues in first week
5. **Cleanup** - After verification period, delete old data

```bash
# After 2-week verification period, cleanup
rm -rf ~/.copilot/memory
rm -rf ~/.claude/metrics
rm -rf ~/.claude/logs

# Archive backups to cold storage
tar -czf ~/archive-backups.tar.gz ~/backups/
rm -rf ~/backups/

echo "✅ Cleanup complete"
```

---

## See Also

- [MEMORY-USAGE-GUIDE.md](MEMORY-USAGE-GUIDE.md) — How to use the memory system
- [MEMORY-ARCHITECTURE-OVERVIEW.md](MEMORY-ARCHITECTURE-OVERVIEW.md) — System design
- [MEMORY-FAQ.md](MEMORY-FAQ.md) — Frequently asked questions
