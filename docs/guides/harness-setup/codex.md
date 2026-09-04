# Codex Harness Setup

**Description:** Codex setup for agentic-engineers custom agents, skills, and permission profiles.

**Status:** Supported, included in `make install`.

**Captured From:** `codex-cli 0.141.0` on 2026-06-19.

**Source of Record:** Local CLI help output from:

- `codex --help`
- `codex exec --help`
- `codex review --help`
- `codex doctor --help`
- `codex sandbox --help`
- `codex mcp --help`
- `codex plugin --help`

## Configuration

When you run `make install-codex`, the renderer installs user-scoped Codex configuration by default:

- `~/.codex/AGENTS.md` - Orchestrator rules and role roster
- `~/.codex/config.toml` - Codex defaults when no foreign user config exists
- `~/.codex/agentic-engineers-orchestrator.config.toml` - startup profile for Orchestrator mode
- `~/.codex/agentic-engineers.config.toml` - mergeable reference when `config.toml` is user-managed
- `~/.codex/agents/*.toml` - Codex custom agent definitions
- `~/.codex/skills/*` - Codex-discoverable agent skills

Repository-scoped `.codex/config.toml`, `.codex/agents/*.toml`, and
`.codex/skills` remain valid Codex locations, but the first agentic-engineers
renderer path is user-scoped to match the existing global harness installers.

## Installation

```bash
make install-codex
```

For a sandboxed install that does not touch your real home directory:

```bash
make install-codex DESTDIR=/tmp/ae-codex BACKUP=never
```

## Permission Modes

Use the least-privileged mode that fits the task:

- `workspace-write/on-request` - normal repo work; Codex edits and runs commands inside the workspace, then asks before crossing the sandbox boundary
- `workspace-write/never` - autopilot-style self-tests with no approval prompts while keeping workspace and network boundaries
- `danger-full-access/never` - true YOLO mode; unrestricted local execution with no approval prompts

The top-level CLI also exposes `--sandbox` values of `read-only`, `workspace-write`, and `danger-full-access`, plus `--ask-for-approval` values of `untrusted`, `on-failure`, `on-request`, and `never`.

## Setup Notes

- Prefer `workspace-write/on-request` for day-to-day development.
- Use `workspace-write/never` only in disposable `DESTDIR` installs, temp clones, or other bounded self-test environments.
- Reserve `danger-full-access/never` for deliberate, high-trust automation in externally isolated environments.
- If `~/.codex/config.toml` already exists and is not managed by this renderer, `make install-codex` writes `~/.codex/agentic-engineers.config.toml` as a mergeable reference instead of overwriting your config.

## Usage

Start Codex in agentic-engineers Orchestrator mode:

```bash
codex --profile agentic-engineers-orchestrator --sandbox workspace-write --ask-for-approval on-request
```

In the current CLI capture, Codex does not expose a native `--agent orchestrator` startup flag.
The repo-supported equivalent is the rendered profile above, which injects
Orchestrator startup instructions through Codex's native `--profile` mechanism.

Then use the delegate prefix for terse fan-out:

```text
delegate: inspect the renderer for missing Codex startup integration; review
the generated custom-agent HANDBACK contract; update docs for the new launch flow
```

The Orchestrator profile treats `delegate:` or `DELEGATE:` as an explicit
request to use Codex subagents. It parses semicolon-separated tasks, routes each
task to the narrowest rendered custom agent, spawns independent work in
parallel, keeps same-file edits coordinated, waits for HANDBACK-style results,
and synthesizes the final response.

Role routing:

- `engineer` - bounded implementation with a clear plan
- `senior-engineer` - complex implementation or diagnosis
- `lead-engineer` - planning, integration review, architecture guidance
- `quality-engineer` - quality gates, test gaps, regression review
- `security-engineer` - defensive security review
- `principal-engineer` - cross-system architecture
- `model-engineer` - model/cost/routing analysis

For disposable self-tests:

```bash
codex exec --profile agentic-engineers-orchestrator \
  --sandbox workspace-write --ask-for-approval never \
  "delegate: summarize active agentic-engineers instructions; list custom agents"
```

### CLI Surface Snapshot

Codex CLI defaults to forwarding options to the interactive CLI when no subcommand is specified. The current command set is:

- Session and execution: `exec`, `review`, `resume`, `apply`, `archive`, `delete`, `unarchive`, `fork`
- Account and health: `login`, `logout`, `doctor`, `completion`, `update`, `features`
- Integrations: `mcp`, `mcp-server`, `plugin`, `app-server`, `remote-control`, `cloud`, `exec-server`, `app`, `debug`
- Shell helpers: `sandbox`

High-value `exec` options captured in the current release:

- `--config/-c`, `--enable`, `--disable`, `--strict-config`
- `--image`, `--model`, `--oss`, `--local-provider`, `--profile`
- `--sandbox`, `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`
- `--cd`, `--add-dir`, `--skip-git-repo-check`, `--ephemeral`
- `--ignore-user-config`, `--ignore-rules`, `--output-schema`, `--output-last-message`
- `--color`, `--json`, `--search`, `--remote`, `--remote-auth-token-env`, `--no-alt-screen`

Captured subcommand highlights:

- `codex exec` accepts a prompt or stdin, and has `resume` and `review` subcommands.
- `codex review` supports `--uncommitted`, `--base`, `--commit`, and `--title`.
- `codex doctor` supports `--json`, `--summary`, `--all`, `--no-color`, and `--ascii`.
- `codex sandbox` supports `--permissions-profile`, `--include-managed-config`, `--allow-unix-socket`, and `--log-denials`.
- `codex mcp` supports `list`, `get`, `add`, `remove`, `login`, and `logout`.
- `codex plugin` supports `add`, `list`, `marketplace`, and `remove`.

### Keeping This Current

Refresh this capture after Codex upgrades or CLI surface changes:

1. Re-run the help commands listed above.
2. Update the command/options snapshot here.
3. Keep `docs/guides/harness-setup/README.md` and the top-level harness table in sync.

### Related Maintenance Skill

The canonical `codex-agent-cleanup` skill lives at
[`src/skills/codex-agent-cleanup/SKILL.md`](../../../src/skills/codex-agent-cleanup/SKILL.md).
It renders through the standard framework flow into the Codex install path, so
new skill work should be created under `src/skills/` first and then rendered into
`dist/codex/` and the Codex user install locations by `make install-codex`.

Use it to keep completed sub-agents closed and agent capacity free for new
parallel work. It is the Codex-specific hygiene routine for agent lifecycle
cleanup.

## Next Steps

- [Harness Setup Overview](README.md)
- [OpenCode Setup](opencode.md)
