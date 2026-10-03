"""
Test: Model Naming Compliance (registry-driven enforcement)

config/models.yaml (read via scripts/models.py) is the single source of truth for
which models exist and which model each role is pinned to (docs/SPEC.md I1-I6). This
file holds NO model list: every expectation below is derived from the registry.

- SOURCE agents (src/agents/): model must be a known registry id, canonical form
  (dot-separated minor version: claude-opus-5.5; single-part: claude-opus-5)
- RENDERED agents (dist/*/): the per-harness spelling is taken from the registry
  - Copilot CLI: models[<pin>].ids.copilot (pass-through of the dotted form)
  - OpenCode: provider-prefixed. github-copilot/ takes the dotted form (SPEC-2026-010);
    other providers take models[<pin>].ids.opencode (hyphenated)
  - Claude Code: models[<pin>].ids.claude (full pinned id, never a floating alias)

Enforcement: pre-commit (`models.py check` / `is-known`), CI, and this file.

Official sources:
- Anthropic: https://docs.anthropic.com/claude/docs/models-overview (canonical format)
- Copilot CLI: https://docs.github.com/en/copilot/reference/ai-models/supported-models
"""

import os
import pytest
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Set

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import models as model_registry  # noqa: E402

# Canonical source format for a Claude model id.
#
# Two version shapes are valid, because Anthropic ships both:
#   - two-part  e.g. claude-haiku-4.5, claude-opus-4.8   (DOT separator)
#   - one-part  e.g. claude-opus-5, claude-sonnet-5, claude-fable-5
#
# The invariant this enforces is "the version separator is a DOT, never a
# hyphen" (claude-opus-4-7 is the forbidden per-harness render, not source).
# It is NOT "the id contains a dot" — single-part versions have no dot at all.
CANONICAL_MODEL_RE = model_registry.canonical_re(model_registry.load_registry())

REPO_ROOT = Path(__file__).parent.parent
REGISTRY = model_registry.load_registry(REPO_ROOT)
ALIASES = {f["claude_alias"] for f in REGISTRY["families"].values() if f.get("claude_alias")}


def _load_locked_models() -> Set[str]:
    """Known (non-retired) model ids from config/models.yaml, via scripts/models.py."""
    models = {m for m, v in REGISTRY["models"].items() if v.get("status") != "retired"}
    assert models, "config/models.yaml lists no usable models"
    return models


def _frontmatter(path: Path):
    m = re.match(r"^---\n(.*?)\n---", path.read_text(), re.DOTALL)
    return m.group(1) if m else None


def _opencode_expected(role: str, provider: str) -> str:
    """The id OpenCode should be given for *role* under *provider*, from the registry."""
    pin = REGISTRY["roles"][role]["model"]
    ids = REGISTRY["models"][pin]["ids"]
    if provider == "github-copilot":
        return ids["copilot"]            # SPEC-2026-010: dotted
    if provider == "openrouter":
        return "anthropic/" + ids["copilot"]
    return ids["opencode"]               # hyphenated for anthropic and most others


@pytest.fixture(scope="module", autouse=True)
def _render_all(render_all):
    """Opt in to the session-scoped render (tests/conftest.py) — the dist/ checks
    below are hard assertions, so a render must be guaranteed."""
    yield


