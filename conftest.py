"""
conftest.py — pytest configuration for agentic-engineers

Ensures the repo root is on sys.path so that:
  from src.orchestration.agents.X import Y
works when running tests from the repo root or any subdirectory.
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

# Also ensure PYTHONPATH environment variable is set
os.environ['PYTHONPATH'] = repo_root + os.pathsep + os.environ.get('PYTHONPATH', '')


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
