#!/usr/bin/env python3
"""tests/test_models_registry.py - config/models.yaml + scripts/models.py.

Covers registry shape, every CLI subcommand, zero-diff sync on the real tree,
resolve/fallback behaviour, and a bump simulation proving that re-pinning a role
needs only a registry edit (+ pin_history) followed by `sync`.
"""

import copy
import datetime
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ae_models", REPO_ROOT / "scripts" / "models.py")
models = importlib.util.module_from_spec(_spec)
sys.modules["ae_models"] = models
_spec.loader.exec_module(models)

CLI = [sys.executable, str(REPO_ROOT / "scripts" / "models.py")]
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


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(root).rglob("*") if p.is_file()}


def edit_registry(root, fn):
    path = Path(root) / "config" / "models.yaml"
    reg = yaml.safe_load(path.read_text())
    fn(reg)
    path.write_text(yaml.safe_dump(reg, sort_keys=False))


@pytest.fixture(scope="module")
def reg():
    return models.load_registry()


# ----------------------------------------------------------------- shape ---

class TestRegistryShape:
    def test_real_registry_passes_check(self):
        errors, _ = models.check()
        assert errors == []

    def test_model_ids_are_canonical_dotted(self, reg):
        rx = models.canonical_re(reg)
        for mid in reg["models"]:
            assert rx.match(mid), mid

    def test_family_matches_id(self, reg):
        for mid, m in reg["models"].items():
            assert m["family"] == mid.split("-")[1]

    def test_every_model_has_all_harness_ids(self, reg):
        for mid, m in reg["models"].items():
            for h in ("claude", "copilot", "opencode"):
                assert m["ids"].get(h), (mid, h)

    def test_claude_ids_are_hyphenated_and_unique(self, reg):
        ids = [m["ids"]["claude"] for m in reg["models"].values()]
        assert len(ids) == len(set(ids))
        assert all("." not in i for i in ids)

    def test_unverified_facts_are_null_not_invented(self, reg):
        for m in reg["models"].values():
            assert m["verified"] is None and m["source"] is None

    def test_roles_match_agents_dir_and_manifest(self, reg):
        on_disk = {p.name[:-len("-agent.md")] for p in (REPO_ROOT / "src/agents").glob("*-agent.md")}
        manifest = yaml.safe_load((REPO_ROOT / "config/FRAMEWORK-MANIFEST.yaml").read_text())
        assert set(reg["roles"]) == on_disk == set(manifest["agents"])

    def test_seeded_pins_match_todays_assignments(self, reg):
        got = {r: (c["model"], c["effort"]) for r, c in reg["roles"].items()}
        assert got == {
            "engineer": ("claude-haiku-4.5", "high"),
            "orchestrator": ("claude-sonnet-5.5", "low"),
            "lead-engineer": ("claude-sonnet-5.5", "high"),
            "quality-engineer": ("claude-sonnet-5.5", "medium"),
            "senior-engineer": ("claude-sonnet-5.5", "high"),
            "model-engineer": ("claude-sonnet-5.5", "high"),
            "security-engineer": ("claude-fable-5", "max"),
            "principal-engineer": ("claude-opus-5.5", "high"),
        }

    def test_fallbacks_per_decision(self, reg):
        fb = {r: c["fallback"] for r, c in reg["roles"].items()}
        assert fb["principal-engineer"] == fb["security-engineer"] == ["claude-opus-5", "claude-opus-4.8"]
        for r in ("lead-engineer", "quality-engineer", "senior-engineer", "model-engineer"):
            assert fb[r] == ["claude-sonnet-5"]

    def test_pin_history_latest_matches_pin(self, reg):
        last = {}
        for e in reg["pin_history"]:
            last[e["role"]] = e["to"]
        assert last == {r: c["model"] for r, c in reg["roles"].items()}


# ------------------------------------------------------------ validators ---

