# Codex Renderer Handoff

Date: 2026-06-14
Branch: `feature/codex-renderer`

## Status

Codex harness support is implemented behind explicit targets and remains an
opt-in install path:

- `make render-codex`
- `make install-codex`
- `make uninstall-codex`
- `make validate-codex`

`make render-all` now includes Codex render output. `make install` still installs
the existing default harness set only (`claude`, `copilot`, `pi`, `opencode`),
while `make install-codex` keeps Codex explicit and workspace-managed.

The second pass adds a native Codex startup profile:

```bash
codex --profile agentic-engineers-orchestrator --sandbox workspace-write --ask-for-approval on-request
```

Codex does not currently expose `--agent orchestrator`. The profile is the
supported CLI startup equivalent: it layers Orchestrator `developer_instructions`
over the base config and keeps custom specialist agents available for spawned
subagent work.

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
  agentic-engineers-orchestrator.config.toml
  agents/*.toml
  skills/
  */SKILL.md
```

The renderer is marker-aware:

- agent manifest: `.codex/agents/.agentic-engine-codex`
- skill marker: `.codex/skills/<skill>/.agentic-engine-codex`
- foreign `config.toml` is preserved; a managed `agentic-engineers.config.toml`
  reference is written instead.

## Permission Guidance

Recommended default:

```bash
codex --profile agentic-engineers-orchestrator --sandbox workspace-write --ask-for-approval on-request
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

2. Start Codex with the Orchestrator profile and safe permissions:

   ```bash
   codex --profile agentic-engineers-orchestrator --sandbox workspace-write --ask-for-approval on-request
   ```

3. Smoke-test terse delegation:

   ```text
   delegate: inspect the renderer for missing Codex startup integration; review
   the generated custom-agent HANDBACK contract; update docs for the launch flow
   ```

   Expected behavior: the root Codex session parses each semicolon-separated
   task as a DELEGATE, routes it to the narrowest rendered custom agent, spawns
   independent work in parallel, waits for HANDBACK-style results, then
   synthesizes a final status.

4. Broaden legacy matrix tests only if Codex becomes part of the default
   all-harness contract. Tests currently hard-code the four default harnesses in
   places such as install correctness, backup harnesses, and workflow matrix
   sizing.
