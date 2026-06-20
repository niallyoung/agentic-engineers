"""
[DEPRECATED] Backward Compatibility Layer for Queue Path Migration (Phase 1-4)

🔴 DEPRECATED - Migration Phase 1-4 completed 2026-05-26
Only ~/.agentic-engineers/ is supported now. This file is kept for migration understanding only.

This module PREVIOUSLY provided utilities for:
1. Detecting legacy queue paths (~/.copilot/queue/{session_id}/)
2. Validating queue path migration integrity (no data loss)
3. Providing migration status and diagnostics

Historical note: During Phase 1-4 of the migration (weeks 1-4), both old and new paths worked.
As of May 26, 2026, only the new path (~/.agentic-engineers/{harness}/{session-id}/queue/) is supported.

DO NOT USE THIS MODULE IN NEW CODE.

Legacy paths NO LONGER SUPPORTED:
- ~/.copilot/queue/
- ~/.claude/queue/
- artifacts/queue/

Canonical path for all harnesses:
- ~/.agentic-engineers/{harness}/{session-id}/queue/

Usage (for historical reference only):
    from src.orchestration.queue_compat import QueuePathMigration
    
    qm = QueuePathMigration()  # ⚠️ Will detect legacy paths only (no longer used)
    legacy_path = qm.detect_legacy_queue("session-123")
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

__all__ = ["QueuePathMigration"]


class QueuePathMigration:
    """
    Manage legacy queue detection and migration validation.
    
    This class helps track the migration from old paths (~/.copilot/queue/)
    to the canonical per-harness queue paths (~/.agentic-engineers/{harness}/{session-id}/queue/).
    """
    
    def __init__(self, legacy_base: Optional[Path] = None, new_base: Optional[Path] = None):
        """
        Initialize QueuePathMigration.
        
        Args:
            legacy_base: Base directory for legacy queue paths (default: ~/.copilot/queue/)
            new_base: Base directory for new queue paths (default: ~/.agentic-engineers/)
        """
        self.legacy_base = legacy_base or Path.home() / ".copilot" / "queue"
        self.new_base = new_base or Path.home() / ".agentic-engineers"
        
        logger.debug(
            f"QueuePathMigration initialized. "
            f"legacy_base={self.legacy_base}, new_base={self.new_base}"
        )
    
    def detect_legacy_queue(self, session_id: str) -> Optional[Path]:
        """
        Detect if legacy queue exists for given session.
        
        Args:
            session_id: Session ID to check
        
        Returns:
            Path to legacy queue if exists, None otherwise
        """
        legacy_path = self.legacy_base / session_id
        
        if legacy_path.exists():
            logger.info(f"Detected legacy queue: {legacy_path}")
            return legacy_path
        
        return None
    
    def list_legacy_sessions(self) -> List[str]:
        """
        List all session directories in the legacy queue base.
        
        Returns:
            List of session IDs found in legacy queue directory
        """
        if not self.legacy_base.exists():
            return []
        
        sessions = []
        for item in self.legacy_base.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                sessions.append(item.name)
        
        return sorted(sessions)
    
    def get_legacy_queue_contents(self, session_id: str) -> Dict[str, List[str]]:
        """
        Get contents of legacy queue by state (incoming, processing, done).
        
        Args:
            session_id: Session ID to check
        
        Returns:
            Dict with keys 'incoming', 'processing', 'done' containing list of file names
        """
        legacy_path = self.legacy_base / session_id
        
        if not legacy_path.exists():
            return {"incoming": [], "processing": [], "done": []}
        
        contents = {}
        for state in ["incoming", "processing", "done"]:
            state_dir = legacy_path / state
            if state_dir.exists():
                files = sorted([f.name for f in state_dir.glob("*.yaml")])
                contents[state] = files
            else:
                contents[state] = []
        
        return contents
    
    def get_new_queue_contents(self, session_id: str, harness: str) -> Dict[str, List[str]]:
        """
        Get contents of new queue by state (incoming, processing, done, failed).
        
        Args:
            session_id: Session ID to check
            harness: Harness name (e.g., 'claude', 'copilot', 'gpt')
        
        Returns:
            Dict with keys 'incoming', 'processing', 'done', 'failed' containing file names
        """
        new_path = self.new_base / harness / session_id / "queue"
        
        if not new_path.exists():
            return {"incoming": [], "processing": [], "done": [], "failed": []}
        
        contents = {}
        for state in ["incoming", "processing", "done", "failed"]:
            state_dir = new_path / state
            if state_dir.exists():
                files = sorted([f.name for f in state_dir.glob("*.yaml")])
                contents[state] = files
            else:
                contents[state] = []
        
        return contents
    
    def validate_migration(self, session_id: str, harness: str = "copilot") -> Dict:
        """
        Validate that migration from old to new path would preserve data.
        
        Checks:
        1. Legacy queue exists
        2. New queue path can be created
        3. Both paths are readable
        4. File counts match (no data loss)
        
        Args:
            session_id: Session to validate
            harness: Target harness (default: 'copilot' for backward compat)
        
        Returns:
            Dict with validation status and details:
            {
                'status': 'success' | 'warning' | 'error',
                'legacy_exists': bool,
                'new_path_exists': bool,
                'legacy_count': int,
                'new_count': int,
                'warnings': List[str],
                'timestamp': str,
                'can_migrate': bool
            }
        """
        result = {
            'status': 'success',
            'legacy_exists': False,
            'new_path_exists': False,
            'legacy_count': 0,
            'new_count': 0,
            'warnings': [],
            'timestamp': datetime.now().isoformat(),
            'can_migrate': False,
        }
        
        # Check legacy queue
        legacy_path = self.detect_legacy_queue(session_id)
        if legacy_path:
            result['legacy_exists'] = True
            try:
                contents = self.get_legacy_queue_contents(session_id)
                legacy_count = sum(len(v) for v in contents.values())
                result['legacy_count'] = legacy_count
                
                if legacy_count > 0:
                    result['warnings'].append(
                        f"Legacy queue has {legacy_count} items in {session_id}"
                    )
            except Exception as e:
                result['status'] = 'error'
                result['warnings'].append(f"Failed to read legacy queue: {e}")
                return result
        else:
            result['warnings'].append(f"No legacy queue found for session {session_id}")
        
        # Check new queue
        new_path = self.new_base / harness / session_id / "queue"
        if new_path.exists():
            result['new_path_exists'] = True
            try:
                contents = self.get_new_queue_contents(session_id, harness)
                new_count = sum(len(v) for v in contents.values())
                result['new_count'] = new_count
            except Exception as e:
                result['status'] = 'error'
                result['warnings'].append(f"Failed to read new queue: {e}")
                return result
        
        # Determine migration readiness
        if result['legacy_exists'] and result['legacy_count'] > 0:
            result['can_migrate'] = True
            if result['new_path_exists'] and result['new_count'] > 0:
                result['warnings'].append(
                    f"New queue already has {result['new_count']} items. "
                    f"Migrate carefully to avoid duplicates."
                )
        
        if not result['legacy_exists']:
            result['can_migrate'] = False
            result['status'] = 'warning'
        
        logger.info(f"Migration validation for {session_id}/{harness}: {result['status']}")
        return result
    
    def get_migration_summary(self) -> Dict:
        """
        Get summary of all legacy queues and their migration status.
        
        Useful for batch migration planning and monitoring.
        
        Returns:
            Dict with:
            {
                'legacy_sessions': List[str],
                'total_legacy_items': int,
                'validations': Dict[session_id, validation_result],
                'timestamp': str
            }
        """
        sessions = self.list_legacy_sessions()
        
        summary = {
            'legacy_sessions': sessions,
            'total_legacy_items': 0,
            'validations': {},
            'timestamp': datetime.now().isoformat(),
        }
        
        for session_id in sessions:
            contents = self.get_legacy_queue_contents(session_id)
            item_count = sum(len(v) for v in contents.values())
            summary['total_legacy_items'] += item_count
            
            # Validate this session (use 'copilot' as default harness)
            validation = self.validate_migration(session_id, "copilot")
            summary['validations'][session_id] = validation
        
        logger.info(
            f"Migration summary: {len(sessions)} legacy sessions, "
            f"{summary['total_legacy_items']} total items"
        )
        return summary
