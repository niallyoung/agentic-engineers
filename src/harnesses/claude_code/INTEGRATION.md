# Claude Code Harness Integration Guide

**Purpose:** Developer reference for Claude Code harness architecture and module integration points.

**Audience:** Engineers extending or debugging the Claude Code harness.

---

## Module Overview

The Claude Code harness is composed of 8 Python modules that work together to manage agent lifecycle, model selection, token budgeting, and error handling. Each module has a distinct responsibility.

### Core Modules

| Module | Purpose | Lines | Key Classes |
|--------|---------|-------|-------------|
| `__init__.py` | Package initialization, harness entry point | ~50 | `ClaudeCodeHarness` |
| `agent_dispatch.py` | Agent routing and execution | ~450 | `AgentDispatcher`, `AgentRouter` |
| `model_registry.py` | Model aliases and capability mapping | ~200 | `ModelRegistry`, `ModelCapabilities` |
| `skill_renderer.py` | Skill definition parsing and availability | ~450 | `SkillRenderer`, `SkillRegistry` |
| `handback_processor.py` | HANDBACK validation and metrics extraction | ~300 | `HandbackProcessor`, `MetricsExtractor` |
| `token_budget.py` | Token usage tracking and budget enforcement | ~250 | `TokenBudgetManager`, `BudgetTracker` |
| `timeout_handler.py` | Operation timeout management | ~200 | `TimeoutHandler`, `TimeoutPolicy` |
| `error_handler.py` | Error detection, formatting, and remediation | ~350 | `ErrorHandler`, `RemediationEngine` |

**Total:** ~2,150 lines of production code

---

## Module Responsibilities

### 1. `__init__.py` — Package Initialization

**Exports:** `ClaudeCodeHarness` class

**Responsibilities:**
- Initialize harness on import
- Load global configuration from `~/.claude/config/claude.jsonc`
- Set up logging and telemetry
- Export public API

**Public API:**
```python
from src.harnesses.claude_code import ClaudeCodeHarness

harness = ClaudeCodeHarness()
response = harness.execute_delegate(delegate_dict)
```

---

### 2. `agent_dispatch.py` — Agent Routing and Execution

**Classes:**
- `AgentRouter` — Routing decision tree based on task type and effort
- `AgentDispatcher` — Executes agents and collects telemetry

**Key Methods:**
```python
AgentRouter.route(delegate: dict) -> Agent
  # Returns the best agent for this task
  # Inputs: task_type, effort, complexity signals
  # Output: Agent instance

AgentDispatcher.execute(agent: Agent, delegate: dict) -> dict
  # Executes agent and returns HANDBACK
  # Calls agent.invoke() and validates response schema
```

**Integrations:**
- Reads from `ModelRegistry` for model assignments
- Writes to `TokenBudgetManager` for token tracking
- Calls `TimeoutHandler` to enforce execution limits
- Passes responses to `HandbackProcessor` for validation

---

### 3. `model_registry.py` — Model Aliases and Capabilities

**Classes:**
- `ModelRegistry` — Maintains model aliases (haiku→claude-haiku-4.5)
- `ModelCapabilities` — Tracks model properties (max tokens, cost/1K)

**Key Methods:**
```python
ModelRegistry.get_model(alias: str) -> str
  # Resolve 'opus' → 'claude-opus-4'

ModelRegistry.override(role: str, model: str) -> None
  # Set session/project override (e.g., engineer→opus)

ModelCapabilities.max_tokens(model: str) -> int
  # Returns token limit for model

ModelCapabilities.cost_per_1k(model: str) -> float
  # Returns USD cost per 1000 tokens
```

**Integrations:**
- Reads configuration from `~/.claude/config/claude.jsonc`
- Used by `AgentDispatcher` to assign models to agents
- Used by `TokenBudgetManager` to calculate costs

---

### 4. `skill_renderer.py` — Skill Definition Parsing

**Classes:**
- `SkillRenderer` — Loads and parses skill SKILL.md files
- `SkillRegistry` — In-memory index of available skills

**Key Methods:**
```python
SkillRenderer.load_all_skills(skill_dir: str) -> SkillRegistry
  # Parse all skills from ~/.claude/config/skills/
  # Extract YAML frontmatter, purpose, dependencies

SkillRegistry.get_skill(name: str) -> Skill
  # Retrieve skill by name (or error)

SkillRegistry.validate_dependencies() -> List[Error]
  # Detect circular dependencies or missing skills
```

