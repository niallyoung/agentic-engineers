"""
Workflow Orchestrator - High-level task execution pipeline

Coordinates complete task flow:
1. Parse raw task description
2. Route via Orchestrator
3. Execute on selected agent
4. Collect Quality Engineer review
5. Record Model Engineer feedback
6. Run Quality Gate
"""

from implementations import create_agent
from artifact_manager import ArtifactManager
from datetime import datetime
from typing import Dict
import hashlib


class WorkflowOrchestrator:
    """Execute complete agentic-engineers workflow."""

    def __init__(self):
        self.artifacts = ArtifactManager()
        self.task_history = []

    def execute_task(self, description: str, scope: str, complexity: str = "medium",
                     has_plan: bool = False, is_security: bool = False) -> Dict:
        """
        Execute a complete task through the agentic-engineers SDLC.

        Args:
            description: Task name/title
            scope: Detailed scope
            complexity: 'low', 'medium', 'high'
            has_plan: True if pre-written plan included
            is_security: True if security-scoped

        Returns:
            Final result dict with routing, execution, QE review, ME feedback, QG decision
        """
        task_id = self._generate_task_id(description)
        print(f"\n🚀 Starting task: {task_id}")

        result = {
            "task_id": task_id,
            "description": description,
            "scope": scope,
            "orchestrator": None,
            "executor": None,
            "quality_engineer": None,
            "model_engineer": None,
            "quality_gate": None,
            "final_status": None
        }

        try:
            # Phase 1: Route via Orchestrator
            result["orchestrator"] = self._orchestrator_phase(
                task_id, description, scope, complexity, has_plan, is_security
            )
            target_agent = result["orchestrator"]["routing_decision"]
            print(f"   ✓ Routed to: {target_agent}")

            # Phase 2: Execute via target agent
            if target_agent in ["engineer", "senior_engineer"]:
                result["executor"] = self._executor_phase(
                    task_id, target_agent, scope
                )
                print(f"   ✓ Executed by: {target_agent}")
            else:
                print(f"   ⚠ Agent {target_agent} not yet executable (stub)")
                result["executor"] = {"status": "STUB", "confidence": 0.0}

            # Phase 3: Quality Engineer review
            result["quality_engineer"] = self._quality_engineer_phase(
                task_id, result["executor"]
            )
            print(f"   ✓ QE Review: {result['quality_engineer'].get('decision', 'N/A')}")

            # Phase 4: Model Engineer feedback
            result["model_engineer"] = self._model_engineer_phase(
                task_id, result["quality_engineer"]
            )
            print(f"   ✓ ME Recommendation: {result['model_engineer'].get('rank_1_model', 'N/A')}")

            # Phase 5: Quality Gate decision
            result["quality_gate"] = self._quality_gate_phase(
                task_id, result["quality_engineer"]
            )
            final_decision = result["quality_gate"].get("decision", "UNKNOWN")
            result["final_status"] = final_decision
            print(f"   ✓ QG Decision: {final_decision}")

            # Store in history
            self.task_history.append({
                "task_id": task_id,
                "description": description,
                "final_status": final_decision,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            result["final_status"] = "ERROR"
            result["error"] = str(e)

        return result

    def _generate_task_id(self, description: str) -> str:
        """Generate task ID: YYYY-MM-DD-{slug}-{hash}"""
        date = datetime.now().strftime("%Y-%m-%d")
        slug = description[:20].lower().replace(" ", "-").replace("_", "-")
        hash_suffix = hashlib.md5(description.encode()).hexdigest()[:6]
        return f"{date}-{slug}-{hash_suffix}"

    def _orchestrator_phase(self, task_id: str, description: str, scope: str,
                           complexity: str, has_plan: bool, is_security: bool) -> Dict:
        """Phase 1: Route task."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": "orchestrator",
            "model": "claude-haiku-4.5",
            "effort": "low",
            "scope": scope,
            "complexity": complexity,
            "has_plan": has_plan,
            "is_security_scoped": is_security
        }

        agent = create_agent("orchestrator")
        result = agent.execute(delegate)

        self.artifacts.write_delegate(task_id, delegate)
        self.artifacts.write_handback(f"{task_id}-orchestrator", result)

        return result

    def _executor_phase(self, task_id: str, executor: str, scope: str) -> Dict:
        """Phase 2: Execute task."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": executor,
            "model": "claude-haiku-4.5" if executor == "engineer" else "claude-sonnet-4.6",
            "effort": "high",
            "scope": scope,
            "plan": [
                "Analyze requirements",
                "Design solution",
                "Implement changes",
                "Validate results"
            ],
            "success_criteria": [
                "All tests pass",
                "Code review approved"
            ]
        }

        agent = create_agent(executor)
        result = agent.execute(delegate)

        self.artifacts.write_delegate(f"{task_id}-{executor}", delegate)
        self.artifacts.write_handback(f"{task_id}-{executor}", result)

        return result

    def _quality_engineer_phase(self, task_id: str, executor_result: Dict) -> Dict:
        """Phase 3: Quality review."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": "quality_engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Post-implementation quality review",
            "quality_score": executor_result.get('quality_score', 90)
        }

        agent = create_agent("quality_engineer")
        result = agent.execute(delegate)

        self.artifacts.write_delegate(f"{task_id}-qe", delegate)
        self.artifacts.write_handback(f"{task_id}-qe", result)

        return result

    def _model_engineer_phase(self, task_id: str, qe_result: Dict) -> Dict:
        """Phase 4: Model recommendations."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": "model_engineer",
            "model": "claude-haiku-4.5",
            "effort": "medium",
            "scope": "Analyze quality and recommend model",
            "quality_score": qe_result.get('quality_score', 90)
        }

        agent = create_agent("model_engineer")
        result = agent.execute(delegate)

        self.artifacts.write_delegate(f"{task_id}-me", delegate)
        self.artifacts.write_handback(f"{task_id}-me", result)

        return result

    def _quality_gate_phase(self, task_id: str, qe_result: Dict) -> Dict:
        """Phase 5: Quality Gate decision."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": "quality_gate_orchestrator",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Run quality gate checks"
        }

        agent = create_agent("quality_gate_orchestrator")
        result = agent.execute(delegate)

        self.artifacts.write_delegate(f"{task_id}-qg", delegate)
        self.artifacts.write_handback(f"{task_id}-qg", result)

        return result

    def summary(self) -> str:
        """Print execution summary."""
        proceed_count = sum(1 for t in self.task_history if t["final_status"] == "PROCEED")
        escalate_count = sum(1 for t in self.task_history if t["final_status"] == "ESCALATE")

        return f"""
╔═══════════════════════════════════════════════════════════════════╗
║  Workflow Summary                                                  ║
╚═══════════════════════════════════════════════════════════════════╝

Tasks Executed:     {len(self.task_history)}
PROCEED:            {proceed_count}
ESCALATE:           {escalate_count}

History:
{chr(10).join(f"  {t['task_id']} → {t['final_status']}" for t in self.task_history[-5:])}
        """


if __name__ == "__main__":
    wf = WorkflowOrchestrator()

    # Example: well-scoped task with plan
    wf.execute_task(
        description="Add timeout grace period",
        scope="Add grace period to authentication service timeout validation",
        complexity="medium",
        has_plan=True,
        is_security=False
    )

    # Example: complex task without plan
    wf.execute_task(
        description="Refactor data storage",
        scope="Redesign data storage partition scheme for better performance",
        complexity="high",
        has_plan=False,
        is_security=False
    )

    print(wf.summary())
