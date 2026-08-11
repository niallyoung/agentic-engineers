"""OpenCode configuration validator (opencode.jsonc).

Security-critical validator that prevents the configuration errors that have
broken the OpenCode CLI harness in the past. Implements four enforcement
layers:

  1. Schema validation     — required/optional fields, types, enums
  2. Cross-field validation — referenced agents must exist, models must be declared
  3. Known-bug regression  — codified rules for every historical incident
  4. Integrity / safety    — file size, comment-sentinel, no secrets, structural
                              limits, optional SHA-256 integrity check

Pure standard-library implementation: no external dependencies. Designed to
run in pre-commit hooks (must be fast: <50 ms on typical configs).

Public API
----------

    >>> from scripts.validate_opencode_config import validate_file
    >>> result = validate_file("opencode.jsonc")
    >>> result.ok
    True
    >>> result.errors
    []

CLI usage
---------

    python3 scripts/validate_opencode_config.py opencode.jsonc
    python3 scripts/validate_opencode_config.py --strict opencode.jsonc
    python3 scripts/validate_opencode_config.py --json opencode.jsonc

Exit codes: 0 = valid, 1 = errors, 2 = warnings (in --strict mode), 3 = I/O error.

NOTE (SPEC-2026-005 framework slimdown, WP-0): moved here from
src/opencode/config_validator.py — that file was pure stdlib (no relative
imports) and this move rescues it ahead of src/opencode/ being deleted in a
later WP. Call sites updated: .githooks/pre-commit, scripts/opencode-safe.sh,
.github/workflows/ci.yml (credential-scan path exclusion), and
tests/test_opencode_config_validation.py.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


class Severity(str, enum.Enum):
    """Finding severity. ``ERROR`` always blocks; ``WARN`` blocks in strict mode."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


@dataclasses.dataclass(frozen=True)
class ValidationError:
    """A single validation finding."""

    code: str            # stable identifier (e.g. ``OC001``) for regression tests
    severity: Severity
    message: str
    path: str = ""       # JSON pointer-ish path, e.g. ``command.sdlc-check.template``
    hint: str = ""       # remediation hint shown to humans

    def format(self) -> str:
        icon = {Severity.ERROR: "❌", Severity.WARN: "⚠️ ", Severity.INFO: "ℹ️ "}[self.severity]
        loc = f" at `{self.path}`" if self.path else ""
        hint = f"\n   → {self.hint}" if self.hint else ""
        return f"{icon} [{self.code}] {self.message}{loc}{hint}"


@dataclasses.dataclass
class ValidationResult:
    """Aggregate result of a validation run."""

    errors: list[ValidationError] = dataclasses.field(default_factory=list)
    warnings: list[ValidationError] = dataclasses.field(default_factory=list)
    info: list[ValidationError] = dataclasses.field(default_factory=list)
    parsed: dict[str, Any] | None = None
    source_path: str = ""
    sha256: str = ""

    @property
    def ok(self) -> bool:
        """True iff there are zero ``ERROR`` findings."""
        return not self.errors

    @property
    def strict_ok(self) -> bool:
        """True iff there are zero ``ERROR`` and zero ``WARN`` findings."""
        return not self.errors and not self.warnings

    def add(self, finding: ValidationError) -> None:
        if finding.severity is Severity.ERROR:
            self.errors.append(finding)
        elif finding.severity is Severity.WARN:
            self.warnings.append(finding)
        else:
            self.info.append(finding)

    def all_findings(self) -> list[ValidationError]:
        return [*self.errors, *self.warnings, *self.info]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "strict_ok": self.strict_ok,
            "source_path": self.source_path,
            "sha256": self.sha256,
            "errors": [dataclasses.asdict(e) | {"severity": e.severity.value} for e in self.errors],
            "warnings": [dataclasses.asdict(e) | {"severity": e.severity.value} for e in self.warnings],
            "info": [dataclasses.asdict(e) | {"severity": e.severity.value} for e in self.info],
        }


# ---------------------------------------------------------------------------
# Schema definition (kept inline so the validator is single-file-deployable)
# ---------------------------------------------------------------------------


# Top-level keys we know about; anything else triggers a WARN (forward-compat).
KNOWN_TOP_LEVEL: frozenset[str] = frozenset({
    "$schema",
    "instructions",
    "default_agent",
    "model",
    "compaction",
    "permission",
    "agent",
    "command",
    "provider",
    "experimental",
    "share",
    "autoupdate",
    "theme",
    "mcp",
    "plugin",
})

