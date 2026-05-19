"""
Tests for todo-maintenance skill — Auto-sync queue DELEGATEs ↔ TODO.md

TDD RED-phase tests covering:
1. DELEGATE → TODO.md sync
2. HANDBACK → TODO.md sync
3. Bidirectional sync with conflict detection
4. Weekly sync report generation
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import the module we're testing (will be created)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sync_todo import (
    TodoSyncManager,
    DelegateEntry,
    HandbackEntry,
    SyncConflict,
    SyncReport,
)


class TestDelegateEntry:
    """Test DELEGATE entry parsing and formatting"""

    def test_parse_delegate_yaml(self):
        """Test parsing DELEGATE YAML file"""
        delegate_yaml = """---
handoff_type: DELEGATE
task_id: 2026-05-18-test-task
role: engineer
model: claude-haiku-4-5
effort: medium
scope: |
  Test task for todo-maintenance skill
  This is a multi-line scope
plan:
  - Step 1: Do something
  - Step 2: Do something else
---
"""
        entry = DelegateEntry.from_yaml(delegate_yaml)
        assert entry.task_id == "2026-05-18-test-task"
        assert entry.role == "engineer"
        assert entry.effort == "medium"
        assert "Test task" in entry.scope
        assert len(entry.plan) == 2

    def test_delegate_entry_to_todo_format(self):
        """Test converting DELEGATE to TODO.md format"""
        entry = DelegateEntry(
            task_id="2026-05-18-test-task",
            role="engineer",
            scope="Test task for todo-maintenance skill",
            effort="medium",
            plan=["Step 1", "Step 2"],
        )
        todo_line = entry.to_todo_line()
        assert "[ ]" in todo_line
        assert "2026-05-18-test-task" in todo_line
        assert "engineer" in todo_line
        assert "Test task" in todo_line

    def test_delegate_entry_incomplete_data(self):
        """Test handling of incomplete DELEGATE data"""
        with pytest.raises(ValueError):
            DelegateEntry(
                task_id="",  # Empty task_id should fail
                role="engineer",
                scope="Test",
                effort="medium",
                plan=[],
            )


class TestHandbackEntry:
    """Test HANDBACK entry parsing and formatting"""

    def test_parse_handback_json(self):
        """Test parsing HANDBACK JSON file"""
        handback_json = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-18-test-task",
            "timestamp": "2026-05-18T10:00:00Z",
            "status": "complete",
            "deliverables": ["file1.py", "file2.py"],
            "tests": ["test_pass_1", "test_pass_2"],
            "tokens": {"used": 1200, "estimated": 1500, "efficiency": 0.80},
            "quality_score": 95,
            "confidence": 0.95,
        }
        entry = HandbackEntry.from_dict(handback_json)
        assert entry.task_id == "2026-05-18-test-task"
        assert entry.status == "complete"
        assert entry.quality_score == 95

    def test_handback_entry_to_todo_format(self):
        """Test converting HANDBACK to TODO.md format (marking complete)"""
        entry = HandbackEntry(
            task_id="2026-05-18-test-task",
            status="complete",
            timestamp="2026-05-18T10:00:00Z",
            quality_score=95,
            confidence=0.95,
        )
        todo_line = entry.to_todo_line()
        assert "[x]" in todo_line
        assert "2026-05-18-test-task" in todo_line
        assert "2026-05-18" in todo_line  # Completion date


class TestTodoSyncManager:
    """Test TodoSyncManager core functionality"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "artifacts" / "queue" / "incoming").mkdir(parents=True)
            (workspace / "artifacts" / "queue" / "processing").mkdir(parents=True)
            (workspace / "artifacts" / "queue" / "done").mkdir(parents=True)
            yield workspace

    @pytest.fixture
    def sync_manager(self, temp_workspace):
        """Create TodoSyncManager instance"""
        todo_path = temp_workspace / "TODO.md"
        queue_path = temp_workspace / "artifacts" / "queue"
        return TodoSyncManager(todo_path=todo_path, queue_path=queue_path)

    def test_sync_manager_initialization(self, sync_manager):
        """Test TodoSyncManager initialization"""
        assert sync_manager.todo_path is not None
        assert sync_manager.queue_path is not None

    def test_read_todo_md(self, sync_manager, temp_workspace):
        """Test reading TODO.md file"""
        todo_content = """# TODO

## IN PROGRESS
- [ ] **TASK-001:** First task (Owner: engineer)

## COMPLETED
- [x] **TASK-002:** Second task (Owner: engineer)
"""
        (temp_workspace / "TODO.md").write_text(todo_content)
        entries = sync_manager.read_todo_md()
        assert len(entries) >= 2

    def test_add_delegate_to_todo(self, sync_manager, temp_workspace):
        """Test adding DELEGATE entry to TODO.md"""
        # Create initial TODO.md
        initial_todo = """# TODO

## IN PROGRESS

## COMPLETED
"""
        (temp_workspace / "TODO.md").write_text(initial_todo)

        # Create DELEGATE file
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-05-18-test-task",
            "role": "engineer",
            "scope": "Test task for todo-maintenance",
            "effort": "medium",
            "plan": ["Step 1", "Step 2"],
        }
        delegate_file = (
            temp_workspace / "artifacts" / "queue" / "incoming" / "DELEGATE-test.yaml"
        )
        delegate_file.write_text(yaml.dump(delegate_data))

        # Sync
        sync_manager.sync_delegate_to_todo(delegate_data)

        # Verify
        todo_content = (temp_workspace / "TODO.md").read_text()
        assert "2026-05-18-test-task" in todo_content
        assert "[ ]" in todo_content

    def test_mark_todo_complete_on_handback(self, sync_manager, temp_workspace):
        """Test marking TODO entry complete when HANDBACK received"""
        # Create TODO.md with pending task
        todo_content = """# TODO

## IN PROGRESS
- [ ] **2026-05-18-test-task:** Test task (Owner: engineer)

## COMPLETED
"""
        (temp_workspace / "TODO.md").write_text(todo_content)

        # Sync HANDBACK
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-18-test-task",
            "status": "complete",
            "timestamp": "2026-05-18T10:00:00Z",
        }
        sync_manager.sync_handback_to_todo(handback_data)

        # Verify
        todo_content = (temp_workspace / "TODO.md").read_text()
        assert "[x]" in todo_content
        assert "2026-05-18-test-task" in todo_content

    def test_detect_orphaned_tasks(self, sync_manager, temp_workspace):
        """Test detecting tasks in TODO but not in queue"""
        # Create TODO.md with orphaned task
        todo_content = """# TODO

## IN PROGRESS
- [ ] **ORPHANED-TASK:** Orphaned task (Owner: engineer)
- [ ] **2026-05-18-real-task:** Real task (Owner: engineer)

## COMPLETED
"""
        (temp_workspace / "TODO.md").write_text(todo_content)

        # Create only one DELEGATE in queue
        delegate_file = (
            temp_workspace / "artifacts" / "queue" / "incoming" / "DELEGATE-real.yaml"
        )
        delegate_data = {
            "task_id": "2026-05-18-real-task",
            "role": "engineer",
        }
        delegate_file.write_text(yaml.dump(delegate_data))

        # Detect orphans
        orphans = sync_manager.detect_orphaned_tasks()
        assert any(o["task_id"] == "ORPHANED-TASK" for o in orphans)

    def test_detect_missing_tasks(self, sync_manager, temp_workspace):
        """Test detecting tasks in queue but not in TODO"""
        # Create TODO.md with one task
        todo_content = """# TODO

## IN PROGRESS
- [ ] **2026-05-18-task-1:** Task 1 (Owner: engineer)

## COMPLETED
"""
        (temp_workspace / "TODO.md").write_text(todo_content)

        # Create two DELEGATEs in queue
        for i in range(1, 3):
            delegate_file = (
                temp_workspace
                / "artifacts"
                / "queue"
                / "incoming"
                / f"DELEGATE-task-{i}.yaml"
            )
            delegate_data = {
                "task_id": f"2026-05-18-task-{i}",
                "role": "engineer",
            }
            delegate_file.write_text(yaml.dump(delegate_data))

        # Detect missing
        missing = sync_manager.detect_missing_tasks()
        assert any(m["task_id"] == "2026-05-18-task-2" for m in missing)

    def test_conflict_detection_same_task_modified(self, sync_manager, temp_workspace):
        """Test detecting conflicts when same task modified in both TODO and queue"""
        # Create TODO.md with modified task
        todo_content = """# TODO

## IN PROGRESS
- [ ] **2026-05-18-test-task:** Modified in TODO (Owner: engineer)

## COMPLETED
"""
        (temp_workspace / "TODO.md").write_text(todo_content)

        # Create DELEGATE with different scope
        delegate_file = (
            temp_workspace / "artifacts" / "queue" / "incoming" / "DELEGATE-test.yaml"
        )
        delegate_data = {
            "task_id": "2026-05-18-test-task",
            "role": "engineer",
            "scope": "Different scope in queue",
        }
        delegate_file.write_text(yaml.dump(delegate_data))

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts()
        assert len(conflicts) > 0

    def test_bidirectional_sync_no_conflicts(self, sync_manager, temp_workspace):
        """Test bidirectional sync when no conflicts exist"""
        # Create TODO.md
        todo_content = """# TODO

## IN PROGRESS
- [ ] **2026-05-18-task-1:** Task 1 (Owner: engineer)

## COMPLETED
- [x] **2026-05-18-task-2:** Task 2 (Owner: engineer)
"""
        (temp_workspace / "TODO.md").write_text(todo_content)

        # Create matching DELEGATE and HANDBACK
        delegate_file = (
            temp_workspace / "artifacts" / "queue" / "incoming" / "DELEGATE-task-1.yaml"
        )
        delegate_data = {"task_id": "2026-05-18-task-1", "role": "engineer"}
        delegate_file.write_text(yaml.dump(delegate_data))

        handback_file = (
            temp_workspace / "artifacts" / "queue" / "done" / "HANDBACK-task-2.json"
        )
        handback_data = {
            "task_id": "2026-05-18-task-2",
            "status": "complete",
        }
        handback_file.write_text(json.dumps(handback_data))

        # Perform bidirectional sync
        result = sync_manager.bidirectional_sync()
        assert result["conflicts"] == 0

    def test_merge_strategy_todo_takes_precedence(self, sync_manager):
        """Test merge strategy: TODO.md manual edits take precedence"""
        # This tests the conflict resolution strategy
        conflict = SyncConflict(
            task_id="test-task",
            source="todo",
            queue_version="Queue version",
            todo_version="TODO version",
        )
        resolved = sync_manager.resolve_conflict(conflict)
        assert resolved == "TODO version"


