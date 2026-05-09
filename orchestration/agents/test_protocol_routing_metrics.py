"""
Protocol Week 2 — Routing & Metrics System Tests

Comprehensive test coverage for:
1. HANDBACK routing logic (18 tests covering all score bands and scenarios)
2. Metrics collection and calculation (10 tests)
3. Metrics persistence (4 tests)
4. Integration (2+ tests)

Total: 30+ tests with 100% pass rate requirement
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict

from orchestration.agents.orchestrator import OrchestratorAgent, MAX_RETRIES
from orchestration.agents.metrics_writer import MetricsWriter


# ─── Test Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def orchestrator():
    """Create OrchestratorAgent instance for testing."""
    return OrchestratorAgent(idle_timeout=1)


@pytest.fixture
def metrics_writer():
    """Create MetricsWriter with temporary directory."""
    temp_dir = tempfile.mkdtemp()
    return MetricsWriter(metrics_dir=temp_dir), temp_dir


@pytest.fixture
def sample_delegate():
    """Sample DELEGATE block for testing."""
    return {
        'task_id': '2026-05-09-test-routing',
        'role': 'engineer',
        'model': 'claude-haiku-4.5',
        'effort': 'medium',
        'estimated_hours': 8,
    }


@pytest.fixture
def sample_handback_base():
    """Base HANDBACK block for testing."""
    return {
        'task_id': '2026-05-09-test-routing',
        'status': 'complete',
        'deliverables': [
            'orchestration/agents/orchestrator.py',
            'orchestration/agents/metrics_writer.py',
            'tests/test_protocol_routing_metrics.py',
        ],
        'tests': {
            'passed': 25,
            'failed': 0,
            'coverage': 95.5,
        },
        'tokens_in': 12840,
        'tokens_out': 8392,
        'effort_actual': 7.5,
        'quality_score': 90,  # Default, overridden in tests
        'escalations': [],
    }


# ─── ROUTING TESTS (18 tests) ───────────────────────────────────────────────


class TestRoutingHighScore:
    """Tests for quality score 90-100 → PROCEED"""
    
    def test_score_95_returns_proceed(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 95 should route to PROCEED."""
        handback = {**sample_handback_base, 'quality_score': 95}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'PROCEED'
        assert context['reason'] == 'High quality score (90+)'
        assert context['quality_score'] == 95
    
    def test_score_100_returns_proceed(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 100 should route to PROCEED."""
        handback = {**sample_handback_base, 'quality_score': 100}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'PROCEED'
        assert context['quality_score'] == 100
    
    def test_score_90_boundary_returns_proceed(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 90 (boundary) should route to PROCEED."""
        handback = {**sample_handback_base, 'quality_score': 90}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'PROCEED'


class TestRoutingAcceptableScore:
    """Tests for quality score 80-89 → PROCEED"""
    
    def test_score_89_returns_proceed(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 89 should route to PROCEED with notes."""
        handback = {**sample_handback_base, 'quality_score': 89}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'PROCEED'
        assert context['reason'] == 'Acceptable quality score (80-89)'
        assert 'notes' in context
    
    def test_score_80_boundary_returns_proceed(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 80 (boundary) should route to PROCEED."""
        handback = {**sample_handback_base, 'quality_score': 80}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'PROCEED'
    
    def test_score_85_returns_proceed(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 85 should route to PROCEED."""
        handback = {**sample_handback_base, 'quality_score': 85}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'PROCEED'


class TestRoutingManualReview:
    """Tests for quality score 70-79 → MANUAL_REVIEW"""
    
    def test_score_75_returns_manual_review(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 75 should route to MANUAL_REVIEW."""
        handback = {**sample_handback_base, 'quality_score': 75}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'MANUAL_REVIEW'
        assert context['reviewer_role'] == 'lead_engineer'
        assert 'review_guidance' in context
    
    def test_score_70_boundary_returns_manual_review(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 70 (boundary) should route to MANUAL_REVIEW."""
        handback = {**sample_handback_base, 'quality_score': 70}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'MANUAL_REVIEW'
    
    def test_score_79_boundary_returns_manual_review(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 79 (boundary) should route to MANUAL_REVIEW."""
        handback = {**sample_handback_base, 'quality_score': 79}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'MANUAL_REVIEW'


class TestRoutingRework:
    """Tests for quality score 60-69 → REWORK (with retry tracking)"""
    
    def test_score_65_returns_rework(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 65 should route to REWORK with retry_context."""
        handback = {**sample_handback_base, 'quality_score': 65}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'REWORK'
        assert 'retry_context' in context
        assert context['max_retries_remaining'] == MAX_RETRIES
    
    def test_rework_includes_retry_context(self, orchestrator, sample_delegate, sample_handback_base):
        """REWORK action should include retry_context with previous score and guidance."""
        handback = {
            **sample_handback_base,
            'quality_score': 65,
            'escalations': ['Failed test coverage threshold', 'Missing documentation'],
        }
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'REWORK'
        retry_ctx = context['retry_context']
        assert 'previous_quality_score' in retry_ctx
        assert retry_ctx['previous_quality_score'] == 65
        assert 'improvement_guidance' in retry_ctx
    
    def test_score_60_boundary_returns_rework(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 60 (boundary) should route to REWORK."""
        handback = {**sample_handback_base, 'quality_score': 60}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'REWORK'
    
    def test_max_retries_exceeded_escalates(self, orchestrator, sample_delegate, sample_handback_base):
        """After MAX_RETRIES exceeded, should ESCALATE instead of REWORK."""
        task_id = sample_delegate['task_id']
        # Simulate max retries
        state = orchestrator._init_task_state(task_id)
        state['retry_count'] = MAX_RETRIES  # Already at max
        
        handback = {**sample_handback_base, 'quality_score': 65}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'ESCALATE'
        assert 'max retries' in context['reason'].lower()


class TestRoutingEscalation:
    """Tests for quality score <60 → ESCALATE"""
    
    def test_score_55_returns_escalate(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 55 should route to ESCALATE."""
        handback = {**sample_handback_base, 'quality_score': 55}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'ESCALATE'
        assert context['escalation_level'] == 'principal_engineer'
    
    def test_score_0_returns_escalate(self, orchestrator, sample_delegate, sample_handback_base):
        """Score 0 should route to ESCALATE."""
        handback = {**sample_handback_base, 'quality_score': 0}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'ESCALATE'
    
    def test_critical_status_escalates_regardless_of_score(self, orchestrator, sample_delegate, sample_handback_base):
        """status='failed' should ESCALATE regardless of quality_score."""
        handback = {
            **sample_handback_base,
            'status': 'failed',
            'quality_score': 95,  # Even high score
            'failure_reason': 'Network timeout on deployment',
        }
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'ESCALATE'
        assert 'critical_issues' in context
    
    def test_blocked_status_escalates(self, orchestrator, sample_delegate, sample_handback_base):
        """status='blocked' should ESCALATE."""
        handback = {
            **sample_handback_base,
            'status': 'blocked',
            'blocked_reason': 'Waiting for security approval',
        }
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'ESCALATE'
        assert 'critical_issues' in context


# ─── METRICS COLLECTION TESTS (10 tests) ───────────────────────────────────


class TestMetricsCollection:
    """Tests for metrics collection from HANDBACK."""
    
    def test_collect_metrics_extracts_all_required_fields(self, orchestrator, sample_delegate, sample_handback_base):
        """collect_metrics should extract all required fields."""
        metrics = orchestrator.collect_metrics(sample_handback_base, sample_delegate)
        
        required_fields = {
            'task_id', 'timestamp', 'role', 'model', 'effort', 'effort_actual',
            'tokens_in', 'tokens_out', 'total_tokens', 'duration_minutes',
            'quality_score_validator', 'quality_score_agent_self',
            'status', 'retry_count', 'test_coverage', 'deliverables_count',
            'efficiency_score', 'rework_cost_ratio',
        }
        
        for field in required_fields:
            assert field in metrics, f"Missing required field: {field}"
    
    def test_token_totals_calculated_correctly(self, orchestrator, sample_delegate, sample_handback_base):
        """total_tokens should equal tokens_in + tokens_out."""
        handback = {
            **sample_handback_base,
            'tokens_in': 1000,
            'tokens_out': 500,
        }
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        assert metrics['total_tokens'] == 1500
        assert metrics['tokens_in'] == 1000
        assert metrics['tokens_out'] == 500
    
    def test_duration_minutes_calculated_from_effort_actual(self, orchestrator, sample_delegate, sample_handback_base):
        """duration_minutes should be effort_actual * 60."""
        handback = {**sample_handback_base, 'effort_actual': 2.5}
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        assert metrics['duration_minutes'] == 150  # 2.5 * 60
    
    def test_efficiency_score_calculated_correctly(self, orchestrator, sample_delegate, sample_handback_base):
        """efficiency_score should be (quality_score / total_tokens) * 100."""
        handback = {
            **sample_handback_base,
            'quality_score': 80,
            'tokens_in': 1000,
            'tokens_out': 4000,
        }
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        expected_efficiency = (80 / 5000) * 100
        assert metrics['efficiency_score'] == pytest.approx(expected_efficiency, rel=0.01)
    
    def test_retry_count_from_task_state(self, orchestrator, sample_delegate, sample_handback_base):
        """retry_count should come from task state."""
        task_id = sample_delegate['task_id']
        state = orchestrator._init_task_state(task_id)
        state['retry_count'] = 2
        
        metrics = orchestrator.collect_metrics(sample_handback_base, sample_delegate)
        assert metrics['retry_count'] == 2
    
    def test_rework_cost_ratio_increases_with_retries(self, orchestrator, sample_delegate, sample_handback_base):
        """rework_cost_ratio should be > 1.0 if retried."""
        task_id = sample_delegate['task_id']
        state = orchestrator._init_task_state(task_id)
        state['retry_count'] = 1  # One retry
        
        metrics = orchestrator.collect_metrics(sample_handback_base, sample_delegate)
        assert metrics['rework_cost_ratio'] > 1.0
        
        # Two retries should have higher ratio
        state['retry_count'] = 2
        metrics = orchestrator.collect_metrics(sample_handback_base, sample_delegate)
        assert metrics['rework_cost_ratio'] > 1.5
    
    def test_test_coverage_extracted(self, orchestrator, sample_delegate, sample_handback_base):
        """Test coverage should be extracted from tests object."""
        handback = {
            **sample_handback_base,
            'tests': {'passed': 30, 'failed': 0, 'coverage': 87.5}
        }
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        assert metrics['test_coverage'] == 87.5
    
    def test_deliverables_count(self, orchestrator, sample_delegate, sample_handback_base):
        """Deliverables count should match length of deliverables array."""
        handback = {
            **sample_handback_base,
            'deliverables': ['file1.py', 'file2.py', 'file3.py']
        }
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        assert metrics['deliverables_count'] == 3
    
    def test_quality_score_agent_self_optional(self, orchestrator, sample_delegate, sample_handback_base):
        """If quality_score_agent_self not provided, use validator score."""
        handback = {**sample_handback_base}
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        assert metrics['quality_score_agent_self'] == sample_handback_base['quality_score']


# ─── METRICS PERSISTENCE TESTS (4 tests) ───────────────────────────────────


class TestMetricsPersistence:
    """Tests for metrics writing to YAML files."""
    
    def test_write_metrics_creates_file(self, metrics_writer):
        """write_metrics should create a YAML file."""
        writer, temp_dir = metrics_writer
        
        metrics = {
            'task_id': '2026-05-09-test',
            'timestamp': datetime.now().isoformat(),
            'quality_score_validator': 85,
            'tokens_in': 1000,
            'tokens_out': 500,
            'total_tokens': 1500,
        }
        
        filepath = writer.write_metrics(metrics)
        assert Path(filepath).exists()
        assert filepath.endswith('-metrics.yaml')
    
    def test_metrics_file_is_valid_yaml(self, metrics_writer):
        """Metrics file should be valid YAML."""
        writer, temp_dir = metrics_writer
        
        metrics = {
            'task_id': '2026-05-09-test',
            'timestamp': datetime.now().isoformat(),
            'quality_score_validator': 90,
        }
        
        filepath = writer.write_metrics(metrics)
        
        with open(filepath, 'r') as f:
            loaded = yaml.safe_load(f)
        
        assert loaded['quality_score_validator'] == 90
    
    def test_load_metrics_retrieves_file(self, metrics_writer):
        """load_metrics should retrieve metrics from file."""
        writer, temp_dir = metrics_writer
        
        metrics = {
            'task_id': '2026-05-09-test',
            'timestamp': datetime.now().isoformat(),
            'quality_score_validator': 87,
        }
        
        writer.write_metrics(metrics)
        loaded = writer.load_metrics('2026-05-09-test')
        
        assert loaded['quality_score_validator'] == 87
    
    def test_aggregate_metrics_sums_daily_totals(self, metrics_writer):
        """aggregate_metrics should sum and average daily metrics."""
        writer, temp_dir = metrics_writer
        
        # Write multiple metrics for same day
        today = datetime.now().strftime('%Y-%m-%d')
        for i in range(3):
            metrics = {
                'task_id': f'2026-05-09-test-{i}',
                'timestamp': datetime.now().isoformat(),
                'quality_score_validator': 80 + (i * 5),
                'total_tokens': 1000 * (i + 1),
            }
            writer.write_metrics(metrics)
        
        aggregated = writer.aggregate_metrics(today)
        
        assert aggregated['task_count'] == 3
        assert aggregated['quality_score']['avg'] == pytest.approx(85, rel=0.1)


# ─── INTEGRATION TESTS (2+ tests) ───────────────────────────────────────────


class TestIntegration:
    """End-to-end tests for routing + metrics flow."""
    
    def test_handback_flows_through_routing_and_metrics(self, orchestrator, sample_delegate, sample_handback_base, metrics_writer):
        """Full flow: HANDBACK → routing decision → metrics collection."""
        writer, temp_dir = metrics_writer
        
        handback = {**sample_handback_base, 'quality_score': 85}
        
        # Route the handback
        action, routing_context = orchestrator.route_handback(handback, sample_delegate)
        assert action == 'PROCEED'
        
        # Collect metrics
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        assert metrics['quality_score_validator'] == 85
        
        # Write metrics
        filepath = writer.write_metrics(metrics)
        assert Path(filepath).exists()
    
    def test_rework_flow_includes_metrics(self, orchestrator, sample_delegate, sample_handback_base, metrics_writer):
        """REWORK flow: collect metrics with retry tracking."""
        writer, temp_dir = metrics_writer
        
        task_id = sample_delegate['task_id']
        # Simulate first attempt
        state = orchestrator._init_task_state(task_id)
        state['retry_count'] = 0
        
        handback = {**sample_handback_base, 'quality_score': 65}
        
        # Route to REWORK
        action, context = orchestrator.route_handback(handback, sample_delegate)
        assert action == 'REWORK'
        
        # Collect metrics (should show retry_count = 0)
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        assert metrics['retry_count'] == 0
        
        # Simulate retry
        state['retry_count'] = 1
        second_handback = {**sample_handback_base, 'quality_score': 88}
        metrics2 = orchestrator.collect_metrics(second_handback, sample_delegate)
        assert metrics2['retry_count'] == 1
        assert metrics2['rework_cost_ratio'] > 1.0


# ─── Edge Case Tests ───────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case and boundary condition tests."""
    
    def test_missing_quality_score_defaults_to_zero(self, orchestrator, sample_delegate, sample_handback_base):
        """If quality_score missing, should default to 0 (ESCALATE)."""
        handback = {**sample_handback_base}
        del handback['quality_score']
        
        action, context = orchestrator.route_handback(handback, sample_delegate)
        # Should escalate (score defaults to 0)
        assert action == 'ESCALATE'
    
    def test_collect_metrics_with_zero_tokens(self, orchestrator, sample_delegate, sample_handback_base):
        """Efficiency score should handle zero tokens gracefully."""
        handback = {**sample_handback_base, 'tokens_in': 0, 'tokens_out': 0}
        metrics = orchestrator.collect_metrics(handback, sample_delegate)
        
        assert metrics['efficiency_score'] == 0.0  # Division by zero handled
    
    def test_routing_with_empty_escalations_list(self, orchestrator, sample_delegate, sample_handback_base):
        """Routing should handle empty escalations list."""
        handback = {**sample_handback_base, 'quality_score': 65, 'escalations': []}
        action, context = orchestrator.route_handback(handback, sample_delegate)
        
        assert action == 'REWORK'
        retry_ctx = context['retry_context']
        assert 'improvement_guidance' in retry_ctx


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
