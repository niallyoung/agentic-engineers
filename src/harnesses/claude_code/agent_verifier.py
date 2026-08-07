"""
Agent Availability Verifier for Claude Code Harness

Systematically verifies all 8 agents render/load correctly in the Claude Code
framework by:
  - Enumerating all agents from src/agents/*.md files
  - Validating agent definitions (role, model, effort, thinking_mode)
  - Testing agent instantiation
  - Testing agent routing (model selection)
  - Generating a compatibility report

Usage:
    from src.harnesses.claude_code.agent_verifier import AgentVerifier
    verifier = AgentVerifier()
    report = verifier.verify_all_agents()
    print(report)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
import json
import hashlib
from datetime import datetime


@dataclass
class AgentDefinition:
    """Agent definition metadata."""
    name: str
    role: str
    model: str
    effort: Optional[str] = None
    thinking_mode: Optional[str] = None
    description: Optional[str] = None
    file_path: Optional[Path] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, handling Path objects."""
        result = asdict(self)
        if self.file_path:
            result['file_path'] = str(self.file_path)
        return result


@dataclass
class VerificationResult:
    """Result of a single agent verification."""
    agent_name: str
    status: str  # "PASS" | "FAIL" | "WARN"
    model: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CompatibilityReport:
    """Full agent compatibility report."""
    timestamp: str
    total_agents: int
    passing: int
    failing: int
    warnings: int
    results: list[VerificationResult] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'total_agents': self.total_agents,
            'passing': self.passing,
            'failing': self.failing,
            'warnings': self.warnings,
            'results': [r.to_dict() for r in self.results],
        }


# Known valid model names in canonical format (source)
KNOWN_MODELS = {
    "claude-haiku-4.5",
    "claude-haiku-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.5",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-opus-4.8",
    # Claude Code harness aliases (no dots)
    "haiku",
    "sonnet",
    "opus",
}

# Expected agent count
EXPECTED_AGENT_COUNT = 8

# Expected agents by name
EXPECTED_AGENTS = {
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "quality-engineer",
    "model-engineer",
    "principal-engineer",
    "security-engineer",
}


