# Migration Guide — Skills Consolidation (2026-06-06)

**Applies to:** agentic-engineers framework, Phase 3 Skills Consolidation
**Branch landed:** `unify/2026-06-05-consolidated-cleanup`
**Scope:** Technical migration only (skill renames, removals, and import-path
changes). User-facing communication and rollout are handled separately.

---

## TL;DR

Phase 3 standardized skill naming and merged duplicate validators. Four skills
changed identity:

| Old name | New name / status | Change type |
|----------|-------------------|-------------|
| `todo-maintenance` | `queue-todo-sync` | Rename |
| `opencode-feature-sync` | `harness-opencode-feature-sync` | Rename |
| `protocol-validation` | `protocol-validator` | Merge (single source of truth) |
| `voice-notify` | *(removed)* | Deletion |

If you reference any of these by name — in a `DELEGATE` block, a Python import,
a config registry, or documentation — update the reference per the sections
below. Behavior is otherwise unchanged: the renames preserve logic, and the
merge preserves the public validation API.

---

## Who Is Affected?

| You are affected if you… | Action required |
|--------------------------|-----------------|
| Invoke skills by name in `DELEGATE` blocks | Update skill names (renames) |
| `import` the protocol validator in Python | Update import path |
| Maintain a fork/registry listing skills | Update registry entries |
| Depend on `voice-notify` audio alerts | Adopt replacement (see §4) |
| Only use rendered harnesses without custom code | **No action** — `make install` re-renders correct names |

**Not affected:** Anyone consuming skills purely through a rendered harness
(`~/.claude/`, `~/.copilot/`, `~/.config/opencode/`) after a fresh
`make install`. The renderer emits the new names automatically.

---

## 1. `todo-maintenance` → `queue-todo-sync`

**Why:** Group queue-related skills under the `queue-*` prefix alongside
`queue-management` and `queue-query`.

**Risk:** 🟢 Low — pure rename, no logic change.

### Before

```yaml
# DELEGATE block
scope: Sync TODO.md with the active queue
target_skill: todo-maintenance
```

```bash
# Direct script invocation
python src/skills/todo-maintenance/scripts/sync_todo.py
```

### After

```yaml
# DELEGATE block
scope: Sync TODO.md with the active queue
target_skill: queue-todo-sync
```

```bash
# Direct script invocation (script filename unchanged)
python src/skills/queue-todo-sync/scripts/sync_todo.py
```

> The script file (`sync_todo.py`) and the OpenCode wrapper
> (`opencode-todo-sync`) keep their names; only the skill directory changed.

---

## 2. `opencode-feature-sync` → `harness-opencode-feature-sync`

**Why:** Apply the `harness-*` convention to harness-specific skills (matching
`harness-integration-tracker`), making it explicit that the skill targets the
OpenCode harness rather than the framework core.

**Risk:** 🟢 Low — pure rename, no logic change.

### Before

```yaml
target_skill: opencode-feature-sync
```

```bash
python src/skills/opencode-feature-sync/scripts/opencode_feature_sync.py
```

### After

```yaml
target_skill: harness-opencode-feature-sync
```

```bash
python src/skills/harness-opencode-feature-sync/scripts/opencode_feature_sync.py
```

> The implementation script (`opencode_feature_sync.py`) keeps its name; only
> the skill directory was prefixed.

---

## 3. `protocol-validation` merged into `protocol-validator`

**Why:** Two validators with overlapping responsibility created a maintenance
hazard and a latent import cycle. `protocol-validator` is now the **single
canonical source of truth** for DELEGATE/HANDBACK validation.

**Risk:** 🟡 Medium — affects Python import paths. The public API is preserved.

### Public API parity

Both the removed `protocol-validation` and the canonical `protocol-validator`
expose module-level helpers with identical signatures:

```python
validate_delegate(delegate: Dict[str, Any]) -> Tuple[bool, List[str]]
validate_handback(handback: Dict[str, Any]) -> Tuple[bool, List[str]]
```

`protocol-validator` additionally offers the richer `ProtocolValidator` class
and a `ValidationResult` object — prefer these for new code.

