"""
RED-phase tests for queue-management skill.
TDD: Tests written first, before implementation.
"""
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Import the skill module (will exist after implementation)
import importlib
qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
QueueManager = qm_mod.QueueManager


class TestQueueManagerParsing:
    """Test task specification parsing."""

    def test_parse_json_spec_valid(self):
        """Parse valid JSON task specification."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        spec = {
            "task_id": "test-task-001",
            "role": "Engineer",
            "scope": "Implement feature X",
            "plan": ["Step 1", "Step 2"],
            "success_criteria": ["Tests pass", "Coverage 85%+"],
        }
        qm = QueueManager()
        parsed = qm.parse_spec(spec, format_type="json")
        
        assert parsed["task_id"] == "test-task-001"
        assert parsed["role"] == "Engineer"

    def test_parse_json_spec_missing_required_field(self):
        """Reject JSON spec with missing required fields."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        spec = {
            "task_id": "test-task-001",
            # Missing 'role' - required field
            "scope": "Implement feature X",
        }
        qm = QueueManager()
        
        with pytest.raises(ValueError, match="Missing required field"):
            qm.parse_spec(spec, format_type="json")

    def test_parse_cli_args_valid(self):
        """Parse valid CLI arguments."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        args = [
            "--task-id", "cli-task-001",
            "--role", "Engineer",
            "--scope", "Fix bug in auth module",
        ]
        qm = QueueManager()
        parsed = qm.parse_spec_from_cli(args)
        
        assert parsed["task_id"] == "cli-task-001"
        assert parsed["role"] == "Engineer"

    def test_parse_cli_args_missing_required(self):
        """Reject CLI args with missing required parameters."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        args = ["--task-id", "cli-task-001"]
        # Missing --role
        
        qm = QueueManager()
        with pytest.raises(ValueError, match="Missing required parameter"):
            qm.parse_spec_from_cli(args)


class TestQueueProtocolValidator:
    """Test QUEUE-PROTOCOL validation."""

    def test_validate_spec_all_required_fields(self):
        """Validate spec has all required QUEUE-PROTOCOL fields."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        ValidationError = qm_mod.ValidationError
        
        spec = {
            "task_id": "valid-task",
            "role": "Engineer",
            "scope": "Implementation task",
            "plan": ["Step 1", "Step 2"],
            "success_criteria": ["Tests pass"],
        }
        
        qm = QueueManager()
        # Should not raise
        qm.validate_protocol(spec)

    def test_validate_spec_invalid_task_id_format(self):
        """Reject invalid task_id format (must be kebab-case)."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        ValidationError = qm_mod.ValidationError
        
        spec = {
            "task_id": "InvalidTaskID",  # Not kebab-case
            "role": "Engineer",
            "scope": "Implementation task",
            "plan": ["Step 1"],
            "success_criteria": ["Tests pass"],
        }
        
        qm = QueueManager()
        with pytest.raises(ValidationError, match="task_id must be kebab-case"):
            qm.validate_protocol(spec)

    def test_validate_spec_invalid_role(self):
        """Reject invalid role."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        ValidationError = qm_mod.ValidationError
        
        spec = {
            "task_id": "valid-task",
            "role": "InvalidRole",  # Not in allowed roles
            "scope": "Implementation task",
            "plan": ["Step 1"],
            "success_criteria": ["Tests pass"],
        }
        
        qm = QueueManager()
        with pytest.raises(ValidationError, match="Invalid role"):
            qm.validate_protocol(spec)

    def test_validate_spec_plan_not_empty(self):
        """Reject spec with empty plan."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        ValidationError = qm_mod.ValidationError
        
        spec = {
            "task_id": "valid-task",
            "role": "Engineer",
            "scope": "Implementation task",
            "plan": [],  # Empty plan
            "success_criteria": ["Tests pass"],
        }
        
        qm = QueueManager()
        with pytest.raises(ValidationError, match="plan must not be empty"):
            qm.validate_protocol(spec)


class TestDelegateGenerator:
    """Test DELEGATE JSON file generation."""

    def test_generate_delegate_creates_file(self):
        """Generate DELEGATE JSON file in correct location."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            qm = QueueManager(queue_dir=tmpdir)
            
            spec = {
                "task_id": "test-delegate-001",
                "role": "Engineer",
                "scope": "Test implementation",
                "plan": ["Step 1", "Step 2"],
                "success_criteria": ["Tests pass"],
            }
            
            delegate_path = qm.generate_delegate(spec)
            
            assert os.path.exists(delegate_path)
            assert delegate_path.endswith(".json")

    def test_delegate_file_has_required_fields(self):
        """DELEGATE file contains required QUEUE-PROTOCOL fields."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            qm = QueueManager(queue_dir=tmpdir)
            
            spec = {
                "task_id": "test-delegate-002",
                "role": "Engineer",
                "scope": "Test implementation",
                "plan": ["Step 1"],
                "success_criteria": ["Tests pass"],
                "effort": "low",
                "priority": "high",
            }
            
            delegate_path = qm.generate_delegate(spec)
            
            with open(delegate_path, 'r') as f:
                content = json.load(f)
            
            assert content["task_id"] == "test-delegate-002"
            assert content["role"] == "Engineer"
            assert "plan" in content
            assert "success_criteria" in content


