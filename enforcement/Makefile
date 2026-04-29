# Enforcement infrastructure Makefile — install/uninstall global Copilot CLI enforcement
# Copies hooks, scripts, instructions, and shared Makefile into ~/.github/

SHELL := /bin/bash
.DEFAULT_GOAL := help

GLOBAL := $(HOME)/.github

.PHONY: help install uninstall status

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Copy hooks, scripts, instructions, and shared Makefile into ~/.github/
	@echo "📦 Installing global enforcement infra (copy mode)..."
	@mkdir -p $(GLOBAL)/hooks $(GLOBAL)/scripts
	@# Remove any existing symlinks from prior installs
	@find $(GLOBAL)/hooks $(GLOBAL)/scripts -maxdepth 1 -type l -delete 2>/dev/null || true
	@for f in copilot-instructions.md shared.mk; do \
		if [ -L "$(GLOBAL)/$$f" ]; then rm -f "$(GLOBAL)/$$f"; fi; \
	done
	@# Hooks
	@install -m 0644 $(CURDIR)/hooks/guard.json $(GLOBAL)/hooks/guard.json
	@install -m 0644 $(CURDIR)/hooks/session-init.json $(GLOBAL)/hooks/session-init.json
	@echo "  ✓ hooks → ~/.github/hooks/"
	@# Scripts (executable)
	@install -m 0755 $(CURDIR)/scripts/copilot-guard.sh $(GLOBAL)/scripts/copilot-guard.sh
	@install -m 0755 $(CURDIR)/scripts/copilot-session-init.sh $(GLOBAL)/scripts/copilot-session-init.sh
	@echo "  ✓ scripts → ~/.github/scripts/"
	@# Instructions
	@install -m 0644 $(CURDIR)/instructions/copilot-instructions.md $(GLOBAL)/copilot-instructions.md
	@echo "  ✓ instructions → ~/.github/copilot-instructions.md"
	@# Shared Makefile
	@install -m 0644 $(CURDIR)/shared.mk $(GLOBAL)/shared.mk
	@echo "  ✓ shared.mk → ~/.github/shared.mk"
	@echo "✅ Global enforcement installed (files copied, not linked)"

uninstall: ## Remove installed files from ~/.github/
	@echo "🧹 Removing global enforcement..."
	@rm -f $(GLOBAL)/hooks/guard.json $(GLOBAL)/hooks/session-init.json
	@rm -f $(GLOBAL)/scripts/copilot-guard.sh $(GLOBAL)/scripts/copilot-session-init.sh
	@rm -f $(GLOBAL)/copilot-instructions.md $(GLOBAL)/shared.mk
	@echo "✅ Uninstalled"

status: ## Show installed files and whether they match source
	@echo "=== Global Enforcement Status ==="
	@for pair in \
		"$(GLOBAL)/hooks/guard.json:$(CURDIR)/hooks/guard.json" \
		"$(GLOBAL)/hooks/session-init.json:$(CURDIR)/hooks/session-init.json" \
		"$(GLOBAL)/scripts/copilot-guard.sh:$(CURDIR)/scripts/copilot-guard.sh" \
		"$(GLOBAL)/scripts/copilot-session-init.sh:$(CURDIR)/scripts/copilot-session-init.sh" \
		"$(GLOBAL)/copilot-instructions.md:$(CURDIR)/instructions/copilot-instructions.md" \
		"$(GLOBAL)/shared.mk:$(CURDIR)/shared.mk"; do \
		dst=$${pair%%:*}; src=$${pair##*:}; \
		if [ -L "$$dst" ]; then \
			echo "  ⚠️  $$dst (still a symlink — re-run install)"; \
		elif [ -f "$$dst" ]; then \
			if cmp -s "$$src" "$$dst"; then \
				echo "  ✅ $$dst (in sync)"; \
			else \
				echo "  🔄 $$dst (out of date — re-run install)"; \
			fi; \
		else \
			echo "  ❌ $$dst (missing)"; \
		fi; \
	done
