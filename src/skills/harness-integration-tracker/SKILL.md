---
name: harness-integration-tracker
description: >
  Continuously discover and document agent/sub-agent integration code/docs/info
  across all harnesses (OpenCode, Copilot, Claude, PI) to prevent drift and
  keep integrations fresh. Scans integration code, parses KNOWN_KEYS/KNOWN_MODELS,
  tracks versioning, identifies drift between docs and code, and generates
  integration-summary.yaml per harness.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: integration
  role: orchestrator
  model: sonnet-4-6
  effort: high
  trigger: on-demand | post-framework-update | monthly-schedule
  tdd_phase: RED  # TDD: Tests written first, implementation follows
---

## Overview

**harness-integration-tracker** keeps the agentic-engineers framework aligned with
how each harness actually works. Harnesses (OpenCode, Copilot, Claude, PI) each
have specific capabilities, configuration keys, and model support. This skill
detects and documents those capabilities, tracks changes across versions, and
identifies drift between the real integration code and what the documentation says.

### Purpose

- **Prevent Integration Drift**: Detect when code changes but docs don't (or vice versa)
- **Track Harness Capabilities**: Maintain an up-to-date registry of KNOWN_KEYS and KNOWN_MODELS per harness
- **Version Tracking**: Record breaking changes and new capabilities as harnesses evolve
- **Auto-Generate Docs**: Produce `INTEGRATION-SUMMARY.md` for each harness in `docs/research/{harness}-docs/`
- **Continuous Monitoring**: Enable scheduled runs to catch drift early

## Supported Harnesses

| Harness | Status | Integration Path | KNOWN_MODELS |
|---------|--------|-------------------|---|
| **OpenCode** | ✅ Active | `src/orchestration/agents/` + config | Haiku, Sonnet, Opus |
| **Copilot CLI** | ✅ Active | `src/orchestration/agents/` + config | Haiku, Sonnet, Opus |
| **Claude Code** | ✅ Active | `src/orchestration/agents/` + config | Haiku, Sonnet, Opus |
| **PI** | 🔄 Planned | TBD | TBD |

## Core Concepts

### KNOWN_KEYS

Configuration keys that a harness recognizes. Examples:

```yaml
# OpenCode KNOWN_KEYS
opencode:
  required:
    - role
    - model
  optional:
    - effort
    - reasoning
    - prompt
    - context
```

Detected by:
1. Scanning `config/*.yaml` for harness-specific configs
2. Parsing agent implementations (`src/orchestration/agents/*.py`)
3. Checking environment variables used by harness initialization code

### KNOWN_MODELS

Models that have been tested and verified with this harness.

```yaml
opencode:
  claude_haiku_4.5:
    version: "1.0"
    capability: fast-drafting
    tested: true
  claude_sonnet_4.6:
    version: "1.0"
    capability: standard
    tested: true
  claude_opus_4.8:
    version: "1.0"
    capability: premium
    tested: true
```

Detected by:
1. Scanning test files for model references
2. Parsing model configs in `src/orchestration/models/`
3. Reading integration test results

### Version Tracking

Records breaking changes and new capabilities:

```yaml
opencode:
  versions:
    "1.0":
      released: "2026-05-01"
      breaking_changes: []
      new_capabilities:
        - parallel-sub-agents
        - renderer-safe-output
    "1.1":
      released: "2026-05-15"
      breaking_changes:
        - deprecated-frontmatter-key: "reasoning_style"
      new_capabilities:
        - native-span-capture
```

### Drift Detection

Identifies mismatches between documentation and code:

```yaml
drift_items:
  - file: "docs/research/opencode-docs/OPENCODE_FEATURES_INDEX.md"
    key: "render-safe-output"
    documented: true
    in_code: true
    status: "OK"
  - file: "docs/research/opencode-docs/INTEGRATION-SUMMARY.md"
    key: "force-reasoning"
    documented: true
    in_code: false
    status: "DRIFT: docs mention key that code doesn't support"
  - file: "src/orchestration/agents/opencode.py"
    key: "parallelism_level"
    documented: false
    in_code: true
    status: "DRIFT: code has undocumented key"
```

## Invocation

### Manual Run (All Harnesses)

```bash
python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py
```

### Scan Specific Harness

```bash
python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py --harness opencode
```

### Generate Report Only (No Dry Run)

```bash
python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py --generate-reports
```

### Check Drift Only

```bash
python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py --check-drift --report <path>
```

### Dry Run (Preview Changes)

```bash
python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py --dry-run
```

## Outputs

### INTEGRATION-SUMMARY.md (per harness)

Auto-generated markdown file written to `docs/research/{harness}-docs/INTEGRATION-SUMMARY.md`:

