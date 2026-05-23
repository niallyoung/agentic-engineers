# -*- coding: utf-8 -*-
"""
agent_creator.py — Agent-Creator skill: scaffold new SPEC-compliant agents.

Automates creation of new agent templates that are immediately SPEC-compliant
and ready for TDD-driven development inside the agentic-engineers framework.

Components:
    AgentConfig         — Configuration dataclass for a new agent
    ConfigValidator     — Validates name, role, model, effort against allowed values
    TemplateGenerator   — Generates SKILL.md, __init__.py, test scaffold, DELEGATE/HANDBACK
    DependencyValidator — Detects circular dependencies, validates dep graph
    IntegrationChecker  — Checks naming conflicts, manifest compatibility, role/model fit
    AgentCreator        — Orchestrates the full scaffold flow (create / dry-run)

Usage (Python API):
    from src.skills.agent_creator.scripts.agent_creator import AgentConfig, AgentCreator

    cfg = AgentConfig(
        name="my-agent",
        role="engineer",
        description="Does X, Y, Z.",
        effort="medium",
    )
    creator = AgentCreator(output_root=Path("src/skills"))
    result = creator.create(cfg)
    print(result)

Usage (CLI):
    python agent_creator.py --name my-agent --role engineer --effort medium
    python agent_creator.py --name my-agent --role engineer --dry-run

Author: Senior Engineer
Phase: TDD GREEN-phase (implements RED-phase test spec)
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================================
# CONSTANTS
# ============================================================================

ALLOWED_ROLES: List[str] = [
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "principal-engineer",
    "security-engineer",
    "quality-engineer",
]

ALLOWED_EFFORTS: List[str] = ["low", "medium", "high"]

ALLOWED_MODELS: List[str] = [
    "claude-haiku-4.5",
    "claude-haiku",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-sonnet",
    "claude-opus-4.7",
    "claude-opus",
    "gpt-4o-mini",
    "gpt-4",
    "gpt-4o",
    "gpt-4-turbo",
    "gemini-2.0-flash",
    "gemini-1-5-pro",
    "gemini-2-pro",
]

DEFAULT_MODEL: str = "claude-haiku-4.5"
DEFAULT_EFFORT: str = "low"

# Recommended minimum models per role (for compatibility warnings)
_ROLE_MINIMUM_MODEL_TIER: Dict[str, str] = {
    "engineer": "haiku",
    "senior-engineer": "sonnet",
    "lead-engineer": "sonnet",
    "principal-engineer": "opus",
    "security-engineer": "sonnet",
    "quality-engineer": "sonnet",
}

# Type alias for dependency graphs: {agent_name: [dep1, dep2, ...]}
DependencyGraph = Dict[str, List[str]]


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for scaffolding a new agent.

    Required:
        name  — Agent name (lowercase alphanumeric + hyphens, max 64 chars)
        role  — Agent role (must be in ALLOWED_ROLES)

    Optional (with sensible defaults):
        model       — LLM model (default: claude-haiku-4.5)
        effort      — Effort band: low/medium/high (default: low)
        thinking    — Enable extended thinking (default: False)
        authority   — Restricts invocation to specific roles (default: None)
        description — Human-readable description (default: "")
        category    — Skill category tag (default: "orchestration")
        dependencies— List of agent names this agent depends on (default: [])
        tools       — List of allowed tools (default: [])
        version     — Semantic version string (default: "1.0")
    """

    name: str
    role: str
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    thinking: bool = False
    authority: Optional[str] = None
    description: str = ""
    category: str = "orchestration"
    dependencies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    version: str = "1.0"

    def __repr__(self) -> str:
        return (
            f"AgentConfig(name={self.name!r}, role={self.role!r}, "
            f"model={self.model!r}, effort={self.effort!r})"
        )


# Use plain str for validation errors — simple and grep-friendly
ValidationError = str


class CreationStatus(Enum):
    """Final status of an AgentCreator.create() call."""
    SUCCESS = "success"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass
