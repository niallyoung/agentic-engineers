"""tests/test_codeowners.py - .github/CODEOWNERS must cover the governance-critical paths.

Pin-change approval evidence (the Model-Pin-Approved-By trailer) is unauthenticated text;
identity binding comes from CODEOWNERS plus GitHub branch protection (GitHub-side, not
verifiable here). This test only guards the repository half: the file exists, covers
every governance path with a pattern that matches a real path, and names one well-formed owner.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEOWNERS = REPO_ROOT / ".github" / "CODEOWNERS"

REQUIRED_PATHS = [
    "/config/models.yaml",
    "/scripts/models.py",
    "/scripts/check_pin_trailers.py",
    "/.githooks/",
    "/.github/workflows/",
    "/docs/SPEC.md",
    "/docs/decisions/",
    "/renderer/scripts/",
    "/renderer/lib/",
]
HANDLE = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def _rules() -> list[tuple[str, list[str]]]:
    rules = []
    for raw in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            parts = line.split()
            rules.append((parts[0], parts[1:]))
    return rules


def test_codeowners_exists():
    assert CODEOWNERS.is_file(), ".github/CODEOWNERS is missing"


def test_every_required_path_has_a_rule():
    patterns = {p for p, _ in _rules()}
    missing = [p for p in REQUIRED_PATHS if p not in patterns]
    assert not missing, f"CODEOWNERS lacks rules for: {missing}"


def test_every_rule_pattern_matches_an_existing_path():
    for pattern, _ in _rules():
        rel = pattern.lstrip("/")
        assert (REPO_ROOT / rel.rstrip("/")).exists(), f"pattern {pattern} matches nothing in the repo"
        if pattern.endswith("/"):
            assert (REPO_ROOT / rel).is_dir(), f"{pattern} ends in / but is not a directory"


def test_owner_is_a_single_wellformed_handle():
    rules = _rules()
    assert rules, "CODEOWNERS has no rules"
    owners = {tuple(o) for _, o in rules}
    assert len(owners) == 1, f"expected one owner set for all rules, got {owners}"
    (owner_set,) = owners
    assert len(owner_set) == 1, f"expected a single owner, got {owner_set}"
    assert HANDLE.match(owner_set[0]), f"malformed owner handle: {owner_set[0]}"
