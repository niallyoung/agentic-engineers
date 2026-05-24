# Agent Memory Configuration

## Overview

This document describes how agentic-engineers agents are configured to use artifact directory storage for memory instead of GitHub Copilot's built-in memory feature.

## Configuration Goals

1. **Disable Copilot Memory**: Explicitly set `copilot_memory_enabled = False` on all agents
2. **Use Artifact Directory Storage**: Default to `~/.agentic-engineers/memory/` for persistent memory
3. **Clear Memory Fields**: Add explicit memory configuration fields to DELEGATE protocol
4. **Environment Isolation**: Set environment variables to enforce artifact-based storage

## DELEGATE Memory Fields

The DELEGATE protocol now includes three new memory-related fields:

### `memory_storage` (string)
- **Type**: enum (`artifact_dir`, `disabled`)
- **Default**: `artifact_dir`
- **Description**: Where agent memory is stored
- **Valid Values**:
  - `artifact_dir`: Store memory in `~/.agentic-engineers/memory/`
  - `disabled`: Agent does not use memory

### `copilot_memory_enabled` (boolean)
- **Type**: boolean
- **Default**: `false`
- **Description**: Whether GitHub Copilot memory feature is enabled
- **Validation**: Must always be `false` (Copilot memory is disabled by design)
- **Note**: This field is explicitly set to `false` on all agents and cannot be overridden

### `memory_paths` (object)
- **Type**: object with optional string keys
- **Description**: Memory storage paths (auto-configured, can be overridden)
- **Default Paths**:
  ```yaml
  memory_paths:
    home: "~/.agentic-engineers/memory/"
    task_memory: "~/.agentic-engineers/memory/{task_id}/"
    shared_memory: "~/.agentic-engineers/memory/shared/"
  ```
- **Usage**:
  - `home`: Root memory directory for all agent memory
  - `task_memory`: Task-specific memory (includes task ID)
  - `shared_memory`: Memory shared across tasks and agents

## Agent Configuration

### All Agent Configs
Every agent in `/src/orchestration/agents/__init__.py` is configured with:

```python
AgentConfig(
    name="Agent Name",
    model="model-name",
    effort="high",
    role="agent_role",
    description="Agent description",
    # Memory configuration
    memory_storage="artifact_dir",           # ← Artifact storage
    copilot_memory_enabled=False              # ← Disabled
)
```

### 8 Primary Agents
1. **Orchestrator** - Routes tasks
2. **Engineer** - Executes planned work
3. **Senior Engineer** - Complex tasks, writes plans
4. **Lead Engineer** - Code review, quality decisions
5. **Principal Engineer** - Architecture, cross-service design
6. **Quality Engineer** - Post-implementation quality gate
7. **Model Engineer** - Token analysis, cost optimization
8. **Security Engineer** - Security analysis, vulnerability audits

All configured with:
- `memory_storage = "artifact_dir"`
- `copilot_memory_enabled = False`

## Environment Variables

When agents are invoked, the following environment variables are set:

| Variable | Value | Purpose |
|----------|-------|---------|
| `AGENTIC_ENGINEERS_MEMORY_HOME` | `~/.agentic-engineers/memory/` | Root memory directory |
| `AGENTIC_ENGINEERS_COPILOT_MEMORY_ENABLED` | `false` | Disable Copilot memory |
| `AGENTIC_ENGINEERS_MEMORY_STORAGE` | `artifact_dir` | Storage location directive |

These are set by `invoke_agent.py` before spawning agent subprocesses.

## Agent Memory Methods

The base `Agent` class includes memory management methods:

### `get_artifact_memory_path() -> str`
Returns the root artifact memory directory path:
- Default: `~/.agentic-engineers/memory/`
- Creates directory if it doesn't exist
- Can be overridden via `AGENTIC_ENGINEERS_MEMORY_HOME` environment variable

```python
agent = MyAgent(config)
memory_root = agent.get_artifact_memory_path()
# Returns: "/Users/niall/.agentic-engineers/memory/"
```

### `get_task_memory_path() -> str`
Returns the task-specific memory directory path:
- Format: `{memory_root}/{task_id}/`
- Creates directory if it doesn't exist
- Requires `task_id` to be set

```python
agent = MyAgent(config)
task_memory = agent.get_task_memory_path()
# Returns: "/Users/niall/.agentic-engineers/memory/2026-05-24-example-task/"
```

### `disable_copilot_memory()`
Explicitly disables Copilot memory and configures artifact storage:
- Sets environment variables to disable Copilot memory
- Sets memory storage to artifact directory
- Called automatically during agent execution

