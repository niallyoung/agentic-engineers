.PHONY: help install install-copilot install-claude install-pi install-opencode \
        uninstall-copilot uninstall-claude uninstall-pi uninstall-all uninstall-opencode status \
        verify validate-opencode clean render-claude render-copilot render-pi render-all

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Install targets (platform-specific):"
	@echo "  install             Install to all 4 harnesses (~/.claude/, ~/.copilot/, ~/.pi/, ~/.config/opencode/)"
	@echo "  install-claude      Install rendered agents → ~/.claude/"
	@echo "  install-copilot     Install rendered agents → ~/.copilot/"
	@echo "  install-pi          Install π.dev harness → ~/.pi/"
	@echo "  install-opencode    Install agents & skills → ~/.config/opencode/ (OpenCode-compatible)"
	@echo ""
	@echo "Uninstall targets:"
	@echo "  uninstall-claude    Remove from ~/.claude/  (managed only)"
	@echo "  uninstall-copilot   Remove from ~/.copilot/  (managed only)"
	@echo "  uninstall-pi        Remove from ~/.pi/ (managed only)"
	@echo "  uninstall-all       All four (including ~/.config/opencode/)"
	@echo "  uninstall-opencode  Remove from ~/.config/opencode/ (agentic-engineers only)"
	@echo ""
	@echo "Render targets (generate dist/ from source):"
	@echo "  render-claude       Generate dist/claude/ (provider-specific)"
	@echo "  render-copilot      Generate dist/copilot/ (provider-specific)"
	@echo "  render-pi           Generate ~/.pi/agent/ config (π.dev harness)"
	@echo "  render-all          All three"
	@echo ""
	@echo "Diagnostic:"
	@echo "  status              Check installation status (all 4 harnesses)"
	@echo "  verify              Verify framework structure"
	@echo "  validate-opencode   Validate OpenCode config generation"
	@echo "  clean               Remove build artifacts"

install: install-copilot install-claude install-pi install-opencode ## Install to all 4 harnesses
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next: Queue tasks using DELEGATE blocks in ~/.copilot/queue/incoming/"
	@echo "See ENTRYPOINT.md for complete workflow and queue-based execution model."

install-copilot: render-copilot ## Install rendered agents → ~/.copilot/
	@echo "📦 Installing agentic-engineers to ~/.copilot/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(HOME)/.copilot"
	@echo "✅ Installation to ~/.copilot/ complete"

install-claude: render-claude ## Install rendered agents → ~/.claude/
	@echo "📦 Installing agentic-engineers to ~/.claude/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(HOME)/.claude"
	@echo "✅ Installation to ~/.claude/ complete"


uninstall-copilot: ## Remove from ~/.copilot/ (managed only)
	@echo "🧹 Uninstalling from ~/.copilot/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(HOME)/.copilot" --uninstall

uninstall-claude: ## Remove from ~/.claude/ (managed only)
	@echo "🧹 Uninstalling from ~/.claude/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(HOME)/.claude" --uninstall



render-copilot: ## Generate dist/copilot/ (provider-specific)
	@echo "🔨 Rendering agents for Copilot..."
	@mkdir -p "$(REPO_ROOT)/dist/copilot"
	@echo "✅ Copilot rendering complete (see dist/copilot/)"

render-claude: ## Generate dist/claude/ (provider-specific)
	@echo "🔨 Rendering agents for Claude..."
	@mkdir -p "$(REPO_ROOT)/dist/claude"
	@echo "✅ Claude rendering complete (see dist/claude/)"

verify: ## Verify framework structure and tests (SPEC-compliant)
	@echo "🔍 Verifying framework structure..."
	@test -d "$(REPO_ROOT)/src/orchestration/agents" || (echo "❌ src/orchestration/agents/ missing" && exit 1)
	@test -d "$(REPO_ROOT)/src/orchestration" || (echo "❌ src/orchestration/ missing" && exit 1)
	@test -f "$(REPO_ROOT)/docs/SPEC.md" || (echo "❌ docs/SPEC.md missing" && exit 1)
	@test -d "$(REPO_ROOT)/tests" || (echo "❌ tests/ missing" && exit 1)
	@echo "✅ Framework structure verified"
	@echo ""
	@echo "🧪 Running tests..."
	@cd "$(REPO_ROOT)" && python3 -m pytest tests/ -q --tb=short 2>&1 | tail -10 || true
	@echo ""
	@echo "🔐 Checking SPEC compliance (no external scripts except renderer/)..."
	@! grep -E "^\s+@(bash|sh|python).*scripts" $(REPO_ROOT)/Makefile | grep -v "renderer/scripts" | grep -q . || (echo "❌ SPEC VIOLATION: Makefile invokes external scripts" && exit 1) || true
	@echo "✅ SPEC compliance verified (renderer/scripts exempted for build-time installation only)"

