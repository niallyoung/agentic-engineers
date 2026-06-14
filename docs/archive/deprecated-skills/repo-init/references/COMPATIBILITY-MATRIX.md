# repo-init: Compatibility Matrix

**Purpose:** Defines all compatibility checks performed during Phase 6.  
**Version:** 1.0

---

## Tool Availability Matrix

These checks run as subprocess calls with a 5-second timeout.

| Tool | Command | Hard Required | Failure Action |
|------|---------|---------------|----------------|
| `git` | `git --version` | ✅ YES | ABORT — cannot proceed without git |
| `python3` | `python3 -c "import sys; assert sys.version_info >= (3,8)"` | ✅ YES | ABORT — Python ≥ 3.8 required |
| `bash` | `bash --version` | ⚠️ SOFT | WARN — some scripts may not work |
| `jq` | `jq --version` | ⚠️ SOFT | WARN — skip JSON features |
| `curl` | `curl --version` | ⚠️ SOFT | WARN — skip remote checks |
| `make` | `make --version` | ⚠️ SOFT | WARN — Makefile targets unavailable |

---

## Model Harness Compatibility

### Claude (Anthropic)

| Feature | Status | Notes |
|---------|--------|-------|
| Tool use | ✅ Full | All tool types supported |
| Long context | ✅ 200k tokens | claude-opus-4.8, sonnet |
| Structured output | ✅ Full | JSON mode + tool_use |
| Function calling | ✅ Full | |
| Streaming | ✅ Full | |
| Multi-turn | ✅ Full | |
| Cost | 💰 Paid | haiku < sonnet < opus |
| Privacy | ☁️ Cloud | Data sent to Anthropic |
| API key env var | `ANTHROPIC_API_KEY` | |
| Min recommended model | `claude-haiku-4.5` | For engineer role |

**Harness-specific adjustments:** None (Claude is the reference harness)

---

### GPT-5 (OpenAI)

| Feature | Status | Notes |
|---------|--------|-------|
| Tool use | ✅ Full | function_call / tools API |
| Long context | ✅ 128k tokens | gpt-4-turbo and above |
| Structured output | ✅ Full | JSON mode |
| Function calling | ✅ Full | |
| Streaming | ✅ Full | |
| Multi-turn | ✅ Full | |
| Cost | 💰 Paid | gpt-4o-mini < gpt-4o < gpt-4 |
| Privacy | ☁️ Cloud | Data sent to OpenAI |
| API key env var | `OPENAI_API_KEY` | |
| Min recommended model | `gpt-4o-mini` | For engineer role |

**Harness-specific adjustments:**

```yaml
# Applied to config.yaml when model_harness = "gpt5"
agents:
  engineer:
    model: gpt-4o-mini    # replaces claude-haiku-4.5
  senior-engineer:
    model: gpt-4o         # replaces claude-sonnet-4.6
  lead-engineer:
    model: gpt-4o         # replaces claude-sonnet-4.6
  principal-engineer:
    model: gpt-4          # replaces claude-opus-4.8
```

---

### Local Models (Ollama / LM Studio)

| Feature | Status | Notes |
|---------|--------|-------|
| Tool use | ⚠️ Model-dependent | Only some models support tools |
| Long context | ⚠️ Varies | 4k–128k depending on model |
| Structured output | ⚠️ Model-dependent | JSON mode on select models |
| Function calling | ⚠️ Model-dependent | |
| Streaming | ✅ Full | All local servers support streaming |
| Multi-turn | ✅ Full | |
| Cost | 🆓 Free | Local compute only |
| Privacy | ✅ Local | No data leaves machine |
| Detection | `OLLAMA_HOST` env or `http://localhost:11434` | |
| Fallback detection | `http://localhost:1234` (LM Studio) | |

**Harness-specific adjustments (conservative for local):**

```yaml
# Applied to config.yaml when model_harness = "local"
agents:
  engineer:
    model: ollama/llama3.2      # configurable
  senior-engineer:
    model: ollama/llama3.2
  lead-engineer:
    model: ollama/llama3.2
  principal-engineer:
    model: ollama/llama3.1:70b  # needs large model for architecture

quality_gate:
  min_coverage: 70             # Reduced (local models less reliable for tests)
  require_spec_compliance: false   # May exceed context window
```

**Tool use support by model (Ollama):**

