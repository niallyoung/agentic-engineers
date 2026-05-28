"""
Tests for src/skills/spec-management/scripts/rollback_manager.py

Targets: RollbackManager — create_version(), get_history(), rollback(),
         rollback_to_version(), _write_version(), _read_version().

Coverage target: 49% → 90%+
"""

import importlib
import json
import os
import pytest
from pathlib import Path

# spec-management has hyphens in path — use importlib.import_module
_rm_mod = importlib.import_module("src.skills.spec-management.scripts.rollback_manager")
RollbackManager = _rm_mod.RollbackManager
SpecVersion = _rm_mod.SpecVersion


@pytest.fixture
def rollback_manager(tmp_path):
    """Return a RollbackManager using a temp directory."""
    return RollbackManager(version_dir=str(tmp_path / "spec-versions"))


class TestRollbackManagerInit:
    """Tests for RollbackManager.__init__()."""

    def test_init_creates_version_dir(self, tmp_path):
        """__init__ should create the version directory."""
        version_dir = tmp_path / "spec-versions"
        rm = RollbackManager(version_dir=str(version_dir))
        assert version_dir.exists()

    def test_init_with_repo_root_env_var(self, tmp_path, monkeypatch):
        """__init__ should resolve $REPO_ROOT from environment."""
        monkeypatch.setenv("REPO_ROOT", str(tmp_path))
        rm = RollbackManager(version_dir="$REPO_ROOT/spec-versions")
        expected = tmp_path / "spec-versions"
        assert rm.version_dir == expected
        assert expected.exists()

    def test_init_without_repo_root_uses_fallback(self, monkeypatch):
        """__init__ with $REPO_ROOT but no env var should use fallback path."""
        monkeypatch.delenv("REPO_ROOT", raising=False)
        rm = RollbackManager(version_dir="$REPO_ROOT/spec-versions")
        # Should not raise and version_dir should be set
        assert rm.version_dir is not None
        assert rm.version_dir.exists()

    def test_init_history_is_empty(self, rollback_manager):
        """Freshly initialized manager should have empty history."""
        assert rollback_manager.get_history() == []


class TestCreateVersion:
    """Tests for RollbackManager.create_version()."""

    def test_create_version_returns_spec_version(self, rollback_manager):
        """create_version should return a SpecVersion object."""
        version = rollback_manager.create_version(
            change_id="SPEC-2026-001",
            previous_hash="abc123",
            new_hash="def456",
            changes={"section": "new content"},
        )
        assert isinstance(version, SpecVersion)

    def test_create_version_sets_correct_fields(self, rollback_manager):
        """create_version should populate all SpecVersion fields."""
        version = rollback_manager.create_version(
            change_id="SPEC-2026-001",
            previous_hash="old_hash",
            new_hash="new_hash",
            changes={"ROUTING": "updated routing"},
        )
        assert version.change_id == "SPEC-2026-001"
        assert version.previous_hash == "old_hash"
        assert version.new_hash == "new_hash"
        assert version.applied_changes == {"ROUTING": "updated routing"}
        assert version.timestamp.endswith("Z")

    def test_create_version_generates_version_id(self, rollback_manager):
        """create_version should assign sequential version IDs."""
        v1 = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        v2 = rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        assert "1" in v1.version_id
        assert "2" in v2.version_id

    def test_create_version_appends_to_history(self, rollback_manager):
        """create_version should add the version to history."""
        rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        assert len(rollback_manager.get_history()) == 2

    def test_create_version_writes_file_to_disk(self, rollback_manager):
        """create_version should write a JSON file to the version directory."""
        version = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        version_file = rollback_manager.version_dir / f"{version.version_id}.json"
        assert version_file.exists()

    def test_create_version_file_content_is_valid_json(self, rollback_manager):
        """Written version file should contain valid JSON with correct data."""
        version = rollback_manager.create_version(
            "SPEC-001", "hash_a", "hash_b", {"section": "text"}
        )
        version_file = rollback_manager.version_dir / f"{version.version_id}.json"
        data = json.loads(version_file.read_text())
        assert data["change_id"] == "SPEC-001"
        assert data["previous_hash"] == "hash_a"
        assert data["new_hash"] == "hash_b"
        assert data["applied_changes"] == {"section": "text"}


