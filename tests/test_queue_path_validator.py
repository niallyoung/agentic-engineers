"""Unit tests for queue path validator."""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from the module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "queue_path_validator",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'skills', '_meta', 'queue-path-validator', 'queue_path_validator.py')
)
queue_path_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue_path_validator)

validate_queue_path = queue_path_validator.validate_queue_path
validate_queue_subdir = queue_path_validator.validate_queue_subdir
QueuePathValidationError = queue_path_validator.QueuePathValidationError
VALID_SUBDIRS = queue_path_validator.VALID_SUBDIRS


class TestValidateQueuePath:
    """Tests for validate_queue_path() function."""
    
    def test_valid_canonical_path_absolute(self):
        """Valid canonical path with absolute format."""
        result = validate_queue_path('~/.agentic-engineers/session-001/opencode/queue')
        assert result['valid'] is True
        assert result['session_id'] == 'session-001'
        assert result['harness'] == 'opencode'
        assert result['error'] is None
    
    def test_valid_canonical_path_relative(self):
        """Valid canonical path with relative format."""
        result = validate_queue_path('.agentic-engineers/session-001/opencode/queue')
        assert result['valid'] is True
        assert result['session_id'] == 'session-001'
        assert result['harness'] == 'opencode'
    
    def test_valid_canonical_path_with_trailing_slash(self):
        """Valid canonical path with trailing slash."""
        result = validate_queue_path('~/.agentic-engineers/session-001/opencode/queue/')
        assert result['valid'] is True
        assert result['session_id'] == 'session-001'
    
    def test_valid_harness_names(self):
        """All valid harness names are accepted."""
        for harness in ['opencode', 'claude', 'copilot', 'pi']:
            result = validate_queue_path(f'~/.agentic-engineers/session-001/{harness}/queue')
            assert result['valid'] is True
            assert result['harness'] == harness
    
    def test_valid_session_id_formats(self):
        """Various valid session ID formats."""
        valid_ids = [
            'session-001',
            'session-abc123',
            '2026-05-28-test',
            'abc-def-ghi',
            'a1-b2-c3-d4-e5',
        ]
        for session_id in valid_ids:
            result = validate_queue_path(f'~/.agentic-engineers/{session_id}/opencode/queue')
            assert result['valid'] is True, f"Session ID {session_id} should be valid"
            assert result['session_id'] == session_id
    
    def test_reject_legacy_copilot_path(self):
        """Reject legacy ~/.copilot/queue path."""
        result = validate_queue_path('~/.copilot/queue')
        assert result['valid'] is False
        assert 'Legacy path' in result['error']
    
    def test_reject_legacy_claude_path(self):
        """Reject legacy ~/.claude/queue path."""
        result = validate_queue_path('~/.claude/queue')
        assert result['valid'] is False
        assert 'Legacy path' in result['error']
    
    def test_reject_legacy_pi_path(self):
        """Reject legacy ~/.pi/queue path."""
        result = validate_queue_path('~/.pi/queue')
        assert result['valid'] is False
        assert 'Legacy path' in result['error']
    
    def test_reject_path_traversal_double_dot(self):
        """Reject path traversal with ..."""
        result = validate_queue_path('~/.agentic-engineers/../../../etc/passwd')
        assert result['valid'] is False
        assert 'traversal' in result['error'].lower()
    
    def test_reject_path_traversal_double_slash(self):
        """Reject path traversal with //."""
        result = validate_queue_path('~/.agentic-engineers//session-001/opencode/queue')
        assert result['valid'] is False
        assert 'traversal' in result['error'].lower()
    
    def test_reject_empty_path(self):
        """Reject empty path."""
        result = validate_queue_path('')
        assert result['valid'] is False
        assert 'non-empty' in result['error'].lower()
    
    def test_reject_none_path(self):
        """Reject None path."""
        result = validate_queue_path(None)
        assert result['valid'] is False
        assert 'non-empty' in result['error'].lower()
    
    def test_reject_invalid_harness(self):
        """Reject invalid harness name."""
        result = validate_queue_path('~/.agentic-engineers/session-001/invalid-harness/queue')
        assert result['valid'] is False
        assert 'Invalid harness' in result['error']
    
    def test_reject_invalid_session_id_too_short(self):
        """Reject session ID that is too short."""
        result = validate_queue_path('~/.agentic-engineers/abc/opencode/queue')
        assert result['valid'] is False
        assert 'Invalid session_id' in result['error']
    
    def test_reject_invalid_session_id_special_chars(self):
        """Reject session ID with invalid special characters."""
        result = validate_queue_path('~/.agentic-engineers/session@001/opencode/queue')
        assert result['valid'] is False
        # Special chars in session_id cause pattern mismatch, not session_id validation error
        assert 'does not match canonical format' in result['error'] or 'Invalid session_id' in result['error']
    
    def test_reject_malformed_path(self):
        """Reject malformed path."""
        result = validate_queue_path('~/.agentic-engineers/session-001')
        assert result['valid'] is False
        assert 'does not match canonical format' in result['error']


