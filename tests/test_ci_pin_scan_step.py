"""
tests/test_ci_pin_scan_step.py - the CI "Model Pin Approval Scan" step on push events.

For a direct push to the default branch (or a squash/merge result) origin/main..HEAD is empty,
so the step must scan the pushed range instead, using github.event.before as the base. That
value is attacker-influenced input: it reaches the script only through `env:`, never through
`${{ }}` inside `run:`. The step's `run:` text is extracted from ci.yml and executed against a
real scratch repo, so the test exercises exactly what CI runs.
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.test_check_pin_trailers import (  # noqa: F401
    ALT_PIN, ALT2_PIN, SCRIPT, TRAILER, branch, commit, git, pin_commit, scan_repo, touch_commit,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STEP_NAME = "Model Pin Approval Scan"
ZERO = "0" * 40


def load_step():
    wf = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    steps = [s for job in wf["jobs"].values() for s in job.get("steps", []) if s.get("name") == STEP_NAME]
    assert len(steps) == 1, "expected exactly one %r step" % STEP_NAME
    return steps[0]


def run_step(repo, base_env):
    """Run the step's script in *repo*; scripts/ is made available as in a checkout."""
    step = load_step()
    scripts = repo / "scripts"
    scripts.mkdir(exist_ok=True)
    for name in ("check_pin_trailers.py", "models.py"):
        (scripts / name).write_text((REPO_ROOT / "scripts" / name).read_text())
    env = {k: v for k, v in os.environ.items() if k != "MODEL_PIN_SCAN_BASE"}
    env.update(base_env)
    return subprocess.run(["bash", "-eo", "pipefail", "-c", step["run"]], cwd=repo, capture_output=True,
                          text=True, timeout=60, env=env)


class TestStepIsInjectionSafe:
    def test_run_script_has_no_expression_interpolation(self):
        assert "${{" not in load_step()["run"]

    def test_event_before_reaches_the_script_only_through_env(self):
        step = load_step()
        env_text = " ".join(str(v) for v in (step.get("env") or {}).values())
        assert "github.event.before" in env_text
        assert "MODEL_PIN_SCAN_BASE" in (step.get("env") or {})

    def test_hostile_base_value_is_not_executed(self, tmp_path):
        repo = scan_repo(tmp_path)
        marker = tmp_path / "pwned"
        res = run_step(repo, {"MODEL_PIN_SCAN_BASE": "x; touch %s; #" % marker})
        assert not marker.exists()
        assert res.returncode == 0  # unresolvable base falls back (nothing to scan on origin/main..HEAD)


class TestPushRange:
    def push_with_unapproved_pin(self, tmp_path):
        """A direct push to main: origin/main already equals HEAD, only `before` is older."""
        repo = scan_repo(tmp_path)
        before = git(repo, "rev-parse", "HEAD").stdout.strip()
        pin_commit(repo, ALT_PIN, "feat: re-pin without approval")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")  # main now == HEAD
        return repo, before

    def test_default_base_alone_misses_the_push(self, tmp_path):
        repo, _ = self.push_with_unapproved_pin(tmp_path)
        res = subprocess.run(["python3", str(SCRIPT), "--base", "origin/main", "--head", "HEAD"],
                             cwd=repo, capture_output=True, text=True)
        assert res.returncode == 0 and "0 commit(s) checked" in res.stdout  # the hole being closed

    def test_step_with_pre_push_sha_flags_unapproved_pin(self, tmp_path):
        repo, before = self.push_with_unapproved_pin(tmp_path)
        res = run_step(repo, {"MODEL_PIN_SCAN_BASE": before})
        assert res.returncode == 1, res.stdout + res.stderr
        assert "re-pin" not in res.stdout  # message text is never echoed

    def test_step_with_pre_push_sha_passes_approved_pin(self, tmp_path):
        repo = scan_repo(tmp_path)
        before = git(repo, "rev-parse", "HEAD").stdout.strip()
        pin_commit(repo, ALT_PIN, "feat: re-pin\n\n" + TRAILER)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        res = run_step(repo, {"MODEL_PIN_SCAN_BASE": before})
        assert res.returncode == 0, res.stdout + res.stderr
        assert "1 commit(s) checked" in res.stdout

    def test_squash_merge_result_on_main_is_scanned(self, tmp_path):
        repo = scan_repo(tmp_path)
        before = git(repo, "rev-parse", "HEAD").stdout.strip()
        base = branch(repo)
        git(repo, "checkout", "-q", "-b", "feat")
        pin_commit(repo, ALT_PIN, "feat: re-pin")
        git(repo, "checkout", "-q", base)
        git(repo, "merge", "--squash", "feat")
        commit(repo, "squash: feat (#1)")  # trailer lost in the squash
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        assert run_step(repo, {"MODEL_PIN_SCAN_BASE": before}).returncode == 1

    def test_merge_commit_push_is_scanned(self, tmp_path):
        repo = scan_repo(tmp_path)
        before = git(repo, "rev-parse", "HEAD").stdout.strip()
        base = branch(repo)
        git(repo, "checkout", "-q", "-b", "feat")
        pin_commit(repo, ALT_PIN, "feat: re-pin")
        git(repo, "checkout", "-q", base)
        touch_commit(repo)
        git(repo, "merge", "--no-ff", "-q", "-m", "Merge feat", "feat")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        assert run_step(repo, {"MODEL_PIN_SCAN_BASE": before}).returncode == 1

    @pytest.mark.parametrize("base", ["", ZERO])
    def test_empty_or_all_zero_base_falls_back_to_origin_main(self, tmp_path, base):
        """A new branch push (before = 0000...) must not crash and still scans origin/main..HEAD."""
        repo = scan_repo(tmp_path)
        pin_commit(repo, ALT_PIN, "feat: re-pin")  # origin/main stays at the seed commit
        res = run_step(repo, {"MODEL_PIN_SCAN_BASE": base})
        assert res.returncode == 1, res.stdout + res.stderr

    def test_unknown_before_sha_falls_back_instead_of_skipping(self, tmp_path):
        """A force-push can leave `before` absent from the clone: do not silently pass."""
        repo = scan_repo(tmp_path)
        pin_commit(repo, ALT_PIN, "feat: re-pin")
        res = run_step(repo, {"MODEL_PIN_SCAN_BASE": "1" * 40})
        assert res.returncode == 1, res.stdout + res.stderr
