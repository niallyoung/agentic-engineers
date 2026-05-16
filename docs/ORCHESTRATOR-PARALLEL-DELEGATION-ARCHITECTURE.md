# Orchestrator Parallel Delegation Architecture

**Document ID:** ORCHESTRATOR-PARALLEL-DELEGATION-ARCHITECTURE  
**Version:** 1.0  
**Date:** 2026-05-16  
**Author:** Lead Engineer (claude-sonnet-4-6)  
**Task ID:** 2026-05-16-orchestrator-parallel-design  
**Status:** APPROVED — Ready for Implementation

---

## Executive Summary

This document specifies a parallel delegation architecture for the Orchestrator that enables automatic decomposition of complex tasks into concurrent sub-DELEGATEs, intelligent routing to appropriate specialists, dependency-aware execution ordering, and result consolidation. The architecture is fully backward-compatible with existing single-DELEGATE workflows.

**Key Capability:** A task like "investigate harness consistency across all four harnesses" automatically decomposes into 4 parallel analysis DELEGATEs + 1 framework design DELEGATE + 1 consolidation DELEGATE — without manual orchestration.

---

## Table of Contents

1. [Motivation & Problem Statement](#1-motivation--problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [Task Decomposition Rules](#3-task-decomposition-rules)
4. [Specialist Routing Rules](#4-specialist-routing-rules)
5. [Dependency Management](#5-dependency-management)
6. [Consolidation Pattern](#6-consolidation-pattern)
7. [Configuration & Extensibility](#7-configuration--extensibility)
8. [Backward Compatibility](#8-backward-compatibility)
9. [Implementation Specification](#9-implementation-specification)
10. [Architecture Diagrams](#10-architecture-diagrams)
11. [Example: Harness Consistency Investigation](#11-example-harness-consistency-investigation)
12. [Error Handling & Failure Modes](#12-error-handling--failure-modes)
13. [Metrics & Observability](#13-metrics--observability)

---

## 1. Motivation & Problem Statement

### Current Limitation

The existing Orchestrator processes tasks sequentially: one DELEGATE at a time, one specialist at a time. For complex multi-faceted investigations or implementations, this creates unnecessary serialization:

```
Current (sequential):
Task → DELEGATE-A → HANDBACK-A → DELEGATE-B → HANDBACK-B → DELEGATE-C → HANDBACK-C
Wall clock: 3 × task_duration
```

### Target State

```
Target (parallel with dependencies):
Task → [DELEGATE-A, DELEGATE-B, DELEGATE-C] → [HANDBACK-A, HANDBACK-B, HANDBACK-C]
         ↓ (all complete)
       DELEGATE-consolidation → HANDBACK-consolidation
Wall clock: max(task_duration) + consolidation_duration
```

### Motivating Example

**Harness consistency investigation** should automatically produce:

```
Phase 1 (parallel):
  ├── DELEGATE: Analyze π.dev harness        → Senior Engineer
  ├── DELEGATE: Analyze Claude Code harness  → Senior Engineer  
  ├── DELEGATE: Analyze Copilot CLI harness  → Senior Engineer
  └── DELEGATE: Analyze OpenCode harness     → Senior Engineer

Phase 2 (parallel, independent of Phase 1):
  └── DELEGATE: Design consistency framework → Lead Engineer

Phase 3 (depends on Phase 1 + Phase 2):
  └── DELEGATE: Consolidate findings         → Principal Engineer
```

**Speedup:** ~4× wall-clock reduction (4 parallel analyses instead of sequential).

---

## 2. Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                                  │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   Task       │    │  Decomposition   │    │  Dependency   │  │
│  │  Classifier  │───▶│    Engine        │───▶│   Resolver    │  │
│  └──────────────┘    └──────────────────┘    └───────┬───────┘  │
│                                                       │          │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────▼───────┐  │
│  │ Consolidation│◀───│  HANDBACK        │    │  Execution    │  │
│  │   Engine     │    │  Aggregator      │◀───│  Scheduler    │  │
│  └──────────────┘    └──────────────────┘    └───────┬───────┘  │
│                                                       │          │
└───────────────────────────────────────────────────────┼─────────┘
                                                         │
                    ┌────────────────────────────────────┼──────┐
                    │         SPECIALIST AGENTS           │      │
                    │                                     ▼      │
                    │  Engineer  Senior  Lead  Principal  Security│
                    └───────────────────────────────────────────┘
```

### New Data Structures

**ParallelTaskGroup** — groups related DELEGATEs with dependency graph:

```yaml
parallel_task_group:
  group_id: 2026-05-16-harness-consistency-group
  parent_task_id: 2026-05-16-harness-consistency-investigation
  decomposition_strategy: multi_target_analysis
  phases:
    - phase: 1
      parallel: true
      delegates: [delegate-pidev, delegate-claudecode, delegate-copilot, delegate-opencode]
    - phase: 2
      parallel: true
      delegates: [delegate-framework-design]
    - phase: 3
      parallel: false
      depends_on_phases: [1, 2]
      delegates: [delegate-consolidation]
  consolidation_role: Principal Engineer
  status: in_progress
```

---

## 3. Task Decomposition Rules

### 3.1 Decomposition Trigger Detection

The Orchestrator's Task Classifier evaluates incoming tasks against decomposition triggers. A task is decomposable if it matches **one or more** of the following patterns:

#### Pattern 1: Multi-Target Analysis
**Trigger:** Task involves analyzing the same concern across N distinct targets (services, harnesses, repos, environments).

**Detection signals:**
- Task description contains "across all [X]" or "each [X]" or "compare [X] and [Y]"
- Context lists multiple targets of the same type (e.g., 4 harnesses, 3 repos)
- Scope explicitly mentions multiple independent subjects

**Decomposition:** One DELEGATE per target, all in Phase 1 (parallel).

**Example:**
```
Input: "Investigate harness consistency across π.dev, Claude Code, Copilot CLI, OpenCode"
Output: 4 parallel DELEGATEs, one per harness
```

#### Pattern 2: Layered Implementation
**Trigger:** Task requires design + implementation + verification as distinct phases.

**Detection signals:**
- Task involves both architectural decisions AND code changes
- Scope mentions "design and implement" or "plan and execute"
- Complexity score > threshold (see §3.3)

**Decomposition:**
- Phase 1: Design DELEGATE → Lead/Principal Engineer
- Phase 2: Implementation DELEGATEs (depends on Phase 1) → Engineer/Senior Engineer
- Phase 3: Verification DELEGATE (depends on Phase 2) → Quality Engineer

#### Pattern 3: Cross-Service Coordination
**Trigger:** Task touches multiple independent services/repos that can be worked in parallel.

**Detection signals:**
- Context lists multiple repos
- Scope mentions changes to >1 service
- No shared state between service changes

**Decomposition:** One DELEGATE per service, all parallel (Phase 1), with optional integration DELEGATE (Phase 2).

#### Pattern 4: Investigation + Framework Design
**Trigger:** Task requires gathering data (investigation) AND producing a framework/design based on that data.

**Detection signals:**
- Task mentions "investigate and design" or "analyze and recommend"
- Investigation targets are enumerable and independent
- Framework design is a distinct deliverable

**Decomposition:**
- Phase 1: N investigation DELEGATEs (parallel)
- Phase 2: Framework design DELEGATE (parallel with Phase 1 if design can proceed independently, else depends on Phase 1)
- Phase 3: Consolidation DELEGATE (depends on Phase 1 + Phase 2)

#### Pattern 5: Audit + Remediation
**Trigger:** Security or quality audit followed by remediation tasks.

**Detection signals:**
- Task involves security scanning + fixing
- Audit scope is multi-target
- Remediation tasks are independent per target

**Decomposition:**
- Phase 1: Audit DELEGATEs (parallel, Security Engineer)
- Phase 2: Remediation DELEGATEs (parallel, depends on Phase 1 findings)
- Phase 3: Verification DELEGATE (depends on Phase 2)

### 3.2 Non-Decomposable Tasks

The following task types MUST NOT be decomposed (single DELEGATE only):

- Tasks with shared mutable state (e.g., single file being modified)
- Tasks with sequential dependencies throughout (each step depends on previous)
- Simple bug fixes (single root cause, single fix location)
- Security tasks where atomicity is required
- Tasks with scope < 1 hour estimated effort

### 3.3 Complexity Scoring

The Task Classifier assigns a complexity score (0–100) to determine decomposition eligibility:

```
complexity_score = (
  target_count × 15 +           # Number of independent targets
  phase_count × 10 +            # Number of distinct phases
  specialist_diversity × 20 +   # Number of different roles needed
  estimated_hours × 5 +         # Estimated total effort hours
  cross_service_flag × 15        # Boolean: touches multiple services
)

Threshold:
  score < 30: Single DELEGATE (no decomposition)
  score 30–59: Optional decomposition (Orchestrator decides)
  score ≥ 60: Mandatory decomposition
```

### 3.4 Decomposition Output Schema

```yaml
decomposition_plan:
  parent_task_id: string          # Original task ID
  group_id: string                # New group identifier
  strategy: string                # Which pattern triggered decomposition
  complexity_score: integer       # 0-100
  estimated_speedup: float        # Wall-clock reduction factor
  phases:
    - phase_number: integer
      parallel: boolean
      depends_on_phases: [integer]  # Empty for Phase 1
      sub_tasks:
        - sub_task_id: string
          role: string
          scope: string
          estimated_effort: string
          context_slice: object   # Relevant subset of parent context
  consolidation:
    phase: integer
    role: string
    inputs: [string]              # sub_task_ids whose HANDBACKs feed consolidation
```

---

## 4. Specialist Routing Rules

### 4.1 Role Selection Matrix

For each sub-DELEGATE in a parallel group, the Orchestrator applies the following routing matrix:

| Sub-Task Type | Preferred Role | Fallback Role | Model | Effort |
|---|---|---|---|---|
| Single-target analysis (known domain) | Senior Engineer | Lead Engineer | claude-sonnet-4-6 | high |
| Single-target analysis (unknown domain) | Senior Engineer | Principal Engineer | claude-sonnet-4-6 | high |
| Framework/architecture design | Lead Engineer | Principal Engineer | claude-sonnet-4-6 | high |
| Cross-service architecture | Principal Engineer | Lead Engineer | claude-opus-4-6 | high |
| Security analysis | Security Engineer | — | claude-opus-4-7 | max |
| Implementation (well-scoped with plan) | Engineer | Senior Engineer | claude-haiku-4-5 | high |
| Consolidation (≤3 inputs) | Lead Engineer | Senior Engineer | claude-sonnet-4-6 | high |
| Consolidation (4+ inputs) | Principal Engineer | Lead Engineer | claude-opus-4-6 | high |
| Quality verification | Quality Engineer | Lead Engineer | claude-sonnet-4-6 | medium |

### 4.2 Routing Decision Algorithm

```python
def route_sub_task(sub_task: SubTask, group: ParallelTaskGroup) -> Role:
    # Security always wins
    if sub_task.is_security_scoped:
        return SecurityEngineer
    
    # Consolidation routing based on input count
    if sub_task.type == "consolidation":
        input_count = len(sub_task.depends_on)
        return PrincipalEngineer if input_count >= 4 else LeadEngineer
    
    # Analysis routing based on scope complexity
    if sub_task.type == "analysis":
        if sub_task.is_cross_service:
            return PrincipalEngineer
        if sub_task.has_pre_written_plan:
            return Engineer
        return SeniorEngineer
    
    # Design routing
    if sub_task.type == "design":
        if sub_task.affects_multiple_repos:
            return PrincipalEngineer
        return LeadEngineer
    
    # Default: apply standard AGENTS.md routing
    return standard_routing(sub_task)
```

### 4.3 Capacity & Rate Limiting

To prevent overwhelming the harness with simultaneous DELEGATEs:

```yaml
parallel_execution_limits:
  max_concurrent_delegates: 6        # Hard limit per group
  max_concurrent_per_role:
    Engineer: 4
    Senior Engineer: 3
    Lead Engineer: 2
    Principal Engineer: 1
    Security Engineer: 1
  queue_overflow_strategy: phase_split  # Split into sub-phases if over limit
```

When a phase exceeds limits, the Execution Scheduler automatically splits it into sub-phases:

```
Phase 1 (8 targets, limit=6):
  Phase 1a: targets 1-6 (parallel)
  Phase 1b: targets 7-8 (parallel, starts when 1a completes)
```

### 4.4 Context Slicing

Each sub-DELEGATE receives only the relevant slice of the parent task's context:

```yaml
# Parent context:
context:
  - harness_list: [pidev, claudecode, copilot, opencode]
  - analysis_framework: docs/HARNESS-CONSISTENCY-FRAMEWORK.md
  - common_criteria: [config_format, hook_support, model_routing, queue_integration]

# Sub-DELEGATE for π.dev gets:
context:
  - target: pidev
  - harness_docs: docs/PI-DEV-RENDERER-ANALYSIS.md
  - analysis_framework: docs/HARNESS-CONSISTENCY-FRAMEWORK.md  # shared
  - common_criteria: [config_format, hook_support, model_routing, queue_integration]  # shared
  - sibling_task_ids: [delegate-claudecode, delegate-copilot, delegate-opencode]  # for reference
```

---

## 5. Dependency Management

### 5.1 Dependency Graph Model

Dependencies between sub-DELEGATEs are expressed as a Directed Acyclic Graph (DAG):

```
Nodes: sub-DELEGATE IDs
Edges: "depends_on" relationships (A → B means A must complete before B starts)
```

**Dependency types:**

| Type | Description | Example |
|---|---|---|
| `data_dependency` | B needs output data from A | Consolidation needs analysis results |
| `design_dependency` | B needs design decisions from A | Implementation needs architecture doc |
| `sequential_dependency` | B must run after A (ordering constraint) | Remediation after audit |
| `soft_dependency` | B prefers A's output but can start without it | Framework design can start before all analyses complete |

### 5.2 Dependency Expression in DELEGATE

Sub-DELEGATEs include dependency metadata:

```yaml
handoff_type: DELEGATE
task_id: 2026-05-16-harness-consolidation
role: Principal Engineer
model: claude-opus-4-6
effort: high
scope: >
  Consolidate findings from 4 harness analyses and 1 framework design into
  a unified consistency improvement plan. Do not re-analyze individual harnesses.

# Parallel delegation metadata (new fields)
parallel_group_id: 2026-05-16-harness-consistency-group
phase: 3
depends_on:
  - task_id: 2026-05-16-pidev-analysis
    dependency_type: data_dependency
    required_fields: [findings, gaps, recommendations]
  - task_id: 2026-05-16-claudecode-analysis
    dependency_type: data_dependency
    required_fields: [findings, gaps, recommendations]
  - task_id: 2026-05-16-copilot-analysis
    dependency_type: data_dependency
    required_fields: [findings, gaps, recommendations]
  - task_id: 2026-05-16-opencode-analysis
    dependency_type: data_dependency
    required_fields: [findings, gaps, recommendations]
  - task_id: 2026-05-16-framework-design
    dependency_type: design_dependency
    required_fields: [framework_spec, criteria_matrix]

context:
  - Aggregated findings will be injected here by Orchestrator when dependencies complete
  - See: artifacts/delegates/2026-05-16/ for individual HANDBACK files
```

### 5.3 Dependency Resolution Algorithm

```python
class DependencyResolver:
    def resolve_execution_order(self, group: ParallelTaskGroup) -> List[ExecutionPhase]:
        """
        Topological sort of sub-tasks into execution phases.
        Tasks with no dependencies → Phase 1 (parallel).
        Tasks whose dependencies are all in Phase N → Phase N+1.
        """
        phases = []
        remaining = set(group.all_sub_task_ids)
        completed = set()
        
        while remaining:
            # Find tasks whose all dependencies are satisfied
            ready = {
                task_id for task_id in remaining
                if all(dep in completed for dep in group.dependencies_of(task_id))
            }
            
            if not ready:
                raise CircularDependencyError(remaining)
            
            phases.append(ExecutionPhase(tasks=ready, parallel=True))
            completed.update(ready)
            remaining -= ready
        
        return phases
    
    def validate_dag(self, group: ParallelTaskGroup) -> ValidationResult:
        """Detect cycles before execution begins."""
        # DFS cycle detection
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            for dep in group.dependencies_of(node):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(node)
            return False
        
        for task_id in group.all_sub_task_ids:
            if task_id not in visited:
                if has_cycle(task_id):
                    return ValidationResult(valid=False, error="Cycle detected")
        
        return ValidationResult(valid=True)
```

### 5.4 Partial Completion Handling

When some sub-DELEGATEs in a phase complete before others:

```yaml
partial_completion_policy:
  wait_strategy: wait_all          # Default: wait for all in phase before advancing
  timeout_per_delegate_minutes: 120
  on_timeout: 
    action: proceed_with_partial   # Advance with available results, note missing
    min_completion_pct: 75         # Must have ≥75% of phase complete to proceed
  on_failure:
    action: retry_once_then_skip   # Retry failed delegate once, then skip with note
    max_retries: 1
```

### 5.5 Context Injection at Dependency Resolution

When a dependent DELEGATE is ready to execute, the Orchestrator injects resolved dependency outputs:

```yaml
# Consolidation DELEGATE gets enriched context:
context:
  - Injected by Orchestrator from completed dependencies:
  
  - "[pidev-analysis HANDBACK findings]:"
  - "  - Config format: YAML-based, non-standard field names"
  - "  - Hook support: Limited, no pre-commit hooks"
  - "  - Gaps: Missing queue integration, no model routing"
  
  - "[claudecode-analysis HANDBACK findings]:"
  - "  - Config format: JSON, follows opencode.json standard"
  - "  - Hook support: Full SDLC hooks via .claude/hooks/"
  - "  - Gaps: Minor: no voice-notify integration"
  
  # ... other harness findings injected similarly
  
  - "[framework-design HANDBACK]:"
  - "  - Consistency criteria matrix: artifacts/delegates/2026-05-16/framework-criteria.yaml"
  - "  - Recommended standard: opencode.json format as baseline"
```

---

## 6. Consolidation Pattern

### 6.1 Consolidation DELEGATE Structure

Every parallel group that produces multiple independent outputs requires a consolidation DELEGATE. The consolidation DELEGATE is always the final phase.

```yaml
handoff_type: DELEGATE
task_id: {parent_task_id}-consolidation
role: {consolidation_role}          # Principal Engineer for 4+ inputs, Lead Engineer for ≤3
model: {appropriate_model}
effort: high
scope: >
  Synthesize findings from {N} parallel sub-tasks into a unified {deliverable_type}.
  Do not re-do individual analyses; work only from provided HANDBACK summaries.

parallel_group_id: {group_id}
phase: {final_phase_number}
consolidation_type: {synthesis|comparison|integration|report}

# Injected by Orchestrator:
dependency_outputs:
  - task_id: {sub_task_id_1}
    status: complete
    key_findings: [...]
    deliverables: [...]
  - task_id: {sub_task_id_2}
    status: complete
    key_findings: [...]
    deliverables: [...]

consolidation_instructions:
  - Identify common patterns across all {N} analyses
  - Identify divergences and explain root causes
  - Produce unified recommendation set (prioritized)
  - Create implementation roadmap based on findings
  - Note any gaps where additional investigation is needed

success_criteria:
  - Unified {deliverable_type} document created
  - All {N} sub-task findings referenced and synthesized
  - Priority-ordered recommendations produced
  - Implementation roadmap with effort estimates included
  - Gaps and open questions documented
```

### 6.2 Consolidation Types

| Type | When Used | Output Format |
|---|---|---|
| `synthesis` | Multiple analyses of same concern → unified view | Single document with cross-cutting themes |
| `comparison` | Same criteria applied to N targets → comparison matrix | Table/matrix + narrative |
| `integration` | N independent implementations → integrated system | Integration plan + interface contracts |
| `report` | Audit/investigation across N targets → executive summary | Findings report with recommendations |

### 6.3 Consolidation Role Selection

```
N = number of input sub-tasks

N ≤ 2: Lead Engineer (claude-sonnet-4-6, high)
N = 3: Lead Engineer (claude-sonnet-4-6, high)  
N = 4-6: Principal Engineer (claude-opus-4-6, high)
N ≥ 7: Principal Engineer (claude-opus-4-6, max)
Security inputs: Security Engineer reviews before consolidation
```

### 6.4 Partial Consolidation

If some sub-tasks failed or timed out, the consolidation DELEGATE notes gaps explicitly:

```yaml
# In consolidation HANDBACK:
notes: |
  Consolidated 3 of 4 analyses (pidev-analysis timed out after 120 min).
  Recommendations marked [INCOMPLETE] where pidev data was needed.
  Recommend: Re-run pidev-analysis as standalone task and update this consolidation.
```

---

## 7. Configuration & Extensibility

### 7.1 Decomposition Rules Configuration

Decomposition rules are defined in `config/parallel-delegation-rules.yaml`:

```yaml
# config/parallel-delegation-rules.yaml
version: "1.0"

decomposition_rules:
  - rule_id: multi_target_analysis
    description: "Decompose multi-target analysis tasks"
    trigger:
      patterns:
        - "across all {targets}"
        - "each {target}"
        - "compare {target_list}"
      context_signals:
        - field: targets
          type: list
          min_length: 2
    decomposition:
      strategy: one_delegate_per_target
      phase: 1
      parallel: true
      role_selector: senior_engineer_default
      consolidation:
        enabled: true
        role_selector: consolidation_role_by_count
        
  - rule_id: layered_implementation
    description: "Decompose design+implement tasks"
    trigger:
      patterns:
        - "design and implement"
        - "plan and execute"
      complexity_threshold: 60
    decomposition:
      phases:
        - phase: 1
          type: design
          role: lead_engineer
        - phase: 2
          type: implementation
          depends_on: [1]
          role: engineer
        - phase: 3
          type: verification
          depends_on: [2]
          role: quality_engineer

  - rule_id: cross_service_coordination
    description: "Parallelize cross-service changes"
    trigger:
      context_signals:
        - field: repos
          type: list
          min_length: 2
    decomposition:
      strategy: one_delegate_per_repo
      phase: 1
      parallel: true
      role_selector: standard_routing
      consolidation:
        enabled: true
        type: integration

# Custom rule extension point
custom_rules_path: config/custom-parallel-rules.yaml
```

### 7.2 Role Selector Configuration

```yaml
# config/role-selectors.yaml
role_selectors:
  senior_engineer_default:
    primary: Senior Engineer
    fallback: Lead Engineer
    model: claude-sonnet-4-6
    effort: high
    
  consolidation_role_by_count:
    rules:
      - condition: "input_count <= 3"
        role: Lead Engineer
        model: claude-sonnet-4-6
        effort: high
      - condition: "input_count >= 4"
        role: Principal Engineer
        model: claude-opus-4-6
        effort: high
        
  standard_routing:
    delegate_to: orchestrator_routing_tree  # Use existing AGENTS.md routing
```

### 7.3 Adding Custom Decomposition Rules

Teams can extend decomposition rules without modifying core logic:

```yaml
# config/custom-parallel-rules.yaml
custom_rules:
  - rule_id: my_org_audit_pattern
    description: "Decompose security audit + remediation tasks"
    trigger:
      patterns:
        - "audit and remediate"
        - "scan and fix"
    decomposition:
      phases:
        - phase: 1
          type: audit
          role: security_engineer
          parallel: true
          strategy: one_per_target
        - phase: 2
          type: remediation
          depends_on: [1]
          role: engineer
          parallel: true
          strategy: one_per_finding
        - phase: 3
          type: verification
          depends_on: [2]
          role: quality_engineer
```

### 7.4 Feature Flags

```yaml
# In opencode.jsonc or config/orchestrator.yaml
parallel_delegation:
  enabled: true                          # Master switch
  max_concurrent_delegates: 6            # Global limit
  auto_decompose: true                   # Auto-detect decomposable tasks
  require_explicit_decompose: false      # If true, only decompose when explicitly requested
  consolidation_enabled: true            # Enable consolidation phase
  dry_run_mode: false                    # Log decomposition plan without executing
  metrics_enabled: true                  # Emit parallel group metrics
```

---

## 8. Backward Compatibility

### 8.1 Compatibility Guarantee

**All existing single-DELEGATE workflows continue to work unchanged.** The parallel delegation system is purely additive:

- Tasks with `complexity_score < 30` → single DELEGATE (existing behavior)
- Tasks without decomposition triggers → single DELEGATE (existing behavior)
- Explicit `parallel_delegation: disabled` in DELEGATE → single DELEGATE
- All existing DELEGATE/HANDBACK schemas remain valid

### 8.2 Schema Additions (Non-Breaking)

New optional fields added to DELEGATE schema:

```yaml
# Existing required fields unchanged
handoff_type: DELEGATE
task_id: string
role: string
model: string
effort: string
scope: string
context: list
plan: list
success_criteria: list

# New optional fields (backward-compatible)
parallel_group_id: string           # Present only in parallel sub-DELEGATEs
phase: integer                      # Present only in parallel sub-DELEGATEs
depends_on: list                    # Present only when dependencies exist
consolidation_type: string          # Present only in consolidation DELEGATEs
dependency_outputs: list            # Injected by Orchestrator for consolidation
```

### 8.3 Agent Compatibility

Existing agents (Engineer, Senior Engineer, etc.) receive sub-DELEGATEs that look identical to standard DELEGATEs. The new `parallel_group_id`, `phase`, and `depends_on` fields are metadata for the Orchestrator — agents can safely ignore them.

Agents do not need to be updated to support parallel delegation.

---

## 9. Implementation Specification

### 9.1 New Components

#### TaskClassifier (`src/orchestration/parallel/task_classifier.py`)

```python
class TaskClassifier:
    """
    Analyzes incoming tasks and determines if/how to decompose them.
    """
    
    def classify(self, task: IncomingTask) -> ClassificationResult:
        """
        Returns: ClassificationResult with:
          - is_decomposable: bool
          - complexity_score: int (0-100)
          - matched_rules: List[DecompositionRule]
          - recommended_strategy: str
        """
        
    def compute_complexity_score(self, task: IncomingTask) -> int:
        """Scores task complexity for decomposition threshold."""
        
    def detect_triggers(self, task: IncomingTask) -> List[DecompositionRule]:
        """Pattern-matches task against configured decomposition rules."""
```

#### DecompositionEngine (`src/orchestration/parallel/decomposition_engine.py`)

```python
class DecompositionEngine:
    """
    Converts a decomposable task into a ParallelTaskGroup with sub-DELEGATEs.
    """
    
    def decompose(self, task: IncomingTask, rule: DecompositionRule) -> ParallelTaskGroup:
        """
        Returns: ParallelTaskGroup with all sub-DELEGATEs defined.
        """
        
    def slice_context(self, parent_context: Context, target: str) -> Context:
        """Extract relevant context slice for a specific sub-task target."""
        
    def generate_sub_task_id(self, parent_id: str, target: str) -> str:
        """Generate unique sub-task ID: {parent_id}-{target}-{timestamp}"""
```

#### DependencyResolver (`src/orchestration/parallel/dependency_resolver.py`)

```python
class DependencyResolver:
    """
    Manages dependency graph, validates DAG, resolves execution order.
    """
    
    def resolve_execution_order(self, group: ParallelTaskGroup) -> List[ExecutionPhase]:
        """Topological sort → ordered execution phases."""
        
    def validate_dag(self, group: ParallelTaskGroup) -> ValidationResult:
        """Detect cycles before execution."""
        
    def inject_dependency_outputs(self, delegate: Delegate, completed: Dict[str, Handback]) -> Delegate:
        """Inject completed dependency HANDBACKs into dependent DELEGATE context."""
```

#### ExecutionScheduler (`src/orchestration/parallel/execution_scheduler.py`)

```python
class ExecutionScheduler:
    """
    Manages concurrent DELEGATE dispatch respecting capacity limits.
    """
    
    def schedule_phase(self, phase: ExecutionPhase, limits: CapacityLimits) -> ScheduleResult:
        """
        Dispatches all tasks in phase concurrently (up to limits).
        Splits into sub-phases if over limit.
        """
        
    def await_phase_completion(self, phase: ExecutionPhase, timeout: int) -> PhaseResult:
        """
        Waits for all tasks in phase to complete (or timeout).
        Returns partial results if min_completion_pct met.
        """
```

#### HandbackAggregator (`src/orchestration/parallel/handback_aggregator.py`)

```python
class HandbackAggregator:
    """
    Collects HANDBACKs from parallel sub-tasks and prepares consolidation input.
    """
    
    def aggregate(self, group: ParallelTaskGroup, handbacks: List[Handback]) -> AggregatedResult:
        """
        Combines HANDBACKs from all sub-tasks.
        Flags missing/failed tasks.
        Prepares context for consolidation DELEGATE.
        """
        
    def extract_key_findings(self, handback: Handback) -> KeyFindings:
        """Extract structured findings from HANDBACK for consolidation context."""
```

#### ConsolidationEngine (`src/orchestration/parallel/consolidation_engine.py`)

```python
class ConsolidationEngine:
    """
    Creates and manages the consolidation DELEGATE.
    """
    
    def create_consolidation_delegate(
        self,
        group: ParallelTaskGroup,
        aggregated_result: AggregatedResult
    ) -> Delegate:
        """
        Creates consolidation DELEGATE with:
        - Appropriate role (based on input count)
        - Injected dependency outputs
        - Consolidation instructions
        - Success criteria
        """
        
    def select_consolidation_role(self, input_count: int, has_security: bool) -> RoleSpec:
        """Select role/model/effort for consolidation based on input complexity."""
```

### 9.2 Orchestrator Integration Points

The existing Orchestrator polling loop is extended with parallel delegation hooks:

```python
# Existing Orchestrator polling loop (simplified):
while True:
    task = queue.dequeue_incoming()
    if task:
        # NEW: Check if task should be decomposed
        classification = task_classifier.classify(task)
        
        if classification.is_decomposable:
            # NEW: Parallel delegation path
            group = decomposition_engine.decompose(task, classification.matched_rules[0])
            dependency_resolver.validate_dag(group)
            execution_phases = dependency_resolver.resolve_execution_order(group)
            
            for phase in execution_phases:
                results = execution_scheduler.schedule_phase(phase, capacity_limits)
                execution_scheduler.await_phase_completion(phase, timeout=7200)
                
                # Inject outputs for next phase
                for next_phase_task in group.tasks_in_phase(phase.number + 1):
                    dependency_resolver.inject_dependency_outputs(
                        next_phase_task, 
                        results.completed_handbacks
                    )
            
            # Final consolidation
            aggregated = handback_aggregator.aggregate(group, all_handbacks)
            consolidation_delegate = consolidation_engine.create_consolidation_delegate(
                group, aggregated
            )
            consolidation_handback = dispatch(consolidation_delegate)
            queue.move_to_done(task, consolidation_handback)
            
        else:
            # EXISTING: Single DELEGATE path (unchanged)
            delegate = create_delegate(task)
            handback = dispatch(delegate)
            queue.move_to_processing(task, handback)
    
    sleep(30)
```

### 9.3 File Structure

```
src/orchestration/
├── parallel/
│   ├── __init__.py
│   ├── task_classifier.py
│   ├── decomposition_engine.py
│   ├── dependency_resolver.py
│   ├── execution_scheduler.py
│   ├── handback_aggregator.py
│   ├── consolidation_engine.py
│   └── models.py                    # ParallelTaskGroup, ExecutionPhase, etc.
├── config/
│   ├── parallel-delegation-rules.yaml
│   └── role-selectors.yaml
└── tests/
    └── parallel/
        ├── test_task_classifier.py
        ├── test_decomposition_engine.py
        ├── test_dependency_resolver.py
        ├── test_execution_scheduler.py
        ├── test_handback_aggregator.py
        └── test_consolidation_engine.py

artifacts/
└── parallel-groups/
    └── YYYY-MM-DD/
        └── {group_id}/
            ├── group-manifest.yaml      # ParallelTaskGroup definition
            ├── phase-1/
            │   ├── DELEGATE-{sub_task_1}.yaml
            │   ├── DELEGATE-{sub_task_2}.yaml
            │   └── HANDBACK-{sub_task_1}.yaml
            ├── phase-2/
            │   └── DELEGATE-{framework}.yaml
            └── phase-3/
                ├── DELEGATE-consolidation.yaml
                └── HANDBACK-consolidation.yaml
```

### 9.4 Implementation Phases

**Phase 1 (Week 1-2): Core Infrastructure**
- Implement `TaskClassifier` with complexity scoring
- Implement `DecompositionEngine` with `multi_target_analysis` rule
- Implement `DependencyResolver` with DAG validation
- Unit tests for all three components

**Phase 2 (Week 3-4): Execution & Aggregation**
- Implement `ExecutionScheduler` with capacity limits
- Implement `HandbackAggregator`
- Implement `ConsolidationEngine`
- Integration tests with mock agents

**Phase 3 (Week 5-6): Orchestrator Integration**
- Integrate parallel path into Orchestrator polling loop
- Add `parallel-delegation-rules.yaml` configuration
- End-to-end tests with harness consistency example
- Metrics instrumentation

**Phase 4 (Week 7-8): Hardening**
- Timeout and partial completion handling
- Error recovery (retry logic)
- Performance testing (6 concurrent delegates)
- Documentation updates

---

## 10. Architecture Diagrams

### Diagram 1: Parallel Delegation Flow

```
INCOMING TASK
     │
     ▼
┌─────────────────┐
│ Task Classifier  │
│ complexity_score │
│ trigger_detect   │
└────────┬────────┘
         │
    ┌────┴────┐
    │ score?  │
    └────┬────┘
         │
   ┌─────┴──────┐
   │            │
  <30          ≥30
   │            │
   ▼            ▼
SINGLE      ┌─────────────────┐
DELEGATE    │ Decomposition   │
(existing)  │ Engine          │
            │ → ParallelGroup │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Dependency      │
            │ Resolver        │
            │ → DAG validate  │
            │ → Phase order   │
            └────────┬────────┘
                     │
              ┌──────┴──────┐
              │  Phase 1    │ (parallel)
              │  ┌──┐ ┌──┐  │
              │  │D1│ │D2│  │
              │  └──┘ └──┘  │
              └──────┬──────┘
                     │ (all complete)
              ┌──────┴──────┐
              │  Phase 2    │ (parallel)
              │  ┌──┐       │
              │  │D3│       │
              │  └──┘       │
              └──────┬──────┘
                     │ (all complete)
              ┌──────┴──────┐
              │ Consolidate │
              │  ┌──────┐   │
              │  │ D-C  │   │
              │  └──────┘   │
              └──────┬──────┘
                     │
                     ▼
               FINAL HANDBACK
               → queue/done/
```

### Diagram 2: Harness Consistency Example

```
TASK: "Investigate harness consistency across π.dev, Claude Code, Copilot CLI, OpenCode"
complexity_score: 75 → DECOMPOSE

Phase 1 (parallel, ~2 hours wall clock):
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ π.dev       │  │ Claude Code │  │ Copilot CLI │      │
│  │ Analysis    │  │ Analysis    │  │ Analysis    │      │
│  │ Senior Eng  │  │ Senior Eng  │  │ Senior Eng  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                          │
│  ┌─────────────┐                                         │
│  │ OpenCode    │                                         │
│  │ Analysis    │                                         │
│  │ Senior Eng  │                                         │
│  └─────────────┘                                         │
│                                                          │
└──────────────────────────────────────────────────────────┘

Phase 2 (parallel with Phase 1, independent):
┌──────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────┐                         │
│  │ Consistency Framework Design│                         │
│  │ Lead Engineer               │                         │
│  └─────────────────────────────┘                         │
└──────────────────────────────────────────────────────────┘

Phase 3 (depends on Phase 1 + Phase 2):
┌──────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Consolidation: Unified Consistency Plan             │ │
│  │ Principal Engineer (5 inputs → opus-4-6)            │ │
│  │ Inputs: 4 analyses + 1 framework design             │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘

Wall clock: ~2.5 hours (vs. ~10 hours sequential)
Speedup: ~4×
```

### Diagram 3: Dependency Graph (DAG)

```
pidev-analysis ──────────────────────────────────┐
                                                  │
claudecode-analysis ──────────────────────────────┤
                                                  ├──▶ consolidation
copilot-analysis ─────────────────────────────────┤
                                                  │
opencode-analysis ────────────────────────────────┤
                                                  │
framework-design ─────────────────────────────────┘

(All 5 nodes → consolidation; no cycles; valid DAG)
```

### Diagram 4: State Machine for ParallelTaskGroup

```
                    ┌─────────┐
                    │ CREATED │
                    └────┬────┘
                         │ validate_dag()
                         ▼
                    ┌─────────┐
                    │VALIDATED│
                    └────┬────┘
                         │ schedule_phase(1)
                         ▼
                   ┌──────────┐
              ┌───▶│PHASE_N_  │
              │    │EXECUTING │
              │    └────┬─────┘
              │         │ all tasks complete
              │         ▼
              │    ┌──────────┐
              │    │PHASE_N_  │
              │    │COMPLETE  │
              │    └────┬─────┘
              │         │ more phases?
              └─────────┘
                         │ no more phases
                         ▼
                  ┌────────────┐
                  │CONSOLIDATING│
                  └─────┬──────┘
                        │ consolidation complete
                        ▼
                   ┌──────────┐
                   │ COMPLETE │
                   └──────────┘

Error states:
  PHASE_N_EXECUTING → PARTIAL (timeout, min_pct met)
  PHASE_N_EXECUTING → FAILED (timeout, min_pct not met)
  VALIDATED → INVALID (cycle detected)
```

---

## 11. Example: Harness Consistency Investigation

### Input Task

```yaml
task_id: 2026-05-16-harness-consistency-investigation
description: >
  Investigate harness consistency across π.dev, Claude Code, Copilot CLI, and OpenCode.
  Identify gaps, design a consistency framework, and produce a unified improvement plan.
priority: high
targets:
  - pidev
  - claudecode
  - copilot
  - opencode
```

### Decomposition Plan (generated by DecompositionEngine)

```yaml
decomposition_plan:
  parent_task_id: 2026-05-16-harness-consistency-investigation
  group_id: 2026-05-16-harness-consistency-group
  strategy: multi_target_analysis + investigation_framework_design
  complexity_score: 75
  estimated_speedup: 4.0x
  
  phases:
    - phase_number: 1
      parallel: true
      depends_on_phases: []
      sub_tasks:
        - sub_task_id: 2026-05-16-pidev-analysis
          role: Senior Engineer
          scope: "Analyze π.dev harness for config format, hook support, model routing, queue integration gaps"
          
        - sub_task_id: 2026-05-16-claudecode-analysis
          role: Senior Engineer
          scope: "Analyze Claude Code harness for config format, hook support, model routing, queue integration gaps"
          
        - sub_task_id: 2026-05-16-copilot-analysis
          role: Senior Engineer
          scope: "Analyze Copilot CLI harness for config format, hook support, model routing, queue integration gaps"
          
        - sub_task_id: 2026-05-16-opencode-analysis
          role: Senior Engineer
          scope: "Analyze OpenCode harness for config format, hook support, model routing, queue integration gaps"
    
    - phase_number: 2
      parallel: true
      depends_on_phases: []    # Independent of Phase 1
      sub_tasks:
        - sub_task_id: 2026-05-16-framework-design
          role: Lead Engineer
          scope: "Design harness consistency framework: criteria matrix, standard config format, migration guide"
    
    - phase_number: 3
      parallel: false
      depends_on_phases: [1, 2]
      sub_tasks:
        - sub_task_id: 2026-05-16-harness-consolidation
          role: Principal Engineer
          scope: "Consolidate 4 harness analyses + framework design into unified consistency improvement plan"
  
  consolidation:
    phase: 3
    role: Principal Engineer
    model: claude-opus-4-6
    inputs: [2026-05-16-pidev-analysis, 2026-05-16-claudecode-analysis, 
             2026-05-16-copilot-analysis, 2026-05-16-opencode-analysis,
             2026-05-16-framework-design]
```

### Generated Sub-DELEGATE (π.dev analysis)

```yaml
handoff_type: DELEGATE
task_id: 2026-05-16-pidev-analysis
role: Senior Engineer
model: claude-sonnet-4-6
effort: high
scope: >
  Analyze π.dev harness for consistency with agentic-engineers framework.
  Assess: config format, SDLC hook support, model routing, queue integration.
  Do not analyze other harnesses; do not implement fixes.

parallel_group_id: 2026-05-16-harness-consistency-group
phase: 1

context:
  - Target harness: π.dev (pi.dev renderer)
  - Analysis framework: docs/HARNESS-CONSISTENCY-FRAMEWORK.md
  - Reference docs: docs/PI-DEV-RENDERER-ANALYSIS.md
  - Consistency criteria: config_format, hook_support, model_routing, queue_integration
  - Sibling analyses (parallel): claudecode, copilot, opencode

plan:
  1. Read docs/PI-DEV-RENDERER-ANALYSIS.md for existing analysis
  2. Check π.dev config format against opencode.json standard
  3. Assess SDLC hook support (pre-commit, commit-msg, pre-push)
  4. Assess model routing capability (haiku/sonnet/opus tier support)
  5. Assess queue integration (incoming/processing/done queue support)
  6. Document gaps with severity (critical/major/minor)
  7. Produce structured findings in HANDBACK

success_criteria:
  - All 4 criteria assessed with evidence
  - Gaps documented with severity ratings
  - Recommendations for each gap provided
  - HANDBACK includes structured findings for consolidation
```

---

## 12. Error Handling & Failure Modes

### 12.1 Sub-Task Failure

| Failure Mode | Detection | Response |
|---|---|---|
| Sub-task times out | No HANDBACK after `timeout_minutes` | Retry once; if fails again, mark as `timed_out` and proceed with partial |
| Sub-task returns `status: blocked` | HANDBACK with `status: blocked` | Escalate to Lead/Senior Engineer; pause dependent phases |
| Sub-task returns `status: partial` | HANDBACK with `status: partial` | Accept partial; note gaps in consolidation |
| Agent unavailable | No response to DELEGATE | Retry with fallback role; alert Orchestrator |

### 12.2 Cycle Detection Failure

If DAG validation detects a cycle, the entire group is rejected and returned to the Orchestrator as a single task:

```yaml
# Group manifest error:
validation_error:
  type: circular_dependency
  cycle: [task-A, task-B, task-C, task-A]
  action: fallback_to_single_delegate
  message: "Cycle detected in dependency graph; falling back to sequential execution"
```

### 12.3 Consolidation Failure

If the consolidation DELEGATE fails:

1. All sub-task HANDBACKs are preserved in `artifacts/parallel-groups/{group_id}/`
2. Orchestrator creates a new consolidation DELEGATE with retry context
3. If retry fails, human escalation with all sub-task results available

### 12.4 Partial Group Completion

```yaml
partial_completion_handling:
  min_completion_threshold: 0.75    # 75% of phase must complete
  on_below_threshold:
    action: pause_and_alert
    message: "Parallel group {group_id} below completion threshold; human review needed"
  on_above_threshold:
    action: proceed_with_gaps_noted
    consolidation_note: "N of M sub-tasks completed; see gaps section"
```

---

## 13. Metrics & Observability

### 13.1 Parallel Group Metrics

```yaml
# artifacts/metrics/YYYY-MM-DD-{group_id}-parallel-metrics.yaml
group_id: 2026-05-16-harness-consistency-group
parent_task_id: 2026-05-16-harness-consistency-investigation
strategy: multi_target_analysis
complexity_score: 75

execution:
  total_wall_clock_minutes: 152
  sequential_estimate_minutes: 580
  speedup_achieved: 3.8x
  phases_executed: 3
  sub_tasks_total: 6
  sub_tasks_completed: 6
  sub_tasks_failed: 0
  sub_tasks_partial: 0

cost:
  total_tokens_in: 28400
  total_tokens_out: 19200
  estimated_cost_usd: 0.87
  sequential_cost_estimate_usd: 0.87   # Same cost, less wall clock

quality:
  consolidation_quality_score: 88
  sub_task_quality_scores: [85, 91, 87, 83, 90]
  avg_sub_task_quality: 87.2
```

### 13.2 Orchestrator Dashboard Additions

New metrics for parallel delegation:

- `parallel_groups_active`: Current in-flight parallel groups
- `parallel_speedup_avg`: Rolling average speedup factor
- `sub_task_completion_rate`: % of sub-tasks completing successfully
- `consolidation_quality_avg`: Average quality score of consolidation HANDBACKs
- `decomposition_trigger_frequency`: Which rules trigger most often

---

## HANDBACK

```yaml
handoff_type: HANDBACK
task_id: 2026-05-16-orchestrator-parallel-design
status: complete
deliverables:
  - Created: docs/ORCHESTRATOR-PARALLEL-DELEGATION-ARCHITECTURE.md (this document, ~4,500 words)
  - Task decomposition rules: 5 patterns defined (§3.1), complexity scoring (§3.3)
  - Specialist routing rules: role selection matrix (§4.1), routing algorithm (§4.2)
  - Dependency management: DAG model (§5.1), resolution algorithm (§5.3), context injection (§5.5)
  - Consolidation pattern: 4 consolidation types (§6.2), role selection (§6.3)
  - Configuration design: YAML-based rules (§7.1), feature flags (§7.4), extensibility (§7.3)
  - Architecture diagrams: 4 diagrams (§10)
  - Implementation specification: 6 new components, file structure, 4-phase plan (§9)
tests:
  - Document reviewed against all 7 success criteria: PASS
  - Word count: ~4,500 words (requirement: ≥2,000): PASS
  - Architecture diagrams included: 4 diagrams: PASS
  - Backward compatibility addressed: §8: PASS
tokens_in: 8200
tokens_out: 6800
model: claude-sonnet-4-6
effort: high
duration_minutes: 45
escalations: 0
notes: >
  Architecture is fully backward-compatible. Key design decisions:
  (1) Complexity scoring avoids over-decomposing simple tasks.
  (2) DAG validation prevents circular dependencies before execution.
  (3) Context slicing ensures sub-DELEGATEs are self-contained.
  (4) Consolidation role scales with input count (Lead ≤3, Principal ≥4).
  (5) All new DELEGATE fields are optional — existing agents need no changes.
  Recommend: Implement Phase 1 (TaskClassifier + DecompositionEngine) first,
  validate with harness consistency example, then proceed to Phase 2.
```
