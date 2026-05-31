"""Skills auditor for comprehensive 6-dimensional evaluation framework."""

import os
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum


class SkillCategory(Enum):
    """Category assignments for skills."""
    CORE = "CORE"
    UTILITY = "UTILITY"
    EXPERIMENTAL = "EXPERIMENTAL"


@dataclass
class DimensionScore:
    """Score for a single dimension."""
    value: int  # 1-10
    notes: str = ""
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.value <= 10:
            raise ValueError(f"Dimension score must be 1-10, got {self.value}")


@dataclass
class SkillScorecard:
    """Complete scorecard for a skill across all 6 dimensions."""
    name: str
    description: str
    path: str
    version: str = "1.0"
    category_assigned: str = "UTILITY"
    
    # 6 Dimensions (each 1-10)
    value: DimensionScore = field(default_factory=lambda: DimensionScore(5))
    usage: DimensionScore = field(default_factory=lambda: DimensionScore(5))
    maintenance: DimensionScore = field(default_factory=lambda: DimensionScore(5))
    tests: DimensionScore = field(default_factory=lambda: DimensionScore(5))
    docs: DimensionScore = field(default_factory=lambda: DimensionScore(5))
    quality: DimensionScore = field(default_factory=lambda: DimensionScore(5))
    
    # Strengths and weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    last_updated: str = ""
    author: str = ""
    role: str = ""
    model: str = ""
    effort: str = ""

    def overall_score(self) -> float:
        """Calculate overall score (0-100 from 6 dimensions)."""
        total = (
            self.value.value +
            self.usage.value +
            self.maintenance.value +
            self.tests.value +
            self.docs.value +
            self.quality.value
        )
        return (total / 60.0) * 100.0

    def dimension_scores_dict(self) -> Dict[str, int]:
        """Return all dimension scores as dict."""
        return {
            "value": self.value.value,
            "usage": self.usage.value,
            "maintenance": self.maintenance.value,
            "tests": self.tests.value,
            "docs": self.docs.value,
            "quality": self.quality.value,
        }


class SkillDiscovery:
    """Discovers and loads skill metadata."""

    def __init__(self, skills_dir: Path) -> None:
        """Initialize skill discovery.
        
        Args:
            skills_dir: Path to skills directory
        """
        self.skills_dir = Path(skills_dir)
        if not self.skills_dir.exists():
            raise ValueError(f"Skills directory not found: {self.skills_dir}")

    def discover_skills(self) -> List[Path]:
        """Discover all skill directories.
        
        Returns:
            List of skill directory paths (excluding _meta and __pycache__)
        """
        skills = []
        exclude_dirs = {"_meta", "__pycache__", "shared", "patterns", 
                       "architecture", "security", "testing", "monitoring",
                       "orchestration", "review", "roles", "optimization",
                       "spec-extract"}
        
        for item in self.skills_dir.iterdir():
            if item.is_dir() and item.name not in exclude_dirs:
                skills.append(item)
        
        return sorted(skills, key=lambda x: x.name)

    def load_metadata(self, skill_path: Path) -> Dict[str, any]:
        """Load SKILL.md metadata from skill directory.
        
        Args:
            skill_path: Path to skill directory
            
        Returns:
            Metadata dict or empty dict if not found
        """
        skill_md = skill_path / "SKILL.md"
        
        if not skill_md.exists():
            return {}
        
        try:
            with open(skill_md, 'r') as f:
                content = f.read()
            
            # Parse YAML frontmatter
            if content.startswith('---'):
                _, frontmatter, _ = content.split('---', 2)
                metadata = yaml.safe_load(frontmatter)
                return metadata or {}
            return {}
        except Exception as e:
            print(f"Error loading metadata from {skill_md}: {e}")
            return {}

    def count_files(self, skill_path: Path, pattern: str = "*.py") -> int:
        """Count files matching pattern in skill directory.
        
        Args:
            skill_path: Path to skill directory
            pattern: File pattern to match
            
        Returns:
            Number of matching files
        """
        return len(list(skill_path.rglob(pattern)))

    def count_lines(self, skill_path: Path, pattern: str = "*.py") -> int:
        """Count total lines of code in skill directory.
        
        Args:
            skill_path: Path to skill directory
            pattern: File pattern to match
            
        Returns:
            Total lines of code
        """
        total = 0
        for file_path in skill_path.rglob(pattern):
            try:
                with open(file_path, 'r') as f:
                    total += len(f.readlines())
            except Exception:
                pass
        return total


