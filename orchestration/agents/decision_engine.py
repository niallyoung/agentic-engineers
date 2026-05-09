"""
DecisionEngine - Specialist agent for post-execution validation decisions.

Evaluates HANDBACK from executed agents against success criteria.
Makes pass/fail/rework decisions on task completion.

This implements the SEPARATION OF CONCERNS principle by delegating all decision
logic from the Orchestrator to a specialist agent.
"""

from typing import Dict, List, Optional, Any
from . import Agent, AgentConfig


DECISION_ENGINE_CONFIG = AgentConfig(
    name="Decision Engine",
    model="claude-sonnet-4-6",
    effort="medium",
    role="decision_engine",
    description="Evaluate HANDBACK against success criteria and decide next action"
)


class DecisionEngine(Agent):
    """
    Specialist agent for post-execution decisions.
    
    Responsibilities:
    1. Receive HANDBACK from executed agent
    2. Evaluate outcomes against success criteria
    3. Make pass/fail/rework decisions
    4. Generate detailed evaluation record
    
    DELEGATE Contract:
    - task_id: decision-{original_task_id}
    - role: decision_engine
    - scope: Evaluate HANDBACK and decide next action
    - context:
        - original_task_id: str
        - original_success_criteria: list[str]
        - agent_status: str (PASS|ESCALATE)
        - quality_score: int (0-100)
        - agent_handback: dict (entire HANDBACK from executed agent)
    
    HANDBACK Contract:
    - status: PASS
    - decision:
        - action: str (proceed|escalate|rework)
        - confidence: float (0.70-0.99)
        - rationale: str
        - evaluation:
            - success_criteria_met: list[dict]
            - quality_score: int
            - blockers: list[str]
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config or DECISION_ENGINE_CONFIG)
    
    def do_work(self) -> Dict:
        """
        Evaluate HANDBACK and make decision on task completion.
        
        Evaluation logic:
        1. Extract success criteria from DELEGATE context
        2. Extract HANDBACK from executed agent
        3. Evaluate each criterion against HANDBACK
        4. Calculate quality score
        5. Determine action:
           - proceed: All criteria met and quality >= 85
           - escalate: Agent escalated or critical failure
           - rework: Quality too low but salvageable (>70)
        
        Returns:
            Dict with decision containing action, confidence, rationale, evaluation
        """
        # Extract context
        context = self.delegate_block.get("context", {})
        original_task_id = context.get("original_task_id", "unknown")
        success_criteria = context.get("original_success_criteria", [])
        agent_status = context.get("agent_status", "UNKNOWN")
        quality_score = context.get("quality_score", 0)
        agent_handback = context.get("agent_handback", {})
        
        # Evaluate criteria
        criteria_results = self._evaluate_criteria(success_criteria, agent_handback)
        all_passed = all(r["passed"] for r in criteria_results)
        
        # Determine action
        decision = self._make_decision(
            agent_status=agent_status,
            criteria_results=criteria_results,
            quality_score=quality_score,
            all_passed=all_passed
        )
        
        return {
            "decision": {
                "action": decision["action"],
                "confidence": decision["confidence"],
                "rationale": decision["rationale"],
                "evaluation": {
                    "success_criteria_met": criteria_results,
                    "quality_score": quality_score,
                    "blockers": decision.get("blockers", []),
                    "all_criteria_passed": all_passed
                }
            }
        }
    
    def _evaluate_criteria(self, criteria: List[str], handback: Dict) -> List[Dict]:
        """
        Evaluate each success criterion against HANDBACK.
        
        Args:
            criteria: List of success criteria from task DELEGATE
            handback: HANDBACK dict from executed agent
        
        Returns:
            List of evaluation dicts with structure:
            {
                "criterion": str,
                "passed": bool,
                "evidence": str,
                "severity": str (critical|high|medium|low)
            }
        """
        results = []
        
        for criterion in criteria:
            # Try to find evidence of criterion in HANDBACK
            criterion_lower = criterion.lower()
            
            passed = self._criterion_met(criterion_lower, handback)
            severity = self._evaluate_severity(criterion_lower, passed)
            evidence = self._find_evidence(criterion_lower, handback)
            
            results.append({
                "criterion": criterion,
                "passed": passed,
                "evidence": evidence,
                "severity": severity
            })
        
        return results
    
    def _criterion_met(self, criterion: str, handback: Dict) -> bool:
        """
        Determine if a criterion is met based on HANDBACK.
        
        Uses heuristics:
        - "test" in criterion → check for test_results or tests_passed
        - "security" in criterion → check for security_score or no vulnerabilities
        - "quality" in criterion → check for quality_score >= 80
        - "deploy" in criterion → check for deployment_status or deployed=true
        - "modified" / "changed" → check for modifications or files_changed
        - "error" / "no errors" / "passing" → check for errors or failures
        - "not" in criterion → negate the check
        """
        # Check handback status first
        if handback.get("status") == "ESCALATE":
            return False
        
        # Check for common criteria patterns
        if "test" in criterion:
            return (
                handback.get("tests_passed", False) or
                handback.get("test_results", {}).get("all_passed", False) or
                handback.get("test_coverage", 0) >= 80 or
                "test" in str(handback.get("deliverables", "")).lower()
            )
        
        if "security" in criterion or "vulnerability" in criterion:
            if "no vulnerabilities" in criterion or "no security" in criterion:
                return (
                    handback.get("security_score", 0) >= 85 or
                    handback.get("vulnerabilities_found", 1) == 0
                )
            return handback.get("security_score", 0) >= 75
        
        if "quality" in criterion:
            quality_threshold = 80 if "high" in criterion else 70
            return handback.get("quality_score", 0) >= quality_threshold
        
        if "deploy" in criterion or "deployed" in criterion or "merge" in criterion:
            return (
                handback.get("deployment_status") == "deployed" or
                handback.get("deployed", False) or
                handback.get("merged", False)
            )
        
        if "modified" in criterion or "changed" in criterion or "file" in criterion:
            return (
                bool(handback.get("files_modified", [])) or
                bool(handback.get("modifications", [])) or
                "modified" in str(handback.get("deliverables", "")).lower()
            )
        
        if "error" in criterion or "fail" in criterion:
            if "no error" in criterion or "no fail" in criterion or "no failure" in criterion:
                return (
                    handback.get("error_count", 0) == 0 or
                    handback.get("failure_count", 0) == 0
                )
            return False
        
        if "passing" in criterion or "pass" in criterion:
            return handback.get("status") == "PASS"
        
        # Default: check if criterion text appears in handback deliverables
        deliverables = str(handback.get("deliverables", "")).lower()
        return criterion in deliverables
    
    def _evaluate_severity(self, criterion: str, passed: bool) -> str:
        """Evaluate severity of a failed criterion."""
        if passed:
            return "pass"
        
        # Critical failures
        if "security" in criterion or "vulnerab" in criterion:
            return "critical"
        if "auth" in criterion or "encrypt" in criterion:
            return "critical"
        
        # High severity
        if "test" in criterion or "coverage" in criterion:
            return "high"
        if "deploy" in criterion or "merge" in criterion:
            return "high"
        
        # Medium severity
        if "quality" in criterion:
            return "medium"
        if "document" in criterion or "comment" in criterion:
            return "medium"
        
        # Low severity
        return "low"
    
    def _find_evidence(self, criterion: str, handback: Dict) -> str:
        """Find supporting evidence in HANDBACK for a criterion."""
        # Look for relevant fields
        for key in ["quality_score", "test_coverage", "security_score", "deliverables"]:
            if key in handback:
                return f"{key}: {handback[key]}"
        
        # Fall back to status
        return f"status: {handback.get('status', 'UNKNOWN')}"
    
    def _make_decision(
        self,
        agent_status: str,
        criteria_results: List[Dict],
        quality_score: int,
        all_passed: bool
    ) -> Dict:
        """
        Make final decision based on evaluation.
        
        Returns:
            Dict with:
            - action: str (proceed|escalate|rework)
            - confidence: float (0.70-0.99)
            - rationale: str
            - blockers: list[str] (if any)
        """
        
        # Check for escalation
        if agent_status == "ESCALATE":
            return {
                "action": "escalate",
                "confidence": 0.95,
                "rationale": "Agent escalated the task. Requires human review.",
                "blockers": ["Agent escalation requested"]
            }
        
        # Check for critical failures
        critical_failures = [r for r in criteria_results if r["severity"] == "critical" and not r["passed"]]
        if critical_failures:
            blockers = [f"{r['criterion']}" for r in critical_failures]
            return {
                "action": "escalate",
                "confidence": 0.92,
                "rationale": f"Critical criteria not met: {', '.join(blockers)}. Task requires escalation.",
                "blockers": blockers
            }
        
        # Check quality score
        if quality_score >= 85 and all_passed:
            return {
                "action": "proceed",
                "confidence": 0.96,
                "rationale": f"All success criteria met. Quality score {quality_score} exceeds threshold. Task is ready to proceed.",
                "blockers": []
            }
        
        if quality_score >= 80 and all_passed:
            return {
                "action": "proceed",
                "confidence": 0.90,
                "rationale": f"All success criteria met. Quality score {quality_score} meets threshold. Task is ready to proceed.",
                "blockers": []
            }
        
        if quality_score >= 70:
            # Salvageable — send back for rework
            failed_criteria = [r for r in criteria_results if not r["passed"]]
            blockers = [f"{r['criterion']}: {r.get('evidence', 'missing')}" for r in failed_criteria]
            return {
                "action": "rework",
                "confidence": 0.85,
                "rationale": f"Quality score {quality_score} is acceptable but {len(failed_criteria)} criteria not fully met. Recommend rework.",
                "blockers": blockers
            }
        
        # Below minimum threshold
        failed_criteria = [r for r in criteria_results if not r["passed"]]
        blockers = [f"{r['criterion']}: {r.get('evidence', 'missing')}" for r in failed_criteria]
        return {
            "action": "escalate",
            "confidence": 0.88,
            "rationale": f"Quality score {quality_score} below threshold. {len(failed_criteria)} criteria failed. Escalating for review.",
            "blockers": blockers
        }
