# OpenCode Harness Troubleshooting Guide

This guide helps diagnose and fix OpenCode harness configuration issues at startup.

## Quick Start

Run the harness validator to check the health of your OpenCode installation:

```bash
# Standard output
python3 -m src.harness.harness_checker

# JSON output (for programmatic parsing)
python3 -m src.harness.harness_checker --json

# With explicit repo root
python3 -m src.harness.harness_checker --repo-root /path/to/agentic-engineers
```

## Common Issues and Fixes

### ❌ Agent Check Failed

**Problem:** `check_agents_loaded` failed

This means the 8 required agents are not properly defined in `AGENTS.md`.

**Causes:**
- `src/AGENTS.md` is missing or corrupted
- Agent roster table is incomplete (fewer than 8 agents)
- Agent role names don't match specification

**Fix:**
```bash
# Verify AGENTS.md exists and is valid
ls -la src/AGENTS.md

# Check agent count (should show 8 agent entries)
grep "^| [1-8] |" src/AGENTS.md | wc -l

# If missing, restore from git:
git checkout src/AGENTS.md
```

**Expected agents:**
1. Orchestrator
2. Engineer
3. Model Engineer
4. Quality Engineer
5. Lead Engineer
6. Senior Engineer
7. Principal Engineer
8. Security Engineer

---

### ❌ Skills Check Failed

**Problem:** `check_skills_available` failed

This means required skills are not available in the `dist/opencode/skills/` directory.

**Causes:**
- OpenCode renderer has not been run
- Skills directory is missing or incomplete
- Less than 14 skills are installed

**Fix:**
```bash
# Run the OpenCode renderer
python3 renderer/scripts/render-opencode.sh

# Verify skills directory was created
ls -la dist/opencode/skills/ | head -20

# Check skill count (should be ≥14)
ls -d dist/opencode/skills/*/ | wc -l
```

**Note:** The renderer must be run after adding or updating skills.

---

### ❌ Queue Paths Check Failed

**Problem:** `check_queue_paths` failed

This means the queue directory structure is not properly initialized.

**Causes:**
- Queue base directory `~/.agentic-engineers/` doesn't exist
- Queue subdirectories are missing
- Directory permissions prevent creation

**Fix:**
```bash
# Create the queue structure manually
mkdir -p ~/.agentic-engineers/default/opencode/queue/{incoming,processing,done}

# Verify structure was created
tree ~/.agentic-engineers/ -L 3

# Check permissions
ls -ld ~/.agentic-engineers/
```

**Structure expected:**
```
~/.agentic-engineers/
├── {session-id}/
│   └── opencode/
│       └── queue/
│           ├── incoming/    # DELEGATE files go here
│           ├── processing/  # In-flight HANDBACKs
│           └── done/        # Completed HANDBACKs
```

**Permission fix (if needed):**
```bash
chmod 755 ~/.agentic-engineers
chmod 755 ~/.agentic-engineers/default
chmod 755 ~/.agentic-engineers/default/opencode
chmod 755 ~/.agentic-engineers/default/opencode/queue
chmod 755 ~/.agentic-engineers/default/opencode/queue/{incoming,processing,done}
```

---

### ❌ Orchestrator Check Failed

**Problem:** `check_orchestrator` failed

This means the Orchestrator agent configuration is not properly set up.

**Causes:**
- OpenCode renderer has not been run
- `dist/opencode/agents/orchestrator.md` is missing or empty
- Orchestrator agent file is corrupted

**Fix:**
```bash
# Run the OpenCode renderer
python3 renderer/scripts/render-opencode.sh

# Verify orchestrator agent was created
ls -la dist/opencode/agents/orchestrator.md

# Check file size (should be > 1KB)
wc -c dist/opencode/agents/orchestrator.md

# Verify content
head -30 dist/opencode/agents/orchestrator.md
```

**Expected content in orchestrator.md:**
- YAML frontmatter with model and permissions
- Orchestrator role description
- Responsibilities section
- Routing decision tree
- Example DELEGATE blocks

---

### ❌ Schema Validation Failed

**Problem:** `check_schemas` failed

This means DELEGATE/HANDBACK schema files are missing or invalid.

**Causes:**
- Schema files missing from docs/specs/
- `delegate-schema.yaml` or `handback-schema.yaml` missing
- Schema files don't contain `required_fields` section
- YAML is malformed

