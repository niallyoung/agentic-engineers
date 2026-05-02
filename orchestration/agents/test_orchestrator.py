"""
RED Phase: Comprehensive tests for Orchestrator agent functionality.

Tests cover:
1. Poll incoming queue, find DELEGATE blocks
2. Validate DELEGATE format per docs/SPEC.md
3. Route task to correct agent per AGENTS.md
4. Delegate task to agent
5. Receive and process HANDBACK
6. Move tasks through queue states (incoming → processing → done)
7. Capture span data (task_id, model, tokens, cost, duration)
8. Generate index.json from artifacts
"""

import unittest
import tempfile
import json
import yaml
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class TestOrchestratorQueuePolling(unittest.TestCase):
    """Test queue polling mechanism."""

    def setUp(self):
        """Create temporary queue structure."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        (self.queue_dir / "incoming").mkdir(exist_ok=True)
        (self.queue_dir / "processing").mkdir(exist_ok=True)
        (self.queue_dir / "done").mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_poll_incoming_queue_finds_tasks(self):
        """Test: Poll incoming queue and find new task files."""
        # Create a test task
        task_file = self.queue_dir / "incoming" / "2026-05-02-test-task.yaml"
        task_data = {
            "task_id": "2026-05-02-test-task",
            "description": "Test task",
            "priority": "high"
        }
        with open(task_file, 'w') as f:
            yaml.dump(task_data, f)
        
        # Poll should find this task
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        tasks = orch.poll_incoming_queue()
        
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['task_id'], "2026-05-02-test-task")
        self.assertEqual(tasks[0]['description'], "Test task")

    def test_poll_incoming_queue_empty(self):
        """Test: Poll incoming queue when empty."""
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        tasks = orch.poll_incoming_queue()
        
        self.assertEqual(len(tasks), 0)

    def test_poll_incoming_queue_multiple_tasks(self):
        """Test: Poll incoming queue with multiple tasks."""
        # Create multiple tasks
        for i in range(3):
            task_file = self.queue_dir / "incoming" / f"2026-05-02-task-{i}.yaml"
            task_data = {
                "task_id": f"2026-05-02-task-{i}",
                "description": f"Task {i}",
                "priority": "high"
            }
            with open(task_file, 'w') as f:
                yaml.dump(task_data, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        tasks = orch.poll_incoming_queue()
        
        self.assertEqual(len(tasks), 3)

    def test_poll_processing_queue_finds_handbacks(self):
        """Test: Poll processing queue and find HANDBACK files."""
        # Create a test HANDBACK
        handback_file = self.queue_dir / "processing" / "2026-05-02-test-HANDBACK-engineer.yaml"
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test",
            "status": "complete",
            "deliverables": [],
            "tokens_in": 100,
            "tokens_out": 80,
            "model": "claude-haiku-4-5",
            "effort": "high",
            "duration_minutes": 10,
            "escalations": 0
        }
        with open(handback_file, 'w') as f:
            yaml.dump(handback_data, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        handbacks = orch.poll_processing_queue()
        
        self.assertEqual(len(handbacks), 1)
        self.assertEqual(handbacks[0]['task_id'], "2026-05-02-test")
        self.assertEqual(handbacks[0]['status'], "complete")

    def test_poll_done_queue_finds_decisions(self):
        """Test: Poll done queue and find decision files."""
        # Create a test decision
        decision_file = self.queue_dir / "done" / "2026-05-02-test-PROCEED.yaml"
        decision_data = {
            "task_id": "2026-05-02-test",
            "decision": "PROCEED",
            "notes": "Test decision"
        }
        with open(decision_file, 'w') as f:
            yaml.dump(decision_data, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        decisions = orch.poll_done_queue()
        
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]['decision'], "PROCEED")


class TestDELEGATEValidation(unittest.TestCase):
    """Test DELEGATE format validation."""

    def setUp(self):
        """Setup for validation tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        (self.queue_dir / "incoming").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "processing").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "done").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_validate_delegate_format_valid(self):
        """Test: Valid DELEGATE format is accepted."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-05-02-test-task",
            "role": "Engineer",
            "model": "claude-haiku-4-5",
            "effort": "high",
            "scope": "Fix bug in module A; do not change module B",
            "context": [
                "File: src/main.py:42 (bug location)",
                "Error: NoneType error on line 42",
                "Repo state: clean main branch"
            ],
            "plan": [
                "Add test showing expected behavior",
                "Fix the bug at line 42",
                "Run tests to verify"
            ],
            "success_criteria": [
                "Tests pass",
                "No other changes",
                "Coverage maintained"
            ]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        is_valid = orch.validate_delegate_format(delegate)
        
        self.assertTrue(is_valid)

    def test_validate_delegate_missing_required_field(self):
        """Test: Invalid DELEGATE with missing required field."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-05-02-test-task",
            # Missing 'role'
            "model": "claude-haiku-4-5",
            "effort": "high",
            "scope": "Fix bug",
            "context": [],
            "plan": ["Step 1"],
            "success_criteria": ["Criteria 1"]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        is_valid = orch.validate_delegate_format(delegate)
        
        self.assertFalse(is_valid)

    def test_validate_delegate_invalid_role(self):
        """Test: Invalid DELEGATE with invalid role."""
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-05-02-test-task",
            "role": "InvalidRole",  # Invalid role
            "model": "claude-haiku-4-5",
            "effort": "high",
            "scope": "Fix bug",
            "context": [],
            "plan": ["Step 1"],
            "success_criteria": ["Criteria 1"]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        is_valid = orch.validate_delegate_format(delegate)
        
        self.assertFalse(is_valid)