class TestTodoMdUpdater:
    """Test TODO.md entry creation."""

    def test_add_todo_entry_creates_entry(self):
        """Add entry to TODO.md in correct phase section."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            todo_path = os.path.join(tmpdir, "TODO.md")
            
            # Create a template TODO.md
            with open(todo_path, 'w') as f:
                f.write("# TODO: agentic-engineers\n\n")
                f.write("## 🟢 PHASE 2 (Weeks 3-4)\n\n")
                f.write("Some existing task\n")
            
            qm = QueueManager(todo_path=todo_path)
            
            spec = {
                "task_id": "phase-2-task",
                "role": "Engineer",
                "scope": "Phase 2 implementation",
                "plan": ["Step 1"],
                "success_criteria": ["Tests pass"],
                "phase": "2",
            }
            
            qm.add_todo_entry(spec)
            
            with open(todo_path, 'r') as f:
                content = f.read()
            
            assert "phase-2-task" in content

    def test_todo_entry_format_has_all_fields(self):
        """TODO.md entry includes task_id, description, effort, owner."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            todo_path = os.path.join(tmpdir, "TODO.md")
            
            with open(todo_path, 'w') as f:
                f.write("# TODO\n\n## 🔴 PHASE 1\n\n")
            
            qm = QueueManager(todo_path=todo_path)
            
            spec = {
                "task_id": "full-task-001",
                "role": "Engineer",
                "scope": "Full feature implementation",
                "plan": ["Step 1", "Step 2"],
                "success_criteria": ["Tests pass"],
                "effort": "medium",
            }
            
            qm.add_todo_entry(spec)
            
            with open(todo_path, 'r') as f:
                content = f.read()
            
            # Verify all expected fields are present
            assert "full-task-001" in content
            assert "Full feature" in content or "implementation" in content
            assert "Engineer" in content


class TestDuplicateDetection:
    """Test duplicate task_id detection."""

    def test_detect_duplicate_in_existing_queue(self):
        """Detect duplicate task_id in existing queue files."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        DuplicateTaskError = qm_mod.DuplicateTaskError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            incoming_dir = os.path.join(tmpdir, "incoming")
            os.makedirs(incoming_dir)
            
            # Create existing task file
            existing_task = os.path.join(incoming_dir, "duplicate-task.json")
            with open(existing_task, 'w') as f:
                json.dump({"task_id": "duplicate-task"}, f)
            
            qm = QueueManager(queue_dir=tmpdir)
            
            with pytest.raises(DuplicateTaskError):
                qm.check_duplicate("duplicate-task")

    def test_detect_duplicate_in_todo_md(self):
        """Detect duplicate task_id in TODO.md."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        DuplicateTaskError = qm_mod.DuplicateTaskError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            todo_path = os.path.join(tmpdir, "TODO.md")
            
            with open(todo_path, 'w') as f:
                f.write("# TODO\n\n- [ ] **TASK-001:** Some task\n")
            
            qm = QueueManager(todo_path=todo_path)
            
            with pytest.raises(DuplicateTaskError):
                qm.check_duplicate("TASK-001")

    def test_no_duplicate_when_unique(self):
        """Allow unique task_id."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            qm = QueueManager(queue_dir=tmpdir)
            
            # Should not raise
            qm.check_duplicate("unique-task-id")


class TestGitIntegration:
    """Test git commit functionality."""

    def test_git_commit_both_files(self):
        """Commit both DELEGATE and TODO.md atomically."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            os.chdir(tmpdir)
            os.system("git init >/dev/null 2>&1")
            os.system("git config user.email 'test@example.com'")
            os.system("git config user.name 'Test'")
            
            # Create initial files
            Path(f"{tmpdir}/TODO.md").write_text("# TODO\n\n## 🟢 PHASE 2\n\n")
            os.system("git add TODO.md && git commit -m 'initial' >/dev/null 2>&1")
            
            qm = QueueManager(queue_dir=tmpdir, todo_path=f"{tmpdir}/TODO.md")
            
            spec = {
                "task_id": "git-test-task",
                "role": "Engineer",
                "scope": "Test git integration",
                "plan": ["Step 1"],
                "success_criteria": ["Tests pass"],
            }
            
            # First generate the DELEGATE file
            qm.generate_delegate(spec)
            qm.add_todo_entry(spec)
            
            # Then commit both files
            qm.commit_to_git(spec, "Add task to queue")
            
            # Verify commit was created
            result = os.popen("git log --oneline | head -1").read()
            assert "queue" in result.lower() or "git-test-task" in result