### Before

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src/skills/protocol-validation/scripts")))
from protocol_validation import validate_delegate, validate_handback

ok, errors = validate_delegate(delegate)
```

### After

```python
import sys
from pathlib import Path

# Canonical single source of truth
sys.path.insert(0, str(Path("src/skills/protocol-validator/scripts")))
from protocol_validator import validate_delegate, validate_handback

ok, errors = validate_delegate(delegate)

# Or, preferred for new code — the class-based API with a result object:
from protocol_validator import ProtocolValidator
result = ProtocolValidator().validate_delegate(delegate)  # -> ValidationResult
```

### Find call sites to update

```bash
# Any lingering reference to the removed module/skill in your code:
grep -rn "protocol-validation\|protocol_validation" . \
  --include="*.py" --include="*.yaml" --include="*.md" \
  | grep -v archive
# Expected in this repo: empty (all internal callers already migrated).
```

> **Cycle note:** the merge eliminated the previous
> `protocol-validator → core_protocol_validator → protocol-validation` chain.
> `queue-management`'s `core_protocol_validator.py` now imports directly from
> `protocol-validator`, with zero circular imports.

---

## 4. `voice-notify` removed entirely

**Why:** Simplification. Audio/TTS notifications were unused in practice and
added cross-platform complexity (macOS `say` / Linux `espeak`). Removed across
24+ files with zero remaining active references.

**Risk:** 🟡 Medium — only if you actively relied on audio alerts.

### Replacement strategy

Lifecycle status is already available through standard, more reliable channels:

| Previous use of `voice-notify` | Replacement |
|--------------------------------|-------------|
| Audible "task complete" alert | `HANDBACK` `status: success` in the queue; tail the queue/log |
| Audible failure/escalation alert | `HANDBACK` `status: failed` + structured logs |
| Ambient progress cues | Harness-native desktop notifications, or `tail -f` on the session log |

### Before

```yaml
# DELEGATE requesting an audio alert on completion
scope: Notify on orchestration completion
target_skill: voice-notify
context:
  event: completion
  voice: optimistic
```

### After

```text
No skill invocation required. Emit a HANDBACK with an explicit status and
rely on logging. If you want a local desktop ping, wire it in your own
post-run hook — it is no longer a framework concern.
```

If you must restore audio locally, see the deprecation record in
[docs/DEPRECATED-SKILLS.md](DEPRECATED-SKILLS.md) (voice-notify, 2026-06-06).

---

## Verification Checklist

Run these after migrating a downstream consumer:

```bash
# 1. No references to old names in your active (non-archive) sources
grep -rn "todo-maintenance\|opencode-feature-sync\|protocol-validation\|voice-notify" \
  src/ docs/ config/ --include="*.py" --include="*.yaml" --include="*.md" \
  | grep -v archive
#   (References that document the *rename itself* are expected and fine.)

# 2. Re-render harnesses with the new names
make install

# 3. Confirm rendered output uses new directory names
ls ~/.claude/skills/ | grep -E 'queue-todo-sync|harness-opencode-feature-sync|protocol-validator'

# 4. Run the test suite
python3 -m pytest tests/ -q
```

---

## Deprecation Timeline

- **2026-06-06** — New names land on `unify/2026-06-05-consolidated-cleanup`.
  Old skill directories deleted; no compatibility shims are provided.
- **Recommended sunset window:** 6 months for any external forks still
  referencing old names, after which old-name support should not be expected.

There are intentionally **no aliases** for the old names inside this repo — a
clean break keeps the "single source of truth" guarantee meaningful. Update
references rather than relying on fallbacks.

---

## See Also

- [docs/DEPRECATED-SKILLS.md](DEPRECATED-SKILLS.md) — full deprecation index
- [docs/guides/ARCHITECTURE-CONSOLIDATION.md](guides/ARCHITECTURE-CONSOLIDATION.md) — why and how consolidation was done
- [docs/SKILLS.md](SKILLS.md) — current skill registry (new names)
- `SKILLS-CONSOLIDATION-PLAN-2026-06-06.md` (repo root) — the original execution plan
