# π.dev + agentic-engineers Integration — Quick Start

## What Was Built

✅ **π.dev Renderer** — Python script to render agentic-engineers config into π.dev harness  
✅ **System Prompt** — Complete Orchestrator identity prompt (134 lines)  
✅ **Agent Roles** — 10 specialized agent roles with routing logic (223 lines)  
✅ **Settings** — Model defaults, UI theme, compaction config  
✅ **Documentation** — Comprehensive integration guide  

## Files Created

### Renderer Sources (committed to git)

```
renderer/
├── pi-dev-src/
│   ├── SYSTEM.md              ← Orchestrator identity + responsibilities
│   ├── AGENTS.md              ← 10 agent roles + routing decision tree
│   └── settings.json          ← Model defaults (Sonnet, dark theme, etc.)
│
├── scripts/
│   └── render-pi-dev.py       ← Renderer executable (NEW)
│
├── PI-DEV-RENDERER.md         ← Full integration documentation
└── README.md                  ← Updated with π.dev section
```

### Generated Files (in ~/.pi/agent/)

```
~/.pi/agent/
├── SYSTEM.md           ← Rendered Orchestrator prompt (replaces π.dev default at bootstrap)
├── AGENTS.md           ← Rendered agent definitions
└── settings.json       ← Rendered model defaults
```

## Quick Test

```bash
# Already done! Files are in ~/.pi/agent/

# To re-render if you modify sources:
cd /path/to/agentic-engineers
python3 renderer/scripts/render-pi-dev.py

# To use with π.dev:
cd /your/project
pi
```

## Key Technical Achievements

### ✅ 100% System Prompt Control from Bootstrap

Research findings confirmed that π.dev reads `~/.pi/agent/SYSTEM.md` **first** and uses it as the complete system prompt, replacing the built-in π default.

**This means**:
- No π.dev forking required
- Works with standard `pi` binary (v0.74.0+)
- Complete control from turn 1 (no defaults leak through)
- Guaranteed agentic-engineers identity

### ✅ Config-Driven (No Code Changes)

Using clean config files instead of forking π gives:
- Future compatibility with π updates
- Easy customization per project (`.pi/SYSTEM.md` overrides)
- Transparent source control (sources in git, rendered files local-only)
- Clean separation of concerns

### ✅ Comprehensive Agent Framework

AGENTS.md defines:
- 10 specialized roles (Engineer, Senior Engineer, Security Engineer, Principal Engineer, etc.)
- Role expertise and best-use cases
- DELEGATE and HANDBACK patterns
- Routing decision tree
- Quality gates and token optimization

### ✅ Production-Ready

Renderer is:
- Idempotent (safe to run multiple times)
- Validated (JSON schema check, markdown structure)
- Documented (complete integration guide in PI-DEV-RENDERER.md)
- Tested (successfully generates all files)

## Documentation

**Complete guide**: [renderer/PI-DEV-RENDERER.md](../renderer/PI-DEV-RENDERER.md)

Covers:
- Installation & setup
- How system prompt control works
- Advanced: project-level overrides
- Advanced: TypeScript extensions
- Troubleshooting
- CLI reference

## Integration Status

- ✅ Research complete (pi.dev config structure, system prompt control mechanisms)
- ✅ Renderer implemented (Python script, 70 lines)
- ✅ Source files created (SYSTEM.md, AGENTS.md, settings.json)
- ✅ Files rendered to ~/.pi/agent/ (tested and verified)
- ✅ Documentation complete (PI-DEV-RENDERER.md, updated README.md)
- ✅ Ready for use and further development

## Next Steps (Future)

1. **TypeScript Extensions** — Dynamic per-turn prompt modifications (if needed)
2. **Project Overrides** — Create `.pi/SYSTEM.md` for repo-specific behavior
3. **Extended Thinking** — Configure when to use Claude's extended thinking mode
4. **A/B Testing** — Run experiments with different agent configs

## Files to Review

1. [renderer/PI-DEV-RENDERER.md](../renderer/PI-DEV-RENDERER.md) — Complete integration guide
2. [renderer/pi-dev-src/SYSTEM.md](../renderer/pi-dev-src/SYSTEM.md) — Master system prompt
3. [renderer/pi-dev-src/AGENTS.md](../renderer/pi-dev-src/AGENTS.md) — Agent role definitions
4. [renderer/scripts/render-pi-dev.py](../renderer/scripts/render-pi-dev.py) — Renderer implementation

---

**Status**: COMPLETE ✅  
**Rendered**: 2026-05-15 21:58  
**π.dev Version**: 0.74.0+  
**agentic-engineers Version**: 1.0
