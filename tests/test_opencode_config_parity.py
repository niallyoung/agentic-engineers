"""The checked-in root opencode.jsonc hard-codes a default model; it must follow the registry.

config/models.yaml is the single source of truth (SPEC I2). `scripts/models.py sync` does not
write opencode.jsonc, so this test is what stops it drifting on a re-pin: its top-level
`model` must be `anthropic/` plus the OpenCode render ID of the `default_agent` role's pin.
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROVIDER = "anthropic/"


def _top_level(key: str) -> str:
    text = (REPO_ROOT / "opencode.jsonc").read_text(encoding="utf-8")
    m = re.search(r'^  "%s":\s*"([^"]+)"' % re.escape(key), text, re.MULTILINE)
    assert m, f"opencode.jsonc has no top-level {key!r}"
    return m.group(1)


def test_root_opencode_model_matches_the_default_agent_pin():
    reg = yaml.safe_load((REPO_ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    role = _top_level("default_agent")
    pin = reg["roles"][role]["model"]
    expected = PROVIDER + reg["models"][pin]["ids"]["opencode"]
    assert _top_level("model") == expected, (
        f"opencode.jsonc model is out of step with the {role} pin: expected {expected}. "
        "Edit it by hand when re-pinning; it is not a sync target.")
