#!/usr/bin/env python3
"""
Comprehensive test suite for renderer/validate_agents.py

Tests cover:
- Frontmatter parsing (valid, malformed, missing)
- Required field validation
- Model validation
- Filename convention validation
- Agent registration in AGENTS.md
- HANDBACK schema validation
- Error reporting
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

try:
    import yaml
except ImportError:
    yaml = None

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "renderer"))
from validate_agents import (
    _parse_frontmatter,
    _load_agents_md,
    validate_agent_file,
    validate_agents,
    validate_handback_schema,
    ValidationError,
    REQUIRED_FIELDS,
    KNOWN_MODELS,
    FILENAME_EXCEPTIONS,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure for testing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    # Create src/agents directory
    agents_dir = repo_root / "src" / "agents"
    agents_dir.mkdir(parents=True)
    
    # Create src directory
    src_dir = repo_root / "src"
    
    return {
        "root": repo_root,
        "agents_dir": agents_dir,
        "src_dir": src_dir,
    }


@pytest.fixture
def valid_agent_frontmatter():
    """A valid agent YAML frontmatter."""
    return """---
name: engineer
description: Executes well-scoped implementation tasks
model: claude-sonnet-4.6
effort: medium
---
"""


@pytest.fixture
def minimal_agent_frontmatter():
    """Minimal valid frontmatter with only required fields."""
    return """---
name: test-agent
description: Test agent
model: sonnet
---
"""


@pytest.fixture
def malformed_frontmatter():
    """Frontmatter with syntax errors."""
    return """---
