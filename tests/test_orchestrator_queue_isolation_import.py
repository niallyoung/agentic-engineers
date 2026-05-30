"""
Regression tests for the orchestrator's queue-isolation import path.

The queue-isolation module physically lives at:

    src/skills/_meta/queue-isolation/scripts/queue_isolation.py

The package directory uses a hyphen (``queue-isolation``), which is not a valid
Python module path. Previously the orchestrator only attempted the dotted import
``src.skills._meta.queue_isolation.scripts`` (underscore), which can never
resolve against the hyphenated directory. As a result ``_QUEUE_ISOLATION`` was
always ``None`` and queue isolation was silently disabled in the orchestrator,
even though ``invoke_agent.py`` loaded the module fine via a sys.path fallback.

These tests prove the orchestrator now imports the real module the same way its
runtime siblings do.
"""

from pathlib import Path

from src.orchestration.agents import orchestrator as orch


EXPECTED_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "src" / "skills" / "_meta" / "queue-isolation" / "scripts" / "queue_isolation.py"
)


def test_try_import_queue_isolation_returns_real_module():
    """The orchestrator helper resolves the hyphenated-dir module, not None."""
    qi = orch._try_import_queue_isolation()

    assert qi is not None, (
        "orchestrator._try_import_queue_isolation() must load the queue_isolation "
        "module from the hyphenated 'queue-isolation' scripts directory"
    )
    # Confirm it is the real module on disk, not a stub.
    assert Path(qi.__file__).resolve() == EXPECTED_MODULE_PATH


def test_module_level_queue_isolation_is_wired():
    """The module-level cache must be populated at import time."""
    assert orch._QUEUE_ISOLATION is not None, (
        "orchestrator._QUEUE_ISOLATION should be populated on import so queue "
        "isolation is active rather than silently falling back to legacy paths"
    )


def test_orchestrator_and_invoke_agent_share_same_module():
    """Both orchestration entrypoints must resolve the identical module."""
    from src.orchestration.agents import invoke_agent as ia

    assert ia._QUEUE_ISOLATION is not None
    assert (
        Path(orch._QUEUE_ISOLATION.__file__).resolve()
        == Path(ia._QUEUE_ISOLATION.__file__).resolve()
    )
