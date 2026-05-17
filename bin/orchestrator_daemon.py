#!/usr/bin/env python3
"""
Orchestrator Polling Daemon Entry Point

This script runs the continuous queue polling loop for the Orchestrator.
It can be invoked from the OpenCode agent or run standalone.

Usage:
    python orchestrator_daemon.py [--idle-timeout 60] [--poll-interval 5] [--max-cycles N]
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.orchestration.agents.automation import AutomationController, main

if __name__ == "__main__":
    # Run the automation controller with command-line arguments
    sys.exit(main() or 0)
