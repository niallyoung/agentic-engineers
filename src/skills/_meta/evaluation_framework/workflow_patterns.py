"""
Workflow Pattern Definitions for End-to-End Testing

Defines 5 core workflow patterns with objectives, success criteria, and metrics collection:
1. SIMPLE: Single task execution (baseline)
2. ESCALATION: Multi-tier agent escalation chain
3. PARALLEL: Concurrent independent tasks
4. CHAINED: Sequential task dependencies
5. ERROR_RECOVERY: Error handling and recovery paths

Each pattern includes:
- Name and description
- Objectives to measure
- Success criteria (pass/fail conditions)
- Expected metrics ranges
- Anomaly detection thresholds
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import time


class WorkflowPattern(Enum):
    """Enumeration of workflow patterns."""
    SIMPLE = "simple"
    ESCALATION = "escalation"
    PARALLEL = "parallel"
    CHAINED = "chained"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class MetricsBaseline:
    """Baseline metrics for anomaly detection."""
    median_latency_ms: int
    median_cost_usd: float
    median_success_rate: float = 95.0
    latency_spike_multiplier: float = 2.0  # >2x = anomaly
    cost_spike_multiplier: float = 2.0     # >2x = anomaly
    min_success_rate: float = 95.0          # <95% = anomaly


@dataclass
class WorkflowDefinition:
    """Complete workflow pattern definition."""
    pattern: WorkflowPattern
    name: str
    description: str
    objectives: List[str]
    success_criteria: List[str]
    failure_scenarios: List[str] = field(default_factory=list)
    expected_latency_ms_range: tuple = (1000, 10000)  # (min, max)
    expected_cost_usd_range: tuple = (0.01, 0.50)     # (min, max)
    expected_success_rate: float = 95.0
    
    # Metrics to track
    metric_keys: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default metric keys if not provided."""
        if not self.metric_keys:
            self.metric_keys = [
                "total_latency_ms",
                "per_task_cost_usd",
                "success_rate",
                "token_count",
                "error_count",
                "escalation_count",
            ]


# ============================================================================
# WORKFLOW PATTERN DEFINITIONS
# ============================================================================

WORKFLOW_SIMPLE = WorkflowDefinition(
    pattern=WorkflowPattern.SIMPLE,
    name="Simple Task Execution",
    description="Single task routed to appropriate agent and executed without escalation.",
    objectives=[
        "Validate basic task routing decision tree",
        "Measure baseline latency and cost for single execution",
        "Verify task completion without errors",
    ],
    success_criteria=[
        "SC1: Task routed to correct agent tier (Engineer for simple tasks)",
        "SC2: Task completes with status=COMPLETE",
        "SC3: Latency within expected range (1-5 seconds)",
        "SC4: Cost within expected range ($0.01-0.10)",
        "SC5: Success rate ≥95% across all harness/model combinations",
    ],
    failure_scenarios=[
        "Task routed to wrong agent tier",
        "Task times out after 10 seconds",
        "Task fails with non-recoverable error",
        "Output validation fails (expected text not found)",
    ],
    expected_latency_ms_range=(1000, 5000),
    expected_cost_usd_range=(0.01, 0.10),
    expected_success_rate=95.0,
)

WORKFLOW_ESCALATION = WorkflowDefinition(
    pattern=WorkflowPattern.ESCALATION,
    name="Escalation Chain (Engineer → Senior → Lead)",
    description="Task escalates through multiple agent tiers when prerequisites are met.",
    objectives=[
        "Validate escalation triggers and routing rules",
        "Verify task completion after escalation",
        "Measure cost increase from multi-tier execution",
        "Track escalation decision rationale",
    ],
    success_criteria=[
        "SC1: Initial routing to Engineer tier",
        "SC2: Escalation triggered after max attempts or complexity detection",
        "SC3: Task successfully routed to Senior Engineer",
        "SC4: Task completed by appropriate tier (Senior or Lead)",
        "SC5: Total cost reflects multi-tier execution (<$0.50)",
        "SC6: Success rate ≥90% (lower than simple due to complexity)",
    ],
    failure_scenarios=[
        "Escalation not triggered when needed",
        "Incorrect escalation target tier",
        "Senior Engineer unable to complete, no further escalation",
        "Lead Engineer decision not returned",
    ],
    expected_latency_ms_range=(3000, 15000),
    expected_cost_usd_range=(0.05, 0.50),
    expected_success_rate=90.0,
)

