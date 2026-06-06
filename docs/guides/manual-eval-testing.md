# Manual Eval Testing

The functional evals backend invokes a **real** harness (Copilot CLI, OpenCode
CLI, π CLI, or Claude via the Anthropic SDK) with a generated `DELEGATE`,
captures the resulting `HANDBACK`, validates it against the canonical protocol
schema, and grades it against the test case's `expected_contains` /
`expected_not_contains` assertions.

This is the local, manual workflow for running it before any CI integration.

## Prerequisites

- Python 3.7+
- For CLI harnesses: the harness binary installed and authenticated
  (`copilot --version`, `opencode --version`, `pi --version`).
- For the Claude SDK harness (`--harness claude`): `pip install anthropic` and
  set your Anthropic API key in the standard SDK environment variable that the
  `anthropic` package reads (the `ANTHROPIC_*_KEY` Anthropic credential env
  var). Provide it via your shell environment, an `.env` file, or a secrets
  manager — never commit the key value.

If a harness is unavailable (binary not on `PATH`, SDK not installed, or API key
missing), the run **skips** those tests with a clear reason rather than failing
hard.

## Entry point

```
python src/skills/_meta/evaluation_framework/framework.py \
    --run-tests tests/evals/ \
    --harness copilot \
    --min-pass-rate 0.8
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--run-tests PATH` | (required) | Directory or single YAML of eval test cases |
| `--harness NAME` | `copilot` | `copilot`, `opencode`, `pi`, `pi-dev`, or `claude` |
| `--agent NAME` | `engineer` | Agent name passed to the harness (`--agent=`) |
| `--model ALIAS` | `sonnet` | `haiku`, `sonnet`, or `opus` |
| `--min-pass-rate FLOAT` | `0.8` | Run succeeds (exit 0) only if pass rate ≥ this |
| `--max-tests N` | (all) | Run only the first N tests (cost control) |
| `--dry-run` | off | Print what *would* be invoked; **no** API calls / subprocesses |

## To test evals against Copilot CLI

1. Ensure Copilot CLI is installed and authenticated (`copilot --version`).
2. Dry run first (prints what would run, makes no calls):

   ```
   python src/skills/_meta/evaluation_framework/framework.py \
       --run-tests tests/evals/ --harness copilot --max-tests 1 --dry-run
   ```

3. Run for real (1 test, stores the HANDBACK):

   ```
   python src/skills/_meta/evaluation_framework/framework.py \
       --run-tests tests/evals/ --harness copilot --max-tests 1
   ```

4. Inspect the captured HANDBACK:

   ```
   cat artifacts/evals/handbacks/test-delegate-basic-001-copilot-*.yaml
   ```

5. For OpenCode, the same but `--harness opencode`. For π, `--harness pi`.
   For Claude via SDK, `--harness claude` (requires `anthropic` + API key).

## Cost control

- Always start with `--dry-run` to confirm the harness, agent, model, test
  count, and the estimated cost the run prints up front:

  ```
  Est. cost:    ~$0.0300 (~$0.0300/test)
  ```

- Use `--max-tests 1` to invoke only the first test while iterating.
- Cost estimates are rough ballparks for awareness; they are not billing
  accurate.

## What gets stored

Each invoked test writes one artifact to:

```
artifacts/evals/handbacks/{test_id}-{harness}-{timestamp}.yaml
```

It contains the parsed `HANDBACK`, the raw harness output, the validation
errors (if any), which assertions were missing/unexpected, the pass/fail
verdict, and timing. Dry runs do **not** write artifacts.

## Verifying protocol validation

- Every captured HANDBACK is auto-validated by the canonical
  **`protocol-validator`** skill
  (`src/skills/protocol-validator/scripts/protocol_validator.py`), the single
  source of truth shared with the renderer and queue system.
- A test is marked **failed** if the HANDBACK is invalid, **even when the
  harness ran successfully**. The validation errors are recorded in the stored
  artifact under `validation_errors`.

## Reading the result line

```
Test result: 2/3 passed (67%), 1 skipped
FAIL: 67% < required 80%
```

- `passed/graded` counts only non-skipped tests.
- Skipped tests (harness unavailable) are reported separately and do not count
  toward the pass rate denominator.
- Exit code is `0` when pass rate ≥ `--min-pass-rate`, else `1`.

## Compatibility-matrix path (separate, hermetic)

The older `TestRunner` compatibility-matrix path is intentionally **hermetic by
default**: it does not spawn real harnesses unless you opt in with
`EVALS_LIVE=1` (or `TestRunner(live=True)`). This keeps unit tests fast and
side-effect-free. The functional eval path above (`--run-tests`) always invokes
for real regardless of `EVALS_LIVE`.

## Later: CI integration (not yet wired)

When ready, add a non-blocking GitHub Actions workflow (e.g.
`evals-on-demand.yml`) triggered on PR or `workflow_dispatch` that runs:

```
python src/skills/_meta/evaluation_framework/framework.py \
    --run-tests tests/evals/ --harness copilot --min-pass-rate 0.9
```

and uploads `artifacts/evals/handbacks/` as a build artifact. Keep it
non-blocking until the signal is trusted.
