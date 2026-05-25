"""Session Memory Directory Setup

Creates and manages the directory structure for session memory storage.

Directory structure:
```
~/.agentic-engineers/{session_id}/memory/
├── delegates/          (DELEGATE event copies)
├── handbacks/          (HANDBACK event copies)  
├── logs/               (agent execution logs)
├── thinking/           (reasoning output)
├── metrics/            (token usage, timing, quality)
├── index.json          (aggregated metadata)
├── index.md            (human-readable index)
└── summary.md          (session summary report)
```
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def get_agentic_engineers_home() -> Path:
    """Get the agentic-engineers home directory (~/.agentic-engineers)."""
    home = Path.home()
    agentic_home = home / ".agentic-engineers"
    return agentic_home


def get_session_memory_dir(session_id: str) -> Path:
    """Get the session memory directory."""
    agentic_home = get_agentic_engineers_home()
    return agentic_home / session_id / "memory"


def setup_session_memory(session_id: str) -> Dict[str, Path]:
    """
    Create session memory directory structure.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Dict mapping subdirectory names to their Path objects
        
    Raises:
        OSError: If directory creation fails
    """
    memory_dir = get_session_memory_dir(session_id)
    
    # Subdirectories to create
    subdirs = {
        "delegates": memory_dir / "delegates",
        "handbacks": memory_dir / "handbacks",
        "logs": memory_dir / "logs",
        "thinking": memory_dir / "thinking",
        "metrics": memory_dir / "metrics",
    }
    
    try:
        # Create main memory directory
        memory_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created session memory directory: {memory_dir}")
        
        # Create subdirectories
        for name, path in subdirs.items():
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created subdirectory: {path}")
        
        # Create .keep files to ensure directories are tracked in git
        for path in subdirs.values():
            keep_file = path / ".keep"
            keep_file.touch(exist_ok=True)
        
        logger.info(f"Session memory structure ready: {memory_dir}")
        return subdirs
        
    except OSError as e:
        logger.error(f"Failed to create session memory structure: {e}")
        raise


def initialize_memory_index(session_id: str, metadata: Optional[Dict] = None) -> Path:
    """
    Initialize empty index.json for the session.
    
    Args:
        session_id: Unique session identifier
        metadata: Optional metadata to include in index
        
    Returns:
        Path to the created index.json
    """
    memory_dir = get_session_memory_dir(session_id)
    index_path = memory_dir / "index.json"
    
    index_data = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "delegates_count": 0,
        "handbacks_count": 0,
        "logs_count": 0,
        "thinking_count": 0,
        "metrics_count": 0,
        "total_tokens_used": 0,
        "quality_scores": [],
        "metadata": metadata or {},
        "delegates": [],
        "handbacks": [],
    }
    
    try:
        with open(index_path, "w") as f:
            json.dump(index_data, f, indent=2)
        logger.debug(f"Created memory index: {index_path}")
        return index_path
    except IOError as e:
        logger.error(f"Failed to create memory index: {e}")
        raise


def cleanup_session_memory(session_id: str, archive: bool = True) -> bool:
    """
    Clean up session memory directory.
    
    Args:
        session_id: Session identifier
        archive: If True, archive instead of delete
        
    Returns:
        True if cleanup successful
    """
    memory_dir = get_session_memory_dir(session_id)
    
    if not memory_dir.exists():
        logger.warning(f"Session memory directory does not exist: {memory_dir}")
        return False
    
    try:
        if archive:
            agentic_home = get_agentic_engineers_home()
            archive_dir = agentic_home / "archive" / session_id
            archive_dir.mkdir(parents=True, exist_ok=True)
            # Move memory dir to archive
            import shutil
            shutil.move(str(memory_dir), str(archive_dir / "memory"))
            logger.info(f"Archived session memory: {archive_dir}")
        else:
            # Delete directly
            import shutil
            shutil.rmtree(memory_dir)
            logger.info(f"Deleted session memory: {memory_dir}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup session memory: {e}")
        return False


def get_memory_stats(session_id: str) -> Dict:
    """Get statistics about session memory."""
    memory_dir = get_session_memory_dir(session_id)
    
    if not memory_dir.exists():
        return {"exists": False, "session_id": session_id}
    
    stats = {
        "exists": True,
        "session_id": session_id,
        "memory_dir": str(memory_dir),
        "delegates_count": len(list((memory_dir / "delegates").glob("*.yaml"))) if (memory_dir / "delegates").exists() else 0,
        "handbacks_count": len(list((memory_dir / "handbacks").glob("*.yaml"))) if (memory_dir / "handbacks").exists() else 0,
        "logs_count": len(list((memory_dir / "logs").glob("*.log"))) if (memory_dir / "logs").exists() else 0,
        "thinking_count": len(list((memory_dir / "thinking").glob("*"))) if (memory_dir / "thinking").exists() else 0,
        "metrics_count": len(list((memory_dir / "metrics").glob("*.json"))) if (memory_dir / "metrics").exists() else 0,
    }
    
    return stats
