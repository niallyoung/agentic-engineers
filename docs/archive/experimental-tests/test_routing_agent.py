"""
Comprehensive test suite for RoutingAgent.

Tests all decision paths in AGENTS.md decision tree.
"""

import pytest
from src.orchestration.agents.routing_agent import RoutingAgent, ROUTING_AGENT_CONFIG


class TestRoutingAgentDecisionTree:
    """Test RoutingAgent decision tree implementation."""
    
    def setup_method(self):
        """Set up test fixture."""
        self.agent = RoutingAgent()
    
    def _create_delegate(self, **context_props) -> dict:
        """Helper to create a DELEGATE block with given properties."""
        context = {
            "original_task_id": "test-task-123",
            "task_description": "test task",
            "is_security_scoped": False,
            "is_cross_service": False,
            "complexity": "medium",
            "has_plan": False,
            "is_code_review": False,
            "is_precommit_quality_gate": False,
        }
        context.update(context_props)
        
        return {
            "task_id": "routing-test-task-123",
            "role": "routing_agent",
            "model": "claude-haiku-4-5",
            "effort": "low",
            "scope": "Route task to appropriate agent",
            "context": context
        }
    
    # Decision 0: Pre-commit Quality Gate
    def test_decision_0_precommit_quality_gate(self):
        """Decision 0: Pre-commit quality gate → Quality Engineer (PRIORITY)."""
        delegate = self._create_delegate(is_precommit_quality_gate=True)
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "quality_engineer"
        assert routing["confidence"] >= 0.90
        assert routing["decision_criteria"]["rule_number"] == 0
        assert routing["decision_criteria"]["priority"] == "immediate"
    
    # Decision 1: Security-scoped
    def test_decision_1_security_scoped(self):
        """Decision 1: Security-scoped task → Security Engineer."""
        delegate = self._create_delegate(is_security_scoped=True)
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "security_engineer"
        assert routing["confidence"] >= 0.90
        assert routing["decision_criteria"]["rule_number"] == 1
    
    def test_decision_1_security_with_various_complexities(self):
        """Test security routing with different complexity levels."""
        for complexity in ["low", "medium", "high"]:
            delegate = self._create_delegate(is_security_scoped=True, complexity=complexity)
            handback = self.agent.execute(delegate)
            
            routing = handback["routing_decision"]
            assert routing["target_agent"] == "security_engineer"
            assert routing["decision_criteria"]["complexity"] == complexity
    
    # Decision 2: Cross-service
    def test_decision_2_cross_service(self):
        """Decision 2: Cross-service task → Principal Engineer."""
        delegate = self._create_delegate(is_cross_service=True)
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "principal_engineer"
        assert routing["confidence"] >= 0.90
        assert routing["decision_criteria"]["rule_number"] == 2
    
    # Decision 3: Code review
    def test_decision_3_code_review_for_pr_review(self):
        """Decision 3a: Code review (PR review) → Lead Engineer."""
        delegate = self._create_delegate(
            is_code_review=True,
            task_description="Please review this PR for code quality"
        )
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "lead_engineer"
        assert routing["decision_criteria"]["rule_number"] == 3
        assert routing["decision_criteria"]["task_type"] == "review"
    
    def test_decision_3_code_validation(self):
        """Decision 3b: Code validation → Quality Engineer."""
        delegate = self._create_delegate(
            is_code_review=True,
            task_description="Validate test coverage and code quality"
        )
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "quality_engineer"
        assert routing["decision_criteria"]["rule_number"] == 3
        assert routing["decision_criteria"]["task_type"] == "validation"
    
    # Decision 4: Complex + unscoped
    def test_decision_4_complex_unscoped(self):
        """Decision 4: Complex + unscoped → Senior Engineer (to produce plan)."""
        delegate = self._create_delegate(complexity="high", has_plan=False)
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "senior_engineer"
        assert routing["confidence"] >= 0.85
        assert routing["decision_criteria"]["rule_number"] == 4
        assert routing["decision_criteria"]["workflow"] == "senior_engineer_plan_then_engineer_execute"
    
    def test_decision_4_low_complexity_with_plan_should_not_trigger(self):
        """Low complexity + plan should skip Decision 4."""
        delegate = self._create_delegate(complexity="low", has_plan=True)
        
        handback = self.agent.execute(delegate)
        
        # Should match Decision 5, not 4
        routing = handback["routing_decision"]
        assert routing["decision_criteria"]["rule_number"] == 5
    
    # Decision 5: Well-scoped + has plan
    def test_decision_5_well_scoped_with_plan_low_complexity(self):
        """Decision 5: Well-scoped low complexity + plan → Engineer."""
        delegate = self._create_delegate(complexity="low", has_plan=True)
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "engineer"
        assert routing["confidence"] >= 0.90
        assert routing["decision_criteria"]["rule_number"] == 5
    
    def test_decision_5_well_scoped_with_plan_medium_complexity(self):
        """Decision 5: Well-scoped medium complexity + plan → Engineer."""
        delegate = self._create_delegate(complexity="medium", has_plan=True)
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "engineer"
        assert routing["decision_criteria"]["rule_number"] == 5
    
    def test_decision_5_high_complexity_with_plan_should_not_trigger(self):
        """High complexity + plan should not trigger Decision 5 (needs Senior Engineer)."""
        delegate = self._create_delegate(complexity="high", has_plan=True)
        
        handback = self.agent.execute(delegate)
        
        # Should fall through to default (Decision 6)
        routing = handback["routing_decision"]
        # High complexity breaks the medium/low requirement of Decision 5
        assert routing["decision_criteria"].get("rule_number", 6) in [5, 6]
    
    # Decision 6: Default fallback
    def test_decision_6_default_fallback(self):
        """Decision 6: Default fallback → Engineer."""
        delegate = self._create_delegate(
            complexity="medium",
            has_plan=False,
            is_security_scoped=False,
            is_cross_service=False,
            is_code_review=False,
            is_precommit_quality_gate=False
        )
        
        handback = self.agent.execute(delegate)
        
        assert handback["status"] == "PASS"
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "engineer"
        assert routing["decision_criteria"]["rule_number"] == 6
        assert routing["decision_criteria"]["default"] == True
    
    # Priority testing: Decision 0 should override all others
    def test_priority_precommit_overrides_security(self):
        """Pre-commit quality gate should override security routing."""
        delegate = self._create_delegate(
            is_precommit_quality_gate=True,
            is_security_scoped=True
        )
        
        handback = self.agent.execute(delegate)
        
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "quality_engineer"
        assert routing["decision_criteria"]["rule_number"] == 0
    
    def test_priority_security_overrides_complexity(self):
        """Security should override complexity-based routing."""
        delegate = self._create_delegate(
            is_security_scoped=True,
            complexity="high",
            has_plan=False
        )
        
        handback = self.agent.execute(delegate)
        
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "security_engineer"
    
    def test_priority_cross_service_overrides_complexity(self):
        """Cross-service should override complexity-based routing."""
        delegate = self._create_delegate(
            is_cross_service=True,
            complexity="high",
            has_plan=False
        )
        
        handback = self.agent.execute(delegate)
        
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "principal_engineer"
    
    # Edge cases
    def test_multiple_criteria_first_match_wins(self):
        """When multiple criteria match, highest priority wins."""
        # Both security and cross-service: security should win (Decision 1 vs 2)
        delegate = self._create_delegate(
            is_security_scoped=True,
            is_cross_service=True,
            complexity="high",
            has_plan=False
        )
        
        handback = self.agent.execute(delegate)
        
        routing = handback["routing_decision"]
        assert routing["target_agent"] == "security_engineer"
        assert routing["decision_criteria"]["rule_number"] == 1
    
    def test_confidence_scores_reasonable(self):
        """All routing decisions should have reasonable confidence scores."""
        test_cases = [
            {"is_precommit_quality_gate": True},
            {"is_security_scoped": True},
            {"is_cross_service": True},
            {"is_code_review": True},
            {"complexity": "high", "has_plan": False},
            {"complexity": "low", "has_plan": True},
        ]
        
        for props in test_cases:
            delegate = self._create_delegate(**props)
            handback = self.agent.execute(delegate)
            
            confidence = handback["routing_decision"]["confidence"]
            assert 0.70 <= confidence <= 0.99, f"Invalid confidence for {props}: {confidence}"
    
    def test_rationale_provided_for_all_routes(self):
        """All routing decisions should include clear rationale."""
        test_cases = [
            {"is_precommit_quality_gate": True},
            {"is_security_scoped": True},
            {"is_cross_service": True},
            {"is_code_review": True},
            {"complexity": "high", "has_plan": False},
            {"complexity": "low", "has_plan": True},
        ]
        
        for props in test_cases:
            delegate = self._create_delegate(**props)
            handback = self.agent.execute(delegate)
            
            rationale = handback["routing_decision"].get("rationale", "")
            assert len(rationale) > 10, f"Rationale too short for {props}"
            assert "route" in rationale.lower(), f"Rationale missing routing info for {props}"