class TestCliInterface:
    """Test CLI command interface."""

    def test_cli_add_to_queue_happy_path(self):
        """CLI: add-to-queue command with all required args."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.cli")
        add_to_queue_cli = qm_mod.add_to_queue_cli
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create necessary directories
            queue_dir = os.path.join(tmpdir, "queue")
            os.makedirs(queue_dir)
            todo_path = os.path.join(tmpdir, "TODO.md")
            with open(todo_path, 'w') as f:
                f.write("# TODO\n\n## 🟢 PHASE 2\n\n")
            
            os.chdir(tmpdir)
            os.system("git init >/dev/null 2>&1")
            os.system("git config user.email 'test@test.com'")
            os.system("git config user.name 'Test'")
            
            # Mock QueueManager initialization to use temp dirs
            from src.skills.queue_management import queue_manager as qm_module
            
            original_init = qm_module.QueueManager.__init__
            
            def mock_init(self, queue_dir_arg=None, todo_path_arg=None):
                original_init(self, queue_dir=queue_dir, todo_path=todo_path)
            
            qm_module.QueueManager.__init__ = mock_init
            
            try:
                args = [
                    "--task-id", "cli-full-task",
                    "--role", "Engineer",
                    "--scope", "CLI test task",
                ]
                
                # Should succeed without raising
                result = add_to_queue_cli(args)
                assert result["success"] == True
            finally:
                # Restore original
                qm_module.QueueManager.__init__ = original_init

    def test_cli_with_json_file(self):
        """CLI: add-to-queue with JSON spec file."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.cli")
        add_to_queue_cli = qm_mod.add_to_queue_cli
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create spec file
            spec_file = os.path.join(tmpdir, "spec.json")
            spec = {
                "task_id": "json-spec-task",
                "role": "Engineer",
                "scope": "JSON spec test",
                "plan": ["Step 1"],
                "success_criteria": ["Pass"],
            }
            with open(spec_file, 'w') as f:
                json.dump(spec, f)
            
            # Create queue and TODO directories
            queue_dir = os.path.join(tmpdir, "queue")
            os.makedirs(queue_dir)
            todo_path = os.path.join(tmpdir, "TODO.md")
            with open(todo_path, 'w') as f:
                f.write("# TODO\n\n## 🟢 PHASE 2\n\n")
            
            os.chdir(tmpdir)
            os.system("git init >/dev/null 2>&1")
            os.system("git config user.email 'test@test.com'")
            os.system("git config user.name 'Test'")
            
            # Mock QueueManager initialization
            from src.skills.queue_management import queue_manager as qm_module
            
            original_init = qm_module.QueueManager.__init__
            
            def mock_init(self, queue_dir_arg=None, todo_path_arg=None):
                original_init(self, queue_dir=queue_dir, todo_path=todo_path)
            
            qm_module.QueueManager.__init__ = mock_init
            
            try:
                args = ["--spec-file", spec_file]
                
                result = add_to_queue_cli(args)
                assert result["success"] == True
            finally:
                qm_module.QueueManager.__init__ = original_init


