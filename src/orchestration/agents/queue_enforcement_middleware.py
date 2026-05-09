"""
Queue Enforcement Middleware - Phase 4 Implementation

Enforces ORCHESTRATOR-FIRST principle: all agents must execute through queue protocol.

This module implements layered enforcement:
1. QueueContext singleton: Tracks whether code is running in queue context
2. QueueEnforcingProxy: Validates queue context before agent.execute() calls
3. Factory validation: Checks queue context at agent creation
4. Clear error messages: Guides users to proper queue usage

Architecture: Implements Pattern 1 from Task 5101 (QueueEnforcingProxy pattern)
with Context Manager support and Factory Validation layers.
"""

import logging
from typing import Any, Optional
from threading import local

logger = logging.getLogger(__name__)


class QueueContext:
    """
    Singleton for queue execution context tracking.
    
    Maintains thread-local flag indicating whether code is currently executing
    within an active queue context (i.e., called by Orchestrator's task loop).
    
    SPEC.md Requirement (lines 25-123):
    > "All work MUST flow through the Orchestrator. No exceptions. The only 
    >  entry point for agent execution is the Orchestrator's queue polling loop."
    """
    
    _context = local()
    
    @classmethod
    def activate(cls) -> None:
        """Mark that we're entering queue context."""
        cls._context.active = True
        logger.debug("Queue context activated")
    
    @classmethod
    def deactivate(cls) -> None:
        """Mark that we're exiting queue context."""
        cls._context.active = False
        logger.debug("Queue context deactivated")
    
    @classmethod
    def is_active(cls) -> bool:
        """Check if queue context is currently active."""
        active = getattr(cls._context, 'active', False)
        return active
    
    @classmethod
    def mark_testing(cls) -> None:
        """
        Explicitly activate context for test code.
        
        Test harnesses should call this to indicate they're testing agent behavior.
        This allows tests to bypass the queue requirement with explicit intent.
        
        Usage:
            with QueueContextManager():
                agent = create_agent("engineer")
                result = agent.execute(test_item)
        
        IMPORTANT: This should only be used in test code. Production code must
        route through the Orchestrator's queue.
        """
        cls.activate()
        logger.info("Queue context marked for testing")