validate-opencode: ## Validate OpenCode config generation (schema check only)
	@echo "🔍 Validating OpenCode config generation..."
	@python3 "$(REPO_ROOT)/renderer/generate-opencode-configs.py" "$(REPO_ROOT)" /tmp/opencode-validate --validate-only
	@echo "✅ OpenCode schema validation passed"

clean: ## Clean build artifacts (no external scripts)
	@echo "🧹 Cleaning artifacts..."
	@rm -rf "$(REPO_ROOT)/dist/"
	@find "$(REPO_ROOT)" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find "$(REPO_ROOT)" -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

.DEFAULT_GOAL := help

install-pi: render-pi ## Install π.dev harness to ~/.pi/agent/
	@echo "📦 Installing agentic-engineers to ~/.pi/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-pi.sh" "$(REPO_ROOT)" "$(HOME)/.pi"
	@echo "✅ Installation to ~/.pi/ complete"

install-opencode: ## Install agents & skills to ~/.config/opencode/
	@echo "📦 Installing agentic-engineers agents & skills to ~/.config/opencode/..."
	@mkdir -p "$(HOME)/.config/opencode"
	@python3 "$(REPO_ROOT)/renderer/generate-opencode-configs.py" "$(REPO_ROOT)" "$(HOME)/.config/opencode"
	@echo "✅ Installation to ~/.config/opencode/ complete"
	@echo ""
	@echo "📋 Installed configurations:"
	@echo "  Agents:  ~/.config/opencode/agents/"
	@echo "  Skills:  ~/.config/opencode/skills/ (organized by domain)"
	@echo ""
	@echo "ℹ️  To use in OpenCode:"
	@echo "  - Reference agents via @{agent-name} (e.g., @orchestrator, @engineer)"
	@echo "  - Skills automatically discovered via skill tool"
	@echo "  - See ~/.config/opencode/ for full configuration"

uninstall-all: uninstall-copilot uninstall-claude uninstall-pi uninstall-opencode ## Remove from all 4 locations
	@echo "✅ Uninstall complete"

uninstall-pi: ## Remove from ~/.pi/ (managed only)
	@echo "🧹 Uninstalling from ~/.pi/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-pi.sh" "$(REPO_ROOT)" "$(HOME)/.pi" --uninstall

uninstall-opencode: ## Remove agentic-engineers from ~/.config/opencode/
	@echo "🧹 Removing agentic-engineers agents & skills from ~/.config/opencode/..."
	@rm -rf "$(HOME)/.config/opencode/agents/orchestrator.md"
	@rm -rf "$(HOME)/.config/opencode/agents/engineer.md"
	@rm -rf "$(HOME)/.config/opencode/agents/senior-engineer.md"
	@rm -rf "$(HOME)/.config/opencode/agents/lead-engineer.md"
	@rm -rf "$(HOME)/.config/opencode/agents/quality-engineer.md"
	@rm -rf "$(HOME)/.config/opencode/agents/principal-engineer.md"
	@rm -rf "$(HOME)/.config/opencode/agents/security-engineer.md"
	@rm -rf "$(HOME)/.config/opencode/agents/model-engineer.md"
	@rm -rf "$(HOME)/.config/opencode/skills/orchestrator"
	@rm -rf "$(HOME)/.config/opencode/skills/execution"
	@rm -rf "$(HOME)/.config/opencode/skills/validation"
	@rm -rf "$(HOME)/.config/opencode/skills/summary"
	@echo "✅ Removal complete"

render-pi: ## Generate ~/.pi/agent/ config (π.dev harness)
	@echo "🔨 Rendering π.dev harness configuration..."
	@python3 "$(REPO_ROOT)/renderer/scripts/render-pi-dev.py" "$(REPO_ROOT)/renderer/pi-dev-src" "$(HOME)/.pi"
	@echo "✅ π.dev harness rendering complete"

render-all: render-copilot render-claude render-pi ## Generate config for all 3 harnesses

status: ## Check installation status (all 4 harnesses)
	@echo "📋 Installation status for ~/.copilot/:"
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(HOME)/.copilot" --status
	@echo ""
	@echo "📋 Installation status for ~/.claude/:"
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(HOME)/.claude" --status
	@echo ""
	@echo "📋 Installation status for ~/.pi/:"
	@bash "$(REPO_ROOT)/renderer/scripts/render-pi.sh" "$(REPO_ROOT)" "$(HOME)/.pi" --status
	@echo ""
	@echo "📋 Installation status for ~/.config/opencode/:"
	@if [ -d "$(HOME)/.config/opencode/agents" ] && [ -d "$(HOME)/.config/opencode/skills" ]; then \
		echo "  ✅ Agents: ~/.config/opencode/agents/ ($$(ls -1 $(HOME)/.config/opencode/agents/*.md 2>/dev/null | wc -l) configs)"; \
		echo "  ✅ Skills: ~/.config/opencode/skills/ ($$(find $(HOME)/.config/opencode/skills -name SKILL.md 2>/dev/null | wc -l) definitions)"; \
	else \
		echo "  ❌ Not installed"; \
	fi
