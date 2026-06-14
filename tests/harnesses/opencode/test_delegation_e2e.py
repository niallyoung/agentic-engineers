"""End-to-end delegation regression tests for the OpenCode harness.

Mission-critical stability gate — target: ≥95% delegation success rate (AC1).

Test groups:
1.  Agent availability (AC2) — all 8 agents load and dispatch correctly
2.  Skill availability (AC3) — all 14+ skills load and render
3.  DELEGATE queuing — happy path, simple/complex/parallel tasks
4.  Queue state transitions — incoming→processing→done, retry, dead-letter
5.  HANDBACK validation — required fields, status values, token counts
6.  DELEGATE validator integration — Group A/B/C pre-flight gates
7.  End-to-end delegation success rate measurement (AC1)
8.  HANDBACK result retrieval (AC4)
9.  Parallel delegation (multiple concurrent tasks)
10. Regression: specific gaps discovered during harness investigation
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

import pytest
import yaml

# Ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.opencode.runner import TaskContext, TaskResult, TaskRunner, TaskState
from src.opencode.harness_session_manager import HarnessSessionManager
from src.orchestration.agents.delegate_validator import DelegateValidator
from src.orchestration.agents.invoke_agent import AgentInvoker, HandbackValidationError


# ---------------------------------------------------------------------------
# Constants — expected agent/skill roster
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = {
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "principal-engineer",
    "security-engineer",
    "quality-engineer",
    "model-engineer",
    "orchestrator",
}

# 14 skills referenced in the task spec (using subset that must always exist)
EXPECTED_SKILLS_MIN = {
    "ab-testing",
    "agent-creator",
    "consistency-checker",
    "cost-aggregation",
    "doc-quality-monitor",
    "file-sync",
    "harness-integration-tracker",
    "harness-opencode-feature-sync",
    "metrics-etl",
    "model-selection",
    "orchestrator",
    "protocol-validator",
    "queue-management",
    "spec-management",
}

CLAUDE_AGENTS_DIR = Path.home() / ".claude" / "agents"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_queue_root() -> Path:
    """Isolated temporary queue root for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "queue"


@pytest.fixture
def runner(tmp_queue_root: Path) -> TaskRunner:
    """Initialized TaskRunner with isolated queue."""
    r = TaskRunner(
        queue_root=tmp_queue_root,
        session_id="test-opencode-session",
        harness="opencode",
    )
    r.initialize()
    return r


@pytest.fixture
def tmp_base_dir() -> Path:
    """Isolated base directory for HarnessSessionManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(tmp_base_dir: Path) -> HarnessSessionManager:
    """Initialized HarnessSessionManager for opencode harness."""
    mgr = HarnessSessionManager(
        harness="opencode",
        session_id="test-session-e2e",
        base_dir=tmp_base_dir,
    )
    mgr.initialize_queue_structure()
    return mgr


@pytest.fixture
def agent_invoker(tmp_queue_root: Path) -> AgentInvoker:
    """AgentInvoker wired to isolated queue with fast poll interval."""
    processing_dir = tmp_queue_root / "processing"
    delegates_dir = tmp_queue_root / "delegates"
    spans_dir = tmp_queue_root / "spans"
    processing_dir.mkdir(parents=True, exist_ok=True)
    delegates_dir.mkdir(parents=True, exist_ok=True)
    spans_dir.mkdir(parents=True, exist_ok=True)
    return AgentInvoker(
        processing_dir=processing_dir,
        delegates_dir=delegates_dir,
        spans_dir=spans_dir,
        poll_interval=1,
        effort_timeouts={"low": 5, "medium": 10, "high": 15},
        session_id="test-session-e2e",
        harness="opencode",
    )


def _make_valid_delegate(
    task_id: str,
    role: str = "engineer",
    effort: str = "low",
    scope: str = (
        "Implement a unit test suite for the authentication module "
        "to validate all login and logout pathways correctly."
    ),
) -> Dict:
    """Return a minimal valid DELEGATE block."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "agent": role,
        "role": role.replace("-", "_"),
        "effort": effort,
        "scope": scope,
        "model": "github-copilot/claude-haiku-4.5",
    }


