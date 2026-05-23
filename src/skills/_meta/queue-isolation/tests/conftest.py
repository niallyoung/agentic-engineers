"""
Pytest conftest for queue-isolation tests.

Adds the scripts directory to sys.path so tests can import queue_isolation
directly (works with hyphenated directory names).
"""
import sys
from pathlib import Path

# Add <skill-root>/scripts to sys.path for direct module imports
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
