# Deployment Guide: Agentic Engineers

"Deploying agentic-engineers" means installing the framework's agent/skill definitions
into a harness (Claude Code, OpenCode, Copilot CLI, Codex) and invoking that harness's
Orchestrator agent interactively. There is no standalone background service — the
Orchestrator builds a DELEGATE and spawns the target agent directly (Agent/Task tool)
within the harness session, reading the HANDBACK back as the tool result. See
[src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
for the canonical description.

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

Every DELEGATE and HANDBACK is recorded in the harness session transcript itself — the
DELEGATE as a sub-agent spawn's prompt, the HANDBACK as that spawn call's result. Dispatch
completes synchronously within the harness session that produced it. If you need to retain
a record of a session's work beyond the session itself, use your harness's own
session-history or transcript-export mechanism, if it offers one — agentic-engineers does
not write a separate copy of its own.

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
