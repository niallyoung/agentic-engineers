#!/usr/bin/env python3
"""
scripts/check_pin_history.py - advisory pin_history audit scanner.

config/models.yaml is the single reference table of models per role. Changing a role's
pin needs no approval trailer; the only thing audited here is that pin_history stays an
append-only record: for every commit in <base>..<head> that touches the registry, the
parent's pin_history should be an unchanged PREFIX of the child's.

This scanner is ADVISORY. A detected rewrite prints a warning and the exit code stays 0
(use --strict to exit 1 instead; hooks and CI do not use it). Registry consistency
(shape, ids, floating aliases, pin_history chain, generated artifacts) is enforced
separately and strictly by `scripts/models.py check` / `sync --check`.

Used by the CI "Model Pin History Audit (advisory)" step and .githooks/pre-push.

Usage:
    scripts/check_pin_history.py [--base REF] [--head REF] [--strict]

Output names only the short SHA: commit messages and model IDs are never echoed.
Warnings are emitted as `::warning::` when GITHUB_ACTIONS=true, else `warning: `.

Exit codes: 0 ok / warnings only / base ref not found (notice, nothing scanned);
1 only with --strict and a rewrite found; 2 environment/usage problem (PyYAML or git
unavailable, bad --head, --base/--head starting with '-').
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import models  # exits 2 with a clear message when PyYAML is missing
except SystemExit as exc:
    sys.stderr.write("error: PyYAML unavailable, cannot audit pin_history "
                     "(python3 -m pip install pyyaml)\n")
    raise SystemExit(2) from exc

REGISTRY = "config/models.yaml"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def fatal(msg: str) -> "None":
    sys.stderr.write("error: %s\n" % msg)
    raise SystemExit(2)


_REG_CACHE: dict[str, dict | None] = {}


def blob_id(rev: str) -> str | None:
    r = git("rev-parse", "--verify", "-q", "%s:%s" % (rev, REGISTRY))
    return r.stdout.strip() if r.returncode == 0 else None


def registry_of(blob: str | None) -> dict | None:
    """Parsed registry for a blob (None when absent or unparseable)."""
    if blob is None:
        return None
    if blob in _REG_CACHE:
        return _REG_CACHE[blob]
    text = git("cat-file", "blob", blob).stdout
    reg: dict | None = None
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "config"))
        with open(os.path.join(root, REGISTRY), "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            reg = models.load_registry(root)
        except models.RegistryError:
            reg = None
    _REG_CACHE[blob] = reg
    return reg


def history_is_append_only(old_reg: dict | None, new_reg: dict | None) -> bool:
    """True when old pin_history is a prefix of new pin_history (entries only appended)."""
    old_h = list((old_reg or {}).get("pin_history") or [])
    if new_reg is None:
        return not old_h  # an unparseable child cannot be shown to preserve history
    new_h = list(new_reg.get("pin_history") or [])
    return new_h[:len(old_h)] == old_h and len(new_h) >= len(old_h)


def rewrites_history(parents: list[str], sha: str) -> bool:
    """True when this commit rewrites pin_history relative to ANY parent (a merge that
    drops or alters history carried by its second parent is noticed too)."""
    if not parents:
        return False  # root commit: it introduces the registry, if at all
    new_blob = blob_id(sha)
    for parent in parents:
        old_blob = blob_id(parent)
        if old_blob is None or old_blob == new_blob:
            continue  # registry introduced here, or identical to this parent's
        old_reg = registry_of(old_blob)
        if old_reg is None:
            continue
        if not history_is_append_only(old_reg, registry_of(new_blob)):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Advisory audit of config/models.yaml pin_history.")
    ap.add_argument("--base", default="origin/main", help="exclusive lower bound (default origin/main)")
    ap.add_argument("--head", default="HEAD", help="inclusive upper bound (default HEAD)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when a pin_history rewrite is found (default: warn only)")
    args = ap.parse_args(argv)
    for opt, val in (("--base", args.base), ("--head", args.head)):
        if val.startswith("-"):
            fatal("%s value %r must not start with '-'" % (opt, val))
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"

    if git("rev-parse", "--git-dir").returncode != 0:
        fatal("not inside a git repository")
    if git("rev-parse", "--verify", "-q", args.base + "^{commit}").returncode != 0:
        print("%snotice: %s not found; skipping pin_history audit"
              % ("::notice::" if annotate else "", args.base))
        return 0
    if git("rev-parse", "--verify", "-q", args.head + "^{commit}").returncode != 0:
        fatal("head ref %r is not a commit" % args.head)

    listing = git("rev-list", "--parents", "--reverse", "%s..%s" % (args.base, args.head))
    if listing.returncode != 0:
        fatal("git rev-list failed: %s" % listing.stderr.strip())
    entries = [ln.split() for ln in listing.stdout.splitlines() if ln.strip()]

    bad = [sha[:12] for sha, *parents in entries if rewrites_history(parents, sha)]
    for short in bad:
        print(("::warning::" if annotate else "warning: ") +
              "commit %s rewrites pin_history (existing entries should stay an unchanged "
              "prefix: append only; the audit trail is lost otherwise)" % short)
    if bad:
        return 1 if args.strict else 0
    print("Model pin history audit: %d commit(s) checked, pin_history is append-only" % len(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
