#!/usr/bin/env python3
"""Minimal setup.py for agentic-engineers package."""

import subprocess
import sys
from pathlib import Path

from setuptools import setup, find_packages

_SCRIPTS_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))
from get_version import FALLBACK_VERSION  # noqa: E402


def get_version():
    """Get version from git tags (primary source via get_version.py).

    Priority:
      1. get_version.py script (reads git tags as primary source)
      2. FALLBACK_VERSION (for offline/no-git scenarios)
    """
    try:
        script_path = _SCRIPTS_DIR / "get_version.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    # Last resort: shared fallback constant (first release version)
    return FALLBACK_VERSION


setup(
    name="agentic-engineers",
    version=get_version(),
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "pyyaml>=6.0",
    ],
)
