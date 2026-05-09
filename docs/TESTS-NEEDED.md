# Tests Needed — This Session's Work

**Date:** 2026-05-09  
**Context:** Pre-implementation gate. These tests must be written (RED phase) before any implementation work begins.  
**Format:** Each entry is a concrete, implementable test specification.

---

## Critical Finding: AGENTS.md Duplication

Before writing any tests, this must be resolved:

- `src/docs/AGENTS.md` — 4,688 bytes (old, partial version from `538fad8`)
- `docs/AGENTS.md` — 27,184 bytes (full, current canonical version)

**Two copies of AGENTS.md exist in the repository.** Tests must target the canonical location and verify the duplicate is removed.

---

## 1. AGENTS.md Location Tests

**File to create:** `tests/test_agents_md_location.py`  
**Why:** Commit `538fad8` moved AGENTS.md without writing any tests. The routing agent embeds the decision tree from AGENTS.md in source code — if the file moves again, that divergence won't be caught automatically.

### Tests to write (RED first):

```python
"""
Tests for AGENTS.md canonical location and integrity.

RED phase: all tests below should FAIL until implementation is correct.
"""
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

class TestAgentsMdCanonicalLocation:
    """AGENTS.md must exist at exactly one canonical location."""

    def test_canonical_agents_md_exists(self):
        """docs/AGENTS.md must exist."""
        assert (REPO_ROOT / "docs" / "AGENTS.md").exists()

    def test_no_duplicate_agents_md_in_src_docs(self):
        """src/docs/AGENTS.md must NOT exist — only one canonical copy."""
        assert not (REPO_ROOT / "src" / "docs" / "AGENTS.md").exists(), \
            "Duplicate AGENTS.md found at src/docs/AGENTS.md — remove it"

    def test_agents_md_not_at_repo_root(self):
        """AGENTS.md must not still be at repo root (old location)."""
        assert not (REPO_ROOT / "AGENTS.md").exists(), \
            "AGENTS.md still at repo root — should be at docs/AGENTS.md"

    def test_agents_md_has_minimum_content(self):
        """docs/AGENTS.md must be the full version (> 10KB)."""
        agents_md = REPO_ROOT / "docs" / "AGENTS.md"
        assert agents_md.stat().st_size > 10_000, \
            f"docs/AGENTS.md is suspiciously small ({agents_md.stat().st_size} bytes) — may be wrong version"

    def test_agents_md_contains_routing_decision_tree(self):
        """docs/AGENTS.md must contain the routing decision tree sections."""
        content = (REPO_ROOT / "docs" / "AGENTS.md").read_text()
        assert "Security Engineer" in content
        assert "Principal Engineer" in content
        assert "Lead Engineer" in content
        assert "Senior Engineer" in content
        assert "Engineer" in content

    def test_agents_md_contains_role_definitions(self):
        """docs/AGENTS.md must define all 8 roles."""
        content = (REPO_ROOT / "docs" / "AGENTS.md").read_text()
        required_roles = [
            "Orchestrator",
            "Security Engineer",
            "Principal Engineer",
            "Lead Engineer",
            "Senior Engineer",
            "Engineer",
            "Quality Engineer",
        ]
        for role in required_roles:
            assert role in content, f"Role '{role}' not found in AGENTS.md"


class TestAgentsMdReferences:
    """Code that references AGENTS.md must use the canonical path."""

    def test_routing_agent_logic_matches_agents_md(self):
        """routing_agent.py decision tree roles match those defined in docs/AGENTS.md."""
        from src.orchestration.agents.routing_agent import RoutingAgent
        content = (REPO_ROOT / "docs" / "AGENTS.md").read_text()
        # The routing agent hard-codes role names — verify they appear in AGENTS.md
        agent = RoutingAgent()
        # Route a security task and verify the role appears in AGENTS.md
        result = agent.route_task({
            "task_id": "test-001",
            "scope": "Review authentication code for vulnerabilities",
            "role": "any",
            "effort": "M"
        })
        assert result.get("assigned_role") in content, \
            f"Routing returned role '{result.get('assigned_role')}' not defined in AGENTS.md"

    def test_models_yaml_at_canonical_location(self):
        """models.yaml must exist at src/config/models.yaml."""
        assert (REPO_ROOT / "src" / "config" / "models.yaml").exists()

    def test_models_yaml_not_at_repo_root(self):
        """models.yaml must not still be at repo root (old location)."""
        assert not (REPO_ROOT / "models.yaml").exists()
```

---

## 2. Routing Logic Regression Tests

**File to create:** `tests/test_routing_regression.py`  
**Why:** The AGENTS.md move could silently break routing if the decision tree in routing_agent.py diverges from docs/AGENTS.md. These tests pin the routing behaviour.

