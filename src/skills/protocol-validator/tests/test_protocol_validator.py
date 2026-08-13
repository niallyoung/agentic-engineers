"""
Tests for protocol-validator skill.

Coverage:
- Core field validation (7 required DELEGATE fields)
- Extension field validation (optional fields)
- Unknown field handling (forward-compatibility)
- Performance targets (<5ms)
- Backward compatibility with Phase 1-3 DELEGATEs
- HANDBACK validation
"""

import pytest
import time
from pathlib import Path
import yaml

# Import validator
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from protocol_validator import (
    ProtocolValidator,
    ValidationResult,
    VALID_STATUSES,
    LEGACY_STATUS_ALIASES,
    EnumDriftFinding,
    EnumDriftReport,
    scan_status_enum_drift,
    _extract_status_set,
)


@pytest.fixture
def validator():
    """Initialize validator with default spec."""
    return ProtocolValidator()


@pytest.fixture
def valid_delegate():
    """A fully valid DELEGATE."""
    return {
        'task_id': 'feature-x-001',
        'skill': 'queue-management',
        'agent': 'senior-engineer',
        'scope': 'Implement feature X with comprehensive testing and documentation across all modules and components for production readiness',
        'success_criteria': [
            'All tests pass with 100% coverage',
            'Code reviewed and approved by team',
            'Documentation complete and reviewed',
        ],
        'plan': [
            'Design API contract and data model with schema validation',
            'Implement core business logic with comprehensive error handling and logging',
            'Write integration tests and performance benchmarks to verify correctness',
            'Document API and create detailed usage guide for all stakeholders',
        ],
        'context': 'Feature X is critical for Q3 roadmap delivery. See SPEC.md for detailed requirements and acceptance criteria that must be met.',
    }


@pytest.fixture
def valid_handback():
    """A fully valid HANDBACK."""
    return {
        'task_id': 'feature-x-001',
        'status': 'success',
        'output': {'feature_implemented': True, 'tests_passing': 1203},
        'metrics': {
            'quality': 0.96,
            'tokens': 45000,
            'cost': 0.32,
            'duration_seconds': 3600,
        }
    }


