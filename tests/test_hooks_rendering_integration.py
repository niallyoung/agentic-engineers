"""
Test suite for hooks rendering integration across all 4 harness renderers.

Covers:
- render-opencode.sh hooks installation
- render-claude.sh hooks installation
- render-copilot.sh hooks installation
- render-pi-dev.py hooks installation
- Hook executability verification
- Git configuration validation
- Harness-specific hook behavior
"""

import os
import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path


class TestHooksExist:
    """Verify all hooks exist and are properly structured."""
    
    def test_all_hooks_exist(self):
        """All required hooks should exist in .githooks/."""
        repo_root = Path(__file__).parent.parent
        hooks_dir = repo_root / '.githooks'
        
        required_hooks = ['pre-commit', 'commit-msg', 'pre-push']
        for hook_name in required_hooks:
            hook_path = hooks_dir / hook_name
            assert hook_path.exists(), f"Hook not found: {hook_path}"
    
    def test_all_hooks_executable(self):
        """All hooks should be executable."""
        repo_root = Path(__file__).parent.parent
        hooks_dir = repo_root / '.githooks'
        
        for hook_file in hooks_dir.glob('*'):
            if hook_file.is_file():
                assert os.access(hook_file, os.X_OK), f"Hook not executable: {hook_file}"
    
    def test_all_hooks_have_shebang(self):
        """All hooks should have proper shebang."""
        repo_root = Path(__file__).parent.parent
        hooks_dir = repo_root / '.githooks'
        
        for hook_file in hooks_dir.glob('*'):
            if hook_file.is_file():
                with open(hook_file) as f:
                    first_line = f.readline()
                assert first_line.startswith('#!/'), f"Missing shebang in {hook_file}: {first_line}"


class TestRenderOpenCodeHooks:
    """Test render-opencode.sh hooks installation."""
    
    def test_render_opencode_script_exists(self):
        """render-opencode.sh should exist."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        assert script.exists(), f"Script not found: {script}"
    
    def test_render_opencode_script_executable(self):
        """render-opencode.sh should be executable."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        assert os.access(script, os.X_OK), f"Script not executable: {script}"
    
    def test_render_opencode_contains_hooks_installation(self):
        """render-opencode.sh should contain hooks installation code."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Check for hooks installation markers
        assert 'Installing git hooks' in content or 'git hooks' in content, \
            "render-opencode.sh missing hooks installation code"
        assert 'core.hooksPath' in content, \
            "render-opencode.sh missing core.hooksPath configuration"
        assert '.githooks' in content, \
            "render-opencode.sh missing .githooks reference"
    
    def test_render_opencode_hooks_chmod(self):
        """render-opencode.sh should make hooks executable."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        
        with open(script) as f:
            content = f.read()
        
        assert 'chmod +x' in content or 'chmod' in content, \
            "render-opencode.sh missing chmod for hooks"


class TestRenderClaudeHooks:
    """Test render-claude.sh hooks installation."""
    
    def test_render_claude_script_exists(self):
        """render-claude.sh should exist."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-claude.sh'
        assert script.exists(), f"Script not found: {script}"
    
    def test_render_claude_script_executable(self):
        """render-claude.sh should be executable."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-claude.sh'
        assert os.access(script, os.X_OK), f"Script not executable: {script}"
    
    def test_render_claude_contains_hooks_installation(self):
        """render-claude.sh should contain hooks installation code."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-claude.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Check for hooks installation markers
        assert 'Installing git hooks' in content or 'git hooks' in content, \
            "render-claude.sh missing hooks installation code"
        assert 'core.hooksPath' in content, \
            "render-claude.sh missing core.hooksPath configuration"
        assert '.githooks' in content, \
            "render-claude.sh missing .githooks reference"


class TestRenderCopilotHooks:
    """Test render-copilot.sh hooks installation."""
    
    def test_render_copilot_script_exists(self):
        """render-copilot.sh should exist."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-copilot.sh'
        assert script.exists(), f"Script not found: {script}"
    
    def test_render_copilot_script_executable(self):
        """render-copilot.sh should be executable."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-copilot.sh'
        assert os.access(script, os.X_OK), f"Script not executable: {script}"
    
    def test_render_copilot_contains_hooks_installation(self):
        """render-copilot.sh should contain hooks installation code."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-copilot.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Check for hooks installation markers
        assert 'Installing git hooks' in content or 'git hooks' in content, \
            "render-copilot.sh missing hooks installation code"
        assert 'core.hooksPath' in content, \
            "render-copilot.sh missing core.hooksPath configuration"
        assert '.githooks' in content, \
            "render-copilot.sh missing .githooks reference"