class TestCheckRules:
    @pytest.mark.parametrize("mutate,needle", [
        (lambda r: r["roles"]["engineer"].update(model="claude-haiku-4.55"), "not in models"),
        (lambda r: r["roles"]["senior-engineer"].update(model="claude-sonnet-4.5"), "pin_history"),
        (lambda r: r["models"]["claude-sonnet-5"].update(status="retired"), "retired"),
        (lambda r: r["roles"]["principal-engineer"].update(fallback=["claude-haiku-4.5"]), "crosses family"),
        (lambda r: r["roles"]["principal-engineer"].update(fallback=["claude-opus-9"]), "not in models"),
        (lambda r: r["roles"]["engineer"].update(effort="turbo"), "effort"),
        (lambda r: r["models"]["claude-sonnet-5"]["ids"].pop("claude"), "ids.claude"),
        (lambda r: r["models"]["claude-sonnet-5"]["ids"].update(claude="claude-sonnet-5.0"), "wrong shape"),
        (lambda r: r["models"].update({"claude-Sonnet-6": copy.deepcopy(r["models"]["claude-sonnet-5"])}), "does not match"),
        (lambda r: r["models"]["claude-sonnet-5"].update(family="opus"), "family"),
        (lambda r: r["roles"].pop("engineer"), "no registry entry"),
        (lambda r: r["roles"].update({"ghost": copy.deepcopy(r["roles"]["engineer"])}), "ghost"),
    ])
    def test_rule_fires(self, tmp_path, mutate, needle):
        root = make_tree(tmp_path)
        edit_registry(root, mutate)
        errors, _ = models.check(root)
        assert any(needle in e for e in errors), errors
        assert cli("check", root=root).returncode == 1

    def test_deprecated_pin_warns_not_errors(self, tmp_path):
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["models"]["claude-fable-5"].update(status="deprecated"))
        cli("sync", root=root)  # Regenerate docs/MODELS.md after registry edit
        errors, warns = models.check(root)
        assert errors == [] and any("deprecated" in w for w in warns)

    def test_stale_frontmatter_is_an_error(self, tmp_path):
        root = make_tree(tmp_path)
        f = root / "src/agents/engineer-agent.md"
        f.write_text(f.read_text().replace("\nmodel: claude-haiku-4.5\n", "\nmodel: claude-sonnet-5\n", 1))
        errors, _ = models.check(root)
        assert any("engineer-agent.md" in e and "stale" in e for e in errors)

    def test_invalid_yaml_is_reported(self, tmp_path):
        root = make_tree(tmp_path)
        (root / "config/models.yaml").write_text("roles: [unclosed\n")
        assert cli("check", root=root).returncode == 1


# ------------------------------------------------------------------- CLI ---

class TestCli:
    def test_check_exit_zero(self):
        r = cli("check")
        assert r.returncode == 0, r.stderr
        assert "0 error(s)" in r.stdout

    def test_get_model_effort_fallback_id(self):
        assert cli("get", "orchestrator").stdout.strip() == "claude-sonnet-5.5"
        assert cli("get", "security-engineer", "--field", "effort").stdout.strip() == "max"
        assert cli("get", "principal-engineer", "--field", "fallback").stdout.strip() == "claude-opus-5 claude-opus-4.8"
        assert cli("get", "orchestrator", "--harness", "claude").stdout.strip() == "claude-sonnet-5-5"
        assert cli("get", "engineer", "--harness", "claude").stdout.strip() == "claude-haiku-4-5"
        assert cli("get", "engineer", "--harness", "copilot").stdout.strip() == "claude-haiku-4.5"
        assert cli("get", "principal-engineer", "--harness", "opencode").stdout.strip() == "claude-opus-5-5"

    def test_get_errors(self):
        assert cli("get", "nope").returncode == 2
        assert cli("get", "engineer", "--field", "id").returncode == 2
        assert cli("get", "engineer", "--harness", "codex").returncode == 2

    def test_is_known(self):
        assert cli("is-known", "claude-fable-5").returncode == 0
        assert cli("is-known", "claude-sonnet-5.55").returncode == 1
        assert cli("is-known", "claude-sonnet-5-5").returncode == 1  # hyphen form is a render, not source

    def test_list_ids_matches_locked_models_shim(self, reg):
        ids = cli("list-ids").stdout.split()
        shim = (REPO_ROOT / ".githooks/LOCKED_MODELS.sh").read_text()
        block = re.search(r"(?ms)^LOCKED_MODELS=\(\n(.*?)\n\)", shim).group(1)
        assert ids == re.findall(r'"([^"]+)"', block) == list(reg["models"])

    def test_list_ids_harness_and_retired(self, tmp_path):
        assert "claude-sonnet-5-5" in cli("list-ids", "--harness", "claude").stdout.split()
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["models"]["claude-opus-4.6"].update(status="retired"))
        assert "claude-opus-4.6" not in cli("list-ids", root=root).stdout.split()
        assert "claude-opus-4.6" in cli("list-ids", "--include-retired", root=root).stdout.split()
        assert cli("is-known", "claude-opus-4.6", root=root).returncode == 1


