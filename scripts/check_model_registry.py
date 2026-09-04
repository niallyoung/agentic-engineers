#!/usr/bin/env python3
"""
scripts/check_model_registry.py — Advisory model-registry drift checker.

Compares LOCKED_MODELS.sh against models.dev's public registry.
Reports: found/not-found, deprecation status, pricing, context window.

ADVISORY-ONLY: exits 0 always (except real crashes); no CI gating.
"""

import json
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCKED_MODELS_SH = REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh"

# models.dev endpoint
MODELS_DEV_API = "https://models.dev/api.json"
REQUEST_TIMEOUT = 5  # seconds


@dataclass
class ModelInfo:
    """Model metadata from registry."""
    id: str
    name: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None  # e.g., "deprecated", "beta"
    context_window: Optional[int] = None
    cost_input: Optional[float] = None  # USD per 1M tokens
    cost_output: Optional[float] = None


@dataclass
class RegistryCheckResult:
    """Result of checking one locked model."""
    model: str
    found: bool
    in_registry_as: Optional[str] = None  # normalized registry id if found
    provider: Optional[str] = None  # models.dev provider id (e.g. "anthropic")
    status: Optional[str] = None
    context_window: Optional[int] = None
    cost_input: Optional[float] = None
    cost_output: Optional[float] = None
    notes: Optional[str] = None


def _parse_locked_models() -> List[str]:
    """Extract LOCKED_MODELS array from .githooks/LOCKED_MODELS.sh."""
    text = LOCKED_MODELS_SH.read_text()
    block = re.search(r"LOCKED_MODELS=\((.*?)\)", text, re.DOTALL)
    if not block:
        raise ValueError("LOCKED_MODELS array not found in LOCKED_MODELS.sh")

    models = []
    for m in re.finditer(r'"(claude-[\w.\-]+)"', block.group(1)):
        models.append(m.group(1))

    return models


def _parse_agent_assignments() -> Dict[str, str]:
    """Extract AGENT_MODEL_ASSIGNMENTS from .githooks/LOCKED_MODELS.sh."""
    text = LOCKED_MODELS_SH.read_text()
    block = re.search(r"AGENT_MODEL_ASSIGNMENTS=\((.*?)\)", text, re.DOTALL)
    if not block:
        raise ValueError("AGENT_MODEL_ASSIGNMENTS array not found in LOCKED_MODELS.sh")

    assignments = {}
    for m in re.finditer(r'"([\w-]+):(claude-[\w.\-]+)"', block.group(1)):
        assignments[m.group(1)] = m.group(2)

    return assignments


