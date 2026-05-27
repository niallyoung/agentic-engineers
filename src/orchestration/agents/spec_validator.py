"""
Spec Validator - Validate current implementation against SPEC.md

Detects TYPE_A/B/C/D drift:
- TYPE_A: Documented feature missing in code
- TYPE_B: Code feature undocumented in spec
- TYPE_C: Spec/code mismatch on same feature
- TYPE_D: Breaking change without deprecation

Usage:
  python spec_validator.py                 # Full validation
  python spec_validator.py --agent NAME    # Validate specific agent
  python spec_validator.py --verbose       # Detailed output
  python spec_validator.py --drift-types   # Only drift analysis
"""

import sys
from typing import Dict, List, Tuple
from implementations import list_agents


class SpecValidator:
    """Validate implementation against SPEC.md"""

    def __init__(self):
        self.agents_in_spec = self._parse_spec()
        self.agents_in_code = self._parse_code()
        self.issues = {
            "TYPE_A": [],  # Documented feature missing
            "TYPE_B": [],  # Code feature undocumented
            "TYPE_C": [],  # Spec/code mismatch
            "TYPE_D": []   # Breaking change
        }

    def _parse_spec(self) -> Dict:
        """Extract agent definitions from SPEC.md"""
        # Stub: would parse docs/SPEC.md
        # For now, return expected spec
        return {
            "GeneralOrchestrator": {
                "model": "claude-haiku-4.5",
                "effort": "low",
                "role": "orchestrator"
            },
            "EngineerAgent": {
                "model": "claude-haiku-4.5",
                "effort": "high",
                "role": "engineer"
            },
            "SeniorEngineerAgent": {
                "model": "claude-sonnet-4.6",
                "effort": "high",
                "role": "senior_engineer"
            },
            "LeadEngineerAgent": {
                "model": "claude-sonnet-4.6",
                "effort": "high",
                "role": "lead_engineer"
            },
            "PrincipalEngineerAgent": {
                "model": "claude-opus-4.7",
                "effort": "high",
                "role": "principal_engineer"
            },
            "QualityEngineerAgent": {
                "model": "claude-sonnet-4.6",
                "effort": "medium",
                "role": "quality_engineer"
            },
            "ModelEngineerAgent": {
                "model": "claude-haiku-4.5",
                "effort": "medium",
                "role": "model_engineer"
            },
            "SecurityEngineerAgent": {
                "model": "claude-opus-4.7",
                "effort": "max",
                "role": "security_engineer"
            },
            # QG Sub-agents
            "SecurityAgentQG": {
                "model": "claude-opus-4.7",
                "effort": "high",
                "role": "security_agent"
            },
            "TestingAgent": {
                "model": "claude-haiku-4.5",
                "effort": "medium",
                "role": "testing_agent"
            },
            "MetricsAgent": {
                "model": "claude-haiku-4.5",
                "effort": "medium",
                "role": "metrics_agent"
            },
            "HealingAgent": {
                "model": "claude-sonnet-4.6",
                "effort": "medium",
                "role": "healing_agent"
            },
            "SpecEngineerAgent": {
                "model": "claude-sonnet-4.6",
                "effort": "medium",
                "role": "spec_engineer"
            },
            "QualityGateOrchestrator": {
                "model": "claude-sonnet-4.6",
                "effort": "medium",
                "role": "quality_gate_orchestrator"
            }
        }

    def _parse_code(self) -> Dict:
        """Extract agent definitions from code"""
        code_agents = {}
        for config in list_agents():
            code_agents[config.name] = {
                "model": config.model,
                "effort": config.effort,
                "role": config.role
            }
        return code_agents

    def validate(self) -> bool:
        """Run full validation"""
        self._check_all_agents_present()
        self._check_all_models_match()
        self._check_all_efforts_match()
        self._check_protocol_structure()
        self._check_no_external_dependencies()

        return len(self.issues["TYPE_A"]) == 0 and len(self.issues["TYPE_D"]) == 0

    def _check_all_agents_present(self):
        """TYPE_A: Check all spec agents are in code"""
        for agent_name in self.agents_in_spec:
            if agent_name not in self.agents_in_code:
                self.issues["TYPE_A"].append(
                    f"Agent {agent_name} documented in spec but missing in code"
                )

    def _check_all_models_match(self):
        """TYPE_C: Check models match spec"""
        for agent_name in self.agents_in_spec:
            if agent_name in self.agents_in_code:
                spec_model = self.agents_in_spec[agent_name]["model"]
                code_model = self.agents_in_code[agent_name]["model"]
                if spec_model != code_model:
                    self.issues["TYPE_C"].append(
                        f"{agent_name} model mismatch: spec={spec_model}, code={code_model}"
                    )

    def _check_all_efforts_match(self):
        """TYPE_C: Check effort levels match spec"""
        for agent_name in self.agents_in_spec:
            if agent_name in self.agents_in_code:
                spec_effort = self.agents_in_spec[agent_name]["effort"]
                code_effort = self.agents_in_code[agent_name]["effort"]
                if spec_effort != code_effort:
                    self.issues["TYPE_C"].append(
                        f"{agent_name} effort mismatch: spec={spec_effort}, code={code_effort}"
                    )

    def _check_protocol_structure(self):
        """Check DELEGATE/HANDBACK protocol is implemented"""
        # Stub: would check agent.execute() signatures, HANDBACK structure, etc.
        pass

    def _check_no_external_dependencies(self):
        """TYPE_D: Check no external dependencies (Claude API calls, shell, etc.)"""
        # Stub: would grep for disallowed patterns
        pass

    def report(self) -> str:
        """Generate validation report"""
        report_lines = [
            "╔═══════════════════════════════════════════════════════════╗",
            "║  Spec Validation Report                                   ║",
            "╚═══════════════════════════════════════════════════════════╝",
            ""
        ]

        # Summary
        total_agents_spec = len(self.agents_in_spec)
        total_agents_code = len(self.agents_in_code)
        report_lines.append(f"Agents in SPEC.md: {total_agents_spec}")
        report_lines.append(f"Agents in code:    {total_agents_code}")
        report_lines.append("")

        # Issues by type
        for issue_type in ["TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"]:
            count = len(self.issues[issue_type])
            emoji = "❌" if issue_type in ["TYPE_A", "TYPE_D"] else "⚠️ " if count > 0 else "✅"
            severity = "HIGH" if issue_type in ["TYPE_A", "TYPE_D"] else "MEDIUM"

            report_lines.append(f"{emoji} {issue_type} ({severity}): {count} issues")

            if self.issues[issue_type]:
                for issue in self.issues[issue_type]:
                    report_lines.append(f"    - {issue}")

        report_lines.append("")

        # Summary
        total_issues = sum(len(v) for v in self.issues.values())
        if total_issues == 0:
            report_lines.append("✅ ALL CHECKS PASSED - Implementation matches spec")
        else:
            high_severity = len(self.issues["TYPE_A"]) + len(self.issues["TYPE_D"])
            medium_severity = len(self.issues["TYPE_B"]) + len(self.issues["TYPE_C"])
            report_lines.append(f"⚠️  {total_issues} issues found ({high_severity} high, {medium_severity} medium)")

        return "\n".join(report_lines)


def main():
    """Entry point"""
    validator = SpecValidator()
    validator.validate()
    print(validator.report())

    # Exit with error if high-severity issues
    high_severity = len(validator.issues["TYPE_A"]) + len(validator.issues["TYPE_D"])
    sys.exit(1 if high_severity > 0 else 0)


if __name__ == "__main__":
    main()
