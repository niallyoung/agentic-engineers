# Enforcement infrastructure Makefile — install/uninstall global Copilot CLI enforcement
# Installs hooks, scripts, instructions, and shared Makefile into ~/.github/

SHELL := /bin/bash
.DEFAULT_GOAL := help

GLOBAL := $(HOME)/.github

.PHONY: help install uninstall status

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Symlink hooks, scripts, instructions, and shared Makefile into ~/.github/
	@echo "🔗 Installing global enforcement infra..."
	@mkdir -p $(GLOBAL)/hooks $(GLOBAL)/scripts
	@# Hooks
	@ln -sf $(CURDIR)/hooks/guard.json $(GLOBAL)/hooks/guard.json
	@ln -sf $(CURDIR)/hooks/session-init.json $(GLOBAL)/hooks/session-init.json
	@echo "  ✓ hooks → ~/.github/hooks/"
	@# Scripts
	@ln -sf $(CURDIR)/scripts/copilot-guard.sh $(GLOBAL)/scripts/copilot-guard.sh
	@ln -sf $(CURDIR)/scripts/copilot-session-init.sh $(GLOBAL)/scripts/copilot-session-init.sh
	@chmod +x $(CURDIR)/scripts/*.sh
	@echo "  ✓ scripts → ~/.github/scripts/"
	@# Instructions
	@ln -sf $(CURDIR)/instructions/copilot-instructions.md $(GLOBAL)/copilot-instructions.md
	@echo "  ✓ instructions → ~/.github/copilot-instructions.md"
	@# Shared Makefile
	@ln -sf $(CURDIR)/shared.mk $(GLOBAL)/shared.mk
	@echo "  ✓ shared.mk → ~/.github/shared.mk"
	@echo "✅ Global enforcement installed"

uninstall: ## Remove symlinks from ~/.github/
	@echo "🔓 Removing global enforcement..."
	@rm -f $(GLOBAL)/hooks/guard.json $(GLOBAL)/hooks/session-init.json
	@rm -f $(GLOBAL)/scripts/copilot-guard.sh $(GLOBAL)/scripts/copilot-session-init.sh
	@rm -f $(GLOBAL)/copilot-instructions.md $(GLOBAL)/shared.mk
	@echo "✅ Uninstalled"

status: ## Show what's currently linked
	@echo "=== Global Enforcement Status ==="
	@for f in $(GLOBAL)/hooks/guard.json $(GLOBAL)/hooks/session-init.json \
		$(GLOBAL)/scripts/copilot-guard.sh $(GLOBAL)/scripts/copilot-session-init.sh \
		$(GLOBAL)/copilot-instructions.md $(GLOBAL)/shared.mk; do \
		if [ -L "$$f" ]; then \
			echo "  ✅ $$f → $$(readlink $$f)"; \
		elif [ -f "$$f" ]; then \
			echo "  ⚠️  $$f (file, not symlink)"; \
		else \
			echo "  ❌ $$f (missing)"; \
		fi; \
	done