class CreationResult:
    """Result of a create() call.

    Fields:
        status      — SUCCESS, FAILED, or DRY_RUN
        agent_name  — Name of the agent being scaffolded
        deliverables— List of file paths created (absolute strings)
        errors      — Validation/integration errors (non-empty means FAILED)
        warnings    — Non-fatal advisory messages
        span        — Metadata dict with timing and file count (for SPAN reporting)
    """

    status: CreationStatus
    agent_name: str
    deliverables: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    span: Optional[Dict] = None

    def __str__(self) -> str:
        status_str = self.status.value.upper()
        lines = [f"[{status_str}] {self.agent_name}"]
        if self.errors:
            lines.append(f"  errors: {', '.join(self.errors[:3])}")
        if self.deliverables:
            lines.append(f"  deliverables: {len(self.deliverables)} files")
        if self.span:
            lines.append(f"  span: {self.span}")
        return "\n".join(lines)


# ============================================================================
# CONFIG VALIDATOR
# ============================================================================

# Valid skill name: lowercase alphanum + hyphens, no leading/trailing/consecutive hyphens
_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_CONSECUTIVE_HYPHENS = re.compile(r"--")


class ConfigValidator:
    """Validates AgentConfig field values against framework constraints.

    All validate_* methods return a list of error strings (empty == valid).
    The composite validate() method runs all checks and merges results.
    """

    def validate_name(self, name: str) -> List[ValidationError]:
        errors: List[ValidationError] = []
        if not name:
            errors.append("name: must not be empty")
            return errors  # further checks meaningless
        if len(name) > 64:
            errors.append(
                f"name: must be ≤64 characters (got {len(name)})"
            )
        # Reject anything with non-lowercase, non-alphanum, non-hyphen
        if re.search(r"[^a-z0-9\-]", name):
            errors.append(
                "name: must be lowercase alphanumeric + hyphens only "
                "(no uppercase, spaces, underscores, or special characters)"
            )
        if name.startswith("-"):
            errors.append("name: must not start with a hyphen")
        if name.endswith("-"):
            errors.append("name: must not end with a hyphen")
        if _CONSECUTIVE_HYPHENS.search(name):
            errors.append("name: must not contain consecutive hyphens (--)")
        return errors

    def validate_role(self, role: str) -> List[ValidationError]:
        if not role:
            return ["role: must not be empty"]
        if role not in ALLOWED_ROLES:
            return [
                f"role: {role!r} is not a valid role. "
                f"Allowed: {', '.join(ALLOWED_ROLES)}"
            ]
        return []

    def validate_effort(self, effort: str) -> List[ValidationError]:
        if effort not in ALLOWED_EFFORTS:
            return [
                f"effort: {effort!r} is not valid. "
                f"Allowed: {', '.join(ALLOWED_EFFORTS)}"
            ]
        return []

    def validate_model(self, model: str) -> List[ValidationError]:
        if model not in ALLOWED_MODELS:
            return [
                f"model: {model!r} is not a recognised model. "
                f"Allowed: {', '.join(ALLOWED_MODELS)}"
            ]
        return []

    def validate(self, config: AgentConfig) -> List[ValidationError]:
        """Run all validations and return merged error list."""
        errors: List[ValidationError] = []
        errors.extend(self.validate_name(config.name))
        errors.extend(self.validate_role(config.role))
        errors.extend(self.validate_effort(config.effort))
        errors.extend(self.validate_model(config.model))
        return errors


# ============================================================================
# TEMPLATE GENERATOR
# ============================================================================

