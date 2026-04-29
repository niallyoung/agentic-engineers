"""
Agent Implementation Template

Use this template as a starting point for implementing agent behavior.
Replace stub `do_work()` method with delegation to sub-agents via DELEGATE/HANDBACK.

CONSTRAINT: agentic-engineers is SELF-CONTAINED. No external calls (Claude API, shell,
services). Agents delegate to other agents via DELEGATE/HANDBACK/FEEDBACK protocol.

This template follows patterns from ENGINEER-IMPLEMENTATION-REFERENCE.py
and demonstrates the structure for all 13 agents.
"""

from . import Agent, AgentConfig
from typing import Dict, Optional
import json


class TemplateAgent(Agent):
    """
    Template for implementing a new agent.

    Replace:
    1. Class name (TemplateAgent → YourAgentName)
    2. Config (use appropriate CONFIG from __init__.py)
    3. do_work() method (stub → real implementation)
    4. Helper methods (add actual logic)
    """

    def __init__(self, config: AgentConfig):
        """Initialize with agent configuration."""
        super().__init__(config)

    def do_work(self) -> Dict:
        """
        Main work execution via agent delegation.

        STUB VERSION: Returns mock results
        REAL VERSION: Delegates to sub-agents via DELEGATE/HANDBACK protocol

        Returns:
            Dict with results to merge into HANDBACK block
        """

        # ============ Phase 1: Extract inputs ============
        scope = self.delegate_block.get("scope", "")
        context = self.delegate_block.get("context", {})
        effort = self.delegate_block.get("effort", "medium")

        # Validate required fields
        if not scope:
            raise ValueError("scope is required")

        # ============ Phase 2: Determine sub-agent to delegate to ============
        # Example: decide which agent(s) handle this work
        sub_agent_role = self._select_sub_agent(scope, effort)

        # ============ Phase 3: Build DELEGATE block for sub-agent ============
        sub_delegate = self._build_delegate(sub_agent_role, scope, context)

        # ============ Phase 4: Delegate to sub-agent ============
        # STUB: Return mock result
        # REAL: sub_agent = create_agent(sub_agent_role)
        #       handback = sub_agent.execute(sub_delegate)
        handback = self._delegate_to_sub_agent(sub_agent_role, sub_delegate)

        # ============ Phase 5: Parse HANDBACK + structure output ============
        parsed_result = self._parse_handback(handback)

        # ============ Phase 6: Generate HANDBACK ============
        return {
            "result": parsed_result,
            "confidence": self._calculate_confidence(parsed_result),
            "deliverables": handback.get("deliverables", [])
        }

    def _select_sub_agent(self, scope: str, effort: str) -> str:
        """
        Determine which sub-agent to delegate to based on scope & effort.

        Returns:
            Sub-agent role name (e.g., 'engineer', 'senior_engineer')
        """
        # Example logic: harder tasks delegate to more capable agents
        if effort == "high":
            return "senior_engineer"
        return "engineer"

    def _build_delegate(self, sub_agent_role: str, scope: str, context: Dict) -> Dict:
        """
        Build DELEGATE block for sub-agent.

        Returns:
            DELEGATE block ready to send to sub-agent
        """
        return {
            "handoff_type": "DELEGATE",
            "task_id": self.task_id,
            "role": sub_agent_role,
            "model": self.config.model,
            "effort": self.delegate_block.get("effort", "medium"),
            "scope": scope,
            "context": context
        }

    def _delegate_to_sub_agent(self, sub_agent_role: str, delegate: Dict) -> Dict:
        """
        Delegate work to sub-agent via DELEGATE/HANDBACK protocol.

        STUB: Return mock handback
        REAL: from implementations import create_agent
              agent = create_agent(sub_agent_role)
              return agent.execute(delegate)
        """
        return {
            "handoff_type": "HANDBACK",
            "status": "PASS",
            "deliverables": [f"Delegated to {sub_agent_role}"],
            "confidence": 0.75
        }

    def _parse_handback(self, handback: Dict) -> Dict:
        """
        Parse sub-agent's HANDBACK block.

        Returns:
            Structured result from sub-agent
        """
        return {
            "delegated_to": handback.get("role", "unknown"),
            "status": handback.get("status", "UNKNOWN"),
            "deliverables": handback.get("deliverables", [])
        }

    def _calculate_confidence(self, result: Dict) -> float:
        """
        Calculate confidence score for this result.

        Base: 0.70, adjust based on sub-agent status
        Clamped to [0.30, 1.00]
        """
        if result.get("status") == "PASS":
            return 0.85
        return 0.50


# ============ REAL IMPLEMENTATION EXAMPLE ============
# This shows what a real implementation would look like (agent delegation, not external calls)

