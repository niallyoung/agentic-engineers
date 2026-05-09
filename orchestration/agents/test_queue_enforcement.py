"""
Queue Enforcement Middleware - Comprehensive Test Suite

Tests for Phase 4 implementation of ORCHESTRATOR-FIRST enforcement.

Test Categories:
1. Core Functionality Tests
   - QueueContext activation/deactivation
   - Context state checking
   - Thread-local isolation
   
2. Proxy Enforcement Tests
   - Detection of violations
   - Blocking of violations
   - Transparent passthrough for other methods
   
3. False Positive Tests
   - No blocking of legitimate queue calls
   - Agent-to-agent delegation within context
   - Orchestrator integration
   
4. Integration Tests
   - Real agent execution within context
   - Factory integration
   - Test harness patterns
   
5. Error Message Tests
   - Clear, actionable error messages
   - Proper constraint references
   - Fix instructions
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any

from orchestration.agents.queue_enforcement_middleware import (
    QueueContext,
    QueueContextManager,
    QueueEnforcementError,
    QueueEnforcingProxy,
    QueueEnforcementLogger,
)


# ============================================================================
# Test Fixtures
# ============================================================================

class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, role: str = "test_agent"):
        self.role = role
        self.execute_called = False
        self.execute_work_item = None
    
    def execute(self, work_item):
        """Execute work (to be intercepted by proxy)."""
        self.execute_called = True
        self.execute_work_item = work_item
        return {"status": "success", "role": self.role}
    
    def get_config(self):
        """Non-execute method (should pass through proxy)."""
        return {"role": self.role}


@pytest.fixture(autouse=True)
def reset_queue_context():
    """Reset queue context before and after each test."""
    QueueContext.deactivate()
    yield
    QueueContext.deactivate()


# ============================================================================
# QueueContext Tests
# ============================================================================

class TestQueueContextBasics:
    """Test QueueContext singleton basic functionality."""
    
    def test_context_starts_inactive(self):
        """Queue context should start deactivated."""
        QueueContext.deactivate()
        assert not QueueContext.is_active()
    
    def test_activate_sets_context_active(self):
        """Activating context should set is_active() to True."""
        QueueContext.activate()
        assert QueueContext.is_active()
    
    def test_deactivate_clears_context(self):
        """Deactivating context should set is_active() to False."""
        QueueContext.activate()
        assert QueueContext.is_active()
        QueueContext.deactivate()
        assert not QueueContext.is_active()
    
    def test_multiple_activations(self):
        """Multiple activations should remain active."""
        QueueContext.activate()
        QueueContext.activate()
        assert QueueContext.is_active()
    
    def test_mark_testing_activates_context(self):
        """mark_testing() should activate context."""
        QueueContext.mark_testing()
        assert QueueContext.is_active()


class TestQueueContextThreadLocal:
    """Test thread-local isolation of queue context."""
    
    def test_context_is_thread_local(self):
        """Context should be thread-local (different per thread)."""
        import threading
        
        QueueContext.deactivate()
        assert not QueueContext.is_active()
        
        result = []
        
        def activate_in_thread():
            QueueContext.activate()
            result.append(QueueContext.is_active())
        
        thread = threading.Thread(target=activate_in_thread)
        thread.start()
        thread.join()
        
        # Thread activated, main thread should still be deactivated
        assert result[0] is True
        assert not QueueContext.is_active()


# ============================================================================
# QueueContextManager Tests
# ============================================================================

class TestQueueContextManager:
    """Test QueueContextManager context manager."""
    
    def test_context_manager_activates_on_enter(self):
        """Entering context manager should activate queue context."""
        assert not QueueContext.is_active()
        with QueueContextManager():
            assert QueueContext.is_active()
    
    def test_context_manager_deactivates_on_exit(self):
        """Exiting context manager should deactivate queue context."""
        with QueueContextManager():
            assert QueueContext.is_active()
        assert not QueueContext.is_active()
    
    def test_context_manager_deactivates_on_exception(self):
        """Queue context should deactivate even if exception in with block."""
        try:
            with QueueContextManager():
                assert QueueContext.is_active()
                raise ValueError("Test exception")
        except ValueError:
            pass
        assert not QueueContext.is_active()
    
    def test_nested_context_managers(self):
        """Nested context managers should work (inner deactivates outer)."""
        assert not QueueContext.is_active()
        with QueueContextManager():
            assert QueueContext.is_active()
            with QueueContextManager():
                assert QueueContext.is_active()
            # Inner context deactivates, so outer is also deactivated
            # This is expected behavior (not reference-counted)
            assert not QueueContext.is_active()
        assert not QueueContext.is_active()
    
    def test_context_manager_returns_self(self):
        """Context manager __enter__ should return self."""
        with QueueContextManager() as cm:
            assert isinstance(cm, QueueContextManager)


# ============================================================================
# QueueEnforcingProxy Detection Tests
# ============================================================================

class TestQueueEnforcingProxyDetection:
    """Test that proxy detects violations."""
    
    def test_proxy_blocks_execute_outside_context(self):
        """Proxy should raise error when execute() called outside context."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        QueueContext.deactivate()
        
        with pytest.raises(QueueEnforcementError) as exc_info:
            proxy.execute({"task": "test"})
        
        assert "attempted to execute() outside queue context" in str(exc_info.value)
        assert "engineer" in str(exc_info.value)
    
    def test_proxy_allows_execute_in_context(self):
        """Proxy should allow execute() when context is active."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        with QueueContextManager():
            result = proxy.execute({"task": "test"})
        
        assert result["status"] == "success"
        assert agent.execute_called
    
    def test_proxy_forwards_work_item(self):
        """Proxy should forward work_item unchanged to wrapped agent."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        work_item = {"task": "test", "data": [1, 2, 3]}
        
        with QueueContextManager():
            proxy.execute(work_item)
        
        assert agent.execute_work_item == work_item
    
    def test_proxy_returns_agent_result(self):
        """Proxy should return result from wrapped agent unchanged."""
        agent = MockAgent("engineer")
        agent.execute = Mock(return_value={"custom": "result"})
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        with QueueContextManager():
            result = proxy.execute({"task": "test"})
        
        assert result == {"custom": "result"}


