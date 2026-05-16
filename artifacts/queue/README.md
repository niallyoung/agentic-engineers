# Queue Directory Structure & Retention Policy

## Directory Layout

```
artifacts/queue/
├── incoming/      # New DELEGATEs waiting for orchestrator routing
├── processing/    # DELEGATEs assigned to agents; HANDBACKs awaiting QE review
├── archive/       # Completed tasks (older than retention window)
└── README.md      # This file
```

## Retention Policy

### `incoming/` Directory
- **Purpose**: Holds new DELEGATE files that haven't been routed yet
- **Retention**: Active queue only
- **Cleanup**: Files moved to `archive/` after processing completion
- **Lifecycle**: DELEGATE → processing/ → archive/

### `processing/` Directory
- **Purpose**: Holds DELEGATEs currently assigned to agents and HANDBACKs awaiting QE review
- **Retention**: Until Quality Engineer reviews and approves
- **Cleanup**: Moved to `archive/` after QE approval
- **Lifecycle**: DELEGATE (routed) → HANDBACK (returned) → archive/

### `archive/` Directory
- **Purpose**: Historical record of completed tasks
- **Retention**: 90 days (configurable)
- **Cleanup**: Automated cleanup script removes files older than retention window
- **Archival**: Can be compressed to `.tar.gz` for long-term storage

## File Naming Convention

```
YYYY-MM-DD-<task-type>-<description>.yaml
```

Example: `2026-05-16-harness-implementation-comprehensive.yaml`

## Automated Cleanup

To clean up archived files older than 90 days:

```bash
find artifacts/queue/archive -type f -mtime +90 -delete
```

Or with compression:

```bash
# Archive to tar.gz before deletion
tar czf artifacts/queue/archive-$(date +%Y%m%d).tar.gz artifacts/queue/archive/
rm -rf artifacts/queue/archive/*
```

## Queue Protocol Reference

See `docs/QUEUE-PROTOCOL.md` for complete DELEGATE/HANDBACK specification.

---
**Last Updated**: 2026-05-16
**Policy Version**: 1.0