class TestDelegateCoreFieIds:
    """Test validation of 7 required DELEGATE core fields."""

    def test_validate_delegate_all_core_fields_present(self, validator, valid_delegate):
        """All 7 core fields present => valid"""
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_delegate_missing_task_id(self, validator, valid_delegate):
        """Missing task_id => error"""
        del valid_delegate['task_id']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('task_id' in e for e in result.errors)

    def test_validate_delegate_invalid_task_id_format(self, validator, valid_delegate):
        """task_id not kebab-case or wrong length => error"""
        # Test: starts with uppercase
        valid_delegate['task_id'] = 'TaskID-001'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('task_id' in e for e in result.errors)
        
        # Test: too short (2 chars)
        valid_delegate['task_id'] = 'ab'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        
        # Test: too long (>50 chars)
        valid_delegate['task_id'] = 'a' + 'b' * 49 + 'c'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False

    def test_validate_delegate_valid_task_id_formats(self, validator, valid_delegate):
        """Test various valid task_id formats"""
        valid_ids = [
            'abc',  # 3 chars minimum
            'a-b',  # 3 chars with hyphen
            'feature-x-001',  # with hyphens
            'a1b',  # lowercase + digit
            'task-name-123-final',  # multiple hyphens
        ]
        for task_id in valid_ids:
            valid_delegate['task_id'] = task_id
            result = validator.validate_delegate(valid_delegate)
            assert result.valid is True, f"Expected valid task_id: {task_id}"

    def test_validate_delegate_missing_skill(self, validator, valid_delegate):
        """Missing or invalid skill => error"""
        del valid_delegate['skill']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('skill' in e for e in result.errors)

    def test_validate_delegate_unknown_skill(self, validator, valid_delegate):
        """Skill that doesn't exist in skills/ => error"""
        valid_delegate['skill'] = 'nonexistent-skill-xyz'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('skill' in e and 'unknown' in e for e in result.errors)

    def test_validate_delegate_missing_agent(self, validator, valid_delegate):
        """Missing agent => error"""
        del valid_delegate['agent']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('agent' in e for e in result.errors)

    def test_validate_delegate_invalid_agent(self, validator, valid_delegate):
        """Agent not in valid set => error"""
        valid_delegate['agent'] = 'unknown-agent'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('agent' in e for e in result.errors)

    def test_validate_delegate_valid_agents(self, validator, valid_delegate):
        """Test all valid agent values"""
        valid_agents = [
            'orchestrator', 'engineer', 'senior-engineer', 'lead-engineer',
            'principal-engineer', 'security-engineer', 'quality-engineer', 'model-engineer'
        ]
        for agent in valid_agents:
            valid_delegate['agent'] = agent
            result = validator.validate_delegate(valid_delegate)
            assert result.valid is True, f"Expected valid agent: {agent}"

    def test_validate_delegate_scope_word_count(self, validator, valid_delegate):
        """scope must be >=15 words"""
        # Test: too short
        valid_delegate['scope'] = 'Do something with feature test'  # 5 words
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('scope' in e for e in result.errors)
        
        # Test: exactly 15 words
        valid_delegate['scope'] = 'Do implement something with feature and testing plus documentation for the system and user experience'  # 15 words
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True

    def test_validate_delegate_missing_scope(self, validator, valid_delegate):
        """Missing scope => error"""
        del valid_delegate['scope']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False

    def test_validate_delegate_success_criteria_required(self, validator, valid_delegate):
        """success_criteria must be non-empty array"""
        # Test: missing
        del valid_delegate['success_criteria']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        
        # Test: empty array
        valid_delegate['success_criteria'] = []
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False

    def test_validate_delegate_success_criteria_valid(self, validator, valid_delegate):
        """success_criteria with >=1 item => valid"""
        valid_delegate['success_criteria'] = ['Single criterion']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True

    def test_validate_delegate_plan_min_steps(self, validator, valid_delegate):
        """plan must have >=2 steps"""
        # Test: only 1 step
        valid_delegate['plan'] = ['Do something']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        
        # Test: exactly 2 steps
        valid_delegate['plan'] = ['Do step one', 'Do step two']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True

    def test_validate_delegate_plan_step_word_count(self, validator, valid_delegate):
        """Each plan step must be >=3 words (9 chars minimum)"""
        valid_delegate['plan'] = [
            'Do something here with details',  # OK
            'Do it',  # Only 2 words, should fail
        ]
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('plan' in e for e in result.errors)

    def test_validate_delegate_context_string(self, validator, valid_delegate):
        """context as string must be >=20 words"""
        # Test: too short
        valid_delegate['context'] = 'Short context here'  # 3 words
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        
        # Test: exactly 20 words
        valid_delegate['context'] = ' '.join(['word'] * 20)
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True

    def test_validate_delegate_context_array(self, validator, valid_delegate):
        """context as array must have >=1 items"""
        # Test: empty array
        valid_delegate['context'] = []
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        
        # Test: 1 item
        valid_delegate['context'] = ['Some context string']
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True


class TestDelegateExtensions:
    """Test validation of optional extension fields."""

    def test_validate_delegate_extension_effort_enum(self, validator, valid_delegate):
        """effort must be low|medium|high if present"""
        valid_delegate['effort'] = 'medium'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True
        
        valid_delegate['effort'] = 'high-complexity'  # Invalid
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('effort' in e for e in result.errors)

    def test_validate_delegate_extension_priority(self, validator, valid_delegate):
        """priority must be 1-10 if present"""
        valid_delegate['priority'] = 5
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True
        
        valid_delegate['priority'] = 11  # Out of range
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False
        assert any('priority' in e for e in result.errors)

    def test_validate_delegate_extension_budget(self, validator, valid_delegate):
        """budget must be non-negative number if present"""
        valid_delegate['budget'] = 1000.50
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True
        
        valid_delegate['budget'] = -100  # Negative
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False

    def test_validate_delegate_extension_parent_task_id(self, validator, valid_delegate):
        """parent_task_id must be string if present"""
        valid_delegate['parent_task_id'] = 'parent-task-001'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True
        
        valid_delegate['parent_task_id'] = 123  # Wrong type
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is False


