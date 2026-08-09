"""
Orchestrator Testing Harness - FOR TESTING ONLY

This file demonstrates how to invoke the OrchestratorAgent for testing purposes.
It is NOT part of the production system and should NOT be imported or executed
as a regular script.

For production use, the Orchestrator agent is invoked through the agent harness
by reading ~/.copilot/agents/orchestrator.agent.md or ~/.claude/agents/orchestrator.agent.md
"""

from src.orchestration.agents.orchestrator import OrchestratorAgent
from datetime import datetime


def test_orchestrator_with_context(agent_context: str = 'copilot', idle_timeout: int = 30):
    """
    Test harness for Orchestrator with specific context.
    
    Args:
        agent_context: 'copilot' or 'claude'
        idle_timeout: seconds to wait before exiting (default 30)
    """
    print(f"\n{'='*70}")
    print(f"ORCHESTRATOR TEST HARNESS (context={agent_context}, timeout={idle_timeout}s)")
    print(f"{'='*70}\n")
    
    orchestrator = OrchestratorAgent(agent_context=agent_context, idle_timeout=idle_timeout)
    print(f"Queue: {orchestrator.queue_manager.base_dir}")
    print()

    # poll_and_process() (subprocess-poll dispatch loop) has been removed —
    # the harness now spawns sub-agents directly via the Agent tool instead
    # of this class draining incoming/ in a loop. This manual harness has not
    # been updated for direct-spawn dispatch yet; there is currently nothing
    # here to drive task processing.
    print("NOTE: poll_and_process() has been removed (direct sub-agent spawning "
          "replaces queue polling). This harness does not yet drive direct-spawn "
          "dispatch, so no tasks will be processed by this call.")

    print(f"\n{'='*70}")
    print("ORCHESTRATOR TEST RESULTS")
    print(f"{'='*70}")
    print(f"Tasks Processed: {orchestrator.tasks_processed}")
    print(f"Successful:      {orchestrator.tasks_success}")
    print(f"Escalated:       {orchestrator.tasks_escalated}")
    print(f"{'='*70}\n")


def test_queue_manager():
    """Test harness for QueueManager context detection."""
    from src.orchestration.agents.orchestrator import QueueManager
    
    print("\nQUEUE MANAGER TEST HARNESS\n")
    
    print("Test 1: Auto-detect context")
    qm = QueueManager()
    print(f"  Detected: {qm.agent_context} → {qm.base_dir}\n")
    
    print("Test 2: Force Copilot context")
    qm_copilot = QueueManager(agent_context='copilot')
    print(f"  Forced:   {qm_copilot.agent_context} → {qm_copilot.base_dir}\n")
    
    print("Test 3: Force Claude context")
    qm_claude = QueueManager(agent_context='claude')
    print(f"  Forced:   {qm_claude.agent_context} → {qm_claude.base_dir}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'queue-manager':
        test_queue_manager()
    else:
        context = sys.argv[1] if len(sys.argv) > 1 else 'copilot'
        timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        test_orchestrator_with_context(agent_context=context, idle_timeout=timeout)