WORKFLOW_PARALLEL = WorkflowDefinition(
    pattern=WorkflowPattern.PARALLEL,
    name="Parallel Task Execution",
    description="Multiple independent tasks executed concurrently by different agents.",
    objectives=[
        "Validate parallel task orchestration",
        "Measure wall-clock latency vs sequential sum",
        "Verify all parallel tasks complete successfully",
        "Track resource utilization across concurrent tasks",
    ],
    success_criteria=[
        "SC1: All 5 parallel tasks routed simultaneously",
        "SC2: All tasks complete with status=COMPLETE",
        "SC3: Wall-clock latency <2x single task latency",
        "SC4: No task starvation or deadlock",
        "SC5: Total cost ≤ sum of sequential costs + 10%",
        "SC6: Success rate ≥95% (all parallel tasks must succeed)",
    ],
    failure_scenarios=[
        "Tasks not executed in parallel",
        "One parallel task blocks others",
        "Task deadlock or resource contention",
        "Partial completion with loss of results",
    ],
    expected_latency_ms_range=(2000, 8000),
    expected_cost_usd_range=(0.05, 0.50),
    expected_success_rate=95.0,
)

WORKFLOW_CHAINED = WorkflowDefinition(
    pattern=WorkflowPattern.CHAINED,
    name="Chained Task Execution (Sequential Dependencies)",
    description="Sequential tasks where output of task N is input to task N+1.",
    objectives=[
        "Validate task dependency handling",
        "Verify data flow between sequential tasks",
        "Measure latency accumulation across chain",
        "Track context preservation across tasks",
    ],
    success_criteria=[
        "SC1: Task 1 completes and output captured",
        "SC2: Task 2 receives Task 1 output as input",
        "SC3: Task 3 receives Task 2 output as input",
        "SC4: Full chain completes in dependency order",
        "SC5: No data loss or corruption between stages",
        "SC6: Success rate ≥92% (lower due to cumulative error risk)",
    ],
    failure_scenarios=[
        "Task dependency not respected (execution out of order)",
        "Output not passed to next task",
        "Data corruption or formatting error in data flow",
        "Task N+1 fails due to unexpected input from task N",
    ],
    expected_latency_ms_range=(5000, 20000),
    expected_cost_usd_range=(0.03, 0.30),
    expected_success_rate=92.0,
)

WORKFLOW_ERROR_RECOVERY = WorkflowDefinition(
    pattern=WorkflowPattern.ERROR_RECOVERY,
    name="Error Handling & Recovery",
    description="Tasks that encounter errors and trigger recovery mechanisms.",
    objectives=[
        "Validate error detection and handling",
        "Verify retry logic and exponential backoff",
        "Measure recovery success rate",
        "Track error classification and escalation",
    ],
    success_criteria=[
        "SC1: Error detected and classified correctly",
        "SC2: Retry triggered automatically (if appropriate)",
        "SC3: Exponential backoff applied correctly",
        "SC4: Max retries respected (no infinite loops)",
        "SC5: Recovery successful or graceful failure",
        "SC6: Success rate ≥85% (intentionally lower for error paths)",
    ],
    failure_scenarios=[
        "Error not detected or ignored",
        "Incorrect error classification",
        "Retry loop exceeds max attempts",
        "Exponential backoff not applied",
        "Recovery attempted but still fails",
    ],
    expected_latency_ms_range=(2000, 25000),
    expected_cost_usd_range=(0.02, 0.50),
    expected_success_rate=85.0,
)


# ============================================================================
# WORKFLOW PATTERN REGISTRY
# ============================================================================

WORKFLOW_PATTERNS: Dict[WorkflowPattern, WorkflowDefinition] = {
    WorkflowPattern.SIMPLE: WORKFLOW_SIMPLE,
    WorkflowPattern.ESCALATION: WORKFLOW_ESCALATION,
    WorkflowPattern.PARALLEL: WORKFLOW_PARALLEL,
    WorkflowPattern.CHAINED: WORKFLOW_CHAINED,
    WorkflowPattern.ERROR_RECOVERY: WORKFLOW_ERROR_RECOVERY,
}

WORKFLOW_PATTERN_NAMES = {
    "simple": WorkflowPattern.SIMPLE,
    "escalation": WorkflowPattern.ESCALATION,
    "parallel": WorkflowPattern.PARALLEL,
    "chained": WorkflowPattern.CHAINED,
    "error-recovery": WorkflowPattern.ERROR_RECOVERY,
    "error_recovery": WorkflowPattern.ERROR_RECOVERY,
}

HARNESSES = ["opencode", "copilot", "claude-code", "pi-dev"]
MODELS = ["haiku", "sonnet", "opus"]


def get_workflow_definition(pattern: str) -> Optional[WorkflowDefinition]:
    """Get workflow definition by name."""
    if isinstance(pattern, WorkflowPattern):
        return WORKFLOW_PATTERNS.get(pattern)
    pattern_enum = WORKFLOW_PATTERN_NAMES.get(pattern.lower())
    if pattern_enum:
        return WORKFLOW_PATTERNS.get(pattern_enum)
    return None


def get_all_workflow_definitions() -> Dict[str, WorkflowDefinition]:
    """Get all workflow definitions as name -> definition mapping."""
    return {
        f.pattern.value: f for f in WORKFLOW_PATTERNS.values()
    }
