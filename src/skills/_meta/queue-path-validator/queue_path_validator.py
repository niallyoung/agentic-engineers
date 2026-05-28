"""Queue path validation logic for canonical queue directory enforcement.

Security Model:
- Canonical format: ~/.agentic-engineers/{session-id}/{harness}/queue/{subdir}
- Rejects legacy paths (e.g., ~/.copilot/queue/, ~/.claude/queue/)
- Prevents path traversal (../, //, symlinks)
- Validates subdirectory names (incoming, processing, done)
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional


# Canonical queue path pattern
CANONICAL_QUEUE_PATTERN = re.compile(
    r'^~?/?\.agentic-engineers/([a-z0-9\-]+)/([a-z0-9\-]+)/queue/?$'
)

# Valid queue subdirectories
VALID_SUBDIRS = {'incoming', 'processing', 'done'}

# Legacy paths to reject (must be at root level, not in canonical path)
LEGACY_PATTERNS = [
    r'^~?/?\.copilot/queue',
    r'^~?/?\.claude/queue',
    r'^~?/?\.pi/queue',
    r'^~?/?copilot/queue',
    r'^~?/?claude/queue',
]


class QueuePathValidationError(Exception):
    """Raised when queue path validation fails."""
    pass


def validate_queue_path(path: str) -> Dict[str, Any]:
    """
    Validate queue path matches canonical format.
    
    Canonical format: ~/.agentic-engineers/{session-id}/{harness}/queue/
    
    Security checks:
    - Rejects legacy paths (~/.copilot/queue/, ~/.claude/queue/)
    - Prevents path traversal (../, //, symlinks)
    - Validates session-id and harness names
    - Ensures path is not a symlink
    
    Args:
        path: Queue path to validate (absolute or relative)
        
    Returns:
        Dict with keys:
        - valid (bool): Whether path is valid
        - session_id (str): Extracted session ID (if valid)
        - harness (str): Extracted harness name (if valid)
        - subdir (str): Extracted subdirectory (if valid)
        - error (str): Error message (if invalid)
        
    Raises:
        QueuePathValidationError: If path is invalid
    """
    if not path or not isinstance(path, str):
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path must be a non-empty string'
        }
    
    # Normalize path
    normalized = path.strip()
    
    # Check for path traversal attempts
    if '..' in normalized or '//' in normalized:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path traversal detected (.., //)'
        }
    
    # Check for legacy paths
    for legacy_pattern in LEGACY_PATTERNS:
        if re.search(legacy_pattern, normalized):
            return {
                'valid': False,
                'session_id': None,
                'harness': None,
                'subdir': None,
                'error': f'Legacy path detected: {normalized}'
            }
    
    # Check for symlinks (if path exists)
    try:
        if os.path.exists(normalized) and os.path.islink(normalized):
            return {
                'valid': False,
                'session_id': None,
                'harness': None,
                'subdir': None,
                'error': 'Symlinks not allowed in queue paths'
            }
    except (OSError, ValueError):
        pass  # Path may not exist yet, continue validation
    
    # Match canonical pattern (without subdir)
    match = CANONICAL_QUEUE_PATTERN.match(normalized)
    if not match:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': f'Path does not match canonical format: {normalized}'
        }
    
    session_id = match.group(1)
    harness = match.group(2)
    
    # Validate session_id format (YYYY-MM-DD-kebab-case or UUID-like)
    if not re.match(r'^[a-z0-9\-]{8,}$', session_id):
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': None,
            'error': f'Invalid session_id format: {session_id}'
        }
    
    # Validate harness name
    if harness not in {'opencode', 'claude', 'copilot', 'pi'}:
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': None,
            'error': f'Invalid harness name: {harness}'
        }
    
    return {
        'valid': True,
        'session_id': session_id,
        'harness': harness,
        'subdir': None,  # No subdir in base path
        'error': None
    }


def validate_queue_subdir(path: str) -> Dict[str, Any]:
    """
    Validate queue path with subdirectory.
    
    Validates: ~/.agentic-engineers/{session-id}/{harness}/queue/{subdir}
    
    Valid subdirs: incoming, processing, done
    
    Args:
        path: Full queue path including subdirectory
        
    Returns:
        Dict with keys:
        - valid (bool): Whether path is valid
        - session_id (str): Extracted session ID (if valid)
        - harness (str): Extracted harness name (if valid)
        - subdir (str): Extracted subdirectory (if valid)
        - error (str): Error message (if invalid)
    """
    if not path or not isinstance(path, str):
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path must be a non-empty string'
        }
    
    normalized = path.strip().rstrip('/')
    
    # Check for path traversal
    if '..' in normalized or '//' in normalized:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path traversal detected (.., //)'
        }
    
    # Check for legacy paths
    for legacy_pattern in LEGACY_PATTERNS:
        if re.search(legacy_pattern, normalized):
            return {
                'valid': False,
                'session_id': None,
                'harness': None,
                'subdir': None,
                'error': f'Legacy path detected: {normalized}'
            }
    
    # Match canonical pattern with subdir
    pattern = re.compile(
        r'^~?/?\.agentic-engineers/([a-z0-9\-]+)/([a-z0-9\-]+)/queue/([a-z]+)/?$'
    )
    match = pattern.match(normalized)
    
    if not match:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': f'Path does not match canonical format with subdir: {normalized}'
        }
    
    session_id = match.group(1)
    harness = match.group(2)
    subdir = match.group(3)
    
    # Validate session_id
    if not re.match(r'^[a-z0-9\-]{8,}$', session_id):
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': subdir,
            'error': f'Invalid session_id format: {session_id}'
        }
    
    # Validate harness
    if harness not in {'opencode', 'claude', 'copilot', 'pi'}:
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': subdir,
            'error': f'Invalid harness name: {harness}'
        }
    
    # Validate subdir
    if subdir not in VALID_SUBDIRS:
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': subdir,
            'error': f'Invalid subdirectory: {subdir}. Must be one of: {VALID_SUBDIRS}'
        }
    
    return {
        'valid': True,
        'session_id': session_id,
        'harness': harness,
        'subdir': subdir,
        'error': None
    }
