"""
Parallel Delegation for the Orchestrator Agent.

Enables the Orchestrator to automatically decompose complex tasks into
multiple parallel DELEGATEs routed to appropriate specialist agents.

Key capabilities:
1. detect_parallelizable_task() - Identify tasks that can be split
2. decompose_task() - Split into sub-DELEGATEs with dependency tracking
3. route_sub_delegates() - Route each sub-task to the right specialist
4. create_consolidation_delegate() - Create a final consolidation task
5. ParallelDelegationManager - Orchestrates the full parallel workflow

Backward compatible: tasks that don't match decomposition rules flow
through the existing single-agent path unchanged.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import yaml


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SubDelegate:
    """A single sub-task DELEGATE within a parallel group."""
    task_id: str
    parent_task_id: str
    role: str
    model: str
    effort: str
    scope: str
    context: Dict
    plan: List[str]
    success_criteria: List[str]
    dependencies: List[str] = field(default_factory=list)
    # Execution tier: 0 = can run immediately, 1 = depends on tier-0, etc.
    execution_tier: int = 0
    metadata: Dict = field(default_factory=dict)

    def to_delegate_dict(self) -> Dict:
        """Serialise to a DELEGATE YAML-compatible dict."""
        return {
            "handoff_type": "DELEGATE",
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "timestamp": datetime.now().isoformat(),
            "role": self.role,
            "model": self.model,
            "effort": self.effort,
            "scope": self.scope,
            "context": self.context,
            "plan": self.plan,
            "success_criteria": self.success_criteria,
            "dependencies": self.dependencies,
            "execution_tier": self.execution_tier,
            **self.metadata,
        }


@dataclass
class ParallelPlan:
    """Full decomposition plan for a complex task."""
    parent_task_id: str
    strategy: str  # e.g. "domain_split", "phase_split", "role_split"
    sub_delegates: List[SubDelegate]
    consolidation_delegate: Optional[SubDelegate]
    estimated_parallelism: int  # max concurrent tasks
    dependency_graph: Dict[str, List[str]]  # task_id -> [dependency task_ids]
    rationale: str

    @property
    def tier_groups(self) -> Dict[int, List[SubDelegate]]:
        """Group sub-delegates by execution tier for ordered dispatch."""
        groups: Dict[int, List[SubDelegate]] = {}
        for sd in self.sub_delegates:
            groups.setdefault(sd.execution_tier, []).append(sd)
        return dict(sorted(groups.items()))


# ---------------------------------------------------------------------------
# Decomposition rules configuration (loaded from YAML or defaults)
# ---------------------------------------------------------------------------

DEFAULT_DECOMPOSITION_RULES = {
    "min_complexity_for_parallel": "high",
    "min_scope_word_count": 20,
    "max_sub_tasks": 10,
    "min_sub_tasks": 2,
    "parallelism_threshold": 3,  # ≥3 independent domains → parallel
    "domain_keywords": {
        "security": ["security", "auth", "encrypt", "secret", "permission", "vulnerability"],
        "testing": ["test", "spec", "coverage", "unit test", "integration test", "e2e"],
        "documentation": ["doc", "readme", "comment", "docstring", "changelog", "guide"],
        "implementation": ["implement", "code", "build", "create", "add", "develop"],
        "review": ["review", "audit", "validate", "check", "verify", "assess"],
        "infrastructure": ["deploy", "ci", "cd", "pipeline", "docker", "k8s", "infra"],
        "database": ["database", "schema", "migration", "query", "index", "model"],
        "api": ["api", "endpoint", "route", "rest", "graphql", "grpc", "interface"],
        "configuration": ["config", "setting", "env", "yaml", "json", "toml"],
        "refactor": ["refactor", "cleanup", "restructure", "reorganize", "rename"],
    },
    "role_routing": {
        "security": {"role": "security_engineer", "model": "claude-opus-4-5", "effort": "high"},
        "testing": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "medium"},
        "documentation": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "low"},
        "implementation": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "medium"},
        "review": {"role": "quality_engineer", "model": "claude-sonnet-4-6", "effort": "medium"},
        "infrastructure": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "medium"},
        "database": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "medium"},
        "api": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "medium"},
        "configuration": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "low"},
        "refactor": {"role": "senior_engineer", "model": "claude-sonnet-4-6", "effort": "high"},
        "default": {"role": "engineer", "model": "claude-haiku-4-5", "effort": "medium"},
    },
    # Domain pairs that can always run in parallel (no shared state)
    "always_parallel_pairs": [
        ["security", "documentation"],
        ["testing", "documentation"],
        ["infrastructure", "documentation"],
        ["security", "testing"],
    ],
    # Domains that must run after implementation
    "depends_on_implementation": ["testing", "review", "documentation"],
}


def load_decomposition_config(config_path: Optional[str] = None) -> Dict:
    """
    Load decomposition rules from YAML file or return defaults.

    Args:
        config_path: Optional path to a YAML config file. If None or not
                     found, returns DEFAULT_DECOMPOSITION_RULES.

    Returns:
        Dict of decomposition rules.
    """
    if config_path:
        try:
            with open(config_path) as fh:
                loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                # Deep merge with defaults so partial configs work
                merged = dict(DEFAULT_DECOMPOSITION_RULES)
                merged.update(loaded)
                return merged
        except (OSError, yaml.YAMLError):
            pass
    return dict(DEFAULT_DECOMPOSITION_RULES)


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------

def detect_parallelizable_task(delegate: Dict, config: Optional[Dict] = None) -> Tuple[bool, str]:
    """
    Determine whether a DELEGATE can be decomposed into parallel sub-tasks.

    Criteria (all must be true):
    1. complexity == "high" OR scope word count >= min_scope_word_count
    2. At least ``parallelism_threshold`` distinct domains detected in scope
    3. Task does not already have a parent_task_id (avoid re-splitting children)
    4. Task does not have parallel_delegation_disabled=True

    Args:
        delegate: DELEGATE dict.
        config:   Decomposition rules (uses defaults if None).

    Returns:
        (is_parallelizable, reason_string)
    """
    cfg = config or DEFAULT_DECOMPOSITION_RULES

    # Guard: already a child task
    if delegate.get("parent_task_id"):
        return False, "Task is already a sub-task (has parent_task_id)"

    # Guard: explicitly disabled
    if delegate.get("parallel_delegation_disabled"):
        return False, "Parallel delegation explicitly disabled"

    # Guard: already has parallel_plan
    if delegate.get("parallel_plan"):
        return False, "Task already has a parallel plan"

    scope = delegate.get("scope", "")
    complexity = delegate.get("complexity", delegate.get("effort", "medium")).lower()
    word_count = len(scope.split())

    min_words = cfg.get("min_scope_word_count", 20)
    min_complexity = cfg.get("min_complexity_for_parallel", "high")
    threshold = cfg.get("parallelism_threshold", 3)

    # Check complexity / scope size
    complexity_ok = (
        complexity == min_complexity
        or word_count >= min_words
    )
    if not complexity_ok:
        return False, (
            f"Complexity '{complexity}' and scope word count {word_count} "
            f"below threshold (need '{min_complexity}' or ≥{min_words} words)"
        )

    # Detect domains
    detected = _detect_domains(scope, cfg.get("domain_keywords", {}))
    if len(detected) < threshold:
        return False, (
            f"Only {len(detected)} domain(s) detected ({', '.join(detected) or 'none'}); "
            f"need ≥{threshold} for parallel split"
        )

    return True, (
        f"Parallelizable: {len(detected)} domains detected "
        f"({', '.join(sorted(detected))})"
    )


def _detect_domains(text: str, domain_keywords: Dict[str, List[str]]) -> Set[str]:
    """Return set of domain names whose keywords appear in *text*.

    Handles both single-word and multi-word keywords.  Single-word keywords
    are matched with word boundaries; multi-word keywords use plain substring
    matching (case-insensitive).
    """
    text_lower = text.lower()
    found: Set[str] = set()
    for domain, keywords in domain_keywords.items():
        for kw in keywords:
            kw_lower = kw.lower()
            if " " in kw_lower:
                # Multi-word keyword: substring match
                if kw_lower in text_lower:
                    found.add(domain)
                    break
            else:
                if re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower):
                    found.add(domain)
                    break
    return found


# ---------------------------------------------------------------------------
# Task decomposition
# ---------------------------------------------------------------------------

def decompose_task(delegate: Dict, config: Optional[Dict] = None) -> ParallelPlan:
    """
    Decompose a complex DELEGATE into a ParallelPlan.

    Strategy:
    1. Detect domains present in scope + context
    2. Create one SubDelegate per domain
    3. Assign execution tiers based on dependency rules
    4. Create a consolidation SubDelegate (tier = max_tier + 1)

    Args:
        delegate: Original DELEGATE dict.
        config:   Decomposition rules.

    Returns:
        ParallelPlan with sub_delegates and consolidation_delegate.
    """
    cfg = config or DEFAULT_DECOMPOSITION_RULES
    parent_id = delegate.get("task_id", f"task-{uuid.uuid4().hex[:8]}")
    scope = delegate.get("scope", "")
    context = delegate.get("context", {})
    original_plan = delegate.get("plan", [])
    original_criteria = delegate.get("success_criteria", [])

    # Combine scope + context text for domain detection
    context_text = scope
    if isinstance(context, dict):
        context_text += " " + " ".join(str(v) for v in context.values() if isinstance(v, str))
    elif isinstance(context, str):
        context_text += " " + context

    detected_domains = _detect_domains(context_text, cfg.get("domain_keywords", {}))

    # Limit to max_sub_tasks
    max_sub = cfg.get("max_sub_tasks", 10)
    domains = sorted(detected_domains)[:max_sub]

    if not domains:
        domains = ["implementation"]

    role_routing = cfg.get("role_routing", {})
    depends_on_impl = set(cfg.get("depends_on_implementation", []))

    # Build sub-delegates
    sub_delegates: List[SubDelegate] = []
    impl_task_ids: List[str] = []

    for domain in domains:
        routing = role_routing.get(domain, role_routing.get("default", {}))
        sub_id = f"{parent_id}-{domain}"
        tier = 1 if domain in depends_on_impl else 0

        # Collect implementation task IDs for dependency wiring
        if domain not in depends_on_impl:
            impl_task_ids.append(sub_id)

        # Extract domain-relevant plan steps
        domain_plan = _extract_domain_plan(domain, original_plan, scope)
        domain_criteria = _extract_domain_criteria(domain, original_criteria)

        sd = SubDelegate(
            task_id=sub_id,
            parent_task_id=parent_id,
            role=routing.get("role", "engineer"),
            model=routing.get("model", "claude-haiku-4-5"),
            effort=routing.get("effort", "medium"),
            scope=f"[{domain.upper()}] {scope}",
            context={
                "domain": domain,
                "parent_scope": scope,
                "parent_context": context,
            },
            plan=domain_plan,
            success_criteria=domain_criteria,
            dependencies=[],
            execution_tier=tier,
        )
        sub_delegates.append(sd)

    # Wire dependencies: tier-1 tasks depend on all tier-0 tasks
    for sd in sub_delegates:
        if sd.execution_tier == 1:
            sd.dependencies = list(impl_task_ids)

    # Build dependency graph
    dep_graph: Dict[str, List[str]] = {sd.task_id: sd.dependencies for sd in sub_delegates}

    # Create consolidation delegate (runs after all sub-tasks)
    max_tier = max((sd.execution_tier for sd in sub_delegates), default=0)
    consolidation_id = f"{parent_id}-consolidation"
    consolidation = SubDelegate(
        task_id=consolidation_id,
        parent_task_id=parent_id,
        role="lead_engineer",
        model="claude-sonnet-4-6",
        effort="medium",
        scope=f"[CONSOLIDATION] Integrate and validate results from parallel sub-tasks: {scope}",
        context={
            "domain": "consolidation",
            "parent_scope": scope,
            "sub_task_ids": [sd.task_id for sd in sub_delegates],
        },
        plan=[
            "Review all sub-task HANDBACKs for completeness",
            "Integrate deliverables from each domain",
            "Validate cross-domain consistency",
            "Run final quality checks",
            "Produce consolidated HANDBACK",
        ],
        success_criteria=[
            "All sub-tasks completed successfully",
            "Deliverables are consistent across domains",
            "Quality score ≥ 85 across all sub-tasks",
        ],
        dependencies=[sd.task_id for sd in sub_delegates],
        execution_tier=max_tier + 1,
    )
    dep_graph[consolidation_id] = consolidation.dependencies

    # Determine strategy name
    strategy = _infer_strategy(domains)

    return ParallelPlan(
        parent_task_id=parent_id,
        strategy=strategy,
        sub_delegates=sub_delegates,
        consolidation_delegate=consolidation,
        estimated_parallelism=sum(1 for sd in sub_delegates if sd.execution_tier == 0),
        dependency_graph=dep_graph,
        rationale=(
            f"Task decomposed into {len(sub_delegates)} sub-tasks across domains: "
            f"{', '.join(domains)}. "
            f"Strategy: {strategy}. "
            f"Max parallelism: {sum(1 for sd in sub_delegates if sd.execution_tier == 0)} concurrent tasks."
        ),
    )


def _infer_strategy(domains: List[str]) -> str:
    """Infer a human-readable strategy name from detected domains."""
    if "security" in domains and "testing" in domains:
        return "security_and_quality_split"
    if "implementation" in domains and "testing" in domains:
        return "impl_test_split"
    if len(domains) >= 4:
        return "domain_split"
    if len(domains) == 2:
        return "dual_domain_split"
    return "multi_domain_split"


def _extract_domain_plan(domain: str, original_plan: List[str], scope: str) -> List[str]:
    """Extract or generate plan steps relevant to a domain."""
    # Filter original plan steps that mention the domain
    relevant = [
        step for step in original_plan
        if domain.lower() in step.lower()
    ]
    if relevant:
        return relevant

    # Generate minimal domain-specific plan
    domain_plans = {
        "security": [
            f"Perform security analysis for: {scope[:80]}",
            "Identify and document security risks",
            "Implement security controls",
            "Validate security posture",
        ],
        "testing": [
            f"Write unit tests for: {scope[:80]}",
            "Write integration tests",
            "Achieve ≥80% coverage",
            "Run full test suite and fix failures",
        ],
        "documentation": [
            f"Write documentation for: {scope[:80]}",
            "Add inline code comments",
            "Update README / AGENTS.md as needed",
        ],
        "implementation": [
            f"Implement core functionality: {scope[:80]}",
            "Add error handling and validation",
            "Ensure backward compatibility",
        ],
        "review": [
            f"Review implementation for: {scope[:80]}",
            "Check code quality and standards",
            "Validate success criteria",
            "Produce quality report",
        ],
        "infrastructure": [
            f"Update infrastructure for: {scope[:80]}",
            "Validate CI/CD pipeline",
            "Test deployment",
        ],
        "refactor": [
            f"Refactor code for: {scope[:80]}",
            "Ensure no regressions",
            "Update tests",
        ],
    }
    return domain_plans.get(domain, [f"Complete {domain} work for: {scope[:80]}"])


def _extract_domain_criteria(domain: str, original_criteria: List[str]) -> List[str]:
    """Extract or generate success criteria relevant to a domain."""
    relevant = [c for c in original_criteria if domain.lower() in c.lower()]
    if relevant:
        return relevant

    domain_criteria = {
        "security": ["No critical security vulnerabilities", "Security review passed"],
        "testing": ["All tests pass", "Coverage ≥ 80%"],
        "documentation": ["Documentation complete and accurate"],
        "implementation": ["Implementation complete", "No regressions"],
        "review": ["Quality score ≥ 85", "All review findings addressed"],
        "infrastructure": ["CI/CD pipeline green", "Deployment successful"],
        "refactor": ["Refactoring complete", "All existing tests pass"],
    }
    return domain_criteria.get(domain, [f"{domain.title()} work complete"])


# ---------------------------------------------------------------------------
# Specialist routing
# ---------------------------------------------------------------------------

def route_sub_delegates(
    plan: ParallelPlan,
    config: Optional[Dict] = None,
) -> List[SubDelegate]:
    """
    Validate and (if needed) adjust role routing for each SubDelegate.

    Applies overrides from config role_routing table.  Returns the same
    list with roles confirmed / corrected.

    Args:
        plan:   ParallelPlan from decompose_task().
        config: Decomposition rules.

    Returns:
        List of SubDelegate with confirmed role assignments.
    """
    cfg = config or DEFAULT_DECOMPOSITION_RULES
    role_routing = cfg.get("role_routing", {})

    routed: List[SubDelegate] = []
    for sd in plan.sub_delegates:
        domain = sd.context.get("domain", "default")
        routing = role_routing.get(domain, role_routing.get("default", {}))
        # Only override if role was set to a default; preserve explicit overrides
        if sd.role == "engineer" and routing.get("role") != "engineer":
            sd.role = routing["role"]
            sd.model = routing.get("model", sd.model)
            sd.effort = routing.get("effort", sd.effort)
        routed.append(sd)

    return routed


# ---------------------------------------------------------------------------
# Consolidation delegate creation
# ---------------------------------------------------------------------------

def create_consolidation_delegate(
    plan: ParallelPlan,
    sub_handbacks: Optional[List[Dict]] = None,
) -> SubDelegate:
    """
    Create (or update) the consolidation SubDelegate for a ParallelPlan.

    If sub_handbacks are provided, enriches the consolidation context with
    actual results so the Lead Engineer has full context.

    Args:
        plan:           ParallelPlan.
        sub_handbacks:  Optional list of completed sub-task HANDBACKs.

    Returns:
        Updated consolidation SubDelegate.
    """
    consolidation = plan.consolidation_delegate
    if consolidation is None:
        raise ValueError("ParallelPlan has no consolidation_delegate")

    if sub_handbacks:
        consolidation.context["sub_handbacks"] = sub_handbacks
        # Compute aggregate quality
        scores = [hb.get("quality_score", 0) for hb in sub_handbacks]
        if scores:
            consolidation.context["avg_sub_quality"] = round(
                sum(scores) / len(scores), 1
            )

    return consolidation


# ---------------------------------------------------------------------------
# Dependency validation
# ---------------------------------------------------------------------------

def validate_dependency_graph(dep_graph: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
    """
    Validate the dependency graph for cycles and missing nodes.

    Uses DFS-based cycle detection.

    Args:
        dep_graph: {task_id: [dependency_task_ids]}

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []
    all_nodes = set(dep_graph.keys())

    # Check for missing dependency references
    for node, deps in dep_graph.items():
        for dep in deps:
            if dep not in all_nodes:
                errors.append(f"Node '{node}' depends on unknown node '{dep}'")

    # Cycle detection via DFS
    visited: Set[str] = set()
    in_stack: Set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for dep in dep_graph.get(node, []):
            if dep not in visited:
                if dfs(dep):
                    return True
            elif dep in in_stack:
                errors.append(f"Cycle detected involving '{node}' → '{dep}'")
                return True
        in_stack.discard(node)
        return False

    for node in all_nodes:
        if node not in visited:
            dfs(node)

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# High-level manager
# ---------------------------------------------------------------------------