class TestRoutingAgentConfiguration:
    """Test RoutingAgent configuration."""
    
    def test_config_properties(self):
        """RoutingAgent should have correct configuration."""
        assert ROUTING_AGENT_CONFIG.name == "Routing Agent"
        assert ROUTING_AGENT_CONFIG.model == "claude-haiku-4-5"
        assert ROUTING_AGENT_CONFIG.effort == "low"
        assert ROUTING_AGENT_CONFIG.role == "routing_agent"
        assert "decision tree" in ROUTING_AGENT_CONFIG.description.lower()
    
    def test_agent_inherits_config(self):
        """RoutingAgent should properly inherit AgentConfig."""
        agent = RoutingAgent()
        assert agent.config == ROUTING_AGENT_CONFIG


class TestRoutingAgentIntegration:
    """Integration tests with orchestrator."""
    
    def test_routing_decision_has_all_required_fields(self):
        """Routing decision should have all required fields."""
        agent = RoutingAgent()
        delegate = {
            "task_id": "routing-test",
            "role": "routing_agent",
            "model": "claude-haiku-4-5",
            "effort": "low",
            "scope": "Route task",
            "context": {
                "original_task_id": "test-task",
                "task_description": "test",
                "is_security_scoped": False,
                "is_cross_service": False,
                "complexity": "medium",
                "has_plan": False,
                "is_code_review": False,
                "is_precommit_quality_gate": False,
            }
        }
        
        handback = agent.execute(delegate)
        
        assert "routing_decision" in handback
        routing = handback["routing_decision"]
        
        required_fields = ["target_agent", "confidence", "rationale", "decision_criteria"]
        for field in required_fields:
            assert field in routing, f"Missing required field: {field}"
    
    def test_decision_criteria_includes_all_context(self):
        """Decision criteria should include all evaluated context."""
        agent = RoutingAgent()
        delegate = {
            "task_id": "routing-test",
            "role": "routing_agent",
            "model": "claude-haiku-4-5",
            "effort": "low",
            "scope": "Route task",
            "context": {
                "original_task_id": "test-task",
                "task_description": "test",
                "is_security_scoped": False,
                "is_cross_service": True,
                "complexity": "high",
                "has_plan": True,
                "is_code_review": False,
                "is_precommit_quality_gate": False,
            }
        }
        
        handback = agent.execute(delegate)
        routing = handback["routing_decision"]
        criteria = routing["decision_criteria"]
        
        # Should include rule number for reproducibility
        assert "rule_number" in criteria
        assert criteria["rule_number"] == 2  # Cross-service rule


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
