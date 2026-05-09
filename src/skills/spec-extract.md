---
name: Spec-Extract Skill
description: Generate specification from codebase to generate/update docs/SPEC.md
type: skill
phase: 6
status: SPEC_COMPLETE
---

# Spec-Extract Skill

**Purpose**: Extract specification from codebase. Analyze code structure, APIs, data models, architecture. Generate/update docs/SPEC.md automatically.

**When to Use**: 
- Initial spec generation (new service)
- Periodic spec refresh (ensure SPEC.md current)
- After major code changes

**Invoked By**: Spec Engineer agent, Healing Agent, manual trigger

---

## Skill Process

1. Analyze code structure (packages, modules, entry points)
2. Extract public APIs (functions, HTTP endpoints, signatures)
3. Extract data models (types, structs, schemas)
4. Extract architecture (responsibilities, dependencies, data flow)
5. Extract configuration (env vars, feature flags)
6. Generate SPEC.md from template

---

## Output Format

Generates docs/SPEC.md with sections:
- **Overview**: Service purpose
- **Architecture**: Responsibilities, dependencies, data flow
- **Features**: Each feature with inputs, outputs, errors
- **Data Models**: Types, structs, database schemas
- **APIs**: HTTP endpoints, parameters, responses
- **Configuration**: Environment variables, options
- **Integration**: Services called, called by
- **Rate Limits**: API rate limits
- **Deprecated**: Deprecated features with migration path

---

## Success Criteria

- ✅ Valid SPEC.md markdown format
- ✅ Extracts features accurately
- ✅ Extracts APIs accurately  
- ✅ Includes all data models
- ✅ Detects major drift (80%+ accuracy)
- ✅ Readable, well-organized output
