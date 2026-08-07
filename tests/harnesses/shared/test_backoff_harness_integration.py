"""
Phase G-2 — Harness-specific integration tests for the backoff poller config.

Category 9 of the G-2 plan: verify that each harness's *shipped* configuration
file carries a valid G-2 backoff/idle-loop block and that
``BackoffConfig.from_settings_dict`` consumes it consistently across all three
harnesses (Claude settings.json, OpenCode opencode.jsonc, Copilot settings.json).

These tests read the real ``dist/`` (and root ``opencode.jsonc``) files, so they
also act as a regression gate: if someone removes or malforms the backoff block
in a shipped config, CI fails here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.harnesses.shared.backoff_poller import (
    BackoffConfig,
    BackoffPoller,
    DEFAULT_BACKOFF_INTERVALS,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_config_validator():
    """Load the OpenCode config_validator module directly from its file.

    We avoid ``from src.harnesses.opencode import ...`` because that package's
    ``__init__`` eagerly imports sibling modules; loading the single file keeps
    these G-2 tests insulated from unrelated harness module state.
    """
    import importlib.util
    import sys

    name = "_oc_config_validator_g2"
    path = REPO_ROOT / "src" / "harnesses" / "opencode" / "config_validator.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass field-type resolution can find the
    # module in sys.modules (required on Python 3.7).
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cv = _load_config_validator()
validate_file = _cv.validate_file
strip_jsonc = _cv.strip_jsonc


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _load_jsonc_idle_loop(path: Path) -> dict:
    # Reuse the validator's JSONC parser so comments/trailing commas are handled.
    data = json.loads(strip_jsonc(path.read_text()))
    return data["idle_loop"]


# ---------------------------------------------------------------------------
# Shared assertions
# ---------------------------------------------------------------------------


def _assert_valid_g2_config(idle_loop: dict) -> BackoffConfig:
    cfg = BackoffConfig.from_settings_dict(idle_loop)
    assert cfg.enabled is True
    # Ladder is non-empty, strictly the documented G-2 rungs when present.
    assert cfg.backoff_intervals[0] == 5
    assert cfg.max_backoff_seconds >= cfg.backoff_intervals[0]
    assert cfg.watch_poll_seconds > 0
    # Config must actually drive a poller end to end.
    poller = BackoffPoller(config=cfg, incoming_dir=None, poll=lambda: {"processed": 0})
    assert poller.level == 0
    assert poller.current_interval == cfg.backoff_intervals[0]
    return cfg


# ---------------------------------------------------------------------------
# Claude Code — settings.json
# ---------------------------------------------------------------------------


class TestClaudeSettingsIntegration:
    SETTINGS = REPO_ROOT / "dist" / "claude" / "settings.json"

    def test_settings_has_idle_loop(self):
        data = _load_json(self.SETTINGS)
        assert "idle_loop" in data

    def test_backoff_config_parses(self):
        data = _load_json(self.SETTINGS)
        cfg = _assert_valid_g2_config(data["idle_loop"])
        assert cfg.backoff_intervals == [5, 30, 180, 600]

    def test_watch_fields_present(self):
        il = _load_json(self.SETTINGS)["idle_loop"]
        assert il["watch_enabled"] is True
        assert il["watch_poll_seconds"] > 0

    def test_full_ladder_advances_to_cap(self):
        il = _load_json(self.SETTINGS)["idle_loop"]
        cfg = BackoffConfig.from_settings_dict(il)
        poller = BackoffPoller(config=cfg, incoming_dir=None, poll=lambda: {"processed": 0})
        for _ in range(6):
            poller.run_cycle()
        assert poller.current_interval == cfg.max_backoff_seconds == 600


# ---------------------------------------------------------------------------
# OpenCode — opencode.jsonc (root + dist) with validator
# ---------------------------------------------------------------------------


class TestOpenCodeConfigIntegration:
    ROOT_CONFIG = REPO_ROOT / "opencode.jsonc"
    DIST_CONFIG = REPO_ROOT / "dist" / "opencode" / "opencode.jsonc"

    @pytest.mark.parametrize("which", ["root", "dist"])
    def test_jsonc_validates_with_backoff_fields(self, which):
        path = self.ROOT_CONFIG if which == "root" else self.DIST_CONFIG
        result = validate_file(path)
        # The extra backoff_* keys must not break the OpenCode config validator.
        assert result.ok, [e.format() for e in result.errors]

    @pytest.mark.parametrize("which", ["root", "dist"])
    def test_backoff_config_parses_from_jsonc(self, which):
        path = self.ROOT_CONFIG if which == "root" else self.DIST_CONFIG
        il = _load_jsonc_idle_loop(path)
        cfg = _assert_valid_g2_config(il)
        assert cfg.backoff_intervals == [5, 30, 180, 600]

    def test_root_and_dist_agree(self):
        root = _load_jsonc_idle_loop(self.ROOT_CONFIG)
        dist = _load_jsonc_idle_loop(self.DIST_CONFIG)
        assert root.get("backoff_intervals") == dist.get("backoff_intervals")
        assert root.get("watch_enabled") == dist.get("watch_enabled")


# ---------------------------------------------------------------------------
# Copilot CLI — settings.json
# ---------------------------------------------------------------------------


class TestCopilotSettingsIntegration:
    SETTINGS = REPO_ROOT / "dist" / "copilot" / "settings.json"

    def test_settings_parses(self):
        data = _load_json(self.SETTINGS)
        assert data.get("harness") == "copilot"
        assert "idle_loop" in data

    def test_backoff_config_parses(self):
        il = _load_json(self.SETTINGS)["idle_loop"]
        cfg = _assert_valid_g2_config(il)
        assert cfg.backoff_intervals == [5, 30, 180, 600]

    def test_type_validation_bool_int_str(self):
        il = _load_json(self.SETTINGS)["idle_loop"]
        assert isinstance(il["enabled"], bool)
        assert all(isinstance(x, int) for x in il["backoff_intervals"])
        assert isinstance(il["skill"], str)


# ---------------------------------------------------------------------------
# Cross-harness consistency
# ---------------------------------------------------------------------------


class TestCrossHarnessConsistency:
    def test_all_three_harnesses_same_ladder(self):
        claude = _load_json(REPO_ROOT / "dist" / "claude" / "settings.json")["idle_loop"]
        copilot = _load_json(REPO_ROOT / "dist" / "copilot" / "settings.json")["idle_loop"]
        opencode = _load_jsonc_idle_loop(REPO_ROOT / "dist" / "opencode" / "opencode.jsonc")

        ladders = [
            BackoffConfig.from_settings_dict(h).backoff_intervals
            for h in (claude, copilot, opencode)
        ]
        assert ladders[0] == ladders[1] == ladders[2] == DEFAULT_BACKOFF_INTERVALS

    def test_all_three_enable_watch(self):
        for path, loader in [
            (REPO_ROOT / "dist" / "claude" / "settings.json", _load_json),
            (REPO_ROOT / "dist" / "copilot" / "settings.json", _load_json),
        ]:
            il = loader(path)["idle_loop"]
            assert BackoffConfig.from_settings_dict(il).watch_enabled is True
        oc = _load_jsonc_idle_loop(REPO_ROOT / "dist" / "opencode" / "opencode.jsonc")
        assert BackoffConfig.from_settings_dict(oc).watch_enabled is True
