"""
Test that QueueEnforcingProxy is properly wired into OrchestratorAgent.

Test C2a: Verify that the Orchestrator wraps QueueManager with QueueEnforcingProxy.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.orchestration.agents.orchestrator import OrchestratorAgent, QueueManager
from src.orchestration.agents.queue_enforcement_middleware import (
    QueueEnforcingProxy,
    QueueContext,
    QueueContextManager,
)


class TestQueueEnforcementWiring:
    """Verify QueueEnforcingProxy is wired into OrchestratorAgent.__init__."""

    def test_queue_manager_is_wrapped_by_proxy(self):
        """
        Test that OrchestratorAgent.__init__ wraps QueueManager with QueueEnforcingProxy.

        Success Criteria (AC1):
        - orchestrator.queue_manager is an instance of QueueEnforcingProxy
        - The wrapped agent is a QueueManager instance
        - The proxy's agent_role is "queue_manager"
        """
        with patch.object(QueueManager, '__init__', return_value=None):
            orchestrator = OrchestratorAgent(queue_dir=None, agent_context=None)

        # AC1: Verify proxy is instantiated
        assert isinstance(orchestrator.queue_manager, QueueEnforcingProxy), \
            "OrchestratorAgent.queue_manager should be a QueueEnforcingProxy instance"

        # AC1: Verify wrapped agent is QueueManager
        assert isinstance(orchestrator.queue_manager._agent, QueueManager), \
            "Proxy should wrap a QueueManager instance"

        # AC1: Verify agent_role is correct
        assert orchestrator.queue_manager._agent_role == "queue_manager", \
            "Proxy's agent_role should be 'queue_manager'"

    def test_proxy_forwards_queue_manager_methods(self):
        """
        Test that proxy transparently forwards QueueManager methods via __getattr__.

        Success Criteria (AC2):
        - All non-execute() methods are forwarded to wrapped QueueManager
        - Calling methods works as expected
        """
        with patch.object(QueueManager, '__init__', return_value=None):
            orchestrator = OrchestratorAgent(queue_dir=None, agent_context=None)

        # Mock a method on the wrapped QueueManager
        mock_method = Mock(return_value=["task1.yaml"])
        orchestrator.queue_manager._agent.list_incoming_tasks = mock_method

        # AC2: Call through proxy — should forward to wrapped manager
        result = orchestrator.queue_manager.list_incoming_tasks()

        assert result == ["task1.yaml"], \
            "Proxy should forward method calls to wrapped QueueManager"
        mock_method.assert_called_once()

    def test_proxy_with_queue_context(self):
        """
        Test that execute() on queue_manager.execute() works when queue context is active.

        Success Criteria (AC3):
        - QueueContext can be activated before calling execute()
        - Queue manager execute() succeeds when context is active
        """
        with patch.object(QueueManager, '__init__', return_value=None):
            orchestrator = OrchestratorAgent(queue_dir=None, agent_context=None)

        # Mock the execute method on wrapped QueueManager
        mock_execute = Mock(return_value={"status": "success"})
        orchestrator.queue_manager._agent.execute = mock_execute

        # AC3: Call execute within queue context
        with QueueContextManager():
            result = orchestrator.queue_manager.execute({"task_id": "test-task"})

        assert result == {"status": "success"}, \
            "Queue manager execute() should return mocked result"
        mock_execute.assert_called_once_with({"task_id": "test-task"})

    def test_proxy_blocks_execute_without_context(self):
        """
        Test that execute() raises QueueEnforcementError when context is not active.

        Success Criteria (AC4):
        - Calling execute() without queue context raises QueueEnforcementError
        - Error message references queue context requirement
        """
        from src.orchestration.agents.queue_enforcement_middleware import QueueEnforcementError

        with patch.object(QueueManager, '__init__', return_value=None):
            orchestrator = OrchestratorAgent(queue_dir=None, agent_context=None)

        # Mock the execute method on wrapped QueueManager
        mock_execute = Mock(return_value={"status": "success"})
        orchestrator.queue_manager._agent.execute = mock_execute

        # Ensure context is deactivated
        QueueContext.deactivate()

        # AC4: Calling execute() without context should raise QueueEnforcementError
        with pytest.raises(QueueEnforcementError) as exc_info:
            orchestrator.queue_manager.execute({"task_id": "test-task"})

        assert "queue context" in str(exc_info.value).lower(), \
            "Error message should reference queue context"
        mock_execute.assert_not_called()

    def test_import_statement_added(self):
        """
        Test that the import statement for QueueEnforcingProxy is in orchestrator.py.

        Success Criteria (AC5):
        - QueueEnforcingProxy is imported from queue_enforcement_middleware
        """
        import inspect
        from src.orchestration.agents import orchestrator as orch_module

        # AC5: Verify import exists by checking module imports
        source = inspect.getsource(orch_module)
        assert "from .queue_enforcement_middleware import QueueEnforcingProxy" in source, \
            "QueueEnforcingProxy import statement should be in orchestrator.py"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
