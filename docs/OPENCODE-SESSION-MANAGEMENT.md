# OpenCode Session Management Guide

## Overview

OpenCode now supports **session-scoped work isolation** through the `HarnessSessionManager` class. This enables:

- **Concurrent sessions**: Multiple OpenCode windows can work independently without interfering
- **Per-harness tracking**: Monitor work by harness type (OpenCode, Copilot, Claude Code, Pi.dev)
- **Metrics per session**: Track tokens, costs, and quality separately for each session
- **Security gates**: Enforce permissions per harness type

## Canonical Queue Path Format

All work routes through canonical queue paths:

```
~/.agentic-engineers/{harness}/{session-id}/queue/
├── incoming/    # New DELEGATEs waiting for pickup
├── processing/  # Tasks currently executing
├── done/        # Completed tasks (HANDBACKs)
├── failed/      # Failed tasks
└── ../metadata.json
```

**Example paths:**

```
# OpenCode session #1
~/.agentic-engineers/a1b2c3d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p/opencode/queue/

# Copilot session #2
~/.agentic-engineers/z9y8x7w6-v5u4-3t2s-1r0q-p9o8n7m6l5k/copilot/queue/

# Claude Code session #3
~/.agentic-engineers/f1e2d3c4-b5a6-7z8y-9x0w-v1u2t3s4r5q/claude-code/queue/
```

## Quick Start

### 1. Automatic Detection (Environment Variables)

OpenCode automatically detects harness type and session ID from environment:

```python
from src.opencode.harness_session_manager import HarnessSessionManager

# Create manager from environment variables
mgr = HarnessSessionManager.from_env()

# Initialize queue structure
result = mgr.initialize_queue_structure()
if result["success"]:
    print(f"Queue initialized: {result['queue_root']}")
    print(f"Session: {mgr.session_id}")
    print(f"Harness: {mgr.harness}")
```

### 2. CLI Arguments (Override Environment)

For explicit control, use CLI arguments:

```python
from src.opencode.harness_session_manager import HarnessSessionManager

# Create manager from CLI arguments (overrides env vars)
mgr = HarnessSessionManager.from_cli_args(
    harness="opencode",
    session_id="my-custom-session-id"
)

# Initialize queue
mgr.initialize_queue_structure()
```

### 3. Manual Creation (Full Control)

For tests or special cases:

```python
from src.opencode.harness_session_manager import HarnessSessionManager

# Create with explicit values
mgr = HarnessSessionManager(
    harness="opencode",
    session_id="test-session-123"
)

# Initialize queue
mgr.initialize_queue_structure()
```

## Environment Variables

The manager respects these environment variables (in priority order):

### Harness Detection

| Variable | Value | Detected As |
|----------|-------|-------------|
| `AGENTIC_HARNESS` | `opencode` | `opencode` |
| `OPENCODE_API` | Any non-empty | `opencode` |
| `CLAUDE_SESSION_ID` | Any non-empty | `claude-code` |
| `COPILOT_SESSION_ID` | Any non-empty | `copilot` |
| *(none)* | - | `local` (fallback) |

### Session ID Detection

| Variable | Value | Used As |
|----------|-------|---------|
| `AGENTIC_SESSION_ID` | UUID or string | Explicit session ID |
| `OPENCODE_SESSION_ID` | UUID or string | Session ID |
| `CLAUDE_SESSION_ID` | UUID or string | Session ID |
| `COPILOT_SESSION_ID` | UUID or string | Session ID |
| *(none)* | - | Generate new UUID |

## Supported Harnesses

The manager validates harness type against:

```python
HarnessSessionManager.SUPPORTED_HARNESSES == {
    "opencode",      # OpenCode CLI harness
    "copilot",       # GitHub Copilot
    "claude-code",   # Claude.ai Code interface
    "pi-dev",        # Pi.dev harness
    "local",         # Local development / fallback
}
```

## API Reference

### `HarnessSessionManager`

Main class for session management.

#### Factory Methods

