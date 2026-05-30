"""Queue path validation logic for canonical queue directory enforcement.

Security Model:
- Canonical format: ~/.agentic-engineers/{session-id}/{harness}/queue/{subdir}
- Rejects legacy paths (e.g., ~/.copilot-legacy/queue, ~/.claude-legacy/queue)
- Prevents path traversal (../, //, symlinks)
- Validates subdirectory names (incoming, processing, done)
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union


# Canonical queue path pattern - matches queue directory (no subdirs yet)
# Handles: ~/.agentic-engineers/{session}/{harness}/queue/ (with or without trailing slash)
CANONICAL_QUEUE_PATTERN = re.compile(
    r'^~?/?\.agentic-engineers/([a-z0-9\-]+)/([a-z0-9\-]+)/queue/?$'
)

# Valid queue subdirectories
VALID_SUBDIRS = {'incoming', 'processing', 'done', 'failed'}

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


def validate_queue_path(path: Union[Path, str]) -> Dict[str, Any]:
    """
    Validate queue path matches canonical format.
    
    This function accepts BOTH file paths (e.g., ~/.agentic-engineers/session/harness/queue/incoming/file.yaml)
    and directory paths (e.g., ~/.agentic-engineers/session/harness/queue/).
    
    For file paths, it extracts and validates the queue directory.
    
    Canonical format: ~/.agentic-engineers/{session-id}/{harness}/queue/[{subdir}/][{file}]
    
    Security checks:
    - Rejects legacy paths (old ~/.copilot and ~/.claude directories)
    - Prevents path traversal (../, //, symlinks)
    - Validates session-id and harness names
    - Ensures path is not a symlink
    
    Contract validation:
    - Input must be a Path or string (not None)
    - Parent directories must be accessible (if path exists)
    
    Args:
        path: Queue path to validate (absolute or relative). Can be file or directory.
        
    Returns:
        Dict with keys:
        - valid (bool): Whether path is valid
        - session_id (str): Extracted session ID (if valid), None otherwise
        - harness (str): Extracted harness name (if valid), None otherwise
        - subdir (str): Extracted subdirectory (if valid), None otherwise
        - error (str): Error message (if invalid), None if valid
        
    Raises:
        AssertionError: If contract violated (path is None, not a string/Path, or parent not accessible)
    """
    # Contract validation: ensure input is not None or proper type
    if path is None:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path must be a non-empty string or Path object'
        }
    
    if not isinstance(path, (Path, str)):
        raise AssertionError(
            f"validate_queue_path requires path to be Path or str, got {type(path).__name__}"
        )
    
    # Convert Path to string for processing
    if isinstance(path, Path):
        path_str = str(path)
    else:
        path_str = path.strip()
    
    # Check for empty string after stripping
    if not path_str:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path must be a non-empty string or Path object'
        }
    
    # Contract validation: if path exists, parent must be a directory
    try:
        path_obj = Path(path_str)
        if path_obj.exists():
            # Verify parent is a directory or path itself is a directory
            if path_obj.is_file():
                parent_dir = path_obj.parent
                assert parent_dir.is_dir(), (
                    f"Parent directory {parent_dir} is not accessible or not a directory"
                )
            elif not path_obj.is_dir():
                raise AssertionError(
                    f"Path exists but is neither file nor directory: {path_str}"
                )
    except (OSError, ValueError) as e:
        # Path may not exist yet, that's OK - continue validation
        pass
    
    # Normalize path
    normalized = path_str.strip()
    
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
    
    # Extract queue directory from file path (if this is a file path)
    # Remove file name and any subdirectories under queue/ to get just the queue dir
    # Examples:
    #   ~/.agentic-engineers/session/harness/queue/incoming/file.yaml → extract queue dir
    #   /absolute/path/.agentic-engineers/session/harness/queue/ → extract queue dir
    #   ~/.agentic-engineers/session/harness/queue/ → exact match
    
    # Find the "queue" directory marker in the path
    parts = normalized.replace('\\', '/').split('/')
    queue_idx = -1
    for i, part in enumerate(parts):
        if part == 'queue':
            queue_idx = i
            break
    
    if queue_idx == -1:
        # No 'queue' marker found
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': f'Path does not match canonical format: {normalized}'
        }
    
    # Extract just the canonical part: from '.agentic-engineers' to 'queue'
    # Find the index of '.agentic-engineers' part
    canonical_start_idx = -1
    for i, part in enumerate(parts):
        if part == '.agentic-engineers':
            canonical_start_idx = i
            break
    
    if canonical_start_idx == -1:
        # No '.agentic-engineers' marker found
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': f'Path does not match canonical format: {normalized}'
        }
    
    # Reconstruct the canonical queue directory path
    # From '.agentic-engineers' to 'queue' (inclusive)
    queue_dir_parts = parts[canonical_start_idx:queue_idx + 1]
    queue_dir_normalized = '/'.join(queue_dir_parts)
    
    # Match canonical pattern (without subdir or file)
    match = CANONICAL_QUEUE_PATTERN.match(queue_dir_normalized)
    if not match:
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': f'Queue directory does not match canonical format: {queue_dir_normalized}'
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
    
    # Validate harness name - accept any harness including local, gpt, and custom names
    if not re.match(r'^[a-z0-9\-]+$', harness):
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': None,
            'error': f'Invalid harness name format: {harness}'
        }
    
    # If there's a subdirectory, validate it
    subdir = None
    if queue_idx + 1 < len(parts) and parts[queue_idx + 1]:
        # Check if next part is a subdirectory (not a file)
        potential_subdir = parts[queue_idx + 1]
        if potential_subdir in VALID_SUBDIRS:
            subdir = potential_subdir
    
    return {
        'valid': True,
        'session_id': session_id,
        'harness': harness,
        'subdir': subdir,  # Subdir if present, None if this is just a file path
        'error': None
    }


def validate_queue_subdir(path: Union[Path, str]) -> Dict[str, Any]:
    """
    Validate queue path with subdirectory.
    
    Validates: ~/.agentic-engineers/{session-id}/{harness}/queue/{subdir}
    
    Valid subdirs: incoming, processing, done, failed
    
    Args:
        path: Full queue path including subdirectory (Path or str)
        
    Returns:
        Dict with keys:
        - valid (bool): Whether path is valid
        - session_id (str): Extracted session ID (if valid)
        - harness (str): Extracted harness name (if valid)
        - subdir (str): Extracted subdirectory (if valid)
        - error (str): Error message (if invalid)
    """
    # Contract validation
    if not isinstance(path, (Path, str)):
        raise AssertionError(
            f"validate_queue_subdir requires path to be Path or str, got {type(path).__name__}"
        )
    
    # Convert Path to string
    if isinstance(path, Path):
        path_str = str(path)
    else:
        path_str = path
    
    if not path_str or not isinstance(path_str, str):
        return {
            'valid': False,
            'session_id': None,
            'harness': None,
            'subdir': None,
            'error': 'Path must be a non-empty string'
        }
    
    normalized = path_str.strip().rstrip('/')
    
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
    
    # Validate harness - accept any harness including local, gpt, and custom names
    if not re.match(r'^[a-z0-9\-]+$', harness):
        return {
            'valid': False,
            'session_id': session_id,
            'harness': harness,
            'subdir': subdir,
            'error': f'Invalid harness name format: {harness}'
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
