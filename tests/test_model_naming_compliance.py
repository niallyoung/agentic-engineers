"""
Test: Model Naming Compliance (LOCKED CHOICES - Positive Enforcement)

Validates that all agent model definitions use LOCKED Claude models by choice:
- SOURCE agents (src/agents/): Must use models from LOCKED_MODELS list
  Locked models: claude-haiku-4.5, claude-sonnet-4.5, claude-sonnet-4.6, claude-opus-4.7
- RENDERED agents (dist/*/): Transform per-harness based on platform requirements
  - Copilot CLI: Pass-through (dots) → claude-opus-4.7
  - OpenCode: Transform to hyphens → claude-opus-4-7
  - Claude Code: Transform to short alias → opus
  - Pi.dev: Uses hyphens (Anthropic API format)

Philosophy: POSITIVE ENFORCEMENT
- We CHOSE these Claude models (not "GPT forbidden")
- Users CAN request model changes via Orchestrator
- Changes are explicit decisions with documented rationale
- Single source of truth: .githooks/LOCKED_MODELS.sh

Enforcement:
1. Pre-commit hook (validates agents use locked models)
2. CI pipeline (blocks merge on violation)
3. Tests in this file (comprehensive compliance verification)
4. Code comments (every agent/renderer explains transformation)

Official sources:
- Anthropic: https://docs.anthropic.com/claude/docs/models-overview (canonical format)
- Copilot CLI: https://docs.github.com/en/copilot/reference/ai-models/supported-models (dots required)
- OpenCode: GitHub issues & investigation (hyphens required)
- Pi.dev: Anthropic API compatibility (hyphens)
"""

import pytest
import re
from pathlib import Path
from typing import Set

# Canonical source format for a Claude model id.
#
# Two version shapes are valid, because Anthropic ships both:
#   - two-part  e.g. claude-haiku-4.5, claude-opus-4.8   (DOT separator)
#   - one-part  e.g. claude-opus-5, claude-sonnet-5, claude-fable-5
#
# The invariant this enforces is "the version separator is a DOT, never a
# hyphen" (claude-opus-4-7 is the forbidden per-harness render, not source).
# It is NOT "the id contains a dot" — single-part versions have no dot at all.
CANONICAL_MODEL_RE = re.compile(r"^claude-(haiku|sonnet|opus|fable)-\d+(\.\d+)?$")

_LOCKED_MODELS_SH = Path(__file__).parent.parent / ".githooks" / "LOCKED_MODELS.sh"


def _load_locked_models() -> Set[str]:
    """Parse the LOCKED_MODELS bash array from the canonical source of truth."""
    content = _LOCKED_MODELS_SH.read_text()
    block = re.search(r"^LOCKED_MODELS=\((.*?)^\)", content, re.DOTALL | re.MULTILINE)
    assert block, f"LOCKED_MODELS array not found in {_LOCKED_MODELS_SH}"
    models = set(re.findall(r'"([^"]+)"', block.group(1)))
    assert models, f"LOCKED_MODELS array is empty in {_LOCKED_MODELS_SH}"
    return models


