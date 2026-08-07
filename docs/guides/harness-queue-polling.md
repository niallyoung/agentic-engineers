# Harness Queue Auto-Polling (Phase G)

Each harness (Claude Code, OpenCode, Copilot CLI) automatically polls its
session queue during idle periods and processes any DELEGATEs it finds — with no
external daemon, cron job, or system service. This guide explains how that works,
how to configure it, and how to troubleshoot it.

> **TL;DR:** When the harness is idle, an in-process idle-loop invokes
> `orchestrator-scheduler --poll-once`. An empty queue triggers exponential
> backoff (5s → 30s → 180s → 600s); a file-watch on `queue/incoming/` wakes the
> harness immediately when a new DELEGATE arrives. All polling is in-process and
> SPEC.md-compliant ("AGENTS with SKILLS", no external daemons).

---

## How It Works

The pipeline has three layers, all in-process within the harness:

```
Harness idle-loop  →  scheduler SKILL  →  queue polling
   (detects idle)      (--poll-once)       (incoming → processing → done)
```

1. **Idle-loop detection.** On each event-loop tick the harness checks: is the
   user idle for ≥ `interval_seconds`, is there no task in progress, and is the
   message queue empty? If all three hold, it is idle.

2. **Scheduler invocation.** When idle, the harness invokes
   `orchestrator-scheduler --poll-once` as a bounded subprocess (default 35s hard
   cap) and parses the single JSON line it prints. Timeouts and errors are
   non-fatal — the harness logs and continues.

3. **Queue polling.** The scheduler resolves the current session + harness from
   the environment, acquires the session queue lock, scans
   `~/.agentic-engineers/{harness}/{session}/queue/incoming/`, and for each
   DELEGATE moves it `incoming → processing`, spawns the sub-agent, writes the
   HANDBACK, and moves it `processing → done`.

4. **Continuous backoff (Phase G-2).** Beneath the single-shot call, the
   `BackoffPoller` engine (`src/harnesses/shared/backoff_poller.py`) repeats the
   poll on an interval that *backs off* when the queue stays empty and *resets*
   the instant work appears.

**Key source files:**

- `src/harnesses/shared/backoff_poller.py` — backoff + file-watch engine
- `src/harnesses/claude_code/idle_loop.py` — Claude Code idle-loop
- `src/harnesses/opencode/idle_loop.py` — OpenCode idle-loop
- `src/harnesses/copilot_cli/idle_loop.py` — Copilot CLI idle-loop
- `src/skills/orchestrator-scheduler/` — the `--poll-once` SKILL

> **Scope:** This guide currently covers **3 harnesses** — Claude Code, OpenCode,
> and Copilot CLI. The π.dev (`src/harnesses/pi/`) and Codex idle-loop
> infrastructure is planned for a future release (π.dev is an empty stub today;
> Codex was recently wired into `make install` but has no idle-loop yet).

---

## Configuration

Polling is configured per harness in its `settings.json` (or equivalent) under
the `idle_loop` key. The Claude Code default lives in `dist/claude/settings.json`:

```json
{
  "idle_loop": {
    "enabled": true,
    "interval_seconds": 180,
    "action": "invoke_skill",
    "skill": "orchestrator-scheduler",
    "args": ["--poll-once"],
    "backoff_intervals": [5, 30, 180, 600],
    "watch_enabled": true,
    "watch_poll_seconds": 0.5
  }
}
```

| Key | Default | Purpose |
|-----|---------|---------|
| `enabled` | `true` | Master switch. `false` makes the idle-loop a no-op. |
| `interval_seconds` | `180` | Idle threshold: how long the user must be idle before the first poll. |
| `action` | `invoke_skill` | What the idle-loop does when idle. |
| `skill` | `orchestrator-scheduler` | Skill to invoke. |
| `args` | `["--poll-once"]` | Args passed to the skill (single-cycle mode). |
| `backoff_intervals` | `[5, 30, 180, 600]` | The exponential-backoff ladder, in seconds. Last value is the cap. |
| `watch_enabled` | `true` | Whether to file-watch `queue/incoming/` to wake early on DELEGATE arrival. |
| `watch_poll_seconds` | `0.5` | How often the file-watch re-scans `incoming/` while sleeping. |

The config is forward-compatible: unknown keys are ignored, missing keys fall
back to defaults, and malformed values are coerced or ignored rather than
crashing the harness.

---

## Exponential Backoff

To avoid busy-polling an empty queue, polling waits a configurable interval keyed
by a *backoff level*:

```
level 0 →   5s   (active: queue recently had work)
level 1 →  30s
level 2 → 180s
level 3 → 600s   (deep idle; capped here)
```

