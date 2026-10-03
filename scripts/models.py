#!/usr/bin/env python3
"""scripts/models.py - reader, validator and sync tool for config/models.yaml.

config/models.yaml is the single source of truth for which model each role is
pinned to. This module is the ONLY code that parses it. Other tools (hooks,
renderers, tests) either import `load_registry` or call this CLI.

Subcommands
  check                      validate the registry and that generated targets are current
  get ROLE [--harness H] [--field model|effort|id|fallback]
  is-known MODEL_ID          exit 0 when MODEL_ID is a known, non-retired model
  list-ids [--harness H] [--include-retired]
  sync [--check]             regenerate derived targets (zero diff on a synced tree)
  resolve ROLE --harness H [--available-from FILE] [--record FILE | --no-record]

Generated targets (all edited in place; hand-written prose is never touched)
  .githooks/LOCKED_MODELS.sh   the LOCKED_MODELS and AGENT_MODEL_ASSIGNMENTS array bodies
  src/AGENTS.md                Model and Effort cells of the roster table, and the
                               "**Model:** `id`, effort `x`" lead of each role section
  src/agents/*-agent.md        the frontmatter `model:` line
  config/FRAMEWORK-MANIFEST.yaml  `model:` and `effort:` of each agent entry
  .agents_verification_sha     regenerated only when src/AGENTS.md changed
  docs/MODELS.md               role table, model table, and pin history (generated from registry)

Stdlib + PyYAML only. No network.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("error: PyYAML is required (pip install pyyaml)\n")
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_REL = "config/models.yaml"
LOCKED_SH_REL = ".githooks/LOCKED_MODELS.sh"
AGENTS_MD_REL = "src/AGENTS.md"
AGENTS_DIR_REL = "src/agents"
MANIFEST_REL = "config/FRAMEWORK-MANIFEST.yaml"
SHA_REL = ".agents_verification_sha"
MODELS_MD_REL = "docs/MODELS.md"

STATUSES = ("current", "supported", "deprecated", "fallback", "retired")
EFFORTS = ("low", "medium", "high", "max")
HARNESS_RENDERS = ("pinned-id", "pass-through", "provider-prefixed", "role-tier-map")
FRESHNESS_DAYS = 180


class RegistryError(Exception):
    """Raised when the registry cannot be loaded at all."""


# --------------------------------------------------------------------------- #
# Loading and small helpers
# --------------------------------------------------------------------------- #

def load_registry(root: Path | str | None = None) -> dict:
    """Load and return config/models.yaml under *root* (default: repo root)."""
    path = Path(root or REPO_ROOT) / REGISTRY_REL
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"{path} not found") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError(f"{path} must contain a mapping at top level")
    return data


def canonical_re(reg: dict) -> re.Pattern:
    fams = "|".join(re.escape(f) for f in (reg.get("families") or {}))
    return re.compile(rf"^claude-({fams or '(?!)'})-\d+(\.\d+)?$")


def role_filename(role: str) -> str:
    return f"{role}-agent.md"


def role_title(role: str) -> str:
    return " ".join(w.capitalize() for w in role.split("-"))


def normalize_id(raw: str) -> str:
    """Normalise a harness/provider model ID for availability comparison."""
    s = str(raw).strip().lower()
    s = re.sub(r"^[a-z0-9-]+/", "", s)       # provider prefix (anthropic/, github-copilot/)
    s = re.sub(r"^anthropic\.", "", s)
    s = re.sub(r"[._]", "-", s)
    return s


def harness_id(reg: dict, model: str, harness: str) -> str | None:
    return ((reg.get("models") or {}).get(model) or {}).get("ids", {}).get(harness)


def _role_cfg(reg: dict, role: str) -> dict:
    roles = reg.get("roles") or {}
    if role not in roles:
        raise KeyError(f"unknown role '{role}' (known: {', '.join(roles)})")
    return roles[role]


def _model_ok(reg: dict, model: str) -> bool:
    m = (reg.get("models") or {}).get(model)
    return isinstance(m, dict) and m.get("status") != "retired"


def _version_tuple(model_id: str) -> tuple[int, int]:
    """Numeric (major, minor) from a canonical dotted model ID, for ordering.

    Never compares lexically: 'claude-sonnet-5.10' is newer than
    'claude-sonnet-5.5' even though the string '5.10' sorts before '5.5'.
    """
    m = re.match(r"^claude-[a-z]+-(\d+)(?:\.(\d+))?$", str(model_id))
    if not m:
        raise ValueError(f"not a canonical model ID: {model_id!r}")
    return (int(m.group(1)), int(m.group(2) or 0))


def _below_min_pin(reg: dict, model: str) -> str | None:
    """Return the family's min_pin if *model* is a known model below it, else None.

    An unknown model, or a family with no floor, is never "below". A MALFORMED floor
    raises ValueError (never swallowed): `check` validates floors via _floor_problem
    first and does not call this for a family whose floor is invalid.
    """
    fam = (reg.get("models") or {}).get(model, {}).get("family")
    if fam is None:
        return None
    floor = ((reg.get("families") or {}).get(fam) or {}).get("min_pin")
    if not floor:
        return None
    return floor if _version_tuple(model) < _version_tuple(floor) else None


def _floor_problem(reg: dict, fam: str) -> str | None:
    """Why family *fam*'s min_pin is invalid, or None (also None when it has no floor)."""
    floor = ((reg.get("families") or {}).get(fam) or {}).get("min_pin")
    if floor is None:
        return None
    try:
        _version_tuple(floor)
    except ValueError:
        return f"'{floor}' is not a canonical dotted model ID (claude-<family>-<major>[.<minor>])"
    entry = (reg.get("models") or {}).get(floor)
    if not isinstance(entry, dict):
        return f"'{floor}' is not in models"
    if entry.get("family") != fam:
        return f"'{floor}' belongs to family '{entry.get('family')}', not '{fam}'"
    if entry.get("status") == "retired":
        return f"'{floor}' is retired"
    return None


