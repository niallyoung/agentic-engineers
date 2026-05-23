# -*- coding: utf-8 -*-
"""
tests/test_task_orchestration.py — TDD RED-phase test suite for task-orchestration skill.

Tests cover:
  - Task classification: AUTONOMOUS vs DECISION_NEEDED vs SEQUENTIAL_ONLY
  - Parallelization analysis: dependency detection, git/filesystem safety
  - Decision shorthand generation: "1(a-z)" format
  - Decision response parsing: "1a, 2c, 3b" → {1: 'a', 2: 'c', 3: 'b'}
  - Framework principle enforcement: task sequencing NEVER asked, genuine decisions ARE asked

TDD Phase: RED → run these, they should fail (ImportError or assertion errors)
           GREEN → implement task_orchestrator.py to make all tests pass.
"""

import sys
from pathlib import Path
import pytest

# ── path bootstrap ──────────────────────────────────────────────────────────
_SKILL_ROOT = Path(__file__).parent.parent
_SCRIPTS_DIR = _SKILL_ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))  # repo root

from task_orchestrator import (
    Task,
    TaskType,
    classify_task,
    can_parallelize,
    generate_decision_shorthand,
    parse_decision_response,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def independent_tasks():
    return [
        Task(id="t1", description="Write unit tests for auth module", dependencies=[]),
        Task(id="t2", description="Write unit tests for billing module", dependencies=[]),
        Task(id="t3", description="Update README documentation", dependencies=[]),
    ]


@pytest.fixture
def dependent_tasks():
    return [
        Task(id="build", description="Build the project", dependencies=[], touches_files=["dist/app.js"]),
        Task(id="test", description="Run tests against build output", dependencies=["build"], touches_files=["dist/app.js"]),
    ]


@pytest.fixture
def git_conflicting_tasks():
    return [
        Task(id="feat-a", description="Implement feature A", dependencies=[], touches_files=["src/auth.py"]),
        Task(id="feat-b", description="Implement feature B", dependencies=[], touches_files=["src/auth.py"]),
    ]


@pytest.fixture
def mixed_tasks():
    return [
        Task(id="docs", description="Update documentation", dependencies=[], touches_files=["README.md"]),
        Task(id="tests", description="Write tests for new API", dependencies=[], touches_files=["tests/test_api.py"]),
        Task(id="deploy", description="Deploy to production", dependencies=["tests"], touches_files=[]),
    ]


# ============================================================================
# TaskType ENUM
# ============================================================================

class TestTaskTypeEnum:
    def test_autonomous_value_exists(self):
        """AUTONOMOUS tasks require no user input — agents execute them independently."""
        assert TaskType.AUTONOMOUS is not None

    def test_decision_needed_value_exists(self):
        """DECISION_NEEDED tasks require genuine user input before proceeding."""
        assert TaskType.DECISION_NEEDED is not None

    def test_sequential_only_value_exists(self):
        """SEQUENTIAL_ONLY tasks have dependencies that prevent parallelization."""
        assert TaskType.SEQUENTIAL_ONLY is not None

    def test_task_type_values_are_distinct(self):
        assert TaskType.AUTONOMOUS != TaskType.DECISION_NEEDED
        assert TaskType.AUTONOMOUS != TaskType.SEQUENTIAL_ONLY
        assert TaskType.DECISION_NEEDED != TaskType.SEQUENTIAL_ONLY


# ============================================================================
# Task DATACLASS
# ============================================================================

class TestTaskDataclass:
    def test_task_has_required_fields(self):
        t = Task(id="t1", description="Do something", dependencies=[])
        assert t.id == "t1"
        assert t.description == "Do something"
        assert t.dependencies == []

    def test_task_touches_files_defaults_to_empty(self):
        t = Task(id="t1", description="Do something", dependencies=[])
        assert t.touches_files == []

    def test_task_with_dependencies(self):
        t = Task(id="t2", description="Run tests", dependencies=["build"])
        assert "build" in t.dependencies

    def test_task_with_file_conflicts(self):
        t = Task(id="t3", description="Edit auth", dependencies=[], touches_files=["src/auth.py"])
        assert "src/auth.py" in t.touches_files


# ============================================================================
# classify_task — AUTONOMOUS
# ============================================================================

class TestClassifyTaskAutonomous:
    """Tasks that are clearly implementation work — never ask user about these."""

    def test_writing_tests_is_autonomous(self):
        result = classify_task("Write unit tests for the payment module")
        assert result == TaskType.AUTONOMOUS

    def test_implementing_feature_is_autonomous(self):
        result = classify_task("Implement the login endpoint")
        assert result == TaskType.AUTONOMOUS

    def test_refactoring_is_autonomous(self):
        result = classify_task("Refactor the database connection pool")
        assert result == TaskType.AUTONOMOUS

    def test_fixing_bug_is_autonomous(self):
        result = classify_task("Fix the null pointer exception in auth handler")
        assert result == TaskType.AUTONOMOUS

    def test_updating_docs_is_autonomous(self):
        result = classify_task("Update README with new installation instructions")
        assert result == TaskType.AUTONOMOUS

    def test_running_linter_is_autonomous(self):
        result = classify_task("Run the linter and fix all warnings")
        assert result == TaskType.AUTONOMOUS

    def test_task_sequencing_question_is_autonomous(self):
        """CRITICAL: 'Which task should I start first?' is NEVER a decision — it's sequencing."""
        result = classify_task("Which task should I start first?")
        assert result == TaskType.AUTONOMOUS

    def test_ordering_question_is_autonomous(self):
        """CRITICAL: Ordering/sequencing is ALWAYS autonomous — agents decide, never ask."""
        result = classify_task("What order should I implement these features?")
        assert result == TaskType.AUTONOMOUS

    def test_which_to_do_first_is_autonomous(self):
        """'Should I do A or B first?' is task sequencing, not a design decision."""
        result = classify_task("Should I do task A or task B first?")
        assert result == TaskType.AUTONOMOUS


# ============================================================================
# classify_task — DECISION_NEEDED
# ============================================================================

class TestClassifyTaskDecisionNeeded:
    """Genuine design/architectural decisions that require user input."""

    def test_technology_choice_needs_decision(self):
        result = classify_task("Should we use Redis or in-memory caching?")
        assert result == TaskType.DECISION_NEEDED

    def test_architecture_choice_needs_decision(self):
        result = classify_task("Should we use a monolith or microservices architecture?")
        assert result == TaskType.DECISION_NEEDED

    def test_removal_or_deprecation_needs_decision(self):
        result = classify_task("Should we remove this feature or deprecate it?")
        assert result == TaskType.DECISION_NEEDED

    def test_breaking_change_needs_decision(self):
        result = classify_task("This change will break the public API — should we proceed?")
        assert result == TaskType.DECISION_NEEDED

    def test_security_tradeoff_needs_decision(self):
        result = classify_task("Should we use OAuth or API keys for authentication?")
        assert result == TaskType.DECISION_NEEDED

    def test_render_ab_choice_needs_decision(self):
        """'Should we use render A or render B?' is a genuine decision."""
        result = classify_task("Should we use render A or render B?")
        assert result == TaskType.DECISION_NEEDED


# ============================================================================
# classify_task — SEQUENTIAL_ONLY
# ============================================================================

class TestClassifyTaskSequentialOnly:
    def test_migration_before_tests_is_sequential(self):
        result = classify_task("Run database migrations, then run tests")
        assert result == TaskType.SEQUENTIAL_ONLY

    def test_build_then_deploy_is_sequential(self):
        result = classify_task("Build the project, then deploy to production")
        assert result == TaskType.SEQUENTIAL_ONLY


# ============================================================================
# can_parallelize
# ============================================================================

class TestCanParallelize:
    def test_independent_tasks_can_parallelize(self, independent_tasks):
        assert can_parallelize(independent_tasks) is True

    def test_dependent_tasks_cannot_parallelize(self, dependent_tasks):
        assert can_parallelize(dependent_tasks) is False

    def test_git_conflicting_tasks_cannot_parallelize(self, git_conflicting_tasks):
        """Two tasks touching the same file are not safe to parallelize (git conflict)."""
        assert can_parallelize(git_conflicting_tasks) is False

    def test_single_task_cannot_parallelize(self):
        tasks = [Task(id="t1", description="Only task", dependencies=[])]
        assert can_parallelize(tasks) is False

    def test_empty_task_list_cannot_parallelize(self):
        assert can_parallelize([]) is False

    def test_mixed_tasks_cannot_parallelize(self, mixed_tasks):
        """'deploy' depends on 'tests' — mixed list of dep + no-dep cannot fully parallelize."""
        assert can_parallelize(mixed_tasks) is False

    def test_two_independent_no_file_overlap_can_parallelize(self):
        tasks = [
            Task(id="a", description="Task A", dependencies=[], touches_files=["src/foo.py"]),
            Task(id="b", description="Task B", dependencies=[], touches_files=["src/bar.py"]),
        ]
        assert can_parallelize(tasks) is True

    def test_tasks_with_no_files_can_parallelize(self):
        tasks = [
            Task(id="a", description="Write tests A", dependencies=[]),
            Task(id="b", description="Write tests B", dependencies=[]),
            Task(id="c", description="Update docs", dependencies=[]),
        ]
        assert can_parallelize(tasks) is True


# ============================================================================
# generate_decision_shorthand
# ============================================================================

class TestGenerateDecisionShorthand:
    def test_two_options_generates_ab_format(self):
        """2 options → 'a' and 'b' choices under question 1."""
        result = generate_decision_shorthand(["Use Redis", "Use in-memory"])
        assert "1a" in result
        assert "1b" in result

    def test_three_options_generates_abc_format(self):
        result = generate_decision_shorthand(["Option X", "Option Y", "Option Z"])
        assert "1a" in result
        assert "1b" in result
        assert "1c" in result

    def test_single_option_generates_only_a(self):
        result = generate_decision_shorthand(["Only option"])
        assert "1a" in result
        assert "1b" not in result

    def test_output_contains_option_text(self):
        result = generate_decision_shorthand(["Use Redis", "Use in-memory"])
        assert "Use Redis" in result
        assert "Use in-memory" in result

    def test_custom_question_number(self):
        """Multiple questions can co-exist: question 2 uses 2(a-z) format."""
        result = generate_decision_shorthand(["Option A", "Option B"], question_number=2)
        assert "2a" in result
        assert "2b" in result

    def test_empty_options_raises_value_error(self):
        with pytest.raises(ValueError):
            generate_decision_shorthand([])

    def test_returns_string(self):
        result = generate_decision_shorthand(["A", "B"])
        assert isinstance(result, str)

    def test_format_is_compact_and_scannable(self):
        """Shorthand must be compact — no excessive whitespace or verbosity."""
        result = generate_decision_shorthand(["Redis", "Memcached", "In-memory"])
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # Each option should fit on its own line
        assert len(lines) >= 3


# ============================================================================
# parse_decision_response
# ============================================================================

class TestParseDecisionResponse:
    def test_single_response_parses_correctly(self):
        result = parse_decision_response("1a")
        assert result == {1: "a"}

    def test_multi_response_parses_correctly(self):
        result = parse_decision_response("1a, 2c, 3b")
        assert result == {1: "a", 2: "c", 3: "b"}

    def test_response_with_spaces_parses_correctly(self):
        result = parse_decision_response("1a 2b 3c")
        assert result == {1: "a", 2: "b", 3: "c"}

    def test_response_no_spaces_parses_correctly(self):
        result = parse_decision_response("1a2b3c")
        assert result == {1: "a", 2: "b", 3: "c"}

    def test_response_with_mixed_whitespace_parses_correctly(self):
        result = parse_decision_response("1a,2c,  3b")
        assert result == {1: "a", 2: "c", 3: "b"}

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_decision_response("invalid")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_decision_response("")

    def test_returns_dict(self):
        result = parse_decision_response("1a")
        assert isinstance(result, dict)

    def test_multi_digit_question_number(self):
        """Question numbers ≥ 10 are valid (large decision sets)."""
        result = parse_decision_response("10a")
        assert result == {10: "a"}

    def test_response_keys_are_integers(self):
        result = parse_decision_response("1a, 2b")
        for key in result:
            assert isinstance(key, int)

    def test_response_values_are_lowercase_letters(self):
        result = parse_decision_response("1a, 2b, 3c")
        for val in result.values():
            assert val.isalpha()
            assert val.islower()


# ============================================================================
# FRAMEWORK PRINCIPLE: task sequencing vs genuine decisions
# ============================================================================

class TestFrameworkPrinciple:
    """
    Validates the core principle: agents NEVER ask about task ordering/sequencing.
    Only genuine design decisions (technology, architecture, irreversible choices)
    warrant pausing for user input.
    """

    SEQUENCING_PHRASES = [
        "Which task should I start first?",
        "What order should I implement these?",
        "Should I do A or B first?",
        "Which should I tackle first?",
        "What sequence should I follow?",
        "Should I start with the tests or the implementation?",
    ]

    GENUINE_DECISION_PHRASES = [
        "Should we use Redis or in-memory caching?",
        "Should we remove this feature or deprecate it?",
        "Should we use render A or render B?",
        "This will break the public API — should we proceed?",
        "Should we use OAuth or API keys?",
        "Should we use a monolith or microservices?",
    ]

    @pytest.mark.parametrize("phrase", SEQUENCING_PHRASES)
    def test_task_sequencing_is_never_a_decision(self, phrase):
        """
        CRITICAL: Asking users about task ordering is PROHIBITED.
        All sequencing questions must resolve to AUTONOMOUS.
        """
        result = classify_task(phrase)
        assert result == TaskType.AUTONOMOUS, (
            f"Task sequencing question was incorrectly classified as {result}.\n"
            f"Agents MUST NEVER ask: '{phrase}'\n"
            "Sequencing is ALWAYS autonomous."
        )

    @pytest.mark.parametrize("phrase", GENUINE_DECISION_PHRASES)
    def test_genuine_decisions_are_flagged(self, phrase):
        """
        Genuine design decisions (irreversible choices, technology selection,
        architectural trade-offs) MUST be presented to the user.
        """
        result = classify_task(phrase)
        assert result == TaskType.DECISION_NEEDED, (
            f"Genuine decision was incorrectly classified as {result}.\n"
            f"Agents MUST pause and ask the user: '{phrase}'"
        )
