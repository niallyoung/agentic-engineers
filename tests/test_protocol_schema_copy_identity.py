"""
Guards against drift between the two copies of the canonical protocol schema.

docs/specs/protocol-core-v1.0.yaml is the single normative, EDITABLE source
(see its own header comment for the full precedence chain). The
protocol-validator skill ships a byte-identical copy at
src/skills/protocol-validator/schema/protocol-core-v1.0.yaml so schema
resolution works when the skill is installed into a harness directory
outside the repo (see protocol_validator.py's ProtocolValidator docstring
for the resolution order). Nothing automatically keeps these two files in
sync — this test is the cheap guard that fails loudly the moment they do.

If this test fails: copy docs/specs/protocol-core-v1.0.yaml over the
skill-local copy (never the reverse — the repo-root file is the editable
source of truth) and re-run.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "docs" / "specs" / "protocol-core-v1.0.yaml"
SKILL_LOCAL = REPO_ROOT / "src" / "skills" / "protocol-validator" / "schema" / "protocol-core-v1.0.yaml"


def test_both_schema_copies_exist():
    assert CANONICAL.exists(), f"Canonical schema missing: {CANONICAL}"
    assert SKILL_LOCAL.exists(), f"Skill-local schema copy missing: {SKILL_LOCAL}"


def test_skill_local_schema_copy_is_byte_identical_to_canonical():
    canonical_bytes = CANONICAL.read_bytes()
    skill_local_bytes = SKILL_LOCAL.read_bytes()
    assert canonical_bytes == skill_local_bytes, (
        "src/skills/protocol-validator/schema/protocol-core-v1.0.yaml has drifted "
        "from docs/specs/protocol-core-v1.0.yaml. Copy the canonical file over the "
        "skill-local copy: "
        "cp docs/specs/protocol-core-v1.0.yaml "
        "src/skills/protocol-validator/schema/protocol-core-v1.0.yaml"
    )
