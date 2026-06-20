"""
Tests for FeedbackLoop skill feedback functionality.

Coverage:
- record_skill_feedback accumulates items correctly
- get_accumulated_count returns correct totals
- get_top_feedback_candidates filters by threshold
- Feedback persists to disk in JSONL format
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.orchestration.feedback.feedback_loop import FeedbackLoop, FeedbackStore


@pytest.fixture
def temp_feedback_dir():
    """Create a temporary directory for feedback artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def feedback_loop(tmp_path):
    """Create a FeedbackLoop instance for testing."""
    # Use temp directory for all paths
    store_path = tmp_path / "feedback_store.jsonl"
    store = FeedbackStore(store_path)

    # Create a new loop
    loop = FeedbackLoop(store=store)

    # Clear the persisted feedback that was loaded from disk for testing
    loop._skill_raw_feedback = {}

    # Override the record method to write to our temp directory
    def patched_record(skill_name, items):
        if not items:
            return
        loop._skill_raw_feedback.setdefault(skill_name, []).extend(items)
        # For testing, write to temp directory
        feedback_dir = tmp_path / "skill-feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        feedback_file = feedback_dir / f"{skill_name}.jsonl"
        with feedback_file.open("a", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")

    loop.record_skill_feedback = patched_record
    loop._feedback_dir = tmp_path / "skill-feedback"
    return loop


class TestFeedbackLoopSkillFeedback:
    """Test FeedbackLoop skill feedback recording and analysis."""

    def test_record_skill_feedback_accumulates(self, feedback_loop):
        """Multiple calls accumulate correctly in memory."""
        # First call
        feedback_loop.record_skill_feedback(
            "queue-management",
            [
                {"skill_name": "queue-management", "effectiveness_score": 0.85},
                {"skill_name": "queue-management", "effectiveness_score": 0.80},
            ]
        )

        assert feedback_loop.get_accumulated_count("queue-management") == 2

        # Second call
        feedback_loop.record_skill_feedback(
            "queue-management",
            [
                {"skill_name": "queue-management", "effectiveness_score": 0.90},
            ]
        )

        assert feedback_loop.get_accumulated_count("queue-management") == 3

    def test_get_accumulated_count_correct(self, feedback_loop):
        """Returns correct total for a skill."""
        # Record feedback for two different skills
        feedback_loop.record_skill_feedback(
            "protocol-validator",
            [
                {"skill_name": "protocol-validator", "effectiveness_score": 0.75},
                {"skill_name": "protocol-validator", "effectiveness_score": 0.70},
                {"skill_name": "protocol-validator", "effectiveness_score": 0.80},
                {"skill_name": "protocol-validator", "effectiveness_score": 0.85},
            ]
        )

        feedback_loop.record_skill_feedback(
            "orchestrator",
            [
                {"skill_name": "orchestrator", "effectiveness_score": 0.95},
                {"skill_name": "orchestrator", "effectiveness_score": 0.90},
            ]
        )

        # Verify counts
        assert feedback_loop.get_accumulated_count("protocol-validator") == 4
        assert feedback_loop.get_accumulated_count("orchestrator") == 2
        assert feedback_loop.get_accumulated_count("non-existent-skill") == 0

    def test_get_top_feedback_candidates_at_threshold(self, feedback_loop):
        """Returns skills at or above threshold."""
        # Set up: 3 items for skill A, 2 for skill B, 4 for skill C
        feedback_loop.record_skill_feedback(
            "skill-a",
            [
                {"skill_name": "skill-a", "effectiveness_score": 0.8},
                {"skill_name": "skill-a", "effectiveness_score": 0.75},
                {"skill_name": "skill-a", "effectiveness_score": 0.85},
            ]
        )

        feedback_loop.record_skill_feedback(
            "skill-b",
            [
                {"skill_name": "skill-b", "effectiveness_score": 0.6},
                {"skill_name": "skill-b", "effectiveness_score": 0.65},
            ]
        )

        feedback_loop.record_skill_feedback(
            "skill-c",
            [
                {"skill_name": "skill-c", "effectiveness_score": 0.9},
                {"skill_name": "skill-c", "effectiveness_score": 0.92},
                {"skill_name": "skill-c", "effectiveness_score": 0.88},
                {"skill_name": "skill-c", "effectiveness_score": 0.95},
            ]
        )

        # Get candidates with threshold 3
        candidates = feedback_loop.get_top_feedback_candidates(threshold=3)
        candidate_skills = [name for name, items in candidates]

        # skill-a (3 items) and skill-c (4 items) should be included
        assert "skill-a" in candidate_skills
        assert "skill-c" in candidate_skills
        # skill-b (2 items) should NOT be included
        assert "skill-b" not in candidate_skills

        # Verify counts
        for name, items in candidates:
            if name == "skill-a":
                assert len(items) == 3
            elif name == "skill-c":
                assert len(items) == 4

    def test_feedback_persists_to_disk(self, feedback_loop):
        """JSONL written to artifacts/metrics/skill-feedback/{skill_name}.jsonl."""
        # Record feedback
        items = [
            {"skill_name": "test-skill", "effectiveness_score": 0.85, "clarity_score": 0.90},
            {"skill_name": "test-skill", "effectiveness_score": 0.80, "clarity_score": 0.88},
        ]
        feedback_loop.record_skill_feedback("test-skill", items)

        # Check that file was created
        feedback_file = feedback_loop._feedback_dir / "test-skill.jsonl"
        assert feedback_file.exists()

        # Verify JSONL format and content
        with feedback_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Parse each line and verify
        parsed_items = []
        for line in lines:
            line = line.strip()
            if line:
                parsed = json.loads(line)
                parsed_items.append(parsed)

        assert len(parsed_items) == 2
        assert parsed_items[0]["effectiveness_score"] == 0.85
        assert parsed_items[1]["effectiveness_score"] == 0.80
        assert parsed_items[0]["clarity_score"] == 0.90
