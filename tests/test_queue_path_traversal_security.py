"""Security regression tests: queue path traversal / queue poisoning.

These tests pin the defence-in-depth guards added to the harness/queue
subsystem to prevent attacker-controlled ``task_id`` / ``status`` / ``decision``
values (read from DELEGATE/HANDBACK YAML) and ``session_id`` / ``harness``
values (read from the environment) from escaping the canonical queue root via
``..``, absolute paths, or embedded path separators.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.orchestration.agents.orchestrator import (  # noqa: E402
    sanitize_path_component,
    ensure_within_directory,
)


def _load_queue_isolation():
    spec = importlib.util.spec_from_file_location(
        "queue_isolation_under_test",
        _REPO_ROOT
        / "src"
        / "skills"
        / "_meta"
        / "queue-isolation"
        / "scripts"
        / "queue_isolation.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MALICIOUS_COMPONENTS = [
    "../evil",
    "../../etc/passwd",
    "/etc/passwd",
    "a/b",
    "a\\b",
    "..",
    ".",
    "",
    "task\x00id",
    "foo bar",  # spaces are not in the safe set
]

SAFE_COMPONENTS = [
    "TASK-REVIEW-HARNESS-001",
    "session-A",
    "my-task-123",
    "task_id.v2",
    "ACCEPT",
]


class TestSanitizePathComponent:
    @pytest.mark.parametrize("value", MALICIOUS_COMPONENTS)
    def test_rejects_malicious(self, value):
        with pytest.raises(ValueError):
            sanitize_path_component(value, field="task_id")

    @pytest.mark.parametrize("value", SAFE_COMPONENTS)
    def test_allows_safe(self, value):
        assert sanitize_path_component(value, field="task_id") == value

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            sanitize_path_component(123, field="task_id")


class TestEnsureWithinDirectory:
    def test_allows_child(self, tmp_path):
        target = tmp_path / "done" / "ok.yaml"
        (tmp_path / "done").mkdir()
        assert ensure_within_directory(target, tmp_path / "done") == target.resolve()

    def test_rejects_escape(self, tmp_path):
        base = tmp_path / "done"
        base.mkdir()
        target = base / ".." / ".." / "escape.yaml"
        with pytest.raises(ValueError):
            ensure_within_directory(target, base)


class TestQueueIsolationTraversal:
    def test_get_queue_path_rejects_session_traversal(self, tmp_path):
        qi = _load_queue_isolation()
        with pytest.raises(ValueError):
            qi.get_queue_path("../../../../etc", "claude", base_dir=tmp_path)

    def test_get_queue_path_rejects_harness_traversal(self, tmp_path):
        qi = _load_queue_isolation()
        with pytest.raises(ValueError):
            qi.get_queue_path("session-001", "../../etc", base_dir=tmp_path)

    def test_get_queue_path_rejects_absolute_session(self, tmp_path):
        qi = _load_queue_isolation()
        with pytest.raises(ValueError):
            qi.get_queue_path("/etc/passwd", "claude", base_dir=tmp_path)

    def test_get_queue_path_allows_canonical(self, tmp_path):
        qi = _load_queue_isolation()
        result = qi.get_queue_path("session-001", "claude", base_dir=tmp_path)
        expected = tmp_path / "artifacts" / "session-001" / "claude" / "queue"
        assert result == expected
        # Resolved path must stay within the canonical artifacts root.
        assert (tmp_path / "artifacts").resolve() in result.resolve().parents

    def test_init_queue_structure_rejects_traversal(self, tmp_path):
        qi = _load_queue_isolation()
        with pytest.raises(ValueError):
            qi.init_queue_structure("../poison", "claude", base_dir=tmp_path)
        # Nothing must have been created outside the artifacts root.
        assert not (tmp_path.parent / "poison").exists()
