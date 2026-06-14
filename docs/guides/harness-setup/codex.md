# Codex Harness Setup

**Description:** Codex setup for agentic-engineers custom agents, skills, and permission profiles.

**Status:** Initial renderer support. Install with `make install-codex`.

## Configuration

The renderer installs user-scoped Codex configuration by default:

- `~/.codex/config.toml` - Codex defaults when no foreign user config exists
- `~/.codex/agentic-engineers-orchestrator.config.toml` - startup profile for Orchestrator mode
- `~/.codex/agents/*.toml` - Codex custom agent definitions
- `~/.agents/skills/*` - Codex-discoverable agent skills

Repository-scoped `.codex/config.toml`, `.codex/agents/*.toml`, and
`.agents/skills` remain valid Codex locations, but the first agentic-engineers
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

Codex does not currently expose a native `--agent orchestrator` startup flag.
The supported equivalent is the rendered profile above, which injects
Orchestrator startup instructions through Codex's native `--profile` mechanism.

Then use the delegate prefix for terse fan-out:

```text
delegate: inspect the renderer for missing Codex startup integration; review
the generated custom-agent HANDBACK contract; update docs for the new launch flow
```

The Orchestrator profile treats `delegate:` or `DELEGATE:` as an explicit
request to use Codex subagents. It parses semicolon-separated tasks, routes each
task to the narrowest rendered custom agent, spawns independent work in
parallel, waits for HANDBACK-style results, and synthesizes the final response.

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

## Next Steps

- [Harness Setup Overview](README.md)
- [OpenCode Setup](opencode.md)