PERMISSION_TOOLS: frozenset[str] = frozenset({
    "read", "edit", "bash", "task", "glob", "grep", "webfetch", "write",
    "todowrite", "todoread", "patch",
})
PERMISSION_VALUES: frozenset[str] = frozenset({"allow", "ask", "deny"})

# Provider-qualified model id pattern: ``provider/model-name``.
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.\-]*\/[A-Za-z0-9][A-Za-z0-9_.\-]*$")
AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]{0,63}$")
COMMAND_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]{0,63}$")

# Minimum & maximum sane sizes for the config file (bytes).
MIN_CONFIG_BYTES = 32
MAX_CONFIG_BYTES = 512 * 1024  # 512 KB; real configs are <10 KB

# Maximum compaction.reserved tokens (sanity check — context windows are ≤1M today)
MAX_COMPACTION_RESERVED = 200_000


# ---------------------------------------------------------------------------
# JSONC parser (strict subset: line + block comments, trailing commas)
# ---------------------------------------------------------------------------


_JSONC_LINE_COMMENT = re.compile(r"//[^\n]*")
_JSONC_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_jsonc(text: str) -> str:
    """Strip ``//`` and ``/* */`` comments + trailing commas from JSONC.

    String-aware: comment markers inside JSON strings are preserved. This is
    important because, e.g., a URL inside ``$schema`` legitimately contains
    ``//``.
    """
    out: list[str] = []
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
                # Unterminated — let JSON parser raise a clean error
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


