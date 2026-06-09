"""
Test that queue paths use canonical format WITHOUT 'artifacts/' segment.
These tests should FAIL initially (RED) then PASS after Phase 2 B1 fixes.
"""
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_artifacts_prefix_removed_from_harness_session_manager():
    """IMPORTANT: This test documents the requirement that artifacts/ must be removed."""
    from src.opencode.harness_session_manager import HarnessSessionManager
    
    # Create a session manager
    mgr = HarnessSessionManager(
        harness="claude-code",  # Use valid harness name
        session_id="test-phase2-001"
    )
    
    queue_root = mgr.queue_root
    
    # ASSERTION: Queue path should NOT contain 'artifacts/'
    # Currently it DOES (artifacts is at ~/.agentic-engineers/artifacts/...)
    # This test FAILS until Phase 2 B1 removes artifacts/
    
    queue_root_str = str(queue_root)
    print(f"\nCurrent queue_root: {queue_root_str}")
    
    # This should FAIL (RED) with current code
    assert "artifacts" not in queue_root_str, \
        f"❌ RED TEST: Path still contains 'artifacts/': {queue_root_str}"
    
    # Expected canonical path
    expected_base = Path.home() / ".agentic-engineers" / "test-phase2-001" / "claude-code" / "queue"
    print(f"Expected path:     {expected_base}")
    print(f"Canonical check:   OK (no artifacts/)")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