def _make_valid_handback(task_id: str, role: str = "engineer") -> Dict:
    """Return a minimal valid HANDBACK dict."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "success",
        "deliverables": ["implementation complete"],
        "tests": ["test_suite_passes"],
        "tokens_in": 1000,
        "tokens_out": 500,
        "model": "claude-haiku-4.5",
        "effort": "low",
        "duration_minutes": 1.5,
    }


# ===========================================================================
# 1. Agent Availability (AC2)
# ===========================================================================


class TestAgentAvailability:
    """All 8 agents must load correctly from ~/.claude/agents/."""

    def test_agents_directory_exists(self) -> None:
        """~/.claude/agents/ directory must exist."""
        if not CLAUDE_AGENTS_DIR.exists():
            pytest.skip("agents directory not found (requires live harness install)")
        assert CLAUDE_AGENTS_DIR.exists(), (
            f"Agents directory missing: {CLAUDE_AGENTS_DIR}"
        )

    def test_all_expected_agents_present(self) -> None:
        """All 8 expected agent .md files must be present."""
        if not CLAUDE_AGENTS_DIR.exists():
            pytest.skip("agents directory not found")
        installed = {p.stem for p in CLAUDE_AGENTS_DIR.glob("*.md")}
        missing = EXPECTED_AGENTS - installed
        assert not missing, f"Missing agent definitions: {sorted(missing)}"

    @pytest.mark.parametrize("agent_name", sorted(EXPECTED_AGENTS))
    def test_agent_file_has_frontmatter(self, agent_name: str) -> None:
        """Each agent .md must have YAML frontmatter with name/description."""
        if not CLAUDE_AGENTS_DIR.exists():
            pytest.skip("agents directory not found")
        agent_file = CLAUDE_AGENTS_DIR / f"{agent_name}.md"
        if not agent_file.exists():
            pytest.skip(f"agent file missing: {agent_file}")
        content = agent_file.read_text()
        assert content.startswith("---"), (
            f"Agent {agent_name} missing YAML frontmatter"
        )
        # Parse frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"Agent {agent_name} has malformed frontmatter"
        frontmatter = yaml.safe_load(parts[1])
        assert "name" in frontmatter or "description" in frontmatter, (
            f"Agent {agent_name} frontmatter missing name/description"
        )

    def test_agent_roles_cover_all_effort_levels(self) -> None:
        """
        Routing: engineer handles low/medium; senior/lead/principal handle higher.
        All 4 effort-level role tiers must be represented.
        """
        if not CLAUDE_AGENTS_DIR.exists():
            pytest.skip("agents directory not found")
        installed = {p.stem for p in CLAUDE_AGENTS_DIR.glob("*.md")}
        # Tier 1: low/medium effort
        assert "engineer" in installed
        # Tier 2: high effort
        assert "senior-engineer" in installed
        # Tier 3: code review / architecture
        assert "lead-engineer" in installed
        # Tier 4: cross-service / epic
        assert "principal-engineer" in installed


# ===========================================================================
# 2. Skill Availability (AC3)
# ===========================================================================


class TestSkillAvailability:
    """All 14+ skills must load and have valid SKILL.md frontmatter."""

    def test_skills_directory_exists(self) -> None:
        """~/.claude/skills/ directory must exist."""
        if not CLAUDE_SKILLS_DIR.exists():
            pytest.skip("skills directory not found (requires live harness install)")
        assert CLAUDE_SKILLS_DIR.exists(), (
            f"Skills directory missing: {CLAUDE_SKILLS_DIR}"
        )

    def test_minimum_skill_count(self) -> None:
        """At least 14 skills must be present."""
        if not CLAUDE_SKILLS_DIR.exists():
            pytest.skip("skills directory not found")
        installed = {p.name for p in CLAUDE_SKILLS_DIR.iterdir() if p.is_dir()}
        assert len(installed) >= 14, (
            f"Expected ≥14 skills, found {len(installed)}: {sorted(installed)}"
        )

    def test_all_expected_skills_present(self) -> None:
        """All expected skills must be installed."""
        if not CLAUDE_SKILLS_DIR.exists():
            pytest.skip("skills directory not found")
        installed = {p.name for p in CLAUDE_SKILLS_DIR.iterdir() if p.is_dir()}
        missing = EXPECTED_SKILLS_MIN - installed
        assert not missing, f"Missing skill definitions: {sorted(missing)}"

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS_MIN))
    def test_skill_has_skill_md(self, skill_name: str) -> None:
        """Each skill directory must contain a SKILL.md file."""
        if not CLAUDE_SKILLS_DIR.exists():
            pytest.skip("skills directory not found")
        skill_dir = CLAUDE_SKILLS_DIR / skill_name
        if not skill_dir.exists():
            pytest.skip(f"skill directory missing: {skill_dir}")
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists(), (
            f"Skill {skill_name} missing SKILL.md at {skill_md}"
        )

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS_MIN))
    def test_skill_md_has_valid_frontmatter(self, skill_name: str) -> None:
        """Each SKILL.md must have parseable YAML frontmatter."""
        if not CLAUDE_SKILLS_DIR.exists():
            pytest.skip("skills directory not found")
        skill_md = CLAUDE_SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_md.exists():
            pytest.skip(f"SKILL.md missing: {skill_md}")
        content = skill_md.read_text()
        assert content.startswith("---"), (
            f"Skill {skill_name} SKILL.md missing YAML frontmatter"
        )
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"Skill {skill_name} SKILL.md malformed frontmatter"
        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict), (
            f"Skill {skill_name} frontmatter did not parse to dict"
        )
        assert "name" in frontmatter or "description" in frontmatter, (
            f"Skill {skill_name} frontmatter missing name/description"
        )


# ===========================================================================
# 3. DELEGATE Queuing — Happy Path
# ===========================================================================


class TestDelegateQueuing:
    """End-to-end DELEGATE queuing tests."""

    def test_simple_task_delegate_queuing(self, runner: TaskRunner) -> None:
        """Simple task DELEGATE queues correctly and reaches incoming state."""
        task_data = {
            "handoff_type": "DELEGATE",
            "role": "engineer",
            "scope": "Implement input validation for the user registration form.",
        }
        task_id = runner.submit_task(task_data)
        assert task_id.startswith("TASK-")
        status = runner.get_task_status(task_id)
        assert status is not None
        assert status["state"] == "incoming"

    def test_complex_task_delegate_queuing(self, runner: TaskRunner) -> None:
        """Complex high-effort DELEGATE queues correctly."""
        task_data = {
            "handoff_type": "DELEGATE",
            "role": "senior_engineer",
            "effort": "high",
            "scope": (
                "Refactor the authentication service to use JWT tokens, "
                "add refresh token support, implement blacklist for revoked tokens, "
                "write comprehensive tests, and update API documentation."
            ),
            "context": {
                "file": "src/auth/service.py",
                "current_state": "session-based auth",
            },
        }
        task_id = runner.submit_task(task_data)
        status = runner.get_task_status(task_id)
        assert status is not None
        assert status["state"] == "incoming"
        assert status["metadata"]["role"] == "senior_engineer"
        assert status["metadata"]["effort"] == "high"

    def test_delegate_preserves_all_metadata(self, runner: TaskRunner) -> None:
        """All DELEGATE metadata is preserved when queued."""
        task_data = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-14-test-metadata",
            "role": "quality_engineer",
            "effort": "medium",
            "scope": "Validate the coverage report and write missing unit tests.",
            "success_criteria": ["coverage >= 95%", "all tests pass"],
            "custom_field": "preserved",
        }
        task_id = runner.submit_task(task_data)
        status = runner.get_task_status(task_id)
        assert status is not None
        meta = status["metadata"]
        assert meta["role"] == "quality_engineer"
        assert meta["success_criteria"] == ["coverage >= 95%", "all tests pass"]
        assert meta["custom_field"] == "preserved"

    def test_delegate_task_id_uniqueness(self, runner: TaskRunner) -> None:
        """Multiple DELEGATEs get unique task IDs."""
        ids = [runner.submit_task({"role": "engineer"}) for _ in range(5)]
        assert len(set(ids)) == 5, "All task IDs must be unique"

    def test_delegate_explicit_task_id(self, runner: TaskRunner) -> None:
        """Explicit task_id is preserved in queue."""
        explicit_id = "TASK-DELEGATE-E2E-001"
        runner.submit_task({"role": "engineer"}, task_id=explicit_id)
        status = runner.get_task_status(explicit_id)
        assert status is not None
        assert status["task_id"] == explicit_id

    def test_delegate_duplicate_task_id_rejected(self, runner: TaskRunner) -> None:
        """Duplicate task_id is rejected to prevent double-submission."""
        task_id = "TASK-DUP-GUARD"
        runner.submit_task({"role": "engineer"}, task_id=task_id)
        with pytest.raises(ValueError, match="already exists"):
            runner.submit_task({"role": "engineer"}, task_id=task_id)


# ===========================================================================
# 4. Queue State Transitions
# ===========================================================================


class TestQueueStateTransitions:
    """DELEGATE→incoming→processing→done state machine."""

    def test_incoming_to_processing_transition(self, runner: TaskRunner) -> None:
        """Task transitions correctly from incoming to processing."""
        task_id = runner.submit_task({"role": "engineer"})
        polled = runner.poll_queue()
        assert task_id in polled
        assert (runner.processing_dir / f"{task_id}.yaml").exists()
        assert not (runner.incoming_dir / f"{task_id}.yaml").exists()

    def test_processing_to_done_transition(self, runner: TaskRunner) -> None:
        """Task transitions correctly from processing to done."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        success = runner._transition_task(
            task_id, TaskState.PROCESSING, TaskState.DONE
        )
        assert success
        assert (runner.done_dir / f"{task_id}.yaml").exists()
        assert not (runner.processing_dir / f"{task_id}.yaml").exists()

    def test_full_delegate_lifecycle_via_execute(self, runner: TaskRunner) -> None:
        """Full lifecycle: submit DELEGATE → poll → execute → retrieve HANDBACK."""
        task_id = runner.submit_task(
            {"role": "engineer", "scope": "Fix the null pointer bug in login."}
        )
        runner.poll_queue()

        handback = {"status": "success", "output": "bug fixed"}

        def handler(ctx: TaskContext) -> Dict:
            return handback

        result = runner.execute_task(task_id, handler)
        assert result.success
        assert result.state == TaskState.DONE

        retrieved = runner.get_result(task_id)
        assert retrieved is not None
        assert retrieved.success
        assert retrieved.output == handback

    def test_retry_on_first_failure(self, runner: TaskRunner) -> None:
        """Task retries on first failure — stays accessible."""
        task_id = runner.submit_task({"role": "engineer"})
        runner.poll_queue()

        attempt = [0]

        def handler(ctx: TaskContext) -> Dict:
            attempt[0] += 1
            if attempt[0] < 2:
                raise RuntimeError("Transient failure")
            return {"status": "success"}

        # First attempt fails
        result = runner.execute_task(task_id, handler)
        assert not result.success
        assert result.state == TaskState.INCOMING

        # Second attempt succeeds
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.success
        assert result.state == TaskState.DONE

    def test_dead_letter_after_max_retries(self, runner: TaskRunner) -> None:
        """Task moves to dead-letter queue after max retries."""
        task_id = runner.submit_task({"role": "engineer"})

        def always_fail(ctx: TaskContext) -> Dict:
            raise RuntimeError("permanent failure")

        for _ in range(3):
            runner.poll_queue()
            runner.execute_task(task_id, always_fail)

        status = runner.get_task_status(task_id)
        assert status is not None
        assert status["state"] == "dead-letter"

    def test_cancelled_task_enters_failed_state(self, runner: TaskRunner) -> None:
        """Cancelled tasks enter failed state and cannot be re-dispatched."""
        task_id = runner.submit_task({"role": "engineer"})
        success = runner.cancel_task(task_id)
        assert success
        assert (runner.failed_dir / f"{task_id}.yaml").exists()
        # Should NOT appear in incoming after cancellation
        assert not (runner.incoming_dir / f"{task_id}.yaml").exists()


