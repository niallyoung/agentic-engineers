"""Comprehensive test suite for skills auditor."""

import pytest
from pathlib import Path
from src.audit.skills_auditor import (
    DimensionScore,
    SkillScorecard,
    SkillCategory,
    SkillDiscovery,
    DimensionEvaluator,
    SkillsAuditor,
)


class TestDimensionScore:
    """Test DimensionScore data class."""

    def test_create_dimension_score(self) -> None:
        """Test creating a dimension score."""
        score = DimensionScore(value=7, notes="Test note")
        assert score.value == 7
        assert score.notes == "Test note"
        assert score.evidence == []

    def test_dimension_score_with_evidence(self) -> None:
        """Test dimension score with evidence."""
        score = DimensionScore(
            value=8,
            notes="Good test coverage",
            evidence=["Has 15 test files", "85% coverage"]
        )
        assert score.value == 8
        assert len(score.evidence) == 2

    def test_dimension_score_validation_too_low(self) -> None:
        """Test that dimension score rejects values below 1."""
        with pytest.raises(ValueError, match="1-10"):
            DimensionScore(value=0)

    def test_dimension_score_validation_too_high(self) -> None:
        """Test that dimension score rejects values above 10."""
        with pytest.raises(ValueError, match="1-10"):
            DimensionScore(value=11)

    def test_dimension_score_edge_values(self) -> None:
        """Test valid edge values."""
        score1 = DimensionScore(value=1)
        assert score1.value == 1
        
        score10 = DimensionScore(value=10)
        assert score10.value == 10


class TestSkillScorecard:
    """Test SkillScorecard data class."""

    def test_create_basic_scorecard(self) -> None:
        """Test creating a basic scorecard."""
        sc = SkillScorecard(
            name="test-skill",
            description="Test description",
            path="/path/to/skill"
        )
        assert sc.name == "test-skill"
        assert sc.description == "Test description"
        assert sc.category_assigned == "UTILITY"

    def test_scorecard_overall_score_default(self) -> None:
        """Test overall score calculation with defaults (all 5s)."""
        sc = SkillScorecard(
            name="test",
            description="test",
            path="/test"
        )
        # All dimensions default to 5
        assert sc.overall_score() == 50.0

    def test_scorecard_overall_score_mixed(self) -> None:
        """Test overall score with mixed dimension scores."""
        sc = SkillScorecard(
            name="test",
            description="test",
            path="/test",
            value=DimensionScore(value=10),
            usage=DimensionScore(value=8),
            maintenance=DimensionScore(value=6),
            tests=DimensionScore(value=4),
            docs=DimensionScore(value=5),
            quality=DimensionScore(value=9),
        )
        # (10+8+6+4+5+9) / 6 * 10 = 42/6 * 10 = 70.0
        assert sc.overall_score() == pytest.approx(70.0, rel=0.1)

    def test_scorecard_overall_score_perfect(self) -> None:
        """Test overall score with all 10s."""
        sc = SkillScorecard(
            name="test",
            description="test",
            path="/test",
            value=DimensionScore(value=10),
            usage=DimensionScore(value=10),
            maintenance=DimensionScore(value=10),
            tests=DimensionScore(value=10),
            docs=DimensionScore(value=10),
            quality=DimensionScore(value=10),
        )
        assert sc.overall_score() == 100.0

    def test_scorecard_dimension_scores_dict(self) -> None:
        """Test dimension scores dict conversion."""
        sc = SkillScorecard(
            name="test",
            description="test",
            path="/test",
            value=DimensionScore(value=7),
            usage=DimensionScore(value=8),
        )
        dims = sc.dimension_scores_dict()
        assert dims["value"] == 7
        assert dims["usage"] == 8
        assert dims["maintenance"] == 5
        assert len(dims) == 6


