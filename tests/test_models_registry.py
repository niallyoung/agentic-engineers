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


def verification_problem(verified, source):
    """None if (verified, source) is a legal pair, else a human-readable problem."""
    if verified is None and source is None:
        return None
    if verified is None or source is None:
        return f"verified={verified!r} source={source!r}: record both or neither"
    if isinstance(verified, datetime.date):
        pass
    elif not (isinstance(verified, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified)):
        return f"verified={verified!r} is not an ISO date"
    else:
        try:
            datetime.date.fromisoformat(verified)
        except ValueError:
            return f"verified={verified!r} is not a real date"
    if not (isinstance(source, str) and re.fullmatch(r"https://[^\s/]+\S*", source)):
        return f"source={source!r} is not an https URL"
    return None


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
        """A model either records NO verification (both null) or a complete, well-formed
        one (ISO date + https source). Half-recorded or invented-looking values fail."""
        for mid, m in reg["models"].items():
            problem = verification_problem(m.get("verified"), m.get("source"))
            assert problem is None, f"{mid}: {problem}"

    @pytest.mark.parametrize("verified,source,ok", [
        (None, None, True),
        ("2026-05-14", "https://example.com/models", True),
        (datetime.date(2026, 5, 14), "https://example.com/models", True),
        ("2026-05-14", None, False),                       # verified without source
        (None, "https://example.com/models", False),       # source without verified
        ("yes", "https://example.com/models", False),      # invented-looking date
        ("2026-13-45", "https://example.com/models", False),
        ("2026-05-14", "see the vendor blog", False),      # not a URL
        ("2026-05-14", "http://example.com/models", False),  # not https
        ("", "", False),                                   # empty strings are not null
    ])
    def test_verification_rule_itself(self, verified, source, ok):
        assert (verification_problem(verified, source) is None) is ok

    def test_roles_match_agents_dir_and_manifest(self, reg):
        on_disk = {p.name[:-len("-agent.md")] for p in (REPO_ROOT / "src/agents").glob("*-agent.md")}
        manifest = yaml.safe_load((REPO_ROOT / "config/FRAMEWORK-MANIFEST.yaml").read_text())
        assert set(reg["roles"]) == on_disk == set(manifest["agents"])

    def test_every_role_has_a_registered_pin_and_valid_effort(self, reg):
        """Registry-driven: a legitimate pin bump (edit config/models.yaml + sync) must not
        need any edit here. Today's concrete assignments live in the registry itself;
        docs/agents/tests that restate them are checked against it, not the other way."""
        assert reg["roles"], "registry has no roles"
        for role, cfg in reg["roles"].items():
            assert cfg["model"] in reg["models"], role
            assert reg["models"][cfg["model"]]["status"] != "retired", role
            assert cfg["effort"] in models.EFFORTS, role

    def test_role_pins_agree_with_agent_frontmatter(self, reg):
        for role, cfg in reg["roles"].items():
            text = (REPO_ROOT / "src" / "agents" / f"{role}-agent.md").read_text()
            m = re.search(r"(?m)^model:\s*(\S+)\s*$", text)
            assert m and m.group(1) == cfg["model"], role

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
        # Derived from the registry (first role's pin), so a legitimate re-pin needs no edit here.
        pinned = next(iter(models.load_registry(root)["roles"].values()))["model"]
        edit_registry(root, lambda r: r["models"][pinned].update(status="deprecated"))
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


class TestAdjacentFamilyFallbacks:
    """fallback_policy.adjacent_families lets a pin fall back across one declared family
    boundary (haiku -> sonnet, fable -> opus). The positive path was untested: only the
    rejecting direction was."""

    @staticmethod
    def _model_of(reg, family):
        for mid, m in reg["models"].items():
            if m["family"] == family and m["status"] != "retired":
                return mid
        pytest.skip(f"registry has no live {family} model")

    @pytest.mark.parametrize("pin_family,fallback_family", [("haiku", "sonnet"), ("fable", "opus")])
    def test_declared_adjacent_family_fallback_is_accepted(self, tmp_path, reg, pin_family, fallback_family):
        assert fallback_family in reg["fallback_policy"]["adjacent_families"][pin_family]
        pin, fb = self._model_of(reg, pin_family), self._model_of(reg, fallback_family)
        root = make_tree(tmp_path)
        role = next(iter(reg["roles"]))
        edit_registry(root, lambda r: r["roles"][role].update(model=pin, fallback=[fb]))
        errors, _ = models.check(root)
        assert not any("crosses family" in e for e in errors), errors

    @pytest.mark.parametrize("pin_family,fallback_family", [("sonnet", "haiku"), ("opus", "fable")])
    def test_adjacency_is_directional(self, tmp_path, reg, pin_family, fallback_family):
        pin, fb = self._model_of(reg, pin_family), self._model_of(reg, fallback_family)
        root = make_tree(tmp_path)
        role = next(iter(reg["roles"]))
        edit_registry(root, lambda r: r["roles"][role].update(model=pin, fallback=[fb]))
        errors, _ = models.check(root)
        assert any("crosses family" in e for e in errors), errors