class AgentVerifier:
    """Main verifier class for agent availability and compatibility."""
    
    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """Initialize the verifier.
        
        Args:
            repo_root: Path to repository root. Defaults to current working directory.
        """
        if repo_root is None:
            repo_root = Path.cwd()
        
        self.repo_root = repo_root
        self.agents_dir = repo_root / "src" / "agents"
        self._agents: list[AgentDefinition] = []
        self._verification_results: list[VerificationResult] = []
    
    def enumerate_agents(self) -> list[AgentDefinition]:
        """Enumerate all agents from src/agents/*.md files.
        
        Returns:
            List of AgentDefinition objects.
            
        Raises:
            FileNotFoundError: If agents directory doesn't exist.
        """
        if not self.agents_dir.exists():
            raise FileNotFoundError(f"Agents directory not found: {self.agents_dir}")
        
        agents = []
        agent_files = sorted(self.agents_dir.glob("*-agent.md"))
        
        for agent_file in agent_files:
            definition = self._parse_agent_file(agent_file)
            if definition:
                agents.append(definition)
        
        self._agents = agents
        return agents
    
    def _parse_agent_file(self, file_path: Path) -> Optional[AgentDefinition]:
        """Parse a single agent markdown file.
        
        Args:
            file_path: Path to agent markdown file.
            
        Returns:
            AgentDefinition if successful, None otherwise.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract frontmatter (YAML between --- markers)
            frontmatter = self._extract_frontmatter(content)
            if not frontmatter:
                return None
            
            # Parse agent name from filename (e.g., engineer-agent.md -> engineer)
            file_name = file_path.stem  # removes .md
            if not file_name.endswith("-agent"):
                return None
            
            # Use name from frontmatter if available, else derive from filename
            agent_name = frontmatter.get("name", file_name.replace("-agent", ""))
            
            definition = AgentDefinition(
                name=agent_name,
                role=agent_name,  # role is same as name in this framework
                model=frontmatter.get("model", ""),
                effort=frontmatter.get("effort"),
                thinking_mode=frontmatter.get("thinking_mode"),
                description=frontmatter.get("description"),
                file_path=file_path,
            )
            
            return definition
        except Exception as e:
            # Log parsing errors but don't crash
            return None
    
    def _extract_frontmatter(self, content: str) -> dict[str, str]:
        """Extract YAML frontmatter from markdown.
        
        Args:
            content: Markdown file content.
            
        Returns:
            Dictionary of frontmatter fields.
        """
        if not content.startswith("---"):
            return {}
        
        # Find closing --- marker
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return {}
        
        # Extract and parse YAML-like frontmatter (simple key: value parsing)
        frontmatter_text = content[3:end_idx].strip()
        result = {}
        
        for line in frontmatter_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Remove inline comments
                if "#" in value:
                    value = value.split("#")[0].strip()
                result[key] = value
        
        return result
    
    def verify_enumeration(self) -> VerificationResult:
        """Verify all agents are enumerated correctly.
        
        Returns:
            VerificationResult for enumeration check.
        """
        agents_found = {agent.name for agent in self._agents}
        missing = EXPECTED_AGENTS - agents_found
        extra = agents_found - EXPECTED_AGENTS
        
        result = VerificationResult(
            agent_name="enumeration",
            status="PASS",
            metadata={
                "agents_found": len(agents_found),
                "expected_count": EXPECTED_AGENT_COUNT,
            },
        )
        
        if len(agents_found) != EXPECTED_AGENT_COUNT:
            result.status = "FAIL"
            result.errors.append(
                f"Expected {EXPECTED_AGENT_COUNT} agents, found {len(agents_found)}"
            )
        
        if missing:
            result.status = "FAIL"
            result.errors.append(f"Missing agents: {', '.join(sorted(missing))}")
        
        if extra:
            result.status = "WARN"
            result.warnings.append(f"Extra agents: {', '.join(sorted(extra))}")
        
        return result
    
    def verify_agent_definition(self, agent: AgentDefinition) -> VerificationResult:
        """Verify a single agent definition.
        
        Args:
            agent: Agent definition to verify.
            
        Returns:
            VerificationResult for the agent.
        """
        result = VerificationResult(
            agent_name=agent.name,
            status="PASS",
            model=agent.model,
            metadata=agent.to_dict(),
        )
        
        # Check required fields
        if not agent.name:
            result.status = "FAIL"
            result.errors.append("Missing or empty 'name' field")
        
        if not agent.model:
            result.status = "FAIL"
            result.errors.append("Missing or empty 'model' field")
        elif agent.model not in KNOWN_MODELS:
            result.status = "FAIL"
            result.errors.append(
                f"Unknown model '{agent.model}'. Valid models: {', '.join(sorted(KNOWN_MODELS))}"
            )
        
        # Only set to WARN if not already FAIL
        if not agent.description and result.status != "FAIL":
            result.status = "WARN"
            result.warnings.append("Missing 'description' field")
        elif not agent.description:
            result.warnings.append("Missing 'description' field")
        
        # Verify file path exists
        if agent.file_path and not agent.file_path.exists():
            result.status = "FAIL"
            result.errors.append(f"Agent file not found: {agent.file_path}")
        
        return result
    
    def verify_agent_instantiation(self, agent: AgentDefinition) -> VerificationResult:
        """Verify agent can be instantiated (mock instantiation).
        
        Args:
            agent: Agent definition to test.
            
        Returns:
            VerificationResult for instantiation test.
        """
        result = VerificationResult(
            agent_name=f"{agent.name}_instantiation",
            status="PASS",
            model=agent.model,
        )
        
        try:
            # Simulate instantiation by checking all required fields are present
            # and have valid types/formats
            
            if not agent.name or not isinstance(agent.name, str):
                raise ValueError(f"Invalid name: {agent.name}")
            
            if not agent.model or not isinstance(agent.model, str):
                raise ValueError(f"Invalid model: {agent.model}")
            
            if agent.model not in KNOWN_MODELS:
                raise ValueError(f"Unknown model: {agent.model}")
            
            # Check file can be read
            if agent.file_path:
                content = agent.file_path.read_text(encoding="utf-8")
                if not content:
                    raise ValueError("Agent file is empty")
            
            result.metadata["instantiable"] = True
            
        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Instantiation failed: {str(e)}")
            result.metadata["instantiable"] = False
        
        return result
    
    def verify_routing(self, agent: AgentDefinition) -> VerificationResult:
        """Verify agent routing logic (model selection).
        
        Args:
            agent: Agent definition to test.
            
        Returns:
            VerificationResult for routing test.
        """
        result = VerificationResult(
            agent_name=f"{agent.name}_routing",
            status="PASS",
            model=agent.model,
        )
        
        # Define expected model routing
        expected_routing = {
            "orchestrator": "claude-haiku-4.5",
            "engineer": "claude-haiku-4.5",
            "senior-engineer": "claude-sonnet-4.5",
            "lead-engineer": "claude-sonnet-4.6",
            "quality-engineer": "claude-sonnet-4.6",
            "model-engineer": "claude-sonnet-4.5",
            "principal-engineer": "claude-opus-4.6",
            "security-engineer": "claude-opus-4.8",
        }
        
        if agent.name not in expected_routing:
            result.status = "WARN"
            result.warnings.append(f"Agent '{agent.name}' not in expected routing table")
            return result
        
        expected_model = expected_routing[agent.name]
        if agent.model != expected_model:
            result.status = "FAIL"
            result.errors.append(
                f"Model mismatch for '{agent.name}': expected '{expected_model}', got '{agent.model}'"
            )
        
        result.metadata["expected_model"] = expected_model
        result.metadata["actual_model"] = agent.model
        
        return result
    
    def verify_all_agents(
        self,
        generate_report: bool = True,
    ) -> CompatibilityReport:
        """Run full verification on all agents.
        
        Args:
            generate_report: Whether to generate a full report.
            
        Returns:
            CompatibilityReport with all verification results.
        """
        # Enumerate agents
        self.enumerate_agents()
        
        # Run verification checks
        results = []
        
        # 1. Enumeration check
        enum_result = self.verify_enumeration()
        results.append(enum_result)
        
        # 2. Definition checks
        for agent in self._agents:
            def_result = self.verify_agent_definition(agent)
            results.append(def_result)
        
        # 3. Instantiation checks
        for agent in self._agents:
            inst_result = self.verify_agent_instantiation(agent)
            results.append(inst_result)
        
        # 4. Routing checks
        for agent in self._agents:
            route_result = self.verify_routing(agent)
            results.append(route_result)
        
        # Count results
        passing = sum(1 for r in results if r.status == "PASS")
        failing = sum(1 for r in results if r.status == "FAIL")
        warnings = sum(1 for r in results if r.status == "WARN")
        
        report = CompatibilityReport(
            timestamp=datetime.utcnow().isoformat(),
            total_agents=len(self._agents),
            passing=passing,
            failing=failing,
            warnings=warnings,
            results=results,
        )
        
        self._verification_results = results
        
        return report
    
    def generate_json_report(self, output_path: Optional[Path] = None) -> str:
        """Generate JSON report of verification results.
        
        Args:
            output_path: Optional path to write JSON report to.
            
        Returns:
            JSON string of the report.
        """
        report = self.verify_all_agents()
        report_dict = report.to_dict()
        report_json = json.dumps(report_dict, indent=2)
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_json, encoding="utf-8")
        
        return report_json
    
    def get_verification_cache_key(self) -> str:
        """Generate a cache key for the current verification state.
        
        Returns:
            SHA256 hash of agent files.
        """
        agent_files = sorted(self.agents_dir.glob("*-agent.md"))
        hasher = hashlib.sha256()
        
        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            hasher.update(content.encode("utf-8"))
        
        return hasher.hexdigest()
    
    def print_report(self, report: Optional[CompatibilityReport] = None) -> None:
        """Print a human-readable verification report.
        
        Args:
            report: CompatibilityReport to print. Uses verify_all_agents() if None.
        """
        if report is None:
            report = self.verify_all_agents()
        
        print("\n" + "=" * 80)
        print("AGENT AVAILABILITY VERIFICATION REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Agents: {report.total_agents}")
        print(f"Passing: {report.passing} | Failing: {report.failing} | Warnings: {report.warnings}")
        print("-" * 80)
        
        for result in report.results:
            status_symbol = "✅" if result.status == "PASS" else ("❌" if result.status == "FAIL" else "⚠️")
            print(f"{status_symbol} {result.agent_name:30} [{result.status}]")
            
            if result.model:
                print(f"   Model: {result.model}")
            
            for error in result.errors:
                print(f"   ERROR: {error}")
            
            for warning in result.warnings:
                print(f"   WARNING: {warning}")
        
        print("=" * 80)
        if report.failing == 0:
            print("✅ All agents verified successfully!")
        else:
            print(f"❌ {report.failing} agent(s) failed verification")
        print("=" * 80 + "\n")


def main() -> int:
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify agent availability and compatibility in Claude Code harness"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write JSON report to file",
    )
    parser.add_argument(
        "--cache-key",
        action="store_true",
        help="Print cache key and exit",
    )
    
    args = parser.parse_args()
    
    repo_root = args.repo_root or Path.cwd()
    verifier = AgentVerifier(repo_root=repo_root)
    
    if args.cache_key:
        print(verifier.get_verification_cache_key())
        return 0
    
    report = verifier.verify_all_agents()
    verifier.print_report(report)
    
    if args.json:
        verifier.generate_json_report(args.json)
        print(f"JSON report written to {args.json}")
    
    return 0 if report.failing == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
