"""
conftest.py — pytest configuration for agentic-engineers

Ensures the repo root is on sys.path so that:
  from src.orchestration.agents.X import Y
works when running tests from the repo root.
"""
import sys
import os

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.dirname(__file__))