# --------------------------------------------------------------------------- #
# Generated targets: pure text transforms (text in, text out)
# --------------------------------------------------------------------------- #

def render_locked_models(text: str, reg: dict) -> str:
    """Generate the entire .githooks/LOCKED_MODELS.sh file from a template.

    The file is wholly generated; hand-edits are overwritten by sync.
    The LOCKED_MODELS array, AGENT_MODEL_ASSIGNMENTS array, and all helper
    functions are generated from the registry.
    """
    models_list = list((reg.get("models") or {}))
    roles = reg.get("roles") or {}

    # Build array bodies
    locked_body = "\n".join(f'    "{m}"' for m in models_list)
    assigns = [f'    "{r}-agent:{c["model"]}"' for r, c in roles.items()]
    assigns_body = "\n".join(assigns)

    # Build the complete file from template
    lines = [
        "#!/usr/bin/env bash",
        "# .githooks/LOCKED_MODELS.sh",
        "#",
        "# GENERATED from config/models.yaml by scripts/models.py sync - do not edit by hand.",
        "# config/models.yaml is the source of truth; regenerate with: make models-sync.",
        "# To change pins, follow the Model Pin Change process in docs/SPEC.md.",
        "#",
        "# Sourcing API (stable): LOCKED_MODELS, AGENT_MODEL_ASSIGNMENTS, is_model_locked,",
        "# get_agent_locked_model, show_locked_models, show_agent_assignments.",
        "#",
        "# Bypass: SKIP_HOOKS=1 (emergency only; document the reason in the commit message)",
        "",
        "LOCKED_MODELS=(",
    ]
    for m in models_list:
        lines.append(f'    "{m}"')
    lines.extend([
        ")",
        "",
        "# Fallback behaviour when a pinned model is unavailable is defined per role in",
        "# config/models.yaml (see docs/MODELS.md); it is not decided in this file.",
        "",
        "# ─── AGENT-MODEL MAPPING: Which agent uses which model ──────────────────────",
        "# Generated from the roles section of config/models.yaml (role pins).",
        "# Format: agent-name:model-choice (space-separated for portability)",
        "AGENT_MODEL_ASSIGNMENTS=(",
    ])
    for assign in assigns:
        lines.append(assign)
    lines.extend([
        ")",
        "",
        "# ─── VALIDATION HELPER: Check if model is in locked set ──────────────────────",
        "is_model_locked() {",
        "    local model=\"$1\"",
        "    ",
        "    for locked_model in \"${LOCKED_MODELS[@]}\"; do",
        "        if [[ \"$model\" == \"$locked_model\" ]]; then",
        "            return 0  # Model is locked (approved)",
        "        fi",
        "    done",
        "    ",
        "    return 1  # Model is NOT locked (not approved)",
        "}",
        "",
        "# ─── INTERACTIVE / DIAGNOSTIC HELPERS ────────────────────────────────────────",
        "# The three functions below (get_agent_locked_model, show_locked_models,",
        "# show_agent_assignments) have NO caller anywhere in this repo — only",
        "# is_model_locked() above is invoked by a hook (.githooks/pre-commit). They are",
        "# kept, and exported, as the documented sourcing API for interactive use:",
        "#   source .githooks/LOCKED_MODELS.sh && show_agent_assignments",
        "# See LOCKED_MODELS_RATIONALE.md § \"Enforcement Mechanism\". Do not delete them",
        "# expecting to remove dead code — delete them only alongside that documented API.",
        "",
        "# Get the locked model for a specific agent.",
        "get_agent_locked_model() {",
        "    local agent_role=\"$1\"",
        "    ",
        "    # Search for agent in assignments (format: \"agent-name:model\")",
        "    for assignment in \"${AGENT_MODEL_ASSIGNMENTS[@]}\"; do",
        "        local agent=\"${assignment%%:*}\"",
        "        local model=\"${assignment##*:}\"",
        "        if [[ \"$agent\" == \"$agent_role\" ]]; then",
        "            echo \"$model\"",
        "            return 0",
        "        fi",
        "    done",
        "    ",
        "    return 1  # Agent not found",
        "}",
        "",
        "# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────",
        "",
        "# Show all locked models (for error messages)",
        "show_locked_models() {",
        "    echo \"Locked models (approved choices):\"",
        "    for model in \"${LOCKED_MODELS[@]}\"; do",
        "        echo \"  - $model\"",
        "    done",
        "}",
        "",
        "# Show agent-model assignments (for documentation)",
        "show_agent_assignments() {",
        "    echo \"Agent model assignments:\"",
        "    for assignment in \"${AGENT_MODEL_ASSIGNMENTS[@]}\"; do",
        "        local agent=\"${assignment%%:*}\"",
        "        local model=\"${assignment##*:}\"",
        "        echo \"  - $agent: $model\"",
        "    done | sort",
        "}",
        "",
        "# ─── EXPORT for sourcing in other hooks ───────────────────────────────────────",
        "export LOCKED_MODELS",
        "export AGENT_MODEL_ASSIGNMENTS",
        "export -f is_model_locked",
        "export -f get_agent_locked_model",
        "export -f show_locked_models",
        "export -f show_agent_assignments",
        "",
        "",
    ])

    return "\n".join(lines)