class TestAgentRouting(unittest.TestCase):
    """Test agent routing per AGENTS.md decision tree."""

    def setUp(self):
        """Setup for routing tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        (self.queue_dir / "incoming").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "processing").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "done").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_route_security_scoped_task(self):
        """Test: Security-scoped task routes to Security Engineer."""
        task = {
            "task_id": "2026-05-02-security-audit",
            "description": "Audit credentials in config files",
            "scope": "security"
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        agent_info = orch.route_task(task)
        
        self.assertEqual(agent_info['role'], "Security Engineer")
        self.assertEqual(agent_info['model'], "claude-opus-4-7")

    def test_route_cross_service_architecture_task(self):
        """Test: Cross-service architecture task routes to Principal Engineer."""
        task = {
            "task_id": "2026-05-02-multi-service",
            "description": "Design service boundary changes affecting 3 services",
            "scope": "cross-service-architecture",
            "repos_affected": ["svc1", "svc2", "svc3"]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        agent_info = orch.route_task(task)
        
        self.assertEqual(agent_info['role'], "Principal Engineer")

    def test_route_complex_coding_without_plan(self):
        """Test: Complex coding without plan routes to Senior Engineer."""
        task = {
            "task_id": "2026-05-02-complex-feature",
            "description": "Implement complex feature without pre-written plan",
            "complexity": "high",
            "has_plan": False
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        agent_info = orch.route_task(task)
        
        self.assertEqual(agent_info['role'], "Senior Engineer")
        self.assertEqual(agent_info['model'], "claude-sonnet-4-6")

    def test_route_code_review_task(self):
        """Test: Code review task routes to Lead Engineer or Quality Engineer."""
        task = {
            "task_id": "2026-05-02-code-review",
            "description": "Review submitted code",
            "type": "code-review"
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        agent_info = orch.route_task(task)
        
        self.assertIn(agent_info['role'], ["Lead Engineer", "Quality Engineer"])

    def test_route_well_planned_task(self):
        """Test: Well-planned task routes to Engineer."""
        task = {
            "task_id": "2026-05-02-well-scoped",
            "description": "Fix timeout issue",
            "complexity": "low",
            "has_plan": True,
            "plan": [
                "Write test",
                "Fix timeout logic",
                "Verify tests pass"
            ]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        agent_info = orch.route_task(task)
        
        self.assertEqual(agent_info['role'], "Engineer")
        self.assertEqual(agent_info['model'], "claude-haiku-4-5")


    """Test span data capture for observability."""

    def setUp(self):
        """Setup for span capture tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        (self.queue_dir / "incoming").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "processing").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "done").mkdir(parents=True, exist_ok=True)
        self.artifacts_date_dir = self.artifacts_dir / "2026-05-02"
        self.artifacts_date_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_capture_span_from_handback(self):
        """Test: Capture OpenTelemetry span from HANDBACK."""
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test-task",
            "status": "complete",
            "tokens_in": 1200,
            "tokens_out": 800,
            "model": "claude-haiku-4-5",
            "duration_minutes": 15,
            "effort": "high",
            "escalations": 0
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        span_file = orch.capture_span("engineer", handback)
        
        self.assertTrue(span_file.exists())
        with open(span_file, 'r') as f:
            span_data = yaml.safe_load(f)
        
        self.assertEqual(span_data['task_id'], "2026-05-02-test-task")
        self.assertEqual(span_data['agent_role'], "engineer")
        self.assertEqual(span_data['tokens_in'], 1200)
        self.assertEqual(span_data['tokens_out'], 800)
        self.assertEqual(span_data['model'], "claude-haiku-4-5")

    def test_span_file_naming_convention(self):
        """Test: Span files follow SPAN-{timestamp}-{agent_type}.yaml naming."""
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test",
            "status": "complete",
            "tokens_in": 100,
            "tokens_out": 80,
            "model": "claude-haiku-4-5",
            "duration_minutes": 10,
            "effort": "high",
            "escalations": 0
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        span_file = orch.capture_span("engineer", handback)
        
        # Verify naming pattern
        self.assertTrue(span_file.name.startswith("SPAN-"))
        self.assertTrue(span_file.name.endswith("-engineer.yaml"))

    def test_span_contains_cost_calculation(self):
        """Test: Span includes calculated cost from token counts."""
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "model": "claude-haiku-4-5",
            "duration_minutes": 10,
            "effort": "high",
            "escalations": 0
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        span_file = orch.capture_span("engineer", handback)
        
        with open(span_file, 'r') as f:
            span_data = yaml.safe_load(f)
        
        # Should have cost calculated
        self.assertIn('cost', span_data)
        self.assertGreater(span_data['cost'], 0)


