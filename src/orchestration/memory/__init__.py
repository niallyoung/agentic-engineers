"""Session Memory Management & Aggregation Infrastructure

Provides centralized memory collection for all session events (DELEGATEs, HANDBACKs, logs, metrics).

Key components:
- SessionMemoryAggregator: Collects memory from queue and logs (aggregator.py)
- SessionMemoryManager: Manages session memory lifecycle (session_manager.py)
- setup_session_memory: Create session memory directory structure (directory_setup.py)
"""

# Import from the actual implementation modules
from .directory_setup import setup_session_memory, get_session_memory_dir
from .artifact_memory import ArtifactMemoryStore, MemoryIndexBuilder
from .aggregator import SessionMemoryAggregator
from .session_manager import SessionMemoryManager as SessionMemoryLifecycleManager
from .session_memory import SessionMemoryManager, GlobalMemoryManager

__all__ = [
    "setup_session_memory",
    "get_session_memory_dir",
    "ArtifactMemoryStore",
    "MemoryIndexBuilder",
    "SessionMemoryAggregator",
    "SessionMemoryLifecycleManager",
    "SessionMemoryManager",
    "GlobalMemoryManager",
]
