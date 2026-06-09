"""
Test Agent Scripts — Minimal implementations for protocol testing

This package contains simple test agents used to verify the DELEGATE/HANDBACK
protocol lifecycle without requiring full agent implementations.

Agents:
- echo_agent.py — Reads DELEGATE, writes HANDBACK with status=success
- delay_agent.py — Reads DELEGATE, sleeps 2s, writes HANDBACK
- escalate_agent.py — Reads DELEGATE, writes HANDBACK with status=escalate

Each agent is a standalone script that:
1. Reads DELEGATE from processing/ directory
2. Performs work (or simulates it)
3. Writes HANDBACK to processing/ directory

The orchestrator then moves the HANDBACK to done/ or other status directories.
"""