class TestUnknownFields:
    """Test forward-compatibility with unknown fields."""

    def test_validate_delegate_unknown_field_logged_as_warning(self, validator, valid_delegate):
        """Unknown field => warning, not error"""
        valid_delegate['future_field'] = 'some value'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True  # Still valid despite unknown field
        assert any('future_field' in w for w in result.warnings)

    def test_validate_delegate_multiple_unknown_fields(self, validator, valid_delegate):
        """Multiple unknown fields => multiple warnings"""
        valid_delegate['field_a'] = 'value_a'
        valid_delegate['field_b'] = 'value_b'
        result = validator.validate_delegate(valid_delegate)
        assert result.valid is True
        assert len(result.warnings) >= 2

    def test_validate_handback_unknown_field(self, validator, valid_handback):
        """Unknown field in HANDBACK => warning"""
        valid_handback['future_field'] = 'value'
        result = validator.validate_handback(valid_handback)
        assert result.valid is True
        assert any('future_field' in w for w in result.warnings)


class TestHandbackValidation:
    """Test HANDBACK validation."""

    def test_validate_handback_all_core_fields_present(self, validator, valid_handback):
        """All 4 core HANDBACK fields present => valid"""
        result = validator.validate_handback(valid_handback)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_handback_missing_task_id(self, validator, valid_handback):
        """Missing task_id => error"""
        del valid_handback['task_id']
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_missing_status(self, validator, valid_handback):
        """Missing status => error"""
        del valid_handback['status']
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_invalid_status(self, validator, valid_handback):
        """Invalid status value => error"""
        valid_handback['status'] = 'completed'  # Should be 'success'
        result = validator.validate_handback(valid_handback)
        assert result.valid is False
        assert any('status' in e for e in result.errors)

    def test_validate_handback_valid_statuses(self, validator, valid_handback):
        """Test all valid status values"""
        valid_statuses = ['success', 'failure', 'partial', 'blocked', 'escalate']
        for status in valid_statuses:
            valid_handback['status'] = status
            result = validator.validate_handback(valid_handback)
            assert result.valid is True, f"Expected valid status: {status}"

    def test_validate_handback_children_results_dict(self, validator, valid_handback):
        """children_results should be a dict keyed by child task_id."""
        valid_handback['children_results'] = {
            'child-task-001': {
                'status': 'success',
                'output': {'notes': 'done'},
                'quality': 0.9,
            }
        }
        result = validator.validate_handback(valid_handback)
        assert result.valid is True
        assert validator.get_spec()['handback']['extensions']['children_results']['type'] == 'object'

    def test_validate_handback_missing_output(self, validator, valid_handback):
        """Missing output => error"""
        del valid_handback['output']
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_missing_metrics(self, validator, valid_handback):
        """Missing metrics => error"""
        del valid_handback['metrics']
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_metrics_quality_range(self, validator, valid_handback):
        """metrics.quality must be 0.0-1.0"""
        valid_handback['metrics']['quality'] = 1.5  # Too high
        result = validator.validate_handback(valid_handback)
        assert result.valid is False
        assert any('quality' in e for e in result.errors)
        
        valid_handback['metrics']['quality'] = -0.1  # Too low
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_metrics_tokens_non_negative(self, validator, valid_handback):
        """metrics.tokens must be >=0"""
        valid_handback['metrics']['tokens'] = -100
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_metrics_cost_non_negative(self, validator, valid_handback):
        """metrics.cost must be >=0"""
        valid_handback['metrics']['cost'] = -1.0
        result = validator.validate_handback(valid_handback)
        assert result.valid is False

    def test_validate_handback_metrics_duration_non_negative(self, validator, valid_handback):
        """metrics.duration_seconds must be >=0"""
        valid_handback['metrics']['duration_seconds'] = -100
        result = validator.validate_handback(valid_handback)
        assert result.valid is False


