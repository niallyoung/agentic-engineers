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
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error
from urllib.error import URLError, HTTPError

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
    except (URLError, HTTPError, Exception) as e:
        # Network unavailable — advisory only, return None
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
    def get_base(m: str) -> str:
        # Extract claude-{variant}-{major}
        match = re.match(r"^(claude-[\w]+)-(\d+)", m)
        if match:
            return match.group(1) + "-" + match.group(2)
        return m

    return get_base(registry_id) == get_base(locked_id)


def _build_model_index(registry_data: Dict) -> Dict[str, ModelInfo]:
    """
    Build a searchable index of models from registry.

    Registry structure: { "providers": [ ... ], "models": [ ... ] }
    or { "data": [ ... ] } etc. We look for a list or models/providers structure.
    """
    index = {}

    # Try common structures
    models_list = []
    if isinstance(registry_data, dict):
        if "models" in registry_data and isinstance(registry_data["models"], list):
            models_list = registry_data["models"]
        elif "data" in registry_data and isinstance(registry_data["data"], list):
            models_list = registry_data["data"]
        elif isinstance(registry_data, list):
            models_list = registry_data
        else:
            # Assume top-level is a dict of models keyed by id
            models_list = []
            for key, val in registry_data.items():
                if isinstance(val, dict):
                    if "id" not in val:
                        val["id"] = key
                    models_list.append(val)

    for model in models_list:
        if not isinstance(model, dict):
            continue

        model_id = model.get("id", "")
        if not model_id:
            continue

        # Extract relevant fields
        info = ModelInfo(
            id=model_id,
            name=model.get("name"),
            provider=model.get("provider"),
            status=model.get("status"),
            context_window=model.get("limit", {}).get("output") if isinstance(model.get("limit"), dict) else None,
        )

        # Extract pricing
        if isinstance(model.get("cost"), dict):
            info.cost_input = model["cost"].get("input")
            info.cost_output = model["cost"].get("output")

        index[model_id] = info

    return index


def check_model_against_registry(
    locked_model: str,
    registry_index: Dict[str, ModelInfo]
) -> RegistryCheckResult:
    """Check a single locked model against the registry."""
    result = RegistryCheckResult(model=locked_model, found=False)

    # Exact match
    if locked_model in registry_index:
        info = registry_index[locked_model]
        result.found = True
        result.in_registry_as = locked_model
        result.status = info.status
        result.context_window = info.context_window
        result.cost_input = info.cost_input
        result.cost_output = info.cost_output
        if info.status:
            result.notes = f"Status: {info.status}"
        return result

    # Try normalization: check for .0 variants or base-only matches
    for registry_id, info in registry_index.items():
        if _normalize_model_id(registry_id, locked_model):
            result.found = True
            result.in_registry_as = registry_id
            result.status = info.status
            result.context_window = info.context_window
            result.cost_input = info.cost_input
            result.cost_output = info.cost_output
            if info.status:
                result.notes = f"Status: {info.status} (found as {registry_id})"
            return result

    # Not found
    result.notes = "unknown to registry (naming mismatch or too new)"
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


def main():
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
        registry_data = {} if args.offline else _fetch_models_dev_registry()

        if registry_data is None:
            # Network unavailable; advisory only
            registry_index = {}
            offline_note = "(network unavailable — advisory skipped)"
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

        # Advisory-only: always exit 0
        sys.exit(0)

    except Exception as e:
        # Real crash: report and exit 1
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
