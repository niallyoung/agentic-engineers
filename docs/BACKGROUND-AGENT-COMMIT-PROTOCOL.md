# Background Agent File Commitment Protocol

**Rule:** Background agents that create files (e.g. `skill-creator`, `agent-creator`) MUST
explicitly stage and commit them before returning HANDBACK — proving no orphaned files, no lost
tests, and giving the Orchestrator a commit SHA to validate against. Without this, an agent that
creates files and runs tests locally but never commits leaves them untracked in the working
tree — invisible to git history, easily lost.

---

## Steps (in order)

1. **Verify files exist** — `git status --short`; every new file shows as `??`.
2. **Run tests** (if applicable) — `pytest <path> -v`; do not proceed until green.
3. **Stage** — `git add <path>`; re-check `git status --short` shows `A` for every file.
4. **Commit** — one commit, message lists every file created.
5. **Capture the SHA** — `COMMIT_SHA=$(git rev-parse HEAD)`; needed for the HANDBACK.
6. **Validate** — `git show HEAD --stat` lists every file. If one is missing: `git add` it, then
   `git commit --amend`, then re-check.

---

## HANDBACK Requirements

Every HANDBACK from a file-creating background agent MUST include:

```yaml
deliverables: [list of every file created]
committed_files: [same list — proves each one reached the commit]
commit_sha: "<full SHA from step 5>"
tests: { passed: N, failed: 0, coverage: NN.N, framework: pytest }
metrics: { quality: 0.0-1.0, tokens: N, cost: 0.0, duration_seconds: N }  # canonical schema: src/AGENTS.md
```

**Orchestrator validation on receipt:** `git cat-file -t <commit_sha>` must return `commit`, and
`git show <commit_sha> --stat` must list every `committed_files` entry. Any missing file →
reject the HANDBACK.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `.pyc` staged | `git reset HEAD <path>/__pycache__/`; add `**/__pycache__/` to `.gitignore`; re-commit |
| Bytecode newer than source | `rm -rf __pycache__`; recompile; re-add source; re-commit |
| Test file missing from disk | Recreate it, `git add`, `git commit --amend` |
| File staged but missing from the commit | `git add <file>`; `git commit --amend`; re-verify with `git show HEAD --stat` |

---

## Checklist Before Returning HANDBACK

- [ ] All files created and staged (`git status --short` shows none as `??`)
- [ ] Tests pass
- [ ] Commit created and includes every file (`git show HEAD --stat`)
- [ ] `commit_sha` and `committed_files` present in the HANDBACK

---

## Worked Example

```bash
mkdir -p src/skills/new-skill/scripts
# ... create SKILL.md, scripts/main.py, scripts/test.py ...
pytest src/skills/new-skill/scripts/test.py -v      # green
git add src/skills/new-skill/
git status --short                                  # all A, none ??
git commit -m "Create: new-skill skill

Files:
- src/skills/new-skill/SKILL.md
- src/skills/new-skill/scripts/main.py
- src/skills/new-skill/scripts/test.py

All tests passing."
COMMIT_SHA=$(git rev-parse HEAD)
git show HEAD --stat                                # confirms all 3 files present
```

---

## Key Policies

1. Commit before HANDBACK — never deferred.
2. Orchestrator verifies the commit SHA before accepting the HANDBACK.
3. `.pyc` files are never staged; `.py` source is always committed.
4. HANDBACK must include `commit_sha` as proof of commitment.

---

## Related Documents

- `.githooks/pre-commit` — validates source integrity
- `docs/CONTRIBUTING/README.md` — general contribution guidelines
- `tests/conftest.py` — pytest fixtures (includes test source audit)
- `.github/workflows/ci.yml` — CI source-integrity checks (orphaned-bytecode gate, folded in
  from the former `validate-sources.yml` in the 2026-08-13 infra consolidation)