class TemplateGenerator:
    """Generates file contents for a new agent scaffold.

    All generate_* methods return a string (file content).
    generate_all() delegates to AgentCreator for file I/O.
    """

    # ------------------------------------------------------------------
    # SKILL.md
    # ------------------------------------------------------------------

    def generate_skill_md(self, config: AgentConfig) -> str:
        """Generate SKILL.md with valid YAML frontmatter + boilerplate body."""
        authority_line = (
            f"  authority: {config.authority}\n" if config.authority else ""
        )
        thinking_str = "true" if config.thinking else "false"
        description = config.description or f"{config.name} agent."

        frontmatter = (
            "---\n"
            f"name: {config.name}\n"
            f"description: {description}\n"
            "license: Proprietary\n"
            "compatibility: agentic-engineers framework\n"
            "metadata:\n"
            f"  author: agentic-engineers\n"
            f'  version: "{config.version}"\n'
            f"  category: {config.category}\n"
            f"  role: {config.role}\n"
            f"  model: {config.model}\n"
            f"  effort: {config.effort}\n"
            f"  thinking: {thinking_str}\n"
            f"{authority_line}"
            "---\n"
        )

        delegate_block = self._delegate_example(config)
        handback_block = self._handback_example(config)

        body = f"""
# {config.name}

## Overview

{description}

## When to Use

- TODO: describe the triggering condition for this agent
- TODO: describe the expected input format
- TODO: describe the expected output/deliverables

## DELEGATE / HANDBACK Protocol

This agent fully inherits the DELEGATE/HANDBACK queue protocol.

### DELEGATE Template

```yaml
{delegate_block}
```

### HANDBACK Template

```yaml
{handback_block}
```

## Implementation Notes

- TODO: describe key algorithms or logic
- TODO: document any external dependencies

## Testing

Run the test scaffold:

```bash
python3 -m pytest tests/test_{config.name.replace("-", "_")}.py -v
```

See [tests/test_{config.name.replace("-", "_")}.py](tests/test_{config.name.replace("-", "_")}.py)
for the TDD RED-phase test suite.
"""
        return frontmatter + body

    def _delegate_example(self, config: AgentConfig) -> str:
        return (
            f"task_id: YYYY-MM-DD-{config.name}-task-name\n"
            f"role: {config.role}\n"
            f"model: {config.model}\n"
            f"effort: {config.effort}\n"
            f"estimated_hours: 4\n"
            f"title: \"Implement <feature> in {config.name}\"\n"
            f"context: |\n"
            f"  <Describe the problem, relevant files, prior art.>\n"
            f"success_criteria:\n"
            f"  - TODO: define measurable success criterion\n"
        )

    def _handback_example(self, config: AgentConfig) -> str:
        return (
            f"task_id: YYYY-MM-DD-{config.name}-task-name\n"
            f"status: complete\n"
            f"deliverables:\n"
            f"  - src/skills/{config.name}/SKILL.md\n"
            f"tests:\n"
            f"  passed: 0\n"
            f"  failed: 0\n"
            f"  coverage: 0\n"
            f"  framework: pytest\n"
            f"summary: |\n"
            f"  <Brief summary of what was done and key decisions.>\n"
        )

    # ------------------------------------------------------------------
    # __init__.py
    # ------------------------------------------------------------------

    def generate_init_py(self, config: AgentConfig) -> str:
        """Generate package __init__.py with module docstring."""
        module_name = config.name.replace("-", "_")
        return (
            f'# -*- coding: utf-8 -*-\n'
            f'"""{module_name} — {config.description or config.name + " agent."}\n\n'
            f'Role:   {config.role}\n'
            f'Model:  {config.model}\n'
            f'Effort: {config.effort}\n'
            f'"""\n'
        )

    # ------------------------------------------------------------------
    # Test scaffold
    # ------------------------------------------------------------------

    def generate_test_scaffold(self, config: AgentConfig) -> str:
        """Generate TDD RED-phase test scaffold for the new agent."""
        module_name = config.name.replace("-", "_")
        class_name = "".join(w.capitalize() for w in config.name.split("-"))

        return f'''# -*- coding: utf-8 -*-
"""
tests/test_{module_name}.py — {config.name}: TDD RED-phase test scaffold.

Generated by agent-creator skill.

Coverage areas (fill in as you implement):
  1. TODO: describe component 1
  2. TODO: describe component 2

Phase: TDD RED-phase — write failing tests before implementation.
"""

import pytest
import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


# TODO: Replace with real imports once implementation exists
# from src.skills.{module_name}.scripts.{module_name} import (
#     {class_name},
# )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_input():
    """Provide a minimal valid input for {config.name}."""
    return {{}}


# ============================================================================
# Test{class_name} — core behaviour
# ============================================================================

class Test{class_name}:
    """RED-phase tests for {config.name}.

    These tests should FAIL until the implementation is complete.
    Add test methods as you discover required behaviour.
    """

    def test_placeholder_always_passes(self, sample_input):
        """Scaffold placeholder — replace with real tests."""
        # TODO: remove this placeholder and implement real tests
        assert sample_input is not None

    def test_import_succeeds(self):
        """Verify the module can be imported once implemented."""
        # TODO: uncomment once implementation exists
        # from src.skills.{module_name}.scripts.{module_name} import {class_name}
        # assert {class_name} is not None
        pass

    # TODO: Add test methods here following RED → GREEN → REFACTOR cycle
    # Example:
    # def test_returns_expected_output(self, sample_input):
    #     obj = {class_name}()
    #     result = obj.run(sample_input)
    #     assert result.status == "success"
'''

    # ------------------------------------------------------------------
    # DELEGATE / HANDBACK standalone templates
    # ------------------------------------------------------------------

    def generate_delegate_template(self, config: AgentConfig) -> str:
        """Standalone DELEGATE YAML template string."""
        return self._delegate_example(config)

    def generate_handback_template(self, config: AgentConfig) -> str:
        """Standalone HANDBACK YAML template string."""
        return self._handback_example(config)

    # ------------------------------------------------------------------
    # scripts/__init__.py
    # ------------------------------------------------------------------

    def generate_scripts_init_py(self, config: AgentConfig) -> str:
        """Generate empty scripts/__init__.py."""
        return f'# -*- coding: utf-8 -*-\n"""scripts package for {config.name}."""\n'


