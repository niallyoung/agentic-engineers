"""
conftest.py — pytest configuration for agentic-engineers

Ensures the repo root and src/skills paths are on sys.path so that:
  - from src.orchestration.agents.X import Y
  - from spec-validator.scripts.spec_validator import ...  # from skill
works when running tests from the repo root or any subdirectory.

Key insight: Skills with hyphenated names (spec-validator, spec-management, etc.)
are importable via importlib.import_module() when src/skills/ is in sys.path,
which works around Python's inability to import hyphenated names directly.
"""
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Test isolation: strip inherited git environment variables.
#
# When the test suite runs from inside a git hook (e.g. the pre-push quality
# gate) git exports GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE (and friends) into
# the environment. Any `git` command run by a test — directly, via os.system,
# or in a child shell script such as test_git_push.sh — then inherits those
# variables and operates on the REAL repository regardless of its own cwd or a
# temp fixture remote. That caused fixture commits ("init", "Add task to
# queue", ...) and even live pushes to land on the real worktree/origin.
#
# Stripping these variables at import time (before any test or subprocess runs)
# guarantees git commands in tests resolve their repository from cwd only.
_DANGEROUS_GIT_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_REFLOG_ACTION",
    "GIT_QUARANTINE_PATH",
    "GIT_PUSH_CERT",
    "GIT_INTERNAL_GETTEXT_TEST_FALLBACKS",
)


def _strip_git_env():
    for _var in _DANGEROUS_GIT_ENV:
        os.environ.pop(_var, None)


_strip_git_env()


# Get repo root (where conftest.py lives)
repo_root = str(Path(__file__).parent.absolute())

# Ensure repo root is in sys.path (at beginning for priority)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Add src/skills to sys.path so we can import hyphenated skill packages
skills_path = os.path.join(repo_root, "src", "skills")
if os.path.exists(skills_path) and skills_path not in sys.path:
    sys.path.insert(0, skills_path)

# Ensure PYTHONPATH environment variable is set for subprocesses
if os.path.exists(skills_path):
    os.environ['PYTHONPATH'] = skills_path + os.pathsep + repo_root + os.pathsep + os.environ.get('PYTHONPATH', '')


def pytest_configure(config):
    """Re-strip inherited git env vars before collection.

    The sys.path setup is done at module import time above, which always runs
    before this hook; repeating it here would be a no-op.
    """
    _strip_git_env()


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_git_env():
    """Ensure no inherited/leaked git env vars point tests at the real repo."""
    _strip_git_env()
    yield
    _strip_git_env()