class TestSyncReport:
    """Test weekly sync report generation"""

    def test_generate_weekly_report(self):
        """Test generating weekly sync report"""
        report = SyncReport(
            week_start="2026-05-18",
            week_end="2026-05-24",
            total_tasks=10,
            completed_tasks=3,
            orphaned_tasks=1,
            missing_tasks=2,
            conflicts=0,
        )
        report_text = report.generate()
        assert "2026-05-18" in report_text
        assert "10" in report_text
        assert "3" in report_text

    def test_report_includes_metrics(self):
        """Test that report includes all metrics"""
        report = SyncReport(
            week_start="2026-05-18",
            week_end="2026-05-24",
            total_tasks=10,
            completed_tasks=3,
            orphaned_tasks=1,
            missing_tasks=2,
            conflicts=0,
        )
        report_text = report.generate()
        assert "Total Tasks" in report_text
        assert "Completed" in report_text
        assert "Orphaned" in report_text
        assert "Missing" in report_text
        assert "Conflicts" in report_text

    def test_report_file_output(self, tmp_path):
        """Test writing report to file"""
        report = SyncReport(
            week_start="2026-05-18",
            week_end="2026-05-24",
            total_tasks=10,
            completed_tasks=3,
            orphaned_tasks=1,
            missing_tasks=2,
            conflicts=0,
        )
        report_file = tmp_path / "sync_report.md"
        report.write_to_file(report_file)
        assert report_file.exists()
        assert "2026-05-18" in report_file.read_text()