**Integrations:**
- Reads skill definitions from `~/.claude/config/skills/`
- Validates skill availability at startup
- Provides skill list to agent CLAUDE.md generation

---

### 5. `handback_processor.py` — HANDBACK Validation

**Classes:**
- `HandbackProcessor` — Schema validation and response parsing
- `MetricsExtractor` — Extracts quality/token/cost metrics

**Key Methods:**
```python
HandbackProcessor.validate(response: dict) -> bool
  # Check HANDBACK matches schema
  # Required fields: task_id, status, output, metrics

MetricsExtractor.extract_metrics(response: dict) -> Metrics
  # Parse tokens, quality, cost, duration
  # Aggregate and normalize values
```

**Integrations:**
- Loads schema from `src/orchestration/handback-schema.yaml`
- Validates all agent responses
- Extracts metrics for `TokenBudgetManager` and telemetry

---

### 6. `token_budget.py` — Token Usage Tracking

**Classes:**
- `TokenBudgetManager` — Per-session and per-day budget enforcement
- `BudgetTracker` — Accumulates token usage over time

**Key Methods:**
```python
TokenBudgetManager.check_budget(tokens_in: int, tokens_out: int) -> bool
  # Check if task would exceed session/daily limits
  # Returns True if within budget, False if would exceed

TokenBudgetManager.record_usage(tokens_in: int, tokens_out: int) -> None
  # Record tokens after task completes
  # Updates session and daily accumulators

TokenBudgetManager.get_remaining() -> dict
  # Returns {'session': N, 'daily': N} tokens remaining
```

**Integrations:**
- Reads budget config from `~/.claude/config/claude.jsonc`
- Called by `AgentDispatcher` before execution
- Receives metrics from `HandbackProcessor` after execution

---

### 7. `timeout_handler.py` — Operation Timeout Management

**Classes:**
- `TimeoutHandler` — Enforces per-operation timeout limits
- `TimeoutPolicy` — Configurable timeout per agent or skill

**Key Methods:**
```python
TimeoutHandler.get_timeout(agent: str, operation: str) -> int
  # Returns timeout in milliseconds
  # Looks up: agent-specific → operation-specific → global default

TimeoutHandler.enforce(operation: str, func: callable) -> Any
  # Execute func with timeout
  # Raises TimeoutError if limit exceeded
```

**Integrations:**
- Reads timeouts from `~/.claude/config/claude.jsonc`
- Called by `AgentDispatcher` to wrap agent execution
- Catches and formats TimeoutError via `ErrorHandler`

---

### 8. `error_handler.py` — Error Detection and Remediation

**Classes:**
- `ErrorHandler` — Categorizes and formats errors
- `RemediationEngine` — Suggests fixes for common issues

**Key Methods:**
```python
ErrorHandler.catch_and_format(exception: Exception) -> ErrorInfo
  # Categorize: ConfigError, SchemaError, TimeoutError, etc.
  # Format user-friendly message

RemediationEngine.suggest_fix(error: ErrorInfo) -> str
  # Return suggested remediation steps
  # Example: "Run 'make install-claude' to fix model not found"
```

**Integrations:**
- Called by all other modules when exceptions occur
- Produces error summaries for console and logs
- Feeds suggestions to operator

---

## Public API Surface

The harness exposes a single entry point:

```python
# src/harnesses/claude_code/__init__.py

class ClaudeCodeHarness:
    """Public API for Claude Code harness."""

    def execute_delegate(self, delegate: dict) -> dict:
        """
        Execute a DELEGATE block and return HANDBACK.

        Args:
            delegate: DELEGATE dict with task_id, agent, scope, plan, success_criteria

        Returns:
            HANDBACK dict with task_id, status, output, metrics

        Raises:
            DelegateValidationError: Invalid DELEGATE structure
            ConfigError: Configuration missing or malformed
            TimeoutError: Agent execution timed out
        """
        # Implementation:
        # 1. Validate DELEGATE schema
        # 2. Check token budget
        # 3. Route to agent via AgentDispatcher
        # 4. Validate HANDBACK response
        # 5. Record metrics
        # 6. Return HANDBACK
```

