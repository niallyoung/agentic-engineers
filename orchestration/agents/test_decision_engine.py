"""
Comprehensive test suite for DecisionEngine.

Tests decision logic for various scenarios.
"""

import pytest
from . decision_engine import DecisionEngine, DECISION_ENGINE_CONFIG


class TestDecisionEngineDecisions:
    """Test DecisionEngine decision logic."""
    
    def setup_method(self):
        """Set up test fixture."""
        self.engine = DecisionEngine()
    
    def _create_delegate(
        self,
        agent_status: str = "PASS",
        quality_score: int = 85,
        success_criteria: list = None,
        **handback_props
    ) -> dict:
        """Helper to create a DELEGATE block with given properties."""
        if success_criteria is None:
            success_criteria = [
                "Code compiles without errors",
                "All tests pass",
                "Quality score >= 80"
            ]
        
        handback = {
            "status": agent_status,
            "quality_score": quality_score,
            "deliverables": ["file1.py", "file2.py"],
            "tests_passed": True,
            "test_coverage": 85
        }
        handback.update(handback_props)
        
        return {
            "task_id": "decision-test-task-123",
            "role": "decision_engine",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Evaluate HANDBACK and decide next action",
            "context": {
                "original_task_id": "test-task-123",
                "original_success_criteria": success_criteria,
                "agent_status": agent_status,
                "quality_score": quality_score,
                "agent_handback": handback
            }
        }
    
    # Decision: PROCEED
    def test_decision_proceed_all_criteria_met_high_quality(self):
        """Decide PROCEED when all criteria met and quality >= 85."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=90,
            tests_passed=True
        )
        
        handback = self.engine.execute(delegate)
        
        assert handback["status"] == "PASS"
        decision = handback["decision"]
        assert decision["action"] == "proceed"
        assert decision["confidence"] >= 0.90
        assert "criteria met" in decision["rationale"].lower()
    
    def test_decision_proceed_all_criteria_met_acceptable_quality(self):
        """Decide PROCEED when all criteria met and quality >= 80."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=82,
            tests_passed=True
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "proceed"
        assert decision["confidence"] >= 0.85
    
    # Decision: ESCALATE
    def test_decision_escalate_agent_escalated(self):
        """Escalate when agent itself escalated."""
        delegate = self._create_delegate(
            agent_status="ESCALATE",
            quality_score=50
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "escalate"
        assert decision["confidence"] >= 0.90
        assert "escalated" in decision["rationale"].lower()
    
    def test_decision_escalate_critical_criteria_failed(self):
        """Escalate when critical criteria failed."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=75,
            success_criteria=[
                "Security test passes (CRITICAL)",
                "No vulnerabilities found"
            ],
            security_score=45  # Low score indicates failed security
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "escalate"
        assert "critical" in decision["rationale"].lower()
    
    def test_decision_escalate_quality_too_low(self):
        """Escalate when quality score is below minimum threshold."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=50,
            tests_passed=False
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "escalate"
        assert "quality" in decision["rationale"].lower()
    
    # Decision: REWORK
    def test_decision_rework_salvageable_quality(self):
        """Send to rework when quality is acceptable but criteria not fully met."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=75,
            success_criteria=[
                "Tests pass",
                "Code documented"
            ],
            tests_passed=True  # One criterion met
            # But documentation missing
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "rework"
        assert decision["confidence"] >= 0.80
        assert "rework" in decision["rationale"].lower()
    
    def test_decision_rework_quality_70_to_79(self):
        """Send to rework when quality is between 70-79."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=72
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "rework"
    
    # Criterion evaluation
    def test_criterion_test_passing(self):
        """Evaluate 'test' criterion correctly."""
        delegate = self._create_delegate(
            success_criteria=["All tests pass"],
            tests_passed=True
        )
        
        handback = self.engine.execute(delegate)
        
        evaluation = handback["decision"]["evaluation"]
        criteria = evaluation["success_criteria_met"]
        # Should have evaluated test criterion
        assert any("test" in c["criterion"].lower() for c in criteria)
    
    def test_criterion_security_high_score(self):
        """Evaluate security criterion with high score."""
        delegate = self._create_delegate(
            success_criteria=["Security score >= 85"],
            security_score=90,
            quality_score=85
        )
        
        handback = self.engine.execute(delegate)
        
        evaluation = handback["decision"]["evaluation"]
        assert evaluation["quality_score"] == 85
    
    def test_criterion_quality_score(self):
        """Evaluate quality score criterion."""
        delegate = self._create_delegate(
            success_criteria=["Quality score >= 80"],
            quality_score=85
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "proceed"
    
    def test_criterion_deployment(self):
        """Evaluate deployment criterion."""
        delegate = self._create_delegate(
            success_criteria=["Code deployed successfully"],
            deployed=True,
            quality_score=85
        )
        
        handback = self.engine.execute(delegate)
        
        evaluation = handback["decision"]["evaluation"]
        # Should be evaluable
        assert isinstance(evaluation["success_criteria_met"], list)
    
    def test_criterion_no_errors(self):
        """Evaluate 'no errors' criterion."""
        delegate = self._create_delegate(
            success_criteria=["No errors in execution"],
            error_count=0,
            quality_score=85
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "proceed"
    
    # Edge cases
    def test_zero_success_criteria(self):
        """Handle case with no success criteria."""
        delegate = self._create_delegate(
            success_criteria=[],
            quality_score=75
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        # Should handle gracefully
        assert "action" in decision
    
    def test_no_handback_status(self):
        """Handle missing agent_handback status."""
        delegate = self._create_delegate(
            quality_score=50,
            agent_status="UNKNOWN"
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] in ["proceed", "escalate", "rework"]
    
    def test_quality_score_edge_case_exactly_85(self):
        """Test quality score exactly at threshold."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=85,
            tests_passed=True
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "proceed"
    
    def test_quality_score_edge_case_exactly_70(self):
        """Test quality score exactly at rework threshold."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=70
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "rework"
    
    def test_quality_score_edge_case_exactly_80(self):
        """Test quality score exactly at proceed threshold."""
        delegate = self._create_delegate(
            agent_status="PASS",
            quality_score=80,
            tests_passed=True
        )
        
        handback = self.engine.execute(delegate)
        
        decision = handback["decision"]
        assert decision["action"] == "proceed"
    
    # Confidence scoring
    def test_confidence_high_for_clear_decisions(self):
        """Confidence should be high for clear decisions."""
        # Clear escalation
        delegate = self._create_delegate(agent_status="ESCALATE", quality_score=0)
        handback = self.engine.execute(delegate)
        
        assert handback["decision"]["confidence"] >= 0.90
    
    def test_confidence_reasonable_for_marginal_decisions(self):
        """Confidence should be lower for marginal decisions."""
        # Marginal rework decision
        delegate = self._create_delegate(quality_score=70)
        handback = self.engine.execute(delegate)
        
        confidence = handback["decision"]["confidence"]
        assert 0.70 <= confidence <= 0.95


class TestDecisionEngineConfiguration:
    """Test DecisionEngine configuration."""
    
    def test_config_properties(self):
        """DecisionEngine should have correct configuration."""
        assert DECISION_ENGINE_CONFIG.name == "Decision Engine"
        assert DECISION_ENGINE_CONFIG.model == "claude-sonnet-4-6"
        assert DECISION_ENGINE_CONFIG.effort == "medium"
        assert DECISION_ENGINE_CONFIG.role == "decision_engine"
        assert "decision" in DECISION_ENGINE_CONFIG.description.lower()
    
    def test_agent_inherits_config(self):
        """DecisionEngine should properly inherit AgentConfig."""
        agent = DecisionEngine()
        assert agent.config == DECISION_ENGINE_CONFIG


class TestDecisionEngineIntegration:
    """Integration tests."""
    
    def test_decision_includes_all_required_fields(self):
        """Decision should have all required fields."""
        engine = DecisionEngine()
        delegate = {
            "task_id": "decision-test",
            "role": "decision_engine",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Evaluate HANDBACK",
            "context": {
                "original_task_id": "test-task",
                "original_success_criteria": ["Test passes"],
                "agent_status": "PASS",
                "quality_score": 85,
                "agent_handback": {"status": "PASS", "tests_passed": True}
            }
        }
        
        handback = engine.execute(delegate)
        
        assert "decision" in handback
        decision = handback["decision"]
        
        required_fields = ["action", "confidence", "rationale", "evaluation"]
        for field in required_fields:
            assert field in decision, f"Missing required field: {field}"
    
    def test_evaluation_includes_criteria_results(self):
        """Evaluation should include detailed criteria results."""
        engine = DecisionEngine()
        delegate = {
            "task_id": "decision-test",
            "role": "decision_engine",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Evaluate HANDBACK",
            "context": {
                "original_task_id": "test-task",
                "original_success_criteria": [
                    "Tests pass",
                    "Code quality >= 80"
                ],
                "agent_status": "PASS",
                "quality_score": 85,
                "agent_handback": {
                    "status": "PASS",
                    "tests_passed": True,
                    "quality_score": 85
                }
            }
        }
        
        handback = engine.execute(delegate)
        evaluation = handback["decision"]["evaluation"]
        
        assert "success_criteria_met" in evaluation
        assert isinstance(evaluation["success_criteria_met"], list)
        assert len(evaluation["success_criteria_met"]) == 2
    
    def test_blockers_provided_when_issues_found(self):
        """Blockers should be provided when there are issues."""
        engine = DecisionEngine()
        delegate = {
            "task_id": "decision-test",
            "role": "decision_engine",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Evaluate HANDBACK",
            "context": {
                "original_task_id": "test-task",
                "original_success_criteria": ["Tests pass"],
                "agent_status": "ESCALATE",
                "quality_score": 50,
                "agent_handback": {"status": "ESCALATE", "error": "Tests failed"}
            }
        }
        
        handback = engine.execute(delegate)
        evaluation = handback["decision"]["evaluation"]
        
        assert "blockers" in evaluation
        assert len(evaluation["blockers"]) > 0


class TestCriterionEvaluation:
    """Test individual criterion evaluation."""
    
    def test_test_criterion_with_test_results(self):
        """Test criterion evaluation with test_results."""
        engine = DecisionEngine()
        delegate = {
            "task_id": "test-decision",
            "role": "decision_engine",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Evaluate",
            "context": {
                "original_task_id": "task",
                "original_success_criteria": ["All tests pass"],
                "agent_status": "PASS",
                "quality_score": 85,
                "agent_handback": {
                    "test_results": {"all_passed": True},
                    "status": "PASS"
                }
            }
        }
        
        handback = engine.execute(delegate)
        decision = handback["decision"]
        assert decision["action"] == "proceed"
    
    def test_security_criterion_high_score(self):
        """Security criterion with high score."""
        engine = DecisionEngine()
        delegate = {
            "task_id": "test-decision",
            "role": "decision_engine",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Evaluate",
            "context": {
                "original_task_id": "task",
                "original_success_criteria": ["No vulnerabilities"],
                "agent_status": "PASS",
                "quality_score": 85,
                "agent_handback": {
                    "security_score": 90,
                    "status": "PASS"
                }
            }
        }
        
        handback = engine.execute(delegate)
        decision = handback["decision"]
        assert decision["action"] == "proceed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
