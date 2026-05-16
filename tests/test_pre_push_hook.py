#!/usr/bin/env python3
"""
Test suite for .githooks/pre-push validation hook

Tests:
  1. Hook file exists and is executable
  2. Hook has correct shebang
  3. SKIP_HOOKS bypass works
  4. Agent YAML validation
  5. Documentation files exist
  6. SPEC.md structure
  7. AGENTS.md structure
  8. Workflow YAML validation
  9. DELEGATE/HANDBACK protocol compliance
  10. SPEC compliance (no external scripts)
  11. Test directory exists
  12. Hook output format
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple
import yaml


class PrePushHookTester:
    """Test harness for pre-push hook validation"""
    
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.hook_path = self.repo_root / ".githooks" / "pre-push"
        self.tests_passed = 0
        self.tests_failed = 0
        
    def run_hook(self, stdin_data: str = "", skip_hooks: bool = False) -> Tuple[int, str, str]:
        """Execute pre-push hook and return exit code, stdout, stderr"""
        env = os.environ.copy()
        if skip_hooks:
            env["SKIP_HOOKS"] = "1"
        
        # Skip pytest during hook testing to avoid timeout
        env["SKIP_PYTEST"] = "1"
        
        try:
            result = subprocess.run(
                [str(self.hook_path), "origin", "https://github.com/test/repo.git"],
                input=stdin_data,
                capture_output=True,
                text=True,
                env=env,
                cwd=str(self.repo_root),
                timeout=10
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "Hook execution timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def test_hook_executable(self):
        """Test 1: Hook file exists and is executable"""
        test_name = "Hook executable"
        try:
            assert self.hook_path.exists(), f"Hook not found at {self.hook_path}"
            assert os.access(self.hook_path, os.X_OK), "Hook is not executable"
            self.pass_test(test_name)
        except AssertionError as e:
            self.fail_test(test_name, str(e))
    
    def test_hook_shebang(self):
        """Test 2: Hook has correct shebang"""
        test_name = "Hook shebang"
        try:
            with open(self.hook_path, 'r') as f:
                first_line = f.readline().strip()
            assert first_line == "#!/usr/bin/env bash", f"Invalid shebang: {first_line}"
            self.pass_test(test_name)
        except Exception as e:
            self.fail_test(test_name, str(e))
    
    def test_skip_hooks_bypass(self):
        """Test 3: SKIP_HOOKS=1 bypasses all checks"""
        test_name = "SKIP_HOOKS bypass"
        try:
            exit_code, stdout, stderr = self.run_hook(skip_hooks=True)
            assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
            assert "SKIP_HOOKS=1" in stdout, "Expected bypass message in output"
            self.pass_test(test_name)
        except AssertionError as e:
            self.fail_test(test_name, str(e))
    
    def test_agent_yaml_validation(self):
        """Test 4: Agent YAML frontmatter validation"""
        test_name = "Agent YAML validation"
        try:
            agents_dir = self.repo_root / "src" / "agents"
            if agents_dir.exists():
                for agent_file in agents_dir.glob("*.md"):
                    if "README" in agent_file.name:
                        continue
                    
                    with open(agent_file, 'r') as f:
                        content = f.read()
                    
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            fm_text = parts[1].strip()
                            try:
                                yaml.safe_load(fm_text)
                            except yaml.YAMLError as e:
                                raise AssertionError(f"Invalid YAML in {agent_file}: {e}")
            
            self.pass_test(test_name)
        except Exception as e:
            self.fail_test(test_name, str(e))
    
    def test_documentation_files_exist(self):
        """Test 5: Required documentation files exist"""
        test_name = "Documentation files"
        try:
            required_docs = [
                self.repo_root / "docs" / "SPEC.md",
                self.repo_root / "docs" / "AGENTS.md",
                self.repo_root / "README.md"
            ]
            
            for doc_file in required_docs:
                assert doc_file.exists(), f"Missing required documentation: {doc_file}"
                assert doc_file.stat().st_size > 0, f"Empty documentation file: {doc_file}"
            
            self.pass_test(test_name)
        except AssertionError as e:
            self.fail_test(test_name, str(e))
    
    def test_spec_md_structure(self):
        """Test 6: SPEC.md has required structure"""
        test_name = "SPEC.md structure"
        try:
            spec_file = self.repo_root / "docs" / "SPEC.md"
            with open(spec_file, 'r') as f:
                content = f.read()
            
            required_fields = ["version:", "status:"]
            for field in required_fields:
                assert field in content, f"SPEC.md missing field: {field}"
            
            assert "# " in content, "SPEC.md missing top-level heading"
            
            self.pass_test(test_name)
        except Exception as e:
            self.fail_test(test_name, str(e))
    
    def test_agents_md_structure(self):
        """Test 7: AGENTS.md has required structure"""
        test_name = "AGENTS.md structure"
        try:
            agents_file = self.repo_root / "docs" / "AGENTS.md"
            with open(agents_file, 'r') as f:
                content = f.read()
            
            assert "# " in content, "AGENTS.md missing top-level heading"
            
            self.pass_test(test_name)
        except Exception as e:
            self.fail_test(test_name, str(e))
    
    def test_workflow_yaml_validation(self):
        """Test 8: GitHub Actions workflow files are valid YAML"""
        test_name = "Workflow YAML validation"
        try:
            workflows_dir = self.repo_root / ".github" / "workflows"
            if workflows_dir.exists():
                for workflow_file in workflows_dir.glob("*.{yml,yaml}"):
                    try:
                        with open(workflow_file, 'r') as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        raise AssertionError(f"Invalid YAML in workflow {workflow_file}: {e}")
                    
                    with open(workflow_file, 'r') as f:
                        content = f.read()
                    assert "name:" in content, f"Workflow {workflow_file} missing 'name' field"
                    assert "on:" in content, f"Workflow {workflow_file} missing 'on' trigger"
            
            self.pass_test(test_name)
        except Exception as e:
            self.fail_test(test_name, str(e))
    
    def test_delegate_handback_protocol(self):
        """Test 9: DELEGATE/HANDBACK files have valid structure"""
        test_name = "DELEGATE/HANDBACK protocol"
        try:
            delegates_dir = self.repo_root / "artifacts" / "delegates"
            if delegates_dir.exists():
                for delegate_file in delegates_dir.glob("*/*.yaml"):
                    try:
                        with open(delegate_file, 'r') as f:
                            data = yaml.safe_load(f)
                        
                        required_fields = ["handoff_type", "task_id", "role", "model"]
                        for field in required_fields:
                            assert field in data, f"DELEGATE missing field: {field}"
                        
                        assert data.get("handoff_type") == "DELEGATE", "Invalid handoff_type"
                    except yaml.YAMLError as e:
                        raise AssertionError(f"Invalid YAML in DELEGATE {delegate_file}: {e}")
            
            self.pass_test(test_name)
        except Exception as e:
            self.fail_test(test_name, str(e))
    
    def test_spec_compliance_no_external_scripts(self):
        """Test 10: No external scripts in orchestration/ (SPEC compliance)"""
        test_name = "SPEC compliance (no external scripts)"
        try:
            scripts_dir = self.repo_root / "orchestration" / "scripts"
            if scripts_dir.exists():
                py_files = list(scripts_dir.glob("*.py"))
                sh_files = list(scripts_dir.glob("*.sh"))
                assert len(py_files) == 0 and len(sh_files) == 0, \
                    f"Found external scripts in orchestration/scripts/"
            
            config_dir = self.repo_root / "orchestration" / "config"
            if config_dir.exists():
                cron_files = list(config_dir.glob("*.cron"))
                assert len(cron_files) == 0, "Found cron files in orchestration/config/"
            
            self.pass_test(test_name)
        except AssertionError as e:
            self.fail_test(test_name, str(e))
    
    def test_tests_directory_exists(self):
        """Test 11: tests/ directory exists"""
        test_name = "tests/ directory"
        try:
            tests_dir = self.repo_root / "tests"
            assert tests_dir.exists(), "tests/ directory not found"
            assert tests_dir.is_dir(), "tests/ is not a directory"
            
            test_files = list(tests_dir.glob("test_*.py"))
            assert len(test_files) > 0, "No test files found in tests/"
            
            self.pass_test(test_name)
        except AssertionError as e:
            self.fail_test(test_name, str(e))
    
    def test_hook_output_format(self):
        """Test 12: Hook produces properly formatted output"""
        test_name = "Hook output format"
        try:
            exit_code, stdout, stderr = self.run_hook()
            
            assert "pre-push" in stdout.lower() or "validation" in stdout.lower(), \
                "Hook output missing 'pre-push' or 'validation' reference"
            assert "✅" in stdout or "❌" in stdout or "⚠️" in stdout, \
                "Hook output missing status indicators"
            
            self.pass_test(test_name)
        except AssertionError as e:
            self.fail_test(test_name, str(e))
    
    def pass_test(self, test_name: str):
        """Record a passing test"""
        print(f"✅ {test_name}")
        self.tests_passed += 1
    
    def fail_test(self, test_name: str, reason: str):
        """Record a failing test"""
        print(f"❌ {test_name}: {reason}")
        self.tests_failed += 1
    
    def run_all_tests(self):
        """Execute all tests"""
        print("=" * 70)
        print("🧪 Pre-push Hook Test Suite")
        print("=" * 70)
        print()
        
        test_methods = [
            method for method in dir(self)
            if method.startswith('test_') and callable(getattr(self, method))
        ]
        
        for test_method in sorted(test_methods):
            getattr(self, test_method)()
        
        print()
        print("=" * 70)
        print("📊 Test Results")
        print("=" * 70)
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Total:  {self.tests_passed + self.tests_failed}")
        print()
        
        if self.tests_failed == 0:
            print("✅ All tests passed!")
            return 0
        else:
            print(f"❌ {self.tests_failed} test(s) failed")
            return 1


if __name__ == "__main__":
    tester = PrePushHookTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