**Each *empty* poll advances the level by one** (capped at the last rung).
**Any of the following resets the level to 0:**

- a poll that processed ≥ 1 DELEGATE, or
- the file-watch detecting a new file in `queue/incoming/`.

**Example timeline:**

```
Empty queue → 5s → 30s → 180s → 600s (deep idle)
  → DELEGATE arrives → file-watch wakes the harness → processes immediately
  → backoff reset to 5s (active)
```

### Performance impact

- Backoff overhead is **< 2ms per cycle** — negligible.
- A representative batch of **5 DELEGATEs processes in ~71ms**.
- The file-watch is a cheap directory scan (`os.scandir`), typically **< 1ms**,
  with no OS-specific inotify/FSEvents dependency.
- An idle session settles into a ~10-minute deep-sleep cadence (level 3), so a
  long-idle harness costs almost nothing, yet still reacts to new work within a
  single `watch_poll_seconds` slice.

---

## Multi-Harness Coordination

When multiple harnesses share one session queue, polling is serialized with a
file-based lock — there are **no races and no double-processing**.

- **Lock path:** `~/.agentic-engineers/{harness}/{session}/queue/.lock`
- **Atomic acquire:** `os.open(..., O_CREAT | O_EXCL | O_WRONLY)` — fails if the
  lock is already held.
- **Contents:** PID, ISO-8601 timestamp, harness name (for debugging races).
- **Contention:** if another live harness holds the lock, the cycle is *skipped*
  (`lock_skipped: true`, `processed: 0`) — this is not an error; the harness
  retries on its next idle cycle.
- **Stale cleanup:** a lock whose mtime is older than 300s is presumed orphaned
  by a crashed harness; it is removed and reacquired.
- **Release:** always in a `finally` block, even if processing errors.

Because the lock is held only during the polling cycle (not during long agent
execution in the spawned sub-agent), contention windows are small and harnesses
naturally take turns draining the queue.

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| DELEGATE never processed | Idle-loop disabled | Confirm `idle_loop.enabled: true` in settings.json. |
| DELEGATE never processed | Session ID not set | Ensure `CLAUDE_SESSION_ID` / `OPENCODE_SESSION_ID` / `COPILOT_SESSION_ID` (or `AGENTIC_SESSION_ID`) is exported. |
| Always `lock_skipped: true` | Another harness holds the lock, or a stale lock | Check `queue/.lock`; if its mtime is > 300s old it auto-clears next cycle, or remove it manually. |
| `lock` errors in JSON output | Lock dir unwritable / permissions | Verify `~/.agentic-engineers/{harness}/{session}/queue/` is writable. |
| Slow to react to new DELEGATEs | File-watch disabled | Set `watch_enabled: true` and a small `watch_poll_seconds` (e.g. `0.5`). |
| `timeout` error in JSON output | Cycle exceeded soft timeout | Remaining items defer to the next cycle (automatic); raise `--timeout` if batches are large. |
| Subprocess / `process` stage error | Sub-agent crashed or skill import failed | Re-run `orchestrator-scheduler --poll-once --verbose`; check the `errors` array's `stage`. |
| Polling never sleeps deeply | Backoff resets every cycle | A stray file in `incoming/` keeps tripping the watch — inspect and clear it. |

### Logs to watch for

The idle-loop and poller log at INFO. Watch for these lines:

- **Idle detection:** `Claude idle for Ns, polling queue`
- **Poll results:** `Queued N DELEGATEs, duration Xs`
- **Backoff levels:** `Empty/failed cycle; backoff advanced to level L (Ns)`
- **Backoff reset:** `Processed N DELEGATE(s); backoff reset to 0`
- **File-watch wake:** `New DELEGATE detected during sleep; waking early`
- **Lock activity:** acquire / release / stale-cleanup are all logged INFO for
  race debugging.
- **Errors (non-fatal):** `Queue poll error: ...` — the harness continues.

The single JSON line emitted by `--poll-once` is the machine-readable summary:

```json
{
  "processed": 3, "failed": 0, "duration_ms": 2400,
  "queue_empty": false, "session_id": "abc-def-ghi", "harness": "claude",
  "lock_skipped": false, "errors": []
}
```

`errors[].stage` is one of `init`, `lock`, `scan`, `timeout`, `process`, `fatal`.

---

## See Also

- [orchestrator-scheduler SKILL](../../src/skills/orchestrator-scheduler/SKILL.md)
- [Phase G — Harness-Native Queue Cooperation](../../src/orchestration/PHASE_G_HARNESS_COOPERATION.md)
- [Continuous polling setup](continuous-polling-setup.md)
- [Continuous polling usage](continuous-polling-usage.md)