# ============================================================================
# QueueEnforcingProxy Transparency Tests
# ============================================================================

class TestQueueEnforcingProxyTransparency:
    """Test that proxy transparently forwards non-execute methods."""
    
    def test_proxy_forwards_non_execute_methods(self):
        """Proxy should forward non-execute methods to wrapped agent."""
        agent = MockAgent("engineer")
        agent.get_config = Mock(return_value={"role": "engineer"})
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        # Should work even without queue context
        result = proxy.get_config()
        
        agent.get_config.assert_called_once()
        assert result == {"role": "engineer"}
    
    def test_proxy_forwards_properties(self):
        """Proxy should forward property access to wrapped agent."""
        agent = MockAgent("engineer")
        agent.role = "engineer"
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        # Should work even without queue context
        assert proxy.role == "engineer"
    
    def test_proxy_repr(self):
        """Proxy __repr__ should show role."""
        proxy = QueueEnforcingProxy(MockAgent("engineer"), "engineer")
        assert "QueueEnforcingProxy" in repr(proxy)
        assert "engineer" in repr(proxy)
    
    def test_proxy_str(self):
        """Proxy __str__ should show role."""
        proxy = QueueEnforcingProxy(MockAgent("engineer"), "engineer")
        assert "QueueEnforcingProxy" in str(proxy)
        assert "engineer" in str(proxy)


# ============================================================================
# QueueEnforcingProxy Error Message Tests
# ============================================================================

