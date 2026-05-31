"""
Comprehensive test suite for agent verifier and startup check.

Tests cover:
  - Agent enumeration (all 8 agents found)
  - Agent definition validation (role, model, effort, thinking_mode)
  - Agent instantiation (can be created without error)
  - Agent routing (correct model selection)
  - Startup verification (quick health check)
  - Compatibility reporting

Target: ≥15 unit tests with ≥85% coverage
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.claude.agent_verifier import (
    AgentVerifier,
    AgentDefinition,
    VerificationResult,
    CompatibilityReport,
    KNOWN_MODELS,
    EXPECTED_AGENTS,
    EXPECTED_AGENT_COUNT,
)
from src.claude.startup_check import StartupChecker, initialize_harness_check


class TestAgentDefinition:
    """Tests for AgentDefinition dataclass."""
    
    def test_agent_definition_creation(self) -> None:
        """Test creating an agent definition."""
        agent = AgentDefinition(
            name="engineer",
            role="engineer",
            model="claude-haiku-4.5",
            effort="high",
            thinking_mode="disabled",
            description="Execute well-scoped tasks",
        )
        
        assert agent.name == "engineer"
        assert agent.role == "engineer"
        assert agent.model == "claude-haiku-4.5"
        assert agent.effort == "high"
        assert agent.thinking_mode == "disabled"
        assert agent.description == "Execute well-scoped tasks"
    
    def test_agent_definition_to_dict(self) -> None:
        """Test converting agent definition to dictionary."""
        agent = AgentDefinition(
            name="orchestrator",
            role="orchestrator",
            model="claude-haiku-4.5",
        )
        
        agent_dict = agent.to_dict()
        assert isinstance(agent_dict, dict)
        assert agent_dict["name"] == "orchestrator"
        assert agent_dict["model"] == "claude-haiku-4.5"
    
    def test_agent_definition_with_file_path(self) -> None:
        """Test agent definition with file path."""
        file_path = Path("/repo/src/agents/engineer-agent.md")
        agent = AgentDefinition(
            name="engineer",
            role="engineer",
            model="claude-haiku-4.5",
            file_path=file_path,
        )
        
        agent_dict = agent.to_dict()
        assert agent_dict["file_path"] == str(file_path)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""
    
    def test_verification_result_pass(self) -> None:
        """Test creating a passing verification result."""
        result = VerificationResult(
            agent_name="engineer",
            status="PASS",
            model="claude-haiku-4.5",
        )
        
        assert result.status == "PASS"
        assert result.agent_name == "engineer"
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_verification_result_fail(self) -> None:
        """Test creating a failing verification result."""
        result = VerificationResult(
            agent_name="test-agent",
            status="FAIL",
            errors=["Missing model field", "Invalid file path"],
        )
        
        assert result.status == "FAIL"
        assert len(result.errors) == 2
    
    def test_verification_result_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = VerificationResult(
            agent_name="engineer",
            status="PASS",
            metadata={"key": "value"},
        )
        
        result_dict = result.to_dict()
        assert result_dict["agent_name"] == "engineer"
        assert result_dict["status"] == "PASS"


class TestCompatibilityReport:
    """Tests for CompatibilityReport dataclass."""
    
    def test_compatibility_report_creation(self) -> None:
        """Test creating a compatibility report."""
        report = CompatibilityReport(
            timestamp="2026-05-30T10:00:00",
            total_agents=8,
            passing=7,
            failing=1,
            warnings=0,
        )
        
        assert report.total_agents == 8
        assert report.passing == 7
        assert report.failing == 1
    
    def test_compatibility_report_to_dict(self) -> None:
        """Test converting report to dictionary."""
        report = CompatibilityReport(
            timestamp="2026-05-30T10:00:00",
            total_agents=8,
            passing=8,
            failing=0,
            warnings=0,
        )
        
        report_dict = report.to_dict()
        assert report_dict["total_agents"] == 8
        assert report_dict["passing"] == 8
        assert isinstance(report_dict["results"], list)


class TestAgentVerifier:
    """Tests for AgentVerifier class."""
    
    @pytest.fixture
    def verifier(self) -> AgentVerifier:
        """Create a verifier instance."""
        repo_root = Path(__file__).parent.parent.parent  # agentic-engineers root
        return AgentVerifier(repo_root=repo_root)
    
    @pytest.fixture
    def mock_agents_dir(self, tmp_path: Path) -> Path:
        """Create a temporary agents directory with test files."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        
        # Create a test agent file
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
name: test
description: Test agent
model: claude-haiku-4.5
---

# Test Agent

