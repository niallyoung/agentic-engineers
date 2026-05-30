"""
Test suite for Queue Path Validator.

Tests enforce canonical queue path (~/.agentic-engineers/{session-id}/{harness}/queue/)
and reject legacy/injected paths.

Requirements:
- AC1: Runtime validator accepts canonical path only
- AC2: Legacy paths rejected
- AC3: Path injection attempts blocked
- AC4: Git hook validates all DELEGATE/HANDBACK files
- AC5: All 5+ test cases passing
"""

import os
import tempfile
import unittest
from pathlib import Path

# Import the validator module (will fail until implementation exists)
import sys
import os
# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    from queue_path_validator import QueuePathValidator
except ImportError:
    # Define a stub for tests to run (will fail in RED phase)
    class QueuePathValidator:
        pass


class TestQueuePathValidator(unittest.TestCase):
    """Test suite for queue path validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = QueuePathValidator()
        # Test session and harness IDs
        self.session_id = "test-session-123"
        self.harness = "opencode"

    # ─────────────────────────────────────────────────────────────────────────────
    # AC1: Canonical path acceptance
    # ─────────────────────────────────────────────────────────────────────────────

    def test_accepts_canonical_path_with_session_and_harness(self):
        """AC1: Validator accepts canonical path: ~/.agentic-engineers/{session-id}/{harness}/queue/"""
        path = "~/.agentic-engineers/test-session-123/opencode/queue/"
        result = self.validator.validate(path)
        self.assertTrue(result.is_valid, "Canonical path should be accepted")
        self.assertEqual(result.errors, [])

    def test_accepts_canonical_path_with_incoming_subdir(self):
        """AC1: Validator accepts canonical path with /incoming/ subdirectory."""
        path = "~/.agentic-engineers/test-session-123/opencode/queue/incoming/"
        result = self.validator.validate(path)
        self.assertTrue(result.is_valid, "Canonical path with /incoming/ should be accepted")

    def test_accepts_canonical_path_expanded_home(self):
        """AC1: Validator accepts expanded home directory path."""
        home = os.path.expanduser("~")
        path = "{home}/.agentic-engineers/test-session-123/opencode/queue/".format(home=home)
        result = self.validator.validate(path)
        self.assertTrue(result.is_valid, "Expanded home path should be accepted")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC2: Legacy paths rejection
    # ─────────────────────────────────────────────────────────────────────────────

    def test_rejects_legacy_artifacts_queue(self):
        """AC2: Validator rejects legacy path artifacts/queue/"""
        path = "artifacts/queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Legacy artifacts/queue/ path should be rejected")
        self.assertTrue(len(result.errors) > 0, "Should have error messages")
        self.assertIn("legacy", " ".join(result.errors).lower())

    def test_rejects_legacy_copilot_queue(self):
        """AC2: Validator rejects legacy path ~/.copilot/queue/{session-id}/"""
        path = "~/.copilot/queue/test-session-123/incoming/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Legacy ~/.copilot/queue/ path should be rejected")
        self.assertTrue(len(result.errors) > 0, "Should have error messages")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC3: Path injection attempts blocked
    # ─────────────────────────────────────────────────────────────────────────────

    def test_blocks_path_traversal_attempt(self):
        """AC3: Validator blocks path traversal injection: /../"""
        path = "~/.agentic-engineers/test-session-123/../../../tmp/queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Path traversal should be blocked")
        self.assertTrue(len(result.errors) > 0, "Should have error messages")

    def test_blocks_shell_metacharacter_injection(self):
        """AC3: Validator blocks shell metacharacters: ;, |, &, $(...)"""
        injection_attempts = [
            "~/.agentic-engineers/test-session-123/opencode/queue/; rm -rf /",
            "~/.agentic-engineers/test-session-123/opencode/queue/ | cat /etc/passwd",
            "~/.agentic-engineers/test-session-123/opencode/queue/ & malicious_command",
            "~/.agentic-engineers/test-session-123/$(whoami)/queue/",
        ]
        for path in injection_attempts:
            with self.subTest(path=path):
                result = self.validator.validate(path)
                self.assertFalse(result.is_valid, "Shell metacharacters should be blocked in: {0}".format(path))

    def test_blocks_double_slash_tricks(self):
        """AC3: Validator blocks double-slash tricks: //"""
        path = "~/.agentic-engineers//test-session-123//opencode//queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Double slashes should be blocked")

    def test_blocks_null_byte_injection(self):
        """AC3: Validator blocks null byte injection: \\x00"""
        path = "~/.agentic-engineers/test-session-123\x00/opencode/queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Null bytes should be blocked")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC4: Git hook validation (integration test)
    # ─────────────────────────────────────────────────────────────────────────────

    def test_git_hook_detects_legacy_spec_paths(self):
        """AC4: Git hook should detect legacy paths in SPEC.md content."""
        # This is tested via the actual git hook in .githooks/pre-push
        # but we verify the validator can detect these patterns
        spec_content = """
        Queue locations:
        - artifacts/queue/
        - ~/.copilot/queue/{session-id}/incoming/
        """
        result = self.validator.find_invalid_paths_in_text(spec_content)
        self.assertTrue(len(result) > 0, "Should detect legacy paths in SPEC.md")

    # ─────────────────────────────────────────────────────────────────────────────
    # Additional coverage: Edge cases and formats
    # ─────────────────────────────────────────────────────────────────────────────

    def test_rejects_empty_path(self):
        """Edge case: Empty path should be rejected."""
        result = self.validator.validate("")
        self.assertFalse(result.is_valid, "Empty path should be rejected")

    def test_rejects_relative_path(self):
        """Edge case: Relative path without ~ should be rejected."""
        path = ".agentic-engineers/test-session-123/opencode/queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Relative paths without ~ should be rejected")

    def test_accepts_path_with_trailing_slash(self):
        """Edge case: Canonical path with trailing slash should be accepted."""
        path = "~/.agentic-engineers/test-session-123/opencode/queue/"
        result = self.validator.validate(path)
        self.assertTrue(result.is_valid, "Path with trailing slash should be accepted")

    def test_accepts_path_without_trailing_slash(self):
        """Edge case: Canonical path without trailing slash should be accepted."""
        path = "~/.agentic-engineers/test-session-123/opencode/queue"
        result = self.validator.validate(path)
        self.assertTrue(result.is_valid, "Path without trailing slash should be accepted")

    def test_rejects_path_missing_session_id(self):
        """Edge case: Missing session-id should be rejected."""
        path = "~/.agentic-engineers//opencode/queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Path with missing session-id should be rejected")

    def test_rejects_path_missing_harness(self):
        """Edge case: Missing harness should be rejected."""
        path = "~/.agentic-engineers/test-session-123//queue/"
        result = self.validator.validate(path)
        self.assertFalse(result.is_valid, "Path with missing harness should be rejected")

    # ─────────────────────────────────────────────────────────────────────────────
    # Validation result structure tests
    # ─────────────────────────────────────────────────────────────────────────────

    def test_validation_result_has_required_fields(self):
        """Test that validation result has required structure."""
        path = "~/.agentic-engineers/test-session-123/opencode/queue/"
        result = self.validator.validate(path)
        
        # Must have is_valid field
        self.assertTrue(hasattr(result, 'is_valid'))
        self.assertIsInstance(result.is_valid, bool)
        
        # Must have errors field
        self.assertTrue(hasattr(result, 'errors'))
        self.assertIsInstance(result.errors, list)

    def test_validation_error_messages_are_helpful(self):
        """Test that error messages provide clear guidance."""
        path = "artifacts/queue/"
        result = self.validator.validate(path)
        
        self.assertFalse(result.is_valid)
        error_text = " ".join(result.errors)
        # Error should mention canonical path or provide guidance
        self.assertTrue(
            len(error_text) > 20,
            "Error messages should be descriptive"
        )


class TestQueuePathValidatorIntegration(unittest.TestCase):
    """Integration tests for queue path validator with real files."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.validator = QueuePathValidator()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_yaml_delegate_file(self):
        """Integration: Validate DELEGATE YAML file for canonical paths."""
        delegate_content = """
task_id: TASK-PHASE-1.5-FIX-1
type: DELEGATE
role: quality-engineer
queue_path: ~/.agentic-engineers/test-session-123/opencode/queue/incoming/
"""
        result = self.validator.find_invalid_paths_in_text(delegate_content)
        self.assertEqual(len(result), 0, "Canonical paths in YAML should pass")

    def test_validate_yaml_with_legacy_path(self):
        """Integration: Reject YAML with legacy queue path."""
        delegate_content = """
task_id: TASK-PHASE-1.5-FIX-1
type: DELEGATE
queue_path: artifacts/queue/
"""
        result = self.validator.find_invalid_paths_in_text(delegate_content)
        self.assertGreater(len(result), 0, "Legacy paths in YAML should be detected")


if __name__ == '__main__':
    unittest.main()