class TestQueueEnforcingProxyErrorMessages:
    """Test that error messages are clear and actionable."""
    
    def test_error_message_includes_role(self):
        """Error message should include the agent role."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        with pytest.raises(QueueEnforcementError) as exc_info:
            proxy.execute({"task": "test"})
        
        assert "engineer" in str(exc_info.value)
    
    def test_error_message_includes_spec_reference(self):
        """Error message should reference SPEC.md constraint."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        with pytest.raises(QueueEnforcementError) as exc_info:
            proxy.execute({"task": "test"})
        
        error_msg = str(exc_info.value)
        assert "SPEC.md" in error_msg
        assert "ORCHESTRATOR-FIRST" in error_msg
    
    def test_error_message_includes_test_fix(self):
        """Error message should include fix for test code."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        with pytest.raises(QueueEnforcementError) as exc_info:
            proxy.execute({"task": "test"})
        
        error_msg = str(exc_info.value)
        assert "test code" in error_msg
        assert "QueueContextManager" in error_msg
    
    def test_error_message_includes_production_fix(self):
        """Error message should include fix for production code."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        with pytest.raises(QueueEnforcementError) as exc_info:
            proxy.execute({"task": "test"})
        
        error_msg = str(exc_info.value)
        assert "production code" in error_msg
        assert "Orchestrator.queue" in error_msg


# ============================================================================
# Integration Tests
# ============================================================================

class TestQueueEnforcementIntegration:
    """Integration tests for queue enforcement in realistic scenarios."""
    
    def test_orchestrator_agent_delegation(self):
        """Orchestrator should be able to create and execute sub-agents."""
        # Simulate orchestrator creating sub-agents within queue context
        with QueueContextManager():
            sub_agent = MockAgent("engineer")
            proxy = QueueEnforcingProxy(sub_agent, "engineer")
            
            result = proxy.execute({"task": "subtask"})
            
            assert result["status"] == "success"
    
    def test_multiple_agents_in_context(self):
        """Multiple agents should execute successfully in queue context."""
        with QueueContextManager():
            for role in ["engineer", "senior_engineer", "lead_engineer"]:
                agent = MockAgent(role)
                proxy = QueueEnforcingProxy(agent, role)
                result = proxy.execute({"task": f"task_for_{role}"})
                assert result["status"] == "success"
    
    def test_sequential_agent_execution(self):
        """Sequential agent execution within context should work."""
        with QueueContextManager():
            agent1 = MockAgent("engineer")
            proxy1 = QueueEnforcingProxy(agent1, "engineer")
            result1 = proxy1.execute({"task": "first"})
            
            agent2 = MockAgent("senior_engineer")
            proxy2 = QueueEnforcingProxy(agent2, "senior_engineer")
            result2 = proxy2.execute({"task": "second"})
            
            assert result1["status"] == "success"
            assert result2["status"] == "success"


# ============================================================================
# False Positive Tests
# ============================================================================

class TestFalsePositives:
    """Test that legitimate usage patterns don't trigger false positives."""
    
    def test_agent_to_agent_delegation_in_context(self):
        """Agent-to-agent delegation within queue context should work."""
        with QueueContextManager():
            # Agent 1 creates and uses Agent 2
            agent1 = MockAgent("orchestrator")
            proxy1 = QueueEnforcingProxy(agent1, "orchestrator")
            
            agent2 = MockAgent("engineer")
            proxy2 = QueueEnforcingProxy(agent2, "engineer")
            
            # Both should work within queue context
            result1 = proxy1.execute({"task": "orchestration"})
            result2 = proxy2.execute({"task": "engineering"})
            
            assert result1["status"] == "success"
            assert result2["status"] == "success"
    
    def test_non_execute_methods_always_work(self):
        """Non-execute methods should work regardless of queue context."""
        agent = MockAgent("engineer")
        agent.validate = Mock(return_value=True)
        agent.configure = Mock(return_value=None)
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        # Without context
        QueueContext.deactivate()
        assert proxy.validate()
        proxy.configure()
        agent.validate.assert_called()
        agent.configure.assert_called()


# ============================================================================
# Lifecycle Tests
# ============================================================================