class TestPerformance:
    """Test validation performance targets."""

    def test_validate_delegate_performance_under_5ms(self, validator, valid_delegate):
        """Validation should complete in <5ms"""
        result = validator.validate_delegate(valid_delegate)
        assert result.duration_ms < 5.0, f"Validation took {result.duration_ms}ms (target: <5ms)"

    def test_validate_handback_performance_under_5ms(self, validator, valid_handback):
        """HANDBACK validation should complete in <5ms"""
        result = validator.validate_handback(valid_handback)
        assert result.duration_ms < 5.0, f"Validation took {result.duration_ms}ms (target: <5ms)"

    def test_validate_performance_batch(self, validator, valid_delegate):
        """Validate 100 DELEGATEs in <500ms total"""
        start_time = time.time()
        for i in range(100):
            delegate = valid_delegate.copy()
            delegate['task_id'] = f'task-{i:03d}'
            result = validator.validate_delegate(delegate)
            assert result.valid is True
        duration_ms = (time.time() - start_time) * 1000
        avg_ms = duration_ms / 100
        assert avg_ms < 5.0, f"Average validation {avg_ms}ms (target: <5ms)"


class TestBackwardCompatibility:
    """Test compatibility with Phase 1-3 DELEGATEs."""

    def test_validate_phase3_delegate(self, validator):
        """Phase 3 DELEGATEs should still validate"""
        # Typical Phase 3 format
        delegate = {
            'task_id': 'implement-auth-001',
            'skill': 'queue-management',
            'agent': 'senior-engineer',
            'scope': 'Implement JWT authentication with comprehensive refresh tokens and role-based access control for all API endpoints',
            'success_criteria': [
                'All authentication tests pass with 100% coverage',
                'Performance benchmarks show <50ms auth overhead',
                'Security audit shows no vulnerabilities',
            ],
            'plan': [
                'Design JWT token structure and expiration strategy',
                'Implement authentication middleware with error handling',
                'Create comprehensive test suite for all auth flows',
                'Document authentication API and integration guide',
            ],
            'context': [
                'Authentication is critical for security',
                'See docs/AUTH-SPEC.md for requirements',
                'Must support OAuth 2.0 token refresh flow',
            ],
            'effort': 'high',
            'priority': 8,
        }
        result = validator.validate_delegate(delegate)
        assert result.valid is True

    def test_validate_delegate_with_unknown_phase4_field(self, validator):
        """Delegate from future Phase with unknown field should still validate"""
        delegate = {
            'task_id': 'future-task-001',
            'skill': 'queue-management',
            'agent': 'engineer',
            'scope': 'Do something meaningful and important in the future with new capabilities and features for system improvement',
            'success_criteria': ['Success criterion'],
            'plan': ['Step one here now please', 'Step two here now please'],
            'context': 'This is detailed context information with required minimum length for proper validation that meets the requirements and all standards specified',
            'future_field': 'value',  # Unknown in current spec
        }
        result = validator.validate_delegate(delegate)
        assert result.valid is True  # Should still validate


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_fields(self, validator, valid_delegate):
        """ValidationResult should have all expected fields"""
        result = validator.validate_delegate(valid_delegate)
        assert hasattr(result, 'valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'duration_ms')
        assert hasattr(result, 'field_types')
        
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.duration_ms, float)
        assert isinstance(result.field_types, dict)

    def test_validation_result_field_types(self, validator, valid_delegate):
        """field_types should contain inferred types"""
        result = validator.validate_delegate(valid_delegate)
        assert 'task_id' in result.field_types
        assert result.field_types['task_id'] == 'str'
        assert 'plan' in result.field_types
        assert result.field_types['plan'] == 'list'


class TestProtocolValidator:
    """Test ProtocolValidator class."""

    def test_validator_initialization(self, validator):
        """Validator should initialize successfully"""
        assert validator is not None
        assert validator.version == '1.0'

    def test_get_spec(self, validator):
        """get_spec() should return spec dict"""
        spec = validator.get_spec()
        assert isinstance(spec, dict)
        assert 'delegate' in spec
        assert 'handback' in spec

    def test_get_version(self, validator):
        """get_version() should return spec version"""
        version = validator.get_version()
        assert version == '1.0'

    def test_validator_with_custom_spec(self, tmp_path):
        """Should support custom spec file"""
        # Create custom spec
        custom_spec = {
            'version': '1.1',
            'delegate': {
                'core_fields': {
                    'task_id': {'type': 'string'},
                    'skill': {'type': 'string'},
                    'agent': {'type': 'string'},
                    'scope': {'type': 'string'},
                    'success_criteria': {'type': 'array'},
                    'plan': {'type': 'array'},
                    'context': {'type': 'string'},
                },
                'extensions': {},
            },
            'handback': {
                'core_fields': {
                    'task_id': {'type': 'string'},
                    'status': {'type': 'string'},
                    'output': {},
                    'metrics': {'type': 'object'},
                },
                'extensions': {},
            },
        }
        
        spec_file = tmp_path / 'custom-spec.yaml'
        with open(spec_file, 'w') as f:
            yaml.dump(custom_spec, f)
        
        validator = ProtocolValidator(spec_path=str(spec_file))
        assert validator.version == '1.1'


