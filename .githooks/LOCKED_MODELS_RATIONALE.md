# Model Lock Rationale

This note explains *why* model selection is a positive, auditable choice. It does not list
the current models: `config/models.yaml` is the source of truth and
[`docs/MODELS.md`](../docs/MODELS.md) is the generated, always-current view of which model
each role pins, the fallbacks, floors and pin history.

## Philosophy: Positive Enforcement

We use **positive enforcement** (explicit pins) instead of **negative enforcement**
(forbidden patterns).

**Positive ("we chose these models"):**
- Clear intent: the registry is the statement of approved models.
- User choice preserved: a user-chosen Claude Code model is never overwritten by the installer.
- Auditable: a pin change is an explicit registry edit with a `pin_history` entry and an approver.
- Simpler code: one registry, validators check shape and consistency instead of a version list.

**Negative ("GPT is forbidden"):**
- Defensive posture that reads as restricting choice.
- Hard to maintain: rejection patterns must change whenever a new model appears.
- Less clear intent: "forbidden" implies restriction rather than strategic choice.

## Model Switch Process

Models are pinned by explicit choice. The authoritative procedure is the **Model Pin
Change** section of [`docs/SPEC.md`](../docs/SPEC.md). In outline:

### 1. Request and evaluation
Contact the Orchestrator with the role, the requested model, the reason and the expected
impact (cost, quality, latency). The Orchestrator weighs cost delta, capability gain,
consistency with other roles and timing, then approves, defers or denies.

### 2. Implementation (if approved)
1. Edit `config/models.yaml`: add the `models.<id>` block if the model is new and change
   `roles.<role>.model` (respecting the family `min_pin` floor).
2. Append one line at the end of the `pin_history` list (date, role, from, to, approval).
3. Run `make models-sync` (`python3 scripts/models.py sync`) to regenerate every derived
   file, including `.githooks/LOCKED_MODELS.sh`. Never hand-edit generated files.
4. Run `make test`, then commit with a `Model-Pin-Approved-By: <approver>` trailer. The
   `commit-msg` hook rejects a pin change without it; adding an unassigned model needs no trailer.
5. Re-run the installer; a managed Claude Code `settings.json` value migrates, a
   user-chosen value is left alone.

## Enforcement Mechanism

- `.githooks/LOCKED_MODELS.sh` is a **generated shim** from `config/models.yaml`. It exposes
  `LOCKED_MODELS`, `AGENT_MODEL_ASSIGNMENTS` and the helpers `is_model_locked`,
  `get_agent_locked_model`, `show_locked_models`, `show_agent_assignments`.
- `.githooks/pre-commit` validates staged agent files against the registry and rejects stale
  generated targets (`python3 scripts/models.py check` and `sync --check`).
- `.githooks/commit-msg` requires the `Model-Pin-Approved-By` trailer on a role pin change.
- Hooks and scripts that need the model set may source the shim:

```bash
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOKS_DIR/LOCKED_MODELS.sh"
is_model_locked "$model" && echo approved
show_agent_assignments
```

The interactive helpers have no caller in the repo other than `is_model_locked`; they are
the documented sourcing API and are kept deliberately.

## Governance

- **Approval authority**: Orchestrator (with input from role leads).
- **Appeal**: if denied, request review in the next budget cycle.
- **Transparency**: every pin change carries a `pin_history` entry and an approver trailer.
- **Audit trail**: git history shows who, what, when, why.

## See Also

- [config/models.yaml](../config/models.yaml) - source of truth
- [docs/MODELS.md](../docs/MODELS.md) - generated model and pin tables
- [LOCKED_MODELS.sh](./LOCKED_MODELS.sh) - generated shim
- [SPEC.md](../docs/SPEC.md) - Model Pin Change process and invariants I1-I6
- [CONTRIBUTING](../docs/CONTRIBUTING/README.md) - contributor guide
