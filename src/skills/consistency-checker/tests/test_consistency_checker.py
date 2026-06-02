"""
Tests for consistency-checker skill.

Coverage:
- Queue scanning (discovering sessions, tasks, states)
- Schema validation per task
- Structural validation (orphans, cycles, depth/width)
- Rate limit checking
- Report generation
- Backward compatibility
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
import yaml

# Import checker
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from consistency_checker import ConsistencyChecker, ConsistencyReport


@pytest.fixture
def temp_queue():
    """Create a temporary queue directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / 'queue'
        queue_path.mkdir()
        yield queue_path


@pytest.fixture
def checker(temp_queue):
    """Create a checker with temporary queue."""
    return ConsistencyChecker(queue_path=str(temp_queue))


@pytest.fixture
def valid_delegate():
    """A valid DELEGATE."""
    return {
        'task_id': 'test-task-001',
        'skill': 'queue-management',
        'agent': 'engineer',
        'scope': 'This is a valid scope with at least fifteen words to satisfy the requirement for comprehensive scope definition',
        'success_criteria': ['Success criterion'],
        'plan': ['Step one here now please do this', 'Step two here now please do this'],
        'context': 'Context with at least twenty words required for validation test case setup and preparation of this particular test implementation scenario here',
    }


@pytest.fixture
def valid_handback():
    """A valid HANDBACK."""
    return {
        'task_id': 'test-task-001',
        'status': 'success',
        'output': {'result': 'done'},
        'metrics': {
            'quality': 0.95,
            'tokens': 1000,
            'cost': 0.50,
            'duration_seconds': 60,
        }
    }


class TestQueueScanning:
    """Test queue discovery and task loading."""

    def test_discover_sessions_empty_queue(self, checker, temp_queue):
        """Empty queue returns no sessions"""
        sessions = checker._discover_sessions()
        assert sessions == []

    def test_discover_sessions_single_session(self, checker, temp_queue):
        """Single session directory discovered"""
        (temp_queue / 'session-1').mkdir()
        sessions = checker._discover_sessions()
        assert sessions == ['session-1']

    def test_discover_sessions_multiple_sessions(self, checker, temp_queue):
        """Multiple session directories discovered and sorted"""
        (temp_queue / 'session-3').mkdir()
        (temp_queue / 'session-1').mkdir()
        (temp_queue / 'session-2').mkdir()
        sessions = checker._discover_sessions()
        assert sessions == ['session-1', 'session-2', 'session-3']

    def test_scan_session_no_tasks(self, checker, temp_queue):
        """Session with no tasks returns empty dict"""
        session_dir = temp_queue / 'session-1'
        session_dir.mkdir()
        (session_dir / 'incoming').mkdir()
        
        tasks = checker._scan_session('session-1')
        assert tasks == {}

    def test_scan_session_with_delegates(self, checker, temp_queue, valid_delegate):
        """Load DELEGATE tasks from session"""
        session_dir = temp_queue / 'session-1'
        (session_dir / 'incoming').mkdir(parents=True)
        
        task_file = session_dir / 'incoming' / 'task-001.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(valid_delegate, f)
        
        tasks = checker._scan_session('session-1')
        assert 'task-001' in tasks
        assert tasks['task-001']['state'] == 'incoming'
        assert tasks['task-001']['data']['task_id'] == 'test-task-001'

    def test_scan_session_multiple_states(self, checker, temp_queue, valid_delegate, valid_handback):
        """Load tasks from multiple queue states"""
        session_dir = temp_queue / 'session-1'
        
        # Create incoming and completed states
        (session_dir / 'incoming').mkdir(parents=True)
        (session_dir / 'completed').mkdir(parents=True)
        
        # Add delegate to incoming
        task_file = session_dir / 'incoming' / 'task-001.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(valid_delegate, f)

        # Add handback to completed. _scan_session keys tasks by the file stem
        # (task_file.stem), so use a distinct filename from the incoming delegate
        # to represent two separate tasks. The handback's task_id is also set
        # distinctly to keep the fixtures self-consistent.
        valid_handback = {**valid_handback, 'task_id': 'test-task-002'}
        task_file = session_dir / 'completed' / 'task-002.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(valid_handback, f)

        tasks = checker._scan_session('session-1')
        assert len(tasks) == 2  # incoming delegate + completed handback (distinct file stems)


