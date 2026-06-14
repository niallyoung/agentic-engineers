# Codex Renderer Handoff

Date: 2026-06-14
Branch: `feature/codex-renderer`

## Status

Initial Codex harness support is implemented behind explicit targets:

- `make render-codex`
- `make install-codex`
- `make uninstall-codex`
- `make validate-codex`

`make render-all` now includes Codex render output. `make install` still installs
the existing default harness set only (`claude`, `copilot`, `pi`, `opencode`) so
we do not unexpectedly write to a user's `~/.codex` during the first rollout.

## Rendered Layout

Render output:

```text
dist/codex/
  AGENTS.md
  config.toml
  agents/*.toml
  skills/*/SKILL.md
```

Install output:

```text
~/.codex/
  AGENTS.md
  config.toml or agentic-engineers.config.toml
  agents/*.toml
~/.agents/skills/
  */SKILL.md
```

The renderer is marker-aware:

- agent manifest: `.codex/agents/.agentic-engine-codex`
- skill marker: `.agents/skills/<skill>/.agentic-engine-codex`
- foreign `config.toml` is preserved; a managed `agentic-engineers.config.toml`
  reference is written instead.

## Permission Guidance

Recommended default:

```bash
codex --sandbox workspace-write --ask-for-approval on-request
```

Autopilot-style disposable self-test:

```bash
codex exec --sandbox workspace-write --ask-for-approval never "<task>"
```

True YOLO/full access:

```bash
codex --dangerously-bypass-approvals-and-sandbox
```

Use full access only in externally isolated temp clones/containers with no real
secrets or mounted home config.

## Verification Run

Completed locally:

```bash
python3 -m pytest tests/test_codex_renderer.py -q
make render-all
make validate-renders
python3 -m pytest tests/test_codex_renderer.py tests/test_harness_toggle.py tests/test_model_naming_compliance.py tests/test_model_compatibility_matrix.py -q
make install-codex DESTDIR=/tmp/ae-codex-install BACKUP=never
make validate-codex
```

Notes:

- `make render-all` needed elevated permission in this Codex sandbox because
  existing non-Codex renderers write `.git/config` to install hooks.
- `make validate-renders` reports stale dist warnings for older removed skills
  in some non-Codex harness outputs, but all current source skills validate
  across `claude`, `copilot`, `opencode`, and `codex`.

## Next Steps

1. Try a real install when ready:

   ```bash
   make install-codex
   ```

2. Start Codex with the safe default:

   ```bash
   codex --sandbox workspace-write --ask-for-approval on-request
   ```

3. Smoke-test orchestration prompt:

   ```text
   Use the agentic-engineers orchestrator. Create DELEGATEs for this work,
   spawn specialist agents where independent, wait for HANDBACKs, then
   summarize status.
   ```

4. Decide whether Codex should join default `make install` after a real-user
   install pass validates that foreign config preservation is comfortable.

5. Broaden legacy matrix tests only after making Codex part of the default
   all-harness contract. Tests currently hard-code the four default harnesses in
   places such as install correctness, backup harnesses, and workflow matrix
   sizing.

