"""
agentic-engineers Agent Framework

All 13 agents for Phase 6 implementation:
- 8 SDLC Agents (Orchestrator, Engineer, Senior Engineer, Lead Engineer, Principal Engineer, Quality Engineer, Model Engineer, Security Engineer)
- 5 Quality Gate Sub-Agents (Security, Testing, Metrics, Healing, Spec Engineer)

This module provides the base class and helper utilities for all agents.
Each agent:
  1. Receives DELEGATE block (task spec)
  2. Executes work
  3. Returns HANDBACK block (results + confidence)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
import yaml
import json

# Import queue enforcement middleware for easy access
from .queue_enforcement_middleware import (
    QueueContext,
    QueueContextManager,
    QueueEnforcementError,
    QueueEnforcingProxy,
    QueueEnforcementLogger,
)


@dataclass
class AgentConfig:
    """Configuration for each agent."""
    name: str
    model: str
    effort: str  # low, medium, high, max
    role: str
    description: str


class Agent(ABC):
    """Base class for all agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.task_id = None
        self.delegate_block = None
        self.handback = {
            "handoff_type": "HANDBACK",
            "task_id": None,
            "timestamp": datetime.now().isoformat(),
            "status": None,  # PASS | ESCALATE
            "severity": None,  # PASS | LOW | MEDIUM | HIGH
        }

    def execute(self, delegate_block: Dict) -> Dict:
        """Execute work from DELEGATE block."""
        self.delegate_block = delegate_block
        self.task_id = delegate_block.get("task_id")
        self.handback["task_id"] = self.task_id

        try:
            # Validate input
            self._validate_input()

            # Do work
            result = self.do_work()

            # Generate HANDBACK
            self.handback["status"] = "PASS"
            self.handback["severity"] = "PASS"
            self.handback.update(result)

        except ValueError as e:
            self.handback["status"] = "ESCALATE"
            self.handback["severity"] = "MEDIUM"
            self.handback["error"] = str(e)
            self.handback["confidence"] = 0.0

        except RuntimeError as e:
            self.handback["status"] = "ESCALATE"
            self.handback["severity"] = "MEDIUM"
            self.handback["error"] = str(e)
            self.handback["confidence"] = 0.3

        return self.handback

    def _validate_input(self):
        """Validate DELEGATE block has required fields."""
        required = ["task_id", "role", "model", "effort", "scope"]
        for field in required:
            if field not in self.delegate_block:
                raise ValueError(f"Missing required field: {field}")

    @abstractmethod
    def do_work(self) -> Dict:
        """Override in subclass. Return dict to merge into HANDBACK."""
        raise NotImplementedError


# Agent Configurations

ORCHESTRATOR_CONFIG = AgentConfig(
    name="General Orchestrator",
    model="claude-haiku-4.5",
    effort="low",
    role="orchestrator",
    description="Route all work to appropriate specialist agents"
)

ENGINEER_CONFIG = AgentConfig(
    name="Engineer",
    model="claude-haiku-4.5",
    effort="high",
    role="engineer",
    description="Execute well-scoped tasks with pre-written plans"
)

SENIOR_ENGINEER_CONFIG = AgentConfig(
    name="Senior Engineer",
    model="claude-sonnet-4.6",
    effort="high",
    role="senior_engineer",
    description="Complex work, writes plans, diagnoses root causes"
)

LEAD_ENGINEER_CONFIG = AgentConfig(
    name="Lead Engineer",
    model="claude-sonnet-4.6",
    effort="high",
    role="lead_engineer",
    description="Code review, architectural guidance, quality decisions"
)

PRINCIPAL_ENGINEER_CONFIG = AgentConfig(
     name="Principal Engineer",
     model="claude-opus-4.6",
     effort="high",
     role="principal_engineer",
     description="Cross-service architecture, complex design decisions"
 )

QUALITY_ENGINEER_CONFIG = AgentConfig(
    name="Quality Engineer",
    model="claude-sonnet-4.6",
    effort="medium",
    role="quality_engineer",
    description="Post-implementation quality gate, code review"
)

MODEL_ENGINEER_CONFIG = AgentConfig(
    name="Model Engineer",
    model="claude-haiku-4.5",
    effort="medium",
    role="model_engineer",
    description="Token analysis, confidence scoring, model recommendations"
)

SECURITY_ENGINEER_CONFIG = AgentConfig(
     name="Security Engineer",
     model="claude-opus-4.8",
     effort="max",
     role="security_engineer",
     description="Security analysis, threat modeling, vulnerability audits"
 )

# Quality Gate Sub-Agents