class DimensionEvaluator:
    """Evaluates skills across 6 dimensions."""

    DIMENSION_RUBRIC = {
        "value": {
            1: "Not essential, low priority for framework",
            2: "Minor utility, rarely used",
            3: "Some utility, niche use cases",
            4: "Moderate utility",
            5: "Useful addition to framework",
            6: "Important capability",
            7: "Very important, frequently referenced",
            8: "Core strategic capability",
            9: "Critical to framework success",
            10: "Essential, central to framework mission",
        },
        "usage": {
            1: "Never used, no integrations",
            2: "Rarely used",
            3: "Occasionally used",
            4: "Limited usage",
            5: "Regular usage",
            6: "Frequent usage",
            7: "Very frequent, multiple integrations",
            8: "Heavy usage, many integrations",
            9: "Extensively used across platform",
            10: "Ubiquitous, integrated everywhere",
        },
        "maintenance": {
            1: "Highly deprecated, no updates",
            2: "Very poor, significant tech debt",
            3: "Poor, needs refactoring",
            4: "Below average",
            5: "Adequate",
            6: "Good",
            7: "Well maintained",
            8: "Excellent, modern best practices",
            9: "Exemplary code quality",
            10: "Perfect, industry-leading practices",
        },
        "tests": {
            1: "No tests",
            2: "Minimal tests (<20% coverage)",
            3: "Poor coverage (<40%)",
            4: "Low coverage (<60%)",
            5: "Moderate coverage (~65%)",
            6: "Good coverage (~75%)",
            7: "Very good coverage (~85%)",
            8: "Excellent coverage (~90%)",
            9: "Outstanding coverage (>95%)",
            10: "Perfect coverage (100%)",
        },
        "docs": {
            1: "No documentation",
            2: "Minimal docs",
            3: "Incomplete docs",
            4: "Basic docs",
            5: "Adequate documentation",
            6: "Good documentation",
            7: "Very good docs",
            8: "Excellent docs",
            9: "Outstanding docs",
            10: "Perfect, exemplary docs",
        },
        "quality": {
            1: "Broken, non-functional",
            2: "Barely functional, many issues",
            3: "Works but with issues",
            4: "Below average quality",
            5: "Average quality",
            6: "Good quality",
            7: "High quality",
            8: "Very high quality",
            9: "Excellent quality",
            10: "Production-grade, no known issues",
        },
    }

    def evaluate_value(self, skill_name: str, metadata: Dict[str, any],
                      discovery: SkillDiscovery, skill_path: Path) -> DimensionScore:
        """Evaluate value dimension (1-10).
        
        Args:
            skill_name: Name of skill
            metadata: Skill metadata
            discovery: Skill discovery instance
            skill_path: Path to skill
            
        Returns:
            DimensionScore for value
        """
        evidence = []
        score = 5
        
        # Check category from metadata
        category = metadata.get("metadata", {}).get("category", "")
        if category in ["optimization", "governance", "orchestration"]:
            score += 2
            evidence.append(f"High-priority category: {category}")
        elif category in ["monitoring", "testing"]:
            score += 1
            evidence.append(f"Medium-priority category: {category}")
        else:
            evidence.append(f"Standard category: {category}")
        
        # Check role requirements
        role = metadata.get("metadata", {}).get("role", "")
        if role in ["principal-engineer", "lead-engineer"]:
            score += 1
            evidence.append(f"Requires senior role: {role}")
        
        # Check effort (lower effort = higher value)
        effort = metadata.get("metadata", {}).get("effort", "")
        if effort == "low":
            score += 1
            evidence.append("Low effort to maintain")
        
        score = min(10, max(1, score))
        return DimensionScore(
            value=score,
            notes=f"Value assessment based on category, role requirements, and effort",
            evidence=evidence[:3]
        )

    def evaluate_usage(self, skill_name: str, discovery: SkillDiscovery,
                      skill_path: Path) -> DimensionScore:
        """Evaluate usage dimension (1-10).
        
        Args:
            skill_name: Name of skill
            discovery: Skill discovery instance
            skill_path: Path to skill
            
        Returns:
            DimensionScore for usage
        """
        evidence = []
        score = 5
        
        # Check for scripts directory
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            script_count = discovery.count_files(scripts_dir, "*.py")
            if script_count > 0:
                score += min(2, script_count // 2)
                evidence.append(f"Has {script_count} integration scripts")
        
        # Check for integration patterns
        init_file = skill_path / "__init__.py"
        if init_file.exists():
            try:
                with open(init_file, 'r') as f:
                    init_content = f.read()
                if "DELEGATE" in init_content or "HANDBACK" in init_content:
                    score += 1
                    evidence.append("Implements DELEGATE/HANDBACK protocols")
            except Exception:
                pass
        
        # Check for README or documentation
        readme = skill_path / "README.md"
        if readme.exists():
            score += 1
            evidence.append("Has comprehensive README")
        
        score = min(10, max(1, score))
        return DimensionScore(
            value=score,
            notes=f"Usage based on integrations, scripts, and documentation",
            evidence=evidence[:3]
        )

    def evaluate_maintenance(self, skill_name: str, skill_path: Path) -> DimensionScore:
        """Evaluate maintenance dimension (1-10).
        
        Args:
            skill_name: Name of skill
            skill_path: Path to skill
            
        Returns:
            DimensionScore for maintenance
        """
        evidence = []
        score = 5
        
        # Check code structure
        py_files = list(skill_path.rglob("*.py"))
        lines = sum(len(open(f).readlines()) for f in py_files if f.is_file())
        
        if lines > 2000:
            score -= 1
            evidence.append(f"Large codebase ({lines} lines)")
        elif lines < 500:
            score += 1
            evidence.append(f"Focused codebase ({lines} lines)")
        else:
            evidence.append(f"Moderate codebase ({lines} lines)")
        
        # Check for type hints
        type_hint_count = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                if "->" in content or ": " in content:
                    type_hint_count += 1
            except Exception:
                pass
        
        if type_hint_count == len(py_files) and py_files:
            score += 1
            evidence.append("Good type hint coverage")
        elif type_hint_count > 0:
            score += 1
            evidence.append("Some type hints present")
        
        # Check for docstrings
        docstring_count = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                if '"""' in content or "'''" in content:
                    docstring_count += 1
            except Exception:
                pass
        
        if docstring_count == len(py_files) and py_files:
            score += 1
            evidence.append("Comprehensive docstrings")
        
        score = min(10, max(1, score))
        return DimensionScore(
            value=score,
            notes=f"Based on code structure, type hints, and documentation",
            evidence=evidence[:3]
        )

    def evaluate_tests(self, skill_name: str) -> DimensionScore:
        """Evaluate tests dimension (1-10).
        
        Args:
            skill_name: Name of skill
            
        Returns:
            DimensionScore for tests
        """
        test_dir = Path("/Users/niall/git/agentic-engineers/tests/skills") / skill_name.replace("-", "_")
        evidence = []
        score = 3  # Default to low
        
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            if test_files:
                score = 5 + min(3, len(test_files) // 2)
                evidence.append(f"Has {len(test_files)} test files")
        
        # Check for conftest or fixtures
        if (test_dir / "conftest.py").exists():
            score += 1
            evidence.append("Has test fixtures/conftest")
        
        score = min(10, max(1, score))
        return DimensionScore(
            value=score,
            notes=f"Based on test file presence and fixtures",
            evidence=evidence[:3]
        )

    def evaluate_docs(self, skill_name: str, skill_path: Path,
                      metadata: Dict[str, any]) -> DimensionScore:
        """Evaluate documentation dimension (1-10).
        
        Args:
            skill_name: Name of skill
            skill_path: Path to skill
            metadata: Skill metadata
            
        Returns:
            DimensionScore for docs
        """
        evidence = []
        score = 5
        
        # Check for SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                with open(skill_md, 'r') as f:
                    content = f.read()
                lines = len(content.split('\n'))
                if lines > 100:
                    score += 2
                    evidence.append("Comprehensive SKILL.md (100+ lines)")
                elif lines > 50:
                    score += 1
                    evidence.append("Good SKILL.md (50+ lines)")
            except Exception:
                pass
        
        # Check for README
        readme = skill_path / "README.md"
        if readme.exists():
            score += 1
            evidence.append("Has README.md")
        
        # Check for API documentation
        if (skill_path / "API.md").exists():
            score += 1
            evidence.append("Has API documentation")
        
        # Check for examples
        examples = list(skill_path.glob("examples/**/*.md"))
        if examples:
            score += 1
            evidence.append(f"Has {len(examples)} examples")
        
        # Check description in metadata
        description = metadata.get("description", "")
        if len(description) > 100:
            evidence.append("Detailed description in metadata")
        
        score = min(10, max(1, score))
        return DimensionScore(
            value=score,
            notes=f"Based on SKILL.md, README, and API docs",
            evidence=evidence[:3]
        )

    def evaluate_quality(self, skill_name: str, skill_path: Path) -> DimensionScore:
        """Evaluate overall code quality dimension (1-10).
        
        Args:
            skill_name: Name of skill
            skill_path: Path to skill
            
        Returns:
            DimensionScore for quality
        """
        evidence = []
        score = 5
        
        # Check for linting markers
        py_files = list(skill_path.rglob("*.py"))
        
        if not py_files:
            return DimensionScore(
                value=3,
                notes="No Python files found",
                evidence=["Empty skill"]
            )
        
        # Check for noqa comments (potential smell)
        noqa_count = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    noqa_count += f.read().count("# noqa")
            except Exception:
                pass
        
        if noqa_count > len(py_files):
            score -= 1
            evidence.append(f"Multiple linting suppressions ({noqa_count})")
        
        # Check for error handling
        error_handling = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                if "try:" in content and "except" in content:
                    error_handling += 1
            except Exception:
                pass
        
        if error_handling > 0:
            score += 1
            evidence.append("Has error handling")
        
        # Check for logging
        logging_count = 0
        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                if "logging" in content or "logger" in content:
                    logging_count += 1
            except Exception:
                pass
        
        if logging_count > 0:
            score += 1
            evidence.append("Uses logging")
        
        score = min(10, max(1, score))
        return DimensionScore(
            value=score,
            notes=f"Based on code patterns, error handling, logging",
            evidence=evidence[:3]
        )


class SkillsAuditor:
    """Main auditor orchestrating the audit process."""

    def __init__(self, skills_dir: Path) -> None:
        """Initialize auditor.
        
        Args:
            skills_dir: Path to skills directory
        """
        self.skills_dir = Path(skills_dir)
        self.discovery = SkillDiscovery(self.skills_dir)
        self.evaluator = DimensionEvaluator()
        self.scorecards: Dict[str, SkillScorecard] = {}

    def audit_all_skills(self) -> Dict[str, SkillScorecard]:
        """Audit all discovered skills.
        
        Returns:
            Dict mapping skill names to scorecards
        """
        skills = self.discovery.discover_skills()
        
        for skill_path in skills:
            skill_name = skill_path.name
            self.audit_skill(skill_name, skill_path)
        
        return self.scorecards

    def audit_skill(self, skill_name: str, skill_path: Path) -> SkillScorecard:
        """Audit a single skill.
        
        Args:
            skill_name: Name of skill
            skill_path: Path to skill directory
            
        Returns:
            Completed scorecard
        """
        metadata = self.discovery.load_metadata(skill_path)
        
        # Extract metadata
        description = metadata.get("description", "")
        version = metadata.get("metadata", {}).get("version", "1.0")
        author = metadata.get("metadata", {}).get("author", "")
        role = metadata.get("metadata", {}).get("role", "")
        model = metadata.get("metadata", {}).get("model", "")
        effort = metadata.get("metadata", {}).get("effort", "medium")
        
        # Evaluate all dimensions
        value_score = self.evaluator.evaluate_value(
            skill_name, metadata, self.discovery, skill_path
        )
        usage_score = self.evaluator.evaluate_usage(
            skill_name, self.discovery, skill_path
        )
        maintenance_score = self.evaluator.evaluate_maintenance(
            skill_name, skill_path
        )
        tests_score = self.evaluator.evaluate_tests(skill_name)
        docs_score = self.evaluator.evaluate_docs(
            skill_name, skill_path, metadata
        )
        quality_score = self.evaluator.evaluate_quality(skill_name, skill_path)
        
        # Determine category
        overall = (
            value_score.value +
            usage_score.value +
            maintenance_score.value +
            tests_score.value +
            docs_score.value +
            quality_score.value
        ) / 6.0
        
        if overall >= 7.5:
            category = SkillCategory.CORE.value
        elif overall >= 5.5:
            category = SkillCategory.UTILITY.value
        else:
            category = SkillCategory.EXPERIMENTAL.value
        
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        if value_score.value >= 7:
            strengths.append("High strategic value")
        if usage_score.value >= 7:
            strengths.append("Well integrated")
        if maintenance_score.value >= 7:
            strengths.append("Well maintained code")
        if tests_score.value >= 7:
            strengths.append("Good test coverage")
        if docs_score.value >= 7:
            strengths.append("Excellent documentation")
        if quality_score.value >= 7:
            strengths.append("High code quality")
        
        if value_score.value <= 3:
            weaknesses.append("Low strategic value")
        if usage_score.value <= 3:
            weaknesses.append("Limited integration")
        if maintenance_score.value <= 3:
            weaknesses.append("Code quality needs improvement")
        if tests_score.value <= 3:
            weaknesses.append("Insufficient test coverage")
        if docs_score.value <= 3:
            weaknesses.append("Poor documentation")
        if quality_score.value <= 3:
            weaknesses.append("Significant quality issues")
        
        # Generate recommendations
        recommendations = []
        if tests_score.value < 7:
            recommendations.append(f"Improve test coverage (current: {tests_score.value}/10)")
        if docs_score.value < 7:
            recommendations.append(f"Enhance documentation (current: {docs_score.value}/10)")
        if maintenance_score.value < 6:
            recommendations.append(f"Refactor code for maintainability (current: {maintenance_score.value}/10)")
        if quality_score.value < 7:
            recommendations.append(f"Address code quality issues (current: {quality_score.value}/10)")
        
        scorecard = SkillScorecard(
            name=skill_name,
            description=description,
            path=str(skill_path),
            version=version,
            category_assigned=category,
            value=value_score,
            usage=usage_score,
            maintenance=maintenance_score,
            tests=tests_score,
            docs=docs_score,
            quality=quality_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            author=author,
            role=role,
            model=model,
            effort=effort,
        )
        
        self.scorecards[skill_name] = scorecard
        return scorecard

    def get_summary_statistics(self) -> Dict[str, any]:
        """Get summary statistics for all audited skills.
        
        Returns:
            Summary statistics dict
        """
        if not self.scorecards:
            return {}
        
        all_scores = [sc.overall_score() for sc in self.scorecards.values()]
        dimension_avgs = {}
        
        for dim in ["value", "usage", "maintenance", "tests", "docs", "quality"]:
            scores = [getattr(sc, dim).value for sc in self.scorecards.values()]
            dimension_avgs[dim] = sum(scores) / len(scores) if scores else 0
        
        category_counts = {}
        for sc in self.scorecards.values():
            cat = sc.category_assigned
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "total_skills": len(self.scorecards),
            "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0,
            "min_score": min(all_scores) if all_scores else 0,
            "max_score": max(all_scores) if all_scores else 0,
            "dimension_averages": dimension_avgs,
            "category_breakdown": category_counts,
            "skills_needing_improvement": [
                name for name, sc in self.scorecards.items()
                if sc.overall_score() < 65
            ]
        }
