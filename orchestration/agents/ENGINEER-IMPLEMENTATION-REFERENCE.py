"""
Engineer Agent Implementation Reference

Model: claude-haiku-4-5 (high effort)
Role: Execute well-scoped tasks with pre-written plans
Invoked: By Orchestrator when task is low-medium complexity + has clear plan

CONSTRAINTS:
  - MUST have pre-written plan (reject if missing)
  - MUST have clear success criteria
  - Executes step-by-step
  - Validates each step
  - Returns HANDBACK with deliverables + quality_score

FEATURES:
  - Validates DELEGATE input (plan required)
  - Executes plan sequentially
  - Produces observable deliverables
  - Measures quality (% success criteria met)
  - Tracks token usage for Model Engineer feedback
  - Returns confidence score

"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TaskResult:
    """Result of executing a single task."""
    step_number: int
    step_description: str
    status: str  # SUCCESS, FAILURE, PARTIAL
    deliverables: List[str]
    error: Optional[str] = None
    time_taken_sec: float = 0.0


class EngineerAgent:
    """Execute well-scoped tasks with pre-written plans."""

    MODEL = "claude-haiku-4-5"
    EFFORT = "high"

    def __init__(self):
        self.task_id = None
        self.delegate_block = None
        self.results = []
        self.handback = {
            "handoff_type": "HANDBACK",
            "task_id": None,
            "timestamp": datetime.now().isoformat(),
            "status": None,  # PASS or ESCALATE
            "severity": None,  # PASS, LOW, MEDIUM, HIGH
        }

    def execute(self, delegate_block: Dict) -> Dict:
        """
        Main execution method.

        Args:
            delegate_block: DELEGATE YAML parsed as dict

        Returns:
            handback_block: Complete HANDBACK dict, ready to write to artifacts/
        """

        self.delegate_block = delegate_block
        self.task_id = delegate_block.get("task_id")
        self.handback["task_id"] = self.task_id

        try:
            # 1. Validate DELEGATE input
            self._validate_input()

            # 2. Extract plan and success criteria
            plan = delegate_block.get("plan", [])
            success_criteria = delegate_block.get("success_criteria", [])

            # 3. Execute plan
            all_deliverables = []
            for i, step in enumerate(plan, start=1):
                result = self._execute_step(i, step)
                self.results.append(result)

                if result.status == "FAILURE":
                    # Stop on failure
                    raise RuntimeError(f"Step {i} failed: {result.error}")

                all_deliverables.extend(result.deliverables)

            # 4. Validate success criteria
            criteria_results = self._validate_success_criteria(success_criteria)
            criteria_passed = sum(1 for c in criteria_results if c["result"])
            criteria_total = len(criteria_results)

            # 5. Calculate quality score
            quality_score = (criteria_passed / criteria_total * 100) if criteria_total > 0 else 0

            # 6. Generate HANDBACK
            self.handback["status"] = "PASS"
            self.handback["severity"] = "PASS"
            self.handback["deliverables"] = all_deliverables
            self.handback["execution_steps"] = [
                {
                    "step": r.step_number,
                    "description": r.step_description,
                    "status": r.status,
                    "deliverables": r.deliverables,
                    "time_taken_sec": r.time_taken_sec
                }
                for r in self.results
            ]
            self.handback["success_criteria_results"] = criteria_results
            self.handback["quality_score"] = quality_score
            self.handback["token_metrics"] = {
                "input_tokens": self._estimate_input_tokens(),
                "output_tokens": self._estimate_output_tokens(),
                "total_tokens": self._estimate_total_tokens()
            }
            self.handback["confidence"] = self._calculate_confidence(quality_score)

        except ValueError as e:
            # Validation error - reject with message
            self.handback["status"] = "ESCALATE"
            self.handback["severity"] = "MEDIUM"
            self.handback["error"] = str(e)
            self.handback["recommendation"] = f"Fix DELEGATE block: {str(e)}"
            self.handback["confidence"] = 0.0

        except RuntimeError as e:
            # Execution error - escalate
            self.handback["status"] = "ESCALATE"
            self.handback["severity"] = "MEDIUM"
            self.handback["error"] = str(e)
            self.handback["recommendation"] = "Review error details above; consider alternative approach"
            self.handback["confidence"] = 0.3
            self.handback["execution_steps"] = [asdict(r) for r in self.results]

        return self.handback

    def _validate_input(self):
        """Validate DELEGATE block has required fields."""

        required_fields = ["task_id", "role", "model", "effort", "scope", "plan", "success_criteria"]
        for field in required_fields:
            if field not in self.delegate_block:
                raise ValueError(f"DELEGATE missing required field: {field}")

        # Validate plan is not empty
        plan = self.delegate_block.get("plan", [])
        if not plan or len(plan) == 0:
            raise ValueError("DELEGATE 'plan' must be non-empty list of steps")

        # Validate success criteria is not empty
        criteria = self.delegate_block.get("success_criteria", [])
        if not criteria or len(criteria) == 0:
            raise ValueError("DELEGATE 'success_criteria' must be non-empty list")

    def _execute_step(self, step_number: int, step_description: str) -> TaskResult:
        """
        Execute a single step of the plan.

        In production, this would actually execute the step (run code, write file, etc.).
        For Phase 6 stub, this is simulated.
        """

        print(f"  Step {step_number}: {step_description}")

        # Stub: simulate execution
        # In production: actually execute the step, capture output
        deliverables = [f"Completed: {step_description[:50]}"]

        return TaskResult(
            step_number=step_number,
            step_description=step_description,
            status="SUCCESS",
            deliverables=deliverables,
            time_taken_sec=2.5
        )

    def _validate_success_criteria(self, criteria: List[str]) -> List[Dict]:
        """
        Validate success criteria.

        In production, this would actually test each criterion.
        For Phase 6 stub, all criteria pass.
        """

        results = []
        for criterion in criteria:
            results.append({
                "criterion": criterion,
                "result": True,  # Stub: all pass
                "evidence": f"Validated: {criterion}"
            })
        return results

    def _calculate_confidence(self, quality_score: float) -> float:
        """Calculate confidence based on quality score."""
        # 100% quality → 0.95 confidence
        # 80% quality → 0.75 confidence
        # 60% quality → 0.50 confidence
        # <60% → 0.30 confidence
        return max(0.30, min(1.0, 0.30 + (quality_score / 100.0) * 0.65))

    def _estimate_input_tokens(self) -> int:
        """Estimate input tokens used (DELEGATE block size)."""
        # Rough estimate: 250 tokens per KB
        block_str = yaml.dump(self.delegate_block)
        return max(100, int(len(block_str) / 4))

    def _estimate_output_tokens(self) -> int:
        """Estimate output tokens (HANDBACK block size)."""
        # Rough estimate: 250 tokens per KB
        handback_str = yaml.dump(self.handback)
        return max(200, int(len(handback_str) / 4))

    def _estimate_total_tokens(self) -> int:
        """Total tokens: input + output."""
        return self._estimate_input_tokens() + self._estimate_output_tokens()

    def print_handback(self):
        """Pretty-print HANDBACK block for debugging."""
        print(f"""