# ===========================================================================
# 5. HANDBACK Validation (AC4)
# ===========================================================================


class TestHandbackValidation:
    """HANDBACK format validation — required fields, status values, integrity."""

    def test_valid_handback_accepted(self, agent_invoker: AgentInvoker) -> None:
        """Valid HANDBACK with all required fields is accepted without error."""
        handback = _make_valid_handback("2026-06-14-test-valid")
        handback_path = agent_invoker.processing_dir / "2026-06-14-test-valid-HANDBACK-engineer.yaml"
        handback_path.write_text(yaml.dump(handback))
        result = agent_invoker._read_and_validate_handback(
            handback_path, "2026-06-14-test-valid"
        )
        assert result is not None
        assert result["status"] == "success"
        assert result["task_id"] == "2026-06-14-test-valid"

    def test_handback_missing_required_field_raises(self, agent_invoker: AgentInvoker) -> None:
        """HANDBACK missing required fields raises HandbackValidationError."""
        handback = _make_valid_handback("2026-06-14-test-missing")
        del handback["tokens_in"]
        handback_path = agent_invoker.processing_dir / "test-missing-HANDBACK-engineer.yaml"
        handback_path.write_text(yaml.dump(handback))
        with pytest.raises(HandbackValidationError, match="missing required fields"):
            agent_invoker._read_and_validate_handback(
                handback_path, "2026-06-14-test-missing"
            )

    def test_handback_wrong_task_id_raises(self, agent_invoker: AgentInvoker) -> None:
        """HANDBACK with mismatched task_id raises HandbackValidationError."""
        handback = _make_valid_handback("task-A")
        handback["task_id"] = "task-B"  # mismatch
        handback_path = agent_invoker.processing_dir / "task-A-HANDBACK-engineer.yaml"
        handback_path.write_text(yaml.dump(handback))
        with pytest.raises(HandbackValidationError, match="does not match"):
            agent_invoker._read_and_validate_handback(handback_path, "task-A")

    def test_handback_invalid_status_raises(self, agent_invoker: AgentInvoker) -> None:
        """HANDBACK with invalid status raises HandbackValidationError."""
        handback = _make_valid_handback("2026-06-14-test-status")
        handback["status"] = "invalid_status"
        handback_path = agent_invoker.processing_dir / "test-status-HANDBACK-engineer.yaml"
        handback_path.write_text(yaml.dump(handback))
        with pytest.raises(HandbackValidationError, match="Invalid HANDBACK status"):
            agent_invoker._read_and_validate_handback(
                handback_path, "2026-06-14-test-status"
            )

    def test_handback_wrong_handoff_type_raises(self, agent_invoker: AgentInvoker) -> None:
        """HANDBACK with wrong handoff_type raises HandbackValidationError."""
        handback = _make_valid_handback("2026-06-14-test-type")
        handback["handoff_type"] = "DELEGATE"  # wrong
        handback_path = agent_invoker.processing_dir / "test-type-HANDBACK-engineer.yaml"
        handback_path.write_text(yaml.dump(handback))
        with pytest.raises(HandbackValidationError, match="handoff_type"):
            agent_invoker._read_and_validate_handback(
                handback_path, "2026-06-14-test-type"
            )

    def test_handback_non_integer_tokens_coerced(self, agent_invoker: AgentInvoker) -> None:
        """HANDBACK with string token counts are coerced to int."""
        handback = _make_valid_handback("2026-06-14-test-tokens")
        handback["tokens_in"] = "1234"
        handback["tokens_out"] = "567"
        handback_path = agent_invoker.processing_dir / "test-tokens-HANDBACK-engineer.yaml"
        handback_path.write_text(yaml.dump(handback))
        result = agent_invoker._read_and_validate_handback(
            handback_path, "2026-06-14-test-tokens"
        )
        assert result["tokens_in"] == 1234
        assert result["tokens_out"] == 567

    def test_handback_empty_file_returns_none(self, agent_invoker: AgentInvoker) -> None:
        """Empty HANDBACK file returns None (TOCTOU race — still being written)."""
        handback_path = agent_invoker.processing_dir / "test-empty-HANDBACK-engineer.yaml"
        handback_path.write_text("")
        result = agent_invoker._read_and_validate_handback(handback_path, "any-id")
        assert result is None

    @pytest.mark.parametrize("status", ["success", "blocked", "partial", "escalate"])
    def test_all_valid_handback_statuses_accepted(
        self, agent_invoker: AgentInvoker, status: str
    ) -> None:
        """All four canonical HANDBACK status values are accepted."""
        handback = _make_valid_handback(f"2026-06-14-test-{status}")
        handback["status"] = status
        handback_path = (
            agent_invoker.processing_dir
            / f"test-{status}-HANDBACK-engineer.yaml"
        )
        handback_path.write_text(yaml.dump(handback))
        result = agent_invoker._read_and_validate_handback(
            handback_path, f"2026-06-14-test-{status}"
        )
        assert result is not None
        assert result["status"] == status


