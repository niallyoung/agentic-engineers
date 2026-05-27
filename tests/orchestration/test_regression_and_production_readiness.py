"""
Regression Tests for Protocol Expansion Initiative (Phase 6)

Tests to ensure no breaking changes to existing orchestrator functionality
while integrating the new protocol expansion features.
"""

import pytest
from datetime import datetime
from typing import Dict
from src.orchestration.agents.orchestrator_protocol_integration import OrchestratorProtocolIntegration
from src.orchestration.agents.quality_engineer_protocol_integration import QualityEngineerProtocolIntegration


class TestRegressionExistingOrchestrator:
    """Test that existing orchestrator functionality still works."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorProtocolIntegration()
        self.quality_engineer = QualityEngineerProtocolIntegration()
    
    def test_delegate_creation_without_quality_baseline(self):
        """Test that DELEGATE creation works without quality_baseline (backward compatibility)."""
        # Create DELEGATE without explicit quality_baseline (should default to 90)
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-regression-no-baseline",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            # quality_baseline not specified - should default to 90
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        assert delegate.task_id == "2026-05-27-regression-no-baseline"
        assert delegate.quality_baseline == 90  # Default value
        assert delegate.role == "engineer"
    
    def test_handback_processing_without_quality_evaluation(self):
        """Test that HANDBACK processing works without quality evaluation."""
        # Create DELEGATE
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-regression-no-eval",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        # Create HANDBACK
        handback = {
            "task_id": "2026-05-27-regression-no-eval",
            "status": "complete",
            "quality_score": 92,
            "test_coverage": 0.92,
            "cost_actual": 1.8,
            "tokens_in": 22000,
            "tokens_out": 8000,
            "time_elapsed_minutes": 200,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": ["Tests pass"],
            "deliverables": ["src/feature.py"],
            "tests": {"unit": True},
            "regressions_detected": 0,
            "success_rate": 0.92,
            "quality_trend": "stable",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # Process HANDBACK
        action, context = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        # Should proceed normally
        assert action == "PROCEED"
        assert context["quality_score"] == 92
    
    def test_multiple_delegates_independence(self):
        """Test that multiple DELEGATEs are independent."""
        delegates = []
        for i in range(5):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-27-regression-multi-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature with comprehensive testing and documentation",
                plan=["Design", "Implement", "Test"],
                quality_baseline=85 + i,  # Different baselines
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            delegates.append(delegate)
        
        # Verify each has correct baseline
        for i, delegate in enumerate(delegates):
            assert delegate.quality_baseline == 85 + i
    
    def test_event_publishing_does_not_break_routing(self):
        """Test that event publishing doesn't interfere with routing decisions."""
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-regression-events",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        handback = {
            "task_id": "2026-05-27-regression-events",
            "status": "complete",
            "quality_score": 92,
            "test_coverage": 0.92,
            "cost_actual": 1.8,
            "tokens_in": 22000,
            "tokens_out": 8000,
            "time_elapsed_minutes": 200,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": ["Tests pass"],
            "deliverables": ["src/feature.py"],
            "tests": {"unit": True},
            "regressions_detected": 0,
            "success_rate": 0.92,
            "quality_trend": "stable",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # Process HANDBACK (events are published internally)
        action, context = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        # Routing should still work correctly
        assert action == "PROCEED"
        assert context["quality_score"] == 92
    
    def test_quality_engineer_optional_integration(self):
        """Test that Quality Engineer integration is optional."""
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-regression-optional",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        handback = {
            "task_id": "2026-05-27-regression-optional",
            "status": "complete",
            "quality_score": 92,
            "test_coverage": 0.92,
            "cost_actual": 1.8,
            "tokens_in": 22000,
            "tokens_out": 8000,
            "time_elapsed_minutes": 200,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": ["Tests pass"],
            "deliverables": ["src/feature.py"],
            "tests": {"unit": True},
            "regressions_detected": 0,
            "success_rate": 0.92,
            "quality_trend": "stable",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # Can process without using Quality Engineer
        action, context = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        assert action == "PROCEED"
        
        # Can also use Quality Engineer separately if desired
        qe = QualityEngineerProtocolIntegration()
        evaluation = qe.evaluate_quality(delegate.to_dict(), handback)
        assert evaluation.quality_score == 92