This is a test agent.
""")
        
        return agents_dir
    
    def test_agent_verifier_init(self, tmp_path: Path) -> None:
        """Test initializing AgentVerifier."""
        verifier = AgentVerifier(repo_root=tmp_path)
        assert verifier.repo_root == tmp_path
        assert verifier.agents_dir == tmp_path / "src" / "agents"
    
    def test_enumerate_agents(self, verifier: AgentVerifier) -> None:
        """Test enumerating all agents from disk."""
        agents = verifier.enumerate_agents()
        
        assert len(agents) == EXPECTED_AGENT_COUNT
        agent_names = {agent.name for agent in agents}
        assert agent_names == EXPECTED_AGENTS
    
    def test_parse_agent_file(self, verifier: AgentVerifier) -> None:
        """Test parsing a single agent markdown file."""
        engineer_file = verifier.agents_dir / "engineer-agent.md"
        definition = verifier._parse_agent_file(engineer_file)
        
        assert definition is not None
        assert definition.name == "engineer"
        assert definition.model == "claude-haiku-4.5"
        assert definition.file_path == engineer_file
    
    def test_extract_frontmatter(self, verifier: AgentVerifier) -> None:
        """Test extracting YAML frontmatter."""
        content = """---
name: test
model: claude-sonnet-4.6
description: Test agent
---

# Content
"""
        frontmatter = verifier._extract_frontmatter(content)
        
        assert frontmatter["name"] == "test"
        assert frontmatter["model"] == "claude-sonnet-4.6"
        assert frontmatter["description"] == "Test agent"
    
    def test_extract_frontmatter_no_marker(self, verifier: AgentVerifier) -> None:
        """Test extracting frontmatter when no marker present."""
        content = "# No frontmatter here\n\nJust content"
        frontmatter = verifier._extract_frontmatter(content)
        
        assert frontmatter == {}
    
    def test_extract_frontmatter_with_comments(self, verifier: AgentVerifier) -> None:
        """Test extracting frontmatter with inline comments."""
        content = """---
