from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


DOC_FILES = [
    REPO_ROOT / "docs" / "guides" / "harness-setup" / "codex.md",
    REPO_ROOT / "renderer" / "README.md",
]


def test_codex_docs_use_explicit_install_language():
    for path in DOC_FILES:
        text = path.read_text(encoding="utf-8")
        assert "Renderer-supported" not in text
        assert "initial rollout" not in text
        assert "join default `make install`" not in text
        assert "make install-codex" in text
    for path in DOC_FILES[0:1]:
        text = path.read_text(encoding="utf-8")
        assert "~/.agents/skills" not in text


def test_codex_docs_describe_default_install():
    # NOTE: previously asserted "Supported, opt-in install" — that claim was
    # false: `make install`'s harness list (Makefile `install:` target) has
    # included `codex` alongside copilot/claude/opencode since before the "pi"
    # harness was removed (confirmed via git log -p on the install: target).
    # Fixed 2026-08-15 as part of an independent security review's M3 finding
    # (docs contradicted actual Makefile behavior); see docs/SPEC.md Update Log.
    codex_setup = (REPO_ROOT / "docs" / "guides" / "harness-setup" / "codex.md").read_text(
        encoding="utf-8"
    )

    assert "Supported, included in `make install`" in codex_setup
    assert "~/.codex/skills" in codex_setup


def test_codex_docs_describe_delegate_fanout():
    codex_setup = (REPO_ROOT / "docs" / "guides" / "harness-setup" / "codex.md").read_text(
        encoding="utf-8"
    )

    for text in (codex_setup,):
        lower = text.lower()
        assert "semicolon-separated" in lower
        assert "same-file edits coordinated" in lower
        assert "parallel" in lower
