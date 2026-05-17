"""Comprehensive tests for the OpenCode config validator.

Target: ≥95 % line coverage of ``src/opencode/config_validator.py``.

Test groups
-----------
1.  ``strip_jsonc`` parser: comments, trailing commas, string safety.
2.  Schema layer: every OC0xx code has at least one positive and one
    negative test.
3.  Regression tests — each codifies a real historical incident
    documented in ``docs/OPENCODE-CONFIG-INVESTIGATION.md``.
4.  Cross-field consistency.
5.  Integrity / safety: size, sentinel, secret scan, SHA-256 digest.
6.  CLI entry point: exit codes 0 / 1 / 2 and JSON output.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

# Ensure repo root is importable when pytest is invoked from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.opencode.config_validator import (  # noqa: E402
    MAX_COMPACTION_RESERVED,
    OpenCodeConfigValidator,
    Severity,
    ValidationError,
    has_jsonc_sentinel,
    integrity_digest,
    main,
    strip_jsonc,
    validate_file,
    validate_text,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


MIN_VALID = """\
// agentic-engineers OpenCode configuration
{
  "$schema": "https://opencode.ai/config.json",
  "model": "github-copilot/claude-haiku-4.5",
  "compaction": {"auto": true, "reserved": 30000},
  "permission": {"read": "allow", "edit": "allow", "bash": "allow"},
  "agent": {"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}},
  "default_agent": "orchestrator",
  "command": {
    "sdlc-check": {
      "description": "Validate SDLC compliance",
      "agent": "orchestrator",
      "subtask": true,
      "template": "Validate SDLC workflow compliance."
    }
  },
  "provider": {
    "github-copilot": {
      "models": {
        "claude-haiku-4.5": {
          "id": "claude-haiku-4.5",
          "name": "Claude Haiku 4.5",
          "limit": {"context": 200000, "output": 8192}
        }
      }
    }
  }
}
"""


def _v(text: str):
    return validate_text(text, source_path="<inline>")


# ---------------------------------------------------------------------------
# 1. JSONC parser
# ---------------------------------------------------------------------------


class TestStripJsonc:
    def test_line_comment(self):
        assert strip_jsonc("// hi\n{}").strip() == "{}"

    def test_block_comment(self):
        assert strip_jsonc("/* c */ {}").strip() == "{}"

    def test_trailing_comma_object(self):
        assert strip_jsonc('{"a": 1,}') == '{"a": 1}'

    def test_trailing_comma_array(self):
        assert strip_jsonc('[1, 2, 3,]') == '[1, 2, 3]'

    def test_comment_inside_string_is_preserved(self):
        # The URL contains '//' but must not be treated as a line comment.
        text = '{"$schema": "https://opencode.ai/config.json"}'
        assert strip_jsonc(text) == text

    def test_escaped_quote_inside_string(self):
        text = r'{"k": "a\"b // not comment"}'
        assert strip_jsonc(text) == text

    def test_unterminated_block_comment_is_tolerated(self):
        # Should not raise; downstream JSON parse will surface the error
        assert "{}" not in strip_jsonc("/* unclosed {}")

    def test_sentinel_detection_line(self):
        assert has_jsonc_sentinel("// hi\n{}") is True

    def test_sentinel_detection_block(self):
        assert has_jsonc_sentinel("/* hi */\n{}") is True

    def test_sentinel_missing(self):
        assert has_jsonc_sentinel("{}\n") is False

    def test_sentinel_blank_lines_first(self):
        assert has_jsonc_sentinel("\n\n// hi\n{}") is True


# ---------------------------------------------------------------------------
# 2. Happy path & top-level schema
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_minimal_valid_config_passes(self):
        r = _v(MIN_VALID)
        assert r.ok, [e.format() for e in r.errors]
        assert r.strict_ok, [w.format() for w in r.warnings]
        assert r.parsed is not None
        assert r.sha256 and len(r.sha256) == 64

    def test_live_repo_config_passes(self):
        repo_cfg = Path(__file__).resolve().parents[1] / "opencode.jsonc"
        if not repo_cfg.exists():
            pytest.skip("repo opencode.jsonc not present")
        r = validate_file(repo_cfg)
        assert r.ok, "live opencode.jsonc must always validate clean: " + "\n".join(
            e.format() for e in r.errors
        )

    def test_unknown_top_level_key_warns(self):
        text = MIN_VALID.replace('"$schema"', '"unknown_root_key": 1, "$schema"')
        r = _v(text)
        codes = {w.code for w in r.warnings}
        assert "OC020" in codes


# ---------------------------------------------------------------------------
# 3. Field-level schema rules (one per OC0xx code)
# ---------------------------------------------------------------------------


def _replace(src: str, needle: str, repl: str) -> str:
    assert needle in src, f"fixture missing {needle!r}"
    return src.replace(needle, repl, 1)


class TestSchemaRules:
    def test_oc000_invalid_json(self):
        r = _v("// hdr\n{not-json")
        assert any(e.code == "OC000" for e in r.errors)
        assert not r.ok

    def test_oc001_top_level_is_array(self):
        r = _v("// hdr\n[]")
        assert any(e.code == "OC001" for e in r.errors)

    def test_oc010_too_small(self):
        r = _v("// x\n{}")
        # The "{}" config is < 32 bytes including header → OC010
        codes = {e.code for e in r.errors}
        assert "OC010" in codes

    def test_oc011_too_large(self):
        big = "// header\n{" + ('"k":"' + "x" * 1024 + '",') * 600 + '"end":1}'
        r = _v(big)
        # File far exceeds MAX_CONFIG_BYTES → OC011 warn
        assert any(w.code == "OC011" for w in r.warnings)

    def test_oc012_missing_sentinel(self):
        r = _v(MIN_VALID.split("\n", 1)[1])  # drop the comment line
        assert any(e.code == "OC012" for e in r.errors)

    def test_oc013_secret_detection(self):
        text = _replace(
            MIN_VALID,
            '"model": "github-copilot/claude-haiku-4.5"',
            '"model": "github-copilot/claude-haiku-4.5",\n  "leak": "api_key: \\"AKIAABCDEFGHIJKLMNOP\\""',
        )
        r = _v(text)
        assert any(e.code == "OC013" for e in r.errors)

    def test_oc022_bad_schema_url(self):
        text = _replace(MIN_VALID, '"$schema": "https://opencode.ai/config.json"',
                        '"$schema": "not-a-url"')
        r = _v(text)
        assert any(e.code == "OC022" for e in r.errors)

    def test_oc021_missing_schema_warn(self):
        text = _replace(MIN_VALID, '"$schema": "https://opencode.ai/config.json",\n  ', "")
        r = _v(text)
        assert any(w.code == "OC021" for w in r.warnings)

    def test_oc023_instructions_wrong_type(self):
        text = _replace(MIN_VALID, '"$schema"', '"instructions": "not-a-list", "$schema"')
        r = _v(text)
        assert any(e.code == "OC023" for e in r.errors)

    def test_oc024_instructions_unsafe_path(self):
        text = _replace(MIN_VALID, '"$schema"',
                        '"instructions": ["../escape.md"], "$schema"')
        r = _v(text)
        assert any(e.code == "OC024" for e in r.errors)

    def test_oc025_default_agent_bad_name(self):
        text = _replace(MIN_VALID, '"default_agent": "orchestrator"',
                        '"default_agent": "Bad Name!"')
        r = _v(text)
        assert any(e.code == "OC025" for e in r.errors)

    def test_oc026_missing_global_model_warn(self):
        text = _replace(MIN_VALID, '"model": "github-copilot/claude-haiku-4.5",\n  ', "")
        r = _v(text)
        assert any(w.code == "OC026" for w in r.warnings)

    def test_oc027_bad_model_id(self):
        text = _replace(MIN_VALID, '"model": "github-copilot/claude-haiku-4.5"',
                        '"model": "no-provider-prefix"')
        r = _v(text)
        assert any(e.code == "OC027" for e in r.errors)

    def test_oc030_compaction_not_object(self):
        text = _replace(MIN_VALID, '"compaction": {"auto": true, "reserved": 30000}',
                        '"compaction": "no"')
        r = _v(text)
        assert any(e.code == "OC030" for e in r.errors)

    def test_oc031_compaction_auto_not_bool(self):
        text = _replace(MIN_VALID, '"auto": true, "reserved": 30000',
                        '"auto": "yes", "reserved": 30000')
        r = _v(text)
        assert any(e.code == "OC031" for e in r.errors)

    def test_oc032_compaction_reserved_negative(self):
        text = _replace(MIN_VALID, '"reserved": 30000', '"reserved": -5')
        r = _v(text)
        assert any(e.code == "OC032" for e in r.errors)

    def test_oc033_compaction_reserved_too_high(self):
        text = _replace(MIN_VALID, '"reserved": 30000',
                        f'"reserved": {MAX_COMPACTION_RESERVED + 1}')
        r = _v(text)
        assert any(w.code == "OC033" for w in r.warnings)

    def test_oc040_permission_not_object(self):
        text = _replace(MIN_VALID,
                        '"permission": {"read": "allow", "edit": "allow", "bash": "allow"}',
                        '"permission": "allow-all"')
        r = _v(text)
        assert any(e.code == "OC040" for e in r.errors)

    def test_oc041_unknown_permission_tool(self):
        text = _replace(MIN_VALID, '"read": "allow"',
                        '"read": "allow", "nuclear": "allow"')
        r = _v(text)
        assert any(w.code == "OC041" for w in r.warnings)

    def test_oc042_invalid_permission_value(self):
        text = _replace(MIN_VALID, '"read": "allow"', '"read": "maybe"')
        r = _v(text)
        assert any(e.code == "OC042" for e in r.errors)

    def test_oc050_agent_not_object(self):
        text = _replace(MIN_VALID,
                        '"agent": {"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}}',
                        '"agent": []')
        r = _v(text)
        assert any(e.code == "OC050" for e in r.errors)

    def test_oc051_invalid_agent_name(self):
        text = _replace(MIN_VALID,
                        '"agent": {"orchestrator":',
                        '"agent": {"Bad Name!":')
        # also fix the default_agent so we don't double-trip
        text = _replace(text, '"default_agent": "orchestrator"',
                        '"default_agent": "orchestrator"')  # no-op; we accept dangling default warn
        r = _v(text)
        assert any(e.code == "OC051" for e in r.errors)

    def test_oc052_agent_spec_not_object(self):
        text = _replace(MIN_VALID,
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}',
                        '"orchestrator": "haiku"')
        r = _v(text)
        assert any(e.code == "OC052" for e in r.errors)

    def test_oc053_agent_model_invalid(self):
        text = _replace(MIN_VALID,
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}',
                        '"orchestrator": {"model": "no-provider"}')
        r = _v(text)
        assert any(e.code == "OC053" for e in r.errors)

    def test_oc054_unknown_mode_warns(self):
        text = _replace(MIN_VALID,
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}',
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5", "mode": "wild"}')
        r = _v(text)
        assert any(w.code == "OC054" for w in r.warnings)

    def test_oc060_command_not_object(self):
        text = _replace(MIN_VALID, '"command": {', '"command": [{')
        # Close bracket replacement to keep JSON parseable:
        # Easier: use a different fixture.
        bad = MIN_VALID.replace(
            '"command": {\n    "sdlc-check": {\n      "description": "Validate SDLC compliance",\n      "agent": "orchestrator",\n      "subtask": true,\n      "template": "Validate SDLC workflow compliance."\n    }\n  }',
            '"command": "nope"',
        )
        r = _v(bad)
        assert any(e.code == "OC060" for e in r.errors)

    def test_oc061_invalid_command_name(self):
        text = _replace(MIN_VALID, '"sdlc-check"', '"Bad Cmd!"')
        r = _v(text)
        assert any(e.code == "OC061" for e in r.errors)

    def test_oc062_command_spec_not_object(self):
        text = _replace(
            MIN_VALID,
            '"sdlc-check": {\n      "description": "Validate SDLC compliance",\n      "agent": "orchestrator",\n      "subtask": true,\n      "template": "Validate SDLC workflow compliance."\n    }',
            '"sdlc-check": "go"',
        )
        r = _v(text)
        assert any(e.code == "OC062" for e in r.errors)

    def test_oc064_command_template_empty(self):
        text = _replace(MIN_VALID, '"template": "Validate SDLC workflow compliance."',
                        '"template": "   "')
        r = _v(text)
        assert any(e.code == "OC064" for e in r.errors)

    def test_oc065_missing_description_warns(self):
        text = _replace(MIN_VALID,
                        '"description": "Validate SDLC compliance",\n      ', "")
        r = _v(text)
        assert any(w.code == "OC065" for w in r.warnings)

    def test_oc066_command_agent_bad_name(self):
        text = _replace(MIN_VALID, '"agent": "orchestrator",\n      "subtask": true',
                        '"agent": "Bad!",\n      "subtask": true')
        r = _v(text)
        assert any(e.code == "OC066" for e in r.errors)

    def test_oc067_subtask_not_bool(self):
        text = _replace(MIN_VALID, '"subtask": true', '"subtask": "yes"')
        r = _v(text)
        assert any(e.code == "OC067" for e in r.errors)

    def test_oc070_provider_not_object(self):
        bad = MIN_VALID.replace('"provider": {', '"provider": "github-copilot", "x": {', 1)
        # easier: build minimal config
        cfg = '// h\n{"$schema":"https://x.test","model":"a/b","provider":"oops"}'
        r = _v(cfg)
        assert any(e.code == "OC070" for e in r.errors)

    def test_oc072_models_not_object(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b",'
               '"provider":{"a":{"models":"no"}}}')
        r = _v(cfg)
        assert any(e.code == "OC072" for e in r.errors)

    def test_oc073_model_spec_not_object(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b",'
               '"provider":{"a":{"models":{"b":"no"}}}}')
        r = _v(cfg)
        assert any(e.code == "OC073" for e in r.errors)

    def test_oc074_id_mismatch_warns(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b",'
               '"provider":{"a":{"models":{"b":{"id":"c","name":"n"}}}}}')
        r = _v(cfg)
        assert any(w.code == "OC074" for w in r.warnings)

    def test_oc075_missing_required_model_field(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b",'
               '"provider":{"a":{"models":{"b":{"id":"b"}}}}}')  # missing "name"
        r = _v(cfg)
        assert any(e.code == "OC075" for e in r.errors)

    def test_oc077_limit_not_positive_int(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b","provider":{"a":{"models":{"b":'
               '{"id":"b","name":"n","limit":{"context":0,"output":8}}}}}}')
        r = _v(cfg)
        assert any(e.code == "OC077" for e in r.errors)

    def test_oc076_limit_not_object(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b","provider":{"a":{"models":{"b":'
               '{"id":"b","name":"n","limit":"no"}}}}}')
        r = _v(cfg)
        assert any(e.code == "OC076" for e in r.errors)

    def test_oc078_cost_not_object(self):
        cfg = ('// h\n{"$schema":"https://x.test","model":"a/b","provider":{"a":{"models":{"b":'
               '{"id":"b","name":"n","cost":"cheap"}}}}}')
        r = _v(cfg)
        assert any(e.code == "OC078" for e in r.errors)


# ---------------------------------------------------------------------------
# 4. Cross-field consistency
# ---------------------------------------------------------------------------


class TestCrossRefs:
    def test_oc080_default_agent_not_declared(self):
        text = _replace(MIN_VALID, '"default_agent": "orchestrator"',
                        '"default_agent": "ghost"')
        r = _v(text)
        assert any(w.code == "OC080" for w in r.warnings)

    def test_oc081_command_agent_undeclared(self):
        text = _replace(MIN_VALID, '"agent": "orchestrator",\n      "subtask": true',
                        '"agent": "ghost",\n      "subtask": true')
        r = _v(text)
        assert any(e.code == "OC081" for e in r.errors)

    def test_oc082_global_model_not_in_provider(self):
        # Swap the global model so it doesn't match any declared provider model
        text = _replace(MIN_VALID, '"model": "github-copilot/claude-haiku-4.5",',
                        '"model": "openai/gpt-5",')
        # also update orchestrator's per-agent model to a declared one
        text = _replace(text,
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}',
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}')
        r = _v(text)
        assert any(w.code == "OC082" for w in r.warnings)

    def test_oc083_agent_model_not_in_provider(self):
        text = _replace(MIN_VALID,
                        '"orchestrator": {"model": "github-copilot/claude-haiku-4.5"}',
                        '"orchestrator": {"model": "openai/gpt-5"}')
        r = _v(text)
        assert any(w.code == "OC083" for w in r.warnings)


# ---------------------------------------------------------------------------
# 5. Historical incident regression
# ---------------------------------------------------------------------------


class TestHistoricalIncidents:
    """One test per documented historical incident — see
    docs/OPENCODE-CONFIG-INVESTIGATION.md."""

    def test_incident_2026_05_17_missing_template(self):
        """Incident: ConfigInvalidError, 4/5 requests failed.

        Root cause: ``command.*`` entries omitted the ``template`` field.
        This regression test MUST catch that exact misconfiguration.
        """
        text = _replace(MIN_VALID,
                        '      "subtask": true,\n      "template": "Validate SDLC workflow compliance."',
                        '      "subtask": true')
        r = _v(text)
        assert not r.ok
        assert any(e.code == "OC063" for e in r.errors), \
            "missing-template regression rule (OC063) failed to fire"

    def test_incident_jsonc_sentinel_required(self):
        """Incident (commit 54b7d05): missing comment sentinel → strict schema
        check rejected the file. Validator must enforce a leading comment."""
        body = MIN_VALID.split("\n", 1)[1]
        r = _v(body)
        assert any(e.code == "OC012" for e in r.errors)

    def test_incident_orchestrator_default_agent_undeclared(self):
        """Incident (commit 91c34ae & follow-ups): ``default_agent`` set to an
        agent not present in the ``agent`` block. Validator warns."""
        text = _replace(MIN_VALID, '"default_agent": "orchestrator"',
                        '"default_agent": "missing"')
        r = _v(text)
        assert any(w.code == "OC080" for w in r.warnings)


# ---------------------------------------------------------------------------
# 6. File I/O & integrity
# ---------------------------------------------------------------------------


class TestFileIO:
    def test_validate_file_missing(self, tmp_path):
        r = validate_file(tmp_path / "nope.jsonc")
        assert not r.ok
        assert any(e.code == "OC999" for e in r.errors)

    def test_validate_file_roundtrip(self, tmp_path):
        p = tmp_path / "opencode.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")
        r = validate_file(p)
        assert r.ok
        assert r.sha256 == integrity_digest(p)

    def test_validate_file_io_error(self, tmp_path, monkeypatch):
        p = tmp_path / "opencode.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")

        real_read = Path.read_text

        def boom(self, *a, **k):
            if self == p:
                raise OSError("disk on fire")
            return real_read(self, *a, **k)

        monkeypatch.setattr(Path, "read_text", boom)
        r = validate_file(p)
        assert any(e.code == "OC998" for e in r.errors)

    def test_integrity_digest_stable(self, tmp_path):
        p = tmp_path / "c.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")
        d1, d2 = integrity_digest(p), integrity_digest(p)
        assert d1 == d2
        assert len(d1) == 64

    def test_result_to_dict_serialisable(self):
        r = _v(MIN_VALID)
        d = r.to_dict()
        json.dumps(d)  # must be serialisable
        assert d["ok"] is True


# ---------------------------------------------------------------------------
# 7. Validation result helpers / dataclasses
# ---------------------------------------------------------------------------


class TestResult:
    def test_error_format_contains_code(self):
        e = ValidationError(code="OCXXX", severity=Severity.ERROR,
                            message="msg", path="a.b", hint="hint")
        s = e.format()
        assert "OCXXX" in s and "a.b" in s and "hint" in s

    def test_warn_format(self):
        e = ValidationError(code="OCXXX", severity=Severity.WARN, message="m")
        assert "⚠" in e.format() or "WARN" in e.format() or "OCXXX" in e.format()

    def test_info_format(self):
        e = ValidationError(code="OCXXX", severity=Severity.INFO, message="m")
        assert "OCXXX" in e.format()

    def test_strict_ok_with_only_warnings(self):
        text = _replace(MIN_VALID, '"description": "Validate SDLC compliance",\n      ', "")
        r = _v(text)
        assert r.ok
        assert not r.strict_ok

    def test_all_findings_includes_info(self):
        r = _v(MIN_VALID)
        # Manually push an info finding to exercise the helper
        r.add(ValidationError(code="OC900", severity=Severity.INFO, message="i"))
        codes = {f.code for f in r.all_findings()}
        assert "OC900" in codes


# ---------------------------------------------------------------------------
# 8. CLI / module entry point
# ---------------------------------------------------------------------------


class TestCLI:
    def _run(self, *argv) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_cli_ok(self, tmp_path):
        p = tmp_path / "opencode.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")
        rc, out = self._run(str(p))
        assert rc == 0
        assert "valid" in out.lower()

    def test_cli_quiet_ok_no_output(self, tmp_path):
        p = tmp_path / "opencode.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")
        rc, out = self._run(str(p), "--quiet")
        assert rc == 0
        assert out == ""

    def test_cli_error_exit_1(self, tmp_path):
        p = tmp_path / "opencode.jsonc"
        p.write_text("// hi\n{not-json", encoding="utf-8")
        rc, out = self._run(str(p))
        assert rc == 1
        assert "OC000" in out

    def test_cli_strict_warning_exit_2(self, tmp_path):
        p = tmp_path / "opencode.jsonc"
        bad = _replace(MIN_VALID, '"description": "Validate SDLC compliance",\n      ', "")
        p.write_text(bad, encoding="utf-8")
        rc, _ = self._run(str(p), "--strict")
        assert rc == 2

    def test_cli_json_output(self, tmp_path):
        p = tmp_path / "opencode.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")
        rc, out = self._run(str(p), "--json")
        assert rc == 0
        data = json.loads(out)
        assert data["ok"] is True
        assert "sha256" in data

    def test_cli_default_path(self, tmp_path, monkeypatch):
        p = tmp_path / "opencode.jsonc"
        p.write_text(MIN_VALID, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc, _ = self._run()
        assert rc == 0


# ---------------------------------------------------------------------------
# 9. Edge-case smoke
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_command_block_is_fine(self):
        text = _replace(
            MIN_VALID,
            '"command": {\n    "sdlc-check": {\n      "description": "Validate SDLC compliance",\n      "agent": "orchestrator",\n      "subtask": true,\n      "template": "Validate SDLC workflow compliance."\n    }\n  }',
            '"command": {}',
        )
        r = _v(text)
        assert r.ok, [e.format() for e in r.errors]

    def test_missing_provider_block_is_fine(self):
        text = MIN_VALID.split('"provider"')[0].rstrip(", \n") + "\n}\n"
        # Build a minimal config without provider block
        cfg = ('// hdr\n{"$schema":"https://opencode.ai/config.json",'
               '"model":"github-copilot/claude-haiku-4.5"}')
        r = _v(cfg)
        # No errors, may have warnings about missing sections
        assert r.ok