name: test
model: claude-haiku-4.5  # This is canonical format
---
"""
        frontmatter = verifier._extract_frontmatter(content)
        
        assert frontmatter["model"] == "claude-haiku-4.5"
    
    def test_verify_enumeration_all_found(self, verifier: AgentVerifier) -> None:
        """Test enumeration verification when all agents are found."""
        verifier.enumerate_agents()
        result = verifier.verify_enumeration()
        
        assert result.status == "PASS"
        assert result.agent_name == "enumeration"
        assert len(result.errors) == 0
    
    def test_verify_enumeration_missing_agents(self) -> None:
        """Test enumeration verification when agents are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            agents_dir = tmp_path / "src" / "agents"
            agents_dir.mkdir(parents=True)
            
            # Create only 2 agents instead of 8
            for name in ["engineer", "orchestrator"]:
                agent_file = agents_dir / f"{name}-agent.md"
                agent_file.write_text(f"---\nname: {name}\nmodel: claude-haiku-4.5\n---\n")
            
            verifier = AgentVerifier(repo_root=tmp_path)
            verifier.enumerate_agents()
            result = verifier.verify_enumeration()
            
            assert result.status == "FAIL"
            assert len(result.errors) > 0
    
    def test_verify_agent_definition_valid(self, verifier: AgentVerifier) -> None:
        """Test verifying a valid agent definition."""
        agent = AgentDefinition(
            name="engineer",
            role="engineer",
            model="claude-haiku-4.5",
            description="Execute well-scoped tasks",
        )
        
        result = verifier.verify_agent_definition(agent)
        assert result.status == "PASS"
        assert len(result.errors) == 0
    
    def test_verify_agent_definition_missing_name(self, verifier: AgentVerifier) -> None:
        """Test verifying agent with missing name."""
        agent = AgentDefinition(
            name="",
            role="test",
            model="claude-haiku-4.5",
        )
        
        result = verifier.verify_agent_definition(agent)
        assert result.status == "FAIL"
        assert any("name" in error.lower() for error in result.errors)
    
    def test_verify_agent_definition_missing_model(self, verifier: AgentVerifier) -> None:
        """Test verifying agent with missing model."""
        agent = AgentDefinition(
            name="test",
            role="test",
            model="",
        )
        
        result = verifier.verify_agent_definition(agent)
        assert result.status == "FAIL"
        assert any("model" in error.lower() for error in result.errors)
    
    def test_verify_agent_definition_unknown_model(self, verifier: AgentVerifier) -> None:
        """Test verifying agent with unknown model."""
        agent = AgentDefinition(
            name="test",
            role="test",
            model="gpt-4o",  # Not in KNOWN_MODELS
        )
        
        result = verifier.verify_agent_definition(agent)
        assert result.status == "FAIL"
        assert any("unknown" in error.lower() for error in result.errors)
    
    def test_verify_agent_definition_missing_description(self, verifier: AgentVerifier) -> None:
        """Test verifying agent with missing description (warning, not error)."""
        agent = AgentDefinition(
            name="test",
            role="test",
            model="claude-haiku-4.5",
            description=None,
        )
        
        result = verifier.verify_agent_definition(agent)
        assert result.status == "WARN"
        assert any("description" in warning.lower() for warning in result.warnings)
    
    def test_verify_agent_instantiation_valid(self, verifier: AgentVerifier) -> None:
        """Test verifying agent instantiation for valid agent."""
        agent = AgentDefinition(
            name="engineer",
            role="engineer",
            model="claude-haiku-4.5",
        )
        
        result = verifier.verify_agent_instantiation(agent)
        assert result.status == "PASS"
        assert result.metadata["instantiable"] is True
    
    def test_verify_agent_instantiation_invalid_model(self, verifier: AgentVerifier) -> None:
        """Test verifying agent instantiation with invalid model."""
        agent = AgentDefinition(
            name="test",
            role="test",
            model="invalid-model-9999",
        )
        
        result = verifier.verify_agent_instantiation(agent)
        assert result.status == "FAIL"
        assert result.metadata["instantiable"] is False
    
    def test_verify_routing_correct_model(self, verifier: AgentVerifier) -> None:
        """Test verifying correct routing for engineer agent."""
        agent = AgentDefinition(
            name="engineer",
            role="engineer",
            model="claude-haiku-4.5",
        )
        
        result = verifier.verify_routing(agent)
        assert result.status == "PASS"
        assert result.metadata["expected_model"] == "claude-haiku-4.5"
    
    def test_verify_routing_wrong_model(self, verifier: AgentVerifier) -> None:
        """Test verifying routing with wrong model."""
        agent = AgentDefinition(
            name="engineer",
            role="engineer",
            model="claude-opus-4.6",  # Wrong for engineer
        )
        
        result = verifier.verify_routing(agent)
        assert result.status == "FAIL"
        assert any("mismatch" in error.lower() for error in result.errors)
    
    def test_verify_all_agents(self, verifier: AgentVerifier) -> None:
        """Test full verification on all agents."""
        report = verifier.verify_all_agents()
        
        assert report.total_agents == EXPECTED_AGENT_COUNT
        assert report.passing > 0
        assert report.failing == 0
        assert len(report.results) > 0
    
    def test_generate_json_report(self, verifier: AgentVerifier, tmp_path: Path) -> None:
        """Test generating JSON report."""
        output_file = tmp_path / "report.json"
        report_json = verifier.generate_json_report(output_path=output_file)
        
        assert output_file.exists()
        report_dict = json.loads(report_json)
        assert report_dict["total_agents"] == EXPECTED_AGENT_COUNT
    
    def test_get_verification_cache_key(self, verifier: AgentVerifier) -> None:
        """Test generating cache key."""
        cache_key = verifier.get_verification_cache_key()
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 64  # SHA256 hex digest length
    
    def test_cache_key_deterministic(self, verifier: AgentVerifier) -> None:
        """Test that cache key is deterministic."""
        key1 = verifier.get_verification_cache_key()
        key2 = verifier.get_verification_cache_key()
        
        assert key1 == key2
    
    def test_print_report_pass(self, verifier: AgentVerifier, capsys) -> None:
        """Test printing a passing report."""
        report = verifier.verify_all_agents()
        verifier.print_report(report)
        
        captured = capsys.readouterr()
        assert "AGENT AVAILABILITY VERIFICATION REPORT" in captured.out
        assert "✅" in captured.out or "All agents verified" in captured.out