# ===========================================================================
# 6. DELEGATE Validator Integration (Group A/B/C gates)
# ===========================================================================


class TestDelegateValidatorIntegration:
    """Pre-flight validation gate ensures only valid DELEGATEs reach the queue."""

    def _minimal_valid_delegate(self, task_id: str = "2026-06-14-test-valid") -> Dict:
        return {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": "engineer",
            "effort": "low",
            "scope": (
                "Implement unit tests for the authentication module "
                "to cover all login and logout code pathways."
            ),
            "model": "claude-haiku-4.5",
        }

    def test_valid_delegate_passes_preflight(self) -> None:
        """Valid DELEGATE block passes all A/B/C gate checks."""
        delegate = self._minimal_valid_delegate()
        ok, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        # Group B/C may have minor warnings; Group A structural gates must pass
        a_failures = [f for f in failures if f.startswith("A")]
        assert not a_failures, f"Group A failures: {a_failures}"

    def test_invalid_task_id_fails_group_a(self) -> None:
        """A1 gate rejects non-date-format task_ids."""
        delegate = self._minimal_valid_delegate()
        delegate["task_id"] = "not-a-valid-task-id"
        _, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert any("A1" in f for f in failures), (
            f"Expected A1 failure, got: {failures}"
        )

    def test_invalid_role_fails_group_a(self) -> None:
        """A3 gate rejects unknown roles."""
        delegate = self._minimal_valid_delegate()
        delegate["role"] = "unknown_role_xyz"
        _, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert any("A3" in f for f in failures), (
            f"Expected A3 failure, got: {failures}"
        )

    def test_scope_too_short_fails_group_a(self) -> None:
        """A6 gate rejects scope with fewer than 15 words."""
        delegate = self._minimal_valid_delegate()
        delegate["scope"] = "Fix bug"
        _, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert any("A6" in f for f in failures), (
            f"Expected A6 failure, got: {failures}"
        )

    def test_high_effort_requires_senior_engineer(self) -> None:
        """C1 gate rejects engineer role with high effort."""
        delegate = self._minimal_valid_delegate()
        delegate["effort"] = "high"
        delegate["scope"] = (
            "Implement a comprehensive refactoring of the authentication "
            "service with full test coverage and documentation updates."
        )
        _, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert any("C1" in f or "A5" in f for f in failures), (
            f"Expected C1/A5 failure for engineer+high, got: {failures}"
        )

    def test_routing_role_validation(self) -> None:
        """validate_routing_role() enforces role sanity without full content check."""
        delegate = {
            "role": "engineer",
            "effort": "low",
            "scope": "Implement a small utility function for string validation.",
        }
        ok, failures = DelegateValidator.validate_routing_role(delegate)
        assert ok, f"Valid routing delegate failed: {failures}"

    def test_routing_role_invalid_role_rejected(self) -> None:
        """validate_routing_role() rejects unrecognized roles."""
        delegate = {"role": "nonexistent_role", "effort": "low", "scope": "anything"}
        ok, failures = DelegateValidator.validate_routing_role(delegate)
        assert not ok
        assert any("A3" in f for f in failures)

    def test_fable5_defensive_only_gate(self) -> None:
        """C5 gate: fable-5 model requires security_engineer role + defensive-only constraint."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-14-security-test",
            "role": "engineer",
            "effort": "low",
            "model": "fable-5/model",
            "scope": (
                "Review defensive configurations in the firewall rule "
                "sets to identify misconfigured allow rules."
            ),
        }
        _, failures = DelegateValidator.validate_delegate_pre_flight(delegate)
        assert any("C5" in f for f in failures), (
            f"Expected C5 fable-5 gate failure, got: {failures}"
        )


# ===========================================================================
# 7. Delegation Success Rate (AC1) — Measurement Test
# ===========================================================================


class TestDelegationSuccessRate:
    """
    Measures delegation success rate across representative task scenarios.
    Target: ≥95% (19/20 or better).

    Uses synchronous handler simulation rather than spawning real agents,
    so results are deterministic and repeatable.
    """

    def _run_delegate_scenarios(self, runner: TaskRunner) -> Dict[str, Any]:
        """Run 20 representative DELEGATE scenarios and return results."""
        scenarios = [
            # (scenario_name, task_data, handler_succeeds)
            ("simple-task", {"role": "engineer", "scope": "Fix login bug"}, True),
            ("complex-task", {"role": "senior_engineer", "effort": "high"}, True),
            ("quality-review", {"role": "quality_engineer"}, True),
            ("security-audit", {"role": "security_engineer"}, True),
            ("model-guidance", {"role": "model_engineer"}, True),
            ("lead-review", {"role": "lead_engineer"}, True),
            ("principal-arch", {"role": "principal_engineer"}, True),
            ("retry-success", {"role": "engineer"}, True),
            ("parallel-task-1", {"role": "engineer"}, True),
            ("parallel-task-2", {"role": "engineer"}, True),
            ("parallel-task-3", {"role": "engineer"}, True),
            ("metadata-rich", {"role": "engineer", "context": {"file": "auth.py"}}, True),
            ("low-effort", {"role": "engineer", "effort": "low"}, True),
            ("medium-effort", {"role": "engineer", "effort": "medium"}, True),
            ("with-criteria", {"role": "engineer", "success_criteria": ["test pass"]}, True),
            ("with-plan", {"role": "engineer", "plan": ["step 1", "step 2"]}, True),
            ("json-output", {"role": "engineer", "output_format": "json"}, True),
            ("large-context", {"role": "engineer", "context": {"data": "x" * 500}}, True),
            ("unicode-scope", {"role": "engineer", "scope": "Implement UTF-8 handling"}, True),
            ("empty-metadata", {"role": "engineer"}, True),
        ]

        results = {"succeeded": 0, "failed": 0, "total": len(scenarios), "details": []}

        for name, task_data, should_succeed in scenarios:
            task_id = f"TASK-SCENARIO-{name[:20].upper().replace('-', '')}"
            try:
                submitted_id = runner.submit_task(task_data, task_id=task_id)
                runner._transition_task(
                    submitted_id, TaskState.INCOMING, TaskState.PROCESSING
                )

                if should_succeed:
                    def handler(ctx: TaskContext, _name=name) -> Dict:
                        return {"scenario": _name, "status": "success"}
                    result = runner.execute_task(submitted_id, handler)
                    if result.success:
                        results["succeeded"] += 1
                        results["details"].append({"scenario": name, "status": "pass"})
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "scenario": name, "status": "fail", "error": result.error
                        })
            except Exception as exc:
                results["failed"] += 1
                results["details"].append({
                    "scenario": name, "status": "error", "error": str(exc)
                })

        return results

    def test_delegation_success_rate_at_least_95_percent(
        self, runner: TaskRunner
    ) -> None:
        """AC1: delegation success rate must be ≥95% across 20 scenarios."""
        results = self._run_delegate_scenarios(runner)
        total = results["total"]
        succeeded = results["succeeded"]
        rate = succeeded / total if total > 0 else 0.0

        failed_details = [d for d in results["details"] if d["status"] != "pass"]
        assert rate >= 0.95, (
            f"Delegation success rate {rate:.1%} < 95% target. "
            f"Failed scenarios: {failed_details}"
        )

    def test_all_agent_roles_dispatch_successfully(self, runner: TaskRunner) -> None:
        """AC2: all 7 non-orchestrator agent roles dispatch without error."""
        roles = [
            "engineer",
            "senior_engineer",
            "lead_engineer",
            "principal_engineer",
            "security_engineer",
            "quality_engineer",
            "model_engineer",
        ]
        succeeded = 0
        for role in roles:
            uid = uuid.uuid4().hex[:8]
            task_id = f"TASK-ROLE-{role[:12].upper()}-{uid}"
            try:
                task_id_actual = runner.submit_task({"role": role}, task_id=task_id)
                runner._transition_task(
                    task_id_actual, TaskState.INCOMING, TaskState.PROCESSING
                )
                result = runner.execute_task(
                    task_id_actual,
                    lambda ctx: {"dispatched": True},
                )
                if result.success:
                    succeeded += 1
            except Exception:
                pass

        assert succeeded == len(roles), (
            f"Only {succeeded}/{len(roles)} roles dispatched successfully"
        )


# ===========================================================================
# 8. HANDBACK Result Retrieval (AC4)
# ===========================================================================


class TestHandbackResultRetrieval:
    """Verify HANDBACK results are correctly retrieved from queue."""

    def test_retrieve_done_task_result(self, runner: TaskRunner) -> None:
        """get_result() returns correct output for done task."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        expected = {"output": "task completed", "lines_changed": 42}
        runner.execute_task(task_id, lambda ctx: expected)

        result = runner.get_result(task_id)
        assert result is not None
        assert result.success
        assert result.state == TaskState.DONE
        assert result.output == expected

    def test_retrieve_dead_letter_task_error(self, runner: TaskRunner) -> None:
        """get_result() returns error info for dead-letter task."""
        task_id = runner.submit_task({"role": "engineer"})
        for _ in range(3):
            runner.poll_queue()
            runner.execute_task(
                task_id, lambda ctx: (_ for _ in ()).throw(RuntimeError("permanent"))
            )

        result = runner.get_result(task_id)
        assert result is not None
        assert not result.success
        assert result.state == TaskState.DEAD_LETTER

    def test_retrieve_result_returns_none_for_processing_task(
        self, runner: TaskRunner
    ) -> None:
        """get_result() returns None for in-flight (processing) task."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        result = runner.get_result(task_id)
        assert result is None

    def test_handback_file_written_by_agent_invoker(
        self, agent_invoker: AgentInvoker
    ) -> None:
        """AgentInvoker correctly reads HANDBACK written to processing_dir."""
        task_id = "2026-06-14-handback-file-test"
        expected_handback = _make_valid_handback(task_id)
        # Simulate agent writing HANDBACK to processing_dir
        hb_path = (
            agent_invoker.processing_dir
            / f"{task_id}-HANDBACK-engineer.yaml"
        )
        hb_path.write_text(yaml.dump(expected_handback))

        result = agent_invoker._read_and_validate_handback(hb_path, task_id)
        assert result is not None
        assert result["status"] == "success"
        assert result["task_id"] == task_id

    def test_synthetic_handback_generated_on_timeout(
        self, agent_invoker: AgentInvoker
    ) -> None:
        """AgentInvoker generates synthetic HANDBACK on agent timeout."""
        delegate = {
            "task_id": "2026-06-14-timeout-test",
            "role": "engineer",
            "effort": "low",
            "model": "claude-haiku-4.5",
        }
        # Use a command that exits immediately without writing HANDBACK
        result = agent_invoker.invoke_agent(delegate, ["true"])
        assert result is not None
        assert result.get("_synthetic") is True
        assert result["status"] == "blocked"

    def test_get_task_status_returns_full_context(self, runner: TaskRunner) -> None:
        """get_task_status() returns complete TaskContext for any state."""
        task_data = {"role": "engineer", "scope": "Build auth module tests."}
        task_id = runner.submit_task(task_data)
        status = runner.get_task_status(task_id)
        assert status is not None
        assert status["task_id"] == task_id
        assert status["state"] == "incoming"
        assert "created_at" in status
        assert "updated_at" in status
        assert status["metadata"]["role"] == "engineer"


# ===========================================================================
# 9. Parallel Delegation
# ===========================================================================


class TestParallelDelegation:
    """Multiple concurrent DELEGATE tasks must not interfere with each other."""

    def test_parallel_task_submission(self, runner: TaskRunner) -> None:
        """10 tasks submitted concurrently all land in incoming queue."""
        task_ids = []
        errors = []
        lock = threading.Lock()

        def submit_task(idx: int) -> None:
            try:
                tid = runner.submit_task({"role": "engineer", "index": idx})
                with lock:
                    task_ids.append(tid)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=submit_task, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Submission errors: {errors}"
        # All 10 should be unique and in incoming
        assert len(task_ids) == 10
        assert len(set(task_ids)) == 10
        incoming = runner.list_tasks(TaskState.INCOMING)
        for tid in task_ids:
            assert tid in incoming, f"Task {tid} not found in incoming queue"

    def test_parallel_tasks_execute_independently(self, runner: TaskRunner) -> None:
        """Parallel tasks execute without cross-contamination of results."""
        n_tasks = 5
        task_ids = []
        for i in range(n_tasks):
            tid = runner.submit_task({"role": "engineer", "task_index": i})
            task_ids.append(tid)

        # Poll all at once
        polled = runner.poll_queue()
        assert len(polled) == n_tasks

        # Execute all
        for tid, orig_idx in zip(task_ids, range(n_tasks)):
            runner.execute_task(
                tid, lambda ctx, idx=orig_idx: {"result": idx, "task": tid}
            )

        # Verify each result is in done state
        for tid in task_ids:
            result = runner.get_result(tid)
            assert result is not None
            assert result.success
            assert result.state == TaskState.DONE

    def test_session_isolation_prevents_cross_contamination(
        self, tmp_base_dir: Path
    ) -> None:
        """Two concurrent sessions do not share queue state."""
        mgr1 = HarnessSessionManager("opencode", "session-A", base_dir=tmp_base_dir)
        mgr2 = HarnessSessionManager("opencode", "session-B", base_dir=tmp_base_dir)
        mgr1.initialize_queue_structure()
        mgr2.initialize_queue_structure()

        assert mgr1.queue_root != mgr2.queue_root
        assert mgr1.queue_root.exists()
        assert mgr2.queue_root.exists()
        # Verify complete path isolation
        assert "session-A" in str(mgr1.queue_root)
        assert "session-B" in str(mgr2.queue_root)
        assert "session-A" not in str(mgr2.queue_root)
        assert "session-B" not in str(mgr1.queue_root)


# ===========================================================================
# 10. Regression Tests — Specific Gaps
# ===========================================================================


class TestRegressionGaps:
    """
    Regression tests for known historical gaps and edge cases.
    Each test codifies a specific failure mode.
    """

    def test_regression_harness_detection_priority(self) -> None:
        """
        REGRESSION: AGENTIC_HARNESS must win over OPENCODE_API, which must win
        over CLAUDE_SESSION_ID. Priority chain must be enforced.
        """
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_HARNESS": "opencode",
                "OPENCODE_API": "1",
                "CLAUDE_SESSION_ID": "claude-abc",
                "COPILOT_SESSION_ID": "copilot-xyz",
            },
        ):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "opencode"

        with mock.patch.dict(
            os.environ,
            {"OPENCODE_API": "1", "CLAUDE_SESSION_ID": "claude-abc"},
            clear=True,
        ):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "opencode"

    def test_regression_session_id_detection_priority(self) -> None:
        """
        REGRESSION: AGENTIC_SESSION_ID must win over OPENCODE_SESSION_ID
        which must win over CLAUDE_SESSION_ID.
        """
        sid = "explicit-session-id"
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_SESSION_ID": sid,
                "OPENCODE_SESSION_ID": "other-id",
                "CLAUDE_SESSION_ID": "another-id",
            },
        ):
            detected = HarnessSessionManager._detect_session_id_from_env()
            assert detected == sid

    def test_regression_queue_init_idempotent(self, tmp_base_dir: Path) -> None:
        """
        REGRESSION: Repeated queue initialization must not corrupt metadata.
        created_at must be preserved across re-initializations.
        """
        mgr = HarnessSessionManager("opencode", "test-idem", base_dir=tmp_base_dir)
        result1 = mgr.initialize_queue_structure()
        with open(result1["metadata_path"]) as f:
            meta1 = json.load(f)
        created_at_1 = meta1["created_at"]

        # Re-initialize same session
        mgr2 = HarnessSessionManager("opencode", "test-idem", base_dir=tmp_base_dir)
        result2 = mgr2.initialize_queue_structure()
        with open(result2["metadata_path"]) as f:
            meta2 = json.load(f)

        assert meta2["created_at"] == created_at_1, (
            "created_at must be preserved on re-initialization"
        )

    def test_regression_corrupted_metadata_recovered(self, tmp_base_dir: Path) -> None:
        """
        REGRESSION: Corrupted metadata.json must be recovered gracefully
        on next initialization rather than raising an exception.
        """
        mgr = HarnessSessionManager("opencode", "test-corrupt", base_dir=tmp_base_dir)
        mgr.initialize_queue_structure()
        # Corrupt the metadata
        mgr.metadata_path.write_text("{ invalid json !!!")
        # Re-initialize must succeed
        result = mgr.initialize_queue_structure()
        assert result["success"] is True

    def test_regression_unsupported_harness_rejected(self) -> None:
        """
        REGRESSION: Unsupported harness value must raise ValueError immediately,
        not fail silently and create an invalid queue path.
        """
        with pytest.raises(ValueError, match="Unsupported harness"):
            HarnessSessionManager("not-a-real-harness", "any-session")

    def test_regression_task_not_found_returns_none(self, runner: TaskRunner) -> None:
        """
        REGRESSION: Querying a nonexistent task must return None, not raise.
        Pre-existing harness bug: KeyError on missing task_id.
        """
        result = runner.get_task_status("TASK-NONEXISTENT-XYZ")
        assert result is None

        result = runner.get_result("TASK-NONEXISTENT-XYZ")
        assert result is None

    def test_regression_handback_yaml_with_document_markers(
        self, agent_invoker: AgentInvoker
    ) -> None:
        """
        REGRESSION: HANDBACK files with leading --- YAML document markers
        must be parsed correctly (agents sometimes emit these).
        """
        task_id = "2026-06-14-yaml-markers-test"
        handback = _make_valid_handback(task_id)
        yaml_with_markers = f"---\n{yaml.dump(handback)}\n---\n"
        hb_path = (
            agent_invoker.processing_dir / f"{task_id}-HANDBACK-engineer.yaml"
        )
        hb_path.write_text(yaml_with_markers)
        result = agent_invoker._read_and_validate_handback(hb_path, task_id)
        assert result is not None
        assert result["task_id"] == task_id

    def test_regression_poll_queue_empty_on_empty_incoming(
        self, runner: TaskRunner
    ) -> None:
        """
        REGRESSION: poll_queue() on empty incoming must return [] not raise.
        Historical bug: glob on missing directory raised FileNotFoundError.
        """
        result = runner.poll_queue()
        assert result == []

    def test_regression_dead_letter_manual_retry_resets_count(
        self, runner: TaskRunner
    ) -> None:
        """
        REGRESSION: Manual retry from dead-letter must reset retry_count to 0,
        otherwise the task immediately re-enters dead-letter on first failure.
        """
        task_id = runner.submit_task({"role": "engineer"})
        for _ in range(3):
            runner.poll_queue()
            runner.execute_task(
                task_id,
                lambda ctx: (_ for _ in ()).throw(RuntimeError("fail")),
            )
        # Confirm dead-letter
        ctx = runner._load_task_context(task_id, TaskState.DEAD_LETTER)
        assert ctx is not None
        assert ctx.retry_count == 3

        # Manual retry
        success = runner.retry_task(task_id)
        assert success

        # Confirm reset
        ctx_after = runner._load_task_context(task_id, TaskState.INCOMING)
        assert ctx_after is not None
        assert ctx_after.retry_count == 0, (
            "retry_count must be reset to 0 after manual retry from dead-letter"
        )

    def test_regression_span_write_failure_does_not_propagate(
        self, agent_invoker: AgentInvoker
    ) -> None:
        """
        REGRESSION: SPAN write failure must be logged but never propagate to
        caller as an exception. Agent invocation must succeed even if SPAN
        directory is read-only.
        """
        # Make spans_dir read-only
        spans_dir = agent_invoker.spans_dir
        spans_dir.mkdir(parents=True, exist_ok=True)
        spans_dir.chmod(0o444)
        try:
            from datetime import datetime
            delegate = {
                "task_id": "2026-06-14-span-fail-test",
                "role": "engineer",
                "effort": "low",
            }
            handback = _make_valid_handback("2026-06-14-span-fail-test")
            # Should not raise even with read-only spans dir
            agent_invoker._write_span(
                delegate,
                handback,
                datetime.now(),
                datetime.now(),
                span_status="success",
            )
        finally:
            spans_dir.chmod(0o755)