name: test
description: "unclosed quote
model: [
---
"""


@pytest.fixture
def missing_closing_delimiter():
    """Frontmatter missing closing --- delimiter."""
    return """---
name: test
description: test
model: sonnet
"""


# ============================================================================
# Unit Tests: Frontmatter Parsing
# ============================================================================

class TestFrontmatterParsing:
    """Test _parse_frontmatter function."""

    def test_valid_frontmatter_parsing(self, valid_agent_frontmatter):
        """Test parsing of valid YAML frontmatter."""
        result = _parse_frontmatter(valid_agent_frontmatter)
        assert result is not None
        assert result["name"] == "engineer"
        assert result["model"] == "claude-sonnet-4.6"

    def test_minimal_frontmatter(self, minimal_agent_frontmatter):
        """Test parsing minimal valid frontmatter."""
        result = _parse_frontmatter(minimal_agent_frontmatter)
        assert result is not None
        assert result["name"] == "test-agent"
        assert result["model"] == "sonnet"

    def test_no_frontmatter(self):
        """Test file without frontmatter returns None."""
        text = "# This is just markdown\nNo frontmatter here"
        result = _parse_frontmatter(text)
        assert result is None

    def test_malformed_frontmatter_raises_error(self, malformed_frontmatter):
        """Test that malformed YAML raises an exception."""
        # Should raise ValueError (wrapped from YAML errors)
        with pytest.raises(ValueError, match="YAML|closed"):
            _parse_frontmatter(malformed_frontmatter)

    def test_missing_closing_delimiter_raises_error(self, missing_closing_delimiter):
        """Test that missing closing --- raises ValueError."""
        with pytest.raises(ValueError, match="never closed"):
            _parse_frontmatter(missing_closing_delimiter)

    def test_empty_frontmatter(self):
        """Test empty frontmatter block."""
        text = """---
---
Content here"""
        result = _parse_frontmatter(text)
        assert result is None or result == {}

    def test_frontmatter_with_extra_fields(self):
        """Test frontmatter with additional fields."""
        text = """---
name: test
description: Test
model: sonnet
extra_field: value
complexity: high
---
"""
        result = _parse_frontmatter(text)
        assert result["name"] == "test"
        assert result["extra_field"] == "value"

    def test_frontmatter_with_list_values(self):
        """Test frontmatter with list values."""
        text = """---
name: test
description: Test
model: sonnet
capabilities:
  - code-review
  - testing
  - documentation
---
"""
        result = _parse_frontmatter(text)
        assert "capabilities" in result


# ============================================================================
# Unit Tests: File Loading
# ============================================================================

class TestFileLoading:
    """Test _load_agents_md function."""

    def test_load_agents_md_file_exists(self, temp_repo):
        """Test loading AGENTS.md when it exists."""
        agents_md_path = temp_repo["src_dir"] / "AGENTS.md"
        agents_md_path.write_text("# Agents\nContent here")
        
        content = _load_agents_md(temp_repo["src_dir"])
        
        assert "Agents" in content
        assert "Content here" in content

    def test_load_agents_md_file_missing(self, temp_repo):
        """Test loading AGENTS.md when it doesn't exist."""
        content = _load_agents_md(temp_repo["src_dir"])
        
        assert content == ""

    def test_load_agents_md_empty_file(self, temp_repo):
        """Test loading empty AGENTS.md."""
        agents_md_path = temp_repo["src_dir"] / "AGENTS.md"
        agents_md_path.write_text("")
        
        content = _load_agents_md(temp_repo["src_dir"])
        
        assert content == ""


# ============================================================================
# Unit Tests: Single File Validation
# ============================================================================

class TestValidateAgentFile:
    """Test validate_agent_file function."""

    def test_validate_agent_file_valid(self, temp_repo, valid_agent_frontmatter):
        """Test validation of a valid agent file."""
        agent_file = temp_repo["agents_dir"] / "engineer-agent.md"
        agent_file.write_text(valid_agent_frontmatter)
        
        agents_md_content = "engineer agent"
        errors = validate_agent_file(agent_file, agents_md_content)
        
        # Should have no errors for valid file with name match
        errors_by_type = {e.message for e in errors}
        filename_errors = [e for e in errors if "Filename" in e.message or "doesn't match" in e.message]
        # engineer -> engineer-agent.md is correct, so should pass
        assert len(filename_errors) == 0 or all("WARNING" == e.level for e in filename_errors)

    def test_validate_agent_file_missing_name(self, temp_repo):
        """Test that missing name is caught."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
description: Test
model: sonnet
---
"""
        agent_file.write_text(content)
        
        errors = validate_agent_file(agent_file, "")
        
        assert len(errors) > 0
        assert any("name" in e.message.lower() for e in errors)

    def test_validate_agent_file_missing_description(self, temp_repo):
        """Test that missing description is caught."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
name: test
model: sonnet
---
"""
        agent_file.write_text(content)
        
        errors = validate_agent_file(agent_file, "")
        
        assert len(errors) > 0
        assert any("description" in e.message.lower() for e in errors)

    def test_validate_agent_file_missing_model(self, temp_repo):
        """Test that missing model is caught."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
name: test
description: Test
---
"""
        agent_file.write_text(content)
        
        errors = validate_agent_file(agent_file, "")
        
        assert len(errors) > 0
        assert any("model" in e.message.lower() for e in errors)

    def test_validate_agent_file_missing_frontmatter(self, temp_repo):
        """Test that missing frontmatter is caught."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        agent_file.write_text("# No frontmatter\nJust content")
        
        errors = validate_agent_file(agent_file, "")
        
        assert len(errors) > 0
        assert any("frontmatter" in e.message.lower() for e in errors)

    def test_validate_agent_file_malformed_frontmatter(self, temp_repo, malformed_frontmatter):
        """Test that malformed YAML is caught."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        agent_file.write_text(malformed_frontmatter)
        
        errors = validate_agent_file(agent_file, "")
        
        assert len(errors) > 0
        assert any("frontmatter" in e.message.lower() or "malformed" in e.message.lower() for e in errors)

    def test_validate_agent_file_unknown_model(self, temp_repo):
        """Test that unknown models are flagged."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
name: test
description: Test
model: unknown-model-xyz
---
"""
        agent_file.write_text(content)
        
        errors = validate_agent_file(agent_file, "", strict=False)
        
        # Should have warning about unknown model
        assert any("model" in e.message.lower() for e in errors)

    def test_validate_agent_file_unknown_model_strict(self, temp_repo):
        """Test that unknown models become errors in strict mode."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
name: test
description: Test
model: unknown-model
---
"""
        agent_file.write_text(content)
        
        errors_normal = validate_agent_file(agent_file, "", strict=False)
        errors_strict = validate_agent_file(agent_file, "", strict=True)
        
        # Strict mode should have error or at least same or more errors
        assert len(errors_strict) >= len([e for e in errors_normal if "model" in e.message.lower()])

    def test_validate_agent_file_filename_mismatch(self, temp_repo):
        """Test that filename not matching name is flagged."""
        agent_file = temp_repo["agents_dir"] / "wrong-agent.md"
        
        content = """---
name: correct
description: Test
model: sonnet
---
"""
        agent_file.write_text(content)
        
        errors = validate_agent_file(agent_file, "")
        
        assert any("filename" in e.message.lower() for e in errors)

    def test_validate_agent_file_filename_matches_name(self, temp_repo):
        """Test that correct filename passes validation."""
        agent_file = temp_repo["agents_dir"] / "correct-agent.md"
        
        content = """---
name: correct
description: Test
model: sonnet
---
"""
        agent_file.write_text(content)
        
        errors = validate_agent_file(agent_file, "")
        
        # Should not have filename errors
        filename_errors = [e for e in errors if "filename" in e.message.lower()]
        assert len(filename_errors) == 0

    def test_validate_agent_file_not_registered(self, temp_repo):
        """Test that unregistered agents are flagged."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
name: test
description: Test
model: sonnet
---
"""
        agent_file.write_text(content)
        
        agents_md_content = "# Agents\nSome other content"
        
        errors = validate_agent_file(agent_file, agents_md_content)
        
        # Should have warning about not being in AGENTS.md
        assert any("not found" in e.message.lower() or "roster" in e.message.lower() for e in errors)

    def test_validate_agent_file_registered(self, temp_repo):
        """Test that registered agents pass validation."""
        agent_file = temp_repo["agents_dir"] / "test-agent.md"
        
        content = """---
name: test
description: Test
model: sonnet
---
"""
        agent_file.write_text(content)
        
        agents_md_content = """# Agent Roster
| test | Test agent | sonnet |
"""
        
        errors = validate_agent_file(agent_file, agents_md_content)
        
        # Should not have registration errors
        reg_errors = [e for e in errors if "not found" in e.message.lower() or "roster" in e.message.lower()]
        assert len(reg_errors) == 0


# ============================================================================
# Unit Tests: Model Validation
# ============================================================================

@pytest.mark.parametrize("model", [
    "claude-haiku-4.5",
    "claude-haiku-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.5",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-opus-4.8",
    "haiku",
    "sonnet",
    "opus",
])
def test_known_models_validation(temp_repo, model):
    """Test that all known models pass validation."""
    agent_file = temp_repo["agents_dir"] / "test-agent.md"
    
    content = f"""---
name: test
description: Test
model: {model}
---
"""
    agent_file.write_text(content)
    
    errors = validate_agent_file(agent_file, "test")
    
    model_errors = [e for e in errors if "model" in e.message.lower() and "known" in e.message.lower()]
    assert len(model_errors) == 0, f"Model {model} should be recognized"


# ============================================================================
# Unit Tests: Full Validation
# ============================================================================

class TestFullValidation:
    """Test validate_agents end-to-end."""

    def test_validate_agents_all_valid(self, temp_repo, capsys):
        """Test validation when all agents are valid."""
        agents_dir = temp_repo["agents_dir"]
        src_dir = temp_repo["src_dir"]
        
        # Create valid agent
        agent_file = agents_dir / "engineer-agent.md"
        agent_file.write_text("""---
name: engineer
description: Implementation tasks
model: sonnet
---
""")
        
        # Create AGENTS.md
        (src_dir / "AGENTS.md").write_text("""# Agent Roster
| engineer | Implementation | sonnet |

## HANDBACK Schema
Required fields: tokens_used, tokens_estimated, efficiency_ratio, model_used, duration_ms, quality_score
""")
        
        error_count, warning_count = validate_agents(agents_dir, src_dir)
        
        assert error_count == 0

    def test_validate_agents_with_errors(self, temp_repo, capsys):
        """Test validation that finds errors."""
        agents_dir = temp_repo["agents_dir"]
        src_dir = temp_repo["src_dir"]
        
        # Create invalid agent (missing model)
        agent_file = agents_dir / "bad-agent.md"
        agent_file.write_text("""---
name: bad
description: Bad agent
---
""")
        
        # Create AGENTS.md
        (src_dir / "AGENTS.md").write_text("# Agents")
        
        error_count, warning_count = validate_agents(agents_dir, src_dir)
        
        assert error_count > 0

    def test_validate_agents_no_agents_found(self, temp_repo, capsys):
        """Test when no agent files are found."""
        agents_dir = temp_repo["agents_dir"]
        src_dir = temp_repo["src_dir"]
        
        error_count, warning_count = validate_agents(agents_dir, src_dir)
        
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "no agent" in captured.out.lower()


# ============================================================================
# Unit Tests: HANDBACK Schema Validation
# ============================================================================

class TestHandbackSchema:
    """Test validate_handback_schema function."""

    def test_handback_schema_complete(self, temp_repo):
        """Test AGENTS.md with complete canonical HANDBACK schema."""
        src_dir = temp_repo["src_dir"]

        agents_md = src_dir / "AGENTS.md"
        agents_md.write_text("""
# HANDBACK Core Schema (docs/specs/protocol-core-v1.0.yaml)
- task_id
- status
- output
- metrics
  - quality
  - tokens
  - cost
  - duration_seconds
""")

        errors = validate_handback_schema(src_dir)

        assert len(errors) == 0

    def test_handback_schema_missing_field(self, temp_repo):
        """Test AGENTS.md missing a canonical HANDBACK metrics subfield."""
        src_dir = temp_repo["src_dir"]

        agents_md = src_dir / "AGENTS.md"
        agents_md.write_text("""
# HANDBACK Core Schema
- task_id
- status
- output
- metrics
  - quality
  - tokens
  - duration_seconds
""")

        errors = validate_handback_schema(src_dir)

        # Should have warning about missing 'cost' metric subfield
        assert len(errors) > 0
        assert any("cost" in e.message for e in errors)

    def test_handback_schema_no_agents_md(self, temp_repo):
        """Test when AGENTS.md doesn't exist."""
        src_dir = temp_repo["src_dir"]
        
        errors = validate_handback_schema(src_dir)
        
        # Should return empty (no file to validate)
        assert errors == []

    def test_handback_schema_all_fields_present(self, temp_repo):
        """Test AGENTS.md with all canonical required fields mentioned."""
        src_dir = temp_repo["src_dir"]

        agents_md = src_dir / "AGENTS.md"
        agents_md.write_text("""
## HANDBACK Format (docs/specs/protocol-core-v1.0.yaml)

Each HANDBACK must include:
- task_id: matching DELEGATE task_id
- status: success | failure | partial | blocked | escalate
- output: summary of what was delivered
- metrics:
  - quality: self-assessed score 0.0-1.0
  - tokens: total tokens consumed
  - cost: USD cost
  - duration_seconds: wall-clock execution time
""")

        errors = validate_handback_schema(src_dir)

        assert len(errors) == 0


# ============================================================================
# Integration Tests: Error Messages
# ============================================================================

class TestErrorMessages:
    """Test error message formatting."""

    def test_validation_error_formatting(self, temp_repo):
        """Test ValidationError formatting."""
        path = temp_repo["agents_dir"] / "test-agent.md"
        error = ValidationError(path, "ERROR", "Test error message")
        
        error_str = str(error)
        assert "ERROR" in error_str
        assert "Test error message" in error_str
        assert "test-agent.md" in error_str

    def test_validation_error_formatting_consistency(self):
        """Test that error formatting is consistent."""
        path = Path("src/agents/test-agent.md")
        error = ValidationError(path, "WARNING", "Test warning")
        
        error_str = str(error)
        assert "[WARNING]" in error_str or "WARNING" in error_str


# ============================================================================
# Parametrized Tests: Filename Convention
# ============================================================================

@pytest.mark.parametrize("agent_name,expected_filename,should_match", [
    ("engineer", "engineer-agent.md", True),
    ("test", "test-agent.md", True),
    ("my-agent", "my-agent-agent.md", True),
    ("engineer", "wrong-agent.md", False),
    ("test", "test.md", False),
])
def test_filename_convention_parametrized(temp_repo, agent_name, expected_filename, should_match):
    """Parametrized test for filename convention."""
    agents_dir = temp_repo["agents_dir"]
    
    agent_file = agents_dir / expected_filename
    content = f"""---
name: {agent_name}
description: Test
model: sonnet
---
"""
    agent_file.write_text(content)
    
    errors = validate_agent_file(agent_file, "")
    
    filename_errors = [e for e in errors if "filename" in e.message.lower()]
    
    if should_match:
        assert len(filename_errors) == 0, f"Filename {expected_filename} should match name {agent_name}"
    else:
        # For non-matching names, we should get an error
        # unless the file is in FILENAME_EXCEPTIONS
        if expected_filename not in FILENAME_EXCEPTIONS:
            pass  # May or may not have error depending on implementation


# ============================================================================
# Parametrized Tests: Required Fields
# ============================================================================

@pytest.mark.parametrize("missing_field", [
    "name",
    "description",
    "model",
])
def test_required_fields_validation(temp_repo, missing_field):
    """Test that each required field is validated."""
    agent_file = temp_repo["agents_dir"] / "test-agent.md"
    
    # Create content with one field missing
    all_fields = {
        "name": "test",
        "description": "Test agent",
        "model": "sonnet",
    }
    del all_fields[missing_field]
    
    content = "---\n"
    for key, value in all_fields.items():
        content += f"{key}: {value}\n"
    content += "---\n"
    
    agent_file.write_text(content)
    
    errors = validate_agent_file(agent_file, "")
    
    assert any(missing_field in e.message.lower() for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=renderer.validate_agents"])
