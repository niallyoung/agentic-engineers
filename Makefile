.PHONY: help install-copilot install-claude install-all \
        uninstall-copilot uninstall-claude uninstall-all status \
        verify clean render-claude render-copilot render-all

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Install targets (platform-specific):"
	@echo "  install-claude      Install rendered agents → ~/.claude/"
	@echo "  install-copilot     Install rendered agents → ~/.copilot/"
	@echo "  install-all         Both"
	@echo ""
	@echo "Uninstall targets:"
	@echo "  uninstall-claude    Remove from ~/.claude/  (managed only)"
	@echo "  uninstall-copilot   Remove from ~/.copilot/  (managed only)"
	@echo "  uninstall-all       Both"
	@echo ""
	@echo "Render targets (generate dist/ from source):"
	@echo "  render-claude       Generate dist/claude/ (provider-specific)"
	@echo "  render-copilot      Generate dist/copilot/ (provider-specific)"
	@echo "  render-all          Both"
	@echo ""
	@echo "Diagnostic:"
	@echo "  status              Check installation status"
	@echo "  verify              Verify framework structure"
	@echo "  clean               Remove both installations"

install-all: install-claude install-copilot ## Install to both ~/.claude/ and ~/.copilot/

install-copilot:
	@bash $(REPO_ROOT)/scripts/install-copilot.sh install

install-claude:
	@bash $(REPO_ROOT)/scripts/install-claude.sh install

uninstall-all: uninstall-claude uninstall-copilot ## Uninstall from both locations

uninstall-copilot:
	@bash $(REPO_ROOT)/scripts/install-copilot.sh --uninstall

uninstall-claude:
	@bash $(REPO_ROOT)/scripts/install-claude.sh --uninstall

status: status-claude status-copilot

status-claude:
	@echo "=== Claude Installation ===" && \
	bash $(REPO_ROOT)/scripts/install-claude.sh --status 2>/dev/null || echo "❌ Not installed"

status-copilot:
	@echo "=== Copilot Installation ===" && \
	bash $(REPO_ROOT)/scripts/install-copilot.sh --status 2>/dev/null || echo "❌ Not installed"

render-all: render-claude render-copilot

render-claude:
	@echo "📦 Rendering agents for Claude → dist/claude/"
	@mkdir -p $(REPO_ROOT)/dist/claude/roles
	@cp $(REPO_ROOT)/orchestration/agents/*.md $(REPO_ROOT)/dist/claude/roles/ 2>/dev/null || true
	@echo "✅ Done"

render-copilot:
	@echo "📦 Rendering agents for Copilot → dist/copilot/"
	@mkdir -p $(REPO_ROOT)/dist/copilot/roles
	@cp $(REPO_ROOT)/orchestration/agents/*.md $(REPO_ROOT)/dist/copilot/roles/ 2>/dev/null || true
	@echo "✅ Done"

verify:
	@echo "🔍 Verifying framework structure..."
	@test -d "$(REPO_ROOT)/orchestration/agents" || (echo "❌ orchestration/agents/ missing" && exit 1)
	@test -d "$(REPO_ROOT)/dist/claude" || (echo "❌ dist/claude/ missing (run: make render-claude)" && exit 1)
	@test -d "$(REPO_ROOT)/dist/copilot" || (echo "❌ dist/copilot/ missing (run: make render-copilot)" && exit 1)
	@test -f "$(REPO_ROOT)/scripts/install-claude.sh" || (echo "❌ scripts/install-claude.sh missing" && exit 1)
	@test -f "$(REPO_ROOT)/scripts/install-copilot.sh" || (echo "❌ scripts/install-copilot.sh missing" && exit 1)
	@echo "✅ Framework structure verified"

clean: uninstall-all
	@echo "✅ Cleanup complete"

.DEFAULT_GOAL := help
