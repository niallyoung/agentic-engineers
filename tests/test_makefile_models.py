#!/usr/bin/env python3
"""Makefile wiring for the model registry (models-sync, models-check).

Scope: the Makefile targets exist, are documented in `make help`, are wired into
the quality gate, and `models-check` really fails on stale generated targets.
The registry's own drift/idempotence behaviour is covered by
tests/test_models_registry.py::TestSync and is deliberately not repeated here.

Anything that mutates files runs in a lightweight temp copy (just the files the
registry reads plus the Makefile; no .git, no dist/), never in the real tree.
"""

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
LOCKED_SH = REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh"

# Everything `make models-check` / `models-sync` reads.
COPY_PATHS = ["Makefile", "scripts/models.py", "config/models.yaml", "config/FRAMEWORK-MANIFEST.yaml",
              "src/AGENTS.md", "src/agents", ".githooks/LOCKED_MODELS.sh", ".agents_verification_sha",
              "docs/MODELS.md"]

_spec = importlib.util.spec_from_file_location("ae_models_makefile", REPO_ROOT / "scripts" / "models.py")
models = importlib.util.module_from_spec(_spec)
sys.modules["ae_models_makefile"] = models
_spec.loader.exec_module(models)


def make(target, cwd=REPO_ROOT):
    return subprocess.run(["make", target], cwd=cwd, capture_output=True, text=True, timeout=120)


def light_copy(dst: Path) -> Path:
    for rel in COPY_PATHS:
        src, out = REPO_ROOT / rel, dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, out) if src.is_dir() else shutil.copy2(src, out)
    return dst


@pytest.fixture(scope="module")
def help_text():
    result = make("help")
    assert result.returncode == 0, f"make help failed: {result.stderr}"
    return result.stdout


class TestMakefileModelsTargets:
    @pytest.mark.parametrize("target", ["models-sync", "models-check"])
    def test_target_is_documented_in_help(self, help_text, target):
        assert re.search(rf"^\s+{target}\s{{2,}}\S", help_text, re.MULTILINE), f"{target} not in make help"

    @pytest.mark.parametrize("target", ["models-sync", "models-check"])
    def test_target_exists_and_is_phony(self, target):
        text = MAKEFILE.read_text()
        assert re.search(rf"^{target}:", text, re.MULTILINE), f"no `{target}:` rule"
        joined = text.replace("\\\n", " ")  # fold backslash continuations
        phony = " ".join(re.findall(r"^\.PHONY:(.*)$", joined, re.MULTILINE))
        assert target in phony.split(), f"{target} missing from .PHONY"

    def test_models_check_is_wired_into_the_quality_gate(self):
        m = re.search(r"^quality-gate:(.*)$", MAKEFILE.read_text(), re.MULTILINE)
        assert m, "no quality-gate rule"
        prereqs = m.group(1).split("##")[0].split()
        assert "models-check" in prereqs

    def test_models_check_passes_on_clean_tree(self):
        """Read-only on the real tree: validates, never rewrites."""
        result = make("models-check")
        assert result.returncode == 0, f"make models-check failed: {result.stderr}\nstdout: {result.stdout}"
        assert "Model registry check passed" in result.stdout

    def test_models_check_fails_on_stale_generated_targets(self, tmp_path):
        """A LEGAL re-pin (>= family floor, with its pin_history entry) whose generated
        targets were not synced must fail purely because the targets are stale; syncing
        then makes the very same registry pass."""
        root = light_copy(tmp_path / "repo")
        reg_path = root / "config" / "models.yaml"
        reg = yaml.safe_load(reg_path.read_text())

        role, cfg = next(iter(reg["roles"].items()))
        alt = next(
            (mid for mid, m in reg["models"].items()
             if mid != cfg["model"] and m["status"] in ("current", "supported")
             and models._below_min_pin(reg, mid) is None),
            None,
        )
        assert alt, "registry offers no alternative legal pin to re-pin to"
        cfg["model"] = alt
        reg["pin_history"].append({"date": "2026-10-03", "role": role, "from": cfg_prev(reg, role),
                                   "to": alt, "approval": "test: legal re-pin without sync"})
        reg_path.write_text(yaml.safe_dump(reg, sort_keys=False))
        assert models.check(root)[0], "precondition: the unsynced tree must have errors"

        result = make("models-check", cwd=root)
        output = result.stdout + result.stderr
        assert result.returncode != 0, f"models-check passed on stale targets:\n{output}"
        assert "stale" in output, output
        for unrelated in ("min_pin", "pin_history", "not in models", "crosses family"):
            assert unrelated not in output, f"failed for the wrong reason ({unrelated}):\n{output}"

        assert make("models-sync", cwd=root).returncode == 0
        healed = make("models-check", cwd=root)
        assert healed.returncode == 0, healed.stdout + healed.stderr


def cfg_prev(reg, role):
    """The pin_history 'from' for a new entry: the latest recorded 'to' for the role."""
    return [e["to"] for e in reg["pin_history"] if e["role"] == role][-1]


class TestLockedModelsShBanner:
    def test_locked_models_sh_has_generated_banner(self):
        """Wording is owned by the generator's header template; only the contract
        (it announces being GENERATED) is asserted here."""
        assert "GENERATED" in LOCKED_SH.read_text(encoding="utf-8")

    def test_locked_models_arrays_source_correctly(self):
        """Sourcing the script yields the exported arrays."""
        result = subprocess.run(
            ["bash", "-c",
             f'source "{LOCKED_SH}" && declare -p LOCKED_MODELS | grep -q "declare -ax" '
             f'&& declare -p AGENT_MODEL_ASSIGNMENTS | grep -q "declare -ax"'],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"arrays not exported: {result.stderr}"
