"""
conftest.py — pytest configuration for agentic-engineers

Ensures the repo root is on sys.path so that:
  from src.orchestration.agents.X import Y
works when running tests from the repo root or any subdirectory.
"""
import sys
import os
from pathlib import Path

# Get repo root (where conftest.py lives)
repo_root = str(Path(__file__).parent.absolute())

# Ensure repo root is in sys.path (at beginning for priority)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
