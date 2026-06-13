"""
End-to-End Tests for Protocol Expansion Initiative (Phase 5)

Tests the complete workflow from DELEGATE creation through quality evaluation
and routing decisions, using real task scenarios.
"""

import pytest
from datetime import datetime
from typing import Dict, List
from src.orchestration.agents.orchestrator_protocol_integration import OrchestratorProtocolIntegration
from src.orchestration.agents.quality_engineer_protocol_integration import QualityEngineerProtocolIntegration


class TestEndToEndWorkflow:
    """Test complete DELEGATE → execution → HANDBACK → quality evaluation → routing workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorProtocolIntegration()
        self.quality_engineer = QualityEngineerProtocolIntegration()
    
    def test_e2e_high_quality_task_proceeds(self):
        """Test end-to-end workflow for high-quality task that proceeds normally."""
        # 1. Orchestrator creates expanded DELEGATE
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-24-e2e-high-quality",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement user authentication feature with comprehensive tests",
            plan=["Design auth system", "Implement auth module", "Write tests", "Security review"],
            quality_baseline=90,
            acceptance_criteria=[
                "All unit tests pass",
                "Integration tests pass",
                "Code coverage ≥90%",
                "Security review passed",
            ],
            cost_target=2.0,
        )
        
        assert delegate.task_id == "2026-05-24-e2e-high-quality"
        assert delegate.quality_baseline == 90
        assert len(delegate.acceptance_criteria) == 4
        
        # 2. Engineer executes task and returns HANDBACK
        handback = {
            "task_id": "2026-05-24-e2e-high-quality",
            "status": "success",
            "quality_score": 94,
            "test_coverage": 0.94,
            "cost_actual": 1.8,
            "tokens_in": 25000,
            "tokens_out": 9000,
            "time_elapsed_minutes": 240,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": [
                "All unit tests pass",
                "Integration tests pass",
                "Code coverage ≥90%",
                "Security review passed",
            ],
            "deliverables": ["src/auth.py", "tests/test_auth.py"],
            "tests": {"unit": True, "integration": True},
            "regressions_detected": 0,
            "success_rate": 0.94,
            "quality_trend": "improved",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed successfully with excellent quality",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # 3. Quality Engineer evaluates quality
        evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        
        assert evaluation.quality_score == 94
        assert evaluation.quality_baseline == 90
        assert not evaluation.escalation_required
        
        # 4. Quality Engineer checks escalation
        should_escalate, context = self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
        
        assert not should_escalate
        assert context is None
        
        # 5. Orchestrator processes HANDBACK with quality evaluation
        routing_decision = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        assert routing_decision[0] == "PROCEED"
        assert routing_decision[1]["quality_score"] == 94
    
    def test_e2e_low_quality_task_escalates(self):
        """Test end-to-end workflow for low-quality task that escalates."""
        # 1. Orchestrator creates expanded DELEGATE
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-24-e2e-low-quality",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement user authentication feature with comprehensive tests",
            plan=["Design auth system", "Implement auth module", "Write tests", "Security review"],
            quality_baseline=90,
            acceptance_criteria=[
                "All unit tests pass",
                "Integration tests pass",
                "Code coverage ≥90%",
                "Security review passed",
            ],
            cost_target=2.0,
        )
        
        # 2. Engineer executes task and returns HANDBACK with low quality
        handback = {
            "task_id": "2026-05-24-e2e-low-quality",
            "status": "success",
            "quality_score": 55,
            "test_coverage": 0.65,
            "cost_actual": 2.5,
            "tokens_in": 30000,
            "tokens_out": 12000,
            "time_elapsed_minutes": 300,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": [
                "All unit tests pass",
            ],
            "deliverables": ["src/auth.py"],
            "tests": {"unit": True, "integration": False},
            "regressions_detected": 2,
            "success_rate": 0.55,
            "quality_trend": "declining",
            "cost_trend": "over",
            "effort_actual": "medium",
            "notes": "Task completed but with quality issues",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # 3. Quality Engineer evaluates quality
        evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        
        assert evaluation.quality_score == 55
        assert evaluation.escalation_required
        
        # 4. Quality Engineer checks escalation
        should_escalate, context = self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
        
        assert should_escalate
        assert context is not None
        assert context["escalation_level"] == "principal_engineer"
        assert context["quality_score"] == 55
        
        # 5. Orchestrator processes HANDBACK with quality evaluation
        routing_decision = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        assert routing_decision[0] == "ESCALATE"
        assert routing_decision[1]["quality_score"] == 55
    
    def test_e2e_medium_quality_task_manual_review(self):
        """Test end-to-end workflow for medium-quality task that requires manual review."""
        # 1. Orchestrator creates expanded DELEGATE
        delegate = self.orchestrator.create_expanded_delegate(
            task_id="2026-05-24-e2e-medium-quality",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement user authentication feature with comprehensive tests",
            plan=["Design auth system", "Implement auth module", "Write tests", "Security review"],
            quality_baseline=90,
            acceptance_criteria=[
                "All unit tests pass",
                "Integration tests pass",
                "Code coverage ≥90%",
                "Security review passed",
            ],
            cost_target=2.0,
        )
        
        # 2. Engineer executes task and returns HANDBACK with medium quality
        handback = {
            "task_id": "2026-05-24-e2e-medium-quality",
            "status": "success",
            "quality_score": 75,
            "test_coverage": 0.78,
            "cost_actual": 1.9,
            "tokens_in": 24000,
            "tokens_out": 8500,
            "time_elapsed_minutes": 220,
            "model_used": "claude-sonnet-4.6",
            "acceptance_criteria_met": [
                "All unit tests pass",
                "Integration tests pass",
                "Code coverage ≥90%",
                "Security review passed",
            ],
            "deliverables": ["src/auth.py", "tests/test_auth.py"],
            "tests": {"unit": True, "integration": True},
            "regressions_detected": 0,
            "success_rate": 0.75,
            "quality_trend": "stable",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed with some quality concerns",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        
        # 3. Quality Engineer evaluates quality
        evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        
        assert evaluation.quality_score == 75
        assert not evaluation.escalation_required  # All criteria met, so no escalation
        
        # 4. Quality Engineer checks escalation
        should_escalate, context = self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
        
        assert not should_escalate
        assert context is None
        
        # 5. Orchestrator processes HANDBACK with quality evaluation
        routing_decision = self.orchestrator.process_expanded_handback(
            handback,
            delegate.to_dict(),
        )
        
        assert routing_decision[0] == "MANUAL_REVIEW"
        assert routing_decision[1]["quality_score"] == 75
    
    def test_e2e_multiple_tasks_quality_trends(self):
        """Test end-to-end workflow with multiple tasks to verify quality trends."""
        task_ids = [
            "2026-05-24-e2e-trend-1",
            "2026-05-24-e2e-trend-2",
            "2026-05-24-e2e-trend-3",
            "2026-05-24-e2e-trend-4",
            "2026-05-24-e2e-trend-5",
        ]
        quality_scores = [80, 82, 84, 86, 88]
        
        for task_id, quality_score in zip(task_ids, quality_scores):
            # 1. Create DELEGATE
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=task_id,
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass", "Code coverage ≥90%"],
                cost_target=2.0,
            )
            
            # 2. Create HANDBACK
            handback = {
                "task_id": task_id,
                "status": "success",
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
                "quality_trend": "improving",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            
            # 3. Evaluate quality
            evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
            
            # 4. Check escalation
            should_escalate, context = self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
            
            # 5. Process HANDBACK
            routing_decision = self.orchestrator.process_expanded_handback(
                handback,
                delegate.to_dict(),
            )
        
        # Verify quality trend
        metrics = self.quality_engineer.get_quality_metrics("engineer", days=7)
        
        assert metrics["count"] == 5
        assert metrics["avg_quality"] == 84.0  # (80+82+84+86+88)/5
        assert metrics["trend"] == "improving"
        assert metrics["min_quality"] == 80
        assert metrics["max_quality"] == 88
    
    def test_e2e_quality_dashboard_generation(self):
        """Test end-to-end workflow with quality dashboard generation."""
        # Create tasks for multiple roles
        for role in ["engineer", "senior-engineer"]:
            for i in range(3):
                task_id = f"2026-05-24-e2e-dashboard-{role}-{i}"
                quality_score = 85 + i
                
                # 1. Create DELEGATE
                delegate = self.orchestrator.create_expanded_delegate(
                    task_id=task_id,
                    role=role,
                    model="claude-sonnet-4.6",
                    effort="medium",
                    scope="Implement feature",
                    plan=["Design", "Implement", "Test"],
                    quality_baseline=90,
                    acceptance_criteria=["Tests pass"],
                    cost_target=2.0,
                )
                
                # 2. Create HANDBACK
                handback = {
                    "task_id": task_id,
                    "status": "success",
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
                
                # 3. Evaluate quality
                evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
                
                # 4. Check escalation
                should_escalate, context = self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
                
                # 5. Process HANDBACK
                routing_decision = self.orchestrator.process_expanded_handback(
                    handback,
                    delegate.to_dict(),
                )
        
        # Generate dashboard
        dashboard = self.quality_engineer.get_quality_dashboard()
        
        assert dashboard["total_evaluations"] == 6
        assert "engineer" in dashboard["roles"]
        assert "senior-engineer" in dashboard["roles"]
        assert "overall" in dashboard
        assert dashboard["overall"]["avg_quality"] > 0
        assert dashboard["overall"]["escalation_rate"] >= 0
    
    def test_e2e_escalation_summary(self):
        """Test end-to-end workflow with escalation summary."""
        # Create tasks with varying quality scores
        quality_scores = [55, 65, 75, 85, 95]
        
        for i, quality_score in enumerate(quality_scores):
            task_id = f"2026-05-24-e2e-escalation-{i}"
            
            # 1. Create DELEGATE
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=task_id,
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            
            # 2. Create HANDBACK
            handback = {
                "task_id": task_id,
                "status": "success",
                "quality_score": quality_score,
                "test_coverage": quality_score / 100,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"] if quality_score >= 80 else [],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0 if quality_score >= 80 else 1,
                "success_rate": quality_score / 100,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            
            # 3. Evaluate quality
            evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
            
            # 4. Check escalation
            should_escalate, context = self.quality_engineer.check_escalation(evaluation, delegate.to_dict())
            
            # 5. Process HANDBACK
            routing_decision = self.orchestrator.process_expanded_handback(
                handback,
                delegate.to_dict(),
            )
        
        # Generate escalation summary
        summary = self.quality_engineer.generate_escalation_summary()
        
        assert summary["total_escalations"] == 3  # 55, 65, 75 are escalated
        assert "by_level" in summary
        assert "by_reason" in summary
        assert "by_role" in summary


class TestPerformanceCharacteristics:
    """Test performance characteristics of the protocol expansion."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = OrchestratorProtocolIntegration()
        self.quality_engineer = QualityEngineerProtocolIntegration()
    
    def test_performance_delegate_creation(self):
        """Test performance of DELEGATE creation."""
        import time
        
        start = time.time()
        for i in range(100):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-24-perf-delegate-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
        elapsed = time.time() - start
        
        avg_time = (elapsed * 1000) / 100  # Convert to ms
        assert avg_time < 10, f"DELEGATE creation took {avg_time:.2f}ms, expected < 10ms"
    
    def test_performance_quality_evaluation(self):
        """Test performance of quality evaluation."""
        import time
        
        # Create test data
        delegates = []
        handbacks = []
        
        for i in range(50):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-24-perf-eval-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            delegates.append(delegate)
            
            handback = {
                "task_id": f"2026-05-24-perf-eval-{i}",
                "status": "success",
                "quality_score": 85 + (i % 10),
                "test_coverage": 0.85,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0,
                "success_rate": 0.85,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            handbacks.append(handback)
        
        # Measure evaluation performance
        start = time.time()
        for delegate, handback in zip(delegates, handbacks):
            evaluation = self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        elapsed = time.time() - start
        
        avg_time = (elapsed * 1000) / 50  # Convert to ms
        assert avg_time < 5, f"Quality evaluation took {avg_time:.2f}ms, expected < 5ms"
    
    def test_performance_metrics_computation(self):
        """Test performance of metrics computation."""
        import time
        
        # Create evaluations
        for i in range(100):
            delegate = self.orchestrator.create_expanded_delegate(
                task_id=f"2026-05-24-perf-metrics-{i}",
                role="engineer",
                model="claude-sonnet-4.6",
                effort="medium",
                scope="Implement feature",
                plan=["Design", "Implement", "Test"],
                quality_baseline=90,
                acceptance_criteria=["Tests pass"],
                cost_target=2.0,
            )
            
            handback = {
                "task_id": f"2026-05-24-perf-metrics-{i}",
                "status": "success",
                "quality_score": 85 + (i % 10),
                "test_coverage": 0.85,
                "cost_actual": 1.8,
                "tokens_in": 22000,
                "tokens_out": 8000,
                "time_elapsed_minutes": 200,
                "model_used": "claude-sonnet-4.6",
                "acceptance_criteria_met": ["Tests pass"],
                "deliverables": ["src/feature.py"],
                "tests": {"unit": True},
                "regressions_detected": 0,
                "success_rate": 0.85,
                "quality_trend": "stable",
                "cost_trend": "under",
                "effort_actual": "medium",
                "notes": "Task completed",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }
            
            self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        
        # Measure metrics computation
        start = time.time()
        metrics = self.quality_engineer.get_quality_metrics("engineer", days=7)
        elapsed = time.time() - start
        
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 10, f"Metrics computation took {elapsed_ms:.2f}ms, expected < 10ms"
    
    def test_performance_dashboard_generation(self):
        """Test performance of dashboard generation."""
        import time
        
        # Create evaluations for multiple roles
        for role in ["engineer", "senior-engineer", "lead-engineer"]:
            for i in range(30):
                delegate = self.orchestrator.create_expanded_delegate(
                    task_id=f"2026-05-24-perf-dashboard-{role}-{i}",
                    role=role,
                    model="claude-sonnet-4.6",
                    effort="medium",
                    scope="Implement feature",
                    plan=["Design", "Implement", "Test"],
                    quality_baseline=90,
                    acceptance_criteria=["Tests pass"],
                    cost_target=2.0,
                )
                
                handback = {
                    "task_id": f"2026-05-24-perf-dashboard-{role}-{i}",
                    "status": "success",
                    "quality_score": 85 + (i % 10),
                    "test_coverage": 0.85,
                    "cost_actual": 1.8,
                    "tokens_in": 22000,
                    "tokens_out": 8000,
                    "time_elapsed_minutes": 200,
                    "model_used": "claude-sonnet-4.6",
                    "acceptance_criteria_met": ["Tests pass"],
                    "deliverables": ["src/feature.py"],
                    "tests": {"unit": True},
                    "regressions_detected": 0,
                    "success_rate": 0.85,
                    "quality_trend": "stable",
                    "cost_trend": "under",
                    "effort_actual": "medium",
                    "notes": "Task completed",
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                }
                
                self.quality_engineer.evaluate_quality(delegate.to_dict(), handback)
        
        # Measure dashboard generation
        start = time.time()
        dashboard = self.quality_engineer.get_quality_dashboard()
        elapsed = time.time() - start
        
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 20, f"Dashboard generation took {elapsed_ms:.2f}ms, expected < 20ms"
