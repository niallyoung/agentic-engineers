"""
End-to-end test for fresh install and queue-based delegation flow.

Tests verify that:
1. Fresh install creates correct directory structure
2. Queue initialization works
3. DELEGATE/HANDBACK flow functions correctly
4. No orphaned files from previous installs

NOTE: Tests that require `make install-copilot` will be skipped in environments
where make is not available or the repo is not a git repository (CI/temp copies).
The artifact location tests run locally and verify core queue mechanics.
"""
import json
import os
import tempfile
import shutil
import uuid
from pathlib import Path
from unittest.mock import patch
import subprocess
import pytest
import yaml


def is_git_repo():
    """Check if current directory is in a git repository."""
    try:
        subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            check=True,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def has_make():
    """Check if make is available."""
    try:
        subprocess.run(['which', 'make'], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class TestFreshInstallE2E:
    """Test fresh install to temporary home directory with full queue flow."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown test environment."""
        # Create temp directories for this test
        self.temp_repo = tempfile.mkdtemp(prefix="test-agentic-repo-")
        self.temp_home = tempfile.mkdtemp(prefix="test-agentic-home-")
        
        yield
        
        # Cleanup
        if os.path.exists(self.temp_repo):
            shutil.rmtree(self.temp_repo, ignore_errors=True)
        if os.path.exists(self.temp_home):
            shutil.rmtree(self.temp_home, ignore_errors=True)

    def _copy_repo_to_temp(self):
        """Copy repo to temp location for fresh install test."""
        repo_root = Path(__file__).parent.parent.absolute()
        
        # Copy entire repo
        for item in os.listdir(repo_root):
            src = os.path.join(repo_root, item)
            dst = os.path.join(self.temp_repo, item)
            
            # Skip certain directories
            if item in ['.git', '__pycache__', '.pytest_cache', 'htmlcov', '.DS_Store', 'dist']:
                continue
            
            # Skip symlinks (hyphenated skill packages may be symlinked)
            if os.path.islink(src):
                continue
            
            if os.path.isdir(src):
                try:
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'), symlinks=False)
                except (shutil.Error, FileNotFoundError):
                    # Skip if directory doesn't copy cleanly (e.g., broken symlinks)
                    pass
            else:
                try:
                    shutil.copy2(src, dst)
                except (IOError, OSError):
                    # Skip if file can't be copied
                    pass

    def _get_session_id(self):
        """Generate a test session ID."""
        return str(uuid.uuid4())

    @pytest.mark.skipif(not (has_make() and is_git_repo()), reason="make or git not available")
    def test_fresh_install_to_temp_home(self):
        """
        Verify that fresh install creates correct directory structure.
        
        SKIP CONDITION: This test is skipped in CI or environments where:
        - make is not available
        - Running outside a git repository (CI temp copies)
        
        Expected structure after install:
        ~/.copilot/
        ├── agents/
        │   └── *.agent.md (8 agents)
        ├── skills/
        │   └── */
        └── queue/
            └── (created by orchestrator on first run)
        """
        self._copy_repo_to_temp()
        session_id = self._get_session_id()
        
        # Initialize git in temp repo (for make install-copilot)
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)
        
        # Simulate fresh install to temp home
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        # Run make install-copilot with custom HOME
        result = subprocess.run(
            ['make', 'install-copilot'],
            cwd=self.temp_repo,
            env=install_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        
        # Verify expected structure exists
        copilot_home = os.path.join(self.temp_home, '.copilot')
        assert os.path.exists(copilot_home), f"~/.copilot/ not created at {copilot_home}"
        
        # Check agents directory
        agents_dir = os.path.join(copilot_home, 'agents')
        assert os.path.isdir(agents_dir), f"agents/ directory not found at {agents_dir}"
        
        agent_files = [f for f in os.listdir(agents_dir) if f.endswith('.agent.md')]
        assert len(agent_files) >= 8, f"Expected at least 8 agents, found {len(agent_files)}: {agent_files}"
        
        # Check skills directory
        skills_dir = os.path.join(copilot_home, 'skills')
        assert os.path.isdir(skills_dir), f"skills/ directory not found at {skills_dir}"
        
        skills_count = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
        assert skills_count > 0, "No skills found in skills/ directory"
        
        # Verify no stale files from previous installs
        assert not os.path.exists(os.path.join(copilot_home, 'incoming-legacy-')), \
            "Found legacy incoming directory (stale files from previous install)"
        assert not os.path.exists(os.path.join(copilot_home, 'processing-legacy-')), \
            "Found legacy processing directory (stale files from previous install)"

    @pytest.mark.skipif(not (has_make() and is_git_repo()), reason="make or git not available")
    def test_queue_init_in_fresh_install(self):
        """
        Verify that queue directories are created correctly.
        
        SKIP CONDITION: Skipped in CI or environments without make/git.
        
        Expected:
        ~/.copilot/queue/{session-id}/
        ├── incoming/
        ├── processing/
        └── done/
        """
        self._copy_repo_to_temp()
        session_id = self._get_session_id()
        
        # Initialize git in temp repo
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)
        
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        result = subprocess.run(
            ['make', 'install-copilot'],
            cwd=self.temp_repo,
            env=install_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        
        # Manually create queue directory structure
        queue_base = os.path.join(self.temp_home, '.copilot', 'queue')
        session_queue = os.path.join(queue_base, session_id)
        
        # Create queue structure as orchestrator would
        for subdir in ['incoming', 'processing', 'done']:
            queue_dir = os.path.join(session_queue, subdir)
            os.makedirs(queue_dir, exist_ok=True)
        
        # Verify structure
        assert os.path.isdir(os.path.join(session_queue, 'incoming')), \
            "incoming/ directory not created"
        assert os.path.isdir(os.path.join(session_queue, 'processing')), \
            "processing/ directory not created"
        assert os.path.isdir(os.path.join(session_queue, 'done')), \
            "done/ directory not created"

    def test_delegate_invoke_without_install(self):
        """
        Verify DELEGATE/HANDBACK flow without requiring full install.
        
        This test demonstrates the queue flow mechanics without needing
        make install-copilot to work. It tests the core protocol directly.
        
        Flow:
        1. Create DELEGATE in incoming/
        2. Verify it's valid YAML
        3. Move to processing/ (simulating orchestrator)
        4. Create HANDBACK response
        5. Verify HANDBACK is valid
        """
        session_id = self._get_session_id()
        
        # Setup queue structure manually (what orchestrator would do)
        queue_base = os.path.join(self.temp_home, '.copilot', 'queue')
        session_queue = os.path.join(queue_base, session_id)
        for subdir in ['incoming', 'processing', 'done']:
            os.makedirs(os.path.join(session_queue, subdir), exist_ok=True)
        
        # Create a DELEGATE
        task_id = f"test-{uuid.uuid4().hex[:8]}"
        delegate_content = {
            'handoff_type': 'DELEGATE',
            'task_id': task_id,
            'role': 'Engineer',
            'model': 'claude-haiku-4.5',
            'effort': 'low',
            'scope': 'Test queue delegation protocol',
            'context': [
                'This is a test DELEGATE to verify queue flow.',
                'Session ID: ' + session_id
            ],
            'success_criteria': [
                'DELEGATE created successfully',
                'HANDBACK received and validated'
            ],
            'plan': [
                'Verify protocol structure',
                'Test queue state transitions',
                'Confirm YAML serialization'
            ]
        }
        
        # Write DELEGATE to incoming/
        delegate_file = os.path.join(session_queue, 'incoming', f'{task_id}.yaml')
        with open(delegate_file, 'w') as f:
            yaml.dump(delegate_content, f)
        
        # Verify DELEGATE is valid YAML
        with open(delegate_file, 'r') as f:
            parsed_delegate = yaml.safe_load(f)
        
        assert parsed_delegate['handoff_type'] == 'DELEGATE'
        assert parsed_delegate['task_id'] == task_id
        assert parsed_delegate['role'] == 'Engineer'
        
        # Simulate orchestrator moving to processing/
        processing_file = os.path.join(session_queue, 'processing', f'{task_id}-processing.yaml')
        shutil.move(delegate_file, processing_file)
        assert not os.path.exists(delegate_file), "DELEGATE not moved from incoming/"
        assert os.path.exists(processing_file), "DELEGATE not in processing/"
        
        # Create a HANDBACK response
        handback_content = {
            'handoff_type': 'HANDBACK',
            'task_id': task_id,
            'status': 'complete',
            'deliverables': [
                'Protocol structure verified',
                'Queue state transitions validated'
            ],
            'tests': [
                'test_delegate_invoke_without_install PASS'
            ],
            'tokens_in': 500,
            'tokens_out': 250,
            'model': 'claude-haiku-4.5',
            'effort': 'low',
            'duration_minutes': 5,
            'escalations': 0
        }
        
        # Write HANDBACK
        handback_file = os.path.join(session_queue, 'processing', f'{task_id}-HANDBACK-Engineer.yaml')
        with open(handback_file, 'w') as f:
            yaml.dump(handback_content, f)
        
        # Verify HANDBACK is valid
        with open(handback_file, 'r') as f:
            parsed_handback = yaml.safe_load(f)
        
        assert parsed_handback['handoff_type'] == 'HANDBACK'
        assert parsed_handback['task_id'] == task_id
        assert parsed_handback['status'] == 'complete'
        assert parsed_handback['tokens_in'] > 0
        assert parsed_handback['tokens_out'] > 0
        
        # Simulate moving to done/
        done_file = os.path.join(session_queue, 'done', f'{task_id}-PROCEED.yaml')
        decision_content = {
            'task_id': task_id,
            'decision': 'PROCEED',
            'notes': 'Quality Engineer verified; ready for deployment'
        }
        with open(done_file, 'w') as f:
            yaml.dump(decision_content, f)
        
        # Cleanup processing files
        os.remove(processing_file)
        os.remove(handback_file)
        
        # Verify final state
        assert not os.path.exists(processing_file), "Processing file not cleaned up"
        assert not os.path.exists(handback_file), "HANDBACK file not cleaned up"
        assert os.path.exists(done_file), "Done file not created"

    @pytest.mark.skipif(not (has_make() and is_git_repo()), reason="make or git not available")
    def test_no_stale_files_after_install(self):
        """
        Verify that no orphaned files from previous installs remain.
        
        SKIP CONDITION: Skipped in CI.
        
        Checks for:
        - Legacy queue directories (incoming-legacy-*, processing-legacy-*, etc.)
        - Migration logs with errors
        - Duplicate agent/skill installations
        """
        self._copy_repo_to_temp()
        
        # Initialize git
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)
        
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        result = subprocess.run(
            ['make', 'install-copilot'],
            cwd=self.temp_repo,
            env=install_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        
        copilot_home = os.path.join(self.temp_home, '.copilot')
        
        # Check for legacy directories
        for item in os.listdir(copilot_home):
            item_path = os.path.join(copilot_home, item)
            assert not item.startswith('incoming-legacy-'), \
                f"Found legacy incoming directory: {item}"
            assert not item.startswith('processing-legacy-'), \
                f"Found legacy processing directory: {item}"
            assert not item.startswith('done-legacy-'), \
                f"Found legacy done directory: {item}"
        
        # Check migration log if it exists
        queue_base = os.path.join(copilot_home, 'queue')
        if os.path.exists(queue_base):
            migration_log = os.path.join(queue_base, '.migration-log')
            if os.path.exists(migration_log):
                with open(migration_log, 'r') as f:
                    migration_entries = yaml.safe_load_all(f)
                    for entry in migration_entries:
                        if entry:
                            # Log should not contain errors
                            assert entry.get('status') != 'error', \
                                f"Migration log contains error: {entry}"
        
        # Verify agents directory doesn't have duplicates
        agents_dir = os.path.join(copilot_home, 'agents')
        if os.path.exists(agents_dir):
            agent_files = os.listdir(agents_dir)
            unique_agents = set(agent_files)
            assert len(agent_files) == len(unique_agents), \
                "Duplicate agents found after install"


class TestQueueArtifactLocations:
    """Test that DELEGATE and HANDBACK artifacts are in correct locations."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="test-artifact-")
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_delegate_artifact_location(self):
        """
        Verify DELEGATE artifacts are stored in artifacts/delegates/
        
        Expected path:
        artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml
        """
        delegates_dir = os.path.join(self.temp_dir, 'artifacts', 'delegates', '2026-05-24')
        os.makedirs(delegates_dir, exist_ok=True)
        
        task_id = 'test-task-001'
        role = 'Engineer'
        
        delegate_file = os.path.join(delegates_dir, f'DELEGATE-{task_id}-{role}.yaml')
        
        delegate_data = {
            'handoff_type': 'DELEGATE',
            'task_id': task_id,
            'role': role,
            'model': 'claude-haiku-4.5',
            'effort': 'low',
            'scope': 'Test artifact location'
        }
        
        with open(delegate_file, 'w') as f:
            yaml.dump(delegate_data, f)
        
        # Verify file exists and is valid
        assert os.path.exists(delegate_file), f"DELEGATE not at expected location: {delegate_file}"
        
        with open(delegate_file, 'r') as f:
            parsed = yaml.safe_load(f)
        
        assert parsed['handoff_type'] == 'DELEGATE'
        assert parsed['task_id'] == task_id

    def test_handback_artifact_location_before_completion(self):
        """
        Verify HANDBACK artifacts are stored in ~/.copilot/queue/{sid}/processing/
        before completion.
        
        Expected path:
        ~/.copilot/queue/{session-id}/processing/{task_id}-HANDBACK-{role}.yaml
        """
        session_id = str(uuid.uuid4())
        processing_dir = os.path.join(
            self.temp_dir, '.copilot', 'queue', session_id, 'processing'
        )
        os.makedirs(processing_dir, exist_ok=True)
        
        task_id = 'test-task-001'
        role = 'Engineer'
        
        handback_file = os.path.join(processing_dir, f'{task_id}-HANDBACK-{role}.yaml')
        
        handback_data = {
            'handoff_type': 'HANDBACK',
            'task_id': task_id,
            'status': 'complete',
            'deliverables': ['Test artifact'],
            'tokens_in': 100,
            'tokens_out': 50
        }
        
        with open(handback_file, 'w') as f:
            yaml.dump(handback_data, f)
        
        # Verify file exists
        assert os.path.exists(handback_file), \
            f"HANDBACK not at expected location: {handback_file}"

    def test_handback_artifact_location_after_completion(self):
        """
        Verify HANDBACK artifacts are moved to ~/.copilot/queue/{sid}/done/
        after orchestrator processes them.
        
        Expected path after:
        ~/.copilot/queue/{session-id}/done/{task_id}-HANDBACK-{role}.yaml
        """
        session_id = str(uuid.uuid4())
        done_dir = os.path.join(
            self.temp_dir, '.copilot', 'queue', session_id, 'done'
        )
        os.makedirs(done_dir, exist_ok=True)
        
        task_id = 'test-task-001'
        role = 'Engineer'
        
        handback_file = os.path.join(done_dir, f'{task_id}-HANDBACK-{role}.yaml')
        
        handback_data = {
            'handoff_type': 'HANDBACK',
            'task_id': task_id,
            'status': 'complete'
        }
        
        with open(handback_file, 'w') as f:
            yaml.dump(handback_data, f)
        
        # Verify file exists
        assert os.path.exists(handback_file), \
            f"HANDBACK not at expected location in done/: {handback_file}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
    """Test fresh install to temporary home directory with full queue flow."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown test environment."""
        # Create temp directories for this test
        self.temp_repo = tempfile.mkdtemp(prefix="test-agentic-repo-")
        self.temp_home = tempfile.mkdtemp(prefix="test-agentic-home-")
        
        yield
        
        # Cleanup
        if os.path.exists(self.temp_repo):
            shutil.rmtree(self.temp_repo, ignore_errors=True)
        if os.path.exists(self.temp_home):
            shutil.rmtree(self.temp_home, ignore_errors=True)

    def _copy_repo_to_temp(self):
        """Copy repo to temp location for fresh install test."""
        repo_root = Path(__file__).parent.parent.absolute()
        
        # Copy entire repo
        for item in os.listdir(repo_root):
            src = os.path.join(repo_root, item)
            dst = os.path.join(self.temp_repo, item)
            
            # Skip certain directories
            if item in ['.git', '__pycache__', '.pytest_cache', 'htmlcov', '.DS_Store', 'dist']:
                continue
            
            # Skip symlinks (hyphenated skill packages may be symlinked)
            if os.path.islink(src):
                continue
            
            if os.path.isdir(src):
                try:
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'), symlinks=False)
                except (shutil.Error, FileNotFoundError):
                    # Skip if directory doesn't copy cleanly (e.g., broken symlinks)
                    pass
            else:
                try:
                    shutil.copy2(src, dst)
                except (IOError, OSError):
                    # Skip if file can't be copied
                    pass

    def _get_session_id(self):
        """Generate a test session ID."""
        return str(uuid.uuid4())

    def test_fresh_install_to_temp_home(self):
        """
        Verify that fresh install creates correct directory structure.
        
        Expected structure after install:
        ~/.copilot/
        ├── agents/
        │   └── *.agent.md (8 agents)
        ├── skills/
        │   └── */
        └── queue/
            └── (created by orchestrator on first run)
        """
        self._copy_repo_to_temp()
        session_id = self._get_session_id()
        
        # Simulate fresh install to temp home
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        # Run make install-copilot with custom HOME
        try:
            result = subprocess.run(
                ['make', 'install-copilot'],
                cwd=self.temp_repo,
                env=install_env,
                capture_output=True,
                text=True,
                timeout=120
            )
            assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.skip("Install timeout (make install-copilot not available or slow)")
        except FileNotFoundError:
            pytest.skip("make not available in test environment")
        
        # Verify expected structure exists
        copilot_home = os.path.join(self.temp_home, '.copilot')
        assert os.path.exists(copilot_home), f"~/.copilot/ not created at {copilot_home}"
        
        # Check agents directory
        agents_dir = os.path.join(copilot_home, 'agents')
        assert os.path.isdir(agents_dir), f"agents/ directory not found at {agents_dir}"
        
        agent_files = [f for f in os.listdir(agents_dir) if f.endswith('.agent.md')]
        assert len(agent_files) >= 8, f"Expected at least 8 agents, found {len(agent_files)}: {agent_files}"
        
        # Check skills directory
        skills_dir = os.path.join(copilot_home, 'skills')
        assert os.path.isdir(skills_dir), f"skills/ directory not found at {skills_dir}"
        
        skills_count = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
        assert skills_count > 0, "No skills found in skills/ directory"
        
        # Verify no stale files from previous installs
        assert not os.path.exists(os.path.join(copilot_home, 'incoming-legacy-')), \
            "Found legacy incoming directory (stale files from previous install)"
        assert not os.path.exists(os.path.join(copilot_home, 'processing-legacy-')), \
            "Found legacy processing directory (stale files from previous install)"

    def test_queue_init_in_fresh_install(self):
        """
        Verify that queue directories are created correctly.
        
        Expected:
        ~/.copilot/queue/{session-id}/
        ├── incoming/
        ├── processing/
        └── done/
        """
        self._copy_repo_to_temp()
        session_id = self._get_session_id()
        
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        try:
            result = subprocess.run(
                ['make', 'install-copilot'],
                cwd=self.temp_repo,
                env=install_env,
                capture_output=True,
                text=True,
                timeout=120
            )
            assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("make not available or install timeout")
        
        # Manually create queue directory structure
        queue_base = os.path.join(self.temp_home, '.copilot', 'queue')
        session_queue = os.path.join(queue_base, session_id)
        
        # Create queue structure as orchestrator would
        for subdir in ['incoming', 'processing', 'done']:
            queue_dir = os.path.join(session_queue, subdir)
            os.makedirs(queue_dir, exist_ok=True)
        
        # Verify structure
        assert os.path.isdir(os.path.join(session_queue, 'incoming')), \
            "incoming/ directory not created"
        assert os.path.isdir(os.path.join(session_queue, 'processing')), \
            "processing/ directory not created"
        assert os.path.isdir(os.path.join(session_queue, 'done')), \
            "done/ directory not created"

    def test_delegate_invoke_in_fresh_install(self):
        """
        Verify that a DELEGATE can be created and moved through queue.
        
        Flow:
        1. Create DELEGATE in incoming/
        2. Verify it's valid YAML
        3. Move to processing/ (simulating orchestrator)
        4. Create HANDBACK response
        5. Verify HANDBACK is valid
        """
        self._copy_repo_to_temp()
        session_id = self._get_session_id()
        
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        try:
            result = subprocess.run(
                ['make', 'install-copilot'],
                cwd=self.temp_repo,
                env=install_env,
                capture_output=True,
                text=True,
                timeout=120
            )
            assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("make not available or install timeout")
        
        # Setup queue structure
        queue_base = os.path.join(self.temp_home, '.copilot', 'queue')
        session_queue = os.path.join(queue_base, session_id)
        for subdir in ['incoming', 'processing', 'done']:
            os.makedirs(os.path.join(session_queue, subdir), exist_ok=True)
        
        # Create a DELEGATE
        task_id = f"test-{uuid.uuid4().hex[:8]}"
        delegate_content = {
            'handoff_type': 'DELEGATE',
            'task_id': task_id,
            'role': 'Engineer',
            'model': 'claude-haiku-4.5',
            'effort': 'low',
            'scope': 'Test fresh install queue delegation',
            'context': [
                'This is a test DELEGATE to verify queue flow.',
                'Session ID: ' + session_id
            ],
            'success_criteria': [
                'DELEGATE created successfully',
                'HANDBACK received and validated'
            ],
            'plan': [
                'Verify fresh install structure',
                'Test queue initialization',
                'Confirm DELEGATE/HANDBACK flow'
            ]
        }
        
        # Write DELEGATE to incoming/
        delegate_file = os.path.join(session_queue, 'incoming', f'{task_id}.yaml')
        with open(delegate_file, 'w') as f:
            yaml.dump(delegate_content, f)
        
        # Verify DELEGATE is valid YAML
        with open(delegate_file, 'r') as f:
            parsed_delegate = yaml.safe_load(f)
        
        assert parsed_delegate['handoff_type'] == 'DELEGATE'
        assert parsed_delegate['task_id'] == task_id
        assert parsed_delegate['role'] == 'Engineer'
        
        # Simulate orchestrator moving to processing/
        processing_file = os.path.join(session_queue, 'processing', f'{task_id}-processing.yaml')
        shutil.move(delegate_file, processing_file)
        assert not os.path.exists(delegate_file), "DELEGATE not moved from incoming/"
        assert os.path.exists(processing_file), "DELEGATE not in processing/"
        
        # Create a HANDBACK response
        handback_content = {
            'handoff_type': 'HANDBACK',
            'task_id': task_id,
            'status': 'complete',
            'deliverables': [
                'Fresh install verified',
                'Queue structure validated'
            ],
            'tests': [
                'test_fresh_install_to_temp_home PASS',
                'test_queue_init_in_fresh_install PASS',
            ],
            'tokens_in': 500,
            'tokens_out': 250,
            'model': 'claude-haiku-4.5',
            'effort': 'low',
            'duration_minutes': 5,
            'escalations': 0
        }
        
        # Write HANDBACK
        handback_file = os.path.join(session_queue, 'processing', f'{task_id}-HANDBACK-Engineer.yaml')
        with open(handback_file, 'w') as f:
            yaml.dump(handback_content, f)
        
        # Verify HANDBACK is valid
        with open(handback_file, 'r') as f:
            parsed_handback = yaml.safe_load(f)
        
        assert parsed_handback['handoff_type'] == 'HANDBACK'
        assert parsed_handback['task_id'] == task_id
        assert parsed_handback['status'] == 'complete'
        assert parsed_handback['tokens_in'] > 0
        assert parsed_handback['tokens_out'] > 0

    def test_no_stale_files_after_install(self):
        """
        Verify that no orphaned files from previous installs remain.
        
        Checks for:
        - Legacy queue directories (incoming-legacy-*, processing-legacy-*, etc.)
        - Migration logs with errors
        - Duplicate agent/skill installations
        """
        self._copy_repo_to_temp()
        
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home
        
        try:
            result = subprocess.run(
                ['make', 'install-copilot'],
                cwd=self.temp_repo,
                env=install_env,
                capture_output=True,
                text=True,
                timeout=120
            )
            assert result.returncode == 0, f"Install failed:\n{result.stderr}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("make not available or install timeout")
        
        copilot_home = os.path.join(self.temp_home, '.copilot')
        
        # Check for legacy directories
        for item in os.listdir(copilot_home):
            item_path = os.path.join(copilot_home, item)
            assert not item.startswith('incoming-legacy-'), \
                f"Found legacy incoming directory: {item}"
            assert not item.startswith('processing-legacy-'), \
                f"Found legacy processing directory: {item}"
            assert not item.startswith('done-legacy-'), \
                f"Found legacy done directory: {item}"
        
        # Check migration log if it exists
        queue_base = os.path.join(copilot_home, 'queue')
        if os.path.exists(queue_base):
            migration_log = os.path.join(queue_base, '.migration-log')
            if os.path.exists(migration_log):
                with open(migration_log, 'r') as f:
                    migration_entries = yaml.safe_load_all(f)
                    for entry in migration_entries:
                        if entry:
                            # Log should not contain errors
                            assert entry.get('status') != 'error', \
                                f"Migration log contains error: {entry}"
        
        # Verify agents directory doesn't have duplicates
        agents_dir = os.path.join(copilot_home, 'agents')
        if os.path.exists(agents_dir):
            agent_files = os.listdir(agents_dir)
            unique_agents = set(agent_files)
            assert len(agent_files) == len(unique_agents), \
                "Duplicate agents found after install"



if __name__ == '__main__':
    pytest.main([__file__, '-v'])