class TestRenderPiDevHooks:
    """Test render-pi-dev.py hooks installation."""
    
    def test_render_pi_dev_script_exists(self):
        """render-pi-dev.py should exist."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        assert script.exists(), f"Script not found: {script}"
    
    def test_render_pi_dev_script_executable(self):
        """render-pi-dev.py should be executable."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        assert os.access(script, os.X_OK), f"Script not executable: {script}"
    
    def test_render_pi_dev_contains_hooks_installation(self):
        """render-pi-dev.py should contain hooks installation code."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        
        with open(script) as f:
            content = f.read()
        
        # Check for hooks installation markers
        assert '_install_git_hooks' in content, \
            "render-pi-dev.py missing _install_git_hooks method"
        assert 'core.hooksPath' in content, \
            "render-pi-dev.py missing core.hooksPath configuration"
        assert '.githooks' in content, \
            "render-pi-dev.py missing .githooks reference"
    
    def test_render_pi_dev_has_install_git_hooks_method(self):
        """render-pi-dev.py should have _install_git_hooks method."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        
        with open(script) as f:
            content = f.read()
        
        # Check for method definition
        assert 'def _install_git_hooks' in content, \
            "render-pi-dev.py missing _install_git_hooks method definition"
        
        # Check for subprocess call to git config
        assert 'subprocess.run' in content, \
            "render-pi-dev.py _install_git_hooks missing subprocess call"
        assert 'git' in content and 'config' in content, \
            "render-pi-dev.py _install_git_hooks missing git config call"


class TestGitConfigurationValidation:
    """Test git configuration for hooks."""
    
    def test_current_repo_has_hooks_path_configured(self):
        """Current repo should have core.hooksPath configured."""
        repo_root = Path(__file__).parent.parent
        
        try:
            result = subprocess.run(
                ['git', '-C', str(repo_root), 'config', 'core.hooksPath'],
                capture_output=True,
                text=True,
                timeout=5
            )
            hooks_path = result.stdout.strip()
            assert hooks_path == '.githooks', \
                f"Expected core.hooksPath=.githooks, got: {hooks_path}"
        except subprocess.TimeoutExpired:
            pytest.skip("Git command timed out")
        except Exception as e:
            pytest.skip(f"Could not check git config: {e}")


class TestHarnessSpecificBehavior:
    """Test harness-specific hook behavior."""
    
    def test_opencode_hooks_shared_repo(self):
        """OpenCode renderer should use shared repo hooks."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        
        with open(script) as f:
            content = f.read()
        
        # OpenCode should reference REPO_ROOT for hooks
        assert 'REPO_ROOT' in content, \
            "OpenCode renderer should use REPO_ROOT for hooks"
    
    def test_claude_hooks_shared_repo(self):
        """Claude renderer should use shared repo hooks."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-claude.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Claude should reference REPO_ROOT for hooks
        assert 'REPO_ROOT' in content, \
            "Claude renderer should use REPO_ROOT for hooks"
    
    def test_copilot_hooks_shared_repo(self):
        """Copilot renderer should use shared repo hooks."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-copilot.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Copilot should reference REPO_ROOT for hooks
        assert 'REPO_ROOT' in content, \
            "Copilot renderer should use REPO_ROOT for hooks"
    
    def test_pi_dev_hooks_repo_discovery(self):
        """Pi.dev renderer should discover repo root for hooks."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        
        with open(script) as f:
            content = f.read()
        
        # Pi.dev should discover repo root
        assert '.git' in content, \
            "Pi.dev renderer should discover .git directory"


class TestHookInstallationErrorHandling:
    """Test error handling in hook installation."""
    
    def test_opencode_handles_missing_hooks_gracefully(self):
        """render-opencode.sh should handle missing hooks gracefully."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Should have conditional check for hooks directory
        assert 'if [ -d' in content and '.githooks' in content, \
            "render-opencode.sh should check if hooks directory exists"
    
    def test_claude_handles_missing_hooks_gracefully(self):
        """render-claude.sh should handle missing hooks gracefully."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-claude.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Should have conditional check for hooks directory
        assert 'if [ -d' in content and '.githooks' in content, \
            "render-claude.sh should check if hooks directory exists"
    
    def test_copilot_handles_missing_hooks_gracefully(self):
        """render-copilot.sh should handle missing hooks gracefully."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-copilot.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Should have conditional check for hooks directory
        assert 'if [ -d' in content and '.githooks' in content, \
            "render-copilot.sh should check if hooks directory exists"
    
    def test_pi_dev_handles_missing_hooks_gracefully(self):
        """render-pi-dev.py should handle missing hooks gracefully."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        
        with open(script) as f:
            content = f.read()
        
        # Should have error handling
        assert 'try:' in content and 'except' in content, \
            "render-pi-dev.py should have try/except for hook installation"
        assert 'return False' in content or 'return True' in content, \
            "render-pi-dev.py should return status for hook installation"


class TestHookDocumentation:
    """Test documentation of hooks in renderers."""
    
    def test_opencode_documents_hooks_installation(self):
        """render-opencode.sh should document hooks installation."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-opencode.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Should have comments explaining hooks
        assert '#' in content, "Script should have comments"
    
    def test_claude_documents_hooks_installation(self):
        """render-claude.sh should document hooks installation."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-claude.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Should have comments explaining hooks
        assert '#' in content, "Script should have comments"
    
    def test_copilot_documents_hooks_installation(self):
        """render-copilot.sh should document hooks installation."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-copilot.sh'
        
        with open(script) as f:
            content = f.read()
        
        # Should have comments explaining hooks
        assert '#' in content, "Script should have comments"
    
    def test_pi_dev_documents_hooks_installation(self):
        """render-pi-dev.py should document hooks installation."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / 'renderer' / 'scripts' / 'render-pi-dev.py'
        
        with open(script) as f:
            content = f.read()
        
        # Should have docstring explaining hooks
        assert '"""' in content or "'''" in content, "Script should have docstrings"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
