# -*- coding: utf-8 -*-
"""
task_orchestrator.py — task-orchestration skill core implementation.

Encodes the autonomous task execution framework principle:
  "Maximize throughput by parallelizing all independent tasks.
   Pause only for genuine decisions (not task sequencing)."

Components:
    TaskType              — Enum: AUTONOMOUS | DECISION_NEEDED | SEQUENTIAL_ONLY
    Task                  — Dataclass: id, description, dependencies, touches_files
    classify_task()       — Classify a task description into a TaskType
    can_parallelize()     — Determine if a list of tasks can run in parallel
    generate_decision_shorthand() — Format options as "1a. Option / 1b. Option / ..."
    parse_decision_response()     — Parse "1a, 2c, 3b" → {1: 'a', 2: 'c', 3: 'b'}

Author: Senior Engineer
Phase: TDD GREEN-phase (implements RED-phase test spec in tests/test_task_orchestration.py)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class TaskType(Enum):
    """Classification of an agent task with respect to autonomous execution.

    AUTONOMOUS
        The agent executes this task without pausing for user input.
        Includes ALL task-sequencing and ordering questions — agents must
        never ask "which task should I do first?" or "what order?".

    DECISION_NEEDED
        A genuine design, architectural, or irreversible choice that requires
        user input before the agent can proceed.  Examples: technology
        selection ("Redis vs in-memory"), breaking-change confirmation,
        deprecate-vs-remove choices.

    SEQUENTIAL_ONLY
        The task has explicit dependencies (build→test, migrate→seed) that
        prevent safe parallel execution.
    """

    AUTONOMOUS = "autonomous"
    DECISION_NEEDED = "decision_needed"
    SEQUENTIAL_ONLY = "sequential_only"


@dataclass
class Task:
    """Represents a unit of work for an agent.

    Attributes:
        id:            Unique short identifier (e.g. "build", "test-auth").
        description:   Human-readable description of the work.
        dependencies:  IDs of tasks that must complete before this one starts.
        touches_files: File paths modified by this task (used for conflict detection).
    """

    id: str
    description: str
    dependencies: List[str]
    touches_files: List[str] = field(default_factory=list)


# ============================================================================
# KEYWORD SETS — used by classify_task()
# ============================================================================

# Phrases that indicate pure task-sequencing questions.
# These MUST resolve to AUTONOMOUS — agents should never ask the user.
_SEQUENCING_PATTERNS = [
    r"\bwhich task\b.*\bfirst\b",
    r"\bwhat order\b",
    r"\bwhich.*order\b",
    r"\bwhat sequence\b",
    r"\bshould i (start|do|tackle|begin|work on)\b.*(first|before|then)\b",
    r"\b(start|tackle|begin) with\b",
    r"\bshould i do .* or .* first\b",
    r"\bwhich should i (start|tackle|begin)\b",
]

# Phrases that signal a genuine decision requiring user input.
_DECISION_PATTERNS = [
    # Technology choices between named alternatives
    r"\bshould we use\b.+\bor\b",
    r"\bshould we (go with|adopt|choose|pick|select)\b",
    # Remove vs deprecate (word order may vary)
    r"\bremove\b.*\bdeprecate\b",
    r"\bdeprecate\b.*\bremove\b",
    r"\b(remove|delete).*\bor\b.*(deprecat|keep|retain)\b",
    r"\b(deprecat).*\bor\b.*(remove|delete|keep)\b",
    # Architectural patterns
    r"\b(monolith|microservice|serverless|event.driven)\b.*(or|vs|versus)\b",
    r"\bshould we (use|adopt|keep|switch|migrate)\b.*(or|vs|versus)\b",
    # Breaking changes / irreversible actions
    r"\bbreak.*(public|api|interface|contract)\b",
    r"\bshould we proceed\b",
    r"\bshould we (continue|go ahead)\b",
    # "render A or render B" style
    r"\brender [a-z]\b.*(or|vs)\b.*\brender [a-z]\b",
    # OAuth / API keys / auth strategy choices
    r"\b(oauth|api key|jwt|session|saml)\b.*(or|vs|versus)\b",
    r"\b(or|vs|versus)\b.*(oauth|api key|jwt|session|saml)\b",
]

# Patterns that indicate explicit sequential dependencies (build→test etc.)
_SEQUENTIAL_MARKERS = [
    r"\b(build|compile|package)\b.{1,30}\b(then|before|after)\b.{1,30}\b(deploy|test|run)\b",
    r"\b(run|execute).{0,30}\b(migrations?|migrate)\b.{0,60}\b(then|before|after)\b",
    r"\b(migrations?|migrate)\b.{0,60}\b(then|before|after)\b.{0,30}\b(test|run|seed)\b",
    r"\bthen\b.{1,60}\bthen\b",  # "do X, then Y, then Z" — sequential pipeline
]


def classify_task(description: str) -> TaskType:
    """Classify a task description into a TaskType.

    **Framework principle**: sequencing questions are ALWAYS AUTONOMOUS.
    The agent never asks the user which order to do things.

    Args:
        description: Natural-language description of the task or question.

    Returns:
        TaskType.AUTONOMOUS       — proceed without user input (incl. all sequencing)
        TaskType.SEQUENTIAL_ONLY  — has explicit ordering dependencies
        TaskType.DECISION_NEEDED  — genuine design/arch decision requiring user choice
    """
    text = description.lower()

    # ── 1. Sequencing check (highest priority) ───────────────────────────────
    # Any question about ordering/sequencing resolves to AUTONOMOUS.
    # Agents never ask users which task to start first.
    for pattern in _SEQUENCING_PATTERNS:
        if re.search(pattern, text):
            return TaskType.AUTONOMOUS

    # ── 2. Sequential dependency markers ─────────────────────────────────────
    for pattern in _SEQUENTIAL_MARKERS:
        if re.search(pattern, text):
            return TaskType.SEQUENTIAL_ONLY

    # ── 3. Genuine decision patterns ──────────────────────────────────────────
    for pattern in _DECISION_PATTERNS:
        if re.search(pattern, text):
            return TaskType.DECISION_NEEDED

    # ── 4. Default: autonomous ────────────────────────────────────────────────
    return TaskType.AUTONOMOUS


# ============================================================================
# can_parallelize
# ============================================================================

def can_parallelize(tasks: List[Task]) -> bool:
    """Determine whether a list of tasks can safely run in parallel.

    Checks:
      1. At least 2 tasks are present.
      2. No task has an explicit dependency on another task in the list.
      3. No two tasks modify overlapping files (git conflict prevention).

    Args:
        tasks: List of Task objects to evaluate.

    Returns:
        True  — all tasks are independent and may be dispatched simultaneously.
        False — at least one dependency or file conflict prevents parallelism.
    """
    if len(tasks) < 2:
        return False

    task_ids = {t.id for t in tasks}

    # ── Check explicit dependencies ──────────────────────────────────────────
    for task in tasks:
        for dep in task.dependencies:
            if dep in task_ids:
                return False

    # ── Check filesystem / git conflicts ─────────────────────────────────────
    seen_files: set = set()
    for task in tasks:
        for f in task.touches_files:
            if f in seen_files:
                return False
            seen_files.add(f)

    return True


# ============================================================================
# generate_decision_shorthand
# ============================================================================

def generate_decision_shorthand(
    options: List[str],
    question_number: int = 1,
) -> str:
    """Format a list of options as the canonical decision shorthand.

    Produces a compact, scannable multi-line string where each option is
    labelled ``{question_number}{letter}.`` for fast user response.

    Example::

        generate_decision_shorthand(["Use Redis", "Use in-memory"], question_number=1)
        # →
        # 1a. Use Redis
        # 1b. Use in-memory

    Args:
        options:         Non-empty list of option strings.
        question_number: 1-based index for this question (default 1).
                         Use 2, 3, … when presenting multiple decisions at once.

    Returns:
        Formatted shorthand string (one option per line).

    Raises:
        ValueError: If ``options`` is empty.
    """
    if not options:
        raise ValueError("options must be a non-empty list")

    letters = "abcdefghijklmnopqrstuvwxyz"
    lines: List[str] = []
    for i, opt in enumerate(options):
        letter = letters[i % len(letters)]
        lines.append(f"{question_number}{letter}. {opt}")
    return "\n".join(lines)


# ============================================================================
# parse_decision_response
# ============================================================================

def parse_decision_response(shorthand: str) -> Dict[int, str]:
    """Parse a user's shorthand decision response into a structured dict.

    Accepts responses in the format ``{number}{letter}`` separated by any
    combination of spaces, commas, or no separator.

    Examples::

        parse_decision_response("1a")           → {1: "a"}
        parse_decision_response("1a, 2c, 3b")   → {1: "a", 2: "c", 3: "b"}
        parse_decision_response("1a2b3c")        → {1: "a", 2: "b", 3: "c"}

    Args:
        shorthand: Raw user response string.

    Returns:
        Mapping from question number (int) to chosen letter (str).

    Raises:
        ValueError: If the string is empty or contains no valid tokens.
    """
    if not shorthand or not shorthand.strip():
        raise ValueError("shorthand response must not be empty")

    # Extract all (number, letter) pairs — tolerates any separator
    tokens = re.findall(r"(\d+)([a-z])", shorthand.lower())

    if not tokens:
        raise ValueError(
            f"No valid shorthand tokens found in response: {shorthand!r}. "
            "Expected format: '1a', '2c', '1a, 2c, 3b', etc."
        )

    return {int(num): letter for num, letter in tokens}
