"""
E2E Protocol Tests: DELEGATE/HANDBACK Schema Round-Trip (Phase 4)

Comprehensive tests covering:
1. DELEGATE round-trips through YAML serialization with all fields intact
2. HANDBACK round-trips through YAML serialization with all fields intact
3. Failure/blocked/escalate HANDBACKs preserve their status-specific metadata
4. Escalation HANDBACKs produce a well-formed follow-up DELEGATE
5. Full DELEGATE -> HANDBACK protocol cycle

These tests verify the DELEGATE/HANDBACK wire format itself — construct,
serialize to YAML, deserialize, and confirm every required field survives —
independent of *how* a DELEGATE reaches its target agent.

NOTE (queue-removal, task-2026-08-13-queue-removal-code): this file used to
drive its DELEGATE/HANDBACK fixtures through a simulated filesystem queue
(incoming/ -> processing/ -> done/failed/ directory moves, multi-harness
queue-path isolation, and a span-capture write to artifacts/{date}/). With
dispatch now a direct sub-agent spawn — a DELEGATE passed directly as a
spawn prompt, a HANDBACK returned synchronously as that call's result — there
is no queue directory state machine to exercise. What remains valuable and is
kept here is the protocol-schema round-trip: that a DELEGATE/HANDBACK
survives YAML (de)serialization with every required field intact. The
directory-transition and queue-isolation assertions were removed as
queue-specific, not schema-specific.

Usage:
    pytest tests/test_e2e_protocol_full_cycle.py -v -s
    make test-protocol-e2e
"""

import yaml
import uuid
from typing import Dict

import pytest


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_delegate() -> Dict:
    """Valid DELEGATE YAML with all required fields."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": f"task-{uuid.uuid4().hex[:8]}",
        "agent": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "high",
        "scope": "Test implementation task with full protocol coverage",
        "plan": [
            "1. Read and understand requirement",
            "2. Identify affected files",
            "3. Write implementation",
            "4. Run tests",
            "5. Commit changes"
        ],
        "success_criteria": [
            "All tests pass",
            "Code follows style guide",
            "No linter warnings"
        ],
        "context": [
            "File: test.py",
            "Error: None",
            "Root cause: Testing protocol"
        ],
        "estimated_tokens": 2000,
    }


@pytest.fixture
def sample_handback(sample_delegate: Dict) -> Dict:
    """Valid HANDBACK YAML with all required fields."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "success",
        "output": "Task completed successfully with full protocol coverage",
        "metrics": {
            "quality": 0.95,
            "tokens": 1800,
            "cost": 0.04,
            "duration_seconds": 120,
        },
        "confidence": 0.95,
        "escalations": [],
    }


def _roundtrip(block: Dict) -> Dict:
    """Serialize a DELEGATE/HANDBACK dict to YAML and back, as it would be
    when passed as a sub-agent spawn prompt / returned as a spawn result."""
    return yaml.safe_load(yaml.dump(block))


# ============================================================================
# Test 1: DELEGATE round-trips through YAML with all fields intact
# ============================================================================

def test_delegate_roundtrips_through_yaml(sample_delegate: Dict):
    """
    A DELEGATE constructed by the spawning agent must survive YAML
    (de)serialization with every required and extension field intact.
    """
    loaded = _roundtrip(sample_delegate)

    assert loaded["handoff_type"] == "DELEGATE"
    assert loaded["task_id"] == sample_delegate["task_id"]
    assert loaded["agent"] == "engineer"
    assert loaded["model"] == "claude-haiku-4.5"
    assert loaded["effort"] == "high"
    assert loaded["scope"] == sample_delegate["scope"]
    assert loaded["plan"] == sample_delegate["plan"]
    assert loaded["success_criteria"] == sample_delegate["success_criteria"]
    assert loaded["context"] == sample_delegate["context"]
    assert loaded["estimated_tokens"] == 2000


# ============================================================================
# Test 2: HANDBACK round-trips through YAML with all fields intact
# ============================================================================

