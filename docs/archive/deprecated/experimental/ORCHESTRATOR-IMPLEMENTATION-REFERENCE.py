"""
⚠️ REFERENCE IMPLEMENTATION ONLY — DO NOT INVOKE DIRECTLY

This file is a reference impl for understanding agent structure.
All work MUST flow through agent SKILLS via DELEGATE/HANDBACK protocol.
Do NOT execute this script directly.

General Orchestrator Agent Implementation Reference

Model: claude-haiku-4-5 (low effort)
Role: Route all work to appropriate specialist agents
Invoked: Every work request (from developers or DELEGATE blocks)

ROUTING LOGIC (from AGENTS.md):
  1. Is it security-scoped? → Security Engineer (Opus 4.7)
  2. Is it cross-service architecture? → Principal Engineer (Opus 4.7)
  3. Is it complex coding without pre-written plan? → Senior Engineer (Sonnet 4.6)
  4. Is it code review? → Lead Engineer (Sonnet 4.6)
  5. Is it well-planned, low-medium complexity? → Engineer (Haiku 4.5)
  6. Otherwise → Escalate to human for clarification

FEATURES:
  - Parse incoming work request (or DELEGATE block)
  - Apply Model Engineer recommendations from artifacts/feedback/
  - Generate DELEGATE block with all required fields
  - Delegate work and wait for HANDBACK
  - Handle timeouts (5 min per agent)
  - Track metrics (cost per task, latency, decision accuracy)
  - Stateless (enables horizontal scaling)

"""

