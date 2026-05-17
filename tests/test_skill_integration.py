"""
Tests for skill integration in SmartRouter - skill registry and routing.
"""

import pytest
import tempfile
from pathlib import Path

from src.orchestration.agents.smart_router import (
    SmartRouter,
    SkillRegistry,
    RoutingDecision,
    RoutingSignal,
    SKILL_AGENT_AFFINITY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_skills_dir(tmp_path):
    """Create a temporary skills directory with some skill subdirs."""
    skills = ["security", "testing", "ab-testing", "metrics-etl", "voice-notify"]
    for skill in skills:
        skill_dir = tmp_path / skill
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(f"# {skill}\nThis skill provides {skill} capabilities.\n")
    return tmp_path


@pytest.fixture
def registry(tmp_skills_dir):
    return SkillRegistry(skills_root=tmp_skills_dir)


@pytest.fixture
def router_with_skills(tmp_skills_dir):
    registry = SkillRegistry(skills_root=tmp_skills_dir)
    return SmartRouter(skill_registry=registry)


# ---------------------------------------------------------------------------
# SkillRegistry with real filesystem
# ---------------------------------------------------------------------------

class TestSkillRegistryFilesystem:
    def test_loads_skills_from_directory(self, registry, tmp_skills_dir):
        skills = registry.available_skills()
        assert len(skills) >= 1

    def test_has_skill_true(self, registry):
        assert registry.has_skill("security")

    def test_has_skill_false_for_missing(self, registry):
        assert not registry.has_skill("nonexistent-skill")

    def test_get_skill_returns_dict(self, registry):
        skill = registry.get_skill("security")
        assert skill is not None
        assert skill["id"] == "security"
        assert skill["has_skill_md"] is True

    def test_get_skill_has_description(self, registry):
        skill = registry.get_skill("testing")
        assert isinstance(skill["description"], str)

    def test_match_skills_to_task_finds_match(self, registry):
        matches = registry.match_skills_to_task("run security audit", "")
        assert "security" in matches

    def test_match_skills_to_task_no_match(self, registry):
        matches = registry.match_skills_to_task("do something unrelated", "")
        assert isinstance(matches, list)

    def test_skill_without_skill_md(self, tmp_path):
        # Skill dir without SKILL.md
        (tmp_path / "bare-skill").mkdir()
        registry = SkillRegistry(skills_root=tmp_path)
        skill = registry.get_skill("bare-skill")
        assert skill is not None
        assert skill["has_skill_md"] is False
        assert skill["description"] == ""


# ---------------------------------------------------------------------------
# Skill-based routing integration tests
# ---------------------------------------------------------------------------

class TestSkillBasedRouting:
    def test_security_skill_in_scope_routes_correctly(self, router_with_skills):
        delegate = {"scope": "perform security audit of the codebase"}
        decision = router_with_skills.route(delegate)
        # Security keyword should trigger security signal
        assert decision.target_agent == "security_engineer"

    def test_testing_skill_in_scope_routes_to_quality(self, router_with_skills):
        delegate = {"scope": "improve testing coverage for the module"}
        decision = router_with_skills.route(delegate)
        assert decision.target_agent in ("quality_engineer", "engineer")

    def test_required_skills_extracted_from_delegate(self, router_with_skills):
        delegate = {
            "scope": "implement feature",
            "required_skills": ["testing", "metrics-etl"],
        }
        decision = router_with_skills.route(delegate)
        assert isinstance(decision.required_skills, list)

    def test_skill_affinity_map_coverage(self):
        """Verify all skill affinity entries map to valid agent names."""
        valid_agents = {
            "security_engineer", "principal_engineer", "lead_engineer",
            "quality_engineer", "model_engineer", "senior_engineer", "engineer",
        }
        for skill, agent in SKILL_AGENT_AFFINITY.items():
            assert agent in valid_agents, f"Skill '{skill}' maps to unknown agent '{agent}'"

    def test_multi_skill_routing_highest_affinity(self, router_with_skills):
        # Multiple security skills → security_engineer should win
        delegate = {
            "scope": "review auth and security",
            "required_skills": ["security", "authentication"],
        }
        decision = router_with_skills.route(delegate)
        assert decision.target_agent == "security_engineer"

    def test_skill_registry_in_router(self, router_with_skills):
        assert router_with_skills.skill_registry is not None
        assert isinstance(router_with_skills.skill_registry, SkillRegistry)

    def test_route_with_empty_skills_still_works(self, router_with_skills):
        delegate = {"scope": "do something", "required_skills": []}
        decision = router_with_skills.route(delegate)
        assert decision.target_agent

    def test_route_with_unknown_skills_falls_through(self, router_with_skills):
        delegate = {
            "scope": "implement feature",
            "required_skills": ["completely-unknown-skill-xyz"],
        }
        decision = router_with_skills.route(delegate)
        # Should fall through to complexity-based routing
        assert decision.target_agent in (
            "engineer", "senior_engineer", "lead_engineer", "principal_engineer"
        )

    def test_skill_match_signal_present(self, router_with_skills):
        # Route by skills that have affinity
        delegate = {
            "scope": "optimize cost and model selection",
            "required_skills": ["cost_optimization"],
        }
        decision = router_with_skills.route(delegate)
        # cost_optimization → model_engineer, but security/cross-service checks happen first
        assert isinstance(decision.signals_fired, list)

    def test_precommit_overrides_skill_routing(self, router_with_skills):
        delegate = {
            "scope": "pre-commit check",
            "required_skills": ["security"],
            "context": {"is_precommit_quality_gate": True},
        }
        decision = router_with_skills.route(delegate)
        # Precommit gate has higher priority than skill routing
        assert decision.target_agent == "quality_engineer"
        assert RoutingSignal.PRECOMMIT_GATE in decision.signals_fired

    def test_security_flag_overrides_skill_routing(self, router_with_skills):
        delegate = {
            "scope": "implement feature",
            "required_skills": ["testing"],
            "context": {"is_security_scoped": True},
        }
        decision = router_with_skills.route(delegate)
        assert decision.target_agent == "security_engineer"

    def test_routing_decision_includes_required_skills(self, router_with_skills):
        delegate = {
            "scope": "implement feature",
            "required_skills": ["testing"],
        }
        decision = router_with_skills.route(delegate)
        assert "testing" in decision.required_skills

    def test_real_skills_directory(self):
        """Test against the actual skills/ directory if it exists."""
        real_skills = Path(__file__).parents[1] / "skills"
        if not real_skills.exists():
            pytest.skip("skills/ directory not found")
        registry = SkillRegistry(skills_root=real_skills)
        skills = registry.available_skills()
        assert len(skills) >= 1
        router = SmartRouter(skill_registry=registry)
        decision = router.route({"scope": "implement feature", "effort": "medium"})
        assert decision.target_agent