class TestSchemaValidation:
    """Test DELEGATE/HANDBACK schema validation."""

    def test_validate_task_valid_delegate(self, checker, valid_delegate):
        """Valid DELEGATE passes validation"""
        task_info = {
            'state': 'incoming',
            'data': valid_delegate,
        }
        is_valid, violations, warnings = checker._validate_task(
            'task-001', task_info, 'session-1'
        )
        assert is_valid is True
        assert len(violations) == 0

    def test_validate_task_invalid_delegate(self, checker, valid_delegate):
        """Invalid DELEGATE fails validation"""
        del valid_delegate['scope']  # Remove required field
        task_info = {
            'state': 'incoming',
            'data': valid_delegate,
        }
        is_valid, violations, warnings = checker._validate_task(
            'task-001', task_info, 'session-1'
        )
        assert is_valid is False
        assert any('scope' in v for v in violations)

    def test_validate_task_unknown_field_warning(self, checker, valid_delegate):
        """Unknown field generates warning but doesn't fail"""
        valid_delegate['future_field'] = 'value'
        task_info = {
            'state': 'incoming',
            'data': valid_delegate,
        }
        is_valid, violations, warnings = checker._validate_task(
            'task-001', task_info, 'session-1'
        )
        assert is_valid is True  # Still valid
        assert any('future_field' in w for w in warnings)


class TestStructuralValidation:
    """Test cycle detection, orphans, depth/width checks."""

    def test_detect_orphaned_parent(self, checker, valid_delegate):
        """Task with non-existent parent flagged as violation"""
        delegate_with_parent = valid_delegate.copy()
        delegate_with_parent['parent_task_id'] = 'nonexistent-parent'
        
        all_tasks = {
            'session-1': {
                'task-001': {
                    'state': 'incoming',
                    'data': delegate_with_parent,
                },
            }
        }
        
        violations = checker._check_structural_issues(all_tasks)
        assert any('orphaned' in v for v in violations)

    def test_detect_cycle_simple(self, checker, valid_delegate):
        """Simple cycle A->B->A detected"""
        task_a = valid_delegate.copy()
        task_a['task_id'] = 'task-a'
        task_a['parent_task_id'] = 'task-b'
        
        task_b = valid_delegate.copy()
        task_b['task_id'] = 'task-b'
        task_b['parent_task_id'] = 'task-a'
        
        all_tasks = {
            'session-1': {
                'task-a': {'state': 'incoming', 'data': task_a},
                'task-b': {'state': 'incoming', 'data': task_b},
            }
        }
        
        violations = checker._check_structural_issues(all_tasks)
        assert any('Cycle' in v for v in violations)

    def test_detect_excessive_children(self, checker, valid_delegate):
        """Parent with >10 children flagged"""
        parent = valid_delegate.copy()
        parent['task_id'] = 'parent-task'
        
        all_tasks = {'session-1': {
            'parent-task': {'state': 'incoming', 'data': parent},
        }}
        
        # Add 11 children
        for i in range(11):
            child = valid_delegate.copy()
            child['task_id'] = f'child-{i:02d}'
            child['parent_task_id'] = 'parent-task'
            all_tasks['session-1'][f'child-{i:02d}'] = {
                'state': 'incoming',
                'data': child,
            }
        
        violations = checker._check_structural_issues(all_tasks)
        assert any('children' in v and '11' in v for v in violations)

    def test_detect_excessive_depth(self, checker, valid_delegate):
        """Chain depth >5 flagged"""
        # Create chain A -> B -> C -> D -> E -> F -> G.
        # Depth is measured in edges, so a 7-node chain has max depth 6 (>5),
        # which is the smallest chain that should trip the depth>5 rule.
        letters = 'ABCDEFG'
        all_tasks = {'session-1': {}}
        
        for i, letter in enumerate(letters):
            task = valid_delegate.copy()
            task['task_id'] = f'task-{letter}'
            if i > 0:
                task['parent_task_id'] = f'task-{letters[i-1]}'
            all_tasks['session-1'][f'task-{letter}'] = {
                'state': 'incoming',
                'data': task,
            }
        
        violations = checker._check_structural_issues(all_tasks)
        assert any('depth' in v and '6' in v for v in violations)