class TestCLIIntegration:
    """Test CLI wrapper integration"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "artifacts" / "queue" / "incoming").mkdir(parents=True)
            (workspace / "artifacts" / "queue" / "processing").mkdir(parents=True)
            (workspace / "artifacts" / "queue" / "done").mkdir(parents=True)
            yield workspace

    def test_cli_sync_command(self, temp_workspace):
        """Test CLI sync command"""
        # This will be tested via subprocess in integration tests
        pass

    def test_cli_report_command(self, temp_workspace):
        """Test CLI report command"""
        # This will be tested via subprocess in integration tests
        pass


class TestIntegration:
    """Integration tests with real queue structure"""

    @pytest.fixture
    def real_workspace(self):
        """Create realistic workspace structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "artifacts" / "queue" / "incoming").mkdir(parents=True)
            (workspace / "artifacts" / "queue" / "processing").mkdir(parents=True)
            (workspace / "artifacts" / "queue" / "done").mkdir(parents=True)

            # Create initial TODO.md
            todo_content = """# TODO

## IN PROGRESS

## COMPLETED
"""
            (workspace / "TODO.md").write_text(todo_content)
            yield workspace

    def test_full_sync_workflow(self, real_workspace):
        """Test complete sync workflow: DELEGATE → TODO → HANDBACK → TODO"""
        manager = TodoSyncManager(
            todo_path=real_workspace / "TODO.md",
            queue_path=real_workspace / "artifacts" / "queue",
        )

        # Step 1: Create DELEGATE
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-05-18-integration-test",
            "role": "engineer",
            "scope": "Integration test task",
            "effort": "medium",
            "plan": ["Step 1"],
        }
        delegate_file = (
            real_workspace
            / "artifacts"
            / "queue"
            / "incoming"
            / "DELEGATE-integration.yaml"
        )
        delegate_file.write_text(yaml.dump(delegate_data))

        # Step 2: Sync DELEGATE to TODO
        manager.sync_delegate_to_todo(delegate_data)
        todo_v1 = (real_workspace / "TODO.md").read_text()
        assert "2026-05-18-integration-test" in todo_v1
        assert "[ ]" in todo_v1

        # Step 3: Create HANDBACK
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-18-integration-test",
            "status": "complete",
            "timestamp": "2026-05-18T10:00:00Z",
        }
        handback_file = (
            real_workspace
            / "artifacts"
            / "queue"
            / "done"
            / "HANDBACK-integration.json"
        )
        handback_file.write_text(json.dumps(handback_data))

        # Step 4: Sync HANDBACK to TODO
        manager.sync_handback_to_todo(handback_data)
        todo_v2 = (real_workspace / "TODO.md").read_text()
        assert "[x]" in todo_v2
        assert "2026-05-18-integration-test" in todo_v2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
