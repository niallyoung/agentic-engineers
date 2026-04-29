# renderer Makefile — render agentic-engineers' canonical specs into per-tool target formats
#
# Targets:
#   install-github    Copy hooks/scripts/instructions into ~/.github/   (legacy compat layout)
#   install-copilot   Render skills into ~/.copilot/skills/
#   install-claude    Render agents → ~/.claude/agents/, skills → ~/.claude/skills/
#   install-all       All three
#   uninstall-*       Per-target uninstall
#   status            Drift report across all targets

SHELL := /bin/bash
.DEFAULT_GOAL := help

REPO_ROOT := $(shell cd $(CURDIR)/.. && pwd)
GITHUB := $(HOME)/.github
COPILOT := $(HOME)/.copilot
CLAUDE := $(HOME)/.claude

.PHONY: help install-all install-github install-copilot install-claude \
        uninstall-github uninstall-copilot uninstall-claude uninstall-all status

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-all: install-github install-copilot install-claude ## Install to all three targets

# -----------------------------------------------------------------------------
# Target 1: ~/.github/  (legacy compat layout — currently no real consumer,
# kept for future enforcement runtime). Files copied, not symlinked.
# -----------------------------------------------------------------------------
install-github: ## Copy hooks/scripts/instructions into ~/.github/
	@echo "📦 Installing → ~/.github/ (legacy compat)..."
	@mkdir -p $(GITHUB)/hooks $(GITHUB)/scripts
	@find $(GITHUB)/hooks $(GITHUB)/scripts -maxdepth 1 -type l -delete 2>/dev/null || true
	@for f in copilot-instructions.md shared.mk; do \
		if [ -L "$(GITHUB)/$$f" ]; then rm -f "$(GITHUB)/$$f"; fi; \
	done
	@install -m 0644 $(CURDIR)/hooks/guard.json $(GITHUB)/hooks/guard.json
	@install -m 0644 $(CURDIR)/hooks/session-init.json $(GITHUB)/hooks/session-init.json
	@install -m 0755 $(CURDIR)/scripts/copilot-guard.sh $(GITHUB)/scripts/copilot-guard.sh
	@install -m 0755 $(CURDIR)/scripts/copilot-session-init.sh $(GITHUB)/scripts/copilot-session-init.sh
	@install -m 0644 $(CURDIR)/instructions/copilot-instructions.md $(GITHUB)/copilot-instructions.md
	@install -m 0644 $(CURDIR)/shared.mk $(GITHUB)/shared.mk
	@echo "✅ ~/.github/ installed"

uninstall-github: ## Remove agentic-engineers files from ~/.github/
	@rm -f $(GITHUB)/hooks/guard.json $(GITHUB)/hooks/session-init.json
	@rm -f $(GITHUB)/scripts/copilot-guard.sh $(GITHUB)/scripts/copilot-session-init.sh
	@rm -f $(GITHUB)/copilot-instructions.md $(GITHUB)/shared.mk
	@echo "✅ ~/.github/ uninstalled"

# -----------------------------------------------------------------------------
# Target 2: ~/.copilot/  (GitHub Copilot CLI — real consumer)
# -----------------------------------------------------------------------------
install-copilot: ## Render skills into ~/.copilot/skills/
	@$(CURDIR)/scripts/render-copilot.sh "$(REPO_ROOT)" "$(COPILOT)"

uninstall-copilot: ## Remove agentic-engine{service-name} skills from ~/.copilot/skills/
	@$(CURDIR)/scripts/render-copilot.sh "$(REPO_ROOT)" "$(COPILOT)" --uninstall

# -----------------------------------------------------------------------------
# Target 3: ~/.claude/  (Claude Code — real consumer)
# -----------------------------------------------------------------------------
install-claude: ## Render agents → ~/.claude/agents/, skills → ~/.claude/skills/
	@$(CURDIR)/scripts/render-claude.sh "$(REPO_ROOT)" "$(CLAUDE)"

uninstall-claude: ## Remove agentic-engine{service-name} files from ~/.claude/
	@$(CURDIR)/scripts/render-claude.sh "$(REPO_ROOT)" "$(CLAUDE)" --uninstall

uninstall-all: uninstall-github uninstall-copilot uninstall-claude ## Uninstall from all targets

# -----------------------------------------------------------------------------
# Status
# -----------------------------------------------------------------------------
status: ## Drift report across all targets
	@echo "=== ~/.github/ (legacy compat) ==="
	@for pair in \
		"$(GITHUB)/hooks/guard.json:$(CURDIR)/hooks/guard.json" \
		"$(GITHUB)/hooks/session-init.json:$(CURDIR)/hooks/session-init.json" \
		"$(GITHUB)/scripts/copilot-guard.sh:$(CURDIR)/scripts/copilot-guard.sh" \
		"$(GITHUB)/scripts/copilot-session-init.sh:$(CURDIR)/scripts/copilot-session-init.sh" \
		"$(GITHUB)/copilot-instructions.md:$(CURDIR)/instructions/copilot-instructions.md" \
		"$(GITHUB)/shared.mk:$(CURDIR)/shared.mk"; do \
		dst=$${pair%%:*}; src=$${pair##*:}; \
		if [ -L "$$dst" ]; then echo "  ⚠️  $$dst (symlink — re-run)"; \
		elif [ -f "$$dst" ]; then \
			if cmp -s "$$src" "$$dst"; then echo "  ✅ $$dst"; \
			else echo "  🔄 $$dst (out of date)"; fi; \
		else echo "  ❌ $$dst (missing)"; fi; \
	done
	@echo ""
	@echo "=== ~/.copilot/skills/ ==="
	@$(CURDIR)/scripts/render-copilot.sh "$(REPO_ROOT)" "$(COPILOT)" --status || true
	@echo ""
	@echo "=== ~/.claude/{agents,skills}/ ==="
	@$(CURDIR)/scripts/render-claude.sh "$(REPO_ROOT)" "$(CLAUDE)" --status || true
