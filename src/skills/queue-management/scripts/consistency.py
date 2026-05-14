"""
Consistency Module

Atomic file operations using POSIX semantics (temp-file-then-move).
"""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class AtomicQueueOps:
    """Atomic file operations for queue management."""

    def __init__(self, queue_path: Path):
        """
        Initialize atomic operations handler.

        Args:
            queue_path: Root queue path for temp file placement
        """
        self.queue_path = Path(queue_path)

    def write_atomic(self, target_path: Path, content: str) -> None:
        """
        Write file atomically using temp-file-then-move.

        Algorithm:
        1. Write to temp file in same directory (atomic rename)
        2. Rename temp to target (atomic on POSIX)
        3. No partial writes on crash

        Args:
            target_path: Target file path
            content: Content to write

        Raises:
            IOError: Write or rename failed
        """
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in same directory (for atomic rename)
        try:
            with NamedTemporaryFile(
                mode="w",
                dir=target_path.parent,
                delete=False,
                prefix=".tmp-",
                suffix=".json",
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Atomic rename (POSIX semantics)
            os.replace(tmp_path, target_path)
        except Exception as e:
            # Clean up temp file if it exists
            try:
                os.unlink(tmp_path)
            except (NameError, OSError):
                pass
            raise IOError(f"Atomic write failed for {target_path}: {e}")

    def move_file(self, from_path: Path, to_path: Path) -> None:
        """
        Move file atomically between queue states.

        Uses os.replace() which is atomic on POSIX systems.

        Args:
            from_path: Source file path
            to_path: Target file path

        Raises:
            FileNotFoundError: Source file doesn't exist
            IOError: Move operation failed
        """
        from_path = Path(from_path)
        to_path = Path(to_path)

        if not from_path.exists():
            raise FileNotFoundError(f"Source file not found: {from_path}")

        to_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            os.replace(from_path, to_path)
        except Exception as e:
            raise IOError(f"Atomic move failed from {from_path} to {to_path}: {e}")

    def read_atomic(self, file_path: Path) -> str:
        """
        Read file content (with implicit atomicity from OS).

        Args:
            file_path: File to read

        Returns:
            File content as string

        Raises:
            FileNotFoundError: File doesn't exist
            IOError: Read failed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path) as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Read failed for {file_path}: {e}")

    def delete_atomic(self, file_path: Path) -> None:
        """
        Delete file atomically.

        Args:
            file_path: File to delete

        Raises:
            FileNotFoundError: File doesn't exist
            IOError: Delete failed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            os.unlink(file_path)
        except Exception as e:
            raise IOError(f"Delete failed for {file_path}: {e}")

    def rename_atomic(self, old_path: Path, new_path: Path) -> None:
        """
        Rename file atomically.

        Args:
            old_path: Current file path
            new_path: New file path

        Raises:
            FileNotFoundError: Source file doesn't exist
            IOError: Rename failed
        """
        old_path = Path(old_path)
        new_path = Path(new_path)

        if not old_path.exists():
            raise FileNotFoundError(f"Source file not found: {old_path}")

        new_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            os.replace(old_path, new_path)
        except Exception as e:
            raise IOError(f"Atomic rename failed from {old_path} to {new_path}: {e}")