```markdown
# OpenCode Integration Summary

**Last Updated**: 2026-05-31 14:30:00 UTC
**Framework Version**: 5.10.0
**Harness Status**: ✅ Active

## KNOWN_KEYS

### Required
- role (agent role)
- model (model identifier)

### Optional
- effort (task complexity: low, medium, high)
- prompt (task description)
- context (additional context files)
- reasoning (reasoning strategy)

## KNOWN_MODELS

| Model | Version | Capability | Tested | Notes |
|-------|---------|-----------|--------|-------|
| Claude Haiku 4.5 | 1.0 | Fast drafting | ✅ | Default for simple tasks |
| Claude Sonnet 4.6 | 1.0 | Standard | ✅ | Recommended for most tasks |
| Claude Opus 4.8 | 1.0 | Premium | ✅ | Complex reasoning tasks |

## Version History

### v1.1 (Released 2026-05-15)
- **Breaking Changes**: Deprecated `reasoning_style` key
- **New Capabilities**: Native span capture, parallelism_level control

### v1.0 (Released 2026-05-01)
- Initial release

## Drift Detection

| Key | Documented | In Code | Status |
|-----|-----------|---------|--------|
| role | ✅ | ✅ | ✅ OK |
| model | ✅ | ✅ | ✅ OK |
| effort | ✅ | ✅ | ✅ OK |
| reasoning | ✅ | ✅ | ✅ OK |
| parallelism_level | ❌ | ✅ | ⚠️ DRIFT: Code supports but not documented |

## Integration Points

- **Agent Impl**: `src/orchestration/agents/opencode.py`
- **Config**: `config/opencode.yaml`
- **Tests**: `tests/test_opencode_*.py`
- **Docs**: `docs/research/opencode-docs/`

## Recommendations

- [ ] Document the `parallelism_level` key in OPENCODE_FEATURES_INDEX.md
- [ ] Verify deprecation of `reasoning_style` is reflected in docs
- [ ] Add integration tests for v1.1 breaking changes
```

### integration-summary.yaml (Machine-Readable)

Produced in working directory or specified output path:

```yaml
harnesses:
  opencode:
    status: active
    version: "1.1"
    known_keys:
      required: [role, model]
      optional: [effort, prompt, context, reasoning]
    known_models:
      - claude_haiku_4.5
      - claude_sonnet_4.6
      - claude_opus_4.8
    drift:
      - key: parallelism_level
        documented: false
        in_code: true
      - key: reasoning_style
        documented: true
        in_code: false
    integration_points:
      agent_impl: src/orchestration/agents/opencode.py
      config: config/opencode.yaml
      tests: [tests/test_opencode_*.py]
      docs: docs/research/opencode-docs/
  copilot:
    status: active
    version: "2.3.0"
    ...
```

## Implementation Details

### Scanning Algorithm

1. **Parse Agent Code**
   - Scan `src/orchestration/agents/*.py` for harness-specific classes/functions
   - Extract configuration parsing (KNOWN_KEYS detection)
   - Find model references

2. **Parse Configs**
   - Read `config/*.yaml` for harness-specific settings
   - Extract environment variable references
   - Identify version strings

3. **Scan Tests**
   - Find `tests/test_*_{harness}_*.py` files
   - Extract model references from test data
   - Record passing/failing tests per model

4. **Check Drift**
   - Parse `docs/research/{harness}-docs/*.md` files
   - Extract documented KNOWN_KEYS and KNOWN_MODELS
   - Compare with code reality
   - Flag mismatches

5. **Generate Reports**
   - Format findings into markdown (human-readable)
   - Export as YAML (machine-readable)
   - Write to `docs/research/{harness}-docs/INTEGRATION-SUMMARY.md`

### Extensibility

To add a new harness (e.g., PI):

1. Add harness class to `harness_integration_tracker.py`:
   ```python
   class ProjectIrisHarness(Harness):
       provider_name = "pi"
       known_keys_pattern = r"PI_.*"  # env var pattern
   ```

2. Add scan method:
   ```python
   def scan_harness_code(self) -> HarnessMetadata:
       ...
   ```

3. Run skill: `python harness_integration_tracker.py --harness pi`

## Testing Strategy (TDD)

Tests cover:

1. **Unit Tests** (~70% coverage)
   - Harness parsing (KNOWN_KEYS extraction)
   - Drift detection (docs vs code comparison)
   - Model version tracking
   - YAML generation

2. **Integration Tests** (~20% coverage)
   - End-to-end scan + report generation
   - Multi-harness scanning
   - Report file writing

3. **Acceptance Tests** (~10% coverage)
   - Verify all harness docs updated
   - Confirm no regressions in docs
   - Validate YAML structure against schema

**Target**: ≥85% code coverage

## Scheduling

### Recommended Run Frequency

```cron
# Daily drift check
0 9 * * * cd /path/to/agentic-engineers && python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py --check-drift

# Weekly full scan + report generation
0 2 * * 0 cd /path/to/agentic-engineers && python src/skills/harness-integration-tracker/scripts/harness_integration_tracker.py --generate-reports
```

### Manual Triggers

- After harness version upgrade (OpenCode, Copilot, Claude)
- Before pushing changes to integration code
- Post-framework version release
- When adding new harness support (PI)

## Related Skills

- **harness-opencode-feature-sync**: Monitors OpenCode-specific renderer alignment
- **protocol-validator**: Validates DELEGATE/HANDBACK protocols
- **spec-validator**: Ensures code complies with SPEC.md

## References

- Framework docs: `docs/PROTOCOL.md`, `docs/QUEUE-PROTOCOL.md`
- Harness research: `docs/research/{harness}-docs/`
- Integration code: `src/orchestration/agents/`, `src/orchestration/models/`
- Tests: `tests/test_*_harness*.py`, `tests/test_harness_integration_tracker.py`

---

**Created**: 2026-05-31
**Last Updated**: 2026-05-31
**Maintained by**: Agentic Engineers Core Team