def render_agents_md(text: str, reg: dict) -> str:
    roles = reg.get("roles") or {}
    # Roster table rows: | **Title** | model | effort | ...rest
    for role, cfg in roles.items():
        title = re.escape(role_title(role))
        text = re.sub(
            rf"(?m)^(\| \*\*{title}\*\* \| )(\S+)( \| )(\S+)( \|.*)$",
            lambda m, c=cfg: f"{m.group(1)}{c['model']}{m.group(3)}{c['effort']}{m.group(5)}",
            text, count=1)
    # Per-role prose lead: first **Model:** `id` and following effort `x` in the section.
    for role, cfg in roles.items():
        head = re.search(rf"(?m)^### \d+\. {re.escape(role_title(role))}\s*$", text)
        if not head:
            continue
        nxt = re.search(r"(?m)^### ", text[head.end():])
        end = head.end() + nxt.start() if nxt else len(text)
        sect = text[head.end():end]
        sect = re.sub(r"(\*\*Model:\*\* `)([^`]+)(`)", lambda m, c=cfg: f"{m.group(1)}{c['model']}{m.group(3)}", sect, count=1)
        sect = re.sub(r"(effort\s+`)([^`]+)(`)", lambda m, c=cfg: f"{m.group(1)}{c['effort']}{m.group(3)}", sect, count=1)
        text = text[:head.end()] + sect + text[end:]
    return text


