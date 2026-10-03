#!/usr/bin/env python3
"""
scripts/check_pin_trailers.py - Model Pin Change approval scanner.

docs/SPEC.md (Model Pin Change): every commit that changes a role's pin
(roles.<role>.model in config/models.yaml) must carry a non-empty
`Model-Pin-Approved-By:` trailer at the START of a line in its message.

This is the single scanner used by the CI "Model Pin Approval Scan" step and by
.githooks/pre-push. It is the authoritative backstop for the commit-msg hook, which
`git commit --no-verify`, rebases and merges can bypass.

Usage:
    scripts/check_pin_trailers.py [--base REF] [--head REF]

Scans every commit in <base>..<head> (default origin/main..HEAD), merges included:

  * normal commit: its pins are compared with its parent's;
  * merge commit: its pins are compared with its FIRST parent's. A change there is
    accepted when the merge message carries the trailer, or when each changed role's new
    pin is exactly the pin of another parent (a side branch), because the commits that
    introduced it on that side are scanned (or are already in <base>). A pin that
    matches no parent (conflict resolution, "evil" merge) needs the trailer on the merge;
  * the commit that first introduces config/models.yaml is not a pin change;
  * a revert that restores a previous pin is still a pin change (and says so).

Output names only the short SHA and role(s): commit messages and model IDs are never
echoed. Annotations (`::error::`) are emitted only when GITHUB_ACTIONS=true.

Exit codes: 0 ok (or base ref not found: notice, nothing scanned), 1 unapproved pin
change found, 2 environment/usage problem (PyYAML or git unavailable, bad --head).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import models  # exits 2 with a clear message when PyYAML is missing
except SystemExit as exc:
    sys.stderr.write("error: PyYAML unavailable, cannot scan model pin changes "
                     "(python3 -m pip install pyyaml)\n")
    raise SystemExit(2) from exc

REGISTRY = "config/models.yaml"
# Line-start only: a mid-line mention, an indented line or an empty value is not approval.
TRAILER = re.compile(r"^Model-Pin-Approved-By:[ \t]*\S", re.MULTILINE)
REVERT = re.compile(r'^Revert "|^This reverts commit [0-9a-f]{7,40}', re.MULTILINE)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def fatal(msg: str) -> "None":
    sys.stderr.write("error: %s\n" % msg)
    raise SystemExit(2)


_PIN_CACHE: dict[str, dict] = {}


def blob_id(rev: str) -> str | None:
    r = git("rev-parse", "--verify", "-q", "%s:%s" % (rev, REGISTRY))
    return r.stdout.strip() if r.returncode == 0 else None


def pins_of(blob: str | None) -> dict:
    """roles.<role>.model for a registry blob ({} when absent or unparseable)."""
    if blob is None:
        return {}
    if blob in _PIN_CACHE:
        return _PIN_CACHE[blob]
    text = git("cat-file", "blob", blob).stdout
    result: dict = {}
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "config"))
        with open(os.path.join(root, REGISTRY), "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            reg = models.load_registry(root)
            result = {r: (c or {}).get("model") for r, c in (reg.get("roles") or {}).items()}
        except models.RegistryError:
            result = {}
    _PIN_CACHE[blob] = result
    return result


def changed_roles(old: dict, new: dict) -> list[str]:
    return [r for r in sorted(set(old) | set(new)) if old.get(r) != new.get(r)]


def check_commit(sha: str, parents: list[str]):
    """Return (kind, roles, message) for an unapproved pin change, else None."""
    if not parents:
        return None  # root commit: it introduces the registry, if at all
    first = parents[0]
    old_blob, new_blob = blob_id(first), blob_id(sha)
    if old_blob is None:
        return None  # the registry is introduced here: seeding it is not a pin change
    if old_blob == new_blob:
        return None
    old, new = pins_of(old_blob), pins_of(new_blob)
    roles = changed_roles(old, new)
    if not roles:
        return None
    msg = git("log", "-1", "--format=%B", sha).stdout
    if TRAILER.search(msg):
        return None
    is_merge = len(parents) > 1
    if is_merge:
        side_pins = [pins_of(blob_id(p)) for p in parents[1:]]
        roles = [r for r in roles if not any(sp.get(r) == new.get(r) for sp in side_pins)]
        if not roles:
            return None
    kind = "merge" if is_merge else ("revert" if REVERT.search(msg) else "commit")
    return kind, roles


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scan commits for unapproved model pin changes.")
    ap.add_argument("--base", default="origin/main", help="exclusive lower bound (default origin/main)")
    ap.add_argument("--head", default="HEAD", help="inclusive upper bound (default HEAD)")
    args = ap.parse_args(argv)
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"

    if git("rev-parse", "--git-dir").returncode != 0:
        fatal("not inside a git repository")
    if git("rev-parse", "--verify", "-q", args.base + "^{commit}").returncode != 0:
        print("%snotice: %s not found; skipping model pin approval scan"
              % ("::notice::" if annotate else "", args.base))
        return 0
    if git("rev-parse", "--verify", "-q", args.head + "^{commit}").returncode != 0:
        fatal("head ref %r is not a commit" % args.head)

    listing = git("rev-list", "--parents", "--reverse", "%s..%s" % (args.base, args.head))
    if listing.returncode != 0:
        fatal("git rev-list failed: %s" % listing.stderr.strip())
    entries = [ln.split() for ln in listing.stdout.splitlines() if ln.strip()]

    bad = []
    for sha, *parents in entries:
        verdict = check_commit(sha, parents)
        if verdict:
            bad.append((sha[:12],) + verdict)

    notes = {
        "commit": "changes role model pin(s) %s without a Model-Pin-Approved-By trailer",
        "merge": "is a merge commit that changes role model pin(s) %s (not introduced by an "
                 "approved side commit, e.g. conflict resolution) without a Model-Pin-Approved-By "
                 "trailer on the merge",
        "revert": "is a revert that changes role model pin(s) %s without a Model-Pin-Approved-By "
                  "trailer (a revert that restores a previous pin is still a pin change and "
                  "needs approval)",
    }
    for short, kind, roles in bad:
        line = "commit %s %s" % (short, notes[kind] % ", ".join(roles))
        print(("::error::" if annotate else "error: ") + line)
    if bad:
        print("See docs/SPEC.md, Model Pin Change: add a line starting with "
              "'Model-Pin-Approved-By: <approver>' to each listed commit message.")
        return 1
    print("Model pin approval scan: %d commit(s) checked, all pin changes approved" % len(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
