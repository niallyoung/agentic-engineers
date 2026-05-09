"""
Tests for src/orchestration/tools/lead_review_cli.py — interactive CLI
for Lead Engineer gray-zone HANDBACK review.

Covers: _load_reviews, save_review_decision, list_pending_reviews,
        review_handback (via input mocking), generate_follow_up_issue.
"""

import json
import sys
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime

from src.orchestration.tools.lead_review_cli import (
    list_pending_reviews,
    review_handback,
    save_review_decision,
    generate_follow_up_issue,
    _load_reviews,
    REVIEWS_FILE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_reviews_file(tmp_path, monkeypatch):
    """Redirect REVIEWS_FILE to a temp path for each test."""
    tmp_reviews = tmp_path / "gray_zone_reviews.json"
    import src.orchestration.tools.lead_review_cli as cli_module
    monkeypatch.setattr(cli_module, "REVIEWS_FILE", tmp_reviews)
    return tmp_reviews


@pytest.fixture
def populated_reviews(isolated_reviews_file):
    """Write sample reviews to the temp file."""
    reviews = {
        "pending-task-001": {
            "task_id": "pending-task-001",
            "score": 75,
            "risk_level": "low",
            "criteria_met": "3/4",
            "coverage": 88,
            "status": "pending",
        },
        "reviewed-task-002": {
            "task_id": "reviewed-task-002",
            "score": 72,
            "risk_level": "medium",
            "criteria_met": "2/3",
            "coverage": 85,
            "status": "reviewed",
            "decision": "CONDITIONAL",
        },
        "pending-task-003": {
            "task_id": "pending-task-003",
            "score": 78,
            "risk_level": "low",
            "criteria_met": "4/4",
            "coverage": 91,
            "status": "pending",
        },
    }
    isolated_reviews_file.parent.mkdir(parents=True, exist_ok=True)
    with open(isolated_reviews_file, "w") as f:
        json.dump(reviews, f)
    return reviews


# ---------------------------------------------------------------------------
# _load_reviews
# ---------------------------------------------------------------------------

class TestLoadReviews:
    def test_returns_empty_dict_when_file_missing(self, isolated_reviews_file):
        """_load_reviews returns {} when the reviews file does not exist."""
        import src.orchestration.tools.lead_review_cli as cli_module
        assert not isolated_reviews_file.exists()
        result = cli_module._load_reviews()
        assert result == {}

    def test_returns_dict_when_file_exists(self, populated_reviews, isolated_reviews_file):
        """_load_reviews returns dict from file when it exists."""
        import src.orchestration.tools.lead_review_cli as cli_module
        result = cli_module._load_reviews()
        assert isinstance(result, dict)
        assert "pending-task-001" in result

    def test_preserves_all_fields(self, populated_reviews, isolated_reviews_file):
        """_load_reviews preserves all fields from the JSON file."""
        import src.orchestration.tools.lead_review_cli as cli_module
        result = cli_module._load_reviews()
        task = result["pending-task-001"]
        assert task["score"] == 75
        assert task["risk_level"] == "low"
        assert task["status"] == "pending"


# ---------------------------------------------------------------------------
# save_review_decision
# ---------------------------------------------------------------------------

class TestSaveReviewDecision:
    def test_creates_reviews_file_if_missing(self, isolated_reviews_file):
        """save_review_decision creates the reviews file when it doesn't exist."""
        import src.orchestration.tools.lead_review_cli as cli_module
        assert not isolated_reviews_file.exists()
        cli_module.save_review_decision("task-new", "ACCEPT", "Looks good")
        assert isolated_reviews_file.exists()

    def test_persists_decision_to_file(self, isolated_reviews_file):
        """save_review_decision persists decision to the JSON file."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.save_review_decision("task-001", "REWORK", "Needs more tests")
        result = cli_module._load_reviews()
        assert "task-001" in result
        assert result["task-001"]["decision"] == "REWORK"
        assert result["task-001"]["notes"] == "Needs more tests"

    def test_sets_status_to_reviewed(self, isolated_reviews_file):
        """save_review_decision sets status=reviewed."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.save_review_decision("task-002", "ACCEPT", "Fine")
        result = cli_module._load_reviews()
        assert result["task-002"]["status"] == "reviewed"

    def test_adds_reviewed_at_timestamp(self, isolated_reviews_file):
        """save_review_decision adds reviewed_at ISO timestamp."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.save_review_decision("task-003", "CONDITIONAL", "Minor fixes needed")
        result = cli_module._load_reviews()
        assert "reviewed_at" in result["task-003"]
        # Timestamp ends with 'Z'
        assert result["task-003"]["reviewed_at"].endswith("Z")

    def test_preserves_existing_task_fields(self, populated_reviews, isolated_reviews_file):
        """save_review_decision merges with existing task data."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.save_review_decision("pending-task-001", "ACCEPT", "Good work")
        result = cli_module._load_reviews()
        task = result["pending-task-001"]
        assert task["score"] == 75  # preserved from original
        assert task["decision"] == "ACCEPT"

    def test_can_save_all_three_decisions(self, isolated_reviews_file):
        """All three valid decisions can be saved."""
        import src.orchestration.tools.lead_review_cli as cli_module
        for decision in ("ACCEPT", "CONDITIONAL", "REWORK"):
            cli_module.save_review_decision(f"task-{decision}", decision, "notes")
        result = cli_module._load_reviews()
        assert result["task-ACCEPT"]["decision"] == "ACCEPT"
        assert result["task-CONDITIONAL"]["decision"] == "CONDITIONAL"
        assert result["task-REWORK"]["decision"] == "REWORK"

    def test_overwrites_existing_decision(self, isolated_reviews_file):
        """save_review_decision can overwrite a previous decision."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.save_review_decision("task-change", "ACCEPT", "First decision")
        cli_module.save_review_decision("task-change", "REWORK", "Changed mind")
        result = cli_module._load_reviews()
        assert result["task-change"]["decision"] == "REWORK"


# ---------------------------------------------------------------------------
# list_pending_reviews
# ---------------------------------------------------------------------------

class TestListPendingReviews:
    def test_prints_no_pending_when_empty(self, isolated_reviews_file, capsys):
        """list_pending_reviews prints no-pending message when file is empty."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.list_pending_reviews()
        captured = capsys.readouterr()
        assert "No pending" in captured.out or "pending" in captured.out.lower()

    def test_prints_pending_count(self, populated_reviews, capsys):
        """list_pending_reviews shows count of pending reviews."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.list_pending_reviews()
        captured = capsys.readouterr()
        assert "2" in captured.out  # 2 pending tasks in fixture

    def test_prints_task_ids_of_pending(self, populated_reviews, capsys):
        """list_pending_reviews shows task IDs of pending reviews."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.list_pending_reviews()
        captured = capsys.readouterr()
        assert "pending-task-001" in captured.out
        assert "pending-task-003" in captured.out

    def test_does_not_show_reviewed_tasks(self, populated_reviews, capsys):
        """list_pending_reviews does not show already-reviewed tasks."""
        import src.orchestration.tools.lead_review_cli as cli_module
        cli_module.list_pending_reviews()
        captured = capsys.readouterr()
        assert "reviewed-task-002" not in captured.out

    def test_no_file_shows_no_pending(self, isolated_reviews_file, capsys):
        """list_pending_reviews with missing file shows no-pending message."""
        import src.orchestration.tools.lead_review_cli as cli_module
        assert not isolated_reviews_file.exists()
        cli_module.list_pending_reviews()
        captured = capsys.readouterr()
        assert "No pending" in captured.out or "0" in captured.out or "pending" in captured.out.lower()


# ---------------------------------------------------------------------------
# review_handback — interactive flow (input mocked)
# ---------------------------------------------------------------------------

class TestReviewHandback:
    def test_accept_decision_saved(self, populated_reviews, capsys):
        """review_handback with 'a' input saves ACCEPT decision."""
        import src.orchestration.tools.lead_review_cli as cli_module
        with patch("builtins.input", side_effect=["a", "Accepted in gray zone"]):
            cli_module.review_handback("pending-task-001")
        result = cli_module._load_reviews()
        assert result["pending-task-001"]["decision"] == "ACCEPT"

    def test_rework_decision_saved(self, populated_reviews, capsys):
        """review_handback with 'r' input saves REWORK decision."""
        import src.orchestration.tools.lead_review_cli as cli_module
        with patch("builtins.input", side_effect=["r", "Needs more test coverage"]):
            cli_module.review_handback("pending-task-001")
        result = cli_module._load_reviews()
        assert result["pending-task-001"]["decision"] == "REWORK"

    def test_conditional_decision_saved(self, populated_reviews, capsys):
        """review_handback with 'c' input saves CONDITIONAL decision."""
        import src.orchestration.tools.lead_review_cli as cli_module
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "gh not configured"
        with patch("builtins.input", side_effect=["c", "Needs follow-up", "Fix coverage, add tests"]), \
             patch("subprocess.run", return_value=mock_result):
            cli_module.review_handback("pending-task-001")
        result = cli_module._load_reviews()
        assert result["pending-task-001"]["decision"] == "CONDITIONAL"

    def test_view_then_accept(self, populated_reviews, capsys):
        """review_handback with 'v' then 'a' shows details then accepts."""
        import src.orchestration.tools.lead_review_cli as cli_module
        with patch("builtins.input", side_effect=["v", "a", "Fine after review"]):
            cli_module.review_handback("pending-task-001")
        captured = capsys.readouterr()
        # 'v' should have triggered JSON output
        assert "pending-task-001" in captured.out

    def test_invalid_input_reprompts(self, populated_reviews, capsys):
        """review_handback re-prompts on invalid input."""
        import src.orchestration.tools.lead_review_cli as cli_module
        with patch("builtins.input", side_effect=["x", "z", "r", "Finally done"]):
            cli_module.review_handback("pending-task-001")
        result = cli_module._load_reviews()
        assert result["pending-task-001"]["decision"] == "REWORK"

    def test_review_handback_unknown_task_id(self, isolated_reviews_file, capsys):
        """review_handback handles a task_id not in reviews file."""
        import src.orchestration.tools.lead_review_cli as cli_module
        with patch("builtins.input", side_effect=["a", "Unknown task accepted"]):
            cli_module.review_handback("completely-unknown-task")
        result = cli_module._load_reviews()
        # Should still save the decision
        assert result["completely-unknown-task"]["decision"] == "ACCEPT"

    def test_accept_uses_default_notes_when_empty(self, populated_reviews, capsys):
        """review_handback uses default ACCEPT notes when user enters empty string."""
        import src.orchestration.tools.lead_review_cli as cli_module
        with patch("builtins.input", side_effect=["a", ""]):
            cli_module.review_handback("pending-task-001")
        result = cli_module._load_reviews()
        # Default notes should be set
        assert result["pending-task-001"]["notes"]


# ---------------------------------------------------------------------------
# generate_follow_up_issue
# ---------------------------------------------------------------------------

class TestGenerateFollowUpIssue:
    def test_calls_gh_cli(self, capsys):
        """generate_follow_up_issue invokes 'gh issue create' via subprocess."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/org/repo/issues/42", stderr="")
            generate_follow_up_issue("task-001", ["Fix coverage", "Address TODOs"])
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "gh" in args
        assert "issue" in args
        assert "create" in args

    def test_issue_title_contains_task_id(self, capsys):
        """Generated issue title includes the task_id."""
        captured_args = {}
        def capture_call(args, **kwargs):
            captured_args["args"] = args
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=capture_call):
            generate_follow_up_issue("my-task-id", ["Fix something"])
        title_idx = captured_args["args"].index("--title") + 1
        assert "my-task-id" in captured_args["args"][title_idx]

    def test_issue_body_contains_follow_up_items(self, capsys):
        """Issue body contains all follow-up items as checkboxes."""
        captured_args = {}
        def capture_call(args, **kwargs):
            captured_args["args"] = args
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=capture_call):
            generate_follow_up_issue("task-abc", ["Item one", "Item two"])
        body_idx = captured_args["args"].index("--body") + 1
        body = captured_args["args"][body_idx]
        assert "Item one" in body
        assert "Item two" in body

    def test_gh_cli_not_found_prints_fallback(self, capsys):
        """generate_follow_up_issue prints items when gh CLI is unavailable."""
        with patch("subprocess.run", side_effect=FileNotFoundError("gh not found")):
            generate_follow_up_issue("task-001", ["Fix coverage"])
        captured = capsys.readouterr()
        assert "Fix coverage" in captured.out or "unavailable" in captured.out.lower()

    def test_gh_cli_timeout_prints_fallback(self, capsys):
        """generate_follow_up_issue prints items when gh CLI times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 30)):
            generate_follow_up_issue("task-001", ["Follow up item"])
        captured = capsys.readouterr()
        assert "Follow up item" in captured.out or "unavailable" in captured.out.lower()

    def test_gh_cli_nonzero_exit_warns(self, capsys):
        """generate_follow_up_issue warns when gh CLI returns non-zero exit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="authentication failed")
            generate_follow_up_issue("task-001", ["Fix stuff"])
        captured = capsys.readouterr()
        # Should print a warning
        assert "warning" in captured.out.lower() or "⚠️" in captured.out or "Could not" in captured.out
