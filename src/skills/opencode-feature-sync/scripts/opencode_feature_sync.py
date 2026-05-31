#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""opencode-feature-sync — drift detection between OpenCode's agent/sub-agent
integration points and the agentic-engineers OpenCode renderer.

This script re-performs the analysis that compares OpenCode's recognized agent
frontmatter schema against what ``renderer/scripts/render-opencode.sh`` emits,
flags drift (no-op keys, missing-but-supported keys, uniform permissions),
discovers candidate new integration points, and can rewrite its own
``references/integration-points.yaml`` registry to stay current.

Default behaviour (no flags) is READ-ONLY (dry run): it prints a markdown report
to stdout and never mutates the registry.

    python3 opencode_feature_sync.py --help
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    yaml = None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SKILL_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY = _SKILL_ROOT / "references" / "integration-points.yaml"
_DEFAULT_OPENCODE = Path("~/git/opencode").expanduser()
# Repo root is src/skills/<skill>/scripts -> up 4 levels.
_DEFAULT_REPO_ROOT = _SKILL_ROOT.parent.parent.parent

# Keys that OpenCode recognizes but the renderer SHOULD emit for full fidelity.
# Used to flag missing-but-now-supported emissions (e.g. reasoning `variant`).
_RECOMMENDED_KEYS = {"variant"}