import json
import yaml
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class GeneralOrchestrator:
    """Master router for all software engineering work."""

    MODEL = "claude-haiku-4-5"
    EFFORT = "low"

    # Agent routing configuration
    AGENTS = {
        "security_engineer": {
            "model": "claude-opus-4-7",
            "effort": "max",
            "description": "Security analysis, threat modeling, vulnerability audits"
        },
        "principal_engineer": {
            "model": "claude-opus-4-7",
            "effort": "high",
            "description": "Cross-service architecture, complex multi-step planning"
        },
        "senior_engineer": {
            "model": "claude-sonnet-4-6",
            "effort": "high",
            "description": "Complex coding tasks, root cause diagnosis, planning"
        },
        "lead_engineer": {
            "model": "claude-sonnet-4-6",
            "effort": "high",
            "description": "Code review, quality decisions, medium-complexity planning"
        },
        "engineer": {
            "model": "claude-haiku-4-5",
            "effort": "high",
            "description": "Well-scoped tasks with pre-written plan"
        },
        "quality_engineer": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "description": "Post-implementation quality gate, code review, model assessment"
        }
    }

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.artifacts_today = self.artifacts_dir / self.current_date
        self.artifacts_today.mkdir(parents=True, exist_ok=True)

        # Model Engineer recommendations cache
        self.model_recommendations = self._load_model_recommendations()

        # Metrics tracking
        self.metrics = {
            "decisions_made": 0,
            "total_cost": 0.0,
            "routing_accuracy": 0.0
        }

    def route_work(self, work_request: Dict) -> Dict:
        """
        Main routing logic.

        Args:
            work_request: Dictionary with:
                - description: What needs to be done
                - complexity: "low", "medium", "high"
                - scope: "single_file", "multi_file", "cross_service", "architecture"
                - has_plan: boolean
                - is_security_scoped: boolean

        Returns:
            routing_decision: Dictionary with:
                - target_agent: name of agent to delegate to
                - delegate_block: YAML block ready to write to artifacts/
                - rationale: why this agent?
                - confidence: 0.0-1.0
        """

        # Apply Model Engineer recommendation if available
        if "signature" in work_request:
            recommendation = self._apply_model_recommendation(work_request["signature"])
            if recommendation:
                return self._create_routing_decision(
                    agent=recommendation["rank_1_agent"],
                    work_request=work_request,
                    confidence=recommendation["confidence"],
                    rationale="Applied Model Engineer recommendation"
                )

        # Routing decision tree (from AGENTS.md)
        if work_request.get("is_security_scoped"):
            return self._route_to_security_engineer(work_request)

        elif work_request.get("scope") == "cross_service" or \
             work_request.get("scope") == "architecture":
            return self._route_to_principal_engineer(work_request)

        elif work_request.get("complexity") == "high" and not work_request.get("has_plan"):
            return self._route_to_senior_engineer(work_request)

        elif work_request.get("is_code_review"):
            return self._route_to_lead_engineer(work_request)

        elif work_request.get("has_plan") and \
             work_request.get("complexity") in ("low", "medium"):
            return self._route_to_engineer(work_request)

        else:
            # Unclear scope - escalate to human
            return self._escalate_to_human(work_request)

    def _route_to_security_engineer(self, work_request: Dict) -> Dict:
        """Route security-scoped work to Security Engineer (Opus 4.7)."""
        return self._create_routing_decision(
            agent="security_engineer",
            work_request=work_request,
            confidence=0.95,
            rationale="Security-scoped task requires highest expertise (Opus)"
        )

    def _route_to_principal_engineer(self, work_request: Dict) -> Dict:
        """Route cross-service architecture work to Principal Engineer (Opus 4.7)."""
        return self._create_routing_decision(
            agent="principal_engineer",
            work_request=work_request,
            confidence=0.92,
            rationale="Cross-service architecture requires principal-level thinking"
        )

    def _route_to_senior_engineer(self, work_request: Dict) -> Dict:
        """Route complex, unplanned work to Senior Engineer (Sonnet 4.6)."""
        return self._create_routing_decision(
            agent="senior_engineer",
            work_request=work_request,
            confidence=0.88,
            rationale="Complex task without plan; Senior Engineer writes plan first"
        )

    def _route_to_lead_engineer(self, work_request: Dict) -> Dict:
        """Route code review to Lead Engineer (Sonnet 4.6)."""
        return self._create_routing_decision(
            agent="lead_engineer",
            work_request=work_request,
            confidence=0.90,
            rationale="Code review/quality gate requires Lead Engineer expertise"
        )

    def _route_to_engineer(self, work_request: Dict) -> Dict:
        """Route well-scoped, planned work to Engineer (Haiku 4.5)."""
        return self._create_routing_decision(
            agent="engineer",
            work_request=work_request,
            confidence=0.92,
            rationale="Well-scoped task with plan → Haiku is efficient"
        )

    def _escalate_to_human(self, work_request: Dict) -> Dict:
        """Escalate unclear work to human."""
        return {
            "target_agent": "human",
            "delegate_block": None,
            "rationale": f"Unable to route: unclear scope or contradictory requirements. Description: {work_request.get('description')}",
            "confidence": 0.0,
            "action": "ESCALATE_TO_HUMAN"
        }

    def _create_routing_decision(self, agent: str, work_request: Dict,
                                confidence: float, rationale: str) -> Dict:
        """Create complete routing decision with DELEGATE block."""

        task_id = self._generate_task_id(work_request.get("description", "work"))
        agent_config = self.AGENTS[agent]

        # Generate DELEGATE block
        delegate_block = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": agent,
            "model": agent_config["model"],
            "effort": agent_config["effort"],
            "scope": work_request.get("description", ""),
            "context": work_request.get("context", {}),
            "success_criteria": work_request.get("success_criteria", []),
            "plan": work_request.get("plan", None),
            "timestamp": datetime.now().isoformat()
        }

        # Estimate cost
        estimated_cost = self._estimate_cost(agent_config["model"], agent_config["effort"])

        return {
            "target_agent": agent,
            "delegate_block": delegate_block,
            "delegate_block_yaml": yaml.dump(delegate_block, default_flow_style=False),
            "rationale": rationale,
            "confidence": confidence,
            "estimated_cost": estimated_cost,
            "task_id": task_id,
            "action": "DELEGATE"
        }

    def delegate_and_wait(self, routing_decision: Dict, timeout_sec: int = 300) -> Dict:
        """
        Write DELEGATE block and wait for HANDBACK.

        In production, this would:
        1. Write DELEGATE block to artifacts/
        2. Invoke agent via Claude API
        3. Poll artifacts/ for HANDBACK (timeout: 5 min)
        4. Return HANDBACK or escalate if timeout

        For Phase 6, this is a stub.
        """

        task_id = routing_decision["task_id"]

        # Write DELEGATE block to artifacts/
        delegate_filename = f"DELEGATE-{datetime.now().isoformat()}-{routing_decision['target_agent']}-{task_id}.yaml"
        delegate_path = self.artifacts_today / delegate_filename

        with open(delegate_path, "w") as f:
            f.write(routing_decision["delegate_block_yaml"])

        print(f"✓ DELEGATE written: {delegate_path}")

        # Wait for HANDBACK (stub - in production, this polls artifacts/)
        print(f"→ Waiting for {routing_decision['target_agent']} to complete (timeout: {timeout_sec}s)...")

        # Stub return (in production would read HANDBACK from artifacts/)
        return {
            "task_id": task_id,
            "status": "PENDING",
            "message": f"In Phase 6 production: would poll artifacts/ for HANDBACK-*-{task_id}.yaml"
        }

    def _apply_model_recommendation(self, task_signature: str) -> Optional[Dict]:
        """Apply Model Engineer recommendation from artifacts/feedback/"""
        if task_signature in self.model_recommendations:
            return self.model_recommendations[task_signature]
        return None

    def _load_model_recommendations(self) -> Dict:
        """Load model recommendations from artifacts/feedback/model-recommendations.jsonl"""
        recommendations = {}
        feedback_dir = self.artifacts_dir / "feedback"

        if not feedback_dir.exists():
            return recommendations

        rec_file = feedback_dir / "model-recommendations.jsonl"
        if rec_file.exists():
            with open(rec_file, "r") as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line)
                        recommendations[rec.get("task_signature")] = rec

        return recommendations

    def _estimate_cost(self, model: str, effort: str) -> float:
        """Estimate cost for task."""
        model_costs = {
            "claude-haiku-4-5": {"low": 0.01, "medium": 0.02, "high": 0.03},
            "claude-sonnet-4-6": {"low": 0.06, "medium": 0.09, "high": 0.15},
            "claude-opus-4-7": {"low": 0.30, "medium": 0.50, "high": 0.75}
        }
        return model_costs.get(model, {}).get(effort, 0.1)

    def _generate_task_id(self, description: str) -> str:
        """Generate unique task_id: YYYY-MM-DD-slug"""
        slug = description[:30].lower().replace(" ", "-")
        return f"{self.current_date}-{slug}-{uuid.uuid4().hex[:8]}"

    def print_routing_decision(self, decision: Dict):
        """Pretty-print routing decision for debugging."""
        print(f"""
╔═══════════════════════════════════════════════════════════╗
║ ROUTING DECISION                                          ║
╚═══════════════════════════════════════════════════════════╝

Task ID:          {decision['task_id']}
Target Agent:     {decision['target_agent']}
Model:            {decision['delegate_block']['model']}
Effort:           {decision['delegate_block']['effort']}
Estimated Cost:   ${decision['estimated_cost']:.4f}
Confidence:       {decision['confidence']:.2f}
Rationale:        {decision['rationale']}

DELEGATE Block (ready to write to artifacts/):

{decision['delegate_block_yaml']}
""")


