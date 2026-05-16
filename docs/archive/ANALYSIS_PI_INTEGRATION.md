# Pi Integration Analysis & Update Plan

## 📊 Current State Analysis

### Backup Location
```
~/backups/.pi-backup-20260516_074815/agent/
```

### Files Comparison

#### New Files (Not in renderer/pi-dev-src/)
| File | Size | Purpose | Managed By |
|------|------|---------|------------|
| `pi.yml` | 4.3 KB | Sub-agent orchestration config | **SHOULD be rendered** |
| `SUB_AGENT_SETUP.md` | 4.6 KB | User documentation for setup | **SHOULD be rendered** |

#### Modified Files
| File | Changes | Should Render |
|------|---------|--------------|
| `settings.json` | Model version + extensions/packages/skills | **YES** |

#### Pi-Managed Files (Do NOT render)
| File | Purpose |
|------|---------|
| `auth.json` | Authentication tokens (Pi maintains) |
| `bin/` | Pi binaries (Pi installs) |
| `sessions/` | Session data (Pi maintains) |

---

## 🔍 Detailed Differences

### settings.json Changes Needed
```diff
- defaultModel: "claude-sonnet-4-20250514" → "claude-3-5-sonnet-20241022"
+ packages: ["orchestration-framework"]
+ extensions: ["agent-orchestrator", "specialized-agents"]
+ skills: ["delegate", "handback", "route-task", "collect-metrics", "verify-completion"]
+ lastChangelogVersion: "0.74.0"
```

### pi.yml Structure (NEW)
**Location**: Should be rendered to `~/.pi/agent/pi.yml`

**Key Sections**:
1. **core** - Default provider, model, thinking settings
2. **extensions** - Agent orchestrator + specialized agents (9 roles)
3. **routing** - Task routing decision tree
4. **skills** - Delegation, handback, routing, metrics, verification
5. **packages** - orchestration-framework
6. **optimization** - Token budget, cost-quality settings

**Purpose**: Enables Pi to understand the agentic-engineers sub-agent framework

---

## ✅ Renderer Update Plan

### 1. Update renderer/pi-dev-src/
- ✅ Add `pi.yml` to source directory
- ✅ Add `SUB_AGENT_SETUP.md` to source directory
- ✅ Update `settings.json` with extensions/packages/skills
- ✅ Update `SYSTEM.md` and `AGENTS.md` (already current)

### 2. Update render-pi-dev.py
- ✅ Extend `files_to_render` list to include:
  - pi.yml
  - SUB_AGENT_SETUP.md
- ✅ Add option to specify source directory (defaults to renderer/pi-dev-src/)
- ✅ Add validation for pi.yml YAML structure
- ✅ Add install/uninstall support via --uninstall flag

### 3. Update Makefile
**New targets needed**:
```makefile
render-pi: ## Generate dist/pi/ with pi.dev configuration
install-pi: render-pi ## Install to ~/.pi/agent/
install-all: install-copilot install-claude install-pi ## Install to all 3 locations
uninstall-pi: ## Remove from ~/.pi/
status-pi: ## Check ~/.pi/ installation status
```

### 4. Create render-pi.sh script
Similar to render-copilot.sh and render-claude.sh:
- Copies rendered files to ~/.pi/agent/
- Preserves Pi-managed files (auth.json, bin/, sessions/)
- Supports --uninstall and --status modes

---

## 📋 Reverse-Engineered Pi Expectations

### pi.yml Format & Structure
Pi expects a YAML configuration file at `~/.pi/agent/pi.yml` that defines:

1. **Extensions** - Capabilities that extend Pi's core behavior
   ```yaml
   extensions:
     - name: "agent-orchestrator"
       capabilities: ["task-routing", "delegation", "metrics"]
   ```

2. **Agents** - Individual specialized agent definitions
   ```yaml
   agents:
     - id: "engineer"
       role: "Engineer"
       model: "claude-3-5-haiku-20241022"
       expertise: "..."
       scope: "..."
   ```

3. **Routing** - Decision tree for task assignment
   ```yaml
   routing:
     rules:
       - condition: "security-scoped"
         agent: "security-engineer"
         priority: 1
   ```

4. **Skills** - Custom capabilities/tools
   ```yaml
   skills:
     - name: "delegate"
       description: "Delegate task to sub-agent"
   ```

5. **Optimization** - Cost and performance settings
   ```yaml
   optimization:
     tokenBudget: 200000
     costQualityTradeoff: "quality-first"
   ```

### Settings.json Format
Pi uses this for UI/model configuration:
```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-3-5-sonnet-20241022",
  "extensions": ["agent-orchestrator", "specialized-agents"],
  "packages": ["orchestration-framework"],
  "skills": ["delegate", "handback", "route-task", ...]
}
```

### File Hierarchy
```
~/.pi/
├── agent/                      # Managed by agentic-engineers renderer
│   ├── SYSTEM.md              # System prompt (rendered)
│   ├── AGENTS.md              # Agent context (rendered)
│   ├── settings.json          # Model settings (rendered)
│   ├── pi.yml                 # Sub-agent config (rendered)
│   ├── SUB_AGENT_SETUP.md     # Documentation (rendered)
│   ├── auth.json              # [Pi-managed, DO NOT touch]
│   ├── bin/                   # [Pi-managed, DO NOT touch]
│   └── sessions/              # [Pi-managed, DO NOT touch]
```

---

## 🛠️ Implementation Steps

### Phase 1: Prepare Source Files
1. Move pi.yml to renderer/pi-dev-src/
2. Move SUB_AGENT_SETUP.md to renderer/pi-dev-src/
3. Update settings.json in renderer/pi-dev-src/

### Phase 2: Update Renderer Script
1. Extend render-pi-dev.py to handle all 5 files
2. Add YAML validation
3. Add --uninstall support
4. Create render-pi.sh wrapper script

### Phase 3: Update Makefile
1. Add render-pi target
2. Add install-pi target
3. Add uninstall-pi target
4. Add status-pi target
5. Update install-all to include install-pi

### Phase 4: Testing
1. Test: `make install-pi`
2. Verify files in ~/.pi/agent/
3. Verify Pi loads config correctly
4. Test: `make uninstall-pi`
5. Verify removal and restore behavior

---

## 🎯 Success Criteria
- ✅ All 5 files properly rendered to ~/.pi/agent/
- ✅ pi.yml validates as proper YAML
- ✅ settings.json has all extensions/packages/skills
- ✅ Makefile has install-pi, uninstall-pi, status-pi targets
- ✅ Pi-managed files (auth.json, bin/, sessions/) never overwritten
- ✅ `make install-all` installs to all 3 locations
- ✅ Full round-trip: generate → install → verify → uninstall works

---

## 📝 Blockers/Notes
- None identified; clean path forward
