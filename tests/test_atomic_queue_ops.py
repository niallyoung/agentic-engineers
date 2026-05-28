"""
Tests for src/skills/queue-management/scripts/consistency.py

Targets: AtomicQueueOps — error paths for write_atomic, move_file,
         read_atomic, delete_atomic, rename_atomic.

Coverage target: 44% → 90%+
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import via path injection — queue-management uses hyphens (not a Python package)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / "src" / "skills" / "queue-management" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from consistency import AtomicQueueOps


class TestAtomicWrite:
    """Tests for AtomicQueueOps.write_atomic()."""

    def test_write_atomic_creates_file(self, tmp_path):
        """write_atomic should create the file with content."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"
        ops.write_atomic(target, '{"key": "value"}')
        assert target.exists()
        assert target.read_text() == '{"key": "value"}'

    def test_write_atomic_creates_parent_dirs(self, tmp_path):
        """write_atomic should create parent directories if they don't exist."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "nested" / "deep" / "test.json"
        ops.write_atomic(target, "content")
        assert target.exists()

    def test_write_atomic_overwrites_existing_file(self, tmp_path):
        """write_atomic should overwrite an existing file atomically."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"
        target.write_text("old content")
        ops.write_atomic(target, "new content")
        assert target.read_text() == "new content"

    def test_write_atomic_raises_ioerror_on_failure(self, tmp_path):
        """write_atomic should raise IOError when rename fails."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"

        with patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(IOError, match="Atomic write failed"):
                ops.write_atomic(target, "content")

    def test_write_atomic_cleans_up_temp_file_on_failure(self, tmp_path):
        """write_atomic should clean up temp file if rename fails."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"

        with patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(IOError):
                ops.write_atomic(target, "content")

        # No .tmp- files should remain
        tmp_files = list(tmp_path.glob(".tmp-*.json"))
        assert len(tmp_files) == 0


class TestAtomicMove:
    """Tests for AtomicQueueOps.move_file()."""

    def test_move_file_moves_successfully(self, tmp_path):
        """move_file should move a file to a new location."""
        ops = AtomicQueueOps(tmp_path)
        src = tmp_path / "source.json"
        src.write_text('{"data": 1}')
        dst = tmp_path / "moved" / "dest.json"

        ops.move_file(src, dst)
        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == '{"data": 1}'

    def test_move_file_raises_when_source_missing(self, tmp_path):
        """move_file should raise FileNotFoundError for missing source."""
        ops = AtomicQueueOps(tmp_path)
        src = tmp_path / "nonexistent.json"
        dst = tmp_path / "dest.json"

        with pytest.raises(FileNotFoundError, match="Source file not found"):
            ops.move_file(src, dst)

    def test_move_file_raises_ioerror_on_failure(self, tmp_path):
        """move_file should raise IOError when os.replace fails."""
        ops = AtomicQueueOps(tmp_path)
        src = tmp_path / "source.json"
        src.write_text("content")
        dst = tmp_path / "dest.json"

        with patch("os.replace", side_effect=OSError("cross-device link")):
            with pytest.raises(IOError, match="Atomic move failed"):
                ops.move_file(src, dst)

    def test_move_file_creates_parent_dirs(self, tmp_path):
        """move_file should create destination parent directories."""
        ops = AtomicQueueOps(tmp_path)
        src = tmp_path / "source.json"
        src.write_text("content")
        dst = tmp_path / "deep" / "nested" / "dest.json"

        ops.move_file(src, dst)
        assert dst.exists()


class TestAtomicRead:
    """Tests for AtomicQueueOps.read_atomic()."""

    def test_read_atomic_reads_content(self, tmp_path):
        """read_atomic should return file content."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"
        target.write_text('{"hello": "world"}')

        result = ops.read_atomic(target)
        assert result == '{"hello": "world"}'

    def test_read_atomic_raises_when_file_missing(self, tmp_path):
        """read_atomic should raise FileNotFoundError for missing file."""
        ops = AtomicQueueOps(tmp_path)
        missing = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError, match="File not found"):
            ops.read_atomic(missing)

    def test_read_atomic_raises_ioerror_on_read_failure(self, tmp_path):
        """read_atomic should raise IOError when reading fails."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"
        target.write_text("content")

        with patch("builtins.open", side_effect=OSError("permission denied")):
            with pytest.raises(IOError, match="Read failed"):
                ops.read_atomic(target)


class TestAtomicDelete:
    """Tests for AtomicQueueOps.delete_atomic()."""

    def test_delete_atomic_removes_file(self, tmp_path):
        """delete_atomic should remove the file."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"
        target.write_text("content")

        ops.delete_atomic(target)
        assert not target.exists()

    def test_delete_atomic_raises_when_file_missing(self, tmp_path):
        """delete_atomic should raise FileNotFoundError for missing file."""
        ops = AtomicQueueOps(tmp_path)
        missing = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError, match="File not found"):
            ops.delete_atomic(missing)

    def test_delete_atomic_raises_ioerror_on_failure(self, tmp_path):
        """delete_atomic should raise IOError when unlink fails."""
        ops = AtomicQueueOps(tmp_path)
        target = tmp_path / "test.json"
        target.write_text("content")

        with patch("os.unlink", side_effect=OSError("permission denied")):
            with pytest.raises(IOError, match="Delete failed"):
                ops.delete_atomic(target)


class TestAtomicRename:
    """Tests for AtomicQueueOps.rename_atomic()."""

    def test_rename_atomic_renames_file(self, tmp_path):
        """rename_atomic should rename the file."""
        ops = AtomicQueueOps(tmp_path)
        old = tmp_path / "old.json"
        old.write_text("data")
        new = tmp_path / "new.json"

        ops.rename_atomic(old, new)
        assert not old.exists()
        assert new.exists()
        assert new.read_text() == "data"

    def test_rename_atomic_raises_when_source_missing(self, tmp_path):
        """rename_atomic should raise FileNotFoundError for missing source."""
        ops = AtomicQueueOps(tmp_path)
        old = tmp_path / "nonexistent.json"
        new = tmp_path / "new.json"

        with pytest.raises(FileNotFoundError, match="Source file not found"):
            ops.rename_atomic(old, new)

    def test_rename_atomic_raises_ioerror_on_failure(self, tmp_path):
        """rename_atomic should raise IOError when rename fails."""
        ops = AtomicQueueOps(tmp_path)
        old = tmp_path / "old.json"
        old.write_text("content")
        new = tmp_path / "subdir" / "new.json"

        with patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(IOError, match="Atomic rename failed"):
                ops.rename_atomic(old, new)

    def test_rename_atomic_creates_parent_dirs(self, tmp_path):
        """rename_atomic should create destination parent directories."""
        ops = AtomicQueueOps(tmp_path)
        old = tmp_path / "old.json"
        old.write_text("content")
        new = tmp_path / "sub" / "dir" / "new.json"

        ops.rename_atomic(old, new)
        assert new.exists()
