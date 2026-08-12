# OpenCode Harness Setup

**Description:** Primary harness for autonomous agent coordination. Recommended for production use.

**Latest Tested:** v1.2.0 (2026-05-30)  
**Minimum Required:** v1.0.0  
**Repository:** [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)

## Features

- ✅ Full DELEGATE/HANDBACK protocol support
- ✅ Direct sub-agent spawn dispatch (Agent/Task tool), with the queue retained as a durable audit trail — not something anything polls to route work
- ✅ Real-time token tracking (27% Orchestrator + 73% subagents)
- ✅ Concurrent agent execution (tested with 36+ agents)
- ✅ Voice notifications with distinct personalities
- ✅ Dark factory mode (autonomous operation)

## Installation

```bash
make install-opencode
```

This will:
1. Create queue directories at `~/.agentic-engineers/opencode/{session-id}/queue/`
2. Render agent configurations into `~/.config/opencode/` with OpenCode-specific model names
3. Install protocol documents and skills
4. Set up the renderer pipeline

## Configuration

### Queue Directories (Audit Trail)

OpenCode records every DELEGATE and HANDBACK to a per-session queue directory as a
durable audit trail — dispatch itself happens via direct sub-agent spawn, not by
anything reading this directory:

```bash
mkdir -p ~/.agentic-engineers/opencode/{session-id}/queue/{incoming,processing,done}
```

These directories are created automatically by `make install-opencode`.

OpenCode's rendered config lives in `~/.config/opencode/` and includes `AGENTS.md`, `opencode.jsonc`, `agents/`, and `skills/`.

### Model Names

OpenCode uses hyphenated model names (e.g., `claude-opus-4-8` instead of `claude-opus-4.8`).

The renderer automatically transforms model names during installation.

## Usage

### Basic Task Invocation

```bash
opencode --agent orchestrator "Your task description here"
```

### Dark Factory Mode (Autonomous)

```bash
opencode --agent orchestrator --dark-factory "Process all pending tasks in queue"
```

This mode:
- Processes tasks autonomously, spawning specialists directly (Agent/Task tool) rather than polling
- Routes to specialists based on task type
- Reads each HANDBACK back in-context as its spawn call returns
- Aggregates results and reports back
- Records each DELEGATE/HANDBACK to the audit-trail queue, then pauses when no pending DELEGATEs or outstanding spawns remain

### Voice Notifications

OpenCode supports voice notifications for task lifecycle events:

```bash
# Enable voice notifications in config
opencode --agent orchestrator --voice "Task completed with 95/100 quality"
```

## Known Limitations

- Requires queue directories to be created at `~/.agentic-engineers/opencode/{session-id}/queue/`
- Model names use hyphenated format (e.g., `claude-opus-4-8`)
- Session-based queue isolation for concurrent operation

## Compatibility Notes

- ✅ Works with Anthropic API keys (default configuration)
- ✅ Supports OpenAI models (gpt-4-turbo, gpt-4o) via API routing
- ✅ Compatible with local models (ollama/mistral, ollama/llama2) with OpenAI-compatible endpoints

## Troubleshooting

### Queue directories not found

**Symptom:** `Error: Queue directory ~/.agentic-engineers/opencode/{session-id}/queue/incoming not found`

**Fix:**
```bash
mkdir -p ~/.agentic-engineers/opencode/{session-id}/queue/{incoming,processing,done}
```

Or re-run:
```bash
make install-opencode
```

### Model not recognized

**Symptom:** `Error: Model 'claude-opus-4.8' not found`

**Cause:** OpenCode expects hyphenated model names.

**Fix:** The renderer should handle this automatically. If not, check that you ran `make install-opencode` and not just `make install`.

### Agent not routing correctly

**Symptom:** Orchestrator isn't spawning the expected specialist, or the audit trail
isn't recording DELEGATE/HANDBACK entries.

**Fix:**
1. Check queue permissions: `ls -la ~/.agentic-engineers/opencode/{session-id}/queue/`
2. Run with `--debug` and confirm the Agent/Task spawn call for the expected role
   actually fires: `opencode --agent orchestrator --debug`
3. Check logs: `tail -f ~/.agentic-engineers/{session-id}/memory/logs/*.log`

There is no polling loop to check separately — if the spawn call fires and returns a
HANDBACK, routing worked; if it doesn't fire at all, the issue is in the Orchestrator's
routing decision, not a stalled poller.

## Advanced Configuration

### Concurrent Agent Execution

OpenCode supports tens to hundreds of concurrent agents. To test:

```bash
# Launch orchestrator with high concurrency
opencode --agent orchestrator --max-agents 100 "Process batch of 100 tasks"
```

**Tested capacity:**
- ✅ 36+ concurrent agents (production validated)
- ✅ 100+ sub-agents in parallel delegation chains
- ✅ 5-tier deep hierarchies

### Voice Notification Customization

Edit `~/.agentic-engineers/config/voice.yaml` to customize voices per agent:

```yaml
orchestrator: "Alex"      # System voice for orchestrator
engineer: "Samantha"      # System voice for engineers
quality_engineer: "Tom"   # System voice for QE
```

## Next Steps

- [Harness Setup Overview](README.md)
