from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


DOC_FILES = [
    REPO_ROOT / "docs" / "CODEX-RENDERER-HANDOFF.md",
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
    for path in DOC_FILES[0:2]:
        text = path.read_text(encoding="utf-8")
        assert "~/.agents/skills" not in text


def test_codex_docs_keep_opt_in_language():
    codex_setup = (REPO_ROOT / "docs" / "guides" / "harness-setup" / "codex.md").read_text(
        encoding="utf-8"
    )

    assert "Supported, opt-in install" in codex_setup
    assert "~/.codex/skills" in codex_setup


def test_codex_docs_describe_delegate_fanout():
    codex_setup = (REPO_ROOT / "docs" / "guides" / "harness-setup" / "codex.md").read_text(
        encoding="utf-8"
    )
    renderer_handoff = (REPO_ROOT / "docs" / "CODEX-RENDERER-HANDOFF.md").read_text(
        encoding="utf-8"
    )

    for text in (codex_setup, renderer_handoff):
        lower = text.lower()
        assert "semicolon-separated" in lower
        assert "same-file edits coordinated" in lower
        assert "parallel" in lower