```python
@classmethod
def from_env(*, base_dir: Optional[Path] = None) -> HarnessSessionManager
    """Create manager by detecting harness and session from environment."""

@classmethod
def from_cli_args(
    harness: Optional[str] = None,
    session_id: Optional[str] = None,
    *,
    base_dir: Optional[Path] = None
) -> HarnessSessionManager
    """Create manager from CLI arguments (overrides environment)."""
```

#### Constructor

```python
def __init__(
    harness: str,
    session_id: str,
    *,
    base_dir: Optional[Path] = None
) -> None
    """
    Initialize with explicit harness and session ID.
    
    Raises:
        ValueError: if harness not in SUPPORTED_HARNESSES
    """
```

#### Properties

```python
@property
def base_dir() -> Path
    """Base directory (~/.agentic-engineers/)."""

@property
def queue_root() -> Path
    """Canonical queue root path (/.../session/{harness}/{session-id}/queue/)."""

@property
def harness_root() -> Path
    """Harness root directory (parent of queue/)."""

@property
def metadata_path() -> Path
    """Path to metadata.json for this session/harness."""

@property
def metadata() -> dict
    """Cached metadata dict (populated after initialize_queue_structure)."""
```

#### Methods

```python
def initialize_queue_structure() -> dict
    """
    Create canonical queue directory structure (idempotent).
    
    Returns dict:
        {
            "success": bool,
            "session_id": str,
            "harness": str,
            "queue_root": str,
            "metadata_path": str,
            "subdirs": {"incoming": ..., "processing": ..., ...}
        }
    """

def validate_queue_structure() -> tuple[bool, str]
    """
    Validate queue structure exists and is canonical.
    
    Returns:
        (is_valid, message)
    """

def to_dict() -> dict
    """Export manager state as dict."""
```

## Examples

### Example 1: Initialization in OpenCode Harness

```python
# In OpenCode harness startup code
from src.opencode.harness_session_manager import HarnessSessionManager

def initialize_opencode():
    # Detect harness and session from environment
    mgr = HarnessSessionManager.from_env()
    
    # Initialize canonical queue structure
    result = mgr.initialize_queue_structure()
    if not result["success"]:
        raise RuntimeError(f"Failed to initialize queue: {result['error']}")
    
    # Store for later use
    QUEUE_ROOT = mgr.queue_root
    SESSION_ID = mgr.session_id
    
    return {
        "queue_root": QUEUE_ROOT,
        "session_id": SESSION_ID,
        "incoming": QUEUE_ROOT / "incoming",
        "processing": QUEUE_ROOT / "processing",
        "done": QUEUE_ROOT / "done",
        "failed": QUEUE_ROOT / "failed",
    }
```

### Example 2: Multiple Concurrent Sessions

```python
from src.opencode.harness_session_manager import HarnessSessionManager

# OpenCode window #1 (auto-detects session from OPENCODE_SESSION_ID)
mgr1 = HarnessSessionManager.from_env()
mgr1.initialize_queue_structure()
print(f"Window 1 queue: {mgr1.queue_root}")

# OpenCode window #2 (with different session ID)
mgr2 = HarnessSessionManager.from_env()
mgr2.initialize_queue_structure()
print(f"Window 2 queue: {mgr2.queue_root}")

# Queues are completely isolated
assert mgr1.queue_root != mgr2.queue_root
```

### Example 3: Validation Before Starting

```python
from src.opencode.harness_session_manager import HarnessSessionManager

mgr = HarnessSessionManager.from_env()

# Check if queue structure exists and is valid
is_valid, msg = mgr.validate_queue_structure()
if not is_valid:
    # Initialize if not valid
    result = mgr.initialize_queue_structure()
    if result["success"]:
        print(f"Queue initialized: {result['queue_root']}")
    else:
        raise RuntimeError(result["error"])
else:
    print(msg)  # "Queue structure is valid: /.../queue"
```

### Example 4: Work with Specific Session

