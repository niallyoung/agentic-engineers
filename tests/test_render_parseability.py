"""
test_render_parseability.py — Harness-parseability suite.

Executable definition of 'widespread harness compatibility':
All distributed harness outputs must remain parseable and consistent.

Validates:
1. Markdown frontmatter (claude/copilot/opencode) — YAML parseable, name/description/model non-empty
2. TOML config (codex agents + config) — TOML parseable, model/model_reasoning_effort/developer_instructions present, NO watch_* keys
3. JSONC (opencode) — valid after comment stripping, passes strict schema validation
4. JSON settings — both settings.json model values agree with src/AGENTS.md orchestrator row

Module-scoped fixture runs `make render-all` once before all tests.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Python 3.7 compat: tomllib added in 3.11
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "dist"


@pytest.fixture(scope="module", autouse=True)
def _render_all():
    """Render every harness once before this module's tests run."""
    result = subprocess.run(
        ["make", "render-all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "make render-all failed:\n"
        f"STDOUT:\n{result.stdout[-3000:]}\n\nSTDERR:\n{result.stderr[-3000:]}"
    )
    yield


def _strip_jsonc(text: str) -> str:
    """Strip JSONC comments (// and /* */) and trailing commas, preserving strings.

    String-aware: comment markers inside JSON strings are preserved.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        # JSON string — copy verbatim, honour backslash escapes
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
            continue
        # Line comment
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        # Block comment
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            if j == -1:
                i = n
            else:
                i = j + 2
            continue
        out.append(c)
        i += 1
    stripped = "".join(out)
    # Remove trailing commas before } or ]
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    return stripped


def _get_frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between '---' delimiters) or ''.

    Standard YAML frontmatter format: --- at start and end.
    Some files have ... inside the YAML (e.g., as part of multiline strings),
    but we always look for the closing --- as the true delimiter.
    """
    if not text.startswith("---"):
        return ""
    # Look for the closing --- (must be at start of line)
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    return text[3:end]


def _parse_agents_table(agents_md: Path) -> dict[str, str]:
    """
    Parse the Agent Roster table from src/AGENTS.md.
    Returns a dict mapping role (kebab-case) to model string.
    Mirrors renderer/lib/agents_table.py's parsing.
    """
    if not agents_md.is_file():
        return {}

    agents = {}
    _row_re = re.compile(r"^\| \*\*[A-Za-z]")
    _escaped_pipe_placeholder = "__ESCAPED_PIPE__"

    for line in agents_md.read_text(encoding="utf-8").splitlines():
        if not _row_re.match(line):
            continue

        # Strip exactly one leading "| " and one trailing " |"
        body = re.sub(r"^\| ", "", line)
        body = re.sub(r" \|$", "", body)

        # Protect escaped pipes from being treated as column separators
        body = body.replace("\\|", _escaped_pipe_placeholder)
        fields = body.split("|")
        if len(fields) < 5:
            continue
        fields = [f.strip().replace(_escaped_pipe_placeholder, "|") for f in fields]

        role_raw, model, effort, description = fields[0], fields[1], fields[2], fields[4]
        role = re.sub(r"\*\*", "", role_raw).strip()
        role_kebab = role.lower().replace(" ", "-")

        if role_kebab and model and effort and description:
            agents[role_kebab] = model

    return agents


class TestRenderMarkdownParseability:
    """Test that markdown-based harnesses (claude/copilot/opencode) are parseable."""

    @pytest.mark.parametrize("harness", ["claude", "copilot", "opencode"])
    def test_rendered_agents_have_parseable_yaml_frontmatter(self, harness):
        """Every rendered agent .md must have valid YAML frontmatter with non-empty description/model."""
        agents_dir = DIST / harness / "agents"
        if not agents_dir.is_dir():
            pytest.skip(f"dist/{harness}/agents/ does not exist")

        for agent_file in agents_dir.glob("*.md"):
            text = agent_file.read_text(encoding="utf-8")
            fm = _get_frontmatter(text)
            assert fm, f"{harness}/{agent_file.name}: no YAML frontmatter"

            # Parse YAML frontmatter as-is. (Previously this stripped bare "..."
            # lines to tolerate a stray YAML document-end marker that
            # render-copilot-agents.py used to leak into the frontmatter for
            # any plain-scalar description — see FIX 1 /
            # TestCopilotFrontmatterSingleDocument below, which pins the fix
            # directly. Tolerating it here would hide a regression instead of
            # catching it, now that the root cause is fixed.)
            try:
                parsed = yaml.safe_load(fm) or {}
            except yaml.YAMLError as e:
                pytest.fail(
                    f"{harness}/{agent_file.name}: invalid YAML frontmatter: {e}"
                )

            # Verify required fields are non-empty
            # Note: different harnesses use different field names:
            #   - claude/copilot use "name" and "model"
            #   - opencode uses "role" and "model" (no explicit "name")
            # Check for description/model which are universal, plus harness-specific identity
            for field in ("description", "model"):
                val = parsed.get(field, "")
                if val is None or not isinstance(val, str):
                    val = ""
                val = val.strip()
                assert val and val != "—", (
                    f"{harness}/{agent_file.name}: {field} is empty or em-dash ('{val}')"
                )

            # Also verify there's some form of identity (name, role, or options.role)
            identity = (
                parsed.get("name") or
                parsed.get("role") or
                (parsed.get("options") or {}).get("role")
            )
            assert identity, f"{harness}/{agent_file.name}: missing identity (name/role)"


class TestCopilotFrontmatterSingleDocument:
    """FIX 1 regression pin (task-2026-08-15-fix-renderer-bugs).

    render-copilot-agents.py used to build the description field via a bare
    yaml.dump(description).strip() — for any plain-scalar description that
    doesn't need quoting, yaml.dump() appends a document-end marker
    ('...\\n') that .strip() does not remove (it only strips whitespace, not
    the literal '...' text). That leaked a stray '...' line into the middle
    of the frontmatter block. A lenient parser can silently swallow that and
    still return a (truncated) dict, so this test does not merely assert "no
    exception" — it re-parses each frontmatter block as a SINGLE YAML
    document (no cleanup/stripping of any kind) and asserts the parsed dict
    actually contains model/accepts/returns/role for all 8 rendered agents.
    """

    def test_all_copilot_agents_parse_as_single_document_with_full_fields(self):
        agents_dir = DIST / "copilot" / "agents"
        assert agents_dir.is_dir(), "dist/copilot/agents/ does not exist — run make render-all"

        agent_files = sorted(agents_dir.glob("*.agent.md"))
        assert len(agent_files) == 8, (
            f"expected 8 rendered copilot agents, found {len(agent_files)}: "
            f"{[f.name for f in agent_files]}"
        )

        for agent_file in agent_files:
            text = agent_file.read_text(encoding="utf-8")
            assert text.startswith("---\n"), f"{agent_file.name}: missing opening frontmatter delimiter"
            end = text.find("\n---\n", 4)
            assert end != -1, f"{agent_file.name}: missing closing frontmatter delimiter"
            fm_raw = text[4:end]

            # No stripping, no line filtering — exactly what a strict YAML
            # loader sees. yaml.safe_load_all() would silently treat a mid-
            # block '...' as a document boundary and only load the first
            # document; using the single-document loader (safe_load) instead
            # means a stray '...' surfaces as a hard parse error or, if it
            # happens to still parse, is caught by the field-presence checks
            # below rather than passing silently.
            documents = list(yaml.safe_load_all(fm_raw))
            assert len(documents) == 1, (
                f"{agent_file.name}: frontmatter contains {len(documents)} YAML "
                f"documents (expected exactly 1) — a stray '...' document-end "
                f"marker is mid-block. Documents: {documents}"
            )
            parsed = documents[0]
            assert isinstance(parsed, dict), f"{agent_file.name}: frontmatter did not parse to a mapping"

            for field in ("model", "accepts", "returns", "role"):
                assert field in parsed, (
                    f"{agent_file.name}: frontmatter missing '{field}' — got keys {sorted(parsed.keys())}"
                )
                assert parsed[field] not in (None, "", []), (
                    f"{agent_file.name}: field '{field}' is empty"
                )


class TestRenderTOMLParseability:
    """Test that codex agents and config files are parseable TOML without watch_* keys."""

    @pytest.mark.skipif(tomllib is None, reason="tomllib/tomli not available")
    def test_codex_agents_are_parseable_toml(self):
        """Every codex agent .toml must parse successfully and contain required fields."""
        agents_dir = DIST / "codex" / "agents"
        if not agents_dir.is_dir():
            pytest.skip("dist/codex/agents/ does not exist")

        for agent_file in agents_dir.glob("*.toml"):
            raw = agent_file.read_text(encoding="utf-8")
            try:
                parsed = tomllib.loads(raw)
            except Exception as e:
                pytest.fail(f"codex/{agent_file.name}: unparseable TOML: {e}")

            # Verify required fields
            for field in ("model", "model_reasoning_effort", "developer_instructions"):
                assert field in parsed, (
                    f"codex/{agent_file.name}: missing required field '{field}'"
                )
                val = parsed.get(field, "")
                assert val, f"codex/{agent_file.name}: {field} is empty"

            # Check for watch_* keys (should never be present)
            for key in parsed:
                assert not key.startswith("watch_"), (
                    f"codex/{agent_file.name}: prohibited key '{key}' found"
                )

    @pytest.mark.skipif(tomllib is None, reason="tomllib/tomli not available")
    def test_codex_config_files_are_parseable_toml(self):
        """Codex config.toml and agentic-engineers-orchestrator.config.toml must parse."""
        for config_name in ["config.toml", "agentic-engineers-orchestrator.config.toml"]:
            config_path = DIST / "codex" / config_name
            if not config_path.is_file():
                pytest.skip(f"dist/codex/{config_name} does not exist")

            raw = config_path.read_text(encoding="utf-8")
            try:
                parsed = tomllib.loads(raw)
            except Exception as e:
                pytest.fail(f"codex/{config_name}: unparseable TOML: {e}")

            # Verify key fields present (at least in config.toml)
            if config_name == "config.toml":
                for field in ("model", "model_reasoning_effort"):
                    assert field in parsed, (
                        f"codex/{config_name}: missing required field '{field}'"
                    )

            # Check for watch_* keys
            for key in parsed:
                assert not key.startswith("watch_"), (
                    f"codex/{config_name}: prohibited key '{key}' found"
                )


class TestOpenCodeJSONParseability:
    """Test that opencode.jsonc is valid JSON after comment stripping."""

    def test_opencode_jsonc_is_valid_json_after_stripping(self):
        """opencode.jsonc must parse to valid JSON after JSONC comment stripping."""
        jsonc_file = DIST / "opencode" / "opencode.jsonc"
        if not jsonc_file.is_file():
            pytest.skip("dist/opencode/opencode.jsonc does not exist")

        raw = jsonc_file.read_text(encoding="utf-8")
        stripped = _strip_jsonc(raw)

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"opencode/opencode.jsonc: invalid JSON after stripping comments: {e}"
            )

        # Verify it's a dict
        assert isinstance(parsed, dict), "opencode.jsonc: top-level must be a JSON object"

    def test_opencode_jsonc_passes_strict_validation(self):
        """opencode.jsonc must pass scripts/validate_opencode_config.py with strict=True."""
        jsonc_file = DIST / "opencode" / "opencode.jsonc"
        if not jsonc_file.is_file():
            pytest.skip("dist/opencode/opencode.jsonc does not exist")

        # Import validator
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            from validate_opencode_config import validate_file

            result = validate_file(str(jsonc_file), strict=True)
            assert result.strict_ok, (
                f"opencode.jsonc: validation failed (strict mode):\n"
                + "\n".join(f.format() for f in result.all_findings())
            )
        finally:
            sys.path.pop(0)


