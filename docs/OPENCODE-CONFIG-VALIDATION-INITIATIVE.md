# OpenCode Configuration Validation Initiative

## Problem: Critical Blind Spot

The Orchestrator (OpenCode CLI harness) has experienced **2 configuration errors** that broke functionality:

1. **First incident**: Unknown (needs investigation)
2. **Second incident (May 17)**: Missing `template` field in custom command definitions
   - Error: `ConfigInvalidError: 4 of 5 requests failed`
   - Impact: OpenCode CLI became unusable
   - Detection: Only caught when running opencode commands (too late)
   - Fix: Copilot CLI had to fix it manually

**Root Cause**: No proactive validation system to catch errors BEFORE installation.

**Why This Matters**: 
- OpenCode CLI is the Orchestrator's primary harness
- Configuration errors break the entire workflow
- The Orchestrator should be self-aware and self-defensive about protecting its own configuration
- We can't rely on external tools (Copilot CLI) to fix our mistakes

## Solution: Comprehensive Validation System

Created **1 DELEGATE** to investigate, design, and implement a proactive validation system:

### **2026-05-17-opencode-config-validation**
**Role**: Security Engineer  
**Model**: Claude Opus 4 (extended thinking)  
**Effort**: High  
**Tokens**: 10,000  

**Scope**: 
1. Investigate all previous opencode.jsonc configuration errors
2. Analyze root causes and patterns
3. Document OpenCode schema requirements
4. Design validation system (pre-commit, pre-install, runtime)
5. Implement JSON Schema validator
6. Add automated testing
7. Design self-defense mechanisms (backup, rollback, audit trail, integrity checks)

**Deliverables** (10 documents + code):
1. Root cause analysis of all incidents
2. Complete OpenCode schema documentation
3. JSON Schema validator (src/opencode/config_validator.py)
4. Pre-commit validation hook (.githooks/pre-commit)
5. Pre-installation validation script (scripts/validate-opencode-config.sh)
6. Runtime validation wrapper (scripts/opencode-safe.sh)
7. Automated tests (tests/test_opencode_config_validation.py, ≥95% coverage)
8. Validation system user guide
9. Common mistakes and how to avoid them
10. Configuration recovery procedures

**Success Criteria**:
- ✅ All previous errors documented and analyzed
- ✅ OpenCode schema fully documented
- ✅ JSON Schema validator implemented
- ✅ Pre-commit hook validates opencode.jsonc
- ✅ Pre-installation validation implemented
- ✅ Runtime validation wrapper implemented
- ✅ Automated tests catch all known errors (regression test)
- ✅ Configuration backup/rollback system implemented
- ✅ Configuration audit trail implemented
- ✅ Configuration integrity checks implemented
- ✅ Quality: 95/100 (security-critical)
- ✅ Coverage: ≥95%

## Why This Matters

### Current State (Broken)
- ❌ No validation of opencode.jsonc before commit
- ❌ No validation before installation
- ❌ Errors only caught when running opencode commands
- ❌ No backup/rollback mechanism
- ❌ No audit trail of configuration changes
- ❌ No integrity checks

### Desired State (Protected)
- ✅ Pre-commit validation prevents invalid commits
- ✅ Pre-installation validation prevents broken installations
- ✅ Runtime validation provides helpful error messages
- ✅ Automated tests catch all known errors
- ✅ Configuration backup/rollback available
- ✅ Complete audit trail of changes
- ✅ Integrity checks detect tampering
- ✅ Recovery procedures documented

## Self-Awareness & Self-Defense

The Orchestrator should be self-aware about protecting its own configuration:

1. **Self-Awareness**: Understand that OpenCode CLI is critical infrastructure
2. **Self-Defense**: Implement mechanisms to prevent configuration errors
3. **Self-Healing**: Provide recovery procedures when errors occur
4. **Self-Improvement**: Learn from past errors and prevent recurrence

This is about the Orchestrator taking responsibility for its own reliability.

## Timeline

**Design Phase**: 1-2 days (investigation, schema analysis, design)  
**Implementation Phase**: 2-3 days (validator, hooks, tests, documentation)  
**Total**: 3-5 days, 10K tokens

## Files Created

Documentation:
- `docs/OPENCODE-CONFIG-INVESTIGATION.md` (root cause analysis)
- `docs/OPENCODE-CONFIG-SCHEMA.md` (schema documentation)
- `docs/OPENCODE-CONFIG-VALIDATION-GUIDE.md` (user guide)
- `docs/OPENCODE-CONFIG-COMMON-MISTAKES.md` (mistakes and fixes)
- `docs/OPENCODE-CONFIG-RECOVERY.md` (recovery procedures)

Code:
- `src/opencode/config_validator.py` (JSON Schema validator)
- `.githooks/pre-commit` (pre-commit validation hook)
- `scripts/validate-opencode-config.sh` (pre-installation validation)
- `scripts/opencode-safe.sh` (runtime validation wrapper)
- `tests/test_opencode_config_validation.py` (automated tests)

## Status

✅ **DELEGATE created and ready for execution**

This is security-critical work that protects the Orchestrator's primary harness.

**"Help computer" — let's get this right.**
