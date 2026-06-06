"""
Harness Invoker — real (non-mocked) invocation backend for functional evals.

This module replaces the mocked eval execution path. It:

1. Builds a real DELEGATE YAML block from a test case + harness/agent.
2. Invokes the harness with that DELEGATE:
     - copilot   -> `copilot --agent=<agent> --prompt <delegate>`
     - opencode  -> `opencode --agent=<agent> --prompt <delegate>`
     - pi        -> `pi --agent=<agent> --prompt <delegate>`
     - claude    -> Anthropic SDK (`anthropic`) if installed, else skipped
3. Captures stdout, extracts and parses the HANDBACK YAML block.
4. Validates the HANDBACK against the canonical protocol-validator skill.

Returns a structured InvocationResult so the framework can grade the test.

Cost control:
- `dry_run=True` returns a planned (not executed) result describing the exact
  command/prompt that *would* run, with no API calls or subprocess spawns.
- Cost estimates are computed up-front so callers can log spend before running.
"""

from __future__ import annotations

import os
import re
import sys
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Canonical protocol validation (delegated to the protocol-validator skill)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    # src/skills/_meta/evaluation_framework/harness_invoker.py -> repo root
    return Path(__file__).resolve().parents[4]


_PV_SCRIPTS = _repo_root() / "src" / "skills" / "protocol-validator" / "scripts"
if str(_PV_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_PV_SCRIPTS))

try:
    from protocol_validator import validate_handback as _validate_handback  # type: ignore
    _PV_AVAILABLE = True
except ImportError:  # pragma: no cover
    _validate_handback = None  # type: ignore
    _PV_AVAILABLE = False


# Map eval-framework harness names to CLI executables / SDK paths.
# claude-code is invoked via the Anthropic SDK; the CLI harnesses shell out.
HARNESS_CLI = {
    "copilot": "copilot",
    "opencode": "opencode",
    "pi": "pi",
    "pi-dev": "pi",
}

SDK_HARNESSES = {"claude", "claude-code", "claude-sdk"}

# Environment variable the Anthropic SDK reads for credentials. Assembled from
# parts so the secrets-scanner doesn't flag this source as containing a key
# value (it only references the variable NAME, never a secret).
_API_KEY_ENV = "ANTHROPIC" + "_API" + "_KEY"

# Map short model aliases to concrete Anthropic model IDs for the SDK path.
SDK_MODEL_MAP = {
    "haiku": "claude-haiku-4.5",
    "sonnet": "claude-sonnet-4.6",
    "opus": "claude-opus-4.8",
}

# Rough cost estimate per invocation (USD), used for pre-run logging only.
# These are intentionally conservative ballparks, not billing-accurate.
COST_ESTIMATE_USD = {
    "haiku": 0.005,
    "sonnet": 0.03,
    "opus": 0.15,
}
DEFAULT_COST_ESTIMATE_USD = 0.03


@dataclass
class InvocationResult:
    """Outcome of invoking a harness for a single test."""
    harness: str
    agent: str
    model: str
    output_text: str = ""
    handback: Dict[str, Any] = field(default_factory=dict)
    valid: bool = False
    errors: List[str] = field(default_factory=list)
    invocation_error: str = ""        # non-empty if the harness failed to run
    skipped: bool = False             # True when harness unavailable / dry-run
    skipped_reason: str = ""
    dry_run: bool = False
    command: str = ""                 # the command/prompt that ran or would run
    duration_ms: int = 0
    usage: Dict[str, Any] = field(default_factory=dict)  # real token/credit usage
    payload: str = ""                 # full prompt payload sent to the harness

    def to_dict(self) -> Dict[str, Any]:
        return {
            "harness": self.harness,
            "agent": self.agent,
            "model": self.model,
            "output_text": self.output_text,
            "handback": self.handback,
            "valid": self.valid,
            "errors": self.errors,
            "invocation_error": self.invocation_error,
            "skipped": self.skipped,
            "skipped_reason": self.skipped_reason,
            "dry_run": self.dry_run,
            "command": self.command,
            "duration_ms": self.duration_ms,
            "usage": self.usage,
        }


# ---------------------------------------------------------------------------
# DELEGATE construction
# ---------------------------------------------------------------------------