class TestGetHistory:
    """Tests for RollbackManager.get_history()."""

    def test_get_history_returns_list(self, rollback_manager):
        """get_history should return a list."""
        assert isinstance(rollback_manager.get_history(), list)

    def test_get_history_is_in_chronological_order(self, rollback_manager):
        """History should be in oldest-first order."""
        rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        rollback_manager.create_version("SPEC-003", "h2", "h3", {})
        history = rollback_manager.get_history()
        assert history[0].change_id == "SPEC-001"
        assert history[1].change_id == "SPEC-002"
        assert history[2].change_id == "SPEC-003"

    def test_get_history_returns_copy(self, rollback_manager):
        """get_history should return a copy, not the internal list."""
        rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        history = rollback_manager.get_history()
        history.clear()
        # Original should not be affected
        assert len(rollback_manager.get_history()) == 1


class TestRollback:
    """Tests for RollbackManager.rollback()."""

    def test_rollback_with_no_history_fails(self, rollback_manager):
        """rollback() with no history should fail."""
        result = rollback_manager.rollback(steps=1)
        assert result["success"] is False
        assert "error" in result

    def test_rollback_more_than_history_fails(self, rollback_manager):
        """rollback() more steps than history should fail."""
        rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        result = rollback_manager.rollback(steps=5)
        assert result["success"] is False
        assert "error" in result

    def test_rollback_to_beginning_fails(self, rollback_manager):
        """rollback() to before first change should fail."""
        rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        result = rollback_manager.rollback(steps=1)
        assert result["success"] is False
        assert "error" in result

    def test_rollback_one_step_succeeds(self, rollback_manager):
        """rollback(1) with 2+ changes in history should succeed."""
        rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        result = rollback_manager.rollback(steps=1)
        assert result["success"] is True
        assert "previous_version" in result
        assert "reverted_versions" in result

    def test_rollback_one_step_returns_correct_target(self, rollback_manager):
        """rollback(1) should identify the correct version to rollback to."""
        v1 = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        v2 = rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        result = rollback_manager.rollback(steps=1)
        assert result["previous_version"] == v1.version_id
        assert v2.version_id in result["reverted_versions"]

    def test_rollback_multiple_steps(self, rollback_manager):
        """rollback(2) should revert 2 changes."""
        v1 = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        v2 = rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        v3 = rollback_manager.create_version("SPEC-003", "h2", "h3", {})
        result = rollback_manager.rollback(steps=2)
        assert result["success"] is True
        assert result["previous_version"] == v1.version_id
        assert len(result["reverted_versions"]) == 2


class TestRollbackToVersion:
    """Tests for RollbackManager.rollback_to_version()."""

    def test_rollback_to_nonexistent_version_fails(self, rollback_manager):
        """rollback_to_version with unknown version_id should fail."""
        result = rollback_manager.rollback_to_version("SPEC-v5.10.999")
        assert result["success"] is False
        assert "error" in result

    def test_rollback_to_version_succeeds(self, rollback_manager):
        """rollback_to_version should succeed when version exists."""
        v1 = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        result = rollback_manager.rollback_to_version(v1.version_id)
        assert result["success"] is True
        assert result["target_version"] == v1.version_id

    def test_rollback_to_version_lists_reverted(self, rollback_manager):
        """rollback_to_version should list all reverted versions."""
        v1 = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        v2 = rollback_manager.create_version("SPEC-002", "h1", "h2", {})
        v3 = rollback_manager.create_version("SPEC-003", "h2", "h3", {})
        result = rollback_manager.rollback_to_version(v1.version_id)
        assert v2.version_id in result["reverted_versions"]
        assert v3.version_id in result["reverted_versions"]

    def test_rollback_to_last_version_no_reversions(self, rollback_manager):
        """rollback_to_version of latest should have empty reverted list."""
        v1 = rollback_manager.create_version("SPEC-001", "h0", "h1", {})
        result = rollback_manager.rollback_to_version(v1.version_id)
        assert result["success"] is True
        assert result["reverted_versions"] == []


class TestReadVersion:
    """Tests for RollbackManager._read_version()."""

    def test_read_version_returns_spec_version(self, rollback_manager):
        """_read_version should reconstruct a SpecVersion from disk."""
        v1 = rollback_manager.create_version("SPEC-001", "old", "new", {"s": "text"})
        read_back = rollback_manager._read_version(v1.version_id)
        assert read_back is not None
        assert read_back.version_id == v1.version_id
        assert read_back.change_id == "SPEC-001"
        assert read_back.previous_hash == "old"
        assert read_back.new_hash == "new"
        assert read_back.applied_changes == {"s": "text"}

    def test_read_version_returns_none_for_missing(self, rollback_manager):
        """_read_version should return None for unknown version."""
        result = rollback_manager._read_version("SPEC-v5.10.999")
        assert result is None
