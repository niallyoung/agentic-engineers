"""
Test suite for spec_version_validator - Audit Trail via spec_version Field

This test suite validates the spec_version field implementation for DELEGATE and HANDBACK schemas.
Tests cover:
1. DELEGATE requires spec_version field
2. HANDBACK spec_version must match DELEGATE
3. Mismatched spec_versions detected and rejected
4. Audit queries work: find_tasks_by_spec_version()
5. Format validation: '1.0', '1.1', '1.1-2026-05-28' accepted; 'v1.0', '1', '1.0.0' rejected
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from spec_version_validator import (
    validate_spec_version_format,
    validate_spec_version_match,
    find_tasks_by_spec_version,
    SpecVersionValidationError,
)


class TestSpecVersionFormatValidation:
    """Test Case 1: Format validation for spec_version field"""

    def test_valid_format_major_minor(self):
        """Accept valid format: major.minor (e.g., '1.0')"""
        assert validate_spec_version_format("1.0") is True
        assert validate_spec_version_format("2.1") is True
        assert validate_spec_version_format("10.5") is True

    def test_valid_format_major_minor_with_date(self):
        """Accept valid format: major.minor-date (e.g., '1.0-2026-05-28')"""
        assert validate_spec_version_format("1.0-2026-05-28") is True
        assert validate_spec_version_format("1.1-2026-05-28") is True
        assert validate_spec_version_format("2.0-2025-01-01") is True

    def test_valid_format_major_minor_with_any_suffix(self):
        """Accept valid format: major.minor-any-suffix (e.g., '1.1-rc1', '1.0-beta')"""
        assert validate_spec_version_format("1.0-rc1") is True
        assert validate_spec_version_format("1.1-beta") is True
        assert validate_spec_version_format("2.0-alpha-20260530") is True

    def test_invalid_format_v_prefix(self):
        """Reject invalid format: v-prefix (e.g., 'v1.0')"""
        assert validate_spec_version_format("v1.0") is False
        assert validate_spec_version_format("v2.1") is False

    def test_invalid_format_single_version(self):
        """Reject invalid format: single number (e.g., '1')"""
        assert validate_spec_version_format("1") is False
        assert validate_spec_version_format("2") is False

    def test_invalid_format_three_part_version(self):
        """Reject invalid format: three-part version (e.g., '1.0.0')"""
        assert validate_spec_version_format("1.0.0") is False
        assert validate_spec_version_format("2.1.3") is False

    def test_invalid_format_empty_string(self):
        """Reject invalid format: empty string"""
        assert validate_spec_version_format("") is False

    def test_invalid_format_non_numeric(self):
        """Reject invalid format: non-numeric major or minor"""
        assert validate_spec_version_format("a.b") is False
        assert validate_spec_version_format("1.x") is False
        assert validate_spec_version_format("x.0") is False


class TestDelegateRequiresSpecVersion:
    """Test Case 2: DELEGATE requires spec_version field"""

    def test_delegate_with_spec_version_valid(self):
        """DELEGATE with spec_version field should be valid"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "role": "engineer",
            "spec_version": "1.0",
        }
        # Should not raise exception
        assert validate_spec_version_match(delegate, None) is True

    def test_delegate_missing_spec_version_raises_error(self):
        """DELEGATE missing spec_version field should raise SpecVersionValidationError"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "role": "engineer",
        }
        with pytest.raises(SpecVersionValidationError):
            validate_spec_version_match(delegate, None)

    def test_delegate_with_valid_spec_version_format(self):
        """DELEGATE with various valid spec_version formats should be accepted"""
        valid_versions = ["1.0", "1.1", "1.1-2026-05-28", "2.0-rc1"]
        for version in valid_versions:
            delegate = {
                "task_id": "2026-05-30-test-task",
                "type": "DELEGATE",
                "spec_version": version,
            }
            assert validate_spec_version_match(delegate, None) is True


class TestHandbackSpecVersionMatching:
    """Test Case 3: HANDBACK spec_version must match DELEGATE"""

    def test_handback_matches_delegate_version(self):
        """HANDBACK with matching spec_version should pass validation"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "spec_version": "1.0",
        }
        handback = {
            "task_id": "2026-05-30-test-task",
            "type": "HANDBACK",
            "spec_version": "1.0",
        }
        # Should not raise exception
        assert validate_spec_version_match(handback, delegate) is True

    def test_handback_mismatches_delegate_version(self):
        """HANDBACK with mismatched spec_version should raise SpecVersionValidationError"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "spec_version": "1.0",
        }
        handback = {
            "task_id": "2026-05-30-test-task",
            "type": "HANDBACK",
            "spec_version": "1.1",
        }
        with pytest.raises(SpecVersionValidationError):
            validate_spec_version_match(handback, delegate)

    def test_handback_mismatches_delegate_with_dates(self):
        """HANDBACK with different dates in spec_version should be rejected"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "spec_version": "1.0-2026-05-28",
        }
        handback = {
            "task_id": "2026-05-30-test-task",
            "type": "HANDBACK",
            "spec_version": "1.0-2026-05-29",
        }
        with pytest.raises(SpecVersionValidationError):
            validate_spec_version_match(handback, delegate)

    def test_handback_missing_spec_version_when_delegate_has_it(self):
        """HANDBACK missing spec_version when DELEGATE has it should raise error"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "spec_version": "1.0",
        }
        handback = {
            "task_id": "2026-05-30-test-task",
            "type": "HANDBACK",
        }
        with pytest.raises(SpecVersionValidationError):
            validate_spec_version_match(handback, delegate)


class TestMismatchDetectionAndRejection:
    """Test Case 4: Mismatched spec_versions detected and rejected"""

    def test_error_message_for_mismatch(self):
        """Error message should clearly indicate version mismatch"""
        delegate = {
            "task_id": "2026-05-30-test-task",
            "type": "DELEGATE",
            "spec_version": "1.0",
        }
        handback = {
            "task_id": "2026-05-30-test-task",
            "type": "HANDBACK",
            "spec_version": "2.0",
        }
        with pytest.raises(SpecVersionValidationError) as exc_info:
            validate_spec_version_match(handback, delegate)
        
        error_msg = str(exc_info.value)
        assert "2026-05-30-test-task" in error_msg
        assert "1.0" in error_msg
        assert "2.0" in error_msg

    def test_multiple_version_mismatches_detected(self):
        """Should detect any spec_version mismatch, not just the first one"""
        test_cases = [
            ("1.0", "1.1"),
            ("1.0", "2.0"),
            ("1.1-2026-05-28", "1.1-2026-05-29"),
            ("2.0-rc1", "2.0-rc2"),
        ]
        for delegate_version, handback_version in test_cases:
            delegate = {
                "task_id": "2026-05-30-test-task",
                "type": "DELEGATE",
                "spec_version": delegate_version,
            }
            handback = {
                "task_id": "2026-05-30-test-task",
                "type": "HANDBACK",
                "spec_version": handback_version,
            }
            with pytest.raises(SpecVersionValidationError):
                validate_spec_version_match(handback, delegate)


class TestAuditQueries:
    """Test Case 5: Audit queries work - find_tasks_by_spec_version()"""

    def test_find_tasks_by_spec_version_single_match(self):
        """find_tasks_by_spec_version() should find tasks matching spec version"""
        # Mock task data
        tasks = [
            {
                "task_id": "2026-05-30-task-001",
                "type": "DELEGATE",
                "spec_version": "1.0",
            },
            {
                "task_id": "2026-05-30-task-002",
                "type": "DELEGATE",
                "spec_version": "1.1",
            },
            {
                "task_id": "2026-05-30-task-003",
                "type": "DELEGATE",
                "spec_version": "1.0",
            },
        ]
        
        results = find_tasks_by_spec_version(tasks, "1.0")
        assert len(results) == 2
        assert all(task["spec_version"] == "1.0" for task in results)
        assert "2026-05-30-task-001" in [t["task_id"] for t in results]
        assert "2026-05-30-task-003" in [t["task_id"] for t in results]

    def test_find_tasks_by_spec_version_no_match(self):
        """find_tasks_by_spec_version() should return empty list for no matches"""
        tasks = [
            {
                "task_id": "2026-05-30-task-001",
                "type": "DELEGATE",
                "spec_version": "1.0",
            },
            {
                "task_id": "2026-05-30-task-002",
                "type": "DELEGATE",
                "spec_version": "1.0",
            },
        ]
        
        results = find_tasks_by_spec_version(tasks, "2.0")
        assert len(results) == 0

    def test_find_tasks_by_spec_version_with_dates(self):
        """find_tasks_by_spec_version() should find tasks with date-suffixed versions"""
        tasks = [
            {
                "task_id": "2026-05-30-task-001",
                "type": "DELEGATE",
                "spec_version": "1.0-2026-05-28",
            },
            {
                "task_id": "2026-05-30-task-002",
                "type": "DELEGATE",
                "spec_version": "1.0-2026-05-29",
            },
            {
                "task_id": "2026-05-30-task-003",
                "type": "DELEGATE",
                "spec_version": "1.0-2026-05-28",
            },
        ]
        
        results = find_tasks_by_spec_version(tasks, "1.0-2026-05-28")
        assert len(results) == 2
        assert "2026-05-30-task-001" in [t["task_id"] for t in results]
        assert "2026-05-30-task-003" in [t["task_id"] for t in results]


class TestSpecVersionValidationPattern:
    """Test Case 6: Pattern validation - regex compliance"""

    def test_pattern_matches_specification(self):
        """Pattern should match exactly: ^\d+\.\d+(-.+)?$"""
        pattern = r"^\d+\.\d+(-.+)?$"
        
        # Should match
        import re
        assert re.match(pattern, "1.0") is not None
        assert re.match(pattern, "1.1") is not None
        assert re.match(pattern, "10.5") is not None
        assert re.match(pattern, "1.0-rc1") is not None
        assert re.match(pattern, "1.0-2026-05-28") is not None
        assert re.match(pattern, "2.0-alpha-beta-gamma") is not None
        
        # Should not match
        assert re.match(pattern, "v1.0") is None
        assert re.match(pattern, "1") is None
        assert re.match(pattern, "1.0.0") is None
        assert re.match(pattern, ".1.0") is None
        assert re.match(pattern, "1.0.") is None

    def test_pattern_allows_multi_part_suffix(self):
        """Pattern should allow multi-part suffixes after hyphen"""
        import re
        pattern = r"^\d+\.\d+(-.+)?$"
        
        assert re.match(pattern, "1.0-2026-05-28-v1-rc1") is not None
        assert re.match(pattern, "2.1-alpha-beta-gamma") is not None


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_spec_version_with_leading_zeros(self):
        """Should handle versions with leading zeros (though discouraged)"""
        # Pattern allows 01.02, but it's not recommended
        assert validate_spec_version_format("01.02") is True
        assert validate_spec_version_format("1.01") is True

    def test_spec_version_with_large_numbers(self):
        """Should handle large version numbers"""
        assert validate_spec_version_format("999.999") is True
        assert validate_spec_version_format("10.20") is True

    def test_spec_version_error_includes_context(self):
        """Error messages should include task_id for debugging"""
        delegate = {
            "task_id": "2026-05-30-important-task",
            "type": "DELEGATE",
            "spec_version": "1.0",
        }
        handback = {
            "task_id": "2026-05-30-important-task",
            "type": "HANDBACK",
            "spec_version": "1.5",
        }
        
        with pytest.raises(SpecVersionValidationError) as exc_info:
            validate_spec_version_match(handback, delegate)
        
        assert "2026-05-30-important-task" in str(exc_info.value)