SECURITY_AGENT_QG_CONFIG = AgentConfig(
     name="Security Agent (QG)",
     model="claude-opus-4.8",
     effort="high",
     role="security_agent",
     description="Scan code for credentials, vulnerabilities, insecure patterns"
 )

TESTING_AGENT_CONFIG = AgentConfig(
    name="Testing Agent",
    model="claude-haiku-4.5",
    effort="medium",
    role="testing_agent",
    description="Parse test output, extract metrics, validate coverage"
)

METRICS_AGENT_CONFIG = AgentConfig(
    name="Metrics Agent",
    model="claude-haiku-4.5",
    effort="medium",
    role="metrics_agent",
    description="Score system health, validate latency/errors/capacity"
)

HEALING_AGENT_CONFIG = AgentConfig(
    name="Healing Agent",
    model="claude-sonnet-4.6",
    effort="medium",
    role="healing_agent",
    description="Identify config issues, apply auto-fixes, verify"
)

SPEC_ENGINEER_CONFIG = AgentConfig(
    name="Spec Engineer",
    model="claude-sonnet-4.6",
    effort="medium",
    role="spec_engineer",
    description="Validate code against specification, detect drift"
)

QUALITY_GATE_ORCHESTRATOR_CONFIG = AgentConfig(
    name="Quality Gate Orchestrator",
    model="claude-sonnet-4.6",
    effort="medium",
    role="quality_gate_orchestrator",
    description="Delegate to 5 QG sub-agents, aggregate, decide PROCEED/ESCALATE"
)

# Phase 5: Pure Orchestrator Refactor

ROUTING_AGENT_CONFIG = AgentConfig(
    name="Routing Agent",
    model="claude-haiku-4.5",
    effort="low",
    role="routing_agent",
    description="Translate AGENTS.md decision tree to route tasks to appropriate agents"
)

DECISION_ENGINE_CONFIG = AgentConfig(
    name="Decision Engine",
    model="claude-sonnet-4.6",
    effort="medium",
    role="decision_engine",
    description="Evaluate HANDBACK against success criteria and decide next action"
)


# Registry of all agents
AGENTS = {
    "orchestrator": ORCHESTRATOR_CONFIG,
    "engineer": ENGINEER_CONFIG,
    "senior_engineer": SENIOR_ENGINEER_CONFIG,
    "lead_engineer": LEAD_ENGINEER_CONFIG,
    "principal_engineer": PRINCIPAL_ENGINEER_CONFIG,
    "quality_engineer": QUALITY_ENGINEER_CONFIG,
    "model_engineer": MODEL_ENGINEER_CONFIG,
    "security_engineer": SECURITY_ENGINEER_CONFIG,
    "security_agent": SECURITY_AGENT_QG_CONFIG,
    "testing_agent": TESTING_AGENT_CONFIG,
    "metrics_agent": METRICS_AGENT_CONFIG,
    "healing_agent": HEALING_AGENT_CONFIG,
    "spec_engineer": SPEC_ENGINEER_CONFIG,
    "quality_gate_orchestrator": QUALITY_GATE_ORCHESTRATOR_CONFIG,
    "routing_agent": ROUTING_AGENT_CONFIG,
    "decision_engine": DECISION_ENGINE_CONFIG,
}


def get_agent_config(role: str) -> Optional[AgentConfig]:
    """Get configuration for an agent by role."""
    return AGENTS.get(role)


def list_agents() -> List[AgentConfig]:
    """List all agents."""
    return list(AGENTS.values())


# Export core classes for easy importing
__all__ = [
    "Agent",
    "AgentConfig",
    "AGENTS",
    "get_agent_config",
    "list_agents",
    "ORCHESTRATOR_CONFIG",
    "ENGINEER_CONFIG",
    "SENIOR_ENGINEER_CONFIG",
    "LEAD_ENGINEER_CONFIG",
    "PRINCIPAL_ENGINEER_CONFIG",
    "QUALITY_ENGINEER_CONFIG",
    "MODEL_ENGINEER_CONFIG",
    "SECURITY_ENGINEER_CONFIG",
    "SECURITY_AGENT_QG_CONFIG",
    "TESTING_AGENT_CONFIG",
    "METRICS_AGENT_CONFIG",
    "HEALING_AGENT_CONFIG",
    "SPEC_ENGINEER_CONFIG",
    "QUALITY_GATE_ORCHESTRATOR_CONFIG",
    "ROUTING_AGENT_CONFIG",
    "DECISION_ENGINE_CONFIG",
    # Queue Enforcement Middleware (Phase 4)
    "QueueContext",
    "QueueContextManager",
    "QueueEnforcementError",
    "QueueEnforcingProxy",
    "QueueEnforcementLogger",
]