╔═══════════════════════════════════════════════════════════╗
║ HANDBACK BLOCK (Engineer Agent)                           ║
╚═══════════════════════════════════════════════════════════╝

Task ID:          {self.handback['task_id']}
Status:           {self.handback['status']}
Severity:         {self.handback['severity']}
Quality Score:    {self.handback.get('quality_score', 'N/A')}%
Confidence:       {self.handback.get('confidence', 'N/A')}
Token Usage:      {self.handback.get('token_metrics', {}).get('total_tokens', 'N/A')}

Execution Steps:  {len(self.handback.get('execution_steps', []))}
Success Criteria: {len(self.handback.get('success_criteria_results', []))} checked

HANDBACK YAML:

{yaml.dump(self.handback, default_flow_style=False)}
""")


def example_usage():
    """Example: executing a well-scoped task."""

    # Create a DELEGATE block (from Orchestrator)
    delegate_block = {
        "handoff_type": "DELEGATE",
        "task_id": "2026-04-29-timeout-grace-period-abc123",
        "role": "engineer",
        "model": "claude-haiku-4-5",
        "effort": "high",
        "scope": "Add timeout grace period to authentication service validation",
        "context": {
            "component": "Token validation layer",
            "issue": "Tokens rejected after expiry period on mobile clients",
            "root_cause": "Clock synchronization differences between client and server"
        },
        "plan": [
            "Add 30s grace period to timeout validation logic",
            "Write test for grace period behavior",
            "Run full test suite"
        ],
        "success_criteria": [
            "All tests pass",
            "Mobile client tests pass"
        ]
    }

    # Execute
    engineer = EngineerAgent()
    handback = engineer.execute(delegate_block)

    # Print results
    engineer.print_handback()

    # Return status
    if handback["status"] == "PASS":
        print("✅ Task completed successfully")
    else:
        print(f"❌ Task escalated: {handback.get('error', 'unknown error')}")


if __name__ == "__main__":
    example_usage()