class ParallelDelegationManager:
    """
    Orchestrates the full parallel delegation workflow.

    Usage::

        mgr = ParallelDelegationManager(config_path="decomposition_config.yaml")
        if mgr.should_parallelize(delegate):
            plan = mgr.plan(delegate)
            # Dispatch tier-0 sub-delegates immediately
            for sd in plan.tier_groups[0]:
                queue.write(sd.to_delegate_dict())
            # ... wait for tier-0, then dispatch tier-1, etc.
            # Finally dispatch consolidation
            queue.write(plan.consolidation_delegate.to_delegate_dict())
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = load_decomposition_config(config_path)

    def should_parallelize(self, delegate: Dict) -> Tuple[bool, str]:
        """Return (bool, reason) for whether delegate should be parallelized."""
        return detect_parallelizable_task(delegate, self.config)

    def plan(self, delegate: Dict) -> ParallelPlan:
        """
        Produce a full ParallelPlan for a delegate.

        Raises:
            ValueError: If delegate is not parallelizable.
        """
        ok, reason = self.should_parallelize(delegate)
        if not ok:
            raise ValueError(f"Cannot parallelize: {reason}")

        raw_plan = decompose_task(delegate, self.config)
        route_sub_delegates(raw_plan, self.config)

        valid, errors = validate_dependency_graph(raw_plan.dependency_graph)
        if not valid:
            raise ValueError(f"Dependency graph invalid: {errors}")

        return raw_plan

    def dispatch_tier(
        self,
        plan: ParallelPlan,
        tier: int,
        queue_writer,
    ) -> List[str]:
        """
        Write all SubDelegates in *tier* to the queue.

        Args:
            plan:         ParallelPlan.
            tier:         Execution tier to dispatch.
            queue_writer: Object with a ``write(task_id, delegate_dict)`` method.

        Returns:
            List of task_ids dispatched.
        """
        dispatched: List[str] = []
        for sd in plan.tier_groups.get(tier, []):
            queue_writer.write(sd.task_id, sd.to_delegate_dict())
            dispatched.append(sd.task_id)
        return dispatched

    def dispatch_consolidation(
        self,
        plan: ParallelPlan,
        queue_writer,
        sub_handbacks: Optional[List[Dict]] = None,
    ) -> str:
        """
        Write the consolidation delegate to the queue.

        Args:
            plan:          ParallelPlan.
            queue_writer:  Object with a ``write(task_id, delegate_dict)`` method.
            sub_handbacks: Optional completed sub-task HANDBACKs for enrichment.

        Returns:
            consolidation task_id.
        """
        consolidation = create_consolidation_delegate(plan, sub_handbacks)
        queue_writer.write(consolidation.task_id, consolidation.to_delegate_dict())
        return consolidation.task_id

    def summarize_plan(self, plan: ParallelPlan) -> str:
        """Return a human-readable summary of the plan."""
        lines = [
            f"Parallel Plan for '{plan.parent_task_id}'",
            f"  Strategy:     {plan.strategy}",
            f"  Sub-tasks:    {len(plan.sub_delegates)}",
            f"  Parallelism:  {plan.estimated_parallelism} concurrent (tier 0)",
            f"  Rationale:    {plan.rationale}",
            "",
            "  Execution tiers:",
        ]
        for tier, sds in plan.tier_groups.items():
            lines.append(f"    Tier {tier}: {', '.join(sd.task_id for sd in sds)}")
        if plan.consolidation_delegate:
            lines.append(
                f"    Tier {plan.consolidation_delegate.execution_tier} "
                f"(consolidation): {plan.consolidation_delegate.task_id}"
            )
        return "\n".join(lines)
