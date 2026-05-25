"""
Test: Model Naming Compliance

Validates that all agent model definitions use the official Anthropic format
(hyphens, not dots). This prevents regression and ensures compatibility with
Anthropic Claude API, Copilot CLI, OpenCode, and pi.dev harnesses.

Official sources:
- Anthropic: https://docs.anthropic.com/claude/docs/models-overview
- Copilot: https://docs.github.com/en/copilot/reference/ai-models/supported-models
- Pi.dev: Anthropic API format

Requirements:
✅ All model names must use hyphens: claude-opus-4-7 (not claude-opus-4.7)
✅ No dots allowed in version numbers
✅ Consistent across all source files (agents, validators, docs)
✅ Consistent across all rendered harnesses (copilot, claude, opencode, pi)
"""

import pytest
import re
from pathlib import Path
from typing import Set


class TestModelNamingCompliance:
    """Test model naming compliance across entire codebase."""

    # Official approved model names (hyphens only)
    APPROVED_MODELS = {
        "claude-haiku-4-5",
        "claude-haiku-4-6",
        "claude-sonnet-4-5",
        "claude-sonnet-4-6",
        "claude-opus-4-5",
        "claude-opus-4-6",
        "claude-opus-4-7",
    }

    # Forbidden patterns (dots, uppercase, etc.)
    FORBIDDEN_PATTERNS = [
        r"claude-haiku-4\.5",  # Dots in version
        r"claude-haiku-4\.6",
        r"claude-sonnet-4\.5",
        r"claude-sonnet-4\.6",
        r"claude-opus-4\.5",
        r"claude-opus-4\.6",
        r"claude-opus-4\.7",
        r"claude-haiku-4_5",   # Underscores in version
        r"claude-sonnet-4_6",
        r"claude-opus-4_7",
        r"CLAUDE-",             # Uppercase prefix
        r"-4-[0-9]+[A-Z]",     # Uppercase in version
    ]

    REPO_ROOT = Path(__file__).parent.parent

    def test_agent_files_use_hyphen_format(self):
        """All agent definition files (frontmatter) must use hyphen-format model names."""
        agent_files = list(self.REPO_ROOT.glob("src/agents/*-agent.md"))
        assert agent_files, "No agent files found in src/agents/"

        for agent_file in agent_files:
            content = agent_file.read_text()

            # Extract frontmatter only (between --- delimiters)
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue

            frontmatter = frontmatter_match.group(1)

            # Extract model from frontmatter
            model_refs = re.findall(r'^model:\s*([^\s\n]+)', frontmatter, re.MULTILINE)

            for model_ref in model_refs:
                # Strip any quotes if present
                model_ref = model_ref.strip('"\'')

                # Check it's approved
                assert model_ref in self.APPROVED_MODELS, (
                    f"{agent_file.name}: Unknown model '{model_ref}'. "
                    f"Approved: {', '.join(sorted(self.APPROVED_MODELS))}"
                )

                # Check no forbidden patterns
                for forbidden in self.FORBIDDEN_PATTERNS:
                    assert not re.search(forbidden, model_ref), (
                        f"{agent_file.name}: Model '{model_ref}' uses forbidden format. "
                        f"Use hyphens only (e.g., claude-opus-4-7)"
                    )

    def test_validator_known_models_use_hyphen_format(self):
        """renderer/validate_agents.py KNOWN_MODELS must use hyphens."""
        validator_file = self.REPO_ROOT / "renderer" / "validate_agents.py"
        assert validator_file.exists(), f"Validator not found: {validator_file}"

        content = validator_file.read_text()

        # Extract KNOWN_MODELS set
        match = re.search(
            r'KNOWN_MODELS\s*=\s*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert match, "KNOWN_MODELS not found in validator"

        known_models_text = match.group(1)

        # Extract model names
        model_names = re.findall(r'"(claude-[^"]+)"', known_models_text)
        assert model_names, "No models found in KNOWN_MODELS"

        for model in model_names:
            # Check approved
            assert model in self.APPROVED_MODELS, (
                f"Validator: Unknown model '{model}'. "
                f"Approved: {', '.join(sorted(self.APPROVED_MODELS))}"
            )

            # Check no dots
            assert "." not in model, (
                f"Validator: Model '{model}' uses dots. "
                f"Use hyphens only (e.g., claude-opus-4-7)"
            )

    def test_agents_registry_uses_hyphen_format(self):
        """docs/AGENTS.md agent registry must use hyphen-format models."""
        agents_doc = self.REPO_ROOT / "docs" / "AGENTS.md"
        assert agents_doc.exists(), f"AGENTS.md not found: {agents_doc}"

        content = agents_doc.read_text()

        # Extract all model references (in tables and descriptions)
        model_refs = re.findall(r'claude-[a-z]+-[0-9-]+', content)

        for model_ref in model_refs:
            # Check no dots
            assert "." not in model_ref, (
                f"AGENTS.md: Model '{model_ref}' uses dots. "
                f"Use hyphens only"
            )

    def test_rendered_copilot_uses_hyphen_format(self):
        """Rendered Copilot files must use hyphen-format models."""
        copilot_dir = self.REPO_ROOT / "dist" / "copilot" / "agents"
        if not copilot_dir.exists():
            pytest.skip("dist/copilot not present")

        copilot_agents = list(copilot_dir.glob("*.agent.md"))
        if not copilot_agents:
            pytest.skip("No rendered Copilot agents found")

        for agent_file in copilot_agents:
            content = agent_file.read_text()
            model_refs = re.findall(r'^model:\s*([^\s\n]+)', content, re.MULTILINE)

            for model in model_refs:
                assert "." not in model, (
                    f"dist/copilot/{agent_file.name}: Model '{model}' uses dots. "
                    f"Rendered files must use hyphens"
                )

    def test_rendered_claude_uses_hyphen_format(self):
        """Rendered Claude files must use hyphen-format models."""
        claude_dir = self.REPO_ROOT / "dist" / "claude" / "agents"
        if not claude_dir.exists():
            pytest.skip("dist/claude not present")

        claude_agents = list(claude_dir.glob("*.md"))
        if not claude_agents:
            pytest.skip("No rendered Claude agents found")

        for agent_file in claude_agents:
            content = agent_file.read_text()
            model_refs = re.findall(r'^model:\s*([^\s\n]+)', content, re.MULTILINE)

            for model in model_refs:
                assert "." not in model, (
                    f"dist/claude/{agent_file.name}: Model '{model}' uses dots"
                )

    def test_rendered_opencode_uses_hyphen_format(self):
        """Rendered OpenCode files must use hyphen-format models."""
        opencode_dir = self.REPO_ROOT / "dist" / "opencode" / "agents"
        if not opencode_dir.exists():
            pytest.skip("dist/opencode not present")

        opencode_agents = list(opencode_dir.glob("*.md"))
        if not opencode_agents:
            pytest.skip("No rendered OpenCode agents found")

        for agent_file in opencode_agents:
            content = agent_file.read_text()
            # OpenCode uses github-copilot/ prefix but model ID must have hyphens
            model_refs = re.findall(
                r'github-copilot/(claude-[^\s\n"]+)|^model:\s*([^\s\n]+)',
                content,
                re.MULTILINE
            )

            for match in model_refs:
                model = match[0] or match[1]
                if model and "claude" in model:
                    assert "." not in model, (
                        f"dist/opencode/{agent_file.name}: Model '{model}' uses dots"
                    )

    def test_pi_harness_uses_correct_format(self):
        """Pi.dev harness must use hyphens (and possibly dated versions)."""
        pi_config = self.REPO_ROOT / "dist" / "pi" / "agent" / "pi.yml"
        if not pi_config.exists():
            pytest.skip("dist/pi not present")

        content = pi_config.read_text()
        model_refs = re.findall(r'claude-[a-z0-9-]+', content, re.IGNORECASE)

        for model in model_refs:
            # Pi may use dated models (claude-haiku-4-5-20251001) or standard
            # But no dots allowed
            assert "." not in model, (
                f"dist/pi/pi.yml: Model '{model}' uses dots"
            )

    def test_no_dots_in_agent_frontmatter(self):
        """CRITICAL: No dots allowed in agent frontmatter model definitions."""
        agent_files = list(self.REPO_ROOT.glob("src/agents/*-agent.md"))

        for agent_file in agent_files:
            content = agent_file.read_text()

            # Extract frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue

            frontmatter = frontmatter_match.group(1)

            # Check no dots in model field
            for forbidden in self.FORBIDDEN_PATTERNS:
                assert not re.search(forbidden, frontmatter), (
                    f"{agent_file.name}: Frontmatter uses forbidden format. "
                    f"Found dots in model names. Use hyphens only."
                )

    def test_official_documentation_references(self):
        """Verify official documentation links are current."""
        spec_file = self.REPO_ROOT / "docs" / "SPEC.md"
        content = spec_file.read_text()

        # Check that official sources are documented
        required_links = [
            "https://docs.anthropic.com/claude/docs/models-overview",
            "https://docs.github.com/en/copilot/reference/ai-models/supported-models",
        ]

        for link in required_links:
            assert link in content, (
                f"SPEC.md missing required official source link: {link}"
            )


class TestModelNamingConsistency:
    """Test consistency of model names across files."""

    REPO_ROOT = Path(__file__).parent.parent

    def test_agent_files_match_validator(self):
        """Models in agent files must be in validator's KNOWN_MODELS."""
        # Get models from validator
        validator_file = self.REPO_ROOT / "renderer" / "validate_agents.py"
        validator_content = validator_file.read_text()

        match = re.search(
            r'KNOWN_MODELS\s*=\s*\{([^}]+)\}',
            validator_content,
            re.DOTALL
        )
        validator_models = set(re.findall(r'"(claude-[^"]+)"', match.group(1)))

        # Get models from agent files
        agent_models = set()
        for agent_file in (self.REPO_ROOT / "src" / "agents").glob("*-agent.md"):
            content = agent_file.read_text()
            models = re.findall(r'model:\s*(claude-[^\s\n]+)', content)
            agent_models.update(models)

        # Agent models should be subset of validator models
        extra_in_agents = agent_models - validator_models
        assert not extra_in_agents, (
            f"Agent files use models not in validator: {extra_in_agents}"
        )

    def test_agent_files_consistency(self):
        """Agent files of same role should use same model (allow exceptions)."""
        models_by_role = {}
        exceptions = {
            "principal-engineer": ["claude-opus-4-6", "claude-opus-4-7"],  # May use both
        }

        for agent_file in (self.REPO_ROOT / "src" / "agents").glob("*-agent.md"):
            # Determine role (order matters - more specific patterns first)
            if "orchestrator" in agent_file.name:
                role = "orchestrator"
            elif "principal-engineer" in agent_file.name:
                role = "principal-engineer"
            elif "senior-engineer" in agent_file.name:
                role = "senior-engineer"
            elif "lead-engineer" in agent_file.name:
                role = "lead-engineer"
            elif "model-engineer" in agent_file.name:
                role = "model-engineer"
            elif "quality-engineer" in agent_file.name:
                role = "quality-engineer"
            elif "security-engineer" in agent_file.name:
                role = "security-engineer"
            elif agent_file.name == "engineer-agent.md":
                role = "engineer"
            else:
                continue

            content = agent_file.read_text()
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue

            frontmatter = frontmatter_match.group(1)
            models = re.findall(r'^model:\s*([^\s\n]+)', frontmatter, re.MULTILINE)

            if models:
                model = models[0].strip('"\'')  # Take first model (should be frontmatter)
                if role not in models_by_role:
                    models_by_role[role] = model
                else:
                    # Allow exceptions (some roles may have multiple valid models)
                    allowed = exceptions.get(role, [models_by_role[role]])
                    assert model in allowed, (
                        f"Inconsistent models for {role} ({agent_file.name}): "
                        f"first was {models_by_role[role]}, now {model}. "
                        f"Expected one of: {allowed}"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
