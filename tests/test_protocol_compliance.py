"""
DELEGATE/HANDBACK protocol-marker evals for rendered harness output.

Verifies that every rendered agent carries the protocol context it needs to
participate in the queue:

  - DELEGATE and HANDBACK appear in the rendered agent body
  - accepts/returns frontmatter wires the agent into the protocol
  - the orchestrator (and model-engineer) reference the canonical queue base
    `~/.agentic-engineers/` and never the deprecated `~/.copilot/queue` /
    `~/.claude/queue` legacy paths in the agent body

There is ONE known SPEC gap captured here as an xfail (not a hard failure, since
this audit does not fix spec issues): the rendered framework doc AGENTS.md still
uses the deprecated `~/.copilot/queue/` path that SPEC §"Queue Architecture &
Paths" forbids. The xfail makes the gap visible in test output and will flip to
XPASS once the source AGENTS.md is migrated.

Renders once (session-scoped) via `make render-all`, asserts against dist/.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "dist"

PER_FILE_AGENT_HARNESSES = ("claude", "copilot", "opencode")

CANONICAL_QUEUE_BASE = "~/.agentic-engineers/"
LEGACY_QUEUE_PATHS = (r"~/\.copilot/queue", r"~/\.claude/queue")


@pytest.fixture(scope="module", autouse=True)
def _render_all():
    result = subprocess.run(
        ["make", "render-all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "make render-all failed:\n"
        f"STDOUT:\n{result.stdout[-3000:]}\n\nSTDERR:\n{result.stderr[-3000:]}"
    )
    yield


def _frontmatter(text):
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def _agent_files(harness):
    return sorted((DIST / harness / "agents").glob("*.md"))


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_every_agent_has_delegate_handback_markers(harness):
    for agent_file in _agent_files(harness):
        body = agent_file.read_text(encoding="utf-8")
        assert "DELEGATE" in body, (
            f"{harness}/{agent_file.name}: no DELEGATE marker in rendered agent"
        )
        assert "HANDBACK" in body, (
            f"{harness}/{agent_file.name}: no HANDBACK marker in rendered agent"
        )


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_every_agent_declares_accepts_and_returns(harness):
    for agent_file in _agent_files(harness):
        fm = _frontmatter(agent_file.read_text(encoding="utf-8"))
        assert "accepts:" in fm, (
            f"{harness}/{agent_file.name}: frontmatter missing 'accepts:'"
        )
        assert "returns:" in fm, (
            f"{harness}/{agent_file.name}: frontmatter missing 'returns:'"
        )
        assert "DELEGATE" in fm, (
            f"{harness}/{agent_file.name}: frontmatter does not wire DELEGATE"
        )
        assert "HANDBACK" in fm, (
            f"{harness}/{agent_file.name}: frontmatter does not wire HANDBACK"
        )


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_orchestrator_references_canonical_queue_base(harness):
    """The orchestrator must poll the canonical ~/.agentic-engineers/ queue base."""
    candidates = [
        p for p in _agent_files(harness) if p.name.startswith("orchestrator")
    ]
    assert candidates, f"{harness}: no orchestrator agent rendered"
    body = candidates[0].read_text(encoding="utf-8")
    assert CANONICAL_QUEUE_BASE in body, (
        f"{harness}/{candidates[0].name}: does not reference canonical queue base "
        f"'{CANONICAL_QUEUE_BASE}'"
    )


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_agent_bodies_have_no_legacy_queue_paths(harness):
    """Rendered agent bodies must not embed deprecated per-harness queue paths."""
    for agent_file in _agent_files(harness):
        body = agent_file.read_text(encoding="utf-8")
        for legacy in LEGACY_QUEUE_PATHS:
            assert not re.search(legacy, body), (
                f"{harness}/{agent_file.name}: contains deprecated queue path "
                f"matching '{legacy}' (SPEC mandates ~/.agentic-engineers/)"
            )


def test_pi_system_embeds_protocol():
    body = (DIST / "pi" / "agent" / "SYSTEM.md").read_text(encoding="utf-8")
    assert "DELEGATE" in body, "pi SYSTEM.md missing DELEGATE protocol context"
    assert "HANDBACK" in body, "pi SYSTEM.md missing HANDBACK protocol context"


@pytest.mark.parametrize("harness", ["claude", "copilot"])
def test_rendered_agents_md_uses_canonical_queue_path(harness):
    agents_md = (DIST / harness / "AGENTS.md").read_text(encoding="utf-8")
    for legacy in LEGACY_QUEUE_PATHS:
        assert not re.search(legacy, agents_md), (
            f"{harness}/AGENTS.md still references deprecated queue path "
            f"matching '{legacy}'"
        )
