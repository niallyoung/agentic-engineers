"""
conftest.py — pytest configuration for agentic-engineers

Ensures the repo root and src/skills paths are on sys.path so that:
  - from src.orchestration.agents.X import Y
  - from queue-management.scripts.queue_ops import QueueOperations  # from skill
works when running tests from the repo root or any subdirectory.

Key insight: Skills with hyphenated names (queue-management, file-sync, etc.) 
are importable via importlib when src/skills/ is in sys.path. We use 
importlib.import_module('queue-management.scripts.queue_ops') rather than
direct imports to handle Python's inability to import modules with hyphens.
"""
import sys
import os
import importlib
from pathlib import Path

# Get repo root (where conftest.py lives)
repo_root = str(Path(__file__).parent.absolute())

# Ensure repo root is in sys.path (at beginning for priority)
if repo_root not in sys.path:
   sys.path.insert(0, repo_root)

# Add src/skills to sys.path so we can import hyphenated skill packages
skills_path = os.path.join(repo_root, "src", "skills")
if os.path.exists(skills_path) and skills_path not in sys.path:
    sys.path.insert(0, skills_path)

# Ensure PYTHONPATH environment variable is set for subprocesses
if os.path.exists(skills_path):
    os.environ['PYTHONPATH'] = skills_path + os.pathsep + repo_root + os.pathsep + os.environ.get('PYTHONPATH', '')


def pytest_configure(config):
    """
    Configure pytest by ensuring skill paths are in sys.path before collection.
    """
    skills_path = os.path.join(repo_root, "src", "skills")
    if os.path.exists(skills_path) and skills_path not in sys.path:
        sys.path.insert(0, skills_path)


def import_hyphenated_module(module_path):
   """
   Import a module with hyphens in the package name using importlib.
    
   Example:
       import_hyphenated_module('src.skills.spec-management.scripts.spec_manager')
    
   This is necessary because GitHub Actions doesn't preserve symlinks, so the 
   underscored package names (spec_management) are not available in CI, but the
   hyphenated ones (spec-management) are the canonical directories.
   """
   return importlib.import_module(module_path)