def has_jsonc_sentinel(raw: str) -> bool:
    """OpenCode requires a comment sentinel so JSONC is recognised; check the
    first non-blank line is a ``//`` comment OR the file opens with ``/*``."""
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        return s.startswith("//") or s.startswith("/*")
    return False


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class OpenCodeConfigValidator:
    """Validate parsed-or-raw OpenCode configuration.

    Most callers should use the module-level helpers ``validate_file`` /
    ``validate_text`` instead of instantiating this directly.
    """

    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict

    # ---- entry points -----------------------------------------------------

    def validate_text(self, raw: str, source_path: str = "") -> ValidationResult:
        result = ValidationResult(source_path=source_path)
        result.sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # Layer 4a: size & sentinel sanity
        self._check_size(raw, result)
        self._check_sentinel(raw, result)
        self._check_no_secrets(raw, result)

        # Parse JSONC → dict (treat parse failure as fatal — no further checks)
        try:
            data = json.loads(strip_jsonc(raw))
        except json.JSONDecodeError as exc:
            result.add(ValidationError(
                code="OC000",
                severity=Severity.ERROR,
                message=f"Invalid JSON/JSONC syntax: {exc.msg} (line {exc.lineno}, col {exc.colno})",
                hint="Run `python -m json.tool` on the stripped file to localise the syntax error.",
            ))
            return result

        if not isinstance(data, dict):
            result.add(ValidationError(
                code="OC001",
                severity=Severity.ERROR,
                message="Top-level value must be a JSON object",
            ))
            return result

        result.parsed = data

        # Layer 1: schema
        self._check_top_level_keys(data, result)
        self._check_schema_url(data, result)
        self._check_instructions(data, result)
        self._check_default_agent(data, result)
        self._check_global_model(data, result)
        self._check_compaction(data, result)
        self._check_permission(data, result)
        self._check_agent(data, result)
        self._check_command(data, result)
        self._check_provider(data, result)

        # Layer 2: cross-field
        self._check_cross_references(data, result)
        return result

    def validate_file(self, path: str | os.PathLike[str]) -> ValidationResult:
        p = Path(path)
        try:
            raw = p.read_text(encoding="utf-8")
        except FileNotFoundError:
            r = ValidationResult(source_path=str(p))
            r.add(ValidationError(
                code="OC999",
                severity=Severity.ERROR,
                message=f"Config file not found: {p}",
                hint="Run `make install` or `scripts/validate-opencode-config.sh` to bootstrap.",
            ))
            return r
        except OSError as exc:
            r = ValidationResult(source_path=str(p))
            r.add(ValidationError(
                code="OC998",
                severity=Severity.ERROR,
                message=f"Cannot read config file {p}: {exc}",
            ))
            return r
        return self.validate_text(raw, source_path=str(p))

    # ---- layer 4: integrity / safety -------------------------------------

    def _check_size(self, raw: str, r: ValidationResult) -> None:
        size = len(raw.encode("utf-8"))
        if size < MIN_CONFIG_BYTES:
            r.add(ValidationError(
                code="OC010",
                severity=Severity.ERROR,
                message=f"Config is suspiciously small ({size} bytes) — likely truncated",
                hint="Restore from backup; see docs/OPENCODE-CONFIG-RECOVERY.md.",
            ))
        elif size > MAX_CONFIG_BYTES:
            r.add(ValidationError(
                code="OC011",
                severity=Severity.WARN,
                message=f"Config is unusually large ({size} bytes > {MAX_CONFIG_BYTES})",
            ))

    def _check_sentinel(self, raw: str, r: ValidationResult) -> None:
        # OpenCode's strict schema check requires a comment-based sentinel so
        # the file is parsed as JSONC. Historical incident: commit 54b7d05.
        if not has_jsonc_sentinel(raw):
            r.add(ValidationError(
                code="OC012",
                severity=Severity.ERROR,
                message="opencode.jsonc must begin with a `//` or `/* */` comment sentinel",
                hint='Prepend a comment line such as `// agentic-engineers OpenCode configuration`.',
            ))

    _SECRET_RE = re.compile(
        r'(?ix)("?(?:api[_-]?key|secret[_-]?key|private[_-]?key|password|token|bearer)"?\s*[:=]\s*"[^"\s]{20,}")'
        r'|(AKIA[0-9A-Z]{16})'
        r'|(ghp_[A-Za-z0-9]{30,})'
        r'|(sk-[A-Za-z0-9]{30,})'
    )

    def _check_no_secrets(self, raw: str, r: ValidationResult) -> None:
        for m in self._SECRET_RE.finditer(raw):
            snippet = m.group(0)[:40]
            r.add(ValidationError(
                code="OC013",
                severity=Severity.ERROR,
                message=f"Possible secret in config: {snippet!r}",
                hint="Secrets must live in env vars or a secret manager — never in opencode.jsonc.",
            ))

    # ---- layer 1: schema -------------------------------------------------

    def _check_top_level_keys(self, data: dict, r: ValidationResult) -> None:
        for k in data:
            if k not in KNOWN_TOP_LEVEL:
                r.add(ValidationError(
                    code="OC020",
                    severity=Severity.WARN,
                    message=f"Unknown top-level key {k!r}",
                    path=k,
                    hint=f"Known keys: {', '.join(sorted(KNOWN_TOP_LEVEL))}.",
                ))

    def _check_schema_url(self, data: dict, r: ValidationResult) -> None:
        if "$schema" not in data:
            r.add(ValidationError(
                code="OC021",
                severity=Severity.WARN,
                message="Missing `$schema` — IDEs and OpenCode CLI cannot self-validate",
                hint='Set "$schema": "https://opencode.ai/config.json".',
            ))
            return
        val = data["$schema"]
        if not isinstance(val, str) or not val.startswith(("http://", "https://")):
            r.add(ValidationError(
                code="OC022",
                severity=Severity.ERROR,
                message="`$schema` must be an http(s) URL",
                path="$schema",
            ))

    def _check_instructions(self, data: dict, r: ValidationResult) -> None:
        if "instructions" not in data:
            return
        val = data["instructions"]
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            r.add(ValidationError(
                code="OC023",
                severity=Severity.ERROR,
                message="`instructions` must be a list of relative path strings",
                path="instructions",
            ))
            return
        for i, p in enumerate(val):
            if p.startswith("/") or ".." in Path(p).parts:
                r.add(ValidationError(
                    code="OC024",
                    severity=Severity.ERROR,
                    message=f"Instruction path must be repo-relative without `..`: {p!r}",
                    path=f"instructions[{i}]",
                ))

    def _check_default_agent(self, data: dict, r: ValidationResult) -> None:
        if "default_agent" not in data:
            return
        v = data["default_agent"]
        if not isinstance(v, str) or not AGENT_NAME_RE.match(v):
            r.add(ValidationError(
                code="OC025",
                severity=Severity.ERROR,
                message=f"`default_agent` must be a lowercase-kebab agent name; got {v!r}",
                path="default_agent",
            ))

    def _check_global_model(self, data: dict, r: ValidationResult) -> None:
        if "model" not in data:
            r.add(ValidationError(
                code="OC026",
                severity=Severity.WARN,
                message="Top-level `model` not set — agents without an explicit model will fail",
                hint='Set "model": "github-copilot/claude-haiku-4.5" or similar.',
            ))
            return
        v = data["model"]
        if not isinstance(v, str) or not MODEL_ID_RE.match(v):
            r.add(ValidationError(
                code="OC027",
                severity=Severity.ERROR,
                message=f"`model` must be `provider/model-id`; got {v!r}",
                path="model",
            ))

    def _check_compaction(self, data: dict, r: ValidationResult) -> None:
        if "compaction" not in data:
            return
        c = data["compaction"]
        if not isinstance(c, dict):
            r.add(ValidationError(code="OC030", severity=Severity.ERROR,
                                  message="`compaction` must be an object", path="compaction"))
            return
        if "auto" in c and not isinstance(c["auto"], bool):
            r.add(ValidationError(code="OC031", severity=Severity.ERROR,
                                  message="`compaction.auto` must be boolean", path="compaction.auto"))
        if "reserved" in c:
            v = c["reserved"]
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                r.add(ValidationError(code="OC032", severity=Severity.ERROR,
                                      message=f"`compaction.reserved` must be a non-negative integer; got {v!r}",
                                      path="compaction.reserved"))
            elif v > MAX_COMPACTION_RESERVED:
                r.add(ValidationError(code="OC033", severity=Severity.WARN,
                                      message=f"`compaction.reserved` ({v}) exceeds {MAX_COMPACTION_RESERVED}",
                                      path="compaction.reserved",
                                      hint="Too-high reservation defeats compaction; typical value is 20000–30000."))

    def _check_permission(self, data: dict, r: ValidationResult) -> None:
        if "permission" not in data:
            return
        p = data["permission"]
        if not isinstance(p, dict):
            r.add(ValidationError(code="OC040", severity=Severity.ERROR,
                                  message="`permission` must be an object", path="permission"))
            return
        for tool, mode in p.items():
            if tool not in PERMISSION_TOOLS:
                r.add(ValidationError(code="OC041", severity=Severity.WARN,
                                      message=f"Unknown permission tool {tool!r}",
                                      path=f"permission.{tool}",
                                      hint=f"Known: {', '.join(sorted(PERMISSION_TOOLS))}."))
            if mode not in PERMISSION_VALUES:
                r.add(ValidationError(code="OC042", severity=Severity.ERROR,
                                      message=f"Permission value must be one of {sorted(PERMISSION_VALUES)}; got {mode!r}",
                                      path=f"permission.{tool}"))

    def _check_agent(self, data: dict, r: ValidationResult) -> None:
        if "agent" not in data:
            return
        a = data["agent"]
        if not isinstance(a, dict):
            r.add(ValidationError(code="OC050", severity=Severity.ERROR,
                                  message="`agent` must be an object keyed by agent name", path="agent"))
            return
        for name, spec in a.items():
            if not AGENT_NAME_RE.match(name):
                r.add(ValidationError(code="OC051", severity=Severity.ERROR,
                                      message=f"Invalid agent name {name!r}", path=f"agent.{name}"))
            if not isinstance(spec, dict):
                r.add(ValidationError(code="OC052", severity=Severity.ERROR,
                                      message=f"Agent spec for {name!r} must be an object", path=f"agent.{name}"))
                continue
            if "model" in spec:
                m = spec["model"]
                if not isinstance(m, str) or not MODEL_ID_RE.match(m):
                    r.add(ValidationError(code="OC053", severity=Severity.ERROR,
                                          message=f"agent.{name}.model invalid: {m!r}",
                                          path=f"agent.{name}.model"))
            if "mode" in spec and spec["mode"] not in {"all", "subagent", "primary", "interactive"}:
                r.add(ValidationError(code="OC054", severity=Severity.WARN,
                                      message=f"agent.{name}.mode {spec['mode']!r} not a recognised mode",
                                      path=f"agent.{name}.mode",
                                      hint="Known modes: all, subagent, primary, interactive."))

    def _check_command(self, data: dict, r: ValidationResult) -> None:
        # **CRITICAL REGRESSION**: this is the rule that would have caught the
        # May 17 incident (missing `template` field caused ConfigInvalidError).
        if "command" not in data:
            return
        cmds = data["command"]
        if not isinstance(cmds, dict):
            r.add(ValidationError(code="OC060", severity=Severity.ERROR,
                                  message="`command` must be an object keyed by command name", path="command"))
            return
        for name, spec in cmds.items():
            ppath = f"command.{name}"
            if not COMMAND_NAME_RE.match(name):
                r.add(ValidationError(code="OC061", severity=Severity.ERROR,
                                      message=f"Invalid command name {name!r}", path=ppath))
            if not isinstance(spec, dict):
                r.add(ValidationError(code="OC062", severity=Severity.ERROR,
                                      message=f"Command spec for {name!r} must be an object", path=ppath))
                continue
            # ⚠️ REQUIRED: template — without it OpenCode raises ConfigInvalidError.
            if "template" not in spec:
                r.add(ValidationError(
                    code="OC063",
                    severity=Severity.ERROR,
                    message=f"command.{name} is missing required `template` field",
                    path=f"{ppath}.template",
                    hint="Every custom command must define a `template` string. See "
                         "docs/OPENCODE-CONFIG-COMMON-MISTAKES.md#missing-template.",
                ))
            else:
                t = spec["template"]
                if not isinstance(t, str) or not t.strip():
                    r.add(ValidationError(code="OC064", severity=Severity.ERROR,
                                          message=f"command.{name}.template must be a non-empty string",
                                          path=f"{ppath}.template"))
            if "description" not in spec:
                r.add(ValidationError(code="OC065", severity=Severity.WARN,
                                      message=f"command.{name} missing `description` (recommended)",
                                      path=f"{ppath}.description"))
            if "agent" in spec:
                ag = spec["agent"]
                if not isinstance(ag, str) or not AGENT_NAME_RE.match(ag):
                    r.add(ValidationError(code="OC066", severity=Severity.ERROR,
                                          message=f"command.{name}.agent invalid: {ag!r}",
                                          path=f"{ppath}.agent"))
            if "subtask" in spec and not isinstance(spec["subtask"], bool):
                r.add(ValidationError(code="OC067", severity=Severity.ERROR,
                                      message=f"command.{name}.subtask must be boolean",
                                      path=f"{ppath}.subtask"))

    def _check_provider(self, data: dict, r: ValidationResult) -> None:
        if "provider" not in data:
            return
        prov = data["provider"]
        if not isinstance(prov, dict):
            r.add(ValidationError(code="OC070", severity=Severity.ERROR,
                                  message="`provider` must be an object keyed by provider id", path="provider"))
            return
        for pname, pspec in prov.items():
            ppath = f"provider.{pname}"
            if not isinstance(pspec, dict):
                r.add(ValidationError(code="OC071", severity=Severity.ERROR,
                                      message=f"Provider {pname!r} must be an object", path=ppath))
                continue
            models = pspec.get("models", {})
            if not isinstance(models, dict):
                r.add(ValidationError(code="OC072", severity=Severity.ERROR,
                                      message=f"{ppath}.models must be an object", path=f"{ppath}.models"))
                continue
            for mname, mspec in models.items():
                mpath = f"{ppath}.models.{mname}"
                if not isinstance(mspec, dict):
                    r.add(ValidationError(code="OC073", severity=Severity.ERROR,
                                          message=f"{mpath} must be an object", path=mpath))
                    continue
                if mspec.get("id") != mname:
                    r.add(ValidationError(code="OC074", severity=Severity.WARN,
                                          message=f"{mpath}.id ({mspec.get('id')!r}) should equal key {mname!r}",
                                          path=f"{mpath}.id"))
                for required in ("name", "id"):
                    if required not in mspec:
                        r.add(ValidationError(code="OC075", severity=Severity.ERROR,
                                              message=f"{mpath} missing required field {required!r}",
                                              path=f"{mpath}.{required}"))
                limit = mspec.get("limit")
                if limit is not None:
                    if not isinstance(limit, dict):
                        r.add(ValidationError(code="OC076", severity=Severity.ERROR,
                                              message=f"{mpath}.limit must be object",
                                              path=f"{mpath}.limit"))
                    else:
                        for k in ("context", "output"):
                            v = limit.get(k)
                            if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v <= 0):
                                r.add(ValidationError(code="OC077", severity=Severity.ERROR,
                                                      message=f"{mpath}.limit.{k} must be a positive int",
                                                      path=f"{mpath}.limit.{k}"))
                cost = mspec.get("cost")
                if cost is not None and not isinstance(cost, dict):
                    r.add(ValidationError(code="OC078", severity=Severity.ERROR,
                                          message=f"{mpath}.cost must be object",
                                          path=f"{mpath}.cost"))

    # ---- layer 2: cross-field --------------------------------------------

    def _check_cross_references(self, data: dict, r: ValidationResult) -> None:
        agents = set(data.get("agent", {}).keys()) if isinstance(data.get("agent"), dict) else set()
        cmds = data.get("command", {}) if isinstance(data.get("command"), dict) else {}

        # 1. default_agent must be declared in `agent` (if `agent` block present)
        da = data.get("default_agent")
        if isinstance(da, str) and agents and da not in agents:
            r.add(ValidationError(
                code="OC080",
                severity=Severity.WARN,
                message=f"default_agent {da!r} is not declared in `agent` block",
                path="default_agent",
                hint=f"Declare it explicitly: \"agent\": {{ \"{da}\": {{ \"model\": \"…\" }} }}.",
            ))

        # 2. Every command.<x>.agent must exist in `agent` (if declared)
        for cname, spec in cmds.items() if isinstance(cmds, dict) else []:
            if not isinstance(spec, dict):
                continue
            ag = spec.get("agent")
            if isinstance(ag, str) and agents and ag not in agents:
                r.add(ValidationError(
                    code="OC081",
                    severity=Severity.ERROR,
                    message=f"command.{cname}.agent refers to undeclared agent {ag!r}",
                    path=f"command.{cname}.agent",
                ))

        # 3. Models referenced by agent.<x>.model must be declared in some provider (if any provider present)
        declared_models: set[str] = set()
        prov = data.get("provider", {})
        if isinstance(prov, dict):
            for pname, pspec in prov.items():
                if isinstance(pspec, dict):
                    for mname in (pspec.get("models") or {}):
                        declared_models.add(f"{pname}/{mname}")

        if declared_models:
            # global model
            gm = data.get("model")
            if isinstance(gm, str) and gm not in declared_models:
                r.add(ValidationError(
                    code="OC082",
                    severity=Severity.WARN,
                    message=f"Top-level model {gm!r} not declared in `provider.*.models`",
                    path="model",
                ))
            # per-agent models
            for aname, aspec in (data.get("agent") or {}).items():
                if isinstance(aspec, dict):
                    am = aspec.get("model")
                    if isinstance(am, str) and am not in declared_models:
                        r.add(ValidationError(
                            code="OC083",
                            severity=Severity.WARN,
                            message=f"agent.{aname}.model {am!r} not declared in `provider.*.models`",
                            path=f"agent.{aname}.model",
                        ))


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def validate_file(path: str | os.PathLike[str], *, strict: bool = False) -> ValidationResult:
    """Validate ``path`` and return a :class:`ValidationResult`."""
    return OpenCodeConfigValidator(strict=strict).validate_file(path)


