"""
End-to-End Example - Complete Task Execution Through agentic-engineers

Demonstrates a single task flowing through:
1. Orchestrator (routing decision)
2. Engineer (execution)
3. Quality Engineer (post-implementation review)
4. Model Engineer (confidence + recommendations)
5. Quality Gate Orchestrator (parallel sub-agents + decision)
"""

from implementations import create_agent
from artifact_manager import ArtifactManager
from datetime import datetime
import hashlib


def generate_task_id(description: str) -> str:
    """Generate task ID: YYYY-MM-DD-{slug}-{hash}"""
    date = datetime.now().strftime("%Y-%m-%d")
    slug = description[:20].lower().replace(" ", "-").replace("_", "-")
    hash_suffix = hashlib.md5(description.encode()).hexdigest()[:6]
    return f"{date}-{slug}-{hash_suffix}"


def run_example():
    """Execute complete example: well-scoped task through full pipeline."""

    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  End-to-End Example: agentic-engineers SDLC + Quality Gate       ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Setup
    artifacts = ArtifactManager()

    # ============ Phase 1: Orchestrator Routes Task ============
    print("\n[1] ORCHESTRATOR: Route incoming task")
    print("-" * 70)

    task_description = "Add timeout grace period to authentication service"
    task_id = generate_task_id(task_description)
    print(f"Task ID: {task_id}")

    # Create DELEGATE block for Orchestrator
    incoming_task = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "orchestrator",
        "model": "claude-haiku-4-5",
        "effort": "low",
        "scope": task_description,
        "complexity": "medium",
        "has_plan": True,
        "is_security_scoped": False
    }

    # Execute Orchestrator
    orchestrator = create_agent("orchestrator")
    orchestrator_result = orchestrator.execute(incoming_task)

    print(f"Status: {orchestrator_result['status']}")
    print(f"Routing: {orchestrator_result['routing_decision']}")
    print(f"Confidence: {orchestrator_result['confidence']}")

    artifacts.write_delegate(task_id, incoming_task)
    artifacts.write_handback(f"{task_id}-orchestrator", orchestrator_result)

    # ============ Phase 2: Engineer Executes Plan ============
    print("\n[2] ENGINEER: Execute well-scoped task with plan")
    print("-" * 70)

    # Create DELEGATE for Engineer (from Orchestrator's recommendation)
    engineer_delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "engineer",
        "model": "claude-haiku-4-5",
        "effort": "high",
        "scope": task_description,
        "context": {
            "file": "lambda/api/main.go:92 (expiry check)",
            "error": "Token rejected after 1hr on mobile",
            "root_cause": "clock skew on device"
        },
        "plan": [
            "Add 30s grace period to exp claim check at line 92",
            "Write test TestTokenExpiryGracePeriod",
            "Run 'make verify'"
        ],
        "success_criteria": [
            "make verify passes",
            "Mobile e2e auth passes"
        ]
    }

    engineer = create_agent("engineer")
    engineer_result = engineer.execute(engineer_delegate)

    print(f"Status: {engineer_result['status']}")
    print(f"Quality Score: {engineer_result.get('quality_score', 'N/A')}%")
    print(f"Deliverables: {engineer_result.get('deliverables', [])}")
    print(f"Confidence: {engineer_result['confidence']}")

    artifacts.write_delegate(f"{task_id}-engineer", engineer_delegate)
    artifacts.write_handback(f"{task_id}-engineer", engineer_result)

    # ============ Phase 3: Quality Engineer Reviews ============
    print("\n[3] QUALITY ENGINEER: Post-implementation review")
    print("-" * 70)

    qe_delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "quality_engineer",
        "model": "claude-sonnet-4-6",
        "effort": "medium",
        "scope": f"Review: {task_description}",
        "quality_score": engineer_result.get('quality_score', 90)
    }

    qe = create_agent("quality_engineer")
    qe_result = qe.execute(qe_delegate)

    print(f"Status: {qe_result['status']}")
    print(f"Quality Score: {qe_result.get('quality_score', 'N/A')}")
    print(f"Model Assessment: {qe_result.get('model_assessment', 'N/A')}")
    print(f"Decision: {qe_result.get('decision', 'N/A')}")

    artifacts.write_delegate(f"{task_id}-qe", qe_delegate)
    artifacts.write_handback(f"{task_id}-qe", qe_result)

    # ============ Phase 4: Model Engineer Recommends ============
    print("\n[4] MODEL ENGINEER: Confidence scoring & recommendations")
    print("-" * 70)

    me_delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "model_engineer",
        "model": "claude-haiku-4-5",
        "effort": "medium",
        "scope": "Analyze quality and recommend model for next similar task",
        "quality_score": qe_result.get('quality_score', 90)
    }

    me = create_agent("model_engineer")
    me_result = me.execute(me_delegate)

    print(f"Status: {me_result['status']}")
    print(f"Confidence: {me_result.get('confidence', 'N/A')}")
    print(f"Rank 1 Model: {me_result.get('rank_1_model', 'N/A')}")
    print(f"Recommendation: {me_result.get('recommendation', 'N/A')}")

    artifacts.write_delegate(f"{task_id}-me", me_delegate)
    artifacts.write_handback(f"{task_id}-me", me_result)

    # ============ Phase 5: Quality Gate (Parallel Sub-Agents) ============
    print("\n[5] QUALITY GATE: Run 5 parallel sub-agents")
    print("-" * 70)

    qg_delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "quality_gate_orchestrator",
        "model": "claude-sonnet-4-6",
        "effort": "medium",
        "scope": f"Quality gate: {task_description}"
    }

    qg_orch = create_agent("quality_gate_orchestrator")
    qg_result = qg_orch.execute(qg_delegate)

    print(f"Status: {qg_result['status']}")
    print(f"Decision: {qg_result['decision']}")
    print(f"Agents Passed: {qg_result.get('agents_passed', 0)}")
    print(f"Agents Escalated: {qg_result.get('agents_escalated', 0)}")
    print(f"Confidence: {qg_result.get('confidence', 'N/A')}")

    artifacts.write_delegate(f"{task_id}-qg", qg_delegate)
    artifacts.write_handback(f"{task_id}-qg", qg_result)

    # ============ Summary ============
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  EXECUTION COMPLETE                                               ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    print(f"\n✅ Task: {task_description}")
    print(f"   Task ID: {task_id}")
    print(f"\n📊 Results:")
    print(f"   Orchestrator → {orchestrator_result['routing_decision']}")
    print(f"   Engineer Quality: {engineer_result.get('quality_score', 'N/A')}%")
    print(f"   QE Assessment: {qe_result.get('decision', 'N/A')}")
    print(f"   Model Recommendation: {me_result.get('rank_1_model', 'N/A')}")
    print(f"   QG Decision: {qg_result['decision']}")

    print(f"\n📁 Artifacts written to:")
    date = datetime.now().strftime("%Y-%m-%d")
    artifacts_list = artifacts.list_artifacts(date)
    print(f"   Delegates: {len(artifacts_list['delegates'])}")
    print(f"   Handbacks: {len(artifacts_list['handbacks'])}")

    print(f"\n✅ Full export: artifacts.export_json('{task_id}')")


if __name__ == "__main__":
    run_example()