---

## Module Integration Flow

```
User submits DELEGATE
  ↓
ClaudeCodeHarness.execute_delegate()
  ├─→ Validate schema (protocol_validator)
  ├─→ Check token budget (TokenBudgetManager.check_budget)
  ├─→ Route to agent (AgentRouter.route)
  │    └─→ Look up model (ModelRegistry.get_model)
  ├─→ Execute agent (AgentDispatcher.execute)
  │    ├─→ Enforce timeout (TimeoutHandler.enforce)
  │    ├─→ Record telemetry (span_capture)
  │    └─→ Handle errors (ErrorHandler)
  ├─→ Validate response (HandbackProcessor.validate)
  ├─→ Extract metrics (MetricsExtractor)
  ├─→ Record usage (TokenBudgetManager.record_usage)
  └─→ Return HANDBACK
```

---

## Configuration Loading

The harness loads configuration in this order (first-found wins):

1. **Session Override** — `~/.claude/sessions/{session-id}/config.jsonc`
2. **Project Override** — `{project-root}/.claude/agents.jsonc`
3. **Per-Project Global** — `~/.claude/projects/{project-name}/agents.jsonc`
4. **Global Config** — `~/.claude/config/claude.jsonc`
5. **Defaults** — Built-in in `__init__.py`

---

## Error Handling Strategy

All modules follow this pattern:

```python
try:
    # Perform operation
    result = do_something()
except SpecificError as e:
    # Categorize
    error_info = ErrorHandler.categorize(e)
    # Suggest fix
    fix = RemediationEngine.suggest(error_info)
    # Return error response (not raise)
    return {
        'status': 'failed',
        'error': error_info.message,
        'remediation': fix
    }
```

This keeps errors informative and actionable without forcing exceptions up the stack.

---

## Testing Entry Points

Each module has unit tests in `tests/harnesses/claude_code/`:

```bash
# Test agent routing
python -m pytest tests/harnesses/claude_code/test_agent_dispatch.py

# Test token budget enforcement
python -m pytest tests/harnesses/claude_code/test_token_budget.py

# Test error handling
python -m pytest tests/harnesses/claude_code/test_error_handler.py

# Run all harness tests
python -m pytest tests/harnesses/claude_code/ -v
```

---

## Extension Points

### Adding a New Agent

1. Create agent definition: `~/.claude/config/agents/my-agent.md`
2. Register in `ModelRegistry`: add to `claude.jsonc`
3. Add routing rule in `AgentRouter.route()` if new task type
4. Test via: `ClaudeCodeHarness.execute_delegate(delegate)`

### Customizing Model Selection

Override `ModelRegistry.get_model()`:

```python
# In ~/.claude/config/claude.jsonc
{
  "model_overrides": {
    "engineer": "opus",  // Always use Opus for engineers
    "orchestrator": "sonnet"
  }
}
```

### Adding Timeout Policy

Edit `~/.claude/config/claude.jsonc`:

```jsonc
{
  "timeouts": {
    "agent_response": 120000,  // 2 min default
    "skill_invocation": 30000  // 30s for skills
  }
}
```

### Modifying Budget Logic

Edit `token_budget.py`, then restart Claude Code:

```python
# Example: enforce hourly limit instead of daily
TokenBudgetManager.check_hourly_budget()
```

---

## Performance Characteristics

| Operation | Typical Time | Bottleneck |
|-----------|--------------|-----------|
| Initialize harness | <100ms | JSONC parsing |
| Route DELEGATE | <50ms | Config lookup |
| Validate HANDBACK | <100ms | Schema validation |
| Extract metrics | <50ms | JSON parsing |
| Check budget | <10ms | In-memory lookup |

**Total per-request overhead:** ~300ms (excluding agent execution)

---

## Further Reading

- [Claude Code Harness Setup](../guides/harness-setup/claude.md) — User setup guide
- [Claude Code Extension Guide](../guides/claude-harness-extension.md) — Configuration customization
- [Troubleshooting Guide](../HARNESS-CLAUDE-TROUBLESHOOTING.md) — Common issues and fixes
- [DELEGATE/HANDBACK Protocol](../orchestration/HANDOFF.md) — Protocol specification
- [Model Selection Framework](../orchestration/AGENTS.md) — Routing rules