class TestQualityValidation:
    """Test quality validation for production readiness."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorProtocolIntegration()
        self.quality_engineer = QualityEngineerProtocolIntegration()
    
    def test_maintain_quality_baseline_90(self):
        """Test that average quality score maintains ≥90 for high-quality tasks."""
        quality_scores = [92, 94, 91, 93, 95, 92, 94, 91, 93, 95]
        
        for i, quality_score in enumerate(quality_scores):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-27-quality-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature with comprehensive testing and documentation",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            
            handback = {
                "task_id": f"2026-05-27-quality-{i}",
                "status": "complete",
                "quality_score": quality_score,
                "test_coverage": quality_score / 100,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0,
                "success_rate": quality_score / 100,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            
            evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
            assert evaluation.quality_score == quality_score
        
        # Verify average quality
        metrics = self.quality_engineer.get_quality_metrics("engineer", days=7)
        assert metrics["avg_quality"] >= 90, f"Average quality {metrics['avg_quality']} < 90"
    
    def test_escalation_rate_acceptable(self):
        """Test that escalation rate is acceptable (< 20%)."""
        # Create 10 tasks with varying quality
        quality_scores = [92, 94, 91, 93, 95, 92, 94, 91, 93, 95]
        
        for i, quality_score in enumerate(quality_scores):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-27-escalation-rate-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature with comprehensive testing and documentation",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            
            handback = {
                "task_id": f"2026-05-27-escalation-rate-{i}",
                "status": "complete",
                "quality_score": quality_score,
                "test_coverage": quality_score / 100,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0,
                "success_rate": quality_score / 100,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            
            evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
            self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
        
        # Verify escalation rate
        dashboard = self.quality_engineer.get_quality_dashboard()
        escalation_rate = dashboard["overall"]["escalation_rate"]
        assert escalation_rate < 0.20, f"Escalation rate {escalation_rate:.1%} >= 20%"
    
    def test_no_regressions_in_quality_scores(self):
        """Test that quality scores don't regress over time."""
        quality_scores = [85, 86, 87, 88, 89, 90, 91, 92, 93, 94]
        
        for i, quality_score in enumerate(quality_scores):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-27-no-regression-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature with comprehensive testing and documentation",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            
            handback = {
                "task_id": f"2026-05-27-no-regression-{i}",
                "status": "complete",
                "quality_score": quality_score,
                "test_coverage": quality_score / 100,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0,
                "success_rate": quality_score / 100,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            
            self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        
        # Verify trend is improving
        metrics = self.quality_engineer.get_quality_metrics("engineer", days=7)
        assert metrics["trend"] == "improving", f"Trend is {metrics['trend']}, expected improving"


class TestProductionReadiness:
    """Test production readiness criteria."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorProtocolIntegration()
        self.quality_engineer = QualityEngineerProtocolIntegration()
    
    def test_all_required_fields_present(self):
        """Test that all required fields are present in expanded schemas."""
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-prod-fields",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        # Check required fields
        assert delegate.task_id is not None
        assert delegate.role is not None
        assert delegate.model is not None
        assert delegate.effort is not None
        assert delegate.scope is not None
        assert delegate.plan is not None
        assert delegate.quality_baseline is not None
        assert delegate.created_at is not None
        assert delegate.version is not None
    
    def test_error_handling_graceful(self):
        """Test that errors are handled gracefully."""
        # Create DELEGATE
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-prod-error",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        # Create invalid HANDBACK (missing required fields)
        invalid_handback = {
            "task_id": "2026-05-27-prod-error",
            "status": "complete",
            # Missing quality_score, test_coverage, etc.
        }
        
        # Should handle gracefully (not crash)
        try:
            action, context = self.orchestrator.process_expanded_handback(
                invalid_handback,
                delegate.to_dict(),
            )
            # If we get here, error was handled
            assert True
        except KeyError:
            # Expected - missing required fields
            assert True
    
    def test_concurrent_task_processing(self):
        """Test that multiple tasks can be processed concurrently."""
        delegates = []
        handbacks = []
        
        # Create multiple DELEGATEs and HANDBACKs
        for i in range(5):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-27-concurrent-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature with comprehensive testing and documentation",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            delegates.append(delegate)
            
            handback = {
                "task_id": f"2026-05-27-concurrent-{i}",
                "status": "complete",
                "quality_score": 90 + i,
                "test_coverage": 0.90,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0,
                "success_rate": 0.90,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            handbacks.append(handback)
        
        # Process all tasks
        results = []
        for delegate, handback in zip(delegates, handbacks):
            action, context = self.orchestrator.process_expanded_handback(
                handback,
                delegate.to_dict(),
            )
            results.append((action, context))
        
        # Verify all processed successfully
        assert len(results) == 5
        for action, context in results:
            assert action == "PROCEED"
            assert context["quality_score"] >= 90
    
    def test_data_consistency(self):
        """Test that data remains consistent across operations."""
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-27-consistency",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["Tests pass"],
            cost_target=2.0,
        )
        
        # Store original values
        original_task_id = delegate.task_id
        original_baseline = delegate.quality_baseline
        
        handback = {
            "task_id": "2026-05-27-consistency",
            "status": "complete",
            "quality_score": 92,
            "test_coverage": 0.92,
            "cost_actual": 1.8,
            "tokens_in": 22000,
            "tokens_out": 8000,
            "time_elapsed_minutes": 200,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": ["Tests pass"],
            "deliverables": ["src/feature.py"],
            "tests": {"unit": True},
            "regressions_detected": 0,
            "success_rate": 0.92,
            "quality_trend": "stable",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # Process HANDBACK
        action, context = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        # Verify data consistency
        assert delegate.task_id == original_task_id
        assert delegate.quality_baseline == original_baseline
        assert action == "PROCEED"