# ============================================================================
# DEPENDENCY VALIDATOR
# ============================================================================

class DependencyValidator:
    """Validates agent dependency graphs for correctness and cycle-freedom.

    Methods work on plain dict graphs: {agent_name: [dep_name, ...]}
    """

    def validate_graph(self, graph: DependencyGraph) -> List[ValidationError]:
        """Validate an entire dependency graph.

        Checks:
        - Self-dependencies
        - Missing dependencies (dep not in graph keys)
        - Circular dependencies (DFS cycle detection)
        """
        errors: List[ValidationError] = []

        # Check for missing and self deps
        for node, deps in graph.items():
            for dep in deps:
                if dep == node:
                    errors.append(
                        f"dependency: self-dependency detected for '{node}'"
                    )
                elif dep not in graph:
                    errors.append(
                        f"dependency: '{node}' depends on missing agent '{dep}' "
                        f"(not found in graph)"
                    )

        # Cycle detection (DFS on the full graph, even if there are missing nodes)
        cycle_errors = self._detect_cycles(graph)
        errors.extend(cycle_errors)

        return errors

    def validate_new_agent(
        self,
        name: str,
        dependencies: List[str],
        existing: DependencyGraph,
    ) -> List[ValidationError]:
        """Check whether adding a new agent with given deps would create a cycle.

        Builds a combined graph (existing + new agent) and checks for cycles.
        Does NOT flag missing deps for existing agent dependencies (they're assumed valid).
        """
        # Build combined graph
        combined: DependencyGraph = {k: list(v) for k, v in existing.items()}
        combined[name] = list(dependencies)

        # Check for self-dep explicitly
        if name in dependencies:
            return [f"dependency: circular dependency detected ('{name}' depends on itself)"]

        # Check for cycles in the combined graph
        return self._detect_cycles(combined)

    def topological_order(self, graph: DependencyGraph) -> List[str]:
        """Return nodes in topological order (dependencies before dependents).

        Returns an empty list for empty graphs.
        Raises ValueError if the graph contains a cycle.
        """
        if not graph:
            return []

        visited: set = set()
        order: List[str] = []

        def dfs(node: str, path: set) -> None:
            if node in path:
                raise ValueError(f"Cycle detected at '{node}'")
            if node in visited:
                return
            path = path | {node}
            for dep in graph.get(node, []):
                if dep in graph:
                    dfs(dep, path)
            visited.add(node)
            order.append(node)

        for node in graph:
            if node not in visited:
                dfs(node, set())

        return order

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_cycles(self, graph: DependencyGraph) -> List[ValidationError]:
        """DFS-based cycle detection over the provided graph.

        Returns list of error strings describing each cycle found.
        """
        visited: set = set()
        in_stack: set = set()
        errors: List[ValidationError] = []

        def dfs(node: str) -> None:
            visited.add(node)
            in_stack.add(node)
            for dep in graph.get(node, []):
                if dep not in graph:
                    continue  # missing deps are handled separately
                if dep not in visited:
                    dfs(dep)
                elif dep in in_stack:
                    errors.append(
                        f"dependency: circular dependency detected "
                        f"('{node}' → '{dep}' forms a cycle)"
                    )
            in_stack.discard(node)

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)

        return errors