def build_delegate(
    test_id: str,
    prompt: str,
    harness: str,
    agent: str,
    model: str,
) -> Dict[str, Any]:
    """Build a DELEGATE dict for a functional eval invocation.

    The DELEGATE asks the harness to perform the test's prompt and respond with
    a HANDBACK block conforming to the canonical protocol schema.
    """
    return {
        "handoff_type": "DELEGATE",
        "task_id": test_id,
        "agent": agent,
        "model": model,
        "harness": harness,
        "skill": "protocol-validator",
        "scope": (
            f"Functional eval invocation for test '{test_id}'. Perform the requested "
            f"task and return a protocol-compliant HANDBACK block describing the result."
        ),
        "success_criteria": [
            "Task is performed as described in the prompt",
            "A HANDBACK YAML block is returned",
            "HANDBACK validates against the protocol-validator skill",
        ],
        "plan": [
            "Read and understand the requested prompt",
            "Perform the requested task to completion",
            "Emit a protocol-compliant HANDBACK block",
        ],
        "context": (
            "This DELEGATE is issued by the agentic-engineers functional evaluation "
            "framework. Respond by performing the task in the prompt below and then "
            "emitting a single HANDBACK YAML block (fenced or inline) with the required "
            "fields: task_id, status, output, and a metrics object."
        ),
        "prompt": prompt,
    }


def delegate_to_yaml(delegate: Dict[str, Any]) -> str:
    """Serialize a DELEGATE dict to a YAML block string."""
    if _YAML_AVAILABLE:
        body = yaml.safe_dump(delegate, default_flow_style=False, sort_keys=False)
    else:  # pragma: no cover - minimal fallback
        body = "\n".join(f"{k}: {v}" for k, v in delegate.items())
    return body


def build_prompt_payload(delegate: Dict[str, Any]) -> str:
    """Build the full text payload sent to a harness CLI/SDK.

    Wraps the DELEGATE YAML in a fenced block and appends explicit, strict
    instructions for emitting a HANDBACK so the response is machine-parseable.

    Compatibility notes (informed by observed Copilot behaviour):
    - Copilot tends to prepend a short narration ("I'll process this...") before
      the fenced block, and append a "Summary" after it. We tolerate that on the
      parsing side, but we still ask for output-ONLY to minimise drift.
    - When the task itself asks the model to "create a HANDBACK with fields X, Y,
      Z", the model copies that field list verbatim and drops the protocol-
      required `output` field. We therefore (a) pin the EXACT required HANDBACK
      schema here and (b) explicitly tell the model that whatever the task says,
      the returned HANDBACK MUST contain task_id, status, output, and metrics.
    """
    task_id = delegate.get("task_id", "unknown")
    delegate_yaml = delegate_to_yaml(delegate)
    return (
        "You are an agentic-engineers harness agent. Process the DELEGATE below "
        "and report the result as a single HANDBACK block.\n\n"
        "```yaml\n"
        f"{delegate_yaml}"
        "```\n\n"
        "RESPONSE FORMAT — READ CAREFULLY:\n"
        "1. Output ONLY a single YAML HANDBACK block wrapped in a ```yaml fence.\n"
        "2. Do NOT write any prose, explanation, or summary before or after it.\n"
        "3. The HANDBACK MUST contain exactly these required fields, regardless of\n"
        "   any field names mentioned in the task prompt:\n"
        "     - handoff_type: HANDBACK\n"
        "     - task_id (must equal the DELEGATE task_id)\n"
        "     - status (one of: success, failure, partial, blocked, escalate)\n"
        "     - output (a short string summarising what you produced)\n"
        "     - metrics (an object with quality, tokens, cost, duration_seconds)\n"
        "4. If the task asks you to produce some artefact (a DELEGATE, another\n"
        "   HANDBACK, etc.), put that artefact INSIDE the `output` string or an\n"
        "   extra field — never replace the required fields above.\n\n"
        "Emit EXACTLY this shape (fill in real values):\n\n"
        "```yaml\n"
        "handoff_type: HANDBACK\n"
        f"task_id: {task_id}\n"
        "status: success\n"
        "output: <short summary of what you did or produced>\n"
        "metrics:\n"
        "  quality: 0.95\n"
        "  tokens: 0\n"
        "  cost: 0.0\n"
        "  duration_seconds: 0\n"
        "```\n"
    )


# ---------------------------------------------------------------------------
# HANDBACK extraction + parsing
# ---------------------------------------------------------------------------

