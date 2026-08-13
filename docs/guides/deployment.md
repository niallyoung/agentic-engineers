# Deployment Guide: Agentic Engineers

## Overview

**This guide previously described deploying a "Continuous Polling Loop Automation"
system** — a background process (`bin/run-automation-controller.sh`) that
continuously polled a task queue, read DELEGATE files, and spawned agents as
subprocesses, packaged as a systemd service / Docker container / Kubernetes
deployment.

That script, the polling loop it wrapped, and the architecture doc it linked to
(`docs/architecture/continuous-polling.md`) no longer exist. An audit of live sessions
found that dispatch never actually went through that polling path in practice — every
real delegation happened via a direct sub-agent spawn instead. The framework has been
updated to match the model that was actually running: the Orchestrator builds a
DELEGATE and spawns the target agent directly (Agent/Task tool) within the harness
session, reading the HANDBACK back as the tool result. See
[src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
for the canonical description.

**Practical consequence:** there is no standalone background service to install,
run under systemd, containerize, or scale horizontally. "Deploying agentic-engineers"
today means installing the framework's agent/skill definitions into a harness
(Claude Code, OpenCode, Copilot CLI, Codex) and invoking that harness's
Orchestrator agent interactively — see the sections below.

---

## Installing the Framework

```bash
git clone <repo-url> agentic-engineers
cd agentic-engineers

# Install into all default harnesses
make install

# Or install a specific harness
make install-opencode      # OpenCode CLI
make install-copilot       # Copilot CLI
make install-claude        # Claude Code
make install-codex         # Codex CLI/IDE
```

By default this installs under your home directory. For an isolated/sandboxed
install (e.g. for testing this guide), set `DESTDIR`:

```bash
DESTDIR=/tmp/test-install make install-opencode
```

See the main [README.md](../../README.md#quick-start) for the full installation
matrix and [docs/ENTRYPOINT.md](../ENTRYPOINT.md) for how to invoke the Orchestrator
once installed.

---

## Running the Orchestrator

The Orchestrator runs **inside** a harness session — it is not a separate process you
start and leave running:

```bash
# Claude Code
claude --agent orchestrator

# OpenCode CLI
opencode --agent orchestrator

# Copilot CLI
copilot --agent orchestrator
```

Then give it work directly (`delegate: ...`). It spawns the appropriate specialist
agent(s), reads their HANDBACKs back in-context, and pauses when there is no pending
DELEGATE and no outstanding spawn (see
[src/AGENTS.md > Pause Condition](../../src/AGENTS.md#pause-condition)). To resume,
give it a new request or add a task to `TODO.md`.

---

## Unattended / Long-Running Operation

**UNRESOLVED:** the old guide's systemd/Docker/Kubernetes scenarios all wrapped
`bin/run-automation-controller.sh`, which does not exist in this repository (there is
no `bin/` directory at all as of this writing) and predates the direct-spawn model in
any case. This framework does not currently ship a supported "always-on production
server" deployment target for the Orchestrator. If you need genuinely unattended,
long-lived operation, check whether your harness offers its own headless/scheduled
invocation mechanism (for example, a harness-native scheduled-agent or background-run
feature) — agentic-engineers itself does not provide one, and this guide should not be
treated as a source of a working command for that use case until it's rewritten by
someone who has verified a real path end to end.

---

## The Audit Trail: Harness Session Transcript

Dispatch is direct, and there is no filesystem queue to back up. Every DELEGATE and
HANDBACK is recorded in the harness session transcript itself — the DELEGATE as a
sub-agent spawn's prompt, the HANDBACK as that spawn call's result. There is no
`~/.agentic-engineers/{harness}/{session-id}/queue/` directory, so there is nothing
under that path to `tar` up, restore, or prune. If you need to retain a record of a
session's work beyond the session itself, use your harness's own session-history or
transcript-export mechanism, if it offers one — agentic-engineers does not write a
separate copy of its own.

There is no "restore and restart a service" procedure to document — dispatch already
completes synchronously within the harness session that produced it, and there is no
queue state to resume from.

---

## Maintenance

**Periodically:**
- Keep the harness CLI itself (Claude Code / OpenCode / Copilot CLI / Codex)
  up to date per its own release process; agentic-engineers has no dependencies of its
  own to patch beyond what `make install` renders.

---

**Document Version**: 2.0
**Last Updated**: 2026-08-09
**Status**: Reflects the Direct Sub-Agent Spawn Execution Model; supersedes the
Continuous Polling Loop Automation deployment guide.