class TestValidateQueueSubdir:
    """Tests for validate_queue_subdir() function."""
    
    def test_valid_incoming_subdir(self):
        """Valid path with incoming subdirectory."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/incoming')
        assert result['valid'] is True
        assert result['subdir'] == 'incoming'
        assert result['session_id'] == 'session-001'
    
    def test_valid_processing_subdir(self):
        """Valid path with processing subdirectory."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/processing')
        assert result['valid'] is True
        assert result['subdir'] == 'processing'
    
    def test_valid_done_subdir(self):
        """Valid path with done subdirectory."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/done')
        assert result['valid'] is True
        assert result['subdir'] == 'done'
    
    def test_valid_subdir_with_trailing_slash(self):
        """Valid path with trailing slash."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/incoming/')
        assert result['valid'] is True
        assert result['subdir'] == 'incoming'
    
    def test_reject_invalid_subdir(self):
        """Reject invalid subdirectory name."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/invalid')
        assert result['valid'] is False
        assert 'Invalid subdirectory' in result['error']
    
    def test_reject_subdir_path_traversal(self):
        """Reject path traversal in subdir path."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/../../../etc')
        assert result['valid'] is False
        assert 'traversal' in result['error'].lower()
    
    def test_reject_legacy_path_with_subdir(self):
        """Reject legacy path even with valid subdir."""
        result = validate_queue_subdir('~/.copilot/queue/incoming')
        assert result['valid'] is False
        assert 'Legacy path' in result['error']
    
    def test_reject_empty_subdir_path(self):
        """Reject empty path."""
        result = validate_queue_subdir('')
        assert result['valid'] is False
        assert 'non-empty' in result['error'].lower()
    
    def test_all_valid_subdirs(self):
        """All valid subdirectories are accepted."""
        for subdir in VALID_SUBDIRS:
            result = validate_queue_subdir(f'~/.agentic-engineers/session-001/opencode/queue/{subdir}')
            assert result['valid'] is True, f"Subdir {subdir} should be valid"
            assert result['subdir'] == subdir


class TestEdgeCases:
    """Edge case tests."""
    
    def test_path_with_spaces(self):
        """Reject path with spaces."""
        result = validate_queue_path('~/.agentic-engineers/session 001/opencode/queue')
        assert result['valid'] is False
    
    def test_path_with_uppercase(self):
        """Reject path with uppercase (should be lowercase)."""
        result = validate_queue_path('~/.agentic-engineers/Session-001/opencode/queue')
        assert result['valid'] is False
    
    def test_path_with_unicode(self):
        """Reject path with unicode characters."""
        result = validate_queue_path('~/.agentic-engineers/séssion-001/opencode/queue')
        assert result['valid'] is False
    
    def test_very_long_session_id(self):
        """Accept very long but valid session ID."""
        long_id = 'a' * 100 + '-' + 'b' * 100
        result = validate_queue_path(f'~/.agentic-engineers/{long_id}/opencode/queue')
        assert result['valid'] is True
    
    def test_whitespace_handling(self):
        """Whitespace is trimmed."""
        result = validate_queue_path('  ~/.agentic-engineers/session-001/opencode/queue  ')
        assert result['valid'] is True
        assert result['session_id'] == 'session-001'


class TestReturnValues:
    """Test return value structure."""
    
    def test_valid_path_return_structure(self):
        """Valid path returns all required fields."""
        result = validate_queue_path('~/.agentic-engineers/session-001/opencode/queue')
        assert 'valid' in result
        assert 'session_id' in result
        assert 'harness' in result
        assert 'subdir' in result
        assert 'error' in result
        assert result['error'] is None
    
    def test_invalid_path_return_structure(self):
        """Invalid path returns all required fields."""
        result = validate_queue_path('~/.copilot/queue')
        assert 'valid' in result
        assert 'session_id' in result
        assert 'harness' in result
        assert 'subdir' in result
        assert 'error' in result
        assert result['error'] is not None
    
    def test_subdir_valid_return_structure(self):
        """Valid subdir path returns all required fields."""
        result = validate_queue_subdir('~/.agentic-engineers/session-001/opencode/queue/incoming')
        assert 'valid' in result
        assert 'session_id' in result
        assert 'harness' in result
        assert 'subdir' in result
        assert 'error' in result
        assert result['subdir'] == 'incoming'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