def example_usage():
    """Example: routing various work requests."""

    orchestrator = GeneralOrchestrator()

    # Example 1: Security-scoped work
    security_work = {
        "description": "Scan code for credentials and vulnerabilities",
        "is_security_scoped": True,
        "complexity": "medium",
        "context": {"file": "lambda/api/main.go"},
    }
    decision = orchestrator.route_work(security_work)
    orchestrator.print_routing_decision(decision)

    # Example 2: Well-scoped, planned work
    planned_work = {
        "description": "Fix auth timeout in {example-service} (30 sec grace period)",
        "complexity": "low",
        "has_plan": True,
        "plan": [
            "1. Add 30s grace period to exp claim check at line 92",
            "2. Write test TestTokenExpiryGracePeriod",
            "3. Run 'make verify'"
        ],
        "success_criteria": ["make verify passes", "Mobile e2e auth passes"]
    }
    decision = orchestrator.route_work(planned_work)
    orchestrator.print_routing_decision(decision)

    # Example 3: Complex work without plan
    complex_work = {
        "description": "Redesign event store for multi-region deployment",
        "complexity": "high",
        "has_plan": False,
        "scope": "architecture",
        "context": {
            "services": ["{example-service}", "{service-name}", "{example-service}"],
            "constraint": "Must maintain immutability, strong consistency"
        }
    }
    decision = orchestrator.route_work(complex_work)
    orchestrator.print_routing_decision(decision)


if __name__ == "__main__":
    example_usage()
