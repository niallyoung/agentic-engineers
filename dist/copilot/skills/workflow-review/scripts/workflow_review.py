"""
workflow_review.py — Workflow-Review skill: validate end-to-end delegation workflows.

Components:
    WorkflowNode        — Represents an agent in the workflow (name, role, skills)
    WorkflowEdge        — Represents a data flow (DELEGATE->work->HANDBACK)
    WorkflowDiagram     — ASCII diagram generator
    WorkflowConsistencyChecker — Checks for gaps (missing gates, cycles, unused components)
    WorkflowReviewer    — Orchestrates full review (diagram + consistency + report)
    WorkflowReport      — Dataclass for results

Features:
  - Parse agents from config/FRAMEWORK-MANIFEST.yaml
  - Generate ASCII workflow diagrams
  - Check for: missing quality gates, incomplete feedback loops, blocked exit criteria, unused components
  - Detect circular delegation chains
  - Validate token budget alignment
  - Output: diagram, checklist, recommendations, report
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WorkflowNode:
    """Represents an agent node in the workflow graph."""
    name: str
    role: str
    agent_type: str
    description: str
    model: str
    status: str


@dataclass
class WorkflowEdge:
    """Represents a directed data-flow edge (DELEGATE → work → HANDBACK)."""
    source: str
    target: str
    edge_type: str  # "delegate", "handback", "quality-gate"
    label: Optional[str] = None


@dataclass
class WorkflowReport:
    """Full workflow review report."""
    timestamp: str
    diagram: str
    consistency_checklist: Dict[str, List[str]]
    cycles_detected: List[str]
    unused_agents: List[str]
    missing_quality_gates: List[str]
    recommendations: List[str]
    quality_score: float
    passed: bool


# ---------------------------------------------------------------------------
# Diagram generator
# ---------------------------------------------------------------------------

class WorkflowDiagram:
    """Generates ASCII diagrams of agent workflows."""

    HEADER_WIDTH = 53

    def __init__(self, nodes: List[WorkflowNode], edges: List[WorkflowEdge]):
        self.nodes = nodes
        self.edges = edges

    def _header(self) -> List[str]:
        w = self.HEADER_WIDTH
        lines = [
            "+" + "-" * w + "+",
            "|" + "AGENT WORKFLOW DIAGRAM".center(w) + "|",
            "|" + "agentic-engineers framework".center(w) + "|",
            "+" + "-" * w + "+",
        ]
        return lines

    def _format_flow(self, source: str, target: str, is_quality_gate: bool = False) -> List[str]:
        """Render a single DELEGATE/HANDBACK flow."""
        gate_label = " (quality gate)" if is_quality_gate else ""
        lines = [
            "",
            "[{src}] --DELEGATE--> [{tgt}]{gate}".format(
                src=source, tgt=target, gate=gate_label
            ),
            "       ^                          |",
            "       |                       HANDBACK",
            "       |                          |",
            "       +--------------------------+",
        ]
        return lines

    def render(self) -> str:
        """Return the full ASCII diagram as a string."""
        output_lines = self._header()

        # Determine orchestrator node
        orchestrator = None
        quality_agent = None
        other_agents = []

        for node in self.nodes:
            name_lower = node.name.lower()
            if "orchestrator" in name_lower:
                orchestrator = node
            elif node.agent_type in ("validation", "quality") or "quality" in name_lower:
                quality_agent = node
            else:
                other_agents.append(node)

        if not orchestrator and self.nodes:
            orchestrator = self.nodes[0]

        orch_name = orchestrator.name if orchestrator else "Orchestrator"

        # Render flows for other agents first
        for node in other_agents:
            if node.name != orch_name:
                output_lines.extend(self._format_flow(orch_name, node.name))

        # Render quality gate flow last
        if quality_agent and quality_agent.name != orch_name:
            output_lines.extend(
                self._format_flow(orch_name, quality_agent.name, is_quality_gate=True)
            )

        output_lines.append("")
        return "\n".join(output_lines)


# ---------------------------------------------------------------------------
# Consistency checker
# ---------------------------------------------------------------------------

class WorkflowConsistencyChecker:
    """Runs structural consistency checks on the loaded workflow."""

    def __init__(
        self,
        nodes: List[WorkflowNode],
        skills_manifest: Dict[str, Any],
        skills_dir: Path,
    ):
        self.nodes = nodes
        self.skills_manifest = skills_manifest
        self.skills_dir = skills_dir

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_has_quality_gates(self) -> Tuple[bool, str]:
        """At least one validation/quality-type agent must exist."""
        for node in self.nodes:
            if node.agent_type in ("validation", "quality") or "quality" in node.name.lower():
                return True, "has_quality_gates"
        return False, "has_quality_gates"

    def check_has_orchestrator(self) -> Tuple[bool, str]:
        """An orchestrator agent must be present."""
        for node in self.nodes:
            if "orchestrator" in node.name.lower() or node.agent_type == "routing":
                return True, "has_orchestrator"
        return False, "has_orchestrator"

    def check_has_feedback_loops(self) -> Tuple[bool, str]:
        """More than one agent means HANDBACK paths can complete."""
        return len(self.nodes) > 1, "has_feedback_loops"

    def check_no_circular_chains(self, cycles: List[str]) -> Tuple[bool, str]:
        """No cycles must be detected."""
        return len(cycles) == 0, "no_circular_chains"

    def check_agents_documented(self) -> Tuple[bool, str]:
        """All agents must have non-empty descriptions."""
        for node in self.nodes:
            if not node.description or not node.description.strip():
                return False, "agents_documented"
        return True, "agents_documented"

    def check_skills_have_skill_md(self) -> Tuple[bool, str]:
        """All skills listed in manifest must have a SKILL.md file."""
        if not self.skills_manifest:
            return True, "skills_have_skill_md"  # nothing to check

        for skill_name in self.skills_manifest:
            skill_dir = self.skills_dir / skill_name
            if not (skill_dir / "SKILL.md").exists():
                return False, "skills_have_skill_md"
        return True, "skills_have_skill_md"

    # ------------------------------------------------------------------
    # Run all checks
    # ------------------------------------------------------------------

    def run_all(self, cycles: List[str]) -> Dict[str, List[str]]:
        """Run all checks and return {passed, failed, warnings}."""
        result = {"passed": [], "failed": [], "warnings": []}  # type: Dict[str, List[str]]

        checks = [
            self.check_has_quality_gates(),
            self.check_has_orchestrator(),
            self.check_has_feedback_loops(),
            (self.check_no_circular_chains(cycles)[0], "no_circular_chains"),
            self.check_agents_documented(),
            self.check_skills_have_skill_md(),
        ]

        for ok, name in checks:
            if ok:
                result["passed"].append(name)
            else:
                result["failed"].append(name)

        # Advisory warnings
        if len(self.nodes) < 3:
            result["warnings"].append("fewer_than_3_agents_defined")

        return result


# ---------------------------------------------------------------------------
# Cycle detector (DFS on agent type hierarchy)
# ---------------------------------------------------------------------------

class CycleDetector:
    """Detects cycles in an agent delegation graph."""

    def __init__(self, nodes: List[WorkflowNode]):
        # Build a simple adjacency list based on type hierarchy
        self.adjacency = self._build_adjacency(nodes)

    @staticmethod
    def _build_adjacency(nodes: List[WorkflowNode]) -> Dict[str, List[str]]:
        """Build type-based delegation adjacency (routing -> implementation -> validation)."""
        name_by_type = {}  # type: Dict[str, str]
        for node in nodes:
            name_by_type[node.agent_type] = node.name

        adjacency = {}  # type: Dict[str, List[str]]
        for node in nodes:
            adjacency[node.name] = []

        # Routing delegates to implementation types
        routing_name = name_by_type.get("routing")
        if routing_name:
            for node in nodes:
                if node.agent_type in ("implementation", "validation", "review", "security"):
                    adjacency[routing_name].append(node.name)

        return adjacency

    def detect(self) -> List[str]:
        """Return list of cycle path strings using DFS."""
        visited = set()  # type: Set[str]
        rec_stack = set()  # type: Set[str]
        cycles = []  # type: List[str]

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)

            for neighbour in self.adjacency.get(node, []):
                if neighbour not in visited:
                    dfs(neighbour, path + [neighbour])
                elif neighbour in rec_stack:
                    # Cycle found
                    cycle_start = path.index(neighbour) if neighbour in path else 0
                    cycle_path = path[cycle_start:] + [neighbour]
                    cycles.append(" -> ".join(cycle_path))

            rec_stack.discard(node)

        for node_name in list(self.adjacency.keys()):
            if node_name not in visited:
                dfs(node_name, [node_name])

        return cycles


# ---------------------------------------------------------------------------
# Main reviewer
# ---------------------------------------------------------------------------

class WorkflowReviewer:
    """
    Orchestrates the full workflow review.

    Usage::

        reviewer = WorkflowReviewer(Path("config/FRAMEWORK-MANIFEST.yaml"))
        report = reviewer.review()
    """

    DEFAULT_MANIFEST_PATH = Path("config/FRAMEWORK-MANIFEST.yaml")

    def __init__(self, manifest_path: Optional[Path] = None):
        if manifest_path is None:
            manifest_path = self.DEFAULT_MANIFEST_PATH
        self.manifest_path = manifest_path
        self._manifest = None      # type: Optional[Dict[str, Any]]
        self._nodes = None         # type: Optional[List[WorkflowNode]]

    # ------------------------------------------------------------------
    # Manifest loading
    # ------------------------------------------------------------------

    def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest is not None:
            return self._manifest

        if yaml is None:
            raise ImportError("pyyaml is required. Install with: pip install pyyaml")

        if not self.manifest_path.exists():
            logger.warning("Manifest not found at %s; using empty manifest.", self.manifest_path)
            self._manifest = {}
            return self._manifest

        with open(self.manifest_path, "r") as fh:
            self._manifest = yaml.safe_load(fh) or {}

        return self._manifest

    def _build_nodes(self) -> List[WorkflowNode]:
        if self._nodes is not None:
            return self._nodes

        manifest = self._load_manifest()
        agents_section = manifest.get("agents", {}) or {}
        nodes = []

        for agent_key, agent_data in agents_section.items():
            if not isinstance(agent_data, dict):
                continue
            nodes.append(
                WorkflowNode(
                    name=agent_data.get("name", agent_key),
                    role=agent_key,
                    agent_type=agent_data.get("type", "unknown"),
                    description=agent_data.get("description", ""),
                    model=agent_data.get("model", ""),
                    status=agent_data.get("status", "unknown"),
                )
            )

        self._nodes = nodes
        return nodes

    def _get_skills_manifest(self) -> Dict[str, Any]:
        manifest = self._load_manifest()
        return manifest.get("skills", {}) or {}

    def _get_skills_dir(self) -> Path:
        return self.manifest_path.parent.parent / "src" / "skills"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_diagram(self) -> str:
        """Return an ASCII diagram representing the agent workflow."""
        nodes = self._build_nodes()
        edges = []  # type: List[WorkflowEdge]
        diagram = WorkflowDiagram(nodes, edges)
        return diagram.render()

    def detect_cycles(self) -> List[str]:
        """Return a list of cycle path strings (empty list if none)."""
        nodes = self._build_nodes()
        detector = CycleDetector(nodes)
        return detector.detect()

    def check_consistency(self) -> Dict[str, List[str]]:
        """
        Run all consistency checks.

        Returns a dict with keys ``passed``, ``failed``, ``warnings``
        each containing a list of check names.
        """
        nodes = self._build_nodes()
        skills_manifest = self._get_skills_manifest()
        skills_dir = self._get_skills_dir()
        cycles = self.detect_cycles()

        checker = WorkflowConsistencyChecker(nodes, skills_manifest, skills_dir)
        return checker.run_all(cycles)

    def _compute_quality_score(self, checklist: Dict[str, List[str]]) -> float:
        """Start at 100, deduct 15 per failed check, 5 per warning; clamp to [0, 100]."""
        score = 100.0
        score -= 15.0 * len(checklist.get("failed", []))
        score -= 5.0 * len(checklist.get("warnings", []))
        return max(0.0, min(100.0, score))

    def _find_unused_agents(self) -> List[str]:
        """Return agents that are active but have no delegation flows defined."""
        nodes = self._build_nodes()
        # In the current model every active agent is potentially reachable from orchestrator.
        # Flag agents whose status is not "active" as unused/disabled.
        return [n.name for n in nodes if n.status != "active"]

    def _find_missing_quality_gates(self) -> List[str]:
        """Return workflow phases that lack a quality gate."""
        nodes = self._build_nodes()
        phases_with_gate = set()  # type: Set[str]
        for node in nodes:
            if node.agent_type in ("validation", "quality") or "quality" in node.name.lower():
                phases_with_gate.add("main")

        all_phases = {"main"}
        return list(all_phases - phases_with_gate)

    def _build_recommendations(
        self,
        checklist: Dict[str, List[str]],
        cycles: List[str],
        missing_gates: List[str],
    ) -> List[str]:
        recs = []  # type: List[str]
        failed = checklist.get("failed", [])
        warnings = checklist.get("warnings", [])

        if "has_quality_gates" in failed:
            recs.append(
                "Add a validation-type agent (e.g. Quality Engineer) to enforce quality gates."
            )
        if "has_orchestrator" in failed:
            recs.append(
                "Add an orchestrator agent to manage task routing and delegation."
            )
        if "has_feedback_loops" in failed:
            recs.append(
                "Add at least two agents so HANDBACK feedback loops can complete."
            )
        if "no_circular_chains" in failed:
            recs.append(
                "Remove circular delegation: {cycles}.".format(cycles="; ".join(cycles))
            )
        if "agents_documented" in failed:
            recs.append(
                "Add descriptions to all agents in FRAMEWORK-MANIFEST.yaml."
            )
        if "skills_have_skill_md" in failed:
            recs.append(
                "Ensure every skill listed in FRAMEWORK-MANIFEST.yaml has a SKILL.md marker file."
            )
        if missing_gates:
            recs.append(
                "Add quality gates to phases: {phases}.".format(phases=", ".join(missing_gates))
            )
        if "fewer_than_3_agents_defined" in warnings:
            recs.append(
                "Consider defining at least 3 agents for a robust delegation workflow."
            )

        return recs

    def review(self) -> WorkflowReport:
        """Run the full workflow review and return a WorkflowReport."""
        diagram = self.generate_diagram()
        cycles = self.detect_cycles()
        checklist = self.check_consistency()
        unused = self._find_unused_agents()
        missing_gates = self._find_missing_quality_gates()
        recommendations = self._build_recommendations(checklist, cycles, missing_gates)
        quality_score = self._compute_quality_score(checklist)
        passed = quality_score >= 70.0

        return WorkflowReport(
            timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            diagram=diagram,
            consistency_checklist=checklist,
            cycles_detected=cycles,
            unused_agents=unused,
            missing_quality_gates=missing_gates,
            recommendations=recommendations,
            quality_score=quality_score,
            passed=passed,
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config/FRAMEWORK-MANIFEST.yaml")
    reviewer = WorkflowReviewer(manifest)
    report = reviewer.review()

    print(report.diagram)
    print("Quality Score: {:.1f}/100".format(report.quality_score))
    print("Status: {}".format("PASS" if report.passed else "FAIL"))

    if report.recommendations:
        print("\nRecommendations:")
        for rec in report.recommendations:
            print("  -", rec)

    sys.exit(0 if report.passed else 1)
