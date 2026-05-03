"""
RoutingAgent - Specialist agent for task routing decisions.

Translates AGENTS.md decision tree into routing decisions.
Receives task analysis from Orchestrator and returns routing decision with confidence.

This implements the SEPARATION OF CONCERNS principle by delegating all routing
logic from the Orchestrator to a specialist agent.
"""

from typing import Dict, Optional
from . import Agent, AgentConfig


ROUTING_AGENT_CONFIG = AgentConfig(
    name="Routing Agent",
    model="claude-haiku-4-5",
    effort="low",
    role="routing_agent",
    description="Translate AGENTS.md decision tree to route tasks to appropriate agents"
)


class RoutingAgent(Agent):
    """
    Specialist agent for routing decisions.
    
    Responsibilities:
    1. Receive task analysis from Orchestrator DELEGATE
    2. Apply AGENTS.md decision tree
    3. Return routing decision with confidence score
    4. Provide rationale for routing choice
    
    DELEGATE Contract:
    - task_id: routing-decision-{original_task_id}
    - role: routing_agent
    - scope: Route task to appropriate agent per AGENTS.md
    - context:
        - original_task_id: str
        - task_description: str
        - is_security_scoped: bool
        - is_cross_service: bool
        - complexity: str (low|medium|high)
        - has_plan: bool
        - is_code_review: bool
        - is_precommit_quality_gate: bool
    
    HANDBACK Contract:
    - status: PASS
    - routing_decision:
        - target_agent: str (engineer, senior_engineer, lead_engineer, principal_engineer, security_engineer, quality_engineer)
        - confidence: float (0.70-0.99)
        - rationale: str
        - decision_criteria: dict
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config or ROUTING_AGENT_CONFIG)
    
    def do_work(self) -> Dict:
        """
        Apply AGENTS.md decision tree to task properties.
        
        Decision tree from AGENTS.md (lines 21-42):
        0. Is this a pre-commit quality gate?
           → YES: Quality Engineer (Sonnet) — PRIORITY route
        
        1. Is this security-scoped?
           → YES: Security Engineer (Opus)
        
        2. Is this cross-service?
           → YES: Principal Engineer (Opus)
        
        3. Is this code review/validation?
           → YES: Lead Engineer (Sonnet) or Quality Engineer (Sonnet)
        
        4. Is this complex + unscoped?
           → YES: Senior Engineer (Sonnet)
        
        5. Is this well-scoped + has plan?
           → YES: Engineer (Haiku)
        
        6. Default fallback
           → Engineer (Haiku)
        
        Returns:
            Dict with routing_decision containing target agent, confidence, rationale
        """
        # Extract task properties from context
        context = self.delegate_block.get("context", {})
        
        is_precommit_quality_gate = context.get("is_precommit_quality_gate", False)
        is_security_scoped = context.get("is_security_scoped", False)
        is_cross_service = context.get("is_cross_service", False)
        is_code_review = context.get("is_code_review", False)
        complexity = context.get("complexity", "medium")
        has_plan = context.get("has_plan", False)
        task_description = context.get("task_description", "")
        
        # Apply decision tree
        
        # Decision 0: Pre-commit quality gate (PRIORITY)
        if is_precommit_quality_gate:
            return {
                "routing_decision": {
                    "target_agent": "quality_engineer",
                    "confidence": 0.95,
                    "rationale": "Pre-commit quality gate has priority routing. Routes to Quality Engineer for immediate validation.",
                    "decision_criteria": {
                        "is_precommit_quality_gate": True,
                        "rule_number": 0,
                        "priority": "immediate"
                    }
                }
            }
        
        # Decision 1: Security-scoped tasks
        if is_security_scoped:
            return {
                "routing_decision": {
                    "target_agent": "security_engineer",
                    "confidence": 0.92,
                    "rationale": "Task involves security concerns (authentication, cryptography, data protection, secrets, vulnerabilities). Routes to Security Engineer per AGENTS.md line 25.",
                    "decision_criteria": {
                        "is_security_scoped": True,
                        "rule_number": 1,
                        "complexity": complexity
                    }
                }
            }
        
        # Decision 2: Cross-service / architectural
        if is_cross_service:
            return {
                "routing_decision": {
                    "target_agent": "principal_engineer",
                    "confidence": 0.90,
                    "rationale": "Task affects multiple services or is architectural in nature. Routes to Principal Engineer per AGENTS.md line 28.",
                    "decision_criteria": {
                        "is_cross_service": True,
                        "rule_number": 2,
                        "scope_type": "cross_service"
                    }
                }
            }
        
        # Decision 3: Code review or validation
        if is_code_review:
            # Code review → Lead Engineer (for PR review, audit code)
            # Validation → Quality Engineer (for test quality, spec validation)
            if "validation" in task_description.lower() or "validate" in task_description.lower():
                return {
                    "routing_decision": {
                        "target_agent": "quality_engineer",
                        "confidence": 0.88,
                        "rationale": "Code validation task. Routes to Quality Engineer per AGENTS.md line 32.",
                        "decision_criteria": {
                            "is_code_review": True,
                            "task_type": "validation",
                            "rule_number": 3
                        }
                    }
                }
            else:
                return {
                    "routing_decision": {
                        "target_agent": "lead_engineer",
                        "confidence": 0.88,
                        "rationale": "Code review task. Routes to Lead Engineer per AGENTS.md line 31.",
                        "decision_criteria": {
                            "is_code_review": True,
                            "task_type": "review",
                            "rule_number": 3
                        }
                    }
                }
        
        # Decision 4: Complex + unscoped
        if complexity == "high" and not has_plan:
            return {
                "routing_decision": {
                    "target_agent": "senior_engineer",
                    "confidence": 0.85,
                    "rationale": "Complex task without clear scope or plan. Routes to Senior Engineer to produce plan, which Engineer will execute per AGENTS.md line 35.",
                    "decision_criteria": {
                        "complexity": complexity,
                        "has_plan": False,
                        "rule_number": 4,
                        "workflow": "senior_engineer_plan_then_engineer_execute"
                    }
                }
            }
        
        # Decision 5: Well-scoped with plan
        if has_plan and complexity in ("low", "medium"):
            return {
                "routing_decision": {
                    "target_agent": "engineer",
                    "confidence": 0.90,
                    "rationale": f"Well-scoped task with plan and {complexity} complexity. Routes to Engineer for execution per AGENTS.md line 37.",
                    "decision_criteria": {
                        "complexity": complexity,
                        "has_plan": True,
                        "rule_number": 5,
                        "planning_status": "has_plan"
                    }
                }
            }
        
        # Decision 6: Default fallback
        return {
            "routing_decision": {
                "target_agent": "engineer",
                "confidence": 0.78,
                "rationale": "No specific decision criteria matched. Routes to Engineer as default fallback per AGENTS.md line 41.",
                "decision_criteria": {
                    "complexity": complexity,
                    "has_plan": has_plan,
                    "rule_number": 6,
                    "default": True,
                    "is_security_scoped": is_security_scoped,
                    "is_cross_service": is_cross_service,
                    "is_code_review": is_code_review
                }
            }
        }