class TestErrorHandling:
    """Test error messages and user feedback."""

    def test_error_message_validation_failure(self):
        """Clear error message for validation failure."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        ValidationError = qm_mod.ValidationError
        
        spec = {
            "task_id": "BadTaskID",  # Not kebab-case
            "role": "Engineer",
            "scope": "Test",
            "plan": ["Step 1"],
            "success_criteria": ["Pass"],
        }
        
        qm = QueueManager()
        with pytest.raises(ValidationError) as exc_info:
            qm.validate_protocol(spec)
        
        # Error message should be user-friendly
        assert "kebab-case" in str(exc_info.value)

    def test_error_message_duplicate_detection(self):
        """Clear error message for duplicate task_id."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        DuplicateTaskError = qm_mod.DuplicateTaskError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = os.path.join(tmpdir, "queue")
            incoming_dir = os.path.join(queue_dir, "incoming")
            os.makedirs(incoming_dir)
            
            # Create file with proper naming: {task_id}.json
            existing = os.path.join(incoming_dir, "dup-task.json")
            with open(existing, 'w') as f:
                json.dump({"task_id": "dup-task"}, f)
            
            qm = QueueManager(queue_dir=queue_dir)
            
            with pytest.raises(DuplicateTaskError) as exc_info:
                qm.check_duplicate("dup-task")
            
            # Error should indicate where duplicate was found
            assert "already exists" in str(exc_info.value)

    def test_cli_error_file_not_found(self):
        """CLI error handling for missing spec file."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.cli")
        add_to_queue_cli = qm_mod.add_to_queue_cli
        
        args = ["--spec-file", "/nonexistent/file.json"]
        result = add_to_queue_cli(args)
        
        assert result["success"] == False
        assert "not found" in result["message"].lower() or "error" in result["message"].lower()

    def test_cli_error_invalid_json(self):
        """CLI error handling for invalid JSON in spec file."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.cli")
        add_to_queue_cli = qm_mod.add_to_queue_cli
        
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = os.path.join(tmpdir, "bad.json")
            with open(spec_file, 'w') as f:
                f.write("{ invalid json }")
            
            args = ["--spec-file", spec_file]
            result = add_to_queue_cli(args)
            
            assert result["success"] == False
            assert "json" in result["message"].lower()

    def test_cli_error_missing_required_cli_args(self):
        """CLI error when required args are missing."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.cli")
        add_to_queue_cli = qm_mod.add_to_queue_cli
        
        args = ["--task-id", "test"]  # Missing --role and --scope
        result = add_to_queue_cli(args)
        
        assert result["success"] == False
        assert "missing required parameter" in result["message"].lower() or "error" in result["message"].lower()

    def test_cli_with_optional_args(self):
        """CLI: add-to-queue with optional effort and priority args."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.cli")
        add_to_queue_cli = qm_mod.add_to_queue_cli
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create queue and TODO directories
            queue_dir = os.path.join(tmpdir, "queue")
            os.makedirs(queue_dir)
            todo_path = os.path.join(tmpdir, "TODO.md")
            with open(todo_path, 'w') as f:
                f.write("# TODO\n\n## 🟢 PHASE 2\n\n")
            
            os.chdir(tmpdir)
            os.system("git init >/dev/null 2>&1")
            os.system("git config user.email 'test@test.com'")
            os.system("git config user.name 'Test'")
            
            # Mock QueueManager initialization
            from src.skills.queue_management import queue_manager as qm_module
            
            original_init = qm_module.QueueManager.__init__
            
            def mock_init(self, queue_dir_arg=None, todo_path_arg=None):
                original_init(self, queue_dir=queue_dir, todo_path=todo_path)
            
            qm_module.QueueManager.__init__ = mock_init
            
            try:
                args = [
                    "--task-id", "cli-optional-args",
                    "--role", "Senior Engineer",
                    "--scope", "Test optional args",
                    "--effort", "high",
                    "--priority", "high",
                ]
                
                result = add_to_queue_cli(args)
                assert result["success"] == True
                assert "optional-args" in result["message"] or "Optional" in result["message"] or "queue" in result["message"]
            finally:
                qm_module.QueueManager.__init__ = original_init


class TestIntegrationFullWorkflow:
    """Integration tests: Full workflow from spec to committed queue."""

    def test_full_workflow_add_task_to_queue(self):
        """Full workflow: Parse → Validate → Generate → Add TODO → Commit."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup git repo
            os.chdir(tmpdir)
            os.system("git init >/dev/null 2>&1")
            os.system("git config user.email 'test@test.com'")
            os.system("git config user.name 'Test'")
            
            # Create TODO.md
            todo_path = os.path.join(tmpdir, "TODO.md")
            with open(todo_path, 'w') as f:
                f.write("# TODO\n\n## 🟢 PHASE 2\n\n")
            
            os.system(f"git add {todo_path} && git commit -m 'init' >/dev/null 2>&1")
            
            qm = QueueManager(queue_dir=tmpdir, todo_path=todo_path)
            
            spec = {
                "task_id": "integration-test-task",
                "role": "Engineer",
                "scope": "Full integration test",
                "plan": ["Parse", "Validate", "Generate", "Commit"],
                "success_criteria": ["All steps pass"],
                "effort": "low",
            }
            
            result = qm.process_task(spec)
            
            assert result["status"] == "success"
            assert result["delegate_path"] is not None
            assert result["todo_updated"] == True
            assert result["committed"] == True

    def test_workflow_rejects_invalid_spec(self):
        """Workflow rejects invalid spec early."""
        import importlib
        qm_mod = importlib.import_module("src.skills.queue-management.queue_manager")
        QueueManager = qm_mod.QueueManager
        ValidationError = qm_mod.ValidationError
        
        qm = QueueManager()
        
        invalid_spec = {
            "task_id": "NotKebabCase",  # Invalid
            "role": "Engineer",
            "scope": "Test",
            "plan": ["Step"],
            "success_criteria": ["Pass"],
        }
        
        with pytest.raises(ValidationError):
            qm.process_task(invalid_spec)
