"""
TDD Test Suite for Agent Definition Verifier (FIX #3)

Tests verify:
1. SHA256 generated correctly (64-char hex)
2. SHA matches for unmodified AGENTS.md; changes when modified
3. DELEGATE with matching SHA accepted; mismatched rejected
4. Model downgrade attacks blocked
5. Git hook validates model_verification_sha
"""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import json

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Import the verifier module
from agent_definition_verifier import (
    generate_agents_sha256,
    verify_sha_matches,
    validate_agent_in_roster,
    load_agents_manifest,
)


class TestAgentDefinitionVerifier(unittest.TestCase):
    """Test suite for agent definition verification"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.agents_file = Path(self.temp_dir) / "test_agents.md"
        self.sha_file = Path(self.temp_dir) / ".agents_verification_sha"
        
        # Sample AGENTS.md content with agent roster
        self.sample_agents_content = """# Agent Roster

| # | Role | Model | Thinking | Cost/Task | Purpose |
|---|------|-------|----------|-----------|---------|
| 1 | Orchestrator | claude-haiku-4.5 | ❌ | $0.03 | Entry point |
| 2 | Engineer | claude-haiku-4.5 | ❌ | $0.05 | Executes tasks |
| 3 | Model Engineer | claude-sonnet-4.6 | ✅ | $0.09 | Analyses metrics |
| 4 | Quality Engineer | claude-sonnet-4.6 | ✅ | $0.09 | Validation |
| 5 | Lead Engineer | claude-sonnet-4.6 | ✅ | $0.09 | Code review |
| 6 | Senior Engineer | claude-sonnet-4.6 | ✅ | $0.09 | Planning |
| 7 | Principal Engineer | claude-opus-4-6 | ✅ | $0.15 | Architecture |
| 8 | Security Engineer | claude-opus-4.7 | ✅ | $0.15 | Security |
"""
        
        # Write sample agents file
        self.agents_file.write_text(self.sample_agents_content)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # ─────────────────────────────────────────────────────────────────────────────
    # AC1: SHA Generated Correctly (64-char hex SHA256)
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_ac1_sha_generated_correctly_format(self):
        """AC1: Verify SHA generated as 64-character hex (SHA256 format)"""
        sha = generate_agents_sha256(str(self.agents_file))
        
        # Must be exactly 64 hex characters
        self.assertEqual(len(sha), 64, f"SHA must be 64 chars, got {len(sha)}")
        
        # Must be valid hex (can convert to int with base 16)
        try:
            int(sha, 16)
        except ValueError:
            self.fail(f"SHA is not valid hex: {sha}")
        
        # Verify it's lowercase
        self.assertEqual(sha, sha.lower(), "SHA must be lowercase hex")

    def test_ac1_sha_is_sha256_hash(self):
        """AC1: Verify SHA matches actual SHA256 of file content"""
        content = self.agents_file.read_text()
        expected_sha = hashlib.sha256(content.encode()).hexdigest()
        actual_sha = generate_agents_sha256(str(self.agents_file))
        
        self.assertEqual(actual_sha, expected_sha, 
                        "Generated SHA must match SHA256 of file content")

    def test_ac1_sha_deterministic(self):
        """AC1: Verify SHA generation is deterministic (same file → same SHA)"""
        sha1 = generate_agents_sha256(str(self.agents_file))
        sha2 = generate_agents_sha256(str(self.agents_file))
        
        self.assertEqual(sha1, sha2, 
                        "SHA must be deterministic — same file must produce same hash")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC2: SHA Matches for Unmodified; Changes When Modified
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_ac2_sha_matches_unmodified(self):
        """AC2: SHA remains unchanged for unmodified AGENTS.md"""
        original_sha = generate_agents_sha256(str(self.agents_file))
        
        # Read and re-write same content (simulating "unmodified")
        content = self.agents_file.read_text()
        self.agents_file.write_text(content)
        
        new_sha = generate_agents_sha256(str(self.agents_file))
        
        self.assertEqual(original_sha, new_sha, 
                        "Unmodified file must have same SHA")

    def test_ac2_sha_changes_on_model_modification(self):
        """AC2: SHA changes when agent model is modified (e.g., downgrade attack)"""
        original_sha = generate_agents_sha256(str(self.agents_file))
        
        # Simulate model downgrade: Security Engineer Opus-4.7 → Sonnet-4.6
        modified_content = self.sample_agents_content.replace(
            "claude-opus-4.7",  # Original Security Engineer model
            "claude-sonnet-4.6"  # Downgraded model
        )
        self.agents_file.write_text(modified_content)
        
        new_sha = generate_agents_sha256(str(self.agents_file))
        
        self.assertNotEqual(original_sha, new_sha, 
                           "SHA must change when agent model is modified")

    def test_ac2_sha_changes_on_any_modification(self):
        """AC2: SHA changes on any AGENTS.md modification (not just models)"""
        original_sha = generate_agents_sha256(str(self.agents_file))
        
        # Modify any content (e.g., cost)
        modified_content = self.sample_agents_content.replace(
            "| $0.03 | Entry point |",
            "| $0.04 | Entry point (modified) |"
        )
        self.agents_file.write_text(modified_content)
        
        new_sha = generate_agents_sha256(str(self.agents_file))
        
        self.assertNotEqual(original_sha, new_sha, 
                           "SHA must change for any file modification")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC3: DELEGATE with Matching SHA Accepted; Mismatched Rejected
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_ac3_matching_sha_accepted(self):
        """AC3: DELEGATE with matching model_verification_sha is accepted"""
        agents_sha = generate_agents_sha256(str(self.agents_file))
        
        delegate = {
            "task_id": "TASK-2026-05-30-test-1",
            "role": "security-engineer",
            "model": "claude-opus-4.7",
            "model_verification_sha": agents_sha
        }
        
        result = verify_sha_matches(delegate, agents_sha)
        
        self.assertTrue(result, 
                       "DELEGATE with matching SHA must be accepted")

    def test_ac3_mismatched_sha_rejected(self):
        """AC3: DELEGATE with mismatched model_verification_sha is rejected"""
        agents_sha = generate_agents_sha256(str(self.agents_file))
        wrong_sha = "0" * 64  # Deliberately wrong SHA
        
        delegate = {
            "task_id": "TASK-2026-05-30-test-2",
            "role": "security-engineer",
            "model": "claude-opus-4.7",
            "model_verification_sha": wrong_sha
        }
        
        result = verify_sha_matches(delegate, agents_sha)
        
        self.assertFalse(result, 
                        "DELEGATE with mismatched SHA must be rejected")

    def test_ac3_missing_sha_rejected(self):
        """AC3: DELEGATE without model_verification_sha field is rejected"""
        agents_sha = generate_agents_sha256(str(self.agents_file))
        
        delegate = {
            "task_id": "TASK-2026-05-30-test-3",
            "role": "security-engineer",
            "model": "claude-opus-4.7",
            # Missing model_verification_sha
        }
        
        result = verify_sha_matches(delegate, agents_sha)
        
        self.assertFalse(result, 
                        "DELEGATE without SHA field must be rejected")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC4: Model Downgrade Attacks Blocked
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_ac4_model_downgrade_blocked_security_engineer(self):
        """AC4: Model downgrade attack blocked (Security Engineer Opus-4.7 → Sonnet-4.6)"""
        # Original: Security Engineer = claude-opus-4.7
        agents_sha = generate_agents_sha256(str(self.agents_file))
        
        # Attacker tries to claim Sonnet-4.6 is valid for Security Engineer
        delegate = {
            "task_id": "TASK-2026-05-30-attack-1",
            "role": "security-engineer",
            "model": "claude-sonnet-4.6",  # Wrong! Should be Opus-4.7
            "model_verification_sha": agents_sha  # Using unmodified roster
        }
        
        # Should reject because Sonnet-4.6 ≠ Opus-4.7 in valid roster
        result = validate_agent_in_roster(
            role="security-engineer",
            model="claude-sonnet-4.6",
            agents_file=str(self.agents_file)
        )
        
        self.assertFalse(result, 
                        "Model downgrade attack must be blocked — Sonnet not valid for Security Engineer")

    def test_ac4_model_not_in_roster_blocked(self):
        """AC4: Model not in AGENTS.md roster is blocked"""
        delegate = {
            "task_id": "TASK-2026-05-30-attack-2",
            "role": "security-engineer",
            "model": "claude-unknown-9.9",  # Invalid model
            "model_verification_sha": generate_agents_sha256(str(self.agents_file))
        }
        
        result = validate_agent_in_roster(
            role="security-engineer",
            model="claude-unknown-9.9",
            agents_file=str(self.agents_file)
        )
        
        self.assertFalse(result, 
                        "Invalid model not in roster must be blocked")

    def test_ac4_valid_model_accepted(self):
        """AC4: Valid model in AGENTS.md roster is accepted"""
        result = validate_agent_in_roster(
            role="security-engineer",
            model="claude-opus-4.7",
            agents_file=str(self.agents_file)
        )
        
        self.assertTrue(result, 
                       "Valid model in roster must be accepted")

    # ─────────────────────────────────────────────────────────────────────────────
    # AC5: Git Hook Validates model_verification_sha
    # (This test verifies the logic; actual hook tested separately)
    # ─────────────────────────────────────────────────────────────────────────────
    
    def test_ac5_load_agents_manifest_success(self):
        """AC5: Load agents manifest successfully extracts roles and models"""
        roster = load_agents_manifest(str(self.agents_file))
        
        self.assertIsNotNone(roster, "Must load agents manifest successfully")
        self.assertIn("security_engineer", roster, "Must extract Security Engineer role")
        self.assertEqual(roster["security_engineer"], "claude-opus-4.7", 
                        "Must extract correct model for Security Engineer")

    def test_ac5_manifest_contains_all_required_roles(self):
        """AC5: Agent manifest contains all required roles from AGENTS.md"""
        roster = load_agents_manifest(str(self.agents_file))
        
        required_roles = [
            "orchestrator",
            "engineer",
            "lead_engineer",
            "principal_engineer",
            "security_engineer",
            "quality_engineer",
            "model_engineer",
            "senior_engineer"
        ]
        
        for role in required_roles:
            self.assertIn(role, roster, f"Roster must include {role}")


class TestAgentDefinitionVerifierEdgeCases(unittest.TestCase):
    """Edge case tests for robustness"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agents_file = Path(self.temp_dir) / "test_agents.md"

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_empty_agents_file(self):
        """Test handling of empty agents file"""
        self.agents_file.write_text("")
        
        sha = generate_agents_sha256(str(self.agents_file))
        expected = hashlib.sha256(b"").hexdigest()
        
        self.assertEqual(sha, expected, 
                        "Must handle empty file correctly")

    def test_nonexistent_file_error(self):
        """Test error handling for nonexistent file"""
        with self.assertRaises(FileNotFoundError):
            generate_agents_sha256(str(Path(self.temp_dir) / "nonexistent.md"))

    def test_whitespace_changes_affect_sha(self):
        """Test that whitespace changes affect SHA (important for attack detection)"""
        content1 = "Role | Model\nsecurity | opus-4.7"
        content2 = "Role | Model\nsecurity | opus-4.7 "  # Extra space
        
        file1 = Path(self.temp_dir) / "file1.md"
        file2 = Path(self.temp_dir) / "file2.md"
        
        file1.write_text(content1)
        file2.write_text(content2)
        
        sha1 = generate_agents_sha256(str(file1))
        sha2 = generate_agents_sha256(str(file2))
        
        self.assertNotEqual(sha1, sha2, 
                           "Whitespace changes must affect SHA (attack detection)")


if __name__ == "__main__":
    unittest.main()