# ------------------------------------------------------------------ sync ---

class TestSync:
    def test_zero_diff_on_real_tree(self):
        """sync on the committed tree changes nothing (git sees no diff in generated targets)."""
        targets = [".githooks/LOCKED_MODELS.sh", "src/AGENTS.md", "src/agents", "config/FRAMEWORK-MANIFEST.yaml",
                   ".agents_verification_sha"]
        before = subprocess.run(["git", "diff", "--", *targets], cwd=REPO_ROOT, capture_output=True, text=True).stdout
        r = cli("sync")
        assert r.returncode == 0 and "0 file(s) updated" in r.stdout, r.stdout + r.stderr
        after = subprocess.run(["git", "diff", "--", *targets], cwd=REPO_ROOT, capture_output=True, text=True).stdout
        assert before == after

    def test_sync_check_clean_and_idempotent(self, tmp_path):
        assert cli("sync", "--check").returncode == 0
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["roles"]["engineer"].update(model="claude-sonnet-5"))
        assert cli("sync", "--check", root=root).returncode == 1
        assert cli("sync", root=root).returncode == 0
        snap = snapshot(root)
        assert cli("sync", root=root).returncode == 0
        assert snapshot(root) == snap

    def test_sync_preserves_prose_and_comments(self, tmp_path):
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["roles"]["quality-engineer"].update(effort="high"))
        cli("sync", root=root)
        old = (REPO_ROOT / "src/AGENTS.md").read_text().splitlines()
        new = (root / "src/AGENTS.md").read_text().splitlines()
        diff = [(a, b) for a, b in zip(old, new) if a != b]
        assert len(old) == len(new) and 1 <= len(diff) <= 2
        assert any("| high |" in b and "Quality Engineer" in b for _, b in diff)
        assert "# model: claude-haiku-4.5" in (root / "src/agents/engineer-agent.md").read_text()


# --------------------------------------------------------------- resolve ---

class TestResolve:
    def test_no_availability_info_returns_pin(self, tmp_path):
        r = cli("resolve", "orchestrator", "--harness", "claude", "--no-record")
        assert r.returncode == 0 and r.stdout.strip() == "claude-sonnet-5-5" and r.stderr == ""

    def test_pin_available(self, tmp_path):
        avail = tmp_path / "a.json"
        avail.write_text(json.dumps({"anthropic": {"models": {"claude-sonnet-5-5": {}}}}))
        rec = tmp_path / "rec.json"
        r = cli("resolve", "orchestrator", "--harness", "opencode", "--available-from", str(avail), "--record", str(rec))
        assert r.returncode == 0 and r.stdout.strip() == "claude-sonnet-5-5" and "WARN" not in r.stderr
        data = json.loads(rec.read_text())["roles"]["orchestrator"]
        assert data["fallback_used"] is False

    def test_fallback_warns_and_records(self, tmp_path):
        avail = tmp_path / "a.json"
        avail.write_text(json.dumps(["anthropic/claude-opus-4.8", "claude-haiku-4-5"]))
        rec = tmp_path / "rec.json"
        r = cli("resolve", "principal-engineer", "--harness", "claude", "--available-from", str(avail), "--record", str(rec))
        assert r.returncode == 0 and r.stdout.strip() == "claude-opus-4-8"
        assert "WARN model-fallback role=principal-engineer pinned=claude-opus-5.5 used=claude-opus-4.8" in r.stderr
        data = json.loads(rec.read_text())["roles"]["principal-engineer"]
        assert data["fallback_used"] is True and data["pinned"] == "claude-opus-5.5" and data["used"] == "claude-opus-4.8"
        assert [t["result"] for t in data["tried"]] == ["not available", "not available", "selected"]

    def test_nothing_available_fails_loudly_no_cross_family_substitution(self, tmp_path):
        avail = tmp_path / "a.json"
        avail.write_text(json.dumps(["claude-haiku-4-5", "claude-sonnet-5"]))
        rec = tmp_path / "rec.json"
        r = cli("resolve", "security-engineer", "--harness", "claude", "--available-from", str(avail), "--record", str(rec))
        assert r.returncode == 3 and r.stdout == "" and "model-unresolved" in r.stderr
        assert json.loads(rec.read_text())["roles"]["security-engineer"]["used"] is None

    def test_default_record_path_under_root_dist(self, tmp_path):
        root = make_tree(tmp_path)
        assert cli("resolve", "engineer", "--harness", "copilot", root=root).returncode == 0
        assert (root / "dist/copilot/model-resolution.json").is_file()

    def test_codex_has_no_ids(self):
        r = cli("resolve", "engineer", "--harness", "codex", "--no-record")
        assert r.returncode == 3