```python
agent = MyAgent(config)
agent.disable_copilot_memory()
# Sets: AGENTIC_ENGINEERS_COPILOT_MEMORY_ENABLED=false
#       AGENTIC_ENGINEERS_MEMORY_STORAGE=artifact_dir
#       AGENTIC_ENGINEERS_MEMORY_HOME=~/.agentic-engineers/memory/
```

## Memory Directory Structure

Memory is organized by task under `~/.agentic-engineers/memory/`:

```
~/.agentic-engineers/memory/
├── shared/                                    # Shared memory (across tasks)
│   ├── agent_registry.json                    # Agent state registry
│   └── metrics.json                           # Aggregated metrics
├── 2026-05-24-fix-auth-bug/                  # Task-specific memory
│   ├── delegate.yaml                          # Copy of original DELEGATE
│   ├── context.json                           # Task context/state
│   ├── progress.log                           # Execution progress
│   └── results.json                           # Task results
└── 2026-05-25-refactor-api/
    ├── delegate.yaml
    ├── context.json
    ├── progress.log
    └── results.json
```

## Migration from Copilot Memory

If Copilot memory was previously used:

1. **Identify existing Copilot memory location**:
   - Default Copilot memory: `~/.copilot/memory/`
   - Check environment for `COPILOT_MEMORY_HOME`

2. **Migrate data** (if needed):
   ```bash
   # Copy existing Copilot memory to agentic-engineers location
   mkdir -p ~/.agentic-engineers/memory/
   cp -r ~/.copilot/memory/* ~/.agentic-engineers/memory/
   ```

3. **Verify Copilot memory is disabled**:
   ```bash
   # Check environment variables
   echo $AGENTIC_ENGINEERS_COPILOT_MEMORY_ENABLED  # Should output: false
   echo $AGENTIC_ENGINEERS_MEMORY_STORAGE          # Should output: artifact_dir
   ```

4. **Test agent execution**:
   ```bash
   # Run an agent and verify memory is stored in artifact directory
   ls ~/.agentic-engineers/memory/
   ```

## Implementation Details

### Where Memory Configuration Is Applied

1. **DELEGATE Protocol** (`delegate-schema.yaml`)
   - Three new optional fields added
   - Memory validation in DELEGATE validator

2. **Agent Base Class** (`src/orchestration/agents/__init__.py`)
   - `AgentConfig` dataclass updated with memory fields
   - `Agent` class includes memory management methods
   - Memory configuration applied in `execute()` method

3. **Agent Invocation** (`src/orchestration/agents/invoke_agent.py`)
   - Memory fields added to DELEGATE before sending
   - Environment variables set before subprocess spawn
   - Memory paths configured for each invocation

4. **Protocol Model** (`src/orchestration/protocol/expanded_delegate.py`)
   - `ExpandedDelegate` dataclass includes memory fields
   - Memory validation in `validate()` method
   - Serialization/deserialization support

## Testing

Memory configuration is validated by:

1. **Unit Tests** (to be added):
   - Memory field validation
   - Path generation
   - Environment variable configuration

2. **Integration Tests**:
   - Agent execution with memory configuration
   - Artifact directory creation
   - Task-specific memory isolation

## Troubleshooting

### Copilot Memory Still Enabled
**Symptom**: Agent uses Copilot memory instead of artifact directory

**Fix**:
1. Check `AGENTIC_ENGINEERS_COPILOT_MEMORY_ENABLED` environment variable
2. Verify it's set to `false` by `invoke_agent.py`
3. Check agent config: `copilot_memory_enabled` must be `False`

### Memory Directory Not Created
**Symptom**: Artifact memory directory doesn't exist

**Fix**:
1. Check `AGENTIC_ENGINEERS_MEMORY_HOME` environment variable
2. Ensure directory is writable: `ls -la ~/.agentic-engineers/`
3. Agent will create directory on first use

### Task Memory Path Error
**Symptom**: `ValueError: task_id must be set before calling get_task_memory_path()`

**Fix**:
1. Ensure DELEGATE includes `task_id` field
2. Verify agent's `execute()` method is called with valid DELEGATE
3. Call `get_task_memory_path()` after `task_id` is set

## See Also

- [DELEGATE Protocol Schema](../src/orchestration/delegate-schema.yaml)
- [Agent Framework](../src/orchestration/agents/__init__.py)
- [Agent Invocation](../src/orchestration/agents/invoke_agent.py)
- [Expanded DELEGATE Schema](../src/orchestration/protocol/expanded_delegate.py)