class TestQueueEnforcementLifecycle:
    """Test complete lifecycle of queue enforcement."""
    
    def test_enforcement_lifecycle(self):
        """Test complete lifecycle: deactivate -> activate -> execute -> deactivate."""
        agent = MockAgent("engineer")
        proxy = QueueEnforcingProxy(agent, "engineer")
        
        # Start: context inactive
        assert not QueueContext.is_active()
        
        # Should fail without context
        with pytest.raises(QueueEnforcementError):
            proxy.execute({"task": "test"})
        
        # Activate context
        with QueueContextManager():
            # Should succeed with context
            result = proxy.execute({"task": "test"})
            assert result["status"] == "success"
        
        # After context exit, should fail again
        assert not QueueContext.is_active()
        with pytest.raises(QueueEnforcementError):
            proxy.execute({"task": "test"})


# ============================================================================
# Enforcement Logger Tests
# ============================================================================

class TestQueueEnforcementLogger:
    """Test logging of enforcement events."""
    
    def test_logger_logs_agent_creation(self, caplog):
        """Logger should log agent creation events."""
        with caplog.at_level(logging.INFO):
            QueueEnforcementLogger.log_agent_creation("engineer", in_context=True)
        
        assert "[ENFORCEMENT]" in caplog.text
        assert "engineer" in caplog.text
        assert "created" in caplog.text.lower()
    
    def test_logger_logs_agent_execution(self, caplog):
        """Logger should log agent execution events."""
        with caplog.at_level(logging.INFO):
            QueueEnforcementLogger.log_agent_execution("engineer", in_context=True)
        
        assert "[ENFORCEMENT]" in caplog.text
        assert "execution" in caplog.text.lower()
    
    def test_logger_logs_violations(self, caplog):
        """Logger should log enforcement violations."""
        with caplog.at_level(logging.WARNING):
            QueueEnforcementLogger.log_violation("engineer", "direct_execution")
        
        assert "[ENFORCEMENT]" in caplog.text
        assert "violation" in caplog.text.lower()


# ============================================================================
# Exception Tests
# ============================================================================

class TestQueueEnforcementError:
    """Test QueueEnforcementError exception."""
    
    def test_error_is_exception(self):
        """QueueEnforcementError should be an Exception."""
        error = QueueEnforcementError("test")
        assert isinstance(error, Exception)
    
    def test_error_message_preserved(self):
        """Error message should be preserved."""
        msg = "Custom error message"
        error = QueueEnforcementError(msg)
        assert str(error) == msg


# ============================================================================
# Edge Cases and Stress Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and stress scenarios."""
    
    def test_rapid_context_toggles(self):
        """Rapid activation/deactivation should work correctly."""
        for _ in range(100):
            QueueContext.activate()
            assert QueueContext.is_active()
            QueueContext.deactivate()
            assert not QueueContext.is_active()
    
    def test_deeply_nested_context_managers(self):
        """Deeply nested context managers should work."""
        depth = 10
        
        def nesting(level):
            if level == 0:
                return QueueContext.is_active()
            with QueueContextManager():
                return nesting(level - 1)
        
        assert nesting(depth)
    
    def test_proxy_with_none_agent(self):
        """Proxy should handle None-like agents gracefully."""
        agent = MockAgent("test")
        agent.execute = Mock(return_value=None)
        proxy = QueueEnforcingProxy(agent, "test")
        
        with QueueContextManager():
            result = proxy.execute({"task": "test"})
            assert result is None
    
    def test_proxy_with_exception_in_agent(self):
        """Proxy should propagate exceptions from wrapped agent."""
        agent = MockAgent("test")
        agent.execute = Mock(side_effect=ValueError("Agent error"))
        proxy = QueueEnforcingProxy(agent, "test")
        
        with QueueContextManager():
            with pytest.raises(ValueError) as exc_info:
                proxy.execute({"task": "test"})
            
            assert "Agent error" in str(exc_info.value)


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