```python
from src.opencode.harness_session_manager import HarnessSessionManager
from pathlib import Path

# Create manager for specific session
mgr = HarnessSessionManager.from_cli_args(
    harness="opencode",
    session_id="my-important-session-123"
)

# Initialize queue
result = mgr.initialize_queue_structure()

# Now submit work to incoming/
delegate_file = mgr.queue_root / "incoming" / "TASK-001.yaml"
delegate_file.write_text("""---
task_id: TASK-001
type: DELEGATE
role: engineer
model: claude-haiku-4.5
...
""")

print(f"DELEGATE submitted to: {delegate_file}")
```

## Integration with Orchestrator

The Orchestrator should detect and use the canonical queue path:

```python
from src.opencode.harness_session_manager import HarnessSessionManager

class Orchestrator:
    def __init__(self):
        # Detect session and harness
        self.session_mgr = HarnessSessionManager.from_env()
        
        # Initialize queue structure
        result = self.session_mgr.initialize_queue_structure()
        if not result["success"]:
            raise RuntimeError(f"Queue init failed: {result['error']}")
        
        # Use canonical queue paths
        self.incoming_dir = self.session_mgr.queue_root / "incoming"
        self.processing_dir = self.session_mgr.queue_root / "processing"
        self.done_dir = self.session_mgr.queue_root / "done"
        self.failed_dir = self.session_mgr.queue_root / "failed"
    
    def poll_incoming(self):
        """Poll canonical incoming/ queue."""
        for task_file in sorted(self.incoming_dir.glob("*.yaml")):
            # Process task...
            pass
```

## Backward Compatibility

The manager maintains backward compatibility with existing code:

- If no environment variables are set, a new UUID is generated for the session
- The default harness is `"local"`
- Existing queue paths (without session isolation) can still be accessed via the `base_dir` parameter

## Testing

For tests, use a temporary base directory:

```python
import tempfile
from src.opencode.harness_session_manager import HarnessSessionManager

with tempfile.TemporaryDirectory() as tmpdir:
    mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
    mgr.initialize_queue_structure()
    
    # Test queue operations...
    assert (mgr.queue_root / "incoming").exists()
```

## Troubleshooting

### Queue structure not initializing

**Problem:** `initialize_queue_structure()` returns `success: False`

**Solution:** Check error message in result dict:
```python
result = mgr.initialize_queue_structure()
if not result["success"]:
    print(result["error"])  # See detailed error
```

### Session ID not detected

**Problem:** New UUID generated each time instead of detecting env var

**Solution:** Verify environment variable is set:
```bash
# Check if OPENCODE_SESSION_ID is set
echo $OPENCODE_SESSION_ID

# Or set it explicitly
export OPENCODE_SESSION_ID="my-session-id"
```

### Multiple queue directories created

**Problem:** Different session IDs being generated for same session

**Solution:** Set `AGENTIC_SESSION_ID` or `OPENCODE_SESSION_ID` explicitly:
```bash
export AGENTIC_SESSION_ID="$(uuidgen)"
```

## Performance Considerations

- **Queue path generation:** O(1) — just string concatenation
- **Queue initialization:** O(1) — creates 4 directories + 1 metadata file
- **Metadata persistence:** ~1ms — JSON serialization
- **Validation:** O(1) — checks existence of 6 items (4 dirs + metadata + root)

## Security Considerations

1. **Session isolation:** Each session has isolated queue paths; concurrent sessions cannot interfere
2. **No secrets in metadata:** Session ID and harness name are non-sensitive
3. **File permissions:** Queue directories inherit permissions from `~/.agentic-engineers/`
4. **No external dependencies:** Pure Python standard library; no third-party code

## See Also

- [SPEC.md > ORCHESTRATOR-FIRST EXECUTION MODEL](../SPEC.md) — Framework architecture
- [AGENTS.md > Queue-Based Execution Model](../AGENTS.md) — Agent delegation patterns
- `src/skills/_meta/queue-isolation/scripts/queue_isolation.py` — Low-level queue path utilities
- `src/orchestration/queue_manager.py` — Orchestrator queue manager
