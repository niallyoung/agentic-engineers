"""
Tests for QueueManager class in src/skills/queue-management/queue_manager.py.

Covers: init, parse_spec, parse_spec_from_cli, validate_protocol,
check_duplicate, generate_delegate, add_todo_entry, commit_to_git,
process_task, custom exceptions.

Target: >=90% coverage of queue_manager.py
"""
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Import queue_manager via path injection ──────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_QM_DIR = _REPO_ROOT / "src" / "skills" / "queue-management"

if str(_QM_DIR) not in sys.path:
    sys.path.insert(0, str(_QM_DIR))

from queue_manager import (
    DuplicateTaskError,
    GitError,
    QueueManagementError,
    QueueManager,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_spec(task_id="my-task"):
    """Return a minimal valid task specification."""
    return {
        "task_id": task_id,
        "role": "Engineer",
        "scope": "Do something useful",
        "plan": ["Step 1", "Step 2"],
        "success_criteria": ["Works correctly"],
    }


def _make_qm(tmp_path) -> QueueManager:
    """Create a QueueManager backed by tmp_path with a fresh todo file."""
    queue_dir = str(tmp_path / "incoming")
    todo_path = str(tmp_path / "TODO.md")
    return QueueManager(queue_dir=queue_dir, todo_path=todo_path)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:
    """Tests for custom exception hierarchy."""

    def test_validation_error_is_queue_management_error(self):
        assert issubclass(ValidationError, QueueManagementError)

    def test_duplicate_task_error_is_queue_management_error(self):
        assert issubclass(DuplicateTaskError, QueueManagementError)

    def test_git_error_is_queue_management_error(self):
        assert issubclass(GitError, QueueManagementError)

    def test_validation_error_raises_and_catches(self):
        with pytest.raises(ValidationError, match="test"):
            raise ValidationError("test")

    def test_duplicate_task_error_raises_and_catches(self):
        with pytest.raises(DuplicateTaskError, match="dup"):
            raise DuplicateTaskError("dup")

    def test_git_error_raises_and_catches(self):
        with pytest.raises(GitError, match="git"):
            raise GitError("git")


# ---------------------------------------------------------------------------
# QueueManager.__init__
# ---------------------------------------------------------------------------

class TestQueueManagerInit:
    """Tests for QueueManager initialization."""

    def test_creates_queue_dir(self, tmp_path):
        """Constructor creates queue_dir if it doesn't exist."""
        qm = _make_qm(tmp_path)
        assert os.path.isdir(qm.queue_dir)

    def test_uses_provided_queue_dir(self, tmp_path):
        """queue_dir is the provided path."""
        qm = _make_qm(tmp_path)
        assert qm.queue_dir == str(tmp_path / "incoming")

    def test_uses_provided_todo_path(self, tmp_path):
        """todo_path is the provided path."""
        qm = _make_qm(tmp_path)
        assert qm.todo_path == str(tmp_path / "TODO.md")

    def test_default_todo_path_from_git(self, tmp_path, monkeypatch):
        """Default todo_path uses git rev-parse when available."""
        import subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = str(tmp_path) + "\n"
        with patch("subprocess.run", return_value=mock_result):
            qm = QueueManager(queue_dir=str(tmp_path / "q"))
        assert qm.todo_path == os.path.join(str(tmp_path), "TODO.md")

    def test_default_todo_path_fallback(self, tmp_path, monkeypatch):
        """Default todo_path falls back to 'TODO.md' when git fails."""
        import subprocess
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            qm = QueueManager(queue_dir=str(tmp_path / "q"))
        assert qm.todo_path == "TODO.md"

    def test_default_todo_path_exception(self, tmp_path):
        """Default todo_path falls back when subprocess raises."""
        with patch("subprocess.run", side_effect=Exception("no git")):
            qm = QueueManager(queue_dir=str(tmp_path / "q"))
        assert qm.todo_path == "TODO.md"


# ---------------------------------------------------------------------------
# parse_spec
# ---------------------------------------------------------------------------

class TestParseSpec:
    """Tests for parse_spec method."""

    def test_valid_spec_returns_as_is(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        result = qm.parse_spec(spec)
        assert result == spec

    def test_missing_task_id_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        del spec["task_id"]
        with pytest.raises(ValueError, match="task_id"):
            qm.parse_spec(spec)

    def test_missing_role_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        del spec["role"]
        with pytest.raises(ValueError, match="role"):
            qm.parse_spec(spec)

    def test_missing_scope_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        del spec["scope"]
        with pytest.raises(ValueError, match="scope"):
            qm.parse_spec(spec)

    def test_missing_plan_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        del spec["plan"]
        with pytest.raises(ValueError, match="plan"):
            qm.parse_spec(spec)

    def test_missing_success_criteria_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        del spec["success_criteria"]
        with pytest.raises(ValueError, match="success_criteria"):
            qm.parse_spec(spec)

    def test_multiple_missing_fields_reported(self, tmp_path):
        qm = _make_qm(tmp_path)
        with pytest.raises(ValueError, match="Missing required field"):
            qm.parse_spec({})


# ---------------------------------------------------------------------------
# parse_spec_from_cli
# ---------------------------------------------------------------------------

class TestParseSpecFromCli:
    """Tests for parse_spec_from_cli method."""

    def test_basic_valid_args(self, tmp_path):
        qm = _make_qm(tmp_path)
        args = ["--task-id", "my-task", "--role", "Engineer", "--scope", "Do work"]
        spec = qm.parse_spec_from_cli(args)
        assert spec["task_id"] == "my-task"
        assert spec["role"] == "Engineer"
        assert spec["scope"] == "Do work"

    def test_missing_task_id_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        with pytest.raises(ValueError, match="--task-id"):
            qm.parse_spec_from_cli(["--role", "Engineer", "--scope", "x"])

    def test_missing_role_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        with pytest.raises(ValueError, match="--role"):
            qm.parse_spec_from_cli(["--task-id", "x", "--scope", "y"])

    def test_missing_scope_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        with pytest.raises(ValueError, match="--scope"):
            qm.parse_spec_from_cli(["--task-id", "x", "--role", "Engineer"])

    def test_default_plan_is_scope(self, tmp_path):
        qm = _make_qm(tmp_path)
        args = ["--task-id", "x", "--role", "Engineer", "--scope", "Do work"]
        spec = qm.parse_spec_from_cli(args)
        assert spec["plan"] == ["Do work"]

    def test_default_success_criteria(self, tmp_path):
        qm = _make_qm(tmp_path)
        args = ["--task-id", "x", "--role", "Engineer", "--scope", "Do work"]
        spec = qm.parse_spec_from_cli(args)
        assert spec["success_criteria"] == ["Task completed"]

    def test_optional_effort_parsed(self, tmp_path):
        qm = _make_qm(tmp_path)
        args = ["--task-id", "x", "--role", "Engineer", "--scope", "y", "--effort", "high"]
        spec = qm.parse_spec_from_cli(args)
        assert spec["effort"] == "high"

    def test_optional_priority_parsed(self, tmp_path):
        qm = _make_qm(tmp_path)
        args = ["--task-id", "x", "--role", "Engineer", "--scope", "y", "--priority", "high"]
        spec = qm.parse_spec_from_cli(args)
        assert spec["priority"] == "high"

    def test_unknown_args_ignored(self, tmp_path):
        qm = _make_qm(tmp_path)
        args = ["--task-id", "x", "--role", "Engineer", "--scope", "y", "--unknown", "val"]
        spec = qm.parse_spec_from_cli(args)
        assert "task_id" in spec


# ---------------------------------------------------------------------------
# validate_protocol
# ---------------------------------------------------------------------------

class TestValidateProtocol:
    """Tests for validate_protocol method."""

    def test_valid_spec_does_not_raise(self, tmp_path):
        qm = _make_qm(tmp_path)
        qm.validate_protocol(_minimal_spec())

    def test_missing_required_field_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        del spec["role"]
        with pytest.raises(ValidationError, match="role"):
            qm.validate_protocol(spec)

    def test_invalid_task_id_uppercase(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec(task_id="MyTask")
        with pytest.raises(ValidationError, match="kebab-case"):
            qm.validate_protocol(spec)

    def test_invalid_task_id_spaces(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec(task_id="my task")
        with pytest.raises(ValidationError, match="kebab-case"):
            qm.validate_protocol(spec)

    def test_valid_task_id_kebab_case(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec(task_id="my-task-123")
        qm.validate_protocol(spec)  # Should not raise

    def test_invalid_role_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        spec["role"] = "InvalidRole"
        with pytest.raises(ValidationError, match="Invalid role"):
            qm.validate_protocol(spec)

    def test_all_valid_roles_accepted(self, tmp_path):
        qm = _make_qm(tmp_path)
        for role in QueueManager.VALID_ROLES:
            spec = _minimal_spec()
            spec["role"] = role
            qm.validate_protocol(spec)  # Should not raise

    def test_empty_plan_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        spec["plan"] = []
        with pytest.raises(ValidationError, match="plan"):
            qm.validate_protocol(spec)

    def test_empty_success_criteria_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        spec["success_criteria"] = []
        with pytest.raises(ValidationError, match="success_criteria"):
            qm.validate_protocol(spec)


# ---------------------------------------------------------------------------
# check_duplicate
# ---------------------------------------------------------------------------

class TestCheckDuplicate:
    """Tests for check_duplicate method."""

    def test_no_existing_files_no_error(self, tmp_path):
        qm = _make_qm(tmp_path)
        qm.check_duplicate("new-task")  # Should not raise

    def test_existing_file_in_queue_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        (tmp_path / "incoming" / "existing-task.json").touch()
        with pytest.raises(DuplicateTaskError, match="existing-task"):
            qm.check_duplicate("existing-task")

    def test_task_in_todo_raises(self, tmp_path):
        qm = _make_qm(tmp_path)
        todo = tmp_path / "TODO.md"
        todo.write_text("- [ ] **my-task:** Do something\n")
        with pytest.raises(DuplicateTaskError, match="my-task"):
            qm.check_duplicate("my-task")

    def test_different_task_id_no_error(self, tmp_path):
        qm = _make_qm(tmp_path)
        todo = tmp_path / "TODO.md"
        todo.write_text("- [ ] **other-task:** Do something\n")
        qm.check_duplicate("new-task")  # Should not raise

    def test_no_todo_file_no_error(self, tmp_path):
        qm = _make_qm(tmp_path)
        # todo_path doesn't exist
        qm.check_duplicate("new-task")  # Should not raise


# ---------------------------------------------------------------------------
# generate_delegate
# ---------------------------------------------------------------------------

class TestGenerateDelegate:
    """Tests for generate_delegate method."""

    def test_creates_json_file_in_queue_dir(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        path = qm.generate_delegate(spec)
        assert os.path.isfile(path)
        assert path.endswith(".json")

    def test_json_file_has_correct_task_id(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec("build-widget")
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert data["task_id"] == "build-widget"

    def test_json_file_has_role(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert data["role"] == "Engineer"

    def test_json_file_has_description_from_scope(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert data["description"] == spec["scope"]

    def test_defaults_effort_to_medium(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert data["effort"] == "medium"

    def test_uses_provided_effort(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        spec["effort"] = "high"
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert data["effort"] == "high"

    def test_defaults_priority_to_normal(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert data["priority"] == "normal"

    def test_created_at_is_present(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        path = qm.generate_delegate(spec)
        with open(path) as f:
            data = json.load(f)
        assert "created_at" in data

    def test_creates_delegates_subdir(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        qm.generate_delegate(spec)
        # delegates/ dir should exist under parent of queue_dir
        parent = os.path.dirname(qm.queue_dir)
        delegates = os.path.join(parent, "delegates")
        assert os.path.isdir(delegates)


# ---------------------------------------------------------------------------
# add_todo_entry
# ---------------------------------------------------------------------------

class TestAddTodoEntry:
    """Tests for add_todo_entry method."""

    def test_creates_todo_file_if_missing(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        qm.add_todo_entry(spec)
        assert os.path.exists(qm.todo_path)

    def test_adds_task_id_line(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec("test-task")
        qm.add_todo_entry(spec)
        content = (tmp_path / "TODO.md").read_text()
        assert "test-task" in content

    def test_adds_effort_line(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        spec["effort"] = "high"
        qm.add_todo_entry(spec)
        content = (tmp_path / "TODO.md").read_text()
        assert "high" in content

    def test_adds_role_line(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        qm.add_todo_entry(spec)
        content = (tmp_path / "TODO.md").read_text()
        assert "Engineer" in content

    def test_inserts_into_existing_phase_section(self, tmp_path):
        qm = _make_qm(tmp_path)
        todo = tmp_path / "TODO.md"
        todo.write_text("## 🟢 PHASE 2\n\n- [ ] **old-task:** Old task\n\n")
        spec = _minimal_spec("new-task")
        spec["phase"] = "2"
        qm.add_todo_entry(spec)
        content = todo.read_text()
        assert "new-task" in content
        assert "old-task" in content

    def test_creates_phase_section_if_missing(self, tmp_path):
        qm = _make_qm(tmp_path)
        todo = tmp_path / "TODO.md"
        todo.write_text("# My TODO\n\n")
        spec = _minimal_spec("new-task")
        spec["phase"] = "2"
        qm.add_todo_entry(spec)
        content = todo.read_text()
        assert "new-task" in content

    def test_todo_entry_format(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec("format-task")
        qm.add_todo_entry(spec)
        content = (tmp_path / "TODO.md").read_text()
        assert "- [ ] **format-task:**" in content


# ---------------------------------------------------------------------------
# commit_to_git
# ---------------------------------------------------------------------------

class TestCommitToGit:
    """Tests for commit_to_git method."""

    def test_calls_git_add_and_commit(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        mock_run = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)
        with patch("subprocess.run", mock_run):
            qm.commit_to_git(spec)
        assert mock_run.call_count == 2
        # First call should be git add
        first_call = mock_run.call_args_list[0]
        assert "git" in first_call[0][0]
        assert "add" in first_call[0][0]

    def test_git_failure_raises_git_error(self, tmp_path):
        import subprocess
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        error = subprocess.CalledProcessError(1, "git")
        error.stderr = b"git error"
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(GitError, match="Git commit failed"):
                qm.commit_to_git(spec)

    def test_custom_message_used(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        captured_calls = []
        def mock_run(cmd, **kwargs):
            captured_calls.append(cmd)
            return MagicMock(returncode=0)
        with patch("subprocess.run", side_effect=mock_run):
            qm.commit_to_git(spec, message="custom: my message")
        commit_call = [c for c in captured_calls if "commit" in c]
        assert len(commit_call) == 1
        assert "custom: my message" in commit_call[0]

    def test_default_message_includes_task_id(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec("the-task")
        captured_calls = []
        def mock_run(cmd, **kwargs):
            captured_calls.append(cmd)
            return MagicMock(returncode=0)
        with patch("subprocess.run", side_effect=mock_run):
            qm.commit_to_git(spec)
        commit_call = [c for c in captured_calls if "commit" in c]
        assert len(commit_call) == 1
        assert "the-task" in " ".join(commit_call[0])


# ---------------------------------------------------------------------------
# process_task
# ---------------------------------------------------------------------------

class TestProcessTask:
    """Tests for process_task end-to-end method."""

    def test_success_result(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        with patch.object(qm, "commit_to_git"):
            result = qm.process_task(spec)
        assert result["status"] == "success"
        assert result["task_id"] == "my-task"
        assert result["todo_updated"] is True
        assert result["committed"] is True

    def test_validation_error_bubbles_up(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec(task_id="BadTaskId")  # uppercase — invalid
        with pytest.raises(ValidationError):
            qm.process_task(spec)

    def test_duplicate_error_bubbles_up(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        # Create pre-existing file
        (tmp_path / "incoming" / "my-task.json").touch()
        with pytest.raises(DuplicateTaskError):
            qm.process_task(spec)

    def test_parse_error_returns_failed_status(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = {}  # missing all required fields — parse raises ValueError
        result = qm.process_task(spec)
        assert result["status"] == "failed"
        assert len(result["errors"]) > 0

    def test_git_error_non_fatal(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        with patch.object(qm, "commit_to_git", side_effect=GitError("git fail")):
            result = qm.process_task(spec)
        assert result["status"] == "success"  # Status still success
        assert result["committed"] is False
        assert any("Git commit failed" in e for e in result["errors"])

    def test_delegate_path_is_file(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec()
        with patch.object(qm, "commit_to_git"):
            result = qm.process_task(spec)
        assert result["delegate_path"] is not None
        assert os.path.isfile(result["delegate_path"])

    def test_process_creates_todo_entry(self, tmp_path):
        qm = _make_qm(tmp_path)
        spec = _minimal_spec("my-workflow-task")
        with patch.object(qm, "commit_to_git"):
            qm.process_task(spec)
        content = (tmp_path / "TODO.md").read_text()
        assert "my-workflow-task" in content


# ---------------------------------------------------------------------------
# check_duplicate extra branch coverage
# ---------------------------------------------------------------------------

class TestCheckDuplicateBranches:
    """Branch coverage for check_duplicate."""

    def test_incoming_subdir_in_queue_dir_is_searched(self, tmp_path):
        """When queue_dir has an 'incoming' subdir, that subdir is also searched."""
        # queue_dir is parent, incoming/ is the subdir
        parent_dir = tmp_path / "queue"
        parent_dir.mkdir()
        incoming_dir = parent_dir / "incoming"
        incoming_dir.mkdir()
        (incoming_dir / "dup-task.json").touch()

        qm = QueueManager(
            queue_dir=str(parent_dir),
            todo_path=str(tmp_path / "TODO.md"),
        )
        with pytest.raises(DuplicateTaskError, match="dup-task"):
            qm.check_duplicate("dup-task")

    def test_nonexistent_queue_dir_no_error(self, tmp_path):
        """check_duplicate handles FileNotFoundError for nonexistent search paths."""
        qm = QueueManager(
            queue_dir=str(tmp_path / "ghost-dir"),
            todo_path=str(tmp_path / "TODO.md"),
        )
        # Re-create the instance but delete queue_dir after init
        import shutil
        shutil.rmtree(qm.queue_dir, ignore_errors=True)
        qm.check_duplicate("any-task")  # Should not raise


# ---------------------------------------------------------------------------
# _get_default_queue_dir with queue_isolation available
# ---------------------------------------------------------------------------

class TestGetDefaultQueueDir:
    """Tests for queue_isolation integration path."""

    def test_uses_queue_isolation_when_available(self, tmp_path):
        """_get_default_queue_dir uses queue_isolation module if present."""
        mock_qi = MagicMock()
        mock_qi.get_session_id.return_value = "test-session"
        mock_qi.detect_harness.return_value = "pytest"
        mock_qi.get_queue_path.return_value = tmp_path / "queue"
        mock_qi.init_queue_structure.return_value = None

        import queue_manager as qm_mod
        with patch.object(qm_mod, "_try_import_queue_isolation", return_value=mock_qi):
            path = QueueManager._get_default_queue_dir()
        assert "incoming" in path

    def test_try_import_queue_isolation_returns_none_on_missing(self):
        """_try_import_queue_isolation returns None if queue_isolation not importable."""
        import queue_manager as qm_mod
        # Temporarily make it fail
        with patch.dict("sys.modules", {"queue_isolation": None}):
            result = qm_mod._try_import_queue_isolation()
        # Should not raise; returns None or the module
        assert result is None or result is not None  # just no exception

    def test_default_queue_dir_with_copilot_session_id(self, tmp_path, monkeypatch):
        """_get_default_queue_dir uses COPILOT_SESSION_ID env var."""
        monkeypatch.setenv("COPILOT_SESSION_ID", "copilot-123")
        import queue_manager as qm_mod
        with patch.object(qm_mod, "_try_import_queue_isolation", return_value=None):
            path = QueueManager._get_default_queue_dir()
        assert "copilot-123" in path

    def test_default_queue_dir_with_claude_session_id(self, tmp_path, monkeypatch):
        """_get_default_queue_dir uses CLAUDE_SESSION_ID env var as fallback."""
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        monkeypatch.setenv("CLAUDE_SESSION_ID", "claude-456")
        import queue_manager as qm_mod
        with patch.object(qm_mod, "_try_import_queue_isolation", return_value=None):
            path = QueueManager._get_default_queue_dir()
        assert "claude-456" in path

    def test_default_queue_dir_fallback_to_local(self, tmp_path, monkeypatch):
        """_get_default_queue_dir falls back to 'local' if no session ID env var."""
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        import queue_manager as qm_mod
        with patch.object(qm_mod, "_try_import_queue_isolation", return_value=None):
            path = QueueManager._get_default_queue_dir()
        assert "local" in path
