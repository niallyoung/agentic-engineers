#!/usr/bin/env python3
"""tests/test_models_docs.py - docs/MODELS.md generation.

docs/MODELS.md is generated from config/models.yaml by `models.py sync`. The
real tree is only ever READ here (`sync --check`); anything that regenerates
runs in a temp copy. Table contents are not restated: one comparison against a
freshly generated copy covers every table at once, so a legitimate registry
edit followed by `sync` never needs a test change.
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ae_models_docs", REPO_ROOT / "scripts" / "models.py")
models = importlib.util.module_from_spec(_spec)
sys.modules["ae_models_docs"] = models
_spec.loader.exec_module(models)

CLI = [sys.executable, str(REPO_ROOT / "scripts" / "models.py")]
MODELS_MD = REPO_ROOT / "docs" / "MODELS.md"
COPY_PATHS = ["config/models.yaml", "config/FRAMEWORK-MANIFEST.yaml", "src/AGENTS.md",
              "src/agents", ".githooks/LOCKED_MODELS.sh", ".agents_verification_sha", "docs/MODELS.md"]


def cli(*args, root=REPO_ROOT):
    return subprocess.run([*CLI, "--root", str(root), *args], capture_output=True, text=True)


def make_tree(tmp_path):
    for rel in COPY_PATHS:
        src, dst = REPO_ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    return tmp_path


class TestModelsDocGeneration:
    def test_models_md_is_current_under_sync_check(self):
        """Read-only on the real tree: docs/MODELS.md (and every other target) is current."""
        result = cli("sync", "--check")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "0 stale target(s)" in result.stdout

    def test_sync_regenerates_missing_models_md_identically(self, tmp_path):
        """Registry-driven comparison: a freshly generated docs/MODELS.md equals the committed
        one, so every table (roles, models, floors, history) is verified against the registry
        without restating any of its content here."""
        root = make_tree(tmp_path)
        (root / "docs" / "MODELS.md").unlink()
        assert cli("sync", root=root).returncode == 0
        generated = root / "docs" / "MODELS.md"
        assert generated.is_file()
        assert generated.read_text() == MODELS_MD.read_text()

    def test_models_md_has_generated_banner(self):
        assert "GENERATED" in MODELS_MD.read_text().splitlines()[0]

    def test_family_floors_section_lists_each_floored_family(self):
        text = MODELS_MD.read_text()
        assert "## Family Floors" in text
        section = text.split("## Family Floors", 1)[1].split("\n## ", 1)[0]
        floors = {f: (c or {}).get("min_pin") for f, c in (models.load_registry().get("families") or {}).items()}
        floored = {f: m for f, m in floors.items() if m}
        assert floored, "registry declares no family floors"
        for family, floor in floored.items():
            assert f"| {family} | `{floor}` |" in section, f"floor row for {family} missing"
