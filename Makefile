.PHONY: help install install-docs install-github install-copilot install-claude install-all \
        uninstall-github uninstall-copilot uninstall-claude uninstall-all status \
        verify clean list-backups restore

INSTALL_PREFIX ?= $(HOME)/.agents
REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
SRC_DIR := $(REPO_ROOT)

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Install targets:"
	@echo "  install-docs        rsync framework into ~/.agents/agentic-engineers/  (doc surface)"
	@echo "  install-github      Render → ~/.github/  (legacy compat layout)"
	@echo "  install-copilot     Render skills → ~/.copilot/skills/"
	@echo "  install-claude      Render agents → ~/.claude/agents/, skills → ~/.claude/skills/"
	@echo "  install-all         All four"
	@echo "  install             Alias for install-docs (back-compat)"
	@echo ""
	@echo "Uninstall targets:"
	@echo "  uninstall-github    Remove agentic-engineers files from ~/.github/"
	@echo "  uninstall-copilot   Remove from ~/.copilot/skills/  (only managed)"
	@echo "  uninstall-claude    Remove from ~/.claude/  (only managed)"
	@echo "  uninstall-all       All three"
	@echo "  clean               Remove ~/.agents/agentic-engineers/  (doc surface)"
	@echo ""
	@echo "Diagnostic:"
	@echo "  verify              Verify framework structure"
	@echo "  status              Drift report across ~/.github/, ~/.copilot/, ~/.claude/"
	@echo "  list-backups        List ~/.agents/ backups"
	@echo "  restore             Restore ~/.agents/ from backup (BACKUP_DATE=YYYYMMDD_HHMMSS)"
	@echo ""
	@echo "Environment:"
	@echo "  INSTALL_PREFIX      ~/.agents/ install root (default: \$$HOME/.agents)"
	@echo "  BACKUP_DATE         Timestamp for restore"

install: install-docs ## Back-compat alias for install-docs

install-all: install-docs install-github install-copilot install-claude ## Install to all targets

install-docs: verify
	@$(MAKE) -s _install-docs-impl

# Renderer targets delegate to renderer/Makefile
install-github:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer install-github

install-copilot:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer install-copilot

install-claude:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer install-claude

uninstall-github:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer uninstall-github

uninstall-copilot:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer uninstall-copilot

uninstall-claude:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer uninstall-claude

uninstall-all: uninstall-github uninstall-copilot uninstall-claude

status:
	@$(MAKE) -s -C $(REPO_ROOT)/renderer status

_install-docs-impl:
	@echo "📦 Installing agentic-engineers framework → $(INSTALL_PREFIX)/agentic-engineers/"
	@INSTALL_DIR="$(INSTALL_PREFIX)/agentic-engineers"; \
	if [ -d "$$INSTALL_DIR" ]; then \
		echo "⚠️  Directory already exists: $$INSTALL_DIR"; \
		echo ""; \
		read -p "Overwrite? (y/n) " -n 1 -r; \
		echo ""; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			echo "❌ Installation cancelled"; \
			exit 1; \
		fi; \
		BACKUP_DATE=$$(date +%Y%m%d_%H%M%S); \
		BACKUP_DIR="$$INSTALL_DIR.$$BACKUP_DATE"; \
		echo "📦 Backing up to: $$BACKUP_DIR"; \
		mv "$$INSTALL_DIR" "$$BACKUP_DIR"; \
		echo "✅ Backup created"; \
	fi
	@mkdir -p "$(INSTALL_PREFIX)"
	@mkdir -p "$(INSTALL_PREFIX)/agentic-engineers"
	@echo "  Copying framework files..."
	@rsync -av --delete \
		--exclude='.git' \
		--exclude='.session-state' \
		--exclude='*.swp' \
		--exclude='.DS_Store' \
		"$(SRC_DIR)/" "$(INSTALL_PREFIX)/agentic-engineers/" >/dev/null
	@echo "✅ Installed to: $(INSTALL_PREFIX)/agentic-engineers/"
	@echo ""
	@echo "Integration instructions:"
	@echo "  1. Add to shell (e.g., ~/.zshrc or ~/.bashrc):"
	@echo "     source $(INSTALL_PREFIX)/agentic-engineers/setup/session-init.sh"
	@echo ""
	@echo "  2. Or run manually at session start:"
	@echo "     bash $(INSTALL_PREFIX)/agentic-engineers/setup/session-init.sh"
	@echo ""
	@echo "  3. Or invoke in Claude Code/Copilot:"
	@echo "     Reference: $(INSTALL_PREFIX)/agentic-engineers/SYSTEM.md"

verify:
	@echo "🔍 Verifying framework structure..."
	@test -d "$(SRC_DIR)/setup" || (echo "❌ setup/ directory missing" && exit 1)
	@test -d "$(SRC_DIR)/orchestration" || (echo "❌ orchestration/ directory missing" && exit 1)
	@test -d "$(SRC_DIR)/skills" || (echo "❌ skills/ directory missing" && exit 1)
	@test -f "$(SRC_DIR)/SYSTEM.md" || (echo "❌ SYSTEM.md missing" && exit 1)
	@test -f "$(SRC_DIR)/README.md" || (echo "❌ README.md missing" && exit 1)
	@test -f "$(SRC_DIR)/setup/session-init.sh" || (echo "❌ setup/session-init.sh missing" && exit 1)
	@echo "✅ Framework structure verified"

list-backups:
	@echo "📦 Available backups in $(INSTALL_PREFIX):"
	@ls -1d "$(INSTALL_PREFIX)"/agentic-engineers.* 2>/dev/null | awk -F/ '{print "  " $$NF}' || echo "  (no backups found)"

restore:
	@if [ -z "$(BACKUP_DATE)" ]; then \
		echo "❌ BACKUP_DATE not specified"; \
		echo ""; \
		echo "Usage: make restore BACKUP_DATE=YYYYMMDD_HHMMSS"; \
		echo ""; \
		echo "Example:"; \
		echo "  make list-backups        # See available dates"; \
		echo "  make restore BACKUP_DATE=20260425_190131"; \
		exit 1; \
	fi
	@BACKUP_DIR="$(INSTALL_PREFIX)/agentic-engineers.$(BACKUP_DATE)"; \
	CURRENT_DIR="$(INSTALL_PREFIX)/agentic-engineers"; \
	if [ ! -d "$$BACKUP_DIR" ]; then \
		echo "❌ Backup not found: $$BACKUP_DIR"; \
		exit 1; \
	fi
	@echo "🔄 Restoring from backup: $(BACKUP_DATE)"
	@BACKUP_DIR="$(INSTALL_PREFIX)/agentic-engineers.$(BACKUP_DATE)"; \
	CURRENT_DIR="$(INSTALL_PREFIX)/agentic-engineers"; \
	rm -rf "$$CURRENT_DIR" && \
	mv "$$BACKUP_DIR" "$$CURRENT_DIR" && \
	echo "✅ Restored to: $$CURRENT_DIR"

clean:
	@echo "🧹 Removing installed framework from $(INSTALL_PREFIX)..."
	@rm -rf "$(INSTALL_PREFIX)/agentic-engineers"
	@echo "✅ Cleanup complete"
	@echo ""
	@echo "Note: Backups are preserved. To remove all including backups:"
	@echo "  rm -rf $(INSTALL_PREFIX)/agentic-engineers*"

.DEFAULT_GOAL := help