class TestArtifactIndexing(unittest.TestCase):
    """Test artifact indexing for searchability."""

    def setUp(self):
        """Setup for indexing tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        (self.queue_dir / "incoming").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "processing").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "done").mkdir(parents=True, exist_ok=True)
        
        # Create sample date directories with artifacts
        for day in range(1, 4):
            date_dir = self.artifacts_dir / f"2026-05-{day:02d}"
            date_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_generate_index_from_artifacts(self):
        """Test: Generate index.json from artifact files."""
        # Create sample span files
        date_dir = self.artifacts_dir / "2026-05-02"
        
        span1 = {
            "task_id": "2026-05-02-task-1",
            "agent_role": "engineer",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost": 0.045
        }
        with open(date_dir / "SPAN-001-engineer.yaml", 'w') as f:
            yaml.dump(span1, f)
        
        span2 = {
            "task_id": "2026-05-02-task-2",
            "agent_role": "senior-engineer",
            "status": "complete",
            "tokens_in": 2000,
            "tokens_out": 1200,
            "cost": 0.18
        }
        with open(date_dir / "SPAN-002-senior-engineer.yaml", 'w') as f:
            yaml.dump(span2, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        index_file = orch.generate_artifact_index()
        
        self.assertTrue(index_file.exists())
        with open(index_file, 'r') as f:
            index = json.load(f)
        
        self.assertIn('artifacts', index)
        self.assertEqual(len(index['artifacts']), 2)

    def test_index_searchable_by_task_id(self):
        """Test: Index is searchable by task_id."""
        date_dir = self.artifacts_dir / "2026-05-02"
        
        span = {
            "task_id": "2026-05-02-specific-task",
            "agent_role": "engineer",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost": 0.045
        }
        with open(date_dir / "SPAN-001-engineer.yaml", 'w') as f:
            yaml.dump(span, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        index_file = orch.generate_artifact_index()
        
        with open(index_file, 'r') as f:
            index = json.load(f)
        
        # Should be able to find by task_id
        found = [a for a in index['artifacts'] if a['task_id'] == "2026-05-02-specific-task"]
        self.assertEqual(len(found), 1)

    def test_index_searchable_by_agent_type(self):
        """Test: Index is searchable by agent_type."""
        date_dir = self.artifacts_dir / "2026-05-02"
        
        for i, agent in enumerate(["engineer", "senior-engineer", "lead-engineer"]):
            span = {
                "task_id": f"2026-05-02-task-{i}",
                "agent_role": agent,
                "status": "complete",
                "tokens_in": 1000,
                "tokens_out": 500,
                "cost": 0.045
            }
            with open(date_dir / f"SPAN-{i:03d}-{agent}.yaml", 'w') as f:
                yaml.dump(span, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        index_file = orch.generate_artifact_index()
        
        with open(index_file, 'r') as f:
            index = json.load(f)
        
        # Should be able to filter by agent type
        engineers = [a for a in index['artifacts'] if a['agent_role'] == "engineer"]
        self.assertEqual(len(engineers), 1)

    def test_index_includes_statistics(self):
        """Test: Index includes aggregate statistics."""
        date_dir = self.artifacts_dir / "2026-05-02"
        
        span = {
            "task_id": "2026-05-02-task-1",
            "agent_role": "engineer",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost": 0.045
        }
        with open(date_dir / "SPAN-001-engineer.yaml", 'w') as f:
            yaml.dump(span, f)
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        index_file = orch.generate_artifact_index()
        
        with open(index_file, 'r') as f:
            index = json.load(f)
        
        # Should have stats
        self.assertIn('stats', index)
        self.assertIn('total_tokens', index['stats'])
        self.assertIn('total_cost', index['stats'])


class TestHandbackProcessing(unittest.TestCase):
    """Test HANDBACK reception and processing."""

    def setUp(self):
        """Setup for HANDBACK tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        (self.queue_dir / "processing").mkdir(exist_ok=True)
        (self.queue_dir / "done").mkdir(exist_ok=True)

    def tearDown(self):
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_process_complete_handback(self):
        """Test: Process HANDBACK with status: complete."""
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test",
            "status": "complete",
            "deliverables": ["src/main.py: added feature X"],
            "tests": ["make verify: PASS"],
            "tokens_in": 1000,
            "tokens_out": 500,
            "model": "claude-haiku-4-5",
            "effort": "high",
            "duration_minutes": 15,
            "escalations": 0
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        result = orch.process_handback(handback)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['next_step'], "quality-gate")

    def test_process_blocked_handback(self):
        """Test: Process HANDBACK with status: blocked."""
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test",
            "status": "blocked",
            "blockers": ["Requires decision on API contract"],
            "tokens_in": 1000,
            "tokens_out": 500,
            "model": "claude-haiku-4-5",
            "effort": "high",
            "duration_minutes": 15,
            "escalations": 0
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        result = orch.process_handback(handback)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['next_step'], "escalate")

    def test_process_partial_handback(self):
        """Test: Process HANDBACK with status: partial."""
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "2026-05-02-test",
            "status": "partial",
            "deliverables": ["src/main.py: partial feature"],
            "tests": ["some tests passing"],
            "tokens_in": 1000,
            "tokens_out": 500,
            "model": "claude-haiku-4-5",
            "effort": "high",
            "duration_minutes": 15,
            "escalations": 0
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        result = orch.process_handback(handback)
        
        self.assertTrue(result['success'])
        self.assertIn(result['next_step'], ["quality-gate", "rework"])