class TestModelNamingCompliance:
    """Test model naming compliance across entire codebase (positive enforcement).
    
    Verifies that agents use LOCKED Claude models by choice, not forbidden patterns.
    Known models are defined in config/models.yaml and enforced by:
    - Pre-commit hook validation (scripts/models.py)
    - This test suite
    - CI/CD pipeline
    """

    # Known models are READ FROM config/models.yaml (scripts/models.py) rather than
    # duplicated here: a hardcoded copy silently drifts from the registry.
    LOCKED_MODELS = _load_locked_models()

    # Approved = every non-retired registry model. No extra legacy ids: an id the
    # registry does not list is not approved.
    APPROVED_MODELS = LOCKED_MODELS

    # Forbidden patterns (old hyphenated format, underscores, uppercase, etc.)
    FORBIDDEN_PATTERNS = [
        r"claude-haiku-4-5",   # Old hyphenated format
        r"claude-haiku-4-6",  # kept: guards the hyphen-vs-dot render format, not
                              # the existence of a 4.6 model (see APPROVED_MODELS above)
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
        """renderer/validate_agents.py KNOWN_MODELS is derived from the registry:
        every registry model id plus the family aliases, nothing else, canonical dotted ids."""
        sys.path.insert(0, str(self.REPO_ROOT / "renderer"))
        import validate_agents

        assert validate_agents.KNOWN_MODELS == self.LOCKED_MODELS | ALIASES
        for model in validate_agents.KNOWN_MODELS - ALIASES:
            assert CANONICAL_MODEL_RE.match(model), (
                f"Validator: Model '{model}' is not a canonical Claude id "
                f"(e.g. claude-opus-4.7 or claude-opus-5)"
            )

    def test_validator_rejects_unregistered_and_hyphenated_ids(self):
        """The validator holds no version allowlist: ids absent from the registry, and
        the hyphenated render form of a registered id, are not known."""
        import validate_agents

        pin = REGISTRY["roles"]["engineer"]["model"]
        hyphenated = REGISTRY["models"][pin]["ids"]["claude"]
        assert pin in validate_agents.KNOWN_MODELS
        assert "claude-haiku-99.9" not in validate_agents.KNOWN_MODELS
        if hyphenated != pin:
            assert hyphenated not in validate_agents.KNOWN_MODELS

    def test_rendered_copilot_uses_hyphen_format(self):
        """Rendered Copilot files must use dot-format models (Copilot CLI requirement)."""
        copilot_dir = self.REPO_ROOT / "dist" / "copilot" / "agents"
        assert copilot_dir.is_dir(), "dist/copilot/agents/ not present — run 'make render-all'"

        copilot_agents = list(copilot_dir.glob("*.agent.md"))
        assert copilot_agents, (
            "No rendered Copilot agents found in "
            "dist/copilot/agents/ — run 'make render-all'"
        )

        for agent_file in copilot_agents:
            content = agent_file.read_text()
            model_refs = re.findall(r'^model:\s*([^\s\n]+)', content, re.MULTILINE)

            for model in model_refs:
                # Copilot CLI takes the canonical id through unchanged: a
                # dotted version (claude-opus-4.7), a single-part version
                # (claude-opus-5), or a bare short-form alias.
                assert CANONICAL_MODEL_RE.match(model) or model in ALIASES, (
                    f"dist/copilot/{agent_file.name}: Model '{model}' is not a "
                    f"canonical Claude id (e.g. claude-opus-4.7, claude-opus-5) "
                    f"or short form (opus)"
                )

    @pytest.mark.parametrize("provider", ["anthropic", "github-copilot"])
    def test_rendered_opencode_uses_hyphen_format(self, provider, tmp_path):
        """Rendered OpenCode frontmatter model is provider/<id>, with the id spelled the
        way that provider needs it, derived from the registry (not a fixed hyphen rule).

        github-copilot/ takes the dotted canonical id (SPEC-2026-010); anthropic and most
        other providers take the registry's hyphenated ids.opencode.

        The exact spelling is ALWAYS asserted: this test renders afresh into a temp dir with
        HOME / XDG cache pointed at an empty temp dir and no models cache, so a developer's
        ~/.cache/opencode/models.json (whose exact spelling the renderer would otherwise
        copy) can never turn the assertion into a no-op.
        """
        home = tmp_path / "home"
        home.mkdir()
        cache = tmp_path / "xdg-cache" / "opencode" / "models.json"  # deliberately absent
        assert not cache.exists()
        repo = tmp_path / "repo"
        shutil.copytree(
            self.REPO_ROOT, repo,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", ".pytest_cache", "*.pyc", "node_modules"),
        )
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        target = tmp_path / "o"
        env = {**os.environ, "NO_COLOR": "1", "HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
               "OPENCODE_MODELS_CACHE": str(cache), "OPENCODE_PROVIDER": provider}
        r = subprocess.run(["bash", str(repo / "renderer" / "scripts" / "render-opencode.sh"), str(repo), str(target)],
                           capture_output=True, text=True, env=env, timeout=300)
        assert r.returncode == 0, r.stderr

        opencode_agents = list((target / "agents").glob("*.md"))
        assert opencode_agents, f"No rendered OpenCode agents found in {target / 'agents'}"

        checked = 0
        for agent_file in opencode_agents:
            fm = _frontmatter(agent_file)
            if not fm:
                continue
            m = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE)
            role = re.search(r"^\s+role:\s*(\S+)", fm, re.MULTILINE)
            if not (m and role and role.group(1) in REGISTRY["roles"]):
                continue
            prov, _, model_id = m.group(1).partition("/")
            assert model_id, f"{agent_file.name}: '{m.group(1)}' is not provider/model"
            expected = _opencode_expected(role.group(1), provider)
            assert model_id == expected, (
                f"{agent_file.name}: '{model_id}' != registry form '{expected}' for provider '{provider}'"
            )
            checked += 1
        assert checked == len(REGISTRY["roles"]), (
            f"expected every registry role rendered, checked {checked}/{len(REGISTRY['roles'])}"
        )


class TestModelNamingConsistency:
    """Test consistency of model names across files."""

    REPO_ROOT = Path(__file__).parent.parent

    def test_agent_files_match_validator(self):
        """Models in agent files must be in the validator's KNOWN_MODELS (registry-derived)
        and equal their role's registry pin."""
        sys.path.insert(0, str(self.REPO_ROOT / "renderer"))
        import validate_agents

        for agent_file in (self.REPO_ROOT / "src" / "agents").glob("*-agent.md"):
            fm = _frontmatter(agent_file)
            assert fm, f"{agent_file.name}: no frontmatter"
            model = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE).group(1).strip("\"'")
            assert model in validate_agents.KNOWN_MODELS, (
                f"{agent_file.name}: '{model}' not in validator KNOWN_MODELS"
            )
            role = agent_file.name[: -len("-agent.md")]
            assert model == REGISTRY["roles"][role]["model"], (
                f"{agent_file.name}: '{model}' != registry pin for role {role}"
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