def render_frontmatter(text: str, model: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        if re.match(r"^model:\s*\S+\s*$", lines[i]):
            lines[i] = f"model: {model}"
            break
    return "\n".join(lines)


def render_manifest(text: str, reg: dict) -> str:
    roles = reg.get("roles") or {}
    out, cur, in_agents = [], None, False
    for line in text.split("\n"):
        if re.match(r"^\S", line):
            in_agents = line.startswith("agents:")
            cur = None
        elif in_agents:
            m = re.match(r"^  ([a-z0-9-]+):\s*$", line)
            if m:
                cur = m.group(1)
            elif cur in roles:
                if re.match(r"^    model:\s", line):
                    line = f"    model: {roles[cur]['model']}"
                elif re.match(r"^    effort:\s", line):
                    line = f"    effort: {roles[cur]['effort']}"
        out.append(line)
    return "\n".join(out)


def render_models_md(reg: dict) -> str:
    """Generate docs/MODELS.md: role table, model table, and pin history summary."""
    lines = [
        "<!-- GENERATED FILE: Do not edit. Regenerated by `python3 scripts/models.py sync`. -->",
        "",
        "# Model Registry Reference",
        "",
        "This document is generated from `config/models.yaml` and describes which model",
        "each role is pinned to, the properties of each model, and the pin change history.",
        "",
    ]

    # Family floors
    fams_with_floor = [(f, c.get("min_pin")) for f, c in (reg.get("families") or {}).items() if c and c.get("min_pin")]
    if fams_with_floor:
        lines.extend([
            "## Family Floors",
            "",
            "A role's pin may never sit below its family's `min_pin` (fallbacks are exempt;",
            "`scripts/models.py check` enforces this by numeric major.minor comparison).",
            "",
            "| Family | Min Pin |",
            "|--------|---------|",
        ])
        for fam, floor in fams_with_floor:
            lines.append(f"| {fam} | `{floor}` |")
        lines.append("")

    # Role table
    lines.extend([
        "## Roles",
        "",
        "| Role | Model | Effort | Fallback |",
        "|------|-------|--------|----------|",
    ])
    for role, cfg in (reg.get("roles") or {}).items():
        model = cfg.get("model", "")
        effort = cfg.get("effort", "")
        fallback = ", ".join(cfg.get("fallback", []))
        lines.append(f"| **{role_title(role)}** | `{model}` | {effort} | {fallback} |")
    lines.append("")

    # Models table
    lines.extend([
        "## Models",
        "",
        "| Model ID | Family | Status | Verified | Claude | Copilot | OpenCode |",
        "|----------|--------|--------|----------|--------|---------|----------|",
    ])
    for mid, m in (reg.get("models") or {}).items():
        family = m.get("family", "")
        status = m.get("status", "")
        verified = str(m.get("verified")) if m.get("verified") else "—"
        ids = m.get("ids") or {}
        claude_id = ids.get("claude", "—")
        copilot_id = ids.get("copilot", "—")
        opencode_id = ids.get("opencode", "—")
        lines.append(
            f"| `{mid}` | {family} | {status} | {verified} | `{claude_id}` | `{copilot_id}` | `{opencode_id}` |"
        )
    lines.append("")

    # Sourced facts + CLI acceptance (only models that carry evidence)
    with_facts = [(mid, m) for mid, m in (reg.get("models") or {}).items() if m.get("facts") or m.get("cli_accepted")]
    if with_facts:
        lines.extend([
            "## Model Facts",
            "",
            "Figures read from the official page named in Source on the Verified date (USD per",
            "MTok; blank = not recorded). CLI accepted = date a real `claude -p` run returned the",
            "model's `modelUsage` key. Never inferred; see `docs/model-evidence/`.",
            "",
            "| Model ID | Price in / out | Cache read | Context | Max output | Cutoff | Verified | CLI accepted | Source |",
            "|----------|----------------|------------|---------|------------|--------|----------|--------------|--------|",
        ])
        for mid, m in with_facts:
            f = m.get("facts") or {}
            pr = f.get("price_per_mtok") or {}
            price = f"${pr['input']:g} / ${pr['output']:g}" if pr.get("input") is not None and pr.get("output") is not None else "—"
            cr = f"${pr['cache_read']:g}" if pr.get("cache_read") is not None else "—"
            ctx = f"{f['context_tokens']:,}" if f.get("context_tokens") else "—"
            mx = f"{f['max_output_tokens']:,}" if f.get("max_output_tokens") else "—"
            acc = (m.get("cli_accepted") or {}).get("date")
            lines.append(
                f"| `{mid}` | {price} | {cr} | {ctx} | {mx} | {f.get('knowledge_cutoff', '—')} | "
                f"{m.get('verified') or '—'} | {acc or '—'} | {m.get('source') or '—'} |"
            )
        lines.append("")

    # Pin history summary
    lines.extend([
        "## Pin History",
        "",
        "| Date | Role | From | To | Approval |",
        "|------|------|------|-----|----------|",
    ])
    for e in (reg.get("pin_history") or []):
        date = e.get("date", "")
        role = e.get("role", "")
        from_model = e.get("from", "—")
        to_model = e.get("to", "")
        approval = e.get("approval", "")
        lines.append(f"| {date} | {role} | {from_model} | `{to_model}` | {approval} |")
    lines.append("")

    return "\n".join(lines)


def _sha_text(agents_md_text: str, previous: str | None) -> str:
    digest = hashlib.sha256(agents_md_text.encode("utf-8")).hexdigest()
    if previous and f"agent_sha256={digest}" in previous:
        return previous
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return f"agent_sha256={digest}\ngenerated_at={now}\n"


def compute_targets(root: Path, reg: dict) -> dict[str, tuple[str | None, str]]:
    """Return {relpath: (current_text_or_None, desired_text)} for every generated target."""
    root = Path(root)
    targets: dict[str, tuple[str | None, str]] = {}

    def rd(rel: str) -> str | None:
        p = root / rel
        return p.read_text(encoding="utf-8") if p.is_file() else None

    cur = rd(LOCKED_SH_REL)
    if cur is not None:
        targets[LOCKED_SH_REL] = (cur, render_locked_models(cur, reg))
    agents_cur = rd(AGENTS_MD_REL)
    if agents_cur is not None:
        agents_new = render_agents_md(agents_cur, reg)
        targets[AGENTS_MD_REL] = (agents_cur, agents_new)
    for role, cfg in (reg.get("roles") or {}).items():
        rel = f"{AGENTS_DIR_REL}/{role_filename(role)}"
        cur = rd(rel)
        if cur is not None:
            targets[rel] = (cur, render_frontmatter(cur, cfg["model"]))
    cur = rd(MANIFEST_REL)
    if cur is not None:
        targets[MANIFEST_REL] = (cur, render_manifest(cur, reg))
    # Generate docs/MODELS.md (always generated, not conditional on existing file)
    models_cur = rd(MODELS_MD_REL)
    models_new = render_models_md(reg)
    targets[MODELS_MD_REL] = (models_cur, models_new)
    if agents_cur is not None and targets[AGENTS_MD_REL][0] != targets[AGENTS_MD_REL][1]:
        prev = rd(SHA_REL)
        targets[SHA_REL] = (prev, _sha_text(targets[AGENTS_MD_REL][1], prev))
    return targets


def sync(root: Path | str | None = None, check_only: bool = False) -> list[str]:
    """Regenerate targets. Returns the list of relpaths that differ (or were changed)."""
    root = Path(root or REPO_ROOT)
    reg = load_registry(root)
    changed = []
    for rel, (cur, new) in compute_targets(root, reg).items():
        if cur != new:
            changed.append(rel)
            if not check_only:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new, encoding="utf-8")
    return changed


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #

