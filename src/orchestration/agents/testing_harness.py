"""
Testing Harness - Run 10 test scenarios from QUALITY-GATE-TEST-FRAMEWORK.md

Each scenario validates Quality Gate decision (PROCEED vs ESCALATE) against
expected outcomes. Tests cover clean commits, security issues, test failures,
metrics degradation, config drift, and spec drift types A-D.
"""

from implementations import create_agent
from artifact_manager import ArtifactManager
from datetime import datetime
import hashlib


class TestScenario:
    """Single test scenario."""

    def __init__(self, name: str, description: str, expected_decision: str):
        self.name = name
        self.description = description
        self.expected_decision = expected_decision
        self.passed = False
        self.actual_decision = None
        self.details = {}

    def run(self, qg_agent):
        """Execute Quality Gate on this scenario's DELEGATE block."""
        delegate = self._build_delegate()
        result = qg_agent.execute(delegate)

        self.actual_decision = result.get('decision', 'UNKNOWN')
        self.passed = (self.actual_decision == self.expected_decision)
        self.details = result

        return self.passed

    def _build_delegate(self) -> dict:
        """Build DELEGATE block for this scenario."""
        return {
            "handoff_type": "DELEGATE",
            "task_id": self._task_id(),
            "role": "quality_gate_orchestrator",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": self.description
        }

    def _task_id(self) -> str:
        """Generate task ID for this scenario."""
        date = datetime.now().strftime("%Y-%m-%d")
        slug = self.name.lower().replace(" ", "-")
        hash_suffix = hashlib.md5(self.name.encode()).hexdigest()[:6]
        return f"{date}-{slug}-{hash_suffix}"

    def report(self) -> str:
        """Format test result."""
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.name:30s} | Expected: {self.expected_decision:8s} | Actual: {self.actual_decision:8s}"


def build_test_scenarios():
    """Create all 10 test scenarios."""
    return [
        TestScenario(
            "Scenario 1: Clean Commit",
            "Clean commit with all tests passing, metrics green, no issues",
            "PROCEED"
        ),
        TestScenario(
            "Scenario 2: Security Issue",
            "Commit detected with hardcoded credentials in config file",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 3: Test Failure",
            "Commit with failing unit tests; coverage dropped below threshold",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 4: Metrics Degradation",
            "Commit showing p99 latency increase >20%, error rate spike",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 5: Config Drift",
            "Commit modified environment variable assignment but old value still referenced",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 6: Spec Drift TYPE_A",
            "Commit deleted feature documented in spec without deprecation",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 7: Spec Drift TYPE_B",
            "Commit added feature not documented in spec",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 8: Spec Drift TYPE_C",
            "Commit modified implementation of feature; spec and code now mismatch",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 9: Spec Drift TYPE_D",
            "Commit made breaking change to API endpoint without deprecation period",
            "ESCALATE"
        ),
        TestScenario(
            "Scenario 10: Mixed Issues",
            "Commit with test failure + spec drift TYPE_B + config issue",
            "ESCALATE"
        ),
    ]


def run_tests():
    """Execute all 10 test scenarios."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  Quality Gate Testing Harness - 10 Test Scenarios                ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Setup
    scenarios = build_test_scenarios()
    qg_agent = create_agent("quality_gate_orchestrator")
    artifacts = ArtifactManager()

    passed_count = 0
    escalated_count = 0

    # Run all scenarios
    print("\nRunning scenarios...\n")
    for scenario in scenarios:
        scenario.run(qg_agent)
        print(scenario.report())

        if scenario.passed:
            passed_count += 1

        # Record artifacts
        task_id = scenario._task_id()
        artifacts.write_delegate(task_id, scenario._build_delegate())
        artifacts.write_handback(task_id, scenario.details)

        if scenario.actual_decision == "ESCALATE":
            escalated_count += 1

    # Summary
    total = len(scenarios)
    pass_rate = (passed_count / total) * 100

    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║  Test Results                                                      ║
╚═══════════════════════════════════════════════════════════════════╝

Total Scenarios:    {total}
Passed:             {passed_count}
Failed:             {total - passed_count}
Pass Rate:          {pass_rate:.1f}%

Expected PROCEED:   {sum(1 for s in scenarios if s.expected_decision == 'PROCEED')}
Expected ESCALATE:  {sum(1 for s in scenarios if s.expected_decision == 'ESCALATE')}
Actual PROCEED:     {total - escalated_count}
Actual ESCALATE:    {escalated_count}

Quality Gates Target:
  - 0% false positives on clean commits (Scenario 1)
  - <2% false negatives on escalable issues (Scenarios 2-10)
  - <30s latency per Quality Gate execution
    """)

    return passed_count == total


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