# ============================================================================
# INTEGRATION CHECKER
# ============================================================================

class IntegrationChecker:
    """Checks compatibility of a new agent with the existing framework.

    Detects naming conflicts, validates role/model pairings against
    the agents-manifest, and surfaces integration warnings.
    """

    def check_naming_conflict(
        self, name: str, existing_names: List[str]
    ) -> List[ValidationError]:
        """Return errors if 'name' conflicts with any existing agent name."""
        if name in existing_names:
            return [
                f"integration: naming conflict — agent '{name}' already exists. "
                "Choose a different name or update the existing agent."
            ]
        return []

    def check_role_model_compatibility(
        self, config: AgentConfig
    ) -> List[str]:
        """Warn if the chosen model is below the recommended tier for the role.

        Returns a list of warnings (not hard errors).
        """
        warnings: List[str] = []
        role = config.role
        model = config.model
        min_tier = _ROLE_MINIMUM_MODEL_TIER.get(role)
        if min_tier and min_tier not in model:
            warnings.append(
                f"compatibility warning: role '{role}' typically uses a "
                f"'{min_tier}' or better model, but '{model}' was specified. "
                "This may produce lower-quality results."
            )
        return warnings

    def check_manifest_compatibility(
        self, config: AgentConfig, manifest: Dict
    ) -> List[ValidationError]:
        """Check config against an agents-manifest dict for naming conflicts."""
        agents = manifest.get("agents", {})
        existing_names = list(agents.keys())
        return self.check_naming_conflict(config.name, existing_names)

    def check(
        self,
        config: AgentConfig,
        existing_names: List[str],
        manifest: Dict,
    ) -> List[str]:
        """Run all integration checks; returns combined errors + warnings."""
        results: List[str] = []
        results.extend(self.check_naming_conflict(config.name, existing_names))
        results.extend(self.check_role_model_compatibility(config))
        results.extend(self.check_manifest_compatibility(config, manifest))
        return results


# ============================================================================
# AGENT CREATOR — orchestration
# ============================================================================