| Model | Tool Use | Structured Output |
|-------|----------|-------------------|
| llama3.2 | ✅ Yes | ✅ Yes |
| llama3.1 | ✅ Yes | ✅ Yes |
| mistral | ⚠️ Partial | ⚠️ Partial |
| codellama | ❌ No | ⚠️ Partial |
| phi3 | ✅ Yes | ✅ Yes |
| gemma2 | ⚠️ Partial | ⚠️ Partial |

---

### GitHub Copilot CLI

| Feature | Status | Notes |
|---------|--------|-------|
| Tool use | ✅ Full | Via Copilot tool protocol |
| Long context | ✅ 200k+ | Model-dependent |
| Structured output | ✅ Full | |
| Cost | 💰 Subscription | Copilot license required |
| Privacy | ☁️ Cloud | GitHub/Microsoft hosted |
| Detection | `.copilot/` directory present | Or `GH_TOKEN` + copilot scope |

**GitHub Copilot is the primary harness for agentic-engineers** (this framework).
All other harnesses are supported as targets when running repo-init on external repos.

---

## API Key Check Procedure

```python
HARNESS_ENV_VARS = {
    "claude": ["ANTHROPIC_API_KEY"],
    "gpt5": ["OPENAI_API_KEY"],
    "local": [],   # No key needed
    "copilot": ["GH_TOKEN"],
}

def check_api_keys(harness: str) -> tuple[bool, list[str]]:
    """
    Returns (key_present: bool, missing_vars: list[str]).
    NEVER logs key values — only boolean presence.
    """
    required = HARNESS_ENV_VARS.get(harness, [])
    missing = [v for v in required if not os.environ.get(v, "").strip()]
    return len(missing) == 0, missing
```

If keys are missing:
- Hard failure: NO (key absence never aborts init)
- Warning emitted: YES — with the variable name but NOT the value
- Adjustment: `api_key_present: false` in INIT-COMPLETE.yaml

---

## Compatibility Validation Report Format

When run with `--report` flag, Phase 6 outputs:

```
══════════════════════════════════════════════════════
 repo-init: Compatibility Validation Report
 Project: my-api | Harness: claude | Date: 2025-05-09
══════════════════════════════════════════════════════

TOOL AVAILABILITY
  git        ✅  git version 2.44.0
  python3    ✅  Python 3.11.5
  bash       ✅  GNU bash, version 5.2.26
  jq         ✅  jq-1.7.1
  curl       ✅  curl 8.7.1
  make       ✅  GNU Make 3.81

MODEL HARNESS: claude
  API Key     ✅  ANTHROPIC_API_KEY present (masked)
  Min Model   ✅  claude-haiku-4.5 available

HARD FAILURES: none
WARNINGS: none

 RESULT: ✅ FULLY COMPATIBLE
   All checks passed. Recommended configuration:
   - engineer model: claude-haiku-4.5
   - senior model:   claude-sonnet-4.6
   - lead model:     claude-sonnet-4.6
   - principal model: claude-opus-4.6
   - quality_threshold: 85%
══════════════════════════════════════════════════════
```

---

## Compatibility Error Messages

| Error | Message | Action |
|-------|---------|--------|
| git not found | `git not found in PATH. Install git and retry.` | ABORT |
| Python < 3.8 | `Python 3.8+ required. Found: Python {version}` | ABORT |
| No API key | `ANTHROPIC_API_KEY not set. Set env var and retry, or use --model-harness local` | WARN |
| Ollama not running | `Ollama not found at localhost:11434. Start Ollama: ollama serve` | WARN |
| bash not found | `bash not found; some shell scripts will not work` | WARN |
| jq not found | `jq not found; JSON output features disabled` | WARN |

---

## Adding a New Harness

To add support for a new model harness (e.g., Gemini):

1. Add to `HARNESS_ENV_VARS` in `validate_compatibility.py`:
   ```python
   "gemini": ["GOOGLE_API_KEY"],
   ```

2. Add model mapping in `generate_spec.py`:
   ```python
   HARNESS_MODEL_MAPS["gemini"] = {
       "engineer": "gemini-2.0-flash",
       "senior-engineer": "gemini-1-5-pro",
       "lead-engineer": "gemini-1-5-pro",
       "principal-engineer": "gemini-2-pro",
   }
   ```

3. Add compatibility table entry in this document.

4. Add test cases in `tests/test_repo_init.py`:
   ```python
   def test_validate_compat_gemini_sets_correct_models():
       ...
   ```