class TestFamilyFloor:
    """Per-family min_pin: pins must be >= the floor, fallbacks are exempt."""

    @staticmethod
    def _reg(**fams):
        return {
            "families": {f: ({"min_pin": m} if m else {}) for f, m in fams.items()},
            "models": {
                "claude-sonnet-5": {"family": "sonnet"},
                "claude-sonnet-5.5": {"family": "sonnet"},
                "claude-sonnet-5.10": {"family": "sonnet"},
                "claude-haiku-4.5": {"family": "haiku"},
            },
        }

    @pytest.mark.parametrize("model,below", [
        ("claude-sonnet-5", True),        # 5.0 < 5.5
        ("claude-sonnet-5.5", False),     # exactly the floor is allowed
        ("claude-sonnet-5.10", False),    # numeric, not lexical: 5.10 > 5.5
    ])
    def test_numeric_comparison(self, model, below):
        reg = self._reg(sonnet="claude-sonnet-5.5", haiku=None)
        assert (models._below_min_pin(reg, model) is not None) is below

    def test_family_without_floor_is_never_below(self):
        reg = self._reg(sonnet="claude-sonnet-5.5", haiku=None)
        assert models._below_min_pin(reg, "claude-haiku-4.5") is None

    def test_unknown_model_is_not_reported_as_below(self):
        assert models._below_min_pin(self._reg(sonnet="claude-sonnet-5.5"), "claude-nope-1") is None

    def test_real_registry_floors_match_the_directive(self, reg):
        # INTENTIONAL LOCK: the floors are a policy directive, not derived data. Changing
        # one is a deliberate SPEC-level decision, so this test is meant to be edited
        # together with it (unlike the pin tests, which are registry-driven).
        assert reg["families"]["sonnet"]["min_pin"] == "claude-sonnet-5.5"
        assert reg["families"]["opus"]["min_pin"] == "claude-opus-5.5"

    def test_real_registry_pins_all_meet_floor(self, reg):
        for role, cfg in reg["roles"].items():
            assert models._below_min_pin(reg, cfg["model"]) is None, role

    @pytest.mark.parametrize("role,low", [
        ("senior-engineer", "claude-sonnet-5"),
        ("principal-engineer", "claude-opus-5"),
    ])
    def test_pin_below_floor_is_a_check_error(self, tmp_path, role, low):
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["roles"][role].update(model=low))
        errors, _ = models.check(root)
        assert any(f"roles.{role}.model" in e and "min_pin" in e for e in errors), errors
        assert cli("check", root=root).returncode == 1

    def test_fallbacks_below_floor_are_allowed(self, reg):
        """The shipped fallback chains deliberately sit below the floor and must stay valid."""
        below = [(role, fb) for role, cfg in reg["roles"].items() for fb in cfg["fallback"]
                 if models._below_min_pin(reg, fb)]
        assert below, "expected at least one fallback below its family floor"
        errors, _ = models.check(REPO_ROOT)
        assert errors == []

    def test_raising_the_floor_above_a_pin_fails_check(self, tmp_path):
        root = make_tree(tmp_path)
        def mutate(r):
            hi = copy.deepcopy(r["models"]["claude-sonnet-5.5"])
            hi["ids"] = {"claude": "claude-sonnet-5-10", "copilot": "claude-sonnet-5.10", "opencode": "claude-sonnet-5-10"}
            hi["cli_accepted"] = {"date": hi["cli_accepted"]["date"], "modelusage_key": "claude-sonnet-5-10"}
            r["models"]["claude-sonnet-5.10"] = hi
            r["families"]["sonnet"]["min_pin"] = "claude-sonnet-5.10"
        edit_registry(root, mutate)
        errors, _ = models.check(root)
        assert any("roles." in e and "is below its family's min_pin" in e for e in errors), errors
        assert not any("families.sonnet.min_pin" in e for e in errors), errors

    # C7: the floor itself is validated, never silently ignored.
    @pytest.mark.parametrize("floor,needle", [
        ("claude-opus-5-5", "not a canonical"),        # hyphen typo
        ("claude-opus-5.55", "not in models"),         # well-formed but unknown
        ("claude-sonnet-5.5", "family"),               # real model, wrong family
        ("claude-opus-4.8", "retired"),                # same family, retired (set in mutate)
    ])
    def test_malformed_floor_is_a_check_error(self, tmp_path, floor, needle):
        root = make_tree(tmp_path)

        def mutate(r):
            if needle == "retired":
                r["models"]["claude-opus-4.8"]["status"] = "retired"
                for cfg in r["roles"].values():
                    cfg["fallback"] = [f for f in cfg["fallback"] if f != "claude-opus-4.8"]
            r["families"]["opus"]["min_pin"] = floor
        edit_registry(root, mutate)
        errors, _ = models.check(root)
        assert any("families.opus.min_pin" in e and needle in e for e in errors), errors
        assert cli("check", root=root).returncode == 1

    def test_floor_typo_with_low_pin_cannot_pass(self, tmp_path):
        """Probe repro: hyphen-typo floor + a pin below the real floor must not yield 0 errors."""
        root = make_tree(tmp_path)

        def mutate(r):
            r["families"]["opus"]["min_pin"] = "claude-opus-5-5"
            r["roles"]["principal-engineer"]["model"] = "claude-opus-4.6"
            r["pin_history"].append({"date": "2026-10-03", "role": "principal-engineer", "from": "claude-opus-5.5",
                                     "to": "claude-opus-4.6", "approval": "test"})
        edit_registry(root, mutate)
        errors, _ = models.check(root)
        assert any("families.opus.min_pin" in e for e in errors), errors

    def test_cross_family_floor_gives_one_clear_error(self, tmp_path):
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["families"]["sonnet"].update(min_pin="claude-opus-9.9"))
        errors, _ = models.check(root)
        assert any("families.sonnet.min_pin" in e for e in errors), errors
        assert not any("roles." in e and "below its family's min_pin" in e for e in errors), errors

    def test_valid_floor_still_passes(self, tmp_path):
        root = make_tree(tmp_path)
        edit_registry(root, lambda r: r["families"]["opus"].update(min_pin="claude-opus-5"))
        cli("sync", root=root)  # docs/MODELS.md renders the floor
        assert models.check(root)[0] == []

    def test_below_min_pin_raises_on_malformed_floor(self):
        reg = {"families": {"opus": {"min_pin": "claude-opus-5-5"}}, "models": {"claude-opus-4.6": {"family": "opus"}}}
        with pytest.raises(ValueError):
            models._below_min_pin(reg, "claude-opus-4.6")

    # C8: status 'fallback' is never a pin.
    @pytest.mark.parametrize("role,model", [
        ("engineer", "claude-haiku-4.5"),            # family without a floor
        ("senior-engineer", "claude-sonnet-5"),      # floored family
        ("principal-engineer", "claude-opus-5"),
    ])
    def test_fallback_status_pin_is_an_error(self, tmp_path, role, model):
        root = make_tree(tmp_path)

        def mutate(r):
            prev = [e["to"] for e in r["pin_history"] if e["role"] == role][-1]
            r["models"][model]["status"] = "fallback"
            r["roles"][role]["model"] = model
            r["roles"][role]["fallback"] = [f for f in r["roles"][role]["fallback"] if f != model]
            if not r["roles"][role]["fallback"]:
                r["roles"][role]["fallback"] = ["claude-sonnet-4.6" if role != "engineer" else "claude-sonnet-5"]
            r["pin_history"].append({"date": "2026-10-03", "role": role, "from": prev, "to": model, "approval": "test"})
        edit_registry(root, mutate)
        errors, _ = models.check(root)
        assert any(f"roles.{role}.model" in e and "fallback" in e and "never a pin" in e for e in errors), errors

    def test_fallback_status_model_in_chain_is_valid(self, reg):
        chained = {f for c in reg["roles"].values() for f in c["fallback"]}
        assert any(reg["models"][f]["status"] == "fallback" for f in chained)
        assert models.check(REPO_ROOT)[0] == []


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