**Fix:**
```bash
# Verify schemas exist
ls -la docs/specs/{delegate,handback}-schema.yaml

# Validate YAML syntax
python3 << 'EOF'
import yaml
for schema_file in ["docs/specs/delegate-schema.yaml", "docs/specs/handback-schema.yaml"]:
    with open(schema_file) as f:
        try:
            data = yaml.safe_load(f)
            print(f"✅ {schema_file} is valid YAML")
            if "required_fields" in data:
                print(f"   - Has required_fields section with {len(data['required_fields'])} fields")
            else:
                print(f"   ⚠️  Missing required_fields section")
        except yaml.YAMLError as e:
            print(f"❌ {schema_file} has YAML errors: {e}")
EOF
```

**Expected schema structure:**
```yaml
required_fields:
  task_id:
    type: string
    pattern: ...
    description: ...
  role:
    type: string
    enum: [...]
  model:
    type: string
  # ... more fields
```

---

## Full Validation Report Example

```
======================================================================
OpenCode Harness Validation Report
======================================================================

✅ check_agents_loaded: All 8 agents are defined in AGENTS.md

✅ check_skills_available: All 19 skills are available with documentation

❌ check_queue_paths: No canonical queue directories found in ~/.agentic-engineers
   → Remediation: Initialize queue structure: `mkdir -p ~/.agentic-engineers/default/opencode/queue/{incoming,processing,done}`

✅ check_orchestrator: Orchestrator agent is properly configured

✅ check_schemas: All schemas are valid and properly configured

======================================================================
Result: FAILED (1 critical, 4 passed)
======================================================================
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed ✅ |
| 1 | One or more critical checks failed ❌ |
| 2 | Non-critical warnings (deprecated, not currently used) |

## Advanced Troubleshooting

### Check Repository Integrity

If multiple checks are failing, the repository may be corrupted:

```bash
# Verify repository structure
./scripts/verify-repo-integrity.sh

# Restore to known-good state
git status  # Check for uncommitted changes
git restore src/AGENTS.md src/SKILLS.md
```

### Manual Harness Initialization

If the harness checker can't fix issues automatically:

```bash
# 1. Ensure AGENTS.md is valid
git checkout src/AGENTS.md

# 2. Run the OpenCode renderer
python3 renderer/scripts/render-opencode.sh

# 3. Initialize queue structure
mkdir -p ~/.agentic-engineers/default/opencode/queue/{incoming,processing,done}

# 4. Re-run the checker
python3 -m src.harness.harness_checker
```

### Debug Mode

For detailed troubleshooting, examine the HarnessChecker logs:

```python
from src.harness.harness_checker import HarnessChecker

checker = HarnessChecker()
result = checker.check_agents_loaded()
print(f"Check: {result.check_name}")
print(f"Passed: {result.passed}")
print(f"Message: {result.message}")
print(f"Remediation: {result.remediation}")

# Run all checks
report = checker.run_all_checks()
for check in report.checks:
    print(check.format())
```

## Integration with OpenCode

The HarnessChecker is designed to run at OpenCode startup to catch configuration errors early.

### Add to OpenCode Init

In `src/opencode/__init__.py`:

```python
from src.harness.harness_checker import HarnessChecker

# At module load time
try:
    checker = HarnessChecker()
    report = checker.run_all_checks()
    if not report.all_passed:
        # Log warnings but don't block
        for check in report.checks:
            if not check.passed:
                print(f"⚠️  {check.format()}")
except Exception as e:
    print(f"⚠️  Harness check skipped: {e}")
```

## Performance

The harness validator is designed to run quickly at startup:

- **Target:** <100ms for all 5 checks
- **Typical time:** 10-50ms (depends on filesystem speed)
- **No blocking I/O:** All checks use local files only

## Further Reading

- [`src/AGENTS.md`](../src/AGENTS.md) — Agent roster and protocol specification
- [`docs/specs/delegate-schema.yaml`](../docs/specs/delegate-schema.yaml) — DELEGATE block schema
- [`docs/specs/handback-schema.yaml`](../docs/specs/handback-schema.yaml) — HANDBACK block schema
- [`dist/opencode/AGENTS.md`](../dist/opencode/AGENTS.md) — OpenCode-specific agent rules