### Tests to write (RED first):

```python
"""
Routing regression tests — pins the routing decision tree behaviour.
All tests must FAIL before routing_agent.py correctly implements docs/AGENTS.md.
"""
import pytest
from src.orchestration.agents.routing_agent import RoutingAgent

class TestRoutingRegressionSecurityTasks:
    def setup_method(self):
        self.agent = RoutingAgent()

    def test_authentication_task_routes_to_security_engineer(self):
        result = self.agent.route_task({
            "task_id": "sec-001", "scope": "Implement JWT authentication", "effort": "M"
        })
        assert result["assigned_role"] == "Security Engineer"

    def test_cryptography_task_routes_to_security_engineer(self):
        result = self.agent.route_task({
            "task_id": "sec-002", "scope": "Add AES-256 encryption to data store", "effort": "L"
        })
        assert result["assigned_role"] == "Security Engineer"

class TestRoutingRegressionArchitectureTasks:
    def setup_method(self):
        self.agent = RoutingAgent()

    def test_multi_service_task_routes_to_principal_engineer(self):
        result = self.agent.route_task({
            "task_id": "arch-001", "scope": "Redesign event bus across all services", "effort": "XL"
        })
        assert result["assigned_role"] == "Principal Engineer"

class TestRoutingRegressionEngineerTasks:
    def setup_method(self):
        self.agent = RoutingAgent()

    def test_well_scoped_task_with_plan_routes_to_engineer(self):
        result = self.agent.route_task({
            "task_id": "eng-001",
            "scope": "Add retry logic to HTTP client",
            "effort": "S",
            "plan": "1. Wrap requests in try/except 2. Add exponential backoff 3. Test"
        })
        assert result["assigned_role"] == "Engineer"

    def test_complex_task_without_plan_routes_to_senior_engineer(self):
        result = self.agent.route_task({
            "task_id": "eng-002",
            "scope": "Refactor the entire queue system for better performance",
            "effort": "XL"
        })
        assert result["assigned_role"] == "Senior Engineer"
```

---

## 3. Dead Reference Tests

**File:** Add to `tests/test_agents_md_location.py`  
**Why:** Cleanup commit `3c94429` deleted files that tests still reference. Need a test that catches dead references.

### Tests to write (RED first):

```python
class TestNoDeadFileReferences:
    """Tests that files referenced in tests and docs actually exist."""

    def test_bin_entrypoint_exists_or_test_is_removed(self):
        """
        bin/run-automation-controller.sh was deleted in commit 3c94429
        but tests/test_automation_integration.py still references it.
        Either restore the script or remove/update the test.
        This test documents the gap until it is resolved.
        """
        entrypoint = REPO_ROOT / "bin" / "run-automation-controller.sh"
        # This test is intentionally asserting the file exists.
        # If the file is permanently deleted, update test_automation_integration.py
        # to remove or replace the TestEntrypointScript test class, then delete this test.
        assert entrypoint.exists(), (
            "bin/run-automation-controller.sh not found. "
            "Either restore it or remove TestEntrypointScript from test_automation_integration.py"
        )

    def test_pre_commit_hook_exists(self):
        """
        Pre-commit hook should exist to enforce TDD compliance.
        Required by TDD-SKILL.md enforcement section.
        """
        # Use dynamic path (not hardcoded /home/user/...)
        git_root = REPO_ROOT  # tests/ is one level below repo root
        hook_path = git_root / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists(), (
            f"Pre-commit hook not found at {hook_path}. "
            "Implement the hook per docs/TDD-SKILL.md enforcement section."
        )
```

---

## 4. TDD Skill Self-Tests

**File to create:** `tests/test_tdd_skill_docs.py`  
**Why:** The TDD skill documents themselves must be verifiable. A skill that can't be tested is a suggestion, not a standard.

### Tests to write (RED first):