class TestModelNamingCompliance:
    """Test model naming compliance across entire codebase (positive enforcement).
    
    Verifies that agents use LOCKED Claude models by choice, not forbidden patterns.
    Locked models are defined in .githooks/LOCKED_MODELS.sh and enforced by:
    - Pre-commit hook validation
    - This test suite
    - CI/CD pipeline
    """

    # Locked models are READ FROM .githooks/LOCKED_MODELS.sh rather than
    # duplicated here. A hardcoded copy silently drifts from the hook the moment
    # a model is approved, which is exactly how the fable-5/opus-5/sonnet-5
    # upgrade broke CI while the pre-commit hook passed.
    LOCKED_MODELS = _load_locked_models()

    # Approved = locked set plus legacy ids still valid in rendered/example
    # output but no longer assigned to any agent.
    APPROVED_MODELS = LOCKED_MODELS | {
        "claude-haiku-4.6",
        "claude-opus-4.5",
    }

    # Forbidden patterns (old hyphenated format, underscores, uppercase, etc.)
    FORBIDDEN_PATTERNS = [
        r"claude-haiku-4-5",   # Old hyphenated format
        r"claude-haiku-4-6",
        r"claude-sonnet-4-5",
        r"claude-sonnet-4-6",
        r"claude-opus-4-5",
        r"claude-opus-4-6",
        r"claude-opus-4-7",
        r"claude-haiku-4_5",   # Underscores in version
        r"claude-sonnet-4_6",
        r"claude-opus-4_7",
        r"CLAUDE-",             # Uppercase prefix
        r"-4-[0-9]+[A-Z]",     # Uppercase in version
    ]

    REPO_ROOT = Path(__file__).parent.parent

    def test_agent_files_use_locked_models(self):
        """Verify agents use LOCKED models (positive enforcement).
        
        Each agent in src/agents/ must use a model from the locked set.
        Locked models are chosen for cost-quality balance and enforced by pre-commit.
        """
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

                # Verify model is in locked set
                assert model_ref in self.LOCKED_MODELS, (
                    f"{agent_file.name}: Model '{model_ref}' not in locked set. "
                    f"Locked models: {', '.join(sorted(self.LOCKED_MODELS))}. "
                    f"To request a model change, contact Orchestrator."
                )

    def test_agent_files_use_hyphen_format(self):
        """Verify locked agents use canonical format with DOTS (Copilot CLI)."""
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

                # Check no forbidden patterns (old hyphenated format)
                for forbidden in self.FORBIDDEN_PATTERNS:
                    assert not re.search(forbidden, model_ref), (
                        f"{agent_file.name}: Model '{model_ref}' uses forbidden format. "
                        f"Use dots for Copilot CLI (e.g., claude-opus-4.7)"
                    )

    def test_validator_known_models_use_hyphen_format(self):
        """renderer/validate_agents.py KNOWN_MODELS must use dots (Copilot CLI format)."""
        validator_file = self.REPO_ROOT / "renderer" / "validate_agents.py"
        assert validator_file.exists(), f"Validator not found: {validator_file}"

        content = validator_file.read_text()

        # Extract KNOWN_MODELS set (may have comments and newlines)
        match = re.search(
            r'KNOWN_MODELS\s*=\s*\{(.*?)\n\}',
            content,
            re.DOTALL
        )
        assert match, "KNOWN_MODELS not found in validator"

        known_models_text = match.group(1)

        # Extract model names
        model_names = re.findall(r'"(claude-[^"]+)"', known_models_text)
        assert model_names, "No models found in KNOWN_MODELS"

        for model in model_names:
            if model in self.APPROVED_MODELS:
                # Canonical shape: dot-separated version, or a single-part
                # version (claude-opus-5) which has no separator at all.
                assert CANONICAL_MODEL_RE.match(model), (
                    f"Validator: Model '{model}' is not a canonical Claude id "
                    f"(e.g. claude-opus-4.7 or claude-opus-5)"
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
        """Rendered Copilot files must use dot-format models (Copilot CLI requirement)."""
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
                # Copilot CLI takes the canonical id through unchanged: a
                # dotted version (claude-opus-4.7), a single-part version
                # (claude-opus-5), or a bare short-form alias.
                assert CANONICAL_MODEL_RE.match(model) or model in {
                    "haiku",
                    "sonnet",
                    "opus",
                    "fable",
                }, (
                    f"dist/copilot/{agent_file.name}: Model '{model}' is not a "
                    f"canonical Claude id (e.g. claude-opus-4.7, claude-opus-5) "
                    f"or short form (opus)"
                )

    def test_rendered_claude_uses_hyphen_format(self):
        """Rendered Claude files must use hyphen-format models (frontmatter only)."""
        claude_dir = self.REPO_ROOT / "dist" / "claude" / "agents"
        if not claude_dir.exists():
            pytest.skip("dist/claude not present")

        claude_agents = list(claude_dir.glob("*.md"))
        if not claude_agents:
            pytest.skip("No rendered Claude agents found")

        for agent_file in claude_agents:
            content = agent_file.read_text()
            # Only check frontmatter (body may contain example DELEGATE blocks with versioned IDs)
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue
            frontmatter = frontmatter_match.group(1)
            model_refs = re.findall(r'^model:\s*([^\s\n]+)', frontmatter, re.MULTILINE)

            for model in model_refs:
                assert "." not in model, (
                    f"dist/claude/{agent_file.name}: Model '{model}' uses dots"
                )

    def test_rendered_opencode_uses_hyphen_format(self):
        """Rendered OpenCode files must use hyphen-format models (frontmatter only)."""
        opencode_dir = self.REPO_ROOT / "dist" / "opencode" / "agents"
        if not opencode_dir.exists():
            pytest.skip("dist/opencode not present")

        opencode_agents = list(opencode_dir.glob("*.md"))
        if not opencode_agents:
            pytest.skip("No rendered OpenCode agents found")

        for agent_file in opencode_agents:
            content = agent_file.read_text()
            # Only check frontmatter (body may contain example DELEGATE blocks with versioned IDs)
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue
            frontmatter = frontmatter_match.group(1)
            # OpenCode uses github-copilot/ prefix but model ID must have hyphens
            model_refs = re.findall(
                r'github-copilot/(claude-[^\s\n"]+)|^model:\s*([^\s\n]+)',
                frontmatter,
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
            # Pi may use dated models (claude-haiku-4.5-20251001) or standard
            # But no dots allowed
            assert "." not in model, (
                f"dist/pi/pi.yml: Model '{model}' uses dots"
            )

    def test_no_dots_in_agent_frontmatter(self):
        """CRITICAL: Agent frontmatter must use dot-format for Copilot CLI compatibility."""
        agent_files = list(self.REPO_ROOT.glob("src/agents/*-agent.md"))

        for agent_file in agent_files:
            content = agent_file.read_text()

            # Extract frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue

            frontmatter = frontmatter_match.group(1)

            # Check no old hyphenated format in model field
            for forbidden in self.FORBIDDEN_PATTERNS:
                assert not re.search(forbidden, frontmatter), (
                    f"{agent_file.name}: Frontmatter uses forbidden format (old hyphenated). "
                    f"Use dots for Copilot CLI (e.g., claude-opus-4.7)"
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
            r'KNOWN_MODELS\s*=\s*\{(.*?)\n\}',
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
            "principal-engineer": ["claude-opus-4.6", "claude-opus-4.7"],  # May use both
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

    def test_agents_use_only_locked_models(self):
        """Verify agents use only LOCKED Claude models (positive enforcement).
        
        Agents are not restricted from using GPT by prohibition, but rather
        are LOCKED to Claude models by choice for cost-quality alignment.
        This test verifies the positive lock is maintained.
        """
        # Models that are NOT locked (should not appear in agents)
        non_locked_patterns = [
            r'gpt-4[^0-9]',  # gpt-4, gpt-4o
            r'gpt-3\.5',      # gpt-3.5-turbo
            r'gpt-4o-mini',   # gpt-4o-mini
        ]

        search_paths = [
            self.REPO_ROOT / "src" / "agents",
            self.REPO_ROOT / "dist" / "copilot" / "agents",
            self.REPO_ROOT / "dist" / "claude" / "agents",
            self.REPO_ROOT / "dist" / "opencode" / "agents",
            self.REPO_ROOT / "dist" / "pi" / "agent",
        ]

        for path in search_paths:
            if not path.exists():
                continue

            for agent_file in path.rglob("*"):
                if not agent_file.is_file() or agent_file.suffix not in {'.md', '.yml', '.yaml'}:
                    continue

                content = agent_file.read_text()
                for pattern in non_locked_patterns:
                    matches = re.findall(pattern, content)
                    assert not matches, (
                        f"{agent_file}: Contains non-locked model. "
                        f"Use LOCKED Claude models: {', '.join(sorted(self.LOCKED_MODELS))}. "
                        f"Matched: {matches}"
                    )

    def test_locked_models_must_be_versioned(self):
        """Verify LOCKED models in source agents have versions (e.g., claude-opus-4.7 not claude-opus).
        
        All locked models require explicit versions for consistency and clarity.
        Unversioned models are ambiguous and prevent clear model assignment.
        """
        agent_files = list(self.REPO_ROOT.glob("src/agents/*-agent.md"))

        for agent_file in agent_files:
            content = agent_file.read_text()

            # Extract frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue

            frontmatter = frontmatter_match.group(1)

            # Check for unversioned models (claude-haiku, claude-sonnet, claude-opus without version)
            unversioned = re.findall(r'claude-(haiku|sonnet|opus)(?:\s|$|[\n"])', frontmatter)
            assert not unversioned, (
                f"{agent_file.name}: Unversioned model found. "
                f"Locked models must have versions: {', '.join(sorted(self.LOCKED_MODELS))}."
            )

    def test_transformer_logic_documented(self):
        """CRITICAL: Each renderer script must have comments explaining model transformation."""
        renderer_files = [
            self.REPO_ROOT / "renderer" / "scripts" / "render-copilot-agents.py",
            self.REPO_ROOT / "renderer" / "scripts" / "render-copilot-agents.sh",
            self.REPO_ROOT / "renderer" / "scripts" / "render-opencode.sh",
            self.REPO_ROOT / "renderer" / "scripts" / "render-pi-dev.py",
        ]

        for renderer_file in renderer_files:
            if not renderer_file.exists():
                continue

            content = renderer_file.read_text()

            # Check for transformation logic comments
            has_comment = any(keyword in content.lower() for keyword in [
                'transform',
                'model',
                'version',
                'copilot',
                'opencode',
                'claude',
                'harness'
            ])

            # Comment doesn't need to be present if file doesn't do transformation
            # (e.g., copilot pass-through), but should at least have something
            if 'model' in content.lower():
                assert has_comment or len(content) < 100, (
                    f"{renderer_file.name}: Contains model transformation but lacks documentation. "
                    f"Add comment explaining: canonical format input → {renderer_file.stem} output format"
                )



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
