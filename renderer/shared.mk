# Makefile.shared — include from any project Makefile
# Usage: add `include ~/.github/Makefile.shared` at top of project Makefile
#
# Provides: install-hooks, pre-commit, pre-push (git hook gates)
# Projects define their own: lint, check, slides, build, test, etc.

.PHONY: install-hooks pre-commit pre-push

# ── Git hook installation ───────────────────────────────────────────

install-hooks: ## Install git hooks that delegate to make targets
	@echo "🔗 Installing git hooks..."
	@mkdir -p .git/hooks
	@printf '#!/bin/sh\nexec make pre-commit\n' > .git/hooks/pre-commit
	@printf '#!/bin/sh\nexec make pre-push\n'   > .git/hooks/pre-push
	@chmod +x .git/hooks/pre-commit .git/hooks/pre-push
	@echo "  ✓ pre-commit → make pre-commit"
	@echo "  ✓ pre-push   → make pre-push"
	@echo "✅ Git hooks installed"

# ── Git hook gates (override in project Makefile if needed) ─────────

pre-commit: lint check ## Pre-commit gate: lint + check

pre-push: lint check ## Pre-push gate: lint + check + build (if exists)
