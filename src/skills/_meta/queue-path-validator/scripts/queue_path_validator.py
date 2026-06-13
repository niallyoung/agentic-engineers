"""
Queue Path Validator — Runtime enforcement of canonical queue paths.

Enforces canonical path format: ~/.agentic-engineers/{harness}/{session-id}/queue/

Rejects:
- Legacy paths: artifacts/queue/, ~/.copilot/queue/
- Path traversal: ../, .., etc.
- Shell metacharacters: ;, |, &, $(), backticks, etc.
- Null bytes and other injection attempts

Usage:
    validator = QueuePathValidator()
    result = validator.validate("~/.agentic-engineers/opencode/session-123/queue/")
    if result.is_valid:
        print("Path is canonical")
    else:
        print("Errors:", result.errors)
"""

import os
import re
from typing import List, NamedTuple


class ValidationResult(object):
    """Result of path validation."""
    
    def __init__(self, is_valid, errors):
        self.is_valid = is_valid
        self.errors = errors if errors else []


class QueuePathValidator(object):
    """Validator for queue paths enforcing canonical format."""
    
    # Canonical path patterns:
    # 1. With tilde: ~/.agentic-engineers/{harness}/{session-id}/queue/[incoming/]
    # 2. Expanded home: /Users/{user}/.agentic-engineers/{harness}/{session-id}/queue/[incoming/]
    # session-id: alphanumeric, hyphens, underscores
    # harness: alphanumeric, hyphens, underscores
    CANONICAL_TILDE_PATTERN = r'^~\/\.agentic-engineers\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+\/queue\/?(?:\/incoming)?/?$'

    # Expanded home pattern: starts with / and contains .agentic-engineers in right place
    # Pattern matches: /path/to/home/.agentic-engineers/{harness}/{session-id}/queue/...
    CANONICAL_EXPANDED_PATTERN = r'^/.+/\.agentic-engineers\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+\/queue\/?(?:\/incoming)?/?$'
    
    # Legacy paths to detect (patterns only, do not include in source) — DEPRECATED
    LEGACY_PATTERNS = [
        r'artifacts/queue/',  # DEPRECATED pattern — for tests only
        r'~/?\.copilot/queue/',  # DEPRECATED pattern — for tests only
    ]
    
    # Injection attack patterns
    INJECTION_PATTERNS = [
        (r'\.\./', 'Path traversal (../) detected'),
        (r'\\\.\.', r'Path traversal (..\) detected'),
        (r'[;|&]', 'Shell metacharacter (;, |, &) detected'),
        (r'\$\(', 'Command substitution $() detected'),
        (r'`', 'Command substitution (backtick) detected'),
        (r'<|>', 'Redirection (<, >) detected'),
        (r'//', 'Double slash (//) detected'),
        (r'\x00', 'Null byte injection detected'),
    ]
    
    def validate(self, path):
        """
        Validate that path follows canonical format.
        
        Args:
            path: Path string to validate
            
        Returns:
            ValidationResult with is_valid bool and errors list
        """
        errors = []
        
        # Check for empty path
        if not path:
            errors.append('Path cannot be empty')
            return ValidationResult(False, errors)
        
        # Normalize path (but preserve ~ and full paths for pattern matching)
        normalized = self._normalize_path(path)
        
        # Check for legacy paths first
        for legacy_pattern in self.LEGACY_PATTERNS:
            if re.search(legacy_pattern, normalized):
                errors.append('Legacy queue path detected. Must use canonical path: ~/.agentic-engineers/{harness}/{session-id}/queue/')
                return ValidationResult(False, errors)
        
        # Check for injection attempts
        injection_error = self._check_injections(normalized)
        if injection_error:
            errors.append(injection_error)
            return ValidationResult(False, errors)
        
        # Check for canonical format (either tilde or expanded)
        is_tilde_canonical = re.match(self.CANONICAL_TILDE_PATTERN, normalized)
        is_expanded_canonical = re.match(self.CANONICAL_EXPANDED_PATTERN, normalized)
        
        if not (is_tilde_canonical or is_expanded_canonical):
            errors.append('Path must follow canonical format: ~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/')
            # Provide helpful error details
            if not normalized.startswith('~') and not normalized.startswith('/'):
                if '.agentic-engineers' in normalized:
                    errors.append('Hint: Absolute or home-relative paths required (use ~/ or /Users/username/)')
            return ValidationResult(False, errors)
        
        # Path is valid
        return ValidationResult(True, [])
    
    def _normalize_path(self, path):
        """
        Normalize path for validation.
        
        Performs basic normalization without resolving symlinks or expanding home
        (we need to preserve ~ for pattern matching).
        
        Args:
            path: Raw path string
            
        Returns:
            Normalized path string
        """
        # Remove leading/trailing whitespace
        normalized = path.strip()
        
        # For canonical paths, we want to preserve ~ and normalize slashes
        # Replace multiple slashes with single slash (but watch for injection)
        # We'll check for this specifically in injection checks
        
        return normalized
    
    def _check_injections(self, path):
        """
        Check for injection attack patterns in path.
        
        Args:
            path: Path string to check
            
        Returns:
            Error message if injection found, None otherwise
        """
        for pattern, message in self.INJECTION_PATTERNS:
            if re.search(pattern, path):
                return message
        return None
    
    def find_invalid_paths_in_text(self, text):
        """
        Find invalid queue paths in text (e.g., SPEC.md, YAML files).
        
        Searches for both legacy paths and non-canonical paths.
        
        Args:
            text: Text content to search
            
        Returns:
            List of found invalid paths
        """
        invalid_paths = []
        
        # Check for legacy paths
        for legacy_pattern in self.LEGACY_PATTERNS:
            matches = re.finditer(legacy_pattern, text)
            for match in matches:
                invalid_paths.append(match.group(0))
        
        # Check for common queue path references that aren't canonical
        queue_patterns = [
            r'(?<!~)artifacts/queue/',
            r'~/?\.copilot/queue/[^~]*',
        ]
        
        for pattern in queue_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                path = match.group(0)
                if path not in invalid_paths:  # Avoid duplicates
                    invalid_paths.append(path)
        
        return invalid_paths
