# Troubleshooting Guide: Agentic Engineers

This guide covers problems you can actually hit under the current architecture:
installing/rendering the framework into a harness, invoking the Orchestrator, and
direct sub-agent spawn dispatch. See
[src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
for how dispatch actually works today.

> **Note for anyone arriving from an old bookmark:** this guide previously diagnosed a
> background "Continuous Polling Loop Automation" process (`bin/run-automation-controller.sh`)
> — stuck polling cycles, stale queue claims, scheduler not firing, memory leaks in a
> long-running daemon, systemd/Docker restart procedures, etc. That script and the
> polling loop it wrapped no longer exist, and none of those symptoms can occur under
> the current model: there is no background loop to get stuck, and a spawned sub-agent
> either returns a HANDBACK in-context or the spawn call itself fails/errors visibly.
> Those sections have been removed rather than reworded — see
> [docs/guides/deployment.md](deployment.md) for what deployment looks like now.

---

## Quick Diagnostic Checklist

```bash
# 1. Check the harness installation is healthy (Claude Code / OpenCode)
python3 -m src.harness.harness_checker --harness claude
python3 -m src.harness.harness_checker --harness opencode

# 2. Verify agents rendered correctly
ls ~/.claude/config/agents/*.md 2>/dev/null | wc -l     # Claude Code
ls ~/.config/opencode/agent/*.md 2>/dev/null | wc -l    # OpenCode

# 3. Confirm the audit-trail queue directory exists for your session
find ~/.agentic-engineers -path '*/queue' -type d | sort

# 4. Re-render + reinstall if anything above looks wrong
make install
```

For harness-specific installation/rendering problems, see:
- [docs/HARNESS-CLAUDE-TROUBLESHOOTING.md](../HARNESS-CLAUDE-TROUBLESHOOTING.md)
- [docs/HARNESS-OPENCODE-TROUBLESHOOTING.md](../HARNESS-OPENCODE-TROUBLESHOOTING.md)

(Copilot CLI, Codex, and π.dev do not yet have dedicated troubleshooting docs; if you
hit a harness-specific problem there, treat the general sections below as your
starting point.)

---

## Common Issues & Solutions

### Issue: "Agent not found" / Orchestrator won't start

**Symptoms:** the harness reports it can't find the `orchestrator` agent, or invoking
`--agent orchestrator` errors immediately.

**Likely cause:** agent definitions weren't rendered/installed for this harness, or
the install is stale relative to the repo.

**Fix:**
```bash
make install-<harness>       # e.g. make install-claude, make install-opencode
```
Then re-run the harness-specific quick-start checks above.

---

### Issue: A spawned sub-agent never returns / hangs

**Symptoms:** the Orchestrator (or any spawning agent) issued an Agent/Task tool call
and it appears stuck.

**What this means under direct spawn:** there is no separate process to inspect —
the spawning agent's context is blocked on that one tool call returning. There is no
"check if the scheduler picked it up" step, because nothing is polling for it; the
spawn call itself *is* the dispatch.

**What to do:**
1. If it's a single spawn, this is a genuine long-running task — let it finish, or
   interrupt the session if your harness supports that.
2. If it's one of several concurrent spawns (parallel delegation), treat the slow one
   as a timeout: proceed with the results already in hand, mark
   `result_aggregation_status: timed_out` in the aggregating HANDBACK, and record the
   incomplete child in `children_failed` (see
   [docs/AGENTS.md > Parallel Delegation](../AGENTS.md#parallel-delegation-direct-spawn-fan-out)).

---

### Issue: Spawn depth or fan-out seems wrong / a cycle wasn't caught

**Symptoms:** an agent re-delegated further than expected, spawned more than 5
concurrent sub-agents, or delegated back to a role already in its own ancestry chain.

**Important:** the depth-3 / fan-out-5 / ancestry limits in
[src/AGENTS.md > Recursion Limits](../../src/AGENTS.md#recursion-limits) are a
documented contract each agent's own definition must observe (via its `tools:`
frontmatter grant — see
[Tools-Frontmatter Permission Model](../../src/AGENTS.md#tools-frontmatter-permission-model)).
**No harness currently enforces this mechanically** — if an agent's own definition or
prompt doesn't respect the limit, nothing will stop it automatically. If you see a
violation, it's a defect in that agent's behavior (or its definition), not a harness
bug to route around. Report it against the offending agent's definition in
`src/agents/`.

---

### Issue: DELEGATE or HANDBACK looks malformed

**Symptoms:** a spawned agent reports it couldn't parse the DELEGATE it was given, or
the spawning agent can't make sense of a HANDBACK it received.

**Fix:**
1. Check required fields against `orchestration/HANDOFF.md` (`handoff_type`, `task_id`,
   `agent`/`role`, `scope`, `plan`, `success_criteria` for DELEGATE; `handoff_type`,
   `task_id`, `status`, `output`/`deliverables`, `metrics` for HANDBACK).
2. If the DELEGATE is genuinely incomplete or unclear, the receiving agent should
   report `status: blocked` rather than guess — that's expected behavior, not a bug.

---

### Issue: Can't find the audit trail for a session

**Symptoms:** you expect a DELEGATE/HANDBACK pair under
`~/.agentic-engineers/{harness}/{session-id}/queue/` and can't find it.

**Fix:**
```bash
# List every session queue root that does exist
find ~/.agentic-engineers -path '*/queue' -type d | sort

# For Claude/Copilot, confirm your session-id
echo $CLAUDE_SESSION_ID
echo $COPILOT_SESSION_ID
```
If nothing has been recorded at all for a session that clearly did work, that's an
audit-trail bug worth reporting — recording every DELEGATE (at spawn) and every
HANDBACK (at completion) via `enqueue()` is mandatory, not optional cleanup (see
[Audit-Trail Strategy](../../src/AGENTS.md#audit-trail-strategy)).

---

## Getting Help

If an issue persists after the steps above:

1. **Collect diagnostic information:**
   ```bash
   echo "=== System Info ===" && uname -a
   echo "=== Python ===" && python3 --version
   echo "=== Harness health ===" && python3 -m src.harness.harness_checker --harness claude --json
   echo "=== Queue roots ===" && find ~/.agentic-engineers -path '*/queue' -type d
   ```
2. **File a bug report with:** the full error/output, the harness and command you ran,
   and (if relevant) the DELEGATE/HANDBACK YAML from the audit trail.

---

**Document Version**: 2.0
**Last Updated**: 2026-08-09
**Status**: Reflects the Direct Sub-Agent Spawn Execution Model; supersedes the
Continuous Polling Loop Automation troubleshooting guide.
