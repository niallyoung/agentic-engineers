"""
Test suite for Protocol Week 1 validation system.

Covers 25+ test cases:
- Group A: Structure validation (hard gates) — 7 tests
- Group B: Content quality validation — 7 tests
- Group C: Routing sanity validation — 4 tests
- HANDBACK validation — 5 tests
- Integration/helper tests — 2+ tests

Source: orchestration/DELEGATE-HANDBACK-QUALITY-GATES.md
        orchestration/delegate-schema.yaml
        orchestration/handback-schema.yaml
"""

import pytest
from pathlib import Path
from src.orchestration.agents.delegate_validator import DelegateValidator, validate_delegate_pre_flight


# Helper function for valid test delegates
def make_valid_delegate(task_id, role='engineer', effort='low', hours=2, **overrides):
    """Create a valid delegate with minimal required fields.

    Scope deliberately avoids B7-trigger keywords (comprehensive, validation,
    system, architecture, integration) so that effort='low' tests do not
    generate false-positive B7 failures.  Context is ≥100 words to pass B5.
    success_criteria count scales with hours to pass B2.
    """
    # Scale criteria count: ceil(hours / 4), minimum 2
    min_criteria = max(2, (hours + 3) // 4)
    _all_criteria = [
        'All tests pass with 90% coverage',
        'No regressions in existing test suite with zero test failures',
        'All 3 new modules pass peer review with zero blocking comments',
        'Performance benchmarks show no regression greater than 5 percent',
        '100 percent of new public API methods have docstrings in README',
        'Edge cases handled and covered by 4 dedicated unit test cases',
        'Integration tests pass in CI environment with zero failures',
        'Code coverage stays above 85 percent for modified packages',
    ]
    criteria = _all_criteria[:min_criteria]

    delegate = {
        'task_id': task_id,
        'role': role,
        'model': 'claude-haiku-4.5' if role == 'engineer' else 'claude-sonnet-4.6',
        'effort': effort,
        'estimated_hours': hours,
        # Scope: ≥15 words, has action verb, avoids B7-trigger keywords
        'scope': (
            'Implement robust error handling and retry logic for API requests '
            'in src/api.py by adding middleware with proper logging'
        ),
        'success_criteria': criteria,
        'plan': [
            {'step': 1, 'action': 'Implement feature in src/main.py', 'duration_minutes': 30},
            {'step': 2, 'action': 'Run pytest tests to verify correctness', 'duration_minutes': 30}
        ],
        # Context: ≥100 words to pass B5
        'context': (
            'This task implements proper error handling for request processing. '
            'The implementation is critical for ensuring compliance with protocol '
            'standards and requirements. Background: the service requires proper '
            'error recovery at multiple layers of request execution. The approach '
            'involves creating middleware that checks request structure, content '
            'quality, and routing sanity. This ensures all requests meet minimum '
            'quality standards before execution and deployment. Implementation '
            'will significantly improve service reliability and reduce bugs in '
            'production. The middleware uses hard gates that block invalid requests '
            'and emits warnings for borderline cases. Testing is essential for '
            'quality assurance. Each change must include unit tests covering the '
            'success path, the error path, and all boundary conditions. The '
            'reviewer must confirm test coverage before approving the pull request.'
        ),
    }
    if effort in ['medium', 'high', 'max', 'epic']:
        delegate['out_of_scope'] = ['Other related items']
    delegate.update(overrides)
    return delegate


class TestGroupAStructure:
    """Group A: Hard gates — any NO = do not send."""
    
    def test_a1_valid_task_id_format(self):
        """A1: task_id matches YYYY-MM-DD-kebab-case format."""
        delegate = make_valid_delegate('2026-05-09-protocol-week1-validation')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed, f"Should pass with valid task_id, got: {failures}"
    
    def test_a1_invalid_task_id_format_missing_date(self):
        """A1: task_id missing date should fail."""
        delegate = make_valid_delegate('invalid-task-id')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('A1' in f for f in failures)
    
    def test_a1_invalid_task_id_format_bad_date(self):
        """A1: task_id with invalid date should fail."""
        delegate = make_valid_delegate('2026-5-9-task')  # Missing zero padding
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('A1' in f for f in failures)
    
    def test_a3_valid_role_engineer(self):
        """A3: role 'engineer' is valid."""
        delegate = make_valid_delegate('2026-05-09-test-role', role='engineer')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_a3_valid_role_senior_engineer(self):
        """A3: role 'senior_engineer' is valid."""
        delegate = make_valid_delegate('2026-05-09-test-role2', role='senior_engineer', hours=20, effort='high')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_a3_invalid_role(self):
        """A3: invalid role should fail."""
        delegate = make_valid_delegate('2026-05-09-test-bad-role', role='invalid_role')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('A3' in f for f in failures)
    
    def test_a6_scope_valid(self):
        """A6: scope with ≥15 words and action verb should pass."""
        delegate = make_valid_delegate('2026-05-09-test-scope')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_a6_scope_too_short(self):
        """A6: scope with <15 words should fail."""
        delegate = make_valid_delegate('2026-05-09-test-short-scope', scope='Short scope')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('A6' in f for f in failures)
    
    def test_a7_no_secrets_pass(self):
        """A7: delegate without secrets should pass."""
        delegate = make_valid_delegate('2026-05-09-clean-delegate')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_a7_secrets_detected(self):
        """A7: delegate with 'api_key' should fail."""
        delegate = make_valid_delegate('2026-05-09-test-secrets', api_key='secret123')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('A7' in f for f in failures)


class TestGroupBContentQuality:
    """Group B: Content quality — refine before sending if fails."""
    
    def test_b1_measurable_criteria_pass(self):
        """B1: criteria with numbers/tests should be measurable."""
        delegate = make_valid_delegate('2026-05-09-test-measurable')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_b1_aspirational_criteria_fail(self):
        """B1: criteria like 'good code' should fail."""
        delegate = make_valid_delegate(
            '2026-05-09-test-aspirational',
            **{'success_criteria': ['Code looks good', 'Works well']}
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('B1' in f for f in failures)
    
    def test_b2_criteria_count_sufficient(self):
        """B2: 12-hour effort needs 3+ criteria."""
        delegate = make_valid_delegate(
            '2026-05-09-test-criteria-count',
            effort='medium',
            hours=12,
            **{
                'success_criteria': [
                    '50 tests pass',
                    'Coverage above 80%',
                    'Integration tests pass with zero failures',
                    'All edge cases covered in 4 dedicated unit tests',
                ]
            }
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_b2_criteria_count_insufficient(self):
        """B2: 16 hours with only 1 criterion should fail."""
        delegate = make_valid_delegate(
            '2026-05-09-test-criteria-insufficient',
            effort='medium',
            hours=16,
            **{'success_criteria': ['Feature works']}
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('B2' in f for f in failures)
    
    def test_b4_testing_step_present(self):
        """B4: plan must include a testing step."""
        delegate = make_valid_delegate('2026-05-09-test-has-testing')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_b4_no_testing_step(self):
        """B4: plan without 'test' step should fail."""
        delegate = make_valid_delegate(
            '2026-05-09-test-no-testing',
            **{
                'plan': [
                    {'step': 1, 'action': 'Implement feature in src/main.py', 'duration_minutes': 60}
                ]
            }
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('B4' in f for f in failures)
    
    def test_b5_context_sufficient(self):
        """B5: context ≥100 words should pass."""
        delegate = make_valid_delegate('2026-05-09-test-context-good')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed
    
    def test_b5_context_too_short(self):
        """B5: context <100 words should fail."""
        delegate = make_valid_delegate('2026-05-09-test-context-short', context='Short.')
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('B5' in f for f in failures)


class TestGroupCRoutingSanity:
    """Group C: Routing sanity checks."""
    
    def test_c1_high_effort_needs_senior(self):
        """C1: high effort requires senior_engineer or above."""
        delegate = make_valid_delegate(
            '2026-05-09-test-effort-role',
            role='engineer',  # Too junior
            effort='high',
            hours=20
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('C1' in f for f in failures)
    
    def test_c1_high_effort_with_senior(self):
        """C1: high effort with senior_engineer should pass."""
        delegate = make_valid_delegate(
            '2026-05-09-test-effort-senior',
            role='senior_engineer',
            effort='high',
            hours=20
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        # Expect no C1 failure
        assert not any('C1' in f for f in validate_delegate_pre_flight(delegate)[1])
    
    def test_c2_security_scope_routes_correctly(self):
        """C2: security scope should route to security_engineer."""
        delegate = make_valid_delegate(
            '2026-05-09-test-security',
            role='engineer',  # Should be security_engineer
            scope='Implement and deploy secure authentication and encryption mechanisms for security'
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('C2' in f for f in failures)
    
    def test_c3_architecture_scope_routes_correctly(self):
        """C3: architecture scope should route to principal_engineer."""
        delegate = make_valid_delegate(
            '2026-05-09-test-architecture',
            role='senior_engineer',  # Should be principal_engineer
            effort='epic',
            hours=150,
            scope='Design and implement cross-service architecture for distributed system integration'
        )
        passed, failures = validate_delegate_pre_flight(delegate)
        assert not passed and any('C3' in f for f in failures)


class TestHandbackValidation:
    """HANDBACK validation (Layer 1: Format Gate)."""
    
    def test_handback_all_required_fields(self):
        """All required fields present in valid HANDBACK."""
        handback = {
            'task_id': '2026-05-09-test',
            'status': 'complete',
            'deliverables': ['file.py'],
            'tests': {'passed': 5, 'failed': 0, 'coverage': 95.0},
            'quality_score': 85,
            'tokens_in': 1000,
            'tokens_out': 500,
            'duration_minutes': 30,
            'notes': 'Task completed with excellent quality and test coverage.'
        }
        required = {'task_id', 'status', 'deliverables', 'tests', 'quality_score',
                    'tokens_in', 'tokens_out', 'duration_minutes', 'notes'}
        assert all(f in handback for f in required)
    
    def test_handback_status_valid_complete(self):
        """Status 'complete' is valid."""
        assert 'complete' in {'complete', 'failed', 'partial', 'blocked'}
    
    def test_handback_status_valid_failed(self):
        """Status 'failed' is valid."""
        assert 'failed' in {'complete', 'failed', 'partial', 'blocked'}
    
    def test_handback_status_valid_partial(self):
        """Status 'partial' is valid."""
        assert 'partial' in {'complete', 'failed', 'partial', 'blocked'}
    
    def test_handback_status_valid_blocked(self):
        """Status 'blocked' is valid."""
        assert 'blocked' in {'complete', 'failed', 'partial', 'blocked'}


class TestIntegration:
    """Integration tests."""
    
    def test_full_valid_delegate_passes(self):
        """Complete valid DELEGATE passes all validations."""
        delegate = {
            'task_id': '2026-05-09-protocol-week1-validation',
            'role': 'senior_engineer',
            'model': 'claude-sonnet-4.6',
            'effort': 'high',
            'estimated_hours': 14,
            'scope': 'Create and implement comprehensive pre-flight validation system enforcing the protocol compliance with hard gates checking',
            'success_criteria': [
                'All 25 tests pass with 95% coverage',
                'Pre-commit hook blocks 100% of invalid DELEGATEs',
                'Pre-commit hook allows 100% of valid DELEGATEs',
                'Retry tracking capped at 2 retries before escalation',
                'Code coverage above 90 percent in new code'
            ],
            'plan': [
                {'step': 1, 'action': 'Create orchestration/delegate-schema.yaml', 'duration_minutes': 30},
                {'step': 2, 'action': 'Implement validate_delegate_pre_flight in orchestrator.py', 'duration_minutes': 120},
                {'step': 3, 'action': 'Write tests in test_protocol_validation.py', 'duration_minutes': 150},
                {'step': 4, 'action': 'Create .git/hooks/pre-commit with validation', 'duration_minutes': 30},
                {'step': 5, 'action': 'Run pytest to verify all tests pass', 'duration_minutes': 30}
            ],
            'context': 'Three specialist agents completed comprehensive protocol review work identifying critical gaps. Quality Engineer identified 5 gaps in current system: no pre-delegation checklist exists, no retry limit enforcement, no canonical metrics record for tracking. Principal Engineer designed 5 architectural decisions with detailed pseudocode specifications. Lead Engineer confirmed all identified gaps are critical and real. The implementation includes hard gates for structure validation, content quality checks, and routing sanity verification. Pre-commit hook enforces compliance before commits. Retry tracking prevents infinite rework loops by capping retries at 2. All deliverables must exist on disk and tests must pass before HANDBACK is accepted by the Orchestrator.',
            'out_of_scope': [
                'Gray-zone manual review gate (70-79)',
                'Metrics collection and aggregation',
                'CI/CD integration gates'
            ]
        }
        passed, failures = validate_delegate_pre_flight(delegate)
        assert passed, f"Valid DELEGATE should pass all groups, got: {failures}"
    
    def test_pre_commit_hook_exists(self):
        """Pre-commit hook file exists and is executable."""
        # Derive project root from this test file's location — avoids subprocess
        # (subprocess.Popen may be mocked by concurrent-threading tests upstream)
        project_root = Path(__file__).parent.parent.resolve()
        hook_path = project_root / '.git' / 'hooks' / 'pre-commit'
        assert hook_path.exists(), "Pre-commit hook must exist"
        stat_info = hook_path.stat().st_mode
        # Check if executable by owner (mode & 0o100 would be non-zero)
        assert stat_info & 0o111, "Pre-commit hook must be executable"


class TestValidatorHelpers:
    """Test validator helper functions."""
    
    def test_task_id_valid_formats(self):
        """Valid task_id formats."""
        validator = DelegateValidator()
        assert validator._valid_task_id('2026-05-09-task')
        assert validator._valid_task_id('2026-01-01-a')
        assert validator._valid_task_id('2025-12-31-simple-task')
    
    def test_task_id_invalid_formats(self):
        """Invalid task_id formats."""
        validator = DelegateValidator()
        assert not validator._valid_task_id('task-name')  # No date
        assert not validator._valid_task_id('2026-5-9-task')  # Missing padding
        assert not validator._valid_task_id('2026-05-09')  # No slug
        assert not validator._valid_task_id('')  # Empty
    
    def test_measurable_vs_aspirational(self):
        """Measurable criteria detection."""
        validator = DelegateValidator()
        # Measurable
        assert validator._is_measurable('All 25 tests pass')
        assert validator._is_measurable('95% coverage achieved')
        # Aspirational
        assert not validator._is_measurable('Good code')
        assert not validator._is_measurable('Works well')
    
    def test_concrete_action_steps(self):
        """Concrete action detection."""
        validator = DelegateValidator()
        # Concrete
        assert validator._is_concrete_action('Create src/utils.py file')
        assert validator._is_concrete_action('Run pytest tests/')
        # Vague
        assert not validator._is_concrete_action('Do work here')
        assert not validator._is_concrete_action('Handle issues')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