```python
"""
Tests that verify TDD skill documentation exists and is complete.
"""
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS = REPO_ROOT / "docs"

class TestTDDSkillDocumentsExist:
    def test_tdd_skill_md_exists(self):
        assert (DOCS / "TDD-SKILL.md").exists()

    def test_tdd_checklist_md_exists(self):
        assert (DOCS / "TDD-CHECKLIST.md").exists()

    def test_current_tdd_gaps_md_exists(self):
        assert (DOCS / "CURRENT-TDD-GAPS.md").exists()

    def test_tdd_roadmap_md_exists(self):
        assert (DOCS / "TDD-ROADMAP.md").exists()

    def test_tests_needed_md_exists(self):
        assert (DOCS / "TESTS-NEEDED.md").exists()

class TestTDDSkillDocumentContent:
    def test_skill_md_contains_red_green_refactor(self):
        content = (DOCS / "TDD-SKILL.md").read_text()
        assert "RED" in content
        assert "GREEN" in content
        assert "REFACTOR" in content

    def test_checklist_md_has_all_phases(self):
        content = (DOCS / "TDD-CHECKLIST.md").read_text()
        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content

    def test_skill_md_defines_coverage_requirement(self):
        content = (DOCS / "TDD-SKILL.md").read_text()
        assert "85%" in content, "TDD skill must state minimum coverage requirement"

    def test_skill_md_defines_handback_block(self):
        content = (DOCS / "TDD-SKILL.md").read_text()
        assert "tdd_compliance" in content, "TDD skill must define tdd_compliance HANDBACK block"
```

---

## 5. Decision Engine Contract Tests

**Why:** 6 tests currently fail because the decision engine thresholds changed. Before fixing the implementation, capture the *correct* contract as tests.

### Tests to write (RED first — after agreeing on correct thresholds):

```python
"""
Decision Engine contract tests.
These capture the agreed business rules, independent of implementation.
Write these BEFORE touching decision_engine.py.
"""
class TestDecisionEngineContractProceed:
    """Tasks meeting ALL quality criteria should proceed."""

    def test_score_above_threshold_proceeds(self, decision_engine):
        """A score of 90 with all criteria met must produce action=proceed."""
        result = decision_engine.evaluate({
            "quality_score": 90,
            "security_clear": True,
            "tests_pass": True,
            "coverage_above_threshold": True
        })
        assert result["action"] == "proceed"

    def test_score_at_exactly_85_proceeds(self, decision_engine):
        """Score of exactly 85 (the threshold) must produce action=proceed."""
        result = decision_engine.evaluate({
            "quality_score": 85,
            "security_clear": True,
            "tests_pass": True,
            "coverage_above_threshold": True
        })
        assert result["action"] == "proceed"  # Boundary: 85 is pass

    def test_score_below_85_reworks(self, decision_engine):
        """Score of 84 must produce action=rework."""
        result = decision_engine.evaluate({
            "quality_score": 84,
            "security_clear": True,
            "tests_pass": True,
            "coverage_above_threshold": True
        })
        assert result["action"] == "rework"

class TestDecisionEngineContractEscalate:
    """Security failures always escalate regardless of quality score."""

    def test_security_failure_escalates_even_with_high_score(self, decision_engine):
        result = decision_engine.evaluate({
            "quality_score": 95,
            "security_clear": False,
            "tests_pass": True,
            "coverage_above_threshold": True
        })
        assert result["action"] == "escalate"
```

---

## 6. Import Path Regression Tests

**Why:** `model_resolver.py` had its import path broken by the restructure (fixed in `77d1fe0`), but there's no test preventing it from breaking again.

**Add to:** `tests/test_model_resolver.py`

```python
class TestImportPaths:
    """Ensure all imports resolve correctly from their canonical locations."""

    def test_model_resolver_importable_from_src(self):
        """ModelResolver must be importable from src.orchestration.agents."""
        from src.orchestration.agents.model_resolver import ModelResolver
        assert ModelResolver is not None

    def test_routing_agent_importable(self):
        from src.orchestration.agents.routing_agent import RoutingAgent
        assert RoutingAgent is not None

    def test_quality_validator_importable(self):
        from src.orchestration.agents.quality_validator import QualityValidator
        assert QualityValidator is not None

    def test_orchestrator_importable(self):
        from src.orchestration.agents.orchestrator import OrchestratorAgent
        assert OrchestratorAgent is not None
```

---

## Implementation Order

Tests must be written in this order (each building on the previous):

1. `tests/test_tdd_skill_docs.py` — Verify this design phase produced its deliverables (**write now**, RED)
2. `tests/test_agents_md_location.py` — Pin AGENTS.md location before any moves (**write now**, RED)
3. `tests/test_routing_regression.py` — Regression guard for routing logic (**write before any routing changes**)
4. Decision engine contract tests — **write before fixing** `test_decision_engine.py` failures
5. Import path regression tests — **add to** `tests/test_model_resolver.py` before any refactoring
6. All other P1/P2 test files — per TDD-ROADMAP.md sprint plan

---

## Acceptance: When Is This Done?

This document is superseded when:
- [ ] All tests listed above exist and pass
- [ ] 0 currently-failing tests remain
- [ ] Coverage ≥ 85% for all P0/P1 modules
- [ ] CI pipeline enforces coverage gate
- [ ] Pre-commit hook is installed and tested