class AgentCreator:
    """Orchestrates the full agent scaffold workflow.

    Args:
        output_root: Base directory for generated agents.
                     Default: src/skills/ (relative to repo root, auto-resolved)

    Usage:
        creator = AgentCreator(output_root=Path("src/skills"))
        result = creator.create(config)           # write files
        result = creator.create(config, dry_run=True)  # validate only
    """

    def __init__(self, output_root: Optional[Path] = None) -> None:
        if output_root is None:
            # Default: resolve to <repo_root>/src/skills
            output_root = Path(__file__).parent.parent.parent.parent / "src" / "skills"
        self.output_root = Path(output_root)
        self._validator = ConfigValidator()
        self._generator = TemplateGenerator()
        self._dep_validator = DependencyValidator()
        self._integration_checker = IntegrationChecker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        config: AgentConfig,
        dry_run: bool = False,
    ) -> CreationResult:
        """Scaffold a new agent.

        Steps:
        1. Validate config fields
        2. Check dependency graph for cycles
        3. Check integration conflicts
        4. Generate file contents
        5. Write files to disk (unless dry_run=True)
        6. Return CreationResult with span metadata

        Args:
            config:  AgentConfig describing the new agent
            dry_run: If True, validate and plan but do NOT write files

        Returns:
            CreationResult with status SUCCESS (or FAILED on validation errors)
        """
        t_start = time.monotonic()

        # --- Step 1: Config validation ---
        config_errors = self._validator.validate(config)
        if config_errors:
            return CreationResult(
                status=CreationStatus.FAILED,
                agent_name=config.name,
                errors=config_errors,
                span=self._build_span(t_start, 0),
            )

        # --- Step 2: Dependency validation ---
        if config.dependencies:
            dep_errors = self._dep_validator.validate_new_agent(
                config.name, config.dependencies, {}
            )
            if dep_errors:
                return CreationResult(
                    status=CreationStatus.FAILED,
                    agent_name=config.name,
                    errors=dep_errors,
                    span=self._build_span(t_start, 0),
                )

        # --- Step 3: Integration warnings (non-blocking) ---
        warnings = self._integration_checker.check_role_model_compatibility(config)

        # --- Step 4: Plan deliverables ---
        agent_dir = self.output_root / "agent-creator" / config.name
        module_name = config.name.replace("-", "_")
        planned_files = self._plan_files(config, agent_dir, module_name)
        deliverables = [str(p) for p in planned_files.keys()]

        # --- Step 5: Write files (unless dry_run) ---
        if not dry_run:
            try:
                self._write_files(planned_files, agent_dir)
            except OSError as exc:
                return CreationResult(
                    status=CreationStatus.FAILED,
                    agent_name=config.name,
                    errors=[f"I/O error: {exc}"],
                    span=self._build_span(t_start, 0),
                )

        files_created = 0 if dry_run else len(planned_files)
        status = CreationStatus.SUCCESS

        return CreationResult(
            status=status,
            agent_name=config.name,
            deliverables=deliverables,
            warnings=warnings,
            span=self._build_span(t_start, files_created),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _plan_files(
        self,
        config: AgentConfig,
        agent_dir: Path,
        module_name: str,
    ) -> Dict[Path, str]:
        """Return ordered dict of {path: content} for all files to create."""
        gen = self._generator
        files: Dict[Path, str] = {}

        # SKILL.md
        files[agent_dir / "SKILL.md"] = gen.generate_skill_md(config)

        # __init__.py
        files[agent_dir / "__init__.py"] = gen.generate_init_py(config)

        # scripts/__init__.py
        files[agent_dir / "scripts" / "__init__.py"] = gen.generate_scripts_init_py(config)

        # tests/test_<module>.py
        files[agent_dir / "tests" / f"test_{module_name}.py"] = gen.generate_test_scaffold(config)

        return files

    def _write_files(
        self, planned_files: Dict[Path, str], agent_dir: Path
    ) -> None:
        """Create directories and write all planned files."""
        for path, content in planned_files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    @staticmethod
    def _build_span(t_start: float, files_created: int) -> Dict:
        duration_ms = int((time.monotonic() - t_start) * 1000)
        return {
            "files_created": files_created,
            "duration_ms": duration_ms,
        }


# ============================================================================
# CLI entry point
# ============================================================================

def _main(argv: Optional[List[str]] = None) -> int:  # pragma: no cover
    """Minimal CLI for agent-creator skill."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="agent_creator",
        description="Scaffold a new SPEC-compliant agentic-engineers agent.",
    )
    parser.add_argument("--name", required=True, help="Agent name (lowercase-hyphenated)")
    parser.add_argument("--role", required=True, choices=ALLOWED_ROLES, help="Agent role")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=ALLOWED_MODELS,
                        help=f"LLM model (default: {DEFAULT_MODEL})")
    parser.add_argument("--effort", default=DEFAULT_EFFORT, choices=ALLOWED_EFFORTS,
                        help=f"Effort band (default: {DEFAULT_EFFORT})")
    parser.add_argument("--description", default="", help="Agent description")
    parser.add_argument("--category", default="orchestration", help="Skill category")
    parser.add_argument("--thinking", action="store_true", help="Enable extended thinking")
    parser.add_argument("--authority", default=None, help="Restrict invocation to role")
    parser.add_argument("--deps", nargs="*", default=[], help="Dependency agent names")
    parser.add_argument("--output", default=None, help="Output root directory")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no file writes")

    args = parser.parse_args(argv)

    config = AgentConfig(
        name=args.name,
        role=args.role,
        model=args.model,
        effort=args.effort,
        thinking=args.thinking,
        authority=args.authority,
        description=args.description,
        category=args.category,
        dependencies=args.deps or [],
    )

    output_root = Path(args.output) if args.output else None
    creator = AgentCreator(output_root=output_root)
    result = creator.create(config, dry_run=args.dry_run)

    print(str(result))

    if result.status == CreationStatus.FAILED:
        for err in result.errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    if result.warnings:
        for w in result.warnings:
            print(f"  WARN: {w}")

    if not args.dry_run:
        print("\nCreated files:")
        for path in result.deliverables:
            print(f"  {path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main())