FACT_PRICE_KEYS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
FACT_KEYS = ("price_per_mtok", "context_tokens", "max_output_tokens", "knowledge_cutoff")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _evidence_problems(mid: str, m: dict, today: _dt.date) -> list[str]:
    """Validate the optional models.<id>.facts and .cli_accepted evidence blocks.

    facts (price/context/output/cutoff) are legal only beside a complete verified date +
    https source; null/absent facts are always legal. cli_accepted records a real Claude CLI
    run: a past-or-today date and the modelUsage key, which must equal ids.claude.
    """
    out: list[str] = []
    facts = m.get("facts")
    if facts is not None:
        if not isinstance(facts, dict):
            out.append(f"models.{mid}.facts: must be a mapping or null")
        else:
            for k in facts:
                if k not in FACT_KEYS:
                    out.append(f"models.{mid}.facts.{k}: unknown fact (allowed: {FACT_KEYS})")
            price = facts.get("price_per_mtok")
            if price is not None:
                if not isinstance(price, dict):
                    out.append(f"models.{mid}.facts.price_per_mtok: must be a mapping")
                else:
                    for k, v in price.items():
                        if k not in FACT_PRICE_KEYS:
                            out.append(f"models.{mid}.facts.price_per_mtok.{k}: unknown key (allowed: {FACT_PRICE_KEYS})")
                        elif not _is_num(v) or v <= 0:
                            out.append(f"models.{mid}.facts.price_per_mtok.{k}: must be a positive number, got {v!r}")
                    for k in ("input", "output"):
                        if k not in price:
                            out.append(f"models.{mid}.facts.price_per_mtok.{k}: required when price_per_mtok is set")
            for k in ("context_tokens", "max_output_tokens"):
                v = facts.get(k)
                if k in facts and (not isinstance(v, int) or isinstance(v, bool) or v <= 0):
                    out.append(f"models.{mid}.facts.{k}: must be a positive integer, got {v!r}")
            if "knowledge_cutoff" in facts:
                kc = facts["knowledge_cutoff"]
                if not (isinstance(kc, str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", kc)):
                    out.append(f"models.{mid}.facts.knowledge_cutoff: must be a YYYY-MM string, got {kc!r}")
            if facts:
                src = m.get("source")
                if not isinstance(m.get("verified"), _dt.date):
                    out.append(f"models.{mid}.facts: present but verified is not an ISO date (facts need verified + source)")
                if not (isinstance(src, str) and re.fullmatch(r"https://[^\s/]+\S*", src)):
                    out.append(f"models.{mid}.facts: present but source is not an https URL (facts need verified + source)")
    acc = m.get("cli_accepted")
    if acc is not None:
        if not isinstance(acc, dict):
            out.append(f"models.{mid}.cli_accepted: must be a mapping or null")
        else:
            d = acc.get("date")
            if not isinstance(d, _dt.date):
                out.append(f"models.{mid}.cli_accepted.date: must be a date, got {d!r}")
            elif d > today:
                out.append(f"models.{mid}.cli_accepted.date: {d} is in the future")
            want = (m.get("ids") or {}).get("claude")
            if acc.get("modelusage_key") != want:
                out.append(f"models.{mid}.cli_accepted.modelusage_key: {acc.get('modelusage_key')!r} must equal ids.claude {want!r}")
            for k in acc:
                if k not in ("date", "modelusage_key", "note"):
                    out.append(f"models.{mid}.cli_accepted.{k}: unknown key")
    return out


def check(root: Path | str | None = None) -> tuple[list[str], list[str]]:
    """Validate the registry and generated targets. Returns (errors, warnings)."""
    root = Path(root or REPO_ROOT)
    errors: list[str] = []
    warns: list[str] = []
    try:
        reg = load_registry(root)
    except RegistryError as exc:
        return [str(exc)], []

    if reg.get("schema_version") != 1:
        errors.append(f"schema_version must be 1, got {reg.get('schema_version')!r}")
    families = reg.get("families") or {}
    models = reg.get("models") or {}
    roles = reg.get("roles") or {}
    harnesses = reg.get("harnesses") or {}
    if not families:
        errors.append("families: at least one family is required")
    if not models:
        errors.append("models: at least one model is required")
    shape = canonical_re(reg)
    adjacent = ((reg.get("fallback_policy") or {}).get("adjacent_families")) or {}

    for hname, h in harnesses.items():
        if not isinstance(h, dict) or h.get("render") not in HARNESS_RENDERS:
            errors.append(f"harnesses.{hname}.render must be one of {HARNESS_RENDERS}")
    id_harnesses = [n for n, h in harnesses.items() if isinstance(h, dict) and h.get("render") != "role-tier-map"]

    # 1-3: model shape, family, per-harness IDs
    seen_claude: dict[str, str] = {}
    today = _dt.date.today()
    for mid, m in models.items():
        if not shape.match(str(mid)):
            errors.append(f"models.{mid}: ID does not match claude-<family>-<major>[.<minor>] (dot separator, declared family)")
            continue
        if not isinstance(m, dict):
            errors.append(f"models.{mid}: must be a mapping")
            continue
        fam = re.match(r"^claude-([a-z]+)-", mid).group(1)
        if m.get("family") != fam:
            errors.append(f"models.{mid}: family '{m.get('family')}' != family embedded in ID '{fam}'")
        if m.get("status") not in STATUSES:
            errors.append(f"models.{mid}: status must be one of {STATUSES}, got {m.get('status')!r}")
        ids = m.get("ids") or {}
        for hname in id_harnesses:
            v = ids.get(hname)
            if not v:
                errors.append(f"models.{mid}.ids.{hname}: missing (harness render is {harnesses[hname].get('render')})")
                continue
            if hname == "copilot":
                ok = re.match(rf"^claude-{fam}-\d+([.-]\d+)?$", str(v))
            else:
                ok = re.match(rf"^claude-{fam}-\d+(-\d+)?$", str(v))
            if not ok:
                errors.append(f"models.{mid}.ids.{hname}: '{v}' has the wrong shape for that harness")
            if hname == "claude":
                if v in seen_claude and seen_claude[v] != mid:
                    errors.append(f"models.{mid}.ids.claude: '{v}' duplicates models.{seen_claude[v]}")
                seen_claude[v] = mid
        ver = m.get("verified")
        if ver is not None:
            vd = ver if isinstance(ver, _dt.date) else None
            if vd is None:
                errors.append(f"models.{mid}.verified: must be a date or null")
            elif (today - vd).days > FRESHNESS_DAYS:
                warns.append(f"models.{mid}: verified {vd} is more than {FRESHNESS_DAYS} days old")
        errors.extend(_evidence_problems(mid, m, today))

    # 3b: every family floor must itself be valid (canonical, known, same family, not retired)
    bad_floor_families: set[str] = set()
    for fam, fcfg in families.items():
        if isinstance(fcfg, dict) and "min_pin" in fcfg:
            problem = _floor_problem(reg, fam)
            if problem:
                errors.append(f"families.{fam}.min_pin: {problem}")
                bad_floor_families.add(fam)

    # 4-5: roles and fallbacks
    for role, cfg in roles.items():
        if not isinstance(cfg, dict):
            errors.append(f"roles.{role}: must be a mapping")
            continue
        model = cfg.get("model")
        if model not in models:
            errors.append(f"roles.{role}.model: '{model}' is not in models")
        elif models[model].get("status") == "retired":
            errors.append(f"roles.{role}.model: '{model}' is retired")
        elif models[model].get("status") == "deprecated":
            warns.append(f"roles.{role}.model: '{model}' is deprecated")
        elif models[model].get("status") == "fallback":
            errors.append(f"roles.{role}.model: '{model}' has status 'fallback' and is never a pin; "
                          f"it is only valid in a fallback chain")
        if model in models and (models[model] or {}).get("family") not in bad_floor_families:
            floor = _below_min_pin(reg, model)
            if floor:
                errors.append(f"roles.{role}.model: '{model}' is below its family's min_pin '{floor}'")
        if cfg.get("effort") not in EFFORTS:
            errors.append(f"roles.{role}.effort: must be one of {EFFORTS}, got {cfg.get('effort')!r}")
        fb = cfg.get("fallback")
        if not isinstance(fb, list) or not fb:
            errors.append(f"roles.{role}.fallback: must be a non-empty list")
            continue
        pfam = (models.get(model) or {}).get("family")
        for f in fb:
            if f not in models:
                errors.append(f"roles.{role}.fallback: '{f}' is not in models")
                continue
            if models[f].get("status") == "retired":
                errors.append(f"roles.{role}.fallback: '{f}' is retired")
            if f == model:
                errors.append(f"roles.{role}.fallback: '{f}' is the pin itself")
            ffam = models[f].get("family")
            if pfam and ffam != pfam and ffam not in (adjacent.get(pfam) or []):
                errors.append(f"roles.{role}.fallback: '{f}' (family {ffam}) crosses family from pin '{model}' ({pfam}); "
                              f"allow it via fallback_policy.adjacent_families if intended")

    # 6: role set equals src/agents and manifest
    agents_dir = root / AGENTS_DIR_REL
    if agents_dir.is_dir():
        on_disk = {p.name[: -len("-agent.md")] for p in agents_dir.glob("*-agent.md")}
        for r in sorted(on_disk - set(roles)):
            errors.append(f"role '{r}' has {AGENTS_DIR_REL}/{role_filename(r)} but no registry entry")
        for r in sorted(set(roles) - on_disk):
            errors.append(f"roles.{r}: no {AGENTS_DIR_REL}/{role_filename(r)} exists")
    man = root / MANIFEST_REL
    if man.is_file():
        try:
            mdata = yaml.safe_load(man.read_text(encoding="utf-8")) or {}
            mroles = set((mdata.get("agents") or {}))
            for r in sorted(mroles - set(roles)):
                errors.append(f"manifest agent '{r}' has no registry role")
            for r in sorted(set(roles) - mroles):
                errors.append(f"roles.{r}: missing from {MANIFEST_REL} agents")
        except yaml.YAMLError as exc:
            errors.append(f"{MANIFEST_REL}: invalid YAML: {exc}")

    # 9: pin_history
    hist = reg.get("pin_history") or []
    last: dict[str, str] = {}
    for i, e in enumerate(hist):
        if not isinstance(e, dict) or not {"date", "role", "to", "approval"} <= set(e):
            errors.append(f"pin_history[{i}]: needs date, role, to, approval (and from)")
            continue
        if e["role"] not in roles:
            errors.append(f"pin_history[{i}]: role '{e['role']}' is not a registry role")
        if e["to"] not in models:
            errors.append(f"pin_history[{i}]: '{e['to']}' is not in models")
        if e["role"] in last and e.get("from") != last[e["role"]]:
            errors.append(f"pin_history[{i}]: from '{e.get('from')}' != previous pin '{last[e['role']]}' for {e['role']}")
        last[e["role"]] = e["to"]
    for role, cfg in roles.items():
        if role not in last:
            errors.append(f"pin_history: no entry for role '{role}'")
        elif isinstance(cfg, dict) and last[role] != cfg.get("model"):
            errors.append(f"pin_history: latest entry for '{role}' is '{last[role]}' but the pin is '{cfg.get('model')}'; "
                          f"append a pin_history entry for every pin change")

    # 7: generated targets current
    if not errors:
        for rel, (cur, new) in compute_targets(root, reg).items():
            if cur != new:
                errors.append(f"{rel}: stale; run `python3 scripts/models.py sync`")
        for rel in (LOCKED_SH_REL, AGENTS_MD_REL, MANIFEST_REL):
            if not (root / rel).is_file():
                errors.append(f"{rel}: missing")
    return errors, warns


# --------------------------------------------------------------------------- #
# resolve
# --------------------------------------------------------------------------- #

def _available_set(path: Path) -> set[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if isinstance(data.get("models"), (list, dict)):
            data = data["models"]
        elif all(isinstance(v, dict) and "models" in v for v in data.values()) and data:
            data = [k for v in data.values() for k in v["models"]]  # models.dev style {provider:{models:{}}}
    if isinstance(data, dict):
        items = list(data)
    else:
        items = [x["id"] if isinstance(x, dict) and "id" in x else x for x in data]
    return {normalize_id(i) for i in items}


def resolve(reg: dict, role: str, harness: str, available: set[str] | None = None) -> dict:
    """Walk pin then fallback chain. Returns a resolution record (never silent)."""
    cfg = _role_cfg(reg, role)
    chain = [cfg["model"], *cfg.get("fallback", [])]
    rec = {"role": role, "harness": harness, "pinned": cfg["model"], "used": None, "id": None,
           "fallback_used": False, "tried": [], "reason": None}
    for model in chain:
        rid = harness_id(reg, model, harness)
        if rid is None:
            rec["tried"].append({"model": model, "result": "no id for harness"})
            continue
        if available is None or normalize_id(rid) in available:
            rec.update(used=model, id=rid, fallback_used=(model != cfg["model"]))
            rec["tried"].append({"model": model, "result": "selected"})
            if rec["fallback_used"]:
                rec["reason"] = f"pin {cfg['model']} not available for harness {harness}"
            return rec
        rec["tried"].append({"model": model, "result": "not available"})
    rec["reason"] = f"no model in chain {chain} available for harness {harness}"
    return rec


def write_record(path: Path, rec: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("roles", {})[rec["role"]] = {
        **rec, "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="models.py", description=__doc__.split("\n")[0])
    p.add_argument("--root", default=str(REPO_ROOT), help="repository root (default: this repo)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    g = sub.add_parser("get")
    g.add_argument("role")
    g.add_argument("--harness")
    g.add_argument("--field", choices=("model", "effort", "id", "fallback"))
    k = sub.add_parser("is-known")
    k.add_argument("model_id")
    li = sub.add_parser("list-ids")
    li.add_argument("--harness")
    li.add_argument("--include-retired", action="store_true")
    s = sub.add_parser("sync")
    s.add_argument("--check", action="store_true")
    r = sub.add_parser("resolve")
    r.add_argument("role")
    r.add_argument("--harness", required=True)
    r.add_argument("--available-from")
    r.add_argument("--record")
    r.add_argument("--no-record", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.root)
    out, err = sys.stdout, sys.stderr
    try:
        if args.cmd == "check":
            errors, warns = check(root)
            for w in warns:
                err.write(f"WARN  {w}\n")
            for e in errors:
                err.write(f"ERROR {e}\n")
            out.write(f"models check: {len(errors)} error(s), {len(warns)} warning(s)\n")
            return 1 if errors else 0
        reg = load_registry(root)
        if args.cmd == "get":
            cfg = _role_cfg(reg, args.role)
            field = args.field or ("id" if args.harness else "model")
            if field == "id":
                if not args.harness:
                    err.write("error: --field id requires --harness\n")
                    return 2
                rid = harness_id(reg, cfg["model"], args.harness)
                if rid is None:
                    err.write(f"error: no {args.harness} ID for {cfg['model']}\n")
                    return 2
                out.write(rid + "\n")
            elif field == "fallback":
                out.write(" ".join(cfg.get("fallback", [])) + "\n")
            else:
                out.write(f"{cfg[field]}\n")
            return 0
        if args.cmd == "is-known":
            return 0 if _model_ok(reg, args.model_id) else 1
        if args.cmd == "list-ids":
            for mid, m in (reg.get("models") or {}).items():
                if m.get("status") == "retired" and not args.include_retired:
                    continue
                if args.harness:
                    rid = (m.get("ids") or {}).get(args.harness)
                    if rid:
                        out.write(rid + "\n")
                else:
                    out.write(mid + "\n")
            return 0
        if args.cmd == "sync":
            changed = sync(root, check_only=args.check)
            if args.check:
                for rel in changed:
                    err.write(f"STALE {rel}\n")
                out.write(f"models sync --check: {len(changed)} stale target(s)\n")
                return 1 if changed else 0
            out.write(f"models sync: {len(changed)} file(s) updated" + "".join(f"\n  {c}" for c in changed) + "\n")
            return 0
        if args.cmd == "resolve":
            avail = _available_set(Path(args.available_from)) if args.available_from else None
            rec = resolve(reg, args.role, args.harness, avail)
            if not args.no_record:
                write_record(Path(args.record) if args.record else root / "dist" / args.harness / "model-resolution.json", rec)
            if rec["used"] is None:
                err.write(f"ERROR model-unresolved role={args.role} pinned={rec['pinned']} reason={rec['reason']}\n")
                return 3
            if rec["fallback_used"]:
                err.write(f"WARN model-fallback role={args.role} pinned={rec['pinned']} used={rec['used']} reason={rec['reason']}\n")
            out.write(rec["id"] + "\n")
            return 0
    except (KeyError, RegistryError, OSError, json.JSONDecodeError) as exc:
        err.write(f"error: {exc.args[0] if isinstance(exc, KeyError) else exc}\n")
        return 2
    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