class TestDelegateCreation(unittest.TestCase):
    """Test DELEGATE creation from task and routing."""

    def setUp(self):
        """Setup for DELEGATE creation tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.artifacts_dir = Path(self.temp_dir.name)
        self.queue_dir = self.artifacts_dir / "queue"
        (self.queue_dir / "incoming").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "processing").mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "done").mkdir(parents=True, exist_ok=True)
        self.delegates_dir = self.artifacts_dir / "delegates"
        self.delegates_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_create_delegate_for_engineer(self):
        """Test: Create DELEGATE for Engineer role."""
        task = {
            "task_id": "2026-05-02-fix-bug",
            "description": "Fix timeout in auth module",
            "complexity": "low",
            "has_plan": True,
            "plan": ["Write test", "Fix bug", "Verify"]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        delegate = orch.create_delegate(task, "Engineer", "claude-haiku-4-5", "high")
        
        self.assertEqual(delegate['handoff_type'], "DELEGATE")
        self.assertEqual(delegate['task_id'], task['task_id'])
        self.assertEqual(delegate['role'], "Engineer")
        self.assertEqual(delegate['model'], "claude-haiku-4-5")

    def test_delegate_includes_plan(self):
        """Test: DELEGATE includes plan for Engineer."""
        task = {
            "task_id": "2026-05-02-fix-bug",
            "description": "Fix timeout",
            "plan": ["Step 1", "Step 2", "Step 3"]
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        delegate = orch.create_delegate(task, "Engineer", "claude-haiku-4-5", "high")
        
        self.assertIn('plan', delegate)
        self.assertEqual(len(delegate['plan']), 3)

    def test_delegate_includes_scope(self):
        """Test: DELEGATE includes scope."""
        task = {
            "task_id": "2026-05-02-fix-bug",
            "description": "Fix timeout in auth module; don't change identity service"
        }
        
        from orchestrator import Orchestrator
        orch = Orchestrator(str(self.artifacts_dir), queue_dir=str(self.queue_dir))
        
        delegate = orch.create_delegate(task, "Engineer", "claude-haiku-4-5", "high")
        
        self.assertIn('scope', delegate)


if __name__ == '__main__':
    unittest.main()