class TestSettingsJSONConsistency:
    """Test that settings.json model fields agree with src/AGENTS.md."""

    def test_settings_models_agree_with_agents_table(self):
        """
        Both dist/{claude,copilot}/settings.json must declare a model field
        that agrees with the Orchestrator model from src/AGENTS.md.
        """
        agents_table = _parse_agents_table(REPO_ROOT / "src" / "AGENTS.md")
        assert agents_table, "Could not parse src/AGENTS.md"

        orchestrator_model = agents_table.get("orchestrator")
        assert orchestrator_model, "Orchestrator model not found in src/AGENTS.md"

        for harness in ["claude", "copilot"]:
            settings_file = DIST / harness / "settings.json"
            if not settings_file.is_file():
                pytest.skip(f"dist/{harness}/settings.json does not exist")

            try:
                parsed = json.loads(settings_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                pytest.fail(f"{harness}/settings.json: invalid JSON: {e}")

            model_val = parsed.get("model", "")
            assert model_val, f"{harness}/settings.json: missing or empty 'model' field"

            # The settings.json values are often short aliases (haiku, sonnet, opus, fable)
            # or full canonical ids (claude-haiku-4.5, etc). The src/AGENTS.md row has the
            # canonical id. This test just checks they refer to the same tier/generation.
            # For now, we'll accept if either:
            #   1. They match exactly, or
            #   2. The settings.json value is a recognized short alias for the AGENTS.md model
            #
            # Example: AGENTS.md says "claude-sonnet-5", settings.json might say "sonnet".
            # This is acceptable because "sonnet" is the short form of the Orchestrator model.
            expected_tier = orchestrator_model.split("-")[1]  # e.g., "sonnet" from "claude-sonnet-5"
            if model_val != orchestrator_model and model_val != expected_tier:
                pytest.fail(
                    f"{harness}/settings.json model '{model_val}' does not match "
                    f"src/AGENTS.md orchestrator model '{orchestrator_model}' (expected tier: {expected_tier})"
                )

    def test_opencode_default_model_agrees_with_agents_table(self):
        """
        FIX 2 regression pin (task-2026-08-15-fix-renderer-bugs): dist/opencode/
        opencode.jsonc's top-level "model" (the OpenCode default model) must be
        derived from the Orchestrator's roster row in src/AGENTS.md, not a
        hardcoded literal. It was previously hardcoded to "claude-haiku-4-5"
        regardless of what the roster's orchestrator row actually said.

        opencode.jsonc's model is a fully-qualified provider-prefixed string
        whose LAST path segment is the model id (e.g. "anthropic/claude-sonnet-5",
        or "openrouter/anthropic/claude-sonnet.5" for providers that nest a
        second provider segment). map_model_opencode() also renders some
        providers (github-copilot, openrouter) in DOTTED version format
        (claude-sonnet.5) rather than the roster's hyphenated form
        (claude-sonnet-5) — this test's provider is whatever the render
        environment auto-detects (see detect_opencode_provider()), which can
        legitimately vary by machine/CI (e.g. a GITHUB_TOKEN in the test env
        flips it to github-copilot), so the comparison normalizes dots to
        hyphens and only checks the last segment rather than assuming a
        specific provider or exact string.
        """
        agents_table = _parse_agents_table(REPO_ROOT / "src" / "AGENTS.md")
        assert agents_table, "Could not parse src/AGENTS.md"

        orchestrator_model = agents_table.get("orchestrator")
        assert orchestrator_model, "Orchestrator model not found in src/AGENTS.md"

        jsonc_file = DIST / "opencode" / "opencode.jsonc"
        if not jsonc_file.is_file():
            pytest.skip("dist/opencode/opencode.jsonc does not exist")

        raw = jsonc_file.read_text(encoding="utf-8")
        parsed = json.loads(_strip_jsonc(raw))

        model_val = parsed.get("model", "")
        assert model_val, "opencode.jsonc: missing or empty 'model' field"
        assert "/" in model_val, f"opencode.jsonc: model '{model_val}' is not provider-qualified"

        model_id = model_val.rsplit("/", 1)[1]
        normalized = model_id.replace(".", "-")
        assert normalized == orchestrator_model, (
            f"opencode.jsonc model-id '{model_id}' (from '{model_val}', normalized "
            f"'{normalized}') does not match src/AGENTS.md orchestrator model "
            f"'{orchestrator_model}'"
        )


class TestMutationDetection:
    """
    Mutation tests to verify the suite catches common corruption patterns.
    These tests intentionally corrupt rendered files in a temp copy and assert
    the main tests would fail (not run in normal CI, just for verification).
    """

    def test_mutation_empty_description_caught_by_markdown_parser(self, tmp_path):
        """Verify suite catches empty description in markdown frontmatter."""
        agent_copy = tmp_path / "test-agent.md"
        agent_copy.write_text(
            "---\nname: test\nmodel: claude-haiku-4.5\ndescription: \n---\n# Content\n"
        )

        text = agent_copy.read_text(encoding="utf-8")
        fm = _get_frontmatter(text)
        parsed = yaml.safe_load(fm) or {}
        val = parsed.get("description", "")
        if val is None or not isinstance(val, str):
            val = ""
        val = val.strip()

        # This should fail the test (empty description is not valid)
        assert not (val and val != "—"), "Mutation not caught: empty description should fail"

    def test_mutation_invalid_toml_caught_by_parser(self, tmp_path):
        """Verify suite catches invalid TOML syntax."""
        if tomllib is None:
            pytest.skip("tomllib/tomli not available")

        config_copy = tmp_path / "test.toml"
        config_copy.write_text("model = \ninvalid syntax here [[[")

        raw = config_copy.read_text(encoding="utf-8")
        with pytest.raises(Exception):
            tomllib.loads(raw)

    def test_mutation_jsonc_invalid_syntax_caught(self, tmp_path):
        """Verify suite catches invalid JSON after JSONC stripping."""
        jsonc_copy = tmp_path / "test.jsonc"
        jsonc_copy.write_text('// comment\n{"key": "value", "bad": ]')

        raw = jsonc_copy.read_text(encoding="utf-8")
        stripped = _strip_jsonc(raw)
        with pytest.raises(json.JSONDecodeError):
            json.loads(stripped)