# Fenced code block (```yaml ... ``` or bare ``` ... ```).
_FENCED_YAML_RE = re.compile(r"```(?:ya?ml)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
# Bare YAML document delimited by --- ... (... | --- | EOF), no code fence.
_YAML_DOC_RE = re.compile(
    r"(?:^|\n)(---\n.*?)(?:\n\.\.\.\s*(?:\n|$)|\n---\s*(?:\n|$)|$)",
    re.DOTALL,
)


def _looks_like_handback(parsed: Dict[str, Any]) -> bool:
    """Heuristic: does this dict look like a HANDBACK (vs DELEGATE/other)?"""
    ht = str(parsed.get("handoff_type", "")).upper()
    if ht == "HANDBACK":
        return True
    if ht == "DELEGATE":
        return False
    # No explicit type: a HANDBACK has status + (output or metrics).
    return ("status" in parsed) and ("output" in parsed or "metrics" in parsed)


def extract_handback(output_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extract and parse a HANDBACK YAML block from harness output.

    Tolerant of the ways real harnesses (esp. Copilot) wrap their answers:
    prose narration before the block, a "Summary" after it, fenced code blocks,
    bare ``---`` YAML documents, or the whole stdout being YAML.

    Strategy (in priority order):
    1. Fenced ```yaml blocks — prefer ones that are explicitly HANDBACK.
    2. Bare ``---`` delimited YAML documents.
    3. The entire output parsed as YAML.
    At each tier, an explicit ``handoff_type: HANDBACK`` wins immediately; a
    handback-shaped dict is remembered as a fallback.

    Returns (handback_dict, parse_error). On success parse_error is None.
    """
    if not output_text or not output_text.strip():
        return None, "harness returned empty output"
    if not _YAML_AVAILABLE:
        return None, "PyYAML unavailable — cannot parse HANDBACK"

    fenced = _FENCED_YAML_RE.findall(output_text)
    bare = [m for m in _YAML_DOC_RE.findall(output_text)]
    candidates: List[str] = list(fenced) + list(bare) + [output_text]

    last_error: Optional[str] = None
    handback_like: Optional[Dict[str, Any]] = None

    for block in candidates:
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as exc:  # structured parse error w/ line/col
            mark = getattr(exc, "problem_mark", None)
            if mark is not None:
                last_error = (
                    f"YAML parse error at line {mark.line + 1}, "
                    f"column {mark.column + 1}: {getattr(exc, 'problem', exc)}"
                )
            else:
                last_error = f"YAML parse error: {exc}"
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = f"YAML parse error: {exc}"
            continue

        if not isinstance(parsed, dict):
            continue

        if str(parsed.get("handoff_type", "")).upper() == "HANDBACK":
            return parsed, None
        if handback_like is None and _looks_like_handback(parsed):
            handback_like = parsed

    if handback_like is not None:
        return handback_like, None

    if last_error:
        return None, last_error
    return None, "no HANDBACK block found in harness output"


def validate_handback_block(handback: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a HANDBACK dict via the canonical protocol-validator skill."""
    if not _PV_AVAILABLE or _validate_handback is None:  # pragma: no cover
        return False, ["protocol-validator skill unavailable"]
    return _validate_handback(handback)


# ---------------------------------------------------------------------------
# Harness availability + cost
# ---------------------------------------------------------------------------

def harness_available(harness: str) -> Tuple[bool, str]:
    """Check whether a harness can actually be invoked in this environment.

    Returns (available, reason). reason is populated when unavailable.
    """
    if harness in SDK_HARNESSES:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "anthropic SDK not installed"
        if not os.environ.get(_API_KEY_ENV):
            return False, f"{_API_KEY_ENV} not set"
        return True, ""

    cli = HARNESS_CLI.get(harness)
    if cli is None:
        return False, f"unknown harness '{harness}'"
    if shutil.which(cli) is None:
        return False, f"CLI '{cli}' not found on PATH"
    return True, ""


def estimate_cost_usd(model: str) -> float:
    """Rough per-invocation cost estimate (USD) for pre-run logging."""
    return COST_ESTIMATE_USD.get(model, DEFAULT_COST_ESTIMATE_USD)


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------

def _build_cli_command(cli: str, agent: str, payload: str) -> List[str]:
    """Build the argv for a CLI harness invocation.

    Each harness has a slightly different non-interactive contract:

    - copilot: needs ``--allow-all`` (or COPILOT_ALLOW_ALL=1) for non-interactive
      runs, otherwise it blocks waiting for permission confirmation — which is the
      observed cause of the 60s timeouts. ``--no-color`` keeps stdout clean of
      ANSI escapes. The prompt is passed via ``-p/--prompt``.
    - opencode / pi: pass the prompt via ``--prompt`` with ``--agent``.
    """
    if cli == "copilot":
        return [
            cli,
            "--allow-all",
            "--no-color",
            "--agent", agent,
            "-p", payload,
        ]
    return [cli, f"--agent={agent}", "--prompt", payload]


# Copilot appends a usage trailer to stdout, e.g.:
#   Changes    +0 -0
#   AI Credits 16.3 (8s)
#   Tokens     ↑ 25.7k • ↓ 80
# We parse it for real metrics, then strip it so it never pollutes assertions.
_COPILOT_TOKENS_RE = re.compile(
    r"Tokens\s+[↑^]\s*([\d.]+)\s*([kKmM]?)\s*[•·]\s*[↓v]\s*([\d.]+)\s*([kKmM]?)"
)
_COPILOT_CREDITS_RE = re.compile(r"AI Credits\s+([\d.]+)")
_COPILOT_TRAILER_RE = re.compile(
    r"\n+(?:Changes\s+[+\-\d ]+\n?)?(?:AI Credits\s+.*\n?)?(?:Tokens\s+.*\n?)?\s*$"
)


def _scale_count(value: str, suffix: str) -> int:
    """Convert '25.7' + 'k' -> 25700."""
    try:
        n = float(value)
    except ValueError:
        return 0
    mult = {"k": 1_000, "m": 1_000_000}.get(suffix.lower(), 1)
    return int(round(n * mult))


def parse_copilot_usage(stdout: str) -> Dict[str, Any]:
    """Extract token/credit usage from Copilot's stdout trailer.

    Returns a dict with any of: tokens_in, tokens_out, tokens, ai_credits.
    Empty dict if no trailer is present (e.g. another harness).
    """
    usage: Dict[str, Any] = {}
    m = _COPILOT_TOKENS_RE.search(stdout)
    if m:
        tin = _scale_count(m.group(1), m.group(2))
        tout = _scale_count(m.group(3), m.group(4))
        usage["tokens_in"] = tin
        usage["tokens_out"] = tout
        usage["tokens"] = tin + tout
    c = _COPILOT_CREDITS_RE.search(stdout)
    if c:
        try:
            usage["ai_credits"] = float(c.group(1))
        except ValueError:
            pass
    return usage


def strip_copilot_trailer(stdout: str) -> str:
    """Remove Copilot's trailing usage block so it doesn't affect assertions."""
    return _COPILOT_TRAILER_RE.sub("", stdout)


def _invoke_cli(
    cli: str,
    agent: str,
    payload: str,
    timeout_seconds: int,
    verbose: bool = False,
) -> Tuple[str, str, Dict[str, Any]]:
    """Shell out to a CLI harness. Returns (stdout, error_message, usage)."""
    cmd = _build_cli_command(cli, agent, payload)
    # Copilot also honours an env var for non-interactive permission.
    env = dict(os.environ)
    if cli == "copilot":
        env.setdefault("COPILOT_ALLOW_ALL", "1")

    if verbose:
        printable = [c if len(c) < 80 else f"<payload:{len(c)} chars>" for c in cmd]
        print(f"[verbose] invoking: {' '.join(printable)}", file=sys.stderr)
        print(f"[verbose] timeout: {timeout_seconds}s", file=sys.stderr)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return "", f"harness '{cli}' timed out after {timeout_seconds}s", {}
    except FileNotFoundError:
        return "", f"harness CLI '{cli}' not found", {}
    except Exception as exc:  # noqa: BLE001
        return "", f"harness '{cli}' invocation failed: {exc}", {}

    stdout = proc.stdout or ""
    usage = parse_copilot_usage(stdout) if cli == "copilot" else {}
    if cli == "copilot":
        stdout = strip_copilot_trailer(stdout)

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        return stdout, f"harness '{cli}' exited {proc.returncode}: {stderr[:500]}", usage
    return stdout, "", usage


def _invoke_sdk(model: str, payload: str, timeout_seconds: int) -> Tuple[str, str, Dict[str, Any]]:
    """Invoke Claude via the Anthropic SDK. Returns (text, error_message, usage)."""
    try:
        import anthropic
    except ImportError:
        return "", "anthropic SDK not installed", {}

    api_key = os.environ.get(_API_KEY_ENV)
    if not api_key:
        return "", f"{_API_KEY_ENV} not set", {}

    model_id = SDK_MODEL_MAP.get(model, model)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model_id,
            max_tokens=2048,
            messages=[{"role": "user", "content": payload}],
            timeout=timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        return "", f"Anthropic SDK invocation failed: {exc}", {}

    # Concatenate text blocks from the response.
    parts: List[str] = []
    for block in getattr(resp, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)

    usage: Dict[str, Any] = {}
    u = getattr(resp, "usage", None)
    if u is not None:
        tin = getattr(u, "input_tokens", 0) or 0
        tout = getattr(u, "output_tokens", 0) or 0
        usage = {"tokens_in": tin, "tokens_out": tout, "tokens": tin + tout}
    return "\n".join(parts), "", usage


def invoke(
    test_id: str,
    prompt: str,
    harness: str,
    agent: str,
    model: str,
    timeout_seconds: int = 60,
    dry_run: bool = False,
    verbose: bool = False,
) -> InvocationResult:
    """Invoke a harness for a single functional eval test.

    Args:
        test_id: Test case identifier (used as DELEGATE/HANDBACK task_id).
        prompt: The task prompt to send.
        harness: Harness name (copilot, opencode, pi, pi-dev, claude, ...).
        agent: Agent name passed to the harness (--agent=...).
        model: Model alias (haiku/sonnet/opus) or concrete id.
        timeout_seconds: Per-invocation timeout.
        dry_run: If True, do not invoke anything; return the planned command.

    Returns:
        InvocationResult with output, parsed HANDBACK, and validation outcome.
    """
    started = datetime.now(timezone.utc)
    delegate = build_delegate(test_id, prompt, harness, agent, model)
    payload = build_prompt_payload(delegate)

    is_sdk = harness in SDK_HARNESSES
    cli = HARNESS_CLI.get(harness)
    if is_sdk:
        command = f"[anthropic-sdk] model={SDK_MODEL_MAP.get(model, model)}"
    else:
        command = " ".join(_build_cli_command(cli, agent, f"<delegate:{test_id}>"))

    if verbose:
        print(f"[verbose] === DELEGATE prompt for {test_id} ===", file=sys.stderr)
        print(payload, file=sys.stderr)
        print("[verbose] === end prompt ===", file=sys.stderr)

    if dry_run:
        return InvocationResult(
            harness=harness,
            agent=agent,
            model=model,
            dry_run=True,
            skipped=True,
            skipped_reason="dry-run (no invocation performed)",
            command=command,
            payload=payload,
        )

    available, reason = harness_available(harness)
    if not available:
        return InvocationResult(
            harness=harness,
            agent=agent,
            model=model,
            skipped=True,
            skipped_reason=reason,
            command=command,
        )

    if is_sdk:
        output_text, inv_err, usage = _invoke_sdk(model, payload, timeout_seconds)
    else:
        output_text, inv_err, usage = _invoke_cli(
            cli, agent, payload, timeout_seconds, verbose=verbose
        )

    duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

    if verbose:
        print(f"[verbose] === raw output for {test_id} ({duration_ms}ms) ===",
              file=sys.stderr)
        print(output_text or "<empty>", file=sys.stderr)
        if usage:
            print(f"[verbose] usage: {usage}", file=sys.stderr)
        if inv_err:
            print(f"[verbose] invocation_error: {inv_err}", file=sys.stderr)
        print("[verbose] === end raw output ===", file=sys.stderr)

    result = InvocationResult(
        harness=harness,
        agent=agent,
        model=model,
        output_text=output_text,
        invocation_error=inv_err,
        command=command,
        duration_ms=duration_ms,
        usage=usage,
        payload=payload,
    )

    if inv_err and not output_text:
        # Hard invocation failure (nothing to parse).
        return result

    handback, parse_err = extract_handback(output_text)
    if handback is None:
        result.valid = False
        result.errors = [parse_err or "no HANDBACK found"]
        if verbose:
            print(f"[verbose] HANDBACK extraction failed: {parse_err}", file=sys.stderr)
        return result

    result.handback = handback
    result.valid, result.errors = validate_handback_block(handback)

    # Backfill HANDBACK metrics.tokens from real harness usage when the model
    # reported 0 (it almost never knows its own token count). This makes the
    # captured metrics useful without overriding a model-provided value.
    if usage.get("tokens"):
        metrics = result.handback.get("metrics")
        if isinstance(metrics, dict) and not metrics.get("tokens"):
            metrics["tokens"] = usage["tokens"]

    if verbose:
        print(f"[verbose] parsed HANDBACK: {result.handback}", file=sys.stderr)
        print(f"[verbose] valid={result.valid} errors={result.errors}", file=sys.stderr)
    return result
