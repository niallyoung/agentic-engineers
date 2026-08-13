"""
test_opencode_hooks_integration.py — Test OpenCode integration with git hooks

Tests:
  1. opencode.jsonc configuration validity
  2. Git hooks path configuration
  3. OpenCode commands availability
  4. Command execution and output
  5. Integration between hooks and OpenCode workflow
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest


REPO_ROOT = Path(__file__).parent.parent
OPENCODE_CONFIG = REPO_ROOT / "opencode.jsonc"
GITHOOKS_DIR = REPO_ROOT / ".githooks"
OPENCODE_COMMANDS_DIR = REPO_ROOT / ".opencode" / "commands"


class TestOpenCodeConfiguration:
    """Test opencode.jsonc configuration"""

    def test_opencode_jsonc_exists(self):
        """Verify opencode.jsonc file exists"""
        assert OPENCODE_CONFIG.exists(), f"{OPENCODE_CONFIG} not found"

    def test_opencode_jsonc_valid_json(self):
        """Verify opencode.jsonc is valid JSON (with JSONC comments stripped)"""
        content = OPENCODE_CONFIG.read_text()
        
        # Strip JSONC comments
        import re
        # Remove // comments (but not in strings)
        lines = []
        for line in content.split('\n'):
            # Find comment start
            comment_idx = line.find('//')
            if comment_idx != -1:
                # Simple heuristic: if it's outside quotes, remove it
                before_comment = line[:comment_idx]
                # Count quotes before comment
                if before_comment.count('"') % 2 == 0:
                    line = before_comment
            lines.append(line)
        content = '\n'.join(lines)
        
        # Remove /* */ comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Should parse as valid JSON
        try:
            config = json.loads(content)
            assert isinstance(config, dict), "Config should be a JSON object"
        except json.JSONDecodeError as e:
            pytest.fail(f"opencode.jsonc is not valid JSON: {e}")

    def test_opencode_config_has_schema(self):
        """Verify config declares $schema"""
        content = OPENCODE_CONFIG.read_text()
        assert '"$schema"' in content, "Config should declare $schema"
        assert "opencode.ai/config.json" in content, "Schema should point to opencode.ai"

    def test_opencode_config_has_commands(self):
        """Verify config declares OpenCode commands"""
        content = OPENCODE_CONFIG.read_text()
        assert '"command"' in content, "Config should declare commands"
        assert '"sdlc-check"' in content, "Should have sdlc-check command"
        assert '"hooks-install"' in content, "Should have hooks-install command"

    def test_opencode_config_has_hooks_path_reference(self):
        """Verify config references .githooks"""
        content = OPENCODE_CONFIG.read_text()
        # The config should mention hooks in comments or description
        assert ".githooks" in content or "git hooks" in content.lower(), \
            "Config should reference .githooks or git hooks"


class TestGitHooksConfiguration:
    """Test git hooks setup"""

    def test_git_hooks_path_configured(self):
        """Verify git config core.hooksPath is set to .githooks"""
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "git config core.hooksPath should succeed"
        assert result.stdout.strip() == ".githooks", \
            f"core.hooksPath should be '.githooks', got '{result.stdout.strip()}'"

    def test_pre_commit_hook_exists_and_executable(self):
        """Verify .githooks/pre-commit exists and is executable"""
        hook = GITHOOKS_DIR / "pre-commit"
        assert hook.exists(), f"{hook} not found"
        assert hook.stat().st_mode & 0o111, f"{hook} is not executable"

    def test_commit_msg_hook_exists_and_executable(self):
        """Verify .githooks/commit-msg exists and is executable"""
        hook = GITHOOKS_DIR / "commit-msg"
        assert hook.exists(), f"{hook} not found"
        assert hook.stat().st_mode & 0o111, f"{hook} is not executable"

    def test_pre_push_hook_exists_and_executable(self):
        """Verify .githooks/pre-push exists and is executable"""
        hook = GITHOOKS_DIR / "pre-push"
        assert hook.exists(), f"{hook} not found"
        assert hook.stat().st_mode & 0o111, f"{hook} is not executable"

    def test_all_hooks_are_bash_scripts(self):
        """Verify all hooks are bash scripts"""
        for hook in GITHOOKS_DIR.glob("*"):
            # Skip markdown documentation files
            if hook.suffix == '.md':
                continue
            if hook.is_file() and hook.stat().st_mode & 0o111:
                content = hook.read_text()
                assert content.startswith("#!/usr/bin/env bash") or content.startswith("#!/bin/bash"), \
                    f"{hook.name} should be a bash script"


@pytest.mark.skip(reason="OpenCode commands deleted as part of file cleanup (2026-05-24). Commands were not actively used in current workflow.")
class TestOpenCodeCommands:
    """Test OpenCode command files (SKIPPED: commands deleted in cleanup)"""

    def test_sdlc_check_command_exists(self):
        """Verify /sdlc-check command file exists"""
        cmd = OPENCODE_COMMANDS_DIR / "sdlc-check.md"
        assert cmd.exists(), f"{cmd} not found"

    def test_hooks_install_command_exists(self):
        """Verify /hooks-install command file exists"""
        cmd = OPENCODE_COMMANDS_DIR / "hooks-install.md"
        assert cmd.exists(), f"{cmd} not found"

    def test_queue_status_command_exists(self):
        """Verify /queue-status command file exists"""
        cmd = OPENCODE_COMMANDS_DIR / "queue-status.md"
        assert cmd.exists(), f"{cmd} not found"

    def test_sdlc_check_has_frontmatter(self):
        """Verify sdlc-check command has valid frontmatter"""
        cmd = OPENCODE_COMMANDS_DIR / "sdlc-check.md"
        content = cmd.read_text()
        assert content.startswith("---"), "Command should start with YAML frontmatter"
        assert "description:" in content, "Command should have description"
        assert "agent:" in content, "Command should specify agent"

    def test_hooks_install_has_frontmatter(self):
        """Verify hooks-install command has valid frontmatter"""
        cmd = OPENCODE_COMMANDS_DIR / "hooks-install.md"
        content = cmd.read_text()
        assert content.startswith("---"), "Command should start with YAML frontmatter"
        assert "description:" in content, "Command should have description"

    def test_queue_status_has_frontmatter(self):
        """Verify queue-status command has valid frontmatter"""
        cmd = OPENCODE_COMMANDS_DIR / "queue-status.md"
        content = cmd.read_text()
        assert content.startswith("---"), "Command should start with YAML frontmatter"
        assert "description:" in content, "Command should have description"

    def test_commands_have_descriptions(self):
        """Verify all commands have meaningful descriptions"""
        for cmd_file in OPENCODE_COMMANDS_DIR.glob("*.md"):
            content = cmd_file.read_text()
            # Extract description from frontmatter
            lines = content.split("\n")
            for line in lines:
                if line.startswith("description:"):
                    desc = line.replace("description:", "").strip()
                    assert len(desc) > 10, f"{cmd_file.name} has too short description: {desc}"
                    break


class TestHooksIntegration:
    """Test integration between hooks and OpenCode"""

    def test_hooks_enforce_spec_compliance(self):
        """Verify pre-commit hook enforces SPEC compliance"""
        hook = GITHOOKS_DIR / "pre-commit"
        content = hook.read_text()
        
        # Check for SPEC enforcement
        assert "SPEC" in content or "spec" in content, \
            "pre-commit hook should enforce SPEC compliance"
        assert "orchestration/scripts" in content, \
            "pre-commit hook should check for external scripts"

    def test_commit_msg_hook_validates_format(self):
        """Verify commit-msg hook validates message format"""
        hook = GITHOOKS_DIR / "commit-msg"
        content = hook.read_text()
        
        # Check for message validation
        assert "conventional" in content.lower() or "format" in content.lower(), \
            "commit-msg hook should validate message format"

    def test_pre_push_hook_runs_tests(self):
        """Verify pre-push hook runs tests"""
        hook = GITHOOKS_DIR / "pre-push"
        content = hook.read_text()
        
        # Check for test execution
        assert "pytest" in content or "test" in content.lower(), \
            "pre-push hook should run tests"

    def test_hooks_have_bypass_mechanisms(self):
        """Verify executable hooks have documented bypass mechanisms"""
        for hook in GITHOOKS_DIR.glob("*"):
            # Skip documentation files - they don't need bypass mechanisms
            if hook.suffix in {".md", ".txt"}:
                continue
            
            if hook.is_file():
                content = hook.read_text()
                assert "SKIP_HOOKS" in content or "bypass" in content.lower(), \
                    f"{hook.name} should have bypass mechanism"


class TestOpenCodeIntegrationWorkflow:
    """Test the complete OpenCode + hooks integration workflow"""

    def test_hooks_path_in_config_matches_actual(self):
        """Verify hooks path in config matches actual configuration"""
        # Read opencode.jsonc
        config_content = OPENCODE_CONFIG.read_text()
        
        # Read git config
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        
        git_hooks_path = result.stdout.strip()
        
        # Both should reference .githooks
        assert ".githooks" in config_content or "git hooks" in config_content.lower(), \
            "opencode.jsonc should reference .githooks"
        assert git_hooks_path == ".githooks", \
            f"git config should have .githooks, got {git_hooks_path}"

    @pytest.mark.skip(reason="OpenCode commands deleted as part of file cleanup (2026-05-24)")
    def test_commands_reference_enforcement_hooks(self):
        """Verify OpenCode commands reference the enforcement hooks"""
        hooks_install = OPENCODE_COMMANDS_DIR / "hooks-install.md"
        content = hooks_install.read_text()
        
        # Should mention core.hooksPath
        assert "core.hooksPath" in content, \
            "hooks-install command should mention core.hooksPath"
        assert ".githooks" in content, \
            "hooks-install command should reference .githooks"

    @pytest.mark.skip(reason="OpenCode commands deleted as part of file cleanup (2026-05-24)")
    def test_sdlc_check_references_hooks(self):
        """Verify sdlc-check command validates hooks"""
        sdlc_check = OPENCODE_COMMANDS_DIR / "sdlc-check.md"
        content = sdlc_check.read_text()
        
        # Should mention git hooks validation
        assert "git" in content.lower() or "hook" in content.lower(), \
            "sdlc-check command should validate git hooks"

    @pytest.mark.skip(reason="OpenCode commands deleted as part of file cleanup (2026-05-24)")
    def test_queue_status_references_artifacts(self):
        """Verify queue-status command checks queue artifacts"""
        queue_status = OPENCODE_COMMANDS_DIR / "queue-status.md"
        content = queue_status.read_text()
        
        # Should mention artifacts/queue
        assert "artifacts/queue" in content or "queue" in content.lower(), \
            "queue-status command should reference queue artifacts"


class TestHooksBypassMechanisms:
    """Test hook bypass mechanisms for emergency scenarios"""

    def test_pre_commit_bypass_documented(self):
        """Verify pre-commit hook documents SKIP_HOOKS bypass"""
        hook = GITHOOKS_DIR / "pre-commit"
        content = hook.read_text()
        
        assert "SKIP_HOOKS=1" in content, \
            "pre-commit hook should document SKIP_HOOKS=1 bypass"
        assert "emergency" in content.lower(), \
            "Bypass should be documented as emergency-only"

    def test_commit_msg_bypass_documented(self):
        """Verify commit-msg hook documents bypass"""
        hook = GITHOOKS_DIR / "commit-msg"
        content = hook.read_text()
        
        # Should have bypass mechanism
        assert "SKIP" in content or "bypass" in content.lower(), \
            "commit-msg hook should have bypass mechanism"

    def test_pre_push_bypass_documented(self):
        """Verify pre-push hook documents bypass"""
        hook = GITHOOKS_DIR / "pre-push"
        content = hook.read_text()
        
        assert "SKIP_HOOKS=1" in content, \
            "pre-push hook should document SKIP_HOOKS=1 bypass"


# ══════════════════════════════════════════════════════════════════════════════
# Integration test markers
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestFullIntegration:
    """Full integration tests for OpenCode + hooks"""

    def test_opencode_config_loadable(self):
        """Verify opencode.jsonc can be loaded as valid config"""
        # This is a basic test that the config is well-formed
        content = OPENCODE_CONFIG.read_text()
        
        # Strip JSONC comments
        import re
        # Remove // comments (but not in strings)
        lines = []
        for line in content.split('\n'):
            # Find comment start
            comment_idx = line.find('//')
            if comment_idx != -1:
                # Simple heuristic: if it's outside quotes, remove it
                before_comment = line[:comment_idx]
                # Count quotes before comment
                if before_comment.count('"') % 2 == 0:
                    line = before_comment
            lines.append(line)
        content = '\n'.join(lines)
        
        # Remove /* */ comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Should parse
        config = json.loads(content)
        
        # Should have required fields
        assert "$schema" in config, "Config should have $schema"
        assert "command" in config, "Config should have commands"
        assert "permission" in config, "Config should have permissions"

    @pytest.mark.skip(reason="OpenCode commands deleted as part of file cleanup (2026-05-24)")
    def test_hooks_and_commands_work_together(self):
        """Verify hooks and OpenCode commands are coordinated"""
        # hooks-install command should match actual git config
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "git config should succeed"
        assert result.stdout.strip() == ".githooks", \
            "Hooks should be configured at .githooks"
        
        # All hook files should exist
        assert (GITHOOKS_DIR / "pre-commit").exists()
        assert (GITHOOKS_DIR / "commit-msg").exists()
        assert (GITHOOKS_DIR / "pre-push").exists()
        
        # All command files should exist
        assert (OPENCODE_COMMANDS_DIR / "hooks-install.md").exists()
        assert (OPENCODE_COMMANDS_DIR / "sdlc-check.md").exists()
        assert (OPENCODE_COMMANDS_DIR / "queue-status.md").exists()
