# -*- coding: utf-8 -*-
"""
validate_compatibility.py — Phase 6: Compatibility validation for repo-init.

Checks:
- Tool availability (git, python3, bash, jq, curl, make)
- Model harness (Claude, GPT-5, Local, GitHub Copilot)
- API key presence (boolean only — never logs key values)
- Recommends model adjustments per harness

Author: Senior Engineer
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOLS: list[tuple[str, list[str], bool]] = [
    # (name, check_command, hard_required)
    ("git",     ["git", "--version"],               True),
    ("python3", [sys.executable, "--version"],      True),
    ("bash",    ["bash", "--version"],               False),
    ("jq",      ["jq", "--version"],                False),
    ("curl",    ["curl", "--version"],               False),
    ("make",    ["make", "--version"],               False),
]

# ── API key environment variables per harness ─────────────────────────────────

_HARNESS_ENV_VARS: dict[str, list[str]] = {
    "claude":  ["ANTHROPIC_API_KEY"],
    "gpt5":    ["OPENAI_API_KEY"],
    "local":   [],
    "copilot": ["GH_TOKEN"],
}

# ── Model assignments per harness ─────────────────────────────────────────────

_HARNESS_MODEL_MAPS: dict[str, dict[str, str]] = {
    "claude": {
        "engineer":           "claude-haiku-4.5",
        "senior-engineer":    "claude-sonnet-4.6",
        "lead-engineer":      "claude-sonnet-4.6",
        "quality-engineer":   "claude-sonnet-4.6",
        "security-engineer":  "claude-opus-4.7",
        "principal-engineer": "claude-opus-4.7",
        "orchestrator":       "claude-sonnet-4.6",
    },
    "gpt5": {
        "engineer":           "gpt-4o-mini",
        "senior-engineer":    "gpt-4o",
        "lead-engineer":      "gpt-4o",
        "quality-engineer":   "gpt-4o",
        "security-engineer":  "gpt-4",
        "principal-engineer": "gpt-4",
        "orchestrator":       "gpt-4o",
    },
    "local": {
        "engineer":           "ollama/llama3.2",
        "senior-engineer":    "ollama/llama3.2",
        "lead-engineer":      "ollama/llama3.2",
        "quality-engineer":   "ollama/llama3.2",
        "security-engineer":  "ollama/llama3.1:70b",
        "principal-engineer": "ollama/llama3.1:70b",
        "orchestrator":       "ollama/llama3.2",
    },
    "copilot": {
        "engineer":           "claude-haiku-4.5",
        "senior-engineer":    "claude-sonnet-4.6",
        "lead-engineer":      "claude-sonnet-4.6",
        "quality-engineer":   "claude-sonnet-4.6",
        "security-engineer":  "claude-opus-4.7",
        "principal-engineer": "claude-opus-4.7",
        "orchestrator":       "claude-sonnet-4.6",
    },
}

# ── Quality threshold adjustments per harness and size ───────────────────────

_QUALITY_THRESHOLDS: dict[str, dict[str, int]] = {
    "claude":  {"small": 85, "medium": 85, "large": 70},
    "gpt5":    {"small": 85, "medium": 85, "large": 70},
    "local":   {"small": 70, "medium": 70, "large": 60},
    "copilot": {"small": 85, "medium": 85, "large": 70},
}


# ============================================================================
# RESULT
# ============================================================================

@dataclass
class CompatibilityResult:
    """Result of Phase 6 compatibility validation."""

    harness: str
    hard_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tool_matrix: Dict[str, bool] = field(default_factory=dict)
    api_key_present: bool = False
    missing_env_vars: List[str] = field(default_factory=list)
    model_assignments: Dict[str, str] = field(default_factory=dict)
    quality_threshold: int = 85
    recommended_adjustments: List[str] = field(default_factory=list)
    local_model_server: Optional[str] = None  # "ollama" | "lm-studio" | None

    def format_report(self) -> str:
        """Human-readable compatibility report."""
        lines = [
            "══════════════════════════════════════════════════════",
            " repo-init: Compatibility Validation Report",
            f" Harness: {self.harness}",
            "══════════════════════════════════════════════════════",
            "",
            "TOOL AVAILABILITY",
        ]
        for tool, available in self.tool_matrix.items():
            icon = "✅" if available else ("❌" if tool in ("git", "python3") else "⚠️")
            lines.append(f"  {tool:<10} {icon}")

        lines += ["", f"MODEL HARNESS: {self.harness}"]
        if self.api_key_present:
            lines.append("  API Key     ✅  Present (masked)")
        elif self.missing_env_vars:
            lines.append(f"  API Key     ⚠️  Missing: {', '.join(self.missing_env_vars)}")

        lines += ["", "MODEL ASSIGNMENTS"]
        for role, model in self.model_assignments.items():
            lines.append(f"  {role:<25} {model}")

        lines += ["", f"QUALITY THRESHOLD: {self.quality_threshold}%", ""]

        if self.hard_failures:
            lines.append("HARD FAILURES:")
            for f in self.hard_failures:
                lines.append(f"  ❌ {f}")
            lines += ["", "RESULT: ❌ INCOMPATIBLE"]
        elif self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  ⚠️  {w}")
            lines += ["", "RESULT: ⚠️  COMPATIBLE WITH WARNINGS"]
        else:
            lines += ["RESULT: ✅ FULLY COMPATIBLE"]

        lines.append("══════════════════════════════════════════════════════")
        return "\n".join(lines)


# ============================================================================
# VALIDATOR
# ============================================================================

def validate_compatibility(cfg) -> CompatibilityResult:
    """
    Run all Phase 6 compatibility checks.

    Args:
        cfg: RepoInitConfig (imported lazily to avoid circular import)

    Returns:
        CompatibilityResult
    """
    result = CompatibilityResult(harness=cfg.model_harness)

    # 1. Tool checks
    result.tool_matrix = _check_tools()
    for tool, hard_required, _ in [(t, hr, None) for t, _, hr in _TOOLS]:
        if hard_required and not result.tool_matrix.get(tool, False):
            result.hard_failures.append(
                f"Required tool not found: {tool}. Install it and retry."
            )
        elif not result.tool_matrix.get(tool, False):
            result.warnings.append(
                f"Optional tool not found: {tool}. Some features may be unavailable."
            )

    # 2. Python version check
    if sys.version_info < (3, 8):
        result.hard_failures.append(
            f"Python 3.8+ required. Found: Python {sys.version}. "
            "Upgrade Python and retry."
        )

    # 3. API key / harness checks
    if cfg.model_harness == "local":
        server = _detect_local_model_server()
        result.local_model_server = server
        if server is None:
            result.warnings.append(
                "Local model harness selected but no local server detected "
                "(checked Ollama at localhost:11434 and LM Studio at localhost:1234). "
                "Start your local server before running agents."
            )
    else:
        env_vars = _HARNESS_ENV_VARS.get(cfg.model_harness, [])
        key_present, missing = _check_api_keys(cfg.model_harness)
        result.api_key_present = key_present
        result.missing_env_vars = missing
        if not key_present and missing:
            result.warnings.append(
                f"API key not found for harness '{cfg.model_harness}'. "
                f"Set environment variable(s): {', '.join(missing)}"
            )

    # 4. Model assignments
    size_class = getattr(cfg, "_size_class", "medium")  # Set by bootstrap if available
    result.model_assignments = dict(
        _HARNESS_MODEL_MAPS.get(cfg.model_harness, _HARNESS_MODEL_MAPS["claude"])
    )
    result.quality_threshold = _QUALITY_THRESHOLDS.get(
        cfg.model_harness, _QUALITY_THRESHOLDS["claude"]
    ).get(size_class, 85)

    # 5. Recommendations
    if cfg.model_harness == "local":
        result.recommended_adjustments.append(
            "Local models: quality_threshold reduced to "
            f"{result.quality_threshold}%"
        )
        result.recommended_adjustments.append(
            "Local models: require_spec_compliance disabled "
            "(may exceed context window)"
        )

    return result


# ============================================================================
# HELPERS
# ============================================================================

def _check_tools() -> dict[str, bool]:
    """Run each tool check. Returns {tool_name: available}."""
    matrix: dict[str, bool] = {}
    for name, cmd, _ in _TOOLS:
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            matrix[name] = r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            matrix[name] = False
    return matrix


def _check_api_keys(harness: str) -> tuple[bool, list[str]]:
    """
    Check if required API keys are present.
    NEVER logs key values — only boolean presence.

    Returns: (all_present, missing_vars)
    """
    required = _HARNESS_ENV_VARS.get(harness, [])
    missing = [v for v in required if not os.environ.get(v, "").strip()]
    return len(missing) == 0, missing


def _detect_local_model_server() -> Optional[str]:
    """Detect running local LLM server (Ollama or LM Studio)."""
    # Try Ollama
    try:
        import urllib.request
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        req = urllib.request.urlopen(ollama_host + "/api/tags", timeout=2)
        if req.status == 200:
            return "ollama"
    except Exception:
        pass

    # Try LM Studio
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:1234/v1/models", timeout=2)
        if req.status == 200:
            return "lm-studio"
    except Exception:
        pass

    return None


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 6: Compatibility validation")
    parser.add_argument("--repo-root", required=True, help="Path to target repository")
    parser.add_argument(
        "--model-harness", default="claude",
        choices=list(_HARNESS_ENV_VARS.keys()),
    )
    parser.add_argument("--report", action="store_true", help="Print full report")
    args = parser.parse_args()

    class _FakeCfg:
        model_harness = args.model_harness
        repo_root = Path(args.repo_root)
        _size_class = "medium"

    result = validate_compatibility(_FakeCfg())

    if args.report:
        print(result.format_report())
    else:
        icon = "✅" if not result.hard_failures else "❌"
        print(f"{icon} Harness: {result.harness}")
        print(f"  Hard failures: {len(result.hard_failures)}")
        print(f"  Warnings: {len(result.warnings)}")
        print(f"  API key present: {result.api_key_present}")
        sys.exit(1 if result.hard_failures else 0)