class EngineerAgentReal(Agent):
    """Real Engineer Agent implementation (delegates to task execution agents)."""

    def __init__(self):
        from . import ENGINEER_CONFIG
        super().__init__(ENGINEER_CONFIG)

    def do_work(self) -> Dict:
        """Execute a well-scoped task with pre-written plan via sub-agent delegation."""

        plan = self.delegate_block.get("plan", [])
        success_criteria = self.delegate_block.get("success_criteria", [])

        if not plan:
            raise ValueError("DELEGATE must include 'plan'")

        # Phase 1: Validate plan
        for i, step in enumerate(plan, 1):
            if not step or not isinstance(step, str):
                raise ValueError(f"Plan step {i} is invalid")

        # Phase 2: Execute each step via sub-agent delegation
        execution_results = []
        all_deliverables = []

        for i, step in enumerate(plan, 1):
            # Delegate step execution to a task-execution agent
            # Real: from implementations import create_agent
            #       executor = create_agent("task_executor")
            #       step_delegate = {task_id, role, effort, scope: step, ...}
            #       handback = executor.execute(step_delegate)

            result = self._execute_step_via_delegation(i, step)
            execution_results.append(result)

            if result["status"] == "FAILURE":
                raise RuntimeError(f"Step {i} failed: {result['error']}")

            all_deliverables.extend(result.get("deliverables", []))

        # Phase 3: Validate success criteria via validation agent
        criteria_results = []
        for criterion in success_criteria:
            # Delegate validation to criteria-validation agent
            # Real: validator = create_agent("criteria_validator")
            #       validation_delegate = {...}
            #       validation_handback = validator.execute(validation_delegate)

            validated = self._validate_criterion_via_delegation(criterion, all_deliverables)
            criteria_results.append(validated)

        # Phase 4: Calculate quality score
        criteria_passed = sum(1 for c in criteria_results if c["passed"])
        quality_score = (criteria_passed / len(criteria_results)) * 100 if criteria_results else 0

        # Phase 5: Return HANDBACK
        return {
            "execution_results": execution_results,
            "success_criteria_results": criteria_results,
            "quality_score": quality_score,
            "deliverables": all_deliverables,
            "confidence": max(0.30, min(1.0, 0.30 + (quality_score / 100.0) * 0.65))
        }

    def _execute_step_via_delegation(self, step_number: int, step_description: str) -> Dict:
        """
        Execute a single step by delegating to sub-agent.

        Real implementation would:
        1. Create DELEGATE block for task-execution agent
        2. Call create_agent("task_executor").execute(delegate)
        3. Parse HANDBACK to extract deliverables
        4. Return structured result
        """
        return {
            "step": step_number,
            "description": step_description,
            "status": "SUCCESS",
            "deliverables": [f"Completed: {step_description}"]
        }

    def _validate_criterion_via_delegation(self, criterion: str, deliverables: list) -> Dict:
        """
        Validate a success criterion by delegating to sub-agent.

        Real implementation would:
        1. Create DELEGATE block for criteria-validation agent
        2. Call create_agent("criteria_validator").execute(delegate)
        3. Parse HANDBACK to get pass/fail
        4. Return result
        """
        return {
            "criterion": criterion,
            "passed": True,
            "evidence": "Validated via delegation"
        }


# ============ HOW TO IMPLEMENT YOUR AGENT ============

"""
Step-by-step guide for implementing a real agent:

🔒 CONSTRAINT: agentic-engineers is SELF-CONTAINED. No external calls.
Agents delegate to other agents via DELEGATE/HANDBACK/FEEDBACK protocol.

1. START with the stub in implementations.py
   - Your agent skeleton already exists
   - It has input validation, error handling, HANDBACK generation

2. UNDERSTAND the architecture:
   - execute() → _validate_input() → do_work() → return HANDBACK
   - do_work() determines which sub-agent(s) to delegate to
   - Returns HANDBACK from sub-agent delegation
   - You only need to replace do_work() method

3. WRITE your do_work() implementation:
   a. Extract inputs from self.delegate_block
   b. Validate required fields
   c. Determine which sub-agent(s) handle this work
   d. Build DELEGATE block for sub-agent
   e. Call: agent = create_agent(role); handback = agent.execute(delegate)
   f. Parse sub-agent's HANDBACK
   g. Calculate confidence
   h. Return dict with results

4. REFERENCE the examples:
   - ENGINEER-IMPLEMENTATION-REFERENCE.py (250 lines, delegation pattern)
   - ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py (300 lines, routing example)

5. USE the testing harness:
   - Run example_end_to_end.py to see your agent in action
   - Run testing_harness.py to validate Quality Gate decisions

6. MEASURE results:
   - Confidence scores (from sub-agent HANDBACK)
   - Execution time (sub-agent timing)
   - Chain depth (how many delegation levels)

Example implementation for SecurityEngineerAgent (delegating to analysis agent):

    def do_work(self) -> Dict:
        scope = self.delegate_block.get("scope", "")

        # Determine: this is security work, delegate to analysis agent
        sub_agent_role = "security_analyzer"

        # Build DELEGATE for analysis agent
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": self.task_id,
            "role": sub_agent_role,
            "effort": "high",
            "scope": scope,
            "context": self.delegate_block.get("context", {})
        }

        # Delegate: analysis agent performs the security assessment
        from implementations import create_agent
        analyzer = create_agent(sub_agent_role)
        handback = analyzer.execute(delegate)

        # Parse sub-agent's HANDBACK
        return {
            "issues_found": handback.get("issues_found", 0),
            "severity": handback.get("severity", "PASS"),
            "recommendations": handback.get("recommendations", []),
            "confidence": handback.get("confidence", 0.75)
        }
"""
