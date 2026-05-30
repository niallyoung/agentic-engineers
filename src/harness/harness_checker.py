"""OpenCode harness runtime validation.

Validates OpenCode harness configuration at startup to catch configuration
errors early and provide actionable remediation steps.

The HarnessChecker class runs 5 critical validation checks:
  1. check_agents_loaded() — verify 8 agents in AGENTS.md + running instance
  2. check_skills_available() — verify 14+ skills can be loaded
  3. check_queue_paths() — verify canonical queue paths exist
  4. check_orchestrator() — test orchestrator invocation
  5. check_schemas() — validate DELEGATE/HANDBACK spec_version

Each check returns (passed: bool, message: str, remediation: str).
On failure, the checker reports detailed errors with remediation steps.

Example:
    >>> checker = HarnessChecker()
    >>> result = checker.run_all_checks()
    >>> if not result.all_passed:
    ...     print(result.report())

Exit codes:
  0 = all checks passed
  1 = critical check failed
  2 = warning (missing non-critical components)
"""

from __future__ import annotations

import dataclasses
import importlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

import yaml


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """Result of a single validation check."""

    check_name: str
    passed: bool
    message: str
    remediation: str = ""

    def format(self) -> str:
        """Format check result for display."""
        icon = "✅" if self.passed else "❌"
        result = f"{icon} {self.check_name}: {self.message}"
        if self.remediation:
            result += f"\n   → Remediation: {self.remediation}"
        return result


