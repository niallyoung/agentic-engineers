#!/usr/bin/env python3
"""Minimal setup.py for agentic-engineers package."""

from setuptools import setup, find_packages
from pathlib import Path
import subprocess

def get_version():
    """Get version from git tags (primary source via get_version.py).
    
    Priority:
      1. get_version.py script (reads git tags as primary source)
      2. Hardcoded fallback "0.8.0" (for offline/no-git scenarios)
    """
    try:
        script_path = Path(__file__).parent / "scripts" / "get_version.py"
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    # Last resort: hardcoded fallback (first release version)
    return "0.8.0"

setup(
    name="agentic-engineers",
    version=get_version(),
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "cryptography>=41.0.0",
        "pyyaml>=6.0",
    ],
)