def _fetch_models_dev_registry() -> Optional[Dict]:
    """Fetch models.dev API; return None if network unavailable."""
    try:
        with urllib.request.urlopen(MODELS_DEV_API, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        # Network unavailable / malformed response — advisory only.
        return None


def _normalize_model_id(registry_id: str, locked_id: str) -> bool:
    """
    Check if a registry model id matches our locked id.

    Handles variations like:
    - claude-sonnet-5 vs claude-sonnet-5.0
    - claude-opus-5 vs claude-opus-5.0
    """
    # Exact match
    if registry_id == locked_id:
        return True

    # Variant: add .0 if absent
    if registry_id == locked_id + ".0":
        return True
    if locked_id == registry_id + ".0":
        return True

    # Variant: family + major version only (strip minor)
    return _match_tier(registry_id, locked_id) is not None


def _model_base(m: str) -> str:
    """Family + major version only, e.g. claude-opus-4.7 -> claude-opus-4."""
    match = re.match(r"^(claude-[\w]+)-(\d+)", m)
    if match:
        return match.group(1) + "-" + match.group(2)
    return m


def _match_tier(registry_id: str, locked_id: str) -> Optional[int]:
    """Rank how well a registry id matches a locked id — lower is better.

    0  exact id
    1  dot/dash spelling variant (Anthropic publishes claude-opus-4-7 where
       LOCKED_MODELS.sh writes claude-opus-4.7)
    2  trailing ".0" variant
    3  family + major only — LOSSY: claude-opus-4.6, 4.7 and 4.8 all share the
       base claude-opus-4, so this tier must never outrank tier 1, or a lookup
       for 4.7 reports 4.5's context window and pricing.

    Returns None when the ids do not correspond at all.
    """
    if registry_id == locked_id:
        return 0
    if registry_id.replace(".", "-") == locked_id.replace(".", "-"):
        return 1
    if registry_id == locked_id + ".0" or locked_id == registry_id + ".0":
        return 2
    if _model_base(registry_id) == _model_base(locked_id):
        return 3
    return None


def _iter_registry_models(registry_data: Dict):
    """Yield (provider_id, model_id, model_dict) from a models.dev api.json payload.

    Verified shape (fetched from https://models.dev/api.json, 2026-09-03):

        { "<provider-id>": { "id": ..., "name": ..., "models": { "<model-id>": {...} } } }

    i.e. the top level is keyed by *provider*, and each provider holds a
    ``models`` dict keyed by model id. The previous implementation treated each
    top-level entry as a model, so every provider dict was indexed under its
    provider id and no locked model could ever be found.

    A flat ``{"models": [...]}`` / ``{"data": [...]}`` list is still accepted as
    a defensive fallback in case the endpoint changes shape.
    """
    if not isinstance(registry_data, dict):
        return

    # Defensive fallback: a flat list of model objects.
    for flat_key in ("models", "data"):
        flat = registry_data.get(flat_key)
        if isinstance(flat, list):
            for model in flat:
                if isinstance(model, dict) and model.get("id"):
                    yield model.get("provider"), model["id"], model
            return

    # Canonical shape: provider -> {"models": {model_id: {...}}}
    for provider_id, provider in registry_data.items():
        if not isinstance(provider, dict):
            continue
        models = provider.get("models")
        if not isinstance(models, dict):
            continue
        for model_id, model in models.items():
            if isinstance(model, dict):
                yield provider_id, model.get("id") or model_id, model


def _build_model_index(registry_data: Dict) -> Dict[str, ModelInfo]:
    """Build a {model_id: ModelInfo} index from a models.dev api.json payload."""
    index: Dict[str, ModelInfo] = {}

    for provider_id, model_id, model in _iter_registry_models(registry_data):
        if not model_id:
            continue

        limit = model.get("limit") if isinstance(model.get("limit"), dict) else {}
        info = ModelInfo(
            id=model_id,
            name=model.get("name"),
            provider=provider_id,
            # models.dev exposes limit.context (input context window) and
            # limit.output (max output tokens). The context window is `context`;
            # this previously read `output` and reported max-output as context.
            status=model.get("status"),
            context_window=limit.get("context"),
        )

        cost = model.get("cost")
        if isinstance(cost, dict):
            info.cost_input = cost.get("input")
            info.cost_output = cost.get("output")

        # Same model id appears under many reseller providers with differing
        # limits. Prefer the first entry seen, but let the canonical "anthropic"
        # provider win any collision so limits/pricing come from the source.
        existing = index.get(model_id)
        if existing is None or (provider_id == "anthropic" and existing.provider != "anthropic"):
            index[model_id] = info

    return index


CANONICAL_PROVIDER = "anthropic"


def check_model_against_registry(
    locked_model: str,
    registry_index: Dict[str, ModelInfo]
) -> RegistryCheckResult:
    """Check a single locked model against the registry.

    models.dev lists the same model under dozens of reseller providers, whose
    reported limits and pricing differ from Anthropic's own. Anthropic also
    publishes dashed ids (``claude-opus-4-7``) where ``LOCKED_MODELS.sh`` uses
    dotted ones (``claude-opus-4.7``), so an exact id hit is usually a reseller.

    Candidates are therefore ranked (canonical provider first, then exact id)
    rather than returning the first hit — an exact reseller match used to win
    over the canonical dashed entry and report that reseller's context window.
    """
    result = RegistryCheckResult(model=locked_model, found=False)

    candidates = [
        (registry_id, info)
        for registry_id, info in registry_index.items()
        if _match_tier(registry_id, locked_model) is not None
    ]

    if not candidates:
        result.notes = "unknown to registry (naming mismatch or too new)"
        return result

    def rank(item):
        registry_id, info = item
        tier = _match_tier(registry_id, locked_model)
        return (
            # Precise matches (exact / dot-dash / ".0") beat the lossy base tier.
            tier >= 3,
            # Within equally precise matches prefer Anthropic itself: a locked id
            # is dotted, so a reseller's verbatim "claude-opus-4.6" (tier 0) is a
            # coincidence, while Anthropic's "claude-opus-4-6" (tier 1) is the
            # real model — and only Anthropic's limits/pricing are authoritative.
            info.provider != CANONICAL_PROVIDER,
            tier,
            registry_id,
        )

    registry_id, info = min(candidates, key=rank)

    result.found = True
    result.in_registry_as = registry_id
    result.provider = info.provider
    result.status = info.status
    result.context_window = info.context_window
    result.cost_input = info.cost_input
    result.cost_output = info.cost_output
    if info.status:
        result.notes = f"Status: {info.status} (found as {registry_id})"
    return result


def format_output_text(
    results: List[RegistryCheckResult],
    locked_models: List[str],
    assignments: Dict[str, str]
) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("Model Registry Drift Check (models.dev)")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    found_count = sum(1 for r in results if r.found)
    lines.append(f"Locked models: {len(locked_models)}")
    lines.append(f"In registry: {found_count}")
    lines.append(f"Not found: {len(results) - found_count}")
    lines.append("")

    # Agent assignments
    lines.append("Agent assignments:")
    for agent, model in sorted(assignments.items()):
        status = next((r.status for r in results if r.model == model), None)
        status_str = f" [STATUS: {status}]" if status else ""
        lines.append(f"  {agent}: {model}{status_str}")
    lines.append("")

    # Model details
    lines.append("Model details:")
    lines.append("-" * 80)
    for result in results:
        status_indicator = "✓ FOUND" if result.found else "✗ NOT FOUND"
        lines.append(f"{result.model}: {status_indicator}")
        if result.found:
            if result.in_registry_as != result.model:
                lines.append(f"  Registry ID: {result.in_registry_as}")
            if result.provider:
                lines.append(f"  Provider: {result.provider}")
            if result.status:
                lines.append(f"  Status: {result.status}")
            if result.context_window:
                lines.append(f"  Context window: {result.context_window:,}")
            if result.cost_input is not None or result.cost_output is not None:
                cost_str = ""
                if result.cost_input is not None:
                    cost_str += f"input=${result.cost_input}/1M"
                if result.cost_output is not None:
                    if cost_str:
                        cost_str += ", "
                    cost_str += f"output=${result.cost_output}/1M"
                if cost_str:
                    lines.append(f"  Pricing: {cost_str}")
        else:
            if result.notes:
                lines.append(f"  Note: {result.notes}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check LOCKED_MODELS.sh against models.dev registry"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON (default: human-readable text)"
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Skip network fetch; use empty fixture"
    )
    args = parser.parse_args()

    try:
        # Parse locked models
        locked_models = _parse_locked_models()
        assignments = _parse_agent_assignments()

        # Fetch registry (or skip if --offline)
        registry_data = None if args.offline else _fetch_models_dev_registry()

        if registry_data is None:
            # No registry to compare against; advisory only.
            registry_index = {}
            offline_note = (
                "(--offline: registry fetch skipped)" if args.offline
                else "(network unavailable — advisory skipped)"
            )
        else:
            registry_index = _build_model_index(registry_data)
            offline_note = ""

        # Check each model
        results = []
        for model in locked_models:
            result = check_model_against_registry(model, registry_index)
            results.append(result)

        # Output
        if args.json:
            output = {
                "offline": args.offline,
                "network_note": offline_note,
                "locked_models_count": len(locked_models),
                "registry_index_size": len(registry_index),
                "found_count": sum(1 for r in results if r.found),
                "results": [asdict(r) for r in results],
                "assignments": assignments,
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_output_text(results, locked_models, assignments))
            if offline_note:
                print(f"\nNote: {offline_note}")

        # Advisory-only: a successful run always reports 0.
        return 0

    except Exception as e:
        # Real crash: report and return 1.
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