# OpenCode directories worth scanning when discovering new integration points.
_DISCOVERY_DIRS = (
    "packages/opencode/src/config",
    "packages/opencode/src/agent",
    "packages/opencode/src/provider",
)
_DISCOVERY_PATTERN = re.compile(r"\b(permission|reasoning|variant|subagent|default_agent)\b")


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------
def load_registry(path: Path) -> dict:
    """Load the integration-points registry from YAML."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to load the registry")
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict) or "integration_points" not in data:
        raise ValueError("registry missing 'integration_points' key")
    return data


def _registry_header_comment(path: Path) -> str:
    """Return the leading comment block of the registry, preserved on rewrite."""
    lines: List[str] = []
    for line in Path(path).read_text().splitlines():
        if line.startswith("#") or line.strip() == "":
            lines.append(line)
            continue
        break
    return "\n".join(lines).rstrip() + "\n" if lines else ""


# ---------------------------------------------------------------------------
# OpenCode introspection
# ---------------------------------------------------------------------------
def extract_known_keys(opencode_root: Path) -> Set[str]:
    """Parse the KNOWN_KEYS set from packages/opencode/src/config/agent.ts."""
    agent_ts = Path(opencode_root) / "packages" / "opencode" / "src" / "config" / "agent.ts"
    return extract_known_keys_from_text(agent_ts.read_text())


def extract_known_keys_from_text(text: str) -> Set[str]:
    """Extract the quoted members of the `KNOWN_KEYS = new Set([ ... ])` literal."""
    match = re.search(r"KNOWN_KEYS\s*=\s*new\s+Set\(\[(.*?)\]\)", text, re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"""["']([A-Za-z_][A-Za-z0-9_]*)["']""", match.group(1)))


def extract_emitted_keys(renderer_text: str) -> Set[str]:
    """Extract the top-level frontmatter keys the renderer emits per agent.

    Scans `echo "..."` and `printf '...'` lines; a key is top-level when the
    emitted string has no leading indentation (nested permission entries like
    `  read: allow` are excluded).
    """
    keys: Set[str] = set()
    for raw in _emitted_strings(renderer_text):
        if raw[:1].isspace():
            continue
        m = re.match(r"([a-z_]+):", raw)
        if m:
            keys.add(m.group(1))
    return keys


def _emitted_strings(renderer_text: str) -> List[str]:
    """Return the literal payloads of echo/printf emission lines."""
    out: List[str] = []
    for line in renderer_text.splitlines():
        stripped = line.strip()
        em = re.match(r"""echo\s+"(.*)"$""", stripped)
        if em:
            out.append(em.group(1))
            continue
        pm = re.match(r"""printf\s+'(.*?)\\n'""", stripped)
        if pm:
            out.append(pm.group(1))
    return out


def detect_permission_uniformity(renderer_text: str) -> bool:
    """Return True when the renderer emits a uniform allow-all permission block.

    Heuristic: a `permission:` block is emitted, every emitted permission entry
    resolves to `allow`, and there is no least-privilege `deny` or per-role
    branching (`"*": deny`).
    """
    if "permission:" not in renderer_text:
        return False
    perm_entries = re.findall(r"""(?:echo|printf)\s+['"]\s+([a-z_]+):\s*(allow|deny|ask)""", renderer_text)
    if not perm_entries:
        return False
    has_deny = any(action == "deny" for _, action in perm_entries)
    has_wildcard_deny = bool(re.search(r"""\*\\?["']?\s*:\s*deny""", renderer_text))
    return not has_deny and not has_wildcard_deny


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------
def detect_drift(known_keys: Set[str], emitted_keys: Set[str], renderer_text: str) -> List[dict]:
    """Compare renderer emissions against OpenCode's recognized schema."""
    findings: List[dict] = []

    for key in sorted(emitted_keys - known_keys):
        findings.append(
            {
                "kind": "noop-key",
                "severity": "error",
                "detail": f"Renderer emits frontmatter key '{key}' which is NOT in OpenCode KNOWN_KEYS; "
                f"it is swept into options and has no effect.",
            }
        )

    for key in sorted(_RECOMMENDED_KEYS - emitted_keys):
        if key in known_keys:
            findings.append(
                {
                    "kind": "missing-supported-key",
                    "severity": "warning",
                    "detail": f"OpenCode supports '{key}' but the renderer does not emit it "
                    f"(reasoning/variant fidelity gap).",
                }
            )

    if detect_permission_uniformity(renderer_text):
        findings.append(
            {
                "kind": "permission-uniformity",
                "severity": "warning",
                "detail": "Renderer emits a uniform allow-all permission block for every agent; "
                "no least-privilege per-role differentiation (mirror explore's '*': deny pattern).",
            }
        )

    return findings


# ---------------------------------------------------------------------------
# Integration point verification + discovery
# ---------------------------------------------------------------------------
def verify_integration_points(registry: dict, opencode_root: Path, renderer_path: Path) -> List[dict]:
    """Confirm each registered integration point still exists; update status."""
    results: List[dict] = []
    for entry in registry.get("integration_points", []):
        rel = entry.get("opencode_path", "")
        base = renderer_path.parent.parent if rel.startswith("renderer/") else Path(opencode_root)
        # renderer-relative entries live in the agentic-engineers repo, not opencode.
        target = (_DEFAULT_REPO_ROOT / rel) if rel.startswith("renderer/") else (base / rel)
        anchor = entry.get("anchor", "")
        exists = target.exists()
        anchor_found = False
        if exists and anchor and not any(c in anchor for c in "*{"):
            anchor_found = anchor in target.read_text(errors="ignore")
        elif exists:
            anchor_found = True  # glob/wildcard anchors: file presence is enough
        results.append(
            {
                "id": entry.get("id"),
                "exists": exists,
                "anchor_found": anchor_found,
                "status": "verified" if (exists and anchor_found) else "missing",
            }
        )
    return results


def discover_candidates(opencode_root: Path, registry: dict) -> List[dict]:
    """Grep OpenCode for agent/permission/reasoning config files not yet registered."""
    known_paths = {e.get("opencode_path") for e in registry.get("integration_points", [])}
    candidates: List[dict] = []
    seen: Set[str] = set()
    for rel_dir in _DISCOVERY_DIRS:
        base = Path(opencode_root) / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.ts")):
            rel = str(path.relative_to(opencode_root))
            if rel in known_paths or rel in seen:
                continue
            if _DISCOVERY_PATTERN.search(path.read_text(errors="ignore")):
                seen.add(rel)
                candidates.append(
                    {
                        "id": "candidate-" + (path.parent.name + "-" + path.stem).replace("_", "-"),
                        "opencode_path": rel,
                        "anchor": "",
                        "what_to_check": "DISCOVERED: references agent/permission/reasoning config; review for relevance.",
                        "last_verified": _today(),
                        "status": "candidate",
                    }
                )
    return candidates


# ---------------------------------------------------------------------------
# Self-update
# ---------------------------------------------------------------------------
def update_registry(
    registry: dict,
    verifications: List[dict],
    candidates: List[dict],
    drift_drifted_ids: Set[str],
    registry_path: Path,
) -> dict:
    """Refresh last_verified, apply verified status, append candidates, and write back."""
    today = _today()
    status_by_id = {v["id"]: v["status"] for v in verifications}
    for entry in registry["integration_points"]:
        eid = entry.get("id")
        verified_status = status_by_id.get(eid)
        if verified_status == "verified":
            entry["last_verified"] = today
            if entry.get("status") != "drifted" or eid not in drift_drifted_ids:
                entry["status"] = "drifted" if eid in drift_drifted_ids else "verified"
        elif verified_status == "missing":
            entry["status"] = "missing"

    existing_ids = {e.get("id") for e in registry["integration_points"]}
    for cand in candidates:
        if cand["id"] not in existing_ids:
            registry["integration_points"].append(cand)
            existing_ids.add(cand["id"])

    write_registry(registry, registry_path)
    return registry


def write_registry(registry: dict, registry_path: Path) -> None:
    """Serialize the registry to YAML, preserving the leading comment header."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to write the registry")
    header = _registry_header_comment(registry_path) if Path(registry_path).exists() else ""
    body = yaml.safe_dump(registry, sort_keys=False, default_flow_style=False, width=100)
    Path(registry_path).write_text(header + body)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def build_report(
    known_keys: Set[str],
    emitted_keys: Set[str],
    findings: List[dict],
    verifications: List[dict],
    candidates: List[dict],
) -> str:
    """Render a markdown drift report."""
    lines: List[str] = []
    lines.append("# OpenCode Feature Sync Report")
    lines.append("")
    lines.append(f"_Generated: {_today()}_")
    lines.append("")
    lines.append("## Recognized frontmatter keys (OpenCode KNOWN_KEYS)")
    lines.append("")
    lines.append("`" + ", ".join(sorted(known_keys)) + "`" if known_keys else "_none extracted_")
    lines.append("")
    lines.append("## Renderer-emitted top-level keys")
    lines.append("")
    lines.append("`" + ", ".join(sorted(emitted_keys)) + "`" if emitted_keys else "_none extracted_")
    lines.append("")
    lines.append("## Drift findings")
    lines.append("")
    if not findings:
        lines.append("- ✅ No drift detected.")
    for f in findings:
        icon = "❌" if f["severity"] == "error" else "⚠️"
        lines.append(f"- {icon} **{f['kind']}**: {f['detail']}")
    lines.append("")
    lines.append("## Integration point verification")
    lines.append("")
    for v in verifications:
        icon = "✅" if v["status"] == "verified" else "❌"
        lines.append(f"- {icon} `{v['id']}` — exists={v['exists']} anchor_found={v['anchor_found']}")
    lines.append("")
    lines.append("## Discovered candidate integration points")
    lines.append("")
    if not candidates:
        lines.append("- _none_")
    for c in candidates:
        lines.append(f"- 🔍 `{c['id']}` → `{c['opencode_path']}`")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _today() -> str:
    return datetime.date.today().isoformat()


def _resolve_renderer_path(repo_root: Path, registry: dict, override: Optional[str]) -> Path:
    if override:
        return Path(override).expanduser()
    rel = registry.get("renderer_path", "renderer/scripts/render-opencode.sh")
    return Path(repo_root) / rel


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry).expanduser()
    registry = load_registry(registry_path)

    opencode_root = Path(args.opencode_root).expanduser()
    repo_root = Path(args.repo_root).expanduser()
    renderer_path = _resolve_renderer_path(repo_root, registry, args.renderer)

    known_keys: Set[str] = set()
    agent_ts = opencode_root / "packages" / "opencode" / "src" / "config" / "agent.ts"
    if agent_ts.exists():
        known_keys = extract_known_keys(opencode_root)

    emitted_keys: Set[str] = set()
    renderer_text = ""
    if renderer_path.exists():
        renderer_text = renderer_path.read_text(errors="ignore")
        emitted_keys = extract_emitted_keys(renderer_text)

    findings = detect_drift(known_keys, emitted_keys, renderer_text) if known_keys else []
    verifications = verify_integration_points(registry, opencode_root, renderer_path)
    candidates = discover_candidates(opencode_root, registry) if opencode_root.exists() else []

    report = build_report(known_keys, emitted_keys, findings, verifications, candidates)

    if args.update_registry:
        drifted_ids = {"renderer-thinking-emission"} if any(
            f["kind"] == "noop-key" for f in findings
        ) else set()
        update_registry(registry, verifications, candidates, drifted_ids, registry_path)
        report += f"\n_Registry updated in place: {registry_path}_\n"
    else:
        report += "\n_Dry run (read-only). Pass --update-registry to refresh the registry._\n"

    if args.report:
        Path(args.report).expanduser().write_text(report)
    else:
        print(report)

    has_errors = any(f["severity"] == "error" for f in findings)
    return 2 if has_errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode_feature_sync.py",
        description="Detect drift between OpenCode agent integration points and the agentic-engineers renderer.",
    )
    parser.add_argument(
        "--opencode-root",
        default=str(_DEFAULT_OPENCODE),
        help="Path to the OpenCode repo (default: ~/git/opencode).",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_DEFAULT_REPO_ROOT),
        help="Path to the agentic-engineers repo root.",
    )
    parser.add_argument(
        "--registry",
        default=str(_DEFAULT_REGISTRY),
        help="Path to integration-points.yaml registry.",
    )
    parser.add_argument(
        "--renderer",
        default=None,
        help="Override path to render-opencode.sh (default: <repo-root>/renderer/scripts/render-opencode.sh).",
    )
    parser.add_argument(
        "--update-registry",
        action="store_true",
        help="SELF-UPDATE: rewrite references/integration-points.yaml (refresh last_verified, append discovered points). "
        "Default is read-only dry run.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Write the markdown report to this path instead of stdout.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