class TestEnumDriftDetection:
    """Tests for scan_status_enum_drift — HANDBACK status enum cross-file consistency."""

    def test_canonical_valid_statuses_constants(self):
        """VALID_STATUSES must include the five canonical values and nothing else."""
        assert VALID_STATUSES == {"success", "failure", "partial", "blocked", "escalate"}

    def test_legacy_aliases_map_to_canonical(self):
        """Legacy aliases must all map to values in VALID_STATUSES."""
        for legacy, canonical in LEGACY_STATUS_ALIASES.items():
            assert canonical in VALID_STATUSES, (
                f"Legacy alias '{legacy}' maps to '{canonical}' which is not in VALID_STATUSES"
            )

    def test_enum_drift_report_dataclass(self):
        """EnumDriftReport.has_drift reflects presence of findings."""
        report_clean = EnumDriftReport(
            canonical=VALID_STATUSES,
            legacy_aliases=set(LEGACY_STATUS_ALIASES.keys()),
            findings=[],
        )
        assert report_clean.has_drift is False

        finding = EnumDriftFinding(
            path="some/file.py",
            name="MY_STATUSES",
            found={"complete", "failed"},
            expected=VALID_STATUSES,
            missing={"success", "failure", "partial", "blocked", "escalate"},
            extra=set(),
        )
        report_dirty = EnumDriftReport(
            canonical=VALID_STATUSES,
            legacy_aliases=set(LEGACY_STATUS_ALIASES.keys()),
            findings=[finding],
        )
        assert report_dirty.has_drift is True

    def test_enum_drift_report_to_text_clean(self):
        """Clean report renders without listing drift locations."""
        report = EnumDriftReport(
            canonical=VALID_STATUSES,
            legacy_aliases=set(),
            findings=[],
        )
        text = report.to_text()
        assert "No" in text or "drift" in text.lower()

    def test_enum_drift_report_to_text_dirty(self):
        """Dirty report names the drifted file and missing values."""
        finding = EnumDriftFinding(
            path="src/skills/queue-management/scripts/queue_ops.py",
            name="VALID_HANDBACK_STATUSES",
            found={"complete", "failed", "partial", "blocked", "escalate"},
            expected=VALID_STATUSES,
            missing={"success", "failure"},
            extra=set(),
        )
        report = EnumDriftReport(
            canonical=VALID_STATUSES,
            legacy_aliases=set(),
            findings=[finding],
        )
        text = report.to_text()
        assert "queue_ops" in text
        assert "success" in text or "failure" in text

    def test_extract_status_set_simple_set_literal(self):
        """_extract_status_set parses a Python set literal."""
        source = 'VALID_STATUSES = {"success", "failure", "partial", "blocked", "escalate"}\n'
        result = _extract_status_set(source, "VALID_STATUSES")
        assert result == {"success", "failure", "partial", "blocked", "escalate"}

    def test_extract_status_set_list_literal(self):
        """_extract_status_set parses a Python list literal."""
        source = 'VALID_STATUSES = ["success", "failure", "partial"]\n'
        result = _extract_status_set(source, "VALID_STATUSES")
        assert result == {"success", "failure", "partial"}

    def test_extract_status_set_returns_none_when_not_found(self):
        """_extract_status_set returns None when variable is absent."""
        source = '# No statuses here\nFOO = 42\n'
        result = _extract_status_set(source, "MISSING_VAR")
        assert result is None

    def test_scan_status_enum_drift_live_repo(self):
        """Scan the actual repo; the canonical HANDBACK enum should be clean."""
        report = scan_status_enum_drift()
        assert not report.has_drift, report.to_text()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