class QueueContextManager:
    """
    Context manager for explicit queue context marking.
    
    Activates queue context on entry, deactivates on exit. Used by:
    - Orchestrator main loop (mark queue processing)
    - Test harnesses (mark testing context)
    - Examples and demos (show proper usage pattern)
    
    Example:
        with QueueContextManager():
            engineer = create_agent("engineer")
            result = engineer.execute(work_item)
            # OK: both create_agent() and execute() succeed
    """
    
    def __enter__(self):
        """Enter: Activate queue context."""
        QueueContext.activate()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit: Deactivate queue context."""
        QueueContext.deactivate()
        return False


class QueueEnforcementError(Exception):
    """
    Raised when agent.execute() is called outside active queue context.
    
    SPEC.md requires all agent execution to flow through the Orchestrator's queue.
    This exception indicates a violation of that requirement.
    
    The exception message provides:
    1. Clear description of the violation
    2. Pointer to SPEC.md constraint
    3. Actionable fix instructions (test vs production)
    4. Example code showing correct usage
    """
    pass


class QueueEnforcingProxy:
    """
    Transparent proxy that enforces queue-only agent execution.
    
    Wraps agent instances and validates queue context before forwarding execute()
    calls. All other methods/attributes are transparently forwarded to the wrapped
    agent, making the proxy invisible to callers.
    
    This proxy is the primary enforcement mechanism for the ORCHESTRATOR-FIRST
    execution model defined in SPEC.md.
    
    Design Pattern: QueueEnforcingProxy (Pattern 1 from Task 5101)
    - Single point of enforcement at execute() call site
    - Clean API: create_agent() still returns intuitive Agent interface
    - Easy to test: inject mock queue context via proxy
    - Zero changes to agent implementations
    - Allows agent-to-agent delegation if within queue context
    
    Example:
        # Direct instantiation (bypasses factory) - still gets proxy
        from src.orchestration.agents.queue_enforcement_middleware import QueueEnforcingProxy
        from src.orchestration.agents.implementations import EngineerAgent
        
        agent = QueueEnforcingProxy(EngineerAgent(), "engineer")
        
        # This fails (no queue context):
        agent.execute(work_item)
        # QueueEnforcementError: Agent 'engineer' attempted to execute()...
        
        # This succeeds (within queue context):
        with QueueContextManager():
            agent.execute(work_item)  # OK
    """
    
    def __init__(self, agent: Any, agent_role: str):
        """
        Initialize proxy.
        
        Args:
            agent: The wrapped agent instance
            agent_role: The role name (for error messages and debugging)
        """
        self._agent = agent
        self._agent_role = agent_role
        logger.debug(f"Created QueueEnforcingProxy for agent role '{agent_role}'")
    
    def execute(self, work_item: Any) -> Any:
        """
        Execute work through queue context enforcement.
        
        Validates that queue context is active before forwarding the execute()
        call to the wrapped agent. This is the enforcement point that prevents
        direct agent execution outside the queue system.
        
        Args:
            work_item: Work to execute (typically a DELEGATE block)
        
        Returns:
            Result from agent.execute(work_item)
        
        Raises:
            QueueEnforcementError: If called outside queue context
        """
        if not QueueContext.is_active():
            raise QueueEnforcementError(
                f"Agent '{self._agent_role}' attempted to execute() outside queue context.\n"
                f"\n"
                f"REQUIREMENT: All agent execution must flow through the Orchestrator's queue.\n"
                f"See SPEC.md lines 25-123 (ORCHESTRATOR-FIRST EXECUTION MODEL).\n"
                f"\n"
                f"TO FIX:\n"
                f"  • If this is test code:\n"
                f"      from src.orchestration.agents.queue_enforcement_middleware import QueueContextManager\n"
                f"      with QueueContextManager():\n"
                f"          agent = create_agent('{self._agent_role}')\n"
                f"          result = agent.execute(work_item)\n"
                f"\n"
                f"  • If this is production code:\n"
                f"      Route through Orchestrator.queue.enqueue() instead of direct execution.\n"
                f"      The Orchestrator will create and execute the agent in queue context.\n"
            )
        
        # Validation passed, forward to wrapped agent
        logger.debug(f"Executing agent '{self._agent_role}' in queue context")
        return self._agent.execute(work_item)
    
    def __getattr__(self, name: str) -> Any:
        """
        Transparently forward all other attributes/methods to wrapped agent.
        
        This allows the proxy to be used anywhere the original agent was used,
        without requiring callers to know about the proxy layer. Only execute()
        calls are intercepted for enforcement; everything else passes through.
        
        Args:
            name: Attribute/method name
        
        Returns:
            Attribute from wrapped agent
        """
        return getattr(self._agent, name)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"QueueEnforcingProxy({self._agent_role})"
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"QueueEnforcingProxy({self._agent_role})"


class QueueEnforcementLogger:
    """
    Logs all queue enforcement events for audit and debugging.
    
    Tracks:
    - Agent creation attempts (with/without context)
    - Agent execution attempts (with/without context)
    - Context activation/deactivation
    - Enforcement violations
    
    Useful for:
    - Debugging context issues
    - Auditing compliance
    - Performance analysis
    - Integration testing
    """
    
    @staticmethod
    def log_agent_creation(agent_role: str, in_context: bool) -> None:
        """Log agent creation event."""
        status = "IN CONTEXT" if in_context else "NO CONTEXT"
        logger.info(f"[ENFORCEMENT] Agent created: role='{agent_role}', status={status}")
    
    @staticmethod
    def log_agent_execution(agent_role: str, in_context: bool) -> None:
        """Log agent execution attempt."""
        status = "ALLOWED" if in_context else "BLOCKED"
        logger.info(f"[ENFORCEMENT] Agent execution: role='{agent_role}', status={status}")
    
    @staticmethod
    def log_violation(agent_role: str, violation_type: str) -> None:
        """Log enforcement violation."""
        logger.warning(f"[ENFORCEMENT] Violation detected: role='{agent_role}', type={violation_type}")


__all__ = [
    "QueueContext",
    "QueueContextManager",
    "QueueEnforcementError",
    "QueueEnforcingProxy",
    "QueueEnforcementLogger",
]
