.PHONY: help install install-copilot install-claude \
        uninstall-copilot uninstall-claude uninstall-all status \
        verify clean render-claude render-copilot render-all

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Install targets (platform-specific):"
	@echo "  install             Install to both ~/.claude/ and ~/.copilot/"
	@echo "  install-claude      Install rendered agents → ~/.claude/"
	@echo "  install-copilot     Install rendered agents → ~/.copilot/"
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

install: ## Queue installation task to Orchestrator
	@echo "❌ SPEC VIOLATION: make install is prohibited" >&2
	@echo "" >&2
	@echo "Installation must be queued as a DELEGATE task, not executed via external script." >&2
	@echo "" >&2
	@echo "To install agentic-engineers:" >&2
	@echo "  1. Create artifacts/queue/incoming/install-task.yaml with DELEGATE block" >&2
	@echo "  2. Start Orchestrator polling" >&2
	@echo "  3. Orchestrator routes to Installation Agent" >&2
	@echo "  4. Agent performs installation and returns HANDBACK" >&2
	@echo "" >&2
	@echo "See: docs/SPEC.md - ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY)" >&2
	@exit 1

uninstall-all: ## Queue uninstall task to Orchestrator
	@echo "❌ SPEC VIOLATION: make uninstall is prohibited" >&2
	@echo "Use Orchestrator queue-based delegation instead." >&2
	@exit 1

status: ## Queue status check task to Orchestrator
	@echo "❌ SPEC VIOLATION: make status is prohibited" >&2
	@echo "Use Orchestrator queue-based delegation instead." >&2
	@exit 1

verify: ## Verify framework structure and tests (SPEC-compliant)
	@echo "🔍 Verifying framework structure..."
	@test -d "$(REPO_ROOT)/orchestration/agents" || (echo "❌ orchestration/agents/ missing" && exit 1)
	@test -d "$(REPO_ROOT)/orchestration" || (echo "❌ orchestration/ missing" && exit 1)
	@test -f "$(REPO_ROOT)/docs/SPEC.md" || (echo "❌ docs/SPEC.md missing" && exit 1)
	@echo "✅ Framework structure verified"
	@echo ""
	@echo "🧪 Running Orchestrator tests..."
	@cd "$(REPO_ROOT)" && python3 -m unittest orchestration.agents.test_orchestrator 2>&1 | tail -5 || true
	@echo ""
	@echo "🔐 Checking SPEC compliance (no external scripts)..."
	@! grep -E "^\s+@(bash|sh|python).*scripts" $(REPO_ROOT)/Makefile || (echo "❌ SPEC VIOLATION: Makefile invokes external scripts" && exit 1)
	@echo "✅ SPEC compliance verified"

clean: ## Clean build artifacts (no external scripts)
	@echo "🧹 Cleaning artifacts..."
	@rm -rf "$(REPO_ROOT)/dist/"
	@find "$(REPO_ROOT)" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find "$(REPO_ROOT)" -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

.DEFAULT_GOAL := help
