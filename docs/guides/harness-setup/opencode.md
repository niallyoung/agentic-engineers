# OpenCode Harness Setup

**Description:** Primary harness for autonomous agent coordination. Recommended for production use.

**Latest Tested:** v1.2.0 (2026-05-30)  
**Minimum Required:** v1.0.0  
**Repository:** [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)

## Features

- ✅ Full DELEGATE/HANDBACK protocol support
- ✅ Queue-based task routing
- ✅ Real-time token tracking (27% Orchestrator + 73% subagents)
- ✅ Concurrent agent execution (tested with 36+ agents)
- ✅ Voice notifications with distinct personalities
- ✅ Dark factory mode (autonomous operation)

## Installation

```bash
make install-opencode
```

This will:
1. Create queue directories at `~/.agentic-engineers/queue/`
2. Render agent configurations with OpenCode-specific model names
3. Install protocol documents and skills
4. Set up the renderer pipeline

## Configuration

### Queue Directories

OpenCode requires queue directories for task routing:

```bash
mkdir -p ~/.agentic-engineers/queue/{incoming,processing,done}
```

These directories are created automatically by `make install-opencode`.

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
- Polls the queue continuously
- Processes tasks autonomously
- Routes to specialists based on task type
- Aggregates results and reports back

### Voice Notifications

OpenCode supports voice notifications for task lifecycle events:

```bash
# Enable voice notifications in config
opencode --agent orchestrator --voice "Task completed with 95/100 quality"
```

## Known Limitations

- Requires queue directories to be created at `~/.agentic-engineers/queue/`
- Model names use hyphenated format (e.g., `claude-opus-4-8`)
- Session-based queue isolation for concurrent operation

## Compatibility Notes

- ✅ Works with Anthropic API keys (default configuration)
- ✅ Supports OpenAI models (gpt-4-turbo, gpt-4o) via API routing
- ✅ Compatible with local models (ollama/mistral, ollama/llama2) with OpenAI-compatible endpoints

## Troubleshooting

### Queue directories not found

**Symptom:** `Error: Queue directory ~/.agentic-engineers/queue/incoming not found`

**Fix:**
```bash
mkdir -p ~/.agentic-engineers/queue/{incoming,processing,done}
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

**Symptom:** Tasks not appearing in queue or agents not picking up work.

**Fix:**
1. Check queue permissions: `ls -la ~/.agentic-engineers/queue/`
2. Verify orchestrator is polling: `opencode --agent orchestrator --debug`
3. Check logs: `tail -f ~/.agentic-engineers/logs/orchestrator.log`

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
- [Advanced Delegation Guide](../advanced-delegation.md)
- [Troubleshooting](../troubleshooting.md)