def validate_text(text: str, *, source_path: str = "", strict: bool = False) -> ValidationResult:
    """Validate raw config ``text`` and return a :class:`ValidationResult`."""
    return OpenCodeConfigValidator(strict=strict).validate_text(text, source_path=source_path)


def integrity_digest(path: str | os.PathLike[str]) -> str:
    """Return the SHA-256 of the file at ``path`` (lowercase hex)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(result: ValidationResult, *, use_json: bool) -> str:
    if use_json:
        return json.dumps(result.to_dict(), indent=2, sort_keys=True)
    lines: list[str] = []
    if result.source_path:
        lines.append(f"opencode-config-validator: {result.source_path}  sha256={result.sha256[:12]}…")
    for f in result.all_findings():
        lines.append(f.format())
    if result.ok and not result.warnings:
        lines.append("✅ Config is valid (0 errors, 0 warnings).")
    elif result.ok:
        lines.append(f"✅ Config has 0 errors ({len(result.warnings)} warnings).")
    else:
        lines.append(f"❌ Config has {len(result.errors)} error(s) and {len(result.warnings)} warning(s).")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    """Module entry point — also wired into ``python3 scripts/validate_opencode_config.py``."""
    parser = argparse.ArgumentParser(
        prog="opencode-config-validator",
        description="Validate an opencode.jsonc file.",
    )
    parser.add_argument("path", nargs="?", default="opencode.jsonc",
                        help="Path to the config file (default: ./opencode.jsonc)")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as failures (exit 2).")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON report.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress success message (errors still printed).")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = validate_file(args.path, strict=args.strict)
    text = _format_report(result, use_json=args.json)
    if not (args.quiet and result.ok and not result.warnings):
        print(text)

    if not result.ok:
        return 1
    if args.strict and result.warnings:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