class TestRateLimiting:
    """Test rate limit checks."""

    def test_rate_limit_per_session_ok(self, checker, valid_delegate):
        """Session with <100 incoming tasks passes"""
        all_tasks = {'session-1': {}}
        
        for i in range(50):
            task = valid_delegate.copy()
            task['task_id'] = f'task-{i:03d}'
            all_tasks['session-1'][f'task-{i:03d}'] = {
                'state': 'incoming',
                'data': task,
            }
        
        violations = checker._check_rate_limits(all_tasks)
        # Should not have per-session violations
        assert not any('incoming tasks' in v and '(max 100' in v for v in violations)

    def test_rate_limit_per_session_exceeded(self, checker, valid_delegate):
        """Session with >100 incoming tasks flagged"""
        all_tasks = {'session-1': {}}
        
        for i in range(101):
            task = valid_delegate.copy()
            task['task_id'] = f'task-{i:03d}'
            all_tasks['session-1'][f'task-{i:03d}'] = {
                'state': 'incoming',
                'data': task,
            }
        
        violations = checker._check_rate_limits(all_tasks)
        assert any('101' in v for v in violations)


class TestReportGeneration:
    """Test consistency report creation and format."""

    def test_check_queue_empty_returns_valid_report(self, checker):
        """Empty queue returns valid report with zero counts"""
        report = checker.check_queue()
        assert isinstance(report, ConsistencyReport)
        assert report.total_tasks == 0
        assert report.pass_rate == 1.0

    def test_check_queue_valid_tasks(self, checker, temp_queue, valid_delegate):
        """Queue with valid tasks returns pass rate 1.0"""
        # Create session with valid task
        session_dir = temp_queue / 'session-1'
        (session_dir / 'incoming').mkdir(parents=True)
        
        task_file = session_dir / 'incoming' / 'task-001.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(valid_delegate, f)
        
        report = checker.check_queue()
        assert report.total_tasks == 1
        assert report.valid_count == 1
        assert report.invalid_count == 0
        assert report.pass_rate == 1.0

    def test_report_has_timestamp(self, checker):
        """Report includes ISO 8601 timestamp"""
        report = checker.check_queue()
        # Should be valid ISO format
        datetime.fromisoformat(report.timestamp.replace('Z', '+00:00'))

    def test_report_has_duration(self, checker):
        """Report includes execution duration"""
        report = checker.check_queue()
        assert report.duration_seconds >= 0.0

    def test_report_aggregates_by_state(self, checker, temp_queue, valid_delegate):
        """Report breaks down counts by queue state"""
        session_dir = temp_queue / 'session-1'
        
        # Add task to incoming
        (session_dir / 'incoming').mkdir(parents=True)
        task_file = session_dir / 'incoming' / 'task-001.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(valid_delegate, f)
        
        # Add task to completed
        (session_dir / 'completed').mkdir(parents=True)
        task_file = session_dir / 'completed' / 'task-002.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(valid_delegate, f)
        
        report = checker.check_queue()
        assert 'incoming' in report.by_state
        assert 'completed' in report.by_state


class TestBackwardCompatibility:
    """Test compatibility with Phase 1-3 tasks."""

    def test_phase3_delegate_validates(self, checker, temp_queue):
        """Phase 3 DELEGATE format still validates"""
        delegate = {
            'task_id': 'auth-impl-001',
            'skill': 'queue-management',
            'agent': 'senior-engineer',
            'scope': 'Implement JWT authentication with comprehensive testing and documentation for security across the gateway and all downstream services',
            'success_criteria': ['All tests pass', 'Security reviewed'],
            'plan': ['Design JWT scheme', 'Implement auth flow', 'Test thoroughly end to end', 'Document the integration'],
            'context': 'Critical security component required for the Q1 roadmap delivery; the gateway currently lacks token validation and must be hardened before launch',
            'effort': 'high',
            'priority': 9,
        }
        
        session_dir = temp_queue / 'session-1'
        (session_dir / 'incoming').mkdir(parents=True)
        
        task_file = session_dir / 'incoming' / 'auth-impl-001.yaml'
        with open(task_file, 'w') as f:
            yaml.dump(delegate, f)
        
        report = checker.check_queue()
        assert report.total_tasks == 1
        assert report.valid_count == 1
        assert report.pass_rate == 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