def test_handback_roundtrips_through_yaml(sample_delegate: Dict, sample_handback: Dict):
    """
    A HANDBACK returned as a spawn call's result must survive YAML
    (de)serialization with every required field intact, and its task_id
    must match the originating DELEGATE's.
    """
    loaded = _roundtrip(sample_handback)

    assert loaded["handoff_type"] == "HANDBACK"
    assert loaded["task_id"] == sample_delegate["task_id"]
    assert loaded["status"] == "success"
    assert "output" in loaded
    assert loaded["metrics"] == sample_handback["metrics"]


# ============================================================================
# Test 3: Failure HANDBACK preserves escalation metadata
# ============================================================================

def test_failure_handback_preserves_escalations(sample_delegate: Dict):
    """A HANDBACK with status=failure round-trips its escalation metadata."""
    failed_handback = {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "failure",
        "output": "Task failed with error",
        "metrics": {
            "quality": 0.0,
            "tokens": 500,
            "cost": 0.02,
            "duration_seconds": 30,
        },
        "confidence": 0.0,
        "escalations": ["Error in implementation"],
    }

    loaded = _roundtrip(failed_handback)

    assert loaded["status"] == "failure"
    assert len(loaded["escalations"]) > 0


# ============================================================================
# Test 4: Blocked HANDBACK preserves retry metadata
# ============================================================================

def test_blocked_handback_preserves_retry_metadata(sample_delegate: Dict):
    """A HANDBACK with status=blocked round-trips its retry-tracking fields."""
    blocked_handback = {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "blocked",
        "output": "Task blocked: resource unavailable",
        "metrics": {
            "quality": 0.5,
            "tokens": 1000,
            "cost": 0.03,
            "duration_seconds": 60,
        },
        "confidence": 0.5,
        "escalations": ["Resource unavailable - will retry"],
        "_retry_count": 1,
        "_last_blocked_reason": "resource unavailable",
    }

    loaded = _roundtrip(blocked_handback)

    assert loaded["status"] == "blocked"
    assert loaded["_retry_count"] == 1
    assert "_last_blocked_reason" in loaded


# ============================================================================
# Test 5: Escalate HANDBACK yields a well-formed follow-up DELEGATE
# ============================================================================

def test_escalate_handback_yields_new_delegate(sample_delegate: Dict):
    """
    A HANDBACK with status=escalate, when the spawning agent re-delegates at
    the higher tier, must produce a new DELEGATE that preserves the
    escalation chain (parent task_id and reason).
    """
    escalate_handback = {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "escalate",
        "output": "Escalating to senior engineer for complex analysis",
        "metrics": {
            "quality": 0.6,
            "tokens": 2000,
            "cost": 0.05,
            "duration_seconds": 180,
        },
        "confidence": 0.4,
        "escalations": ["Complexity exceeds engineer scope"],
    }
    assert _roundtrip(escalate_handback)["status"] == "escalate"

    # Spawning agent constructs the follow-up DELEGATE at the higher tier.
    new_delegate = dict(sample_delegate)
    new_delegate["agent"] = "senior-engineer"
    new_delegate["escalation_parent"] = sample_delegate["task_id"]
    new_delegate["escalation_reason"] = "Complexity exceeds engineer scope"

    loaded = _roundtrip(new_delegate)

    assert loaded["agent"] == "senior-engineer"
    assert loaded["escalation_parent"] == sample_delegate["task_id"]
    assert loaded["escalation_reason"] == "Complexity exceeds engineer scope"


# ============================================================================
# Integration: Full DELEGATE -> HANDBACK Protocol Cycle
# ============================================================================

def test_full_protocol_cycle(sample_delegate: Dict, sample_handback: Dict):
    """
    Integration test: a DELEGATE is constructed, passed directly as a spawn
    prompt (simulated here as a YAML round-trip), and the target agent
    returns a HANDBACK synchronously as that spawn's result (likewise
    round-tripped). Confirms the full schema survives both hops.
    """
    delegate_out = _roundtrip(sample_delegate)
    assert delegate_out["task_id"] == sample_delegate["task_id"]
    assert delegate_out["handoff_type"] == "DELEGATE"

    # Target agent executes and returns a HANDBACK for the same task_id.
    handback_out = _roundtrip(sample_handback)
    assert handback_out["task_id"] == delegate_out["task_id"]
    assert handback_out["handoff_type"] == "HANDBACK"
    assert handback_out["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
