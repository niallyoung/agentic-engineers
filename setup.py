#!/usr/bin/env python3
"""Minimal setup.py for agentic-engineers package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from VERSION file
version_file = Path(__file__).parent / "VERSION"
if version_file.exists():
    version = version_file.read_text().strip()
else:
    version = "0.8.0"  # fallback

setup(
    name="agentic-engineers",
    version=version,
    packages=find_packages(),
    python_requires=">=3.7",
)