class TestStartupChecker:
    """Tests for StartupChecker class."""
    
    @pytest.fixture
    def tmp_cache_dir(self, tmp_path: Path) -> Path:
        """Create a temporary cache directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        return cache_dir
    
    def test_startup_checker_init(self, tmp_cache_dir: Path) -> None:
        """Test initializing StartupChecker."""
        checker = StartupChecker(cache_dir=tmp_cache_dir)
        assert checker.cache_dir == tmp_cache_dir
        assert checker.cache_ttl_seconds == 3600
    
    def test_get_cache_key(self) -> None:
        """Test getting cache key from checker."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root)
        cache_key = checker._get_cache_key()
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 64
    
    def test_write_and_read_cache(self, tmp_cache_dir: Path) -> None:
        """Test writing and reading cache."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        # Generate report
        report = checker.verifier.verify_all_agents()
        
        # Write cache
        checker._write_cache(report)
        assert checker.cache_file.exists()
        
        # Read cache
        cached = checker._read_cache()
        assert cached is not None
        assert cached["total_agents"] == EXPECTED_AGENT_COUNT
    
    def test_cache_expiration(self, tmp_cache_dir: Path) -> None:
        """Test cache expiration based on TTL."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(
            repo_root=repo_root,
            cache_dir=tmp_cache_dir,
            cache_ttl_seconds=0,  # Expire immediately
        )
        
        # Generate and cache report
        report = checker.verifier.verify_all_agents()
        checker._write_cache(report)
        
        # Cache should be expired
        import time
        time.sleep(0.1)  # Wait slightly
        cached = checker._read_cache()
        assert cached is None
    
    def test_cache_invalidation_on_key_change(self, tmp_cache_dir: Path) -> None:
        """Test cache invalidation when file key changes."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        # Write cache
        report = checker.verifier.verify_all_agents()
        checker._write_cache(report)
        
        # Mock getting a different cache key
        original_get_key = checker._get_cache_key
        checker._get_cache_key = lambda: "different_key_12345"
        
        # Cache should be invalid
        cached = checker._read_cache()
        assert cached is None
        
        # Restore
        checker._get_cache_key = original_get_key
    
    def test_run_check_without_cache(self, tmp_cache_dir: Path) -> None:
        """Test running check without using cache."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        status = checker.run_check(use_cache=False)
        
        assert "success" in status
        assert "agents_checked" in status
        assert "agents_failed" in status
        assert "cache_hit" in status
        assert status["cache_hit"] is False
    
    def test_run_check_with_cache_hit(self, tmp_cache_dir: Path) -> None:
        """Test running check with cache hit."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        # First run (no cache)
        status1 = checker.run_check(use_cache=False)
        assert status1["cache_hit"] is False
        
        # Second run (should hit cache)
        status2 = checker.run_check(use_cache=True)
        assert status2["cache_hit"] is True
    
    def test_run_check_success_message(self, tmp_cache_dir: Path) -> None:
        """Test run_check success message."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        status = checker.run_check(use_cache=False)
        
        assert status["success"] is True
        assert status["agents_checked"] == EXPECTED_AGENT_COUNT
        assert status["agents_failed"] == 0
        assert "✅" in status["message"] or "All" in status["message"]
    
    def test_report_to_status_success(self) -> None:
        """Test converting successful report to status."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root)
        
        report_dict = {
            "total_agents": 8,
            "failing": 0,
        }
        
        status = checker._report_to_status(report_dict, cache_hit=False)
        assert status["success"] is True
    
    def test_report_to_status_failure(self) -> None:
        """Test converting failed report to status."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root)
        
        report_dict = {
            "total_agents": 8,
            "failing": 2,
        }
        
        status = checker._report_to_status(report_dict, cache_hit=False)
        assert status["success"] is False
        assert status["agents_failed"] == 2
    
    def test_clear_cache(self, tmp_cache_dir: Path) -> None:
        """Test clearing cache."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        # Write cache
        report = checker.verifier.verify_all_agents()
        checker._write_cache(report)
        assert checker.cache_file.exists()
        
        # Clear cache
        checker.clear_cache()
        assert not checker.cache_file.exists()
    
    def test_get_quick_status(self, tmp_cache_dir: Path) -> None:
        """Test getting quick status string."""
        repo_root = Path(__file__).parent.parent.parent
        checker = StartupChecker(repo_root=repo_root, cache_dir=tmp_cache_dir)
        
        status_msg = checker.get_quick_status()
        assert isinstance(status_msg, str)
        assert len(status_msg) > 0


class TestIntegration:
    """Integration tests."""
    
    def test_full_verification_workflow(self) -> None:
        """Test complete verification workflow."""
        repo_root = Path(__file__).parent.parent.parent
        verifier = AgentVerifier(repo_root=repo_root)
        
        # Enumerate
        agents = verifier.enumerate_agents()
        assert len(agents) == EXPECTED_AGENT_COUNT
        
        # Verify all
        report = verifier.verify_all_agents()
        
        assert report.total_agents == EXPECTED_AGENT_COUNT
        assert report.failing == 0
        assert report.passing > 0
    
    def test_startup_check_full_workflow(self) -> None:
        """Test complete startup check workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            repo_root = Path(__file__).parent.parent.parent
            
            checker = StartupChecker(repo_root=repo_root, cache_dir=cache_dir)
            
            # Run without cache
            status1 = checker.run_check(use_cache=False)
            assert status1["success"] is True
            assert status1["cache_hit"] is False
            
            # Run with cache
            status2 = checker.run_check(use_cache=True)
            assert status2["success"] is True
            assert status2["cache_hit"] is True
    
    def test_initialize_harness_check_success(self) -> None:
        """Test harness initialization check."""
        result = initialize_harness_check()
        assert isinstance(result, bool)
        # In CI, this should pass
        if Path(__file__).parent.parent.parent.name == "agentic-engineers":
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