class TestSkillDiscovery:
    """Test SkillDiscovery functionality."""

    def test_skill_discovery_initialization(self) -> None:
        """Test initializing skill discovery."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        assert discovery.skills_dir == skills_path

    def test_skill_discovery_invalid_path(self) -> None:
        """Test that invalid path raises error."""
        with pytest.raises(ValueError, match="Skills directory not found"):
            SkillDiscovery(Path("/nonexistent/path"))

    def test_discover_skills(self) -> None:
        """Test discovering skills in directory."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        skills = discovery.discover_skills()
        
        # Should find multiple skills
        assert len(skills) > 10
        
        # Should not include excluded dirs
        excluded = {"_meta", "__pycache__", "shared", "patterns"}
        skill_names = {s.name for s in skills}
        assert not any(name in skill_names for name in excluded)

    def test_discover_skills_returns_paths(self) -> None:
        """Test that discover_skills returns Path objects."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        skills = discovery.discover_skills()
        
        assert all(isinstance(s, Path) for s in skills)
        assert all(s.is_dir() for s in skills)

    def test_load_metadata_from_skill(self) -> None:
        """Test loading metadata from SKILL.md."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        
        # Find a skill with SKILL.md
        skills = discovery.discover_skills()
        if skills:
            skill = skills[0]
            metadata = discovery.load_metadata(skill)
            
            # May be empty if no SKILL.md, but shouldn't error
            assert isinstance(metadata, dict)

    def test_count_files(self) -> None:
        """Test counting Python files in skill."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        
        # Count .py files in a known skill
        skill_path = skills_path / "agent-creator"
        if skill_path.exists():
            count = discovery.count_files(skill_path)
            assert count >= 0

    def test_count_lines(self) -> None:
        """Test counting lines of code in skill."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        
        # Count lines in a skill
        skill_path = skills_path / "agent-creator"
        if skill_path.exists():
            lines = discovery.count_lines(skill_path)
            assert isinstance(lines, int)
            assert lines >= 0


class TestDimensionEvaluator:
    """Test DimensionEvaluator functionality."""

    def test_evaluator_initialization(self) -> None:
        """Test evaluator initialization."""
        evaluator = DimensionEvaluator()
        assert evaluator is not None
        assert len(evaluator.DIMENSION_RUBRIC) == 6

    def test_evaluate_value_returns_score(self) -> None:
        """Test that evaluate_value returns a DimensionScore."""
        evaluator = DimensionEvaluator()
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        
        metadata = {
            "metadata": {
                "category": "optimization",
                "role": "lead-engineer",
                "effort": "low"
            }
        }
        
        score = evaluator.evaluate_value("test", metadata, discovery, skills_path)
        assert isinstance(score, DimensionScore)
        assert 1 <= score.value <= 10

    def test_evaluate_usage_returns_score(self) -> None:
        """Test that evaluate_usage returns a DimensionScore."""
        evaluator = DimensionEvaluator()
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        discovery = SkillDiscovery(skills_path)
        
        score = evaluator.evaluate_usage("test", discovery, skills_path)
        assert isinstance(score, DimensionScore)
        assert 1 <= score.value <= 10

    def test_evaluate_maintenance_returns_score(self) -> None:
        """Test that evaluate_maintenance returns a DimensionScore."""
        evaluator = DimensionEvaluator()
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        score = evaluator.evaluate_maintenance("test", skills_path)
        assert isinstance(score, DimensionScore)
        assert 1 <= score.value <= 10

    def test_evaluate_tests_returns_score(self) -> None:
        """Test that evaluate_tests returns a DimensionScore."""
        evaluator = DimensionEvaluator()
        score = evaluator.evaluate_tests("test-skill")
        assert isinstance(score, DimensionScore)
        assert 1 <= score.value <= 10

    def test_evaluate_docs_returns_score(self) -> None:
        """Test that evaluate_docs returns a DimensionScore."""
        evaluator = DimensionEvaluator()
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        score = evaluator.evaluate_docs("test", skills_path, {})
        assert isinstance(score, DimensionScore)
        assert 1 <= score.value <= 10

    def test_evaluate_quality_returns_score(self) -> None:
        """Test that evaluate_quality returns a DimensionScore."""
        evaluator = DimensionEvaluator()
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        score = evaluator.evaluate_quality("test", skills_path)
        assert isinstance(score, DimensionScore)
        assert 1 <= score.value <= 10

    def test_dimension_rubric_completeness(self) -> None:
        """Test that rubric has all dimensions with 1-10 entries."""
        evaluator = DimensionEvaluator()
        
        expected_dims = {"value", "usage", "maintenance", "tests", "docs", "quality"}
        assert set(evaluator.DIMENSION_RUBRIC.keys()) == expected_dims
        
        for dim, rubric in evaluator.DIMENSION_RUBRIC.items():
            assert len(rubric) == 10
            for i in range(1, 11):
                assert i in rubric