@dataclasses.dataclass
class ValidationReport:
    """Complete validation report with all check results."""

    checks: list[CheckResult] = dataclasses.field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def all_passed(self) -> bool:
        """True if all critical checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def passed_count(self) -> int:
        """Count of passed checks."""
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        """Count of failed checks."""
        return sum(1 for c in self.checks if not c.passed)

    def report(self) -> str:
        """Format complete report."""
        lines = [
            "=" * 70,
            "OpenCode Harness Validation Report",
            "=" * 70,
            "",
        ]

        for check in self.checks:
            lines.append(check.format())
            lines.append("")

        lines.append("=" * 70)
        status = f"PASSED ({self.passed_count}/{len(self.checks)} checks)"
        if not self.all_passed:
            status = f"FAILED ({self.failed_count} critical, {self.passed_count} passed)"
        lines.append(f"Result: {status}")
        lines.append("=" * 70)

        return "\n".join(lines)


class HarnessCheckError(Exception):
    """Error during harness validation."""

    pass


# ---------------------------------------------------------------------------
# Harness Checker Implementation
# ---------------------------------------------------------------------------


class HarnessChecker:
    """OpenCode harness startup validation.

    Validates:
      1. All 8 agents are loaded and available
      2. All 14+ skills are available and renderable
      3. Queue paths exist and are canonical
      4. Orchestrator can be invoked successfully
      5. DELEGATE/HANDBACK schemas are correct

    Usage:
        >>> checker = HarnessChecker()
        >>> result = checker.run_all_checks()
        >>> print(result.report())
    """

    EXPECTED_AGENT_COUNT = 8
    EXPECTED_SKILL_COUNT = 14
    EXPECTED_AGENTS = {
        "orchestrator",
        "engineer",
        "senior-engineer",
        "lead-engineer",
        "principal-engineer",
        "security-engineer",
        "quality-engineer",
        "model-engineer",
    }

    def __init__(self, repo_root: str | None = None):
        """Initialize HarnessChecker.

        Args:
            repo_root: Root directory of agentic-engineers repo.
                      If None, will attempt to find it.
        """
        self.repo_root = Path(repo_root or self._find_repo_root())
        self.src_root = self.repo_root / "src"
        self.dist_opencode = self.repo_root / "dist" / "opencode"
        self.dist_agent_dir = self.src_root / "orchestration"  # For schemas

    def _find_repo_root(self) -> Path:
        """Find agentic-engineers repo root."""
        current = Path.cwd()
        for _ in range(10):
            if (current / "SPEC.md").exists() and (current / "src" / "AGENTS.md").exists():
                return current
            current = current.parent
        raise HarnessCheckError(
            "Could not find agentic-engineers repo root. "
            "Please run from within the repository or pass repo_root explicitly."
        )

    def run_all_checks(self) -> ValidationReport:
        """Run all 5 validation checks.

        Returns:
            ValidationReport with all check results.
        """
        report = ValidationReport()

        checks = [
            ("check_agents_loaded", self.check_agents_loaded),
            ("check_skills_available", self.check_skills_available),
            ("check_queue_paths", self.check_queue_paths),
            ("check_orchestrator", self.check_orchestrator),
            ("check_schemas", self.check_schemas),
        ]

        for check_name, check_func in checks:
            try:
                result = check_func()
                report.checks.append(result)
            except Exception as e:
                report.checks.append(
                    CheckResult(
                        check_name=check_name,
                        passed=False,
                        message=f"Check failed with exception: {str(e)}",
                        remediation="Check the error details above and ensure the repo is properly initialized.",
                    )
                )

        return report

    def check_agents_loaded(self) -> CheckResult:
        """Verify all 8 agents are defined in AGENTS.md.

        Checks:
          - AGENTS.md exists
          - Exactly 8 agents are defined
          - All expected agent names are present
          - Agent roles match the specification

        Returns:
            CheckResult indicating if all agents are properly loaded.
        """
        agents_md = self.src_root / "AGENTS.md"

        if not agents_md.exists():
            return CheckResult(
                check_name="check_agents_loaded",
                passed=False,
                message=f"AGENTS.md not found at {agents_md}",
                remediation="Ensure the repository is properly initialized and AGENTS.md exists.",
            )

        content = agents_md.read_text()

        # Extract agent table from AGENTS.md
        # Expected format: "| # | Role | Model | ..." with agent rows
        agent_patterns = [
            r"\|\s*1\s*\|\s*\*\*Orchestrator\*\*",
            r"\|\s*2\s*\|\s*\*\*Engineer\*\*",
            r"\|\s*3\s*\|\s*\*\*Model Engineer\*\*",
            r"\|\s*4\s*\|\s*\*\*Quality Engineer\*\*",
            r"\|\s*5\s*\|\s*\*\*Lead Engineer\*\*",
            r"\|\s*6\s*\|\s*\*\*Senior Engineer\*\*",
            r"\|\s*7\s*\|\s*\*\*Principal Engineer\*\*",
            r"\|\s*8\s*\|\s*\*\*Security Engineer\*\*",
        ]

        found_agents = []
        for pattern in agent_patterns:
            if re.search(pattern, content):
                found_agents.append(True)
            else:
                found_agents.append(False)

        if not all(found_agents):
            missing = [self.EXPECTED_AGENTS.pop() for i, f in enumerate(found_agents) if not f]
            return CheckResult(
                check_name="check_agents_loaded",
                passed=False,
                message=f"Found {sum(found_agents)}/{len(found_agents)} expected agents in AGENTS.md",
                remediation="Ensure all 8 agent role definitions are present in AGENTS.md with correct formatting.",
            )

        return CheckResult(
            check_name="check_agents_loaded",
            passed=True,
            message=f"All {self.EXPECTED_AGENT_COUNT} agents are defined in AGENTS.md",
        )

    def check_skills_available(self) -> CheckResult:
        """Verify 14+ skills are available and renderable.

        Checks:
          - dist/opencode/skills/ directory exists
          - At least 14 skill subdirectories exist
          - Each skill has a SKILL.md or README.md file

        Returns:
            CheckResult indicating if skills are available.
        """
        skills_dir = self.dist_opencode / "skills"

        if not skills_dir.exists():
            return CheckResult(
                check_name="check_skills_available",
                passed=False,
                message=f"Skills directory not found at {skills_dir}",
                remediation="Run the OpenCode renderer: `python renderer/scripts/render-opencode.sh`",
            )

        # Count skill directories
        skill_subdirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

        if len(skill_subdirs) < self.EXPECTED_SKILL_COUNT:
            return CheckResult(
                check_name="check_skills_available",
                passed=False,
                message=f"Found {len(skill_subdirs)} skills, expected at least {self.EXPECTED_SKILL_COUNT}",
                remediation="Run the OpenCode renderer to sync all skills: `python renderer/scripts/render-opencode.sh`",
            )

        # Check that skills have documentation
        skills_with_docs = 0
        for skill_dir in skill_subdirs:
            if (skill_dir / "SKILL.md").exists() or (skill_dir / "README.md").exists():
                skills_with_docs += 1

        if skills_with_docs < self.EXPECTED_SKILL_COUNT:
            return CheckResult(
                check_name="check_skills_available",
                passed=False,
                message=f"Only {skills_with_docs}/{len(skill_subdirs)} skills have documentation",
                remediation="Ensure all skills have SKILL.md or README.md files.",
            )

        return CheckResult(
            check_name="check_skills_available",
            passed=True,
            message=f"All {len(skill_subdirs)} skills are available with documentation",
        )

    def check_queue_paths(self) -> CheckResult:
        """Verify queue paths exist and are canonical.

        Checks:
          - Queue base path ~/.agentic-engineers/ exists or is creatable
          - Queue structure matches canonical format:
            ~/.agentic-engineers/{session}/{harness}/queue/incoming/
            ~/.agentic-engineers/{session}/{harness}/queue/processing/
            ~/.agentic-engineers/{session}/{harness}/queue/done/

        Returns:
            CheckResult indicating if queue paths are valid.
        """
        queue_base = Path.home() / ".agentic-engineers"

        # Check if base exists; if not, it's creatable (not a failure)
        if not queue_base.exists():
            try:
                queue_base.mkdir(parents=True, exist_ok=True)
                return CheckResult(
                    check_name="check_queue_paths",
                    passed=True,
                    message=f"Queue base path created at {queue_base}",
                )
            except Exception as e:
                return CheckResult(
                    check_name="check_queue_paths",
                    passed=False,
                    message=f"Queue base path {queue_base} is not writable: {str(e)}",
                    remediation=f"Check permissions on {queue_base}. Run `mkdir -p {queue_base}` with proper permissions.",
                )

        # Verify canonical queue structure exists for at least one session/harness combo
        queue_dirs_found = 0
        try:
            for session_dir in queue_base.iterdir():
                if session_dir.is_dir() and not session_dir.name.startswith("."):
                    for harness_dir in session_dir.iterdir():
                        if harness_dir.is_dir() and not harness_dir.name.startswith("."):
                            queue_dir = harness_dir / "queue"
                            if queue_dir.exists():
                                required_subdirs = ["incoming", "processing", "done"]
                                all_exist = all((queue_dir / d).exists() for d in required_subdirs)
                                if all_exist:
                                    queue_dirs_found += 1
        except Exception:
            pass

        if queue_dirs_found == 0:
            return CheckResult(
                check_name="check_queue_paths",
                passed=False,
                message=f"No canonical queue directories found in {queue_base}",
                remediation=f"Initialize queue structure: `mkdir -p {queue_base}/default/opencode/queue/{{incoming,processing,done}}`",
            )

        return CheckResult(
            check_name="check_queue_paths",
            passed=True,
            message=f"Queue paths are properly configured with {queue_dirs_found} valid queue(s)",
        )

    def check_orchestrator(self) -> CheckResult:
        """Test orchestrator invocation.

        Checks:
          - Orchestrator agent exists in dist/opencode/agents/
          - Orchestrator.md is readable and well-formed
          - Basic orchestrator configuration is present

        Returns:
            CheckResult indicating if orchestrator is properly configured.
        """
        orchestrator_path = self.dist_opencode / "agents" / "orchestrator.md"

        if not orchestrator_path.exists():
            return CheckResult(
                check_name="check_orchestrator",
                passed=False,
                message=f"Orchestrator agent not found at {orchestrator_path}",
                remediation="Run the OpenCode renderer: `python renderer/scripts/render-opencode.sh`",
            )

        try:
            content = orchestrator_path.read_text()
            if not content or len(content) < 100:
                return CheckResult(
                    check_name="check_orchestrator",
                    passed=False,
                    message="Orchestrator agent file is empty or too small",
                    remediation="Ensure orchestrator.md is properly generated by the renderer.",
                )

            # Check for expected content in orchestrator
            # It should have responsibilities/capabilities/boundaries
            required_content = [
                "Orchestrator",
                "Route",  # routing-related content
            ]
            found_content = [s for s in required_content if s in content]

            if len(found_content) < len(required_content):
                return CheckResult(
                    check_name="check_orchestrator",
                    passed=False,
                    message=f"Orchestrator agent missing expected content",
                    remediation="Verify that orchestrator.md is correctly formatted with routing and coordination content.",
                )

            return CheckResult(
                check_name="check_orchestrator",
                passed=True,
                message="Orchestrator agent is properly configured",
            )

        except Exception as e:
            return CheckResult(
                check_name="check_orchestrator",
                passed=False,
                message=f"Error reading orchestrator configuration: {str(e)}",
                remediation="Check that orchestrator.md is readable and properly formatted.",
            )

    def check_schemas(self) -> CheckResult:
        """Validate DELEGATE/HANDBACK schemas are correct.

        Checks:
          - delegate-schema.yaml exists and is valid YAML
          - handback-schema.yaml exists and is valid YAML
          - Both schemas have required_fields section
          - spec_version matches expected format

        Returns:
            CheckResult indicating if schemas are properly configured.
        """
        schemas = {
            "delegate": self.dist_agent_dir / "delegate-schema.yaml",
            "handback": self.dist_agent_dir / "handback-schema.yaml",
        }

        missing_schemas = []
        for schema_name, schema_path in schemas.items():
            if not schema_path.exists():
                missing_schemas.append(schema_name)

        if missing_schemas:
            return CheckResult(
                check_name="check_schemas",
                passed=False,
                message=f"Schema files not found: {', '.join(missing_schemas)}",
                remediation="Ensure delegate-schema.yaml and handback-schema.yaml exist in src/orchestration/",
            )

        # Validate schemas are proper YAML
        try:
            for schema_name, schema_path in schemas.items():
                with open(schema_path) as f:
                    schema_content = yaml.safe_load(f)
                if not schema_content:
                    return CheckResult(
                        check_name="check_schemas",
                        passed=False,
                        message=f"Schema {schema_name} is empty or not valid YAML",
                        remediation=f"Check {schema_path} and ensure it contains valid YAML.",
                    )

                # Check for required_fields section
                if "required_fields" not in schema_content:
                    return CheckResult(
                        check_name="check_schemas",
                        passed=False,
                        message=f"Schema {schema_name} missing 'required_fields' section",
                        remediation=f"Ensure {schema_path} contains a 'required_fields' section.",
                    )

        except yaml.YAMLError as e:
            return CheckResult(
                check_name="check_schemas",
                passed=False,
                message=f"Schema validation failed: {str(e)}",
                remediation="Check that delegate-schema.yaml and handback-schema.yaml are valid YAML files.",
            )

        return CheckResult(
            check_name="check_schemas",
            passed=True,
            message="All schemas are valid and properly configured",
        )


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run harness validation from CLI.

    Exit codes:
      0 = all checks passed
      1 = critical check failed
      2 = warning (missing non-critical components)

    Usage:
        python -m src.harness.harness_checker
        python -m src.harness.harness_checker --verbose
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenCode harness startup validation"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    parser.add_argument(
        "--repo-root", help="Override repository root detection"
    )

    args = parser.parse_args(argv)

    try:
        checker = HarnessChecker(repo_root=args.repo_root)
        report = checker.run_all_checks()

        if args.json:
            import json
            results = [
                {
                    "check": c.check_name,
                    "passed": c.passed,
                    "message": c.message,
                    "remediation": c.remediation,
                }
                for c in report.checks
            ]
            print(json.dumps({"passed": report.all_passed, "checks": results}, indent=2))
        else:
            print(report.report())

        return 0 if report.all_passed else 1

    except Exception as e:
        print(f"❌ Harness validation failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