# ------------------------------------------------------- bump simulation ---

class TestBumpSimulation:
    """Re-pinning a role touches the registry (+ pin_history) and generated files only."""

    GENERATED = {"src/AGENTS.md", "src/agents/senior-engineer-agent.md",
                 "config/FRAMEWORK-MANIFEST.yaml", ".agents_verification_sha", "docs/MODELS.md"}

    @staticmethod
    def _bump(reg):
        reg["models"]["claude-sonnet-9.9"] = {
            "family": "sonnet", "status": "current", "verified": None, "source": None,
            "ids": {"claude": "claude-sonnet-9-9", "copilot": "claude-sonnet-9.9", "opencode": "claude-sonnet-9-9"}}
        reg["roles"]["senior-engineer"]["model"] = "claude-sonnet-9.9"

    def test_bump_needs_only_registry_and_generated_files(self, tmp_path):
        root = make_tree(tmp_path)
        before = snapshot(root)

        edit_registry(root, self._bump)
        # Without a pin_history entry the check refuses, and generated files are stale.
        errors, _ = models.check(root)
        assert any("pin_history" in e for e in errors)

        edit_registry(root, lambda r: r["pin_history"].append(
            {"date": datetime.date(2026, 10, 3), "role": "senior-engineer", "from": "claude-sonnet-5.5",
             "to": "claude-sonnet-9.9", "approval": "test"}))
        errors, _ = models.check(root)
        assert any("stale" in e for e in errors) and not any("pin_history" in e for e in errors)

        assert cli("sync", root=root).returncode == 0
        assert models.check(root) == ([], [])

        after = snapshot(root)
        changed = {p for p in after if before.get(p) != after[p]}
        assert changed == self.GENERATED | {"config/models.yaml", ".githooks/LOCKED_MODELS.sh"}

        shim = (root / ".githooks/LOCKED_MODELS.sh").read_text()
        assert '"claude-sonnet-9.9"' in shim and '"senior-engineer-agent:claude-sonnet-9.9"' in shim
        assert "\nmodel: claude-sonnet-9.9\n" in (root / "src/agents/senior-engineer-agent.md").read_text()
        assert cli("get", "senior-engineer", "--harness", "claude", root=root).stdout.strip() == "claude-sonnet-9-9"
        # Nothing else in the tree (other agent files, other roles) moved.
        assert after["src/agents/engineer-agent.md"] == before["src/agents/engineer-agent.md"]

    def test_bump_to_typo_id_fails(self, tmp_path):
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["roles"]["senior-engineer"].update(model="claude-sonnet-9.99"))
        assert cli("check", root=root).returncode == 1

    def test_bump_to_retired_model_fails(self, tmp_path):
        root = make_tree(tmp_path)
        def mut(r):
            r["models"]["claude-sonnet-4.5"]["status"] = "retired"
            r["roles"]["senior-engineer"]["model"] = "claude-sonnet-4.5"
        edit_registry(root, mut)
        errors, _ = models.check(root)
        assert any("retired" in e for e in errors)