class TestSkillsAuditor:
    """Test SkillsAuditor functionality."""

    def test_auditor_initialization(self) -> None:
        """Test auditor initialization."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        
        assert auditor.skills_dir == skills_path
        assert auditor.discovery is not None
        assert auditor.evaluator is not None
        assert auditor.scorecards == {}

    def test_audit_skill(self) -> None:
        """Test auditing a single skill."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        
        # Audit agent-creator skill
        skill_path = skills_path / "agent-creator"
        if skill_path.exists():
            scorecard = auditor.audit_skill("agent-creator", skill_path)
            
            assert isinstance(scorecard, SkillScorecard)
            assert scorecard.name == "agent-creator"
            assert 0 <= scorecard.overall_score() <= 100

    def test_audit_all_skills(self) -> None:
        """Test auditing all skills."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        
        scorecards = auditor.audit_all_skills()
        
        assert len(scorecards) > 10
        assert all(isinstance(sc, SkillScorecard) for sc in scorecards.values())

    def test_get_summary_statistics(self) -> None:
        """Test getting summary statistics."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        
        # Audit first
        auditor.audit_all_skills()
        
        stats = auditor.get_summary_statistics()
        
        assert "total_skills" in stats
        assert "avg_score" in stats
        assert "min_score" in stats
        assert "max_score" in stats
        assert "dimension_averages" in stats
        assert "category_breakdown" in stats
        assert "skills_needing_improvement" in stats
        
        # Verify numeric ranges
        assert stats["total_skills"] > 10
        assert 0 <= stats["avg_score"] <= 100
        assert 0 <= stats["min_score"] <= stats["max_score"] <= 100

    def test_dimension_averages_all_present(self) -> None:
        """Test that dimension averages include all 6 dimensions."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        stats = auditor.get_summary_statistics()
        dims = stats["dimension_averages"]
        
        expected_dims = {"value", "usage", "maintenance", "tests", "docs", "quality"}
        assert set(dims.keys()) == expected_dims

    def test_category_breakdown_structure(self) -> None:
        """Test that category breakdown has expected categories."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        stats = auditor.get_summary_statistics()
        categories = stats["category_breakdown"]
        
        # Should have at least one category
        assert len(categories) > 0
        
        # Categories should be valid
        valid_categories = {"CORE", "UTILITY", "EXPERIMENTAL"}
        assert all(cat in valid_categories for cat in categories.keys())

    def test_audit_skill_creates_recommendations(self) -> None:
        """Test that audit creates recommendations."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        
        skill_path = skills_path / "agent-creator"
        if skill_path.exists():
            scorecard = auditor.audit_skill("agent-creator", skill_path)
            
            # Scorecard should have recommendations (at least potentially)
            assert isinstance(scorecard.recommendations, list)

    def test_category_assignment_based_on_score(self) -> None:
        """Test that categories are assigned based on scores."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        for name, sc in auditor.scorecards.items():
            score = sc.overall_score()
            
            if score >= 75:
                assert sc.category_assigned == "CORE", f"{name} should be CORE but isn't"
            elif score >= 55:
                assert sc.category_assigned == "UTILITY", f"{name} should be UTILITY but isn't"
            else:
                assert sc.category_assigned == "EXPERIMENTAL", f"{name} should be EXPERIMENTAL but isn't"


class TestIntegration:
    """Integration tests for the audit framework."""

    def test_full_audit_workflow(self) -> None:
        """Test complete audit workflow."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        # Initialize and run audit
        auditor = SkillsAuditor(skills_path)
        scorecards = auditor.audit_all_skills()
        
        # Verify all skills were audited
        assert len(scorecards) > 10
        
        # Verify each scorecard is complete
        for name, sc in scorecards.items():
            assert sc.name == name
            assert 0 <= sc.overall_score() <= 100
            assert len(sc.dimension_scores_dict()) == 6

    def test_audit_maintains_consistency(self) -> None:
        """Test that multiple audits are consistent."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        # First audit
        auditor1 = SkillsAuditor(skills_path)
        auditor1.audit_all_skills()
        stats1 = auditor1.get_summary_statistics()
        
        # Second audit
        auditor2 = SkillsAuditor(skills_path)
        auditor2.audit_all_skills()
        stats2 = auditor2.get_summary_statistics()
        
        # Should be identical
        assert stats1["total_skills"] == stats2["total_skills"]
        assert stats1["avg_score"] == stats2["avg_score"]

    def test_audit_identifies_weak_skills(self) -> None:
        """Test that audit identifies skills needing improvement."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        stats = auditor.get_summary_statistics()
        
        weak_skills = stats["skills_needing_improvement"]
        
        # All weak skills should have score < 65
        for skill_name in weak_skills:
            sc = auditor.scorecards[skill_name]
            assert sc.overall_score() < 65
