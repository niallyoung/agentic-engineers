"""
tests/conftest.py — Shared pytest fixtures and utilities for agentic-engineers tests.

Provides common DELEGATE/HANDBACK factory functions and fixtures to eliminate
duplication across test modules. Import via pytest fixture injection or directly.

Usage (fixture injection):
    def test_something(delegate_block, handback_block):
        ...

Usage (direct import):
    from tests.conftest import make_delegate, make_handback
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, Optional

# Import queue test helpers (fixtures for isolated/legacy queues)
from tests.helpers.queue_test_helpers import (
    isolated_queue_env,
    isolated_queue_copilot,
    isolated_queue_claude,
    legacy_queue_env,
    queue_test_env,
    assert_queue_path_is_isolated,
    assert_queue_path_is_legacy,
    assert_queue_subdirs_exist,
)


# ---------------------------------------------------------------------------
# Test Source Audit (Solution 3: Prevent bytecode cache loading)
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """
    Clear pytest cache at session start to force fresh test discovery.
    
    This prevents pytest from loading tests from .pyc bytecode cache when
    .py source files are missing. Especially important for background agents
    that create test files - if source is missing, we want to catch it NOW
    (at collection time) not later (when test tries to run).
    """
    cache_dir = os.path.join(os.getcwd(), '.pytest_cache')
    if os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
            print("\n🧹 Cleared .pytest_cache (force fresh test discovery)")
        except Exception as e:
            print(f"\n⚠️  Could not clear .pytest_cache: {e}")


def pytest_collection_modifyitems(session, config, items):
    """
    Audit: Verify all collected tests come from .py source files (not .pyc cache).
    
    This is critical for detecting when background agents create test files but
    forget to commit the source. Pytest might load the .pyc from cache, masking
    the missing source until tests try to run.
    
    Validation:
    1. Each test must come from a .py file (not .pyc)
    2. The .py file must exist on disk
    3. The .py file should be tracked in git (for background agent files)
    """
    print("\n🔍 Audit: Test Source Integrity")
    
    missing_sources = []
    untracked_tests = []
    
    for item in items:
        # Get the test's source file path
        test_file = item.fspath.strpath
        
        # 1. Verify it's a .py file, not .pyc
        if not test_file.endswith('.py'):
            error_msg = f"   ❌ Test from bytecode cache: {test_file}"
            print(error_msg)
            missing_sources.append(test_file)
            continue
        
        # 2. Verify the .py file exists on disk
        if not os.path.isfile(test_file):
            error_msg = f"   ❌ Test source missing: {test_file}"
            print(error_msg)
            missing_sources.append(test_file)
            continue
        
        # 3. Verify the .py file is tracked in git (if in skills/ or src/)
        # This catches untracked test sources from background agents
        if ('skills/' in test_file or 'src/' in test_file) and '/tests/' not in test_file:
            try:
                result = os.system(f"git ls-files '{test_file}' > /dev/null 2>&1")
                if result != 0:
                    untracked_msg = f"   ⚠️  Test source not tracked in git: {test_file}"
                    print(untracked_msg)
                    untracked_tests.append(test_file)
            except Exception:
                pass  # Ignore git check failures in non-git environments
    
    # 4. Fail if any sources are missing (tests from orphaned bytecode)
    if missing_sources:
        error_msg = (
            "\n❌ TEST SOURCE AUDIT FAILED\n"
            "Some tests are from bytecode cache without .py source:\n"
        )
        for src in missing_sources:
            error_msg += f"   - {src}\n"
        error_msg += (
            "\nFIX: Clear cache and re-run pytest:\n"
            "   rm -rf .pytest_cache __pycache__\n"
            "   pytest --cache-clear\n"
        )
        print(error_msg)
        pytest.exit(error_msg, returncode=1)
    
    if untracked_tests:
        print(f"\n⚠️  {len(untracked_tests)} test source(s) not tracked in git")
        print("   This is OK for development, but background agents MUST commit test sources")
    
    print(f"✅ Test source audit passed: {len(items)} tests from valid .py sources")


# ---------------------------------------------------------------------------
# Factory functions (importable directly, not just as fixtures)
# ---------------------------------------------------------------------------


def make_delegate(
    task_id: str = "2026-01-01-test-task",
    role: str = "engineer",
    effort: str = "medium",
    model: str = "claude-haiku-4-5",
    scope: str = "Test scope",
    context: Optional[list] = None,
    plan: Optional[list] = None,
    success_criteria: Optional[list] = None,
    **overrides,
) -> Dict:
    """
    Create a minimal valid DELEGATE block for testing.

    All parameters have sensible defaults. Use ``**overrides`` to set any
    additional or non-default fields.

    Example::

        make_delegate(task_id="my-task", role="senior_engineer", effort="high")
        make_delegate(is_security_scoped=True)
    """
    block = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": role,
        "model": model,
        "effort": effort,
        "scope": scope,
        "context": context if context is not None else ["File: test.py"],
        "plan": plan if plan is not None else ["1. Write test", "2. Verify"],
        "success_criteria": success_criteria if success_criteria is not None else ["Tests pass"],
    }
    block.update(overrides)
    return block


def make_handback(
    task_id: str = "2026-01-01-test-task",
    status: str = "complete",
    quality_score: int = 90,
    tokens_in: int = 1000,
    tokens_out: int = 500,
    cost_usd: float = 0.05,
    effort_actual: float = 0.5,
    **overrides,
) -> Dict:
    """
    Create a minimal valid HANDBACK block for testing.

    All parameters have sensible defaults. Use ``**overrides`` to set any
    additional or non-default fields.

    Example::

        make_handback(quality_score=75, status="complete")
        make_handback(task_id="my-task", tokens_in=2000, tokens_out=800)
    """
    block = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": status,
        "quality_score": quality_score,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "effort_actual": effort_actual,
        "deliverables": [],
        "tests": {"passed": 10, "failed": 0, "coverage": 95.0},
    }
    block.update(overrides)
    return block


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def delegate_block() -> Dict:
    """Minimal valid DELEGATE block."""
    return make_delegate()


@pytest.fixture
def handback_block() -> Dict:
    """Minimal valid HANDBACK block."""
    return make_handback()


@pytest.fixture
def high_quality_handback() -> Dict:
    """HANDBACK with high quality score (90+), triggers PROCEED."""
    return make_handback(quality_score=95)


@pytest.fixture
def low_quality_handback() -> Dict:
    """HANDBACK with low quality score (<60), triggers ESCALATE."""
    return make_handback(quality_score=45)


@pytest.fixture
def gray_zone_handback() -> Dict:
    """HANDBACK with gray-zone quality score (70-79), triggers MANUAL_REVIEW."""
    return make_handback(quality_score=74)


@pytest.fixture
def tmp_queue(tmp_path: Path) -> Path:
    """
    Temporary queue directory with incoming/processing/done subdirectories.

    Returns the base queue path. Subdirectories are pre-created.
    """
    for subdir in ("incoming", "processing", "done"):
        (tmp_path / subdir).mkdir(parents=True)
    return tmp_path


@pytest.fixture(scope="session", autouse=True)
def regenerate_dist():
    """
    Auto-regenerate dist/ from src/ before any tests run.
    
    This fixture runs once per test session (before all tests) and ensures dist/
    is populated from source. This allows dist/ to be kept out of git (as a
    generated artifact) while tests can still validate the render pipeline.
    
    Triggered automatically for all tests (autouse=True).
    """
    repo_root = Path(__file__).resolve().parent.parent
    render_targets = [
        "render-copilot",
        "render-claude",
        "render-opencode",
        "render-pi",
        "render-specs"
    ]
    
    # Check if dist/ is empty (needs regeneration)
    dist_dir = repo_root / "dist"
    dist_is_empty = not any(dist_dir.glob("*"))
    
    if dist_is_empty:
        print("\n🔨 Regenerating dist/ from src/ before tests...\n")
        for target in render_targets:
            result = os.system(f"cd {repo_root} && make {target} > /dev/null 2>&1")
            if result != 0:
                print(f"⚠️  make {target} failed (non-critical for tests)")
        print("✅ dist/ regenerated\n")
