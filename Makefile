.PHONY: help install verify clean

INSTALL_PREFIX ?= $(HOME)/.agents
REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
SRC_DIR := $(REPO_ROOT)

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Targets:"
	@echo "  make install       Install framework to ~/.agents/agentic-engineers/"
	@echo "  make verify        Verify installation integrity"
	@echo "  make clean         Remove installed files from ~/.agents/"
	@echo ""
	@echo "Environment:"
	@echo "  INSTALL_PREFIX     Installation root (default: ~/.agents)"

install: verify
	@echo "📦 Installing agentic-engineers framework..."
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

clean:
	@echo "🧹 Removing installed framework from $(INSTALL_PREFIX)..."
	@rm -rf "$(INSTALL_PREFIX)/agentic-engineers"
	@echo "✅ Cleanup complete"

.DEFAULT_GOAL := help
