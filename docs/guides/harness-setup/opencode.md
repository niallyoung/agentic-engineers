# OpenCode Harness Setup

**Description:** Primary harness for autonomous agent coordination. Recommended for production use.

**Latest Tested:** v1.2.0 (2026-05-30)  
**Minimum Required:** v1.0.0  
**Repository:** [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)

## Features

- ✅ Full DELEGATE/HANDBACK protocol support
- ✅ Direct sub-agent spawn dispatch (Agent/Task tool) — the harness session transcript is the durable audit record; nothing polls anything to route work
- ✅ Real-time token tracking (27% Orchestrator + 73% subagents)
- ✅ Concurrent agent execution (tested with 36+ agents)
- ✅ Voice notifications with distinct personalities
- ✅ Dark factory mode (autonomous operation)

## Installation

```bash
make install-opencode
```

This will:
1. Render agent configurations into `~/.config/opencode/` with OpenCode-specific model names
2. Install protocol documents and skills
3. Set up the renderer pipeline

## Configuration

### Audit Trail

There is no filesystem queue. OpenCode dispatches via direct sub-agent spawn (Agent/Task
tool), and every DELEGATE and HANDBACK is recorded in the harness session transcript
itself — the DELEGATE as a spawn prompt, the HANDBACK as that spawn's result. Nothing
reads or writes a separate queue directory.

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
opencode --agent orchestrator --dark-factory "Process all pending work"
```

This mode:
- Processes tasks autonomously, spawning specialists directly (Agent/Task tool) rather than polling
- Routes to specialists based on task type
- Reads each HANDBACK back in-context as its spawn call returns
- Aggregates results and reports back
- Pauses when no pending DELEGATEs or outstanding spawns remain — the session transcript is already the audit record, so there is no separate write step

### Voice Notifications

OpenCode supports voice notifications for task lifecycle events:

```bash
# Enable voice notifications in config
opencode --agent orchestrator --voice "Task completed with 95/100 quality"
```

## Known Limitations

- Model names use hyphenated format (e.g., `claude-opus-4-8`)
- Each session is independently isolated for concurrent operation — there is no shared queue state to coordinate

## Compatibility Notes

- ✅ Works with Anthropic API keys (default configuration)
- ✅ Supports OpenAI models (gpt-4-turbo, gpt-4o) via API routing
- ✅ Compatible with local models (ollama/mistral, ollama/llama2) with OpenAI-compatible endpoints

## Troubleshooting

### Model not recognized

**Symptom:** `Error: Model 'claude-opus-4.8' not found`

**Cause:** OpenCode expects hyphenated model names.

**Fix:** The renderer should handle this automatically. If not, check that you ran `make install-opencode` and not just `make install`.

### Agent not routing correctly

**Symptom:** Orchestrator isn't spawning the expected specialist.

**Fix:**
1. Run with `--debug` and confirm the Agent/Task spawn call for the expected role
   actually fires: `opencode --agent orchestrator --debug`
2. Check logs: `tail -f ~/.agentic-engineers/{session-id}/memory/logs/*.log`

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
