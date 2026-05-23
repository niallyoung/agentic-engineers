#!/usr/bin/env python3
"""Minimal setup.py for agentic-engineers package."""

from setuptools import setup, find_packages
from pathlib import Path
import subprocess

def get_version():
    """Get version from get_version.py (reads git tags as primary source)."""
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
    
    # Fallback: read VERSION file
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    
    # Last resort
    return "0.8.0"

setup(
    name="agentic-engineers",
    version=get_version(),
    packages=find_packages(),
    python_requires=">=3.7",
)
