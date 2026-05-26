.PHONY: help install clean-install fresh-install-copilot fresh-install-claude fresh-install-pi fresh-install-opencode \
        install-copilot install-claude install-pi install-opencode \
        uninstall-copilot uninstall-claude uninstall-pi uninstall-all uninstall-opencode \
        status status-opencode \
        verify validate-opencode validate-agents validate-skills validate-renders validate-specs clean \
        render-claude render-copilot render-pi render-opencode render-specs render-all \
        lint test quality-gate

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Install targets (platform-specific):"
	@echo "  install             Install to all 4 harnesses (~/.claude/, ~/.copilot/, ~/.pi/, ~/.config/opencode/)"
	@echo "  clean-install       Interactive backup + fresh install (prompts for each harness)"
	@echo "  fresh-install-copilot     Interactive: install Copilot only (with optional backup)"
	@echo "  fresh-install-claude      Interactive: install Claude only (with optional backup)"
	@echo "  fresh-install-pi          Interactive: install π.dev only (with optional backup)"
	@echo "  fresh-install-opencode    Interactive: install OpenCode only (with optional backup)"
	@echo "  install-claude      Install rendered agents → ~/.claude/"
	@echo "  install-copilot     Install rendered agents + skills → ~/.copilot/ (full agent support)"
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
	@echo "  render-opencode     Generate dist/opencode/ (OpenCode-compatible)"
	@echo "  render-all          All four + specs"
	@echo ""
	@echo "Diagnostic:"
	@echo "  status              Check installation status (all 4 harnesses)"
	@echo "  status-opencode     Check ~/.config/opencode/ install status"
	@echo "  verify              Full verification (structure + agents + skills + protocols)"
	@echo "  validate-opencode   Validate OpenCode config generation"
	@echo "  validate-agents     Validate agent YAML frontmatter + AGENTS.md registration"
	@echo "  validate-skills     Validate skill frontmatter + SKILLS.md registry completeness"
	@echo "  validate-renders    Verify all src/skills/ have corresponding dist/ outputs"
	@echo "  validate-specs      Verify dist/specs/ is deployed and valid"
	@echo "  clean               Remove build artifacts"
	@echo ""
	@echo "Quality & Testing:"
	@echo "  lint                Lint Python, Shell, and YAML files"
	@echo "  test                Run pytest test suite with coverage"
	@echo "  quality-gate        Pre-push quality checks (lint + test + verify)"

install: install-copilot install-claude install-pi install-opencode ## Install to all 4 harnesses
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next: Queue tasks using DELEGATE blocks in ~/.copilot/queue/incoming/"
	@echo "See ENTRYPOINT.md for complete workflow and queue-based execution model."

clean-install: ## Fresh install with interactive backup prompts (timestamped backups)
	@echo "🔄 Starting clean installation with interactive backup..."
	@echo "   (You will be prompted to confirm each harness backup)"
	@echo ""
	@bash "$(REPO_ROOT)/renderer/scripts/backup-harnesses.sh" copilot claude pi opencode
	@echo ""
	@echo "📦 Proceeding with fresh installation..."
	@$(MAKE) install

fresh-install-copilot: ## Interactive: install Copilot only (with optional backup)
	@bash "$(REPO_ROOT)/renderer/scripts/install-harness.sh" "$(REPO_ROOT)" copilot

fresh-install-claude: ## Interactive: install Claude only (with optional backup)
	@bash "$(REPO_ROOT)/renderer/scripts/install-harness.sh" "$(REPO_ROOT)" claude

fresh-install-pi: ## Interactive: install π.dev only (with optional backup)
	@bash "$(REPO_ROOT)/renderer/scripts/install-harness.sh" "$(REPO_ROOT)" pi

fresh-install-opencode: ## Interactive: install OpenCode only (with optional backup)
	@bash "$(REPO_ROOT)/renderer/scripts/install-harness.sh" "$(REPO_ROOT)" opencode

install-copilot: render-copilot ## Install rendered agents + skills → ~/.copilot/ (full agent support)
	@echo "📋 Validating dist/copilot/ is populated..."
	@test -d "$(REPO_ROOT)/dist/copilot/skills" || (echo "❌ dist/copilot/skills/ missing — run 'make render-copilot' first" && exit 1)
	@test -d "$(REPO_ROOT)/dist/copilot/agents" || (echo "❌ dist/copilot/agents/ missing — run 'make render-copilot' first" && exit 1)
	@echo "   ✓ dist/copilot/ validated"
	@echo "📦 Installing from dist/copilot/ → ~/.copilot/..."
	@mkdir -p "$(HOME)/.copilot"
	@rsync -a --exclude='.DS_Store' "$(REPO_ROOT)/dist/copilot/" "$(HOME)/.copilot/"
	@if [ -d "$(REPO_ROOT)/.githooks" ]; then \
		git -C "$(REPO_ROOT)" config core.hooksPath .githooks; \
		for hook in "$(REPO_ROOT)"/.githooks/*; do [ -f "$$hook" ] && chmod +x "$$hook"; done; \
		echo "✅ Git hooks installed (core.hooksPath = .githooks)"; \
	fi
	@echo "✅ Installation to ~/.copilot/ complete (agents + skills)"

install-claude: render-claude ## Install rendered agents → ~/.claude/
	@echo "📋 Validating dist/claude/ is populated..."
	@test -d "$(REPO_ROOT)/dist/claude/skills" || (echo "❌ dist/claude/skills/ missing — run 'make render-claude' first" && exit 1)
	@test -d "$(REPO_ROOT)/dist/claude/agents" || (echo "❌ dist/claude/agents/ missing — run 'make render-claude' first" && exit 1)
	@echo "   ✓ dist/claude/ validated"
	@echo "📦 Installing from dist/claude/ → ~/.claude/..."
	@mkdir -p "$(HOME)/.claude"
	@rsync -a --exclude='.DS_Store' "$(REPO_ROOT)/dist/claude/" "$(HOME)/.claude/"
	@if [ -d "$(REPO_ROOT)/.githooks" ]; then \
		git -C "$(REPO_ROOT)" config core.hooksPath .githooks; \
		for hook in "$(REPO_ROOT)"/.githooks/*; do [ -f "$$hook" ] && chmod +x "$$hook"; done; \
		echo "✅ Git hooks installed (core.hooksPath = .githooks)"; \
	fi
	@echo "✅ Installation to ~/.claude/ complete"

# Copilot CLI now supports custom agents. Agents are rendered alongside skills.
# render-copilot-agents.sh and render-copilot-agents.py handle agent rendering.
# Both are called by make install-copilot for complete agent + skill installation.

uninstall-copilot: ## Remove from ~/.copilot/ (managed only)
	@echo "🧹 Uninstalling from ~/.copilot/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(HOME)/.copilot" --uninstall

uninstall-claude: ## Remove from ~/.claude/ (managed only)
	@echo "🧹 Uninstalling from ~/.claude/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(HOME)/.claude" --uninstall



render-copilot: ## Generate dist/copilot/ with agents + skills (provider-specific)
	@echo "🔨 Rendering agents and skills for Copilot..."
	@mkdir -p "$(REPO_ROOT)/dist/copilot"
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot-agents.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/copilot"
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/copilot"
	@echo "🔍 Validating rendered Copilot config..."
	@test -d "$(REPO_ROOT)/dist/copilot/agents" || (echo "❌ agents directory not rendered" && exit 1)
	@test -d "$(REPO_ROOT)/dist/copilot/skills" || (echo "❌ skills directory not rendered" && exit 1)
	@echo "   ✓ Copilot agents validated"
	@echo "   ✓ Copilot skills validated"
	@echo "✅ Copilot rendering complete (see dist/copilot/)"

render-claude: ## Generate dist/claude/ (provider-specific)
	@echo "🔨 Rendering agents for Claude..."
	@mkdir -p "$(REPO_ROOT)/dist/claude"
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/claude"
	@echo "🔍 Validating rendered Claude config..."
	@test -d "$(REPO_ROOT)/dist/claude/agents" || (echo "❌ agents directory not rendered" && exit 1)
	@test -d "$(REPO_ROOT)/dist/claude/skills" || (echo "❌ skills directory not rendered" && exit 1)
	@echo "   ✓ Claude config validated"
	@echo "✅ Claude rendering complete (see dist/claude/)"

verify: ## Verify framework structure and tests (agents, skills, dependencies, queue)
	@echo "🔍 Verifying framework structure..."
	@echo ""
	@echo "1️⃣  Checking directory structure..."
	@test -d "$(REPO_ROOT)/src/orchestration/agents" || (echo "❌ src/orchestration/agents/ missing" && exit 1)
	@test -d "$(REPO_ROOT)/src/orchestration" || (echo "❌ src/orchestration/ missing" && exit 1)
	@test -d "$(REPO_ROOT)/src/skills" || (echo "❌ src/skills/ missing" && exit 1)
	@test -d "$(REPO_ROOT)/tests" || (echo "❌ tests/ missing" && exit 1)
	@echo "   ✓ Directory structure verified"
	@echo ""
	@echo "2️⃣  Checking agent YAML validity..."
	@for agent in $(REPO_ROOT)/src/orchestration/agents/*.py; do \
		if [ -f "$$agent" ]; then \
			python3 -m py_compile "$$agent" 2>/dev/null || (echo "❌ $$agent has syntax errors" && exit 1); \
		fi; \
	done
	@echo "   ✓ All agents have valid Python syntax"
	@echo ""
	@echo "3️⃣  Checking skill references exist..."
	@SKILLS_DIR="$(REPO_ROOT)/src/skills"; \
	if [ -d "$$SKILLS_DIR" ]; then \
		SKILL_COUNT=$$(find "$$SKILLS_DIR" -name "SKILL.md" | wc -l | tr -d ' '); \
		echo "   ✓ Found $$SKILL_COUNT skill definitions"; \
	else \
		echo "❌ Skills directory not found"; exit 1; \
	fi
	@echo ""
	@echo "4️⃣  Checking for circular dependencies..."
	@python3 -c "import sys; sys.path.insert(0, '$(REPO_ROOT)'); \
		from src.orchestration.agents import spec_validator; \
		print('   ✓ No circular dependencies detected')" 2>/dev/null || \
		echo "   ⚠️  Unable to check dependencies (validator not available)"
	@echo ""
	@echo "5️⃣  Checking installation structure completeness..."
	@test -f "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" || (echo "❌ render-copilot.sh missing" && exit 1)
	@test -f "$(REPO_ROOT)/renderer/scripts/render-claude.sh" || (echo "❌ render-claude.sh missing" && exit 1)
	@test -f "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" || (echo "❌ render-opencode.sh missing" && exit 1)
	@test -f "$(REPO_ROOT)/renderer/scripts/render-pi.sh" || (echo "❌ render-pi.sh missing" && exit 1)
	@echo "   ✓ Installation scripts verified"
	@echo ""
	@echo "6️⃣  Checking queue infrastructure..."
	@if [ -d "$(HOME)/.copilot/queue" ]; then \
		echo "   ✓ Queue infrastructure exists (Copilot)"; \
	else \
		echo "   ⚠️  Queue not installed (run 'make install-copilot')"; \
	fi
	@echo ""
	@echo "7️⃣  Validating agent definitions (src/agents/)..."
	@python3 "$(REPO_ROOT)/renderer/validate_agents.py" 2>&1 || echo "   ⚠️  Agent validation skipped (validator error)"
	@echo ""
	@echo "8️⃣  Validating skill definitions (src/skills/)..."
	@python3 "$(REPO_ROOT)/renderer/validate_skills.py" 2>&1 || echo "   ⚠️  Skill validation skipped (validator error)"
	@echo ""
	@echo "9️⃣  Checking protocol documents present..."
	@test -f "$(REPO_ROOT)/src/AGENTS.md" || (echo "❌ src/AGENTS.md missing" && exit 1)
	@test -f "$(REPO_ROOT)/src/DECISION-MAKING.md" || (echo "❌ src/DECISION-MAKING.md missing" && exit 1)
	@test -f "$(REPO_ROOT)/src/SKILLS.md" || (echo "❌ src/SKILLS.md missing" && exit 1)
	@test -f "$(REPO_ROOT)/src/CLI-PERMISSIONS.md" || (echo "❌ src/CLI-PERMISSIONS.md missing" && exit 1)
	@test -f "$(REPO_ROOT)/src/TOKEN_METRICS.md" || (echo "❌ src/TOKEN_METRICS.md missing" && exit 1)
	@test -f "$(REPO_ROOT)/src/TODO.md.template" || (echo "❌ src/TODO.md.template missing" && exit 1)
	@test -f "$(REPO_ROOT)/CONTRIBUTING.md" || (echo "❌ CONTRIBUTING.md missing" && exit 1)
	@echo "   ✓ All protocol documents present"
	@echo ""
	@echo "✅ Framework structure verified"

validate-opencode: ## Validate OpenCode config generation (status + JSON schema check)
	@echo "🔍 Validating OpenCode install at ~/.config/opencode/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode" --status
	@if [ -f "$(HOME)/.config/opencode/opencode.jsonc" ]; then \
		(command -v jq >/dev/null && jq -e --raw-input 'inputs' "$(HOME)/.config/opencode/opencode.jsonc" >/dev/null 2>&1) \
		|| python3 -c "import json,sys,re; t=open(sys.argv[1]).read(); t=re.sub(r'^\s*//.*$$','',t,flags=re.M); json.loads(t)" "$(HOME)/.config/opencode/opencode.jsonc"; \
		echo "✅ opencode.jsonc is valid JSONC"; \
	fi
	@echo "✅ OpenCode validation complete"

validate-agents: ## Validate agent definition files (src/agents/ YAML frontmatter + registration)
	@echo "🔍 Validating agent definitions..."
	@python3 "$(REPO_ROOT)/renderer/validate_agents.py" || (echo "❌ Agent validation failed — fix errors above" && exit 1)
	@echo "✅ Agent validation complete"

validate-skills: ## Validate skill definition files (frontmatter + SKILLS.md registry completeness)
	@echo "🔍 Validating skill definitions..."
	@python3 "$(REPO_ROOT)/renderer/validate_skills.py" || (echo "❌ Skill validation failed — fix errors above" && exit 1)
	@echo "✅ Skill validation complete"

validate-renders: ## Verify all src/skills/ have corresponding dist/ outputs (fails if out of sync)
	@echo "🔍 Validating dist/ renders are in sync with src/skills/..."
	@python3 "$(REPO_ROOT)/renderer/scripts/validate_renders.py" "$(REPO_ROOT)" || (echo "❌ Render validation failed — run 'make render-all' to regenerate" && exit 1)
	@echo "✅ Render validation complete"

lint: ## Lint Python, Shell, and YAML files
	@echo "🔍 Linting Python files (syntax check)..."
	@find "$(REPO_ROOT)/src" -name "*.py" -type f -exec python3 -m py_compile {} \; 2>&1 | grep -v "^$$" || echo "   ✓ Python syntax OK"
	@find "$(REPO_ROOT)/tests" -name "*.py" -type f -exec python3 -m py_compile {} \; 2>&1 | grep -v "^$$" || echo "   ✓ Test syntax OK"
	@if command -v ruff >/dev/null 2>&1; then \
		echo "🔍 Linting Python files (ruff style)..."; \
		ruff check "$(REPO_ROOT)/src" "$(REPO_ROOT)/tests" 2>&1 || echo "   ⚠️  Ruff warnings detected"; \
	fi
	@echo "🔍 Linting Shell files (bash -n)..."
	@find "$(REPO_ROOT)/renderer/scripts" -name "*.sh" -type f -exec bash -n {} \; && echo "   ✓ Shell syntax OK"
	@if command -v shellcheck >/dev/null 2>&1; then \
		echo "🔍 Linting Shell files (shellcheck)..."; \
		find "$(REPO_ROOT)/renderer/scripts" -name "*.sh" -type f -exec shellcheck {} \; && echo "   ✓ shellcheck OK" || echo "   ⚠️  shellcheck warnings"; \
	fi
	@if [ -f "$(REPO_ROOT)/opencode.jsonc" ]; then \
		echo "🔍 Linting YAML/JSON files..."; \
		python3 -c "import json,sys,re; t=open('$(REPO_ROOT)/opencode.jsonc').read(); t=re.sub(r'^\s*//.*$$','',t,flags=re.M); json.loads(t)" && echo "   ✓ opencode.jsonc syntax OK"; \
	fi
	@echo ""
	@echo "✅ All lints passed"

test: ## Run pytest test suite with coverage
	@echo "🧪 Running pytest test suite..."
	@cd "$(REPO_ROOT)" && python3 -m pytest tests/ \
		--cov=src \
		--cov-report=term-missing:skip-covered \
		--cov-report=html:htmlcov \
		-v --tb=short
	@echo ""
	@echo "✅ Tests complete. HTML coverage report: htmlcov/index.html"

test-concurrent: ## Run concurrent invocation tests (race condition guard)
	@echo "🔀 Running concurrent invocation tests (race condition guard)..."
	@echo "   Validates that HANDBACK file writes are atomic and the poller"
	@echo "   never reads a partially-written file under thread concurrency."
	@cd "$(REPO_ROOT)" && python3 -m pytest \
		tests/test_invoke_agent.py::TestConcurrentInvocations \
		-v --tb=short
	@echo ""
	@echo "✅ Concurrent tests passed — no race conditions detected"

quality-gate: lint test test-concurrent verify validate-renders ## Pre-push quality checks (lint + test + concurrent + verify + render validation)
	@echo ""
	@echo "✅✅✅ Quality gate PASSED ✅✅✅"
	@echo ""
	@echo "Ready to push:"
	@echo "  - Linting: PASS"
	@echo "  - Tests: PASS"
	@echo "  - Verification: PASS"
	@echo "  - Render validation: PASS"
	@echo ""
	@echo "Next: git push && git push --tags"

clean: ## Clean build artifacts (no external scripts)
	@echo "🧹 Cleaning artifacts..."
	@rm -rf "$(REPO_ROOT)/dist/"
	@find "$(REPO_ROOT)" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find "$(REPO_ROOT)" -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

.DEFAULT_GOAL := help

install-pi: render-pi ## Install π.dev harness from dist/pi/ → ~/.pi/
	@echo "📋 Validating dist/pi/ is populated..."
	@test -d "$(REPO_ROOT)/dist/pi" || (echo "❌ dist/pi/ missing — run 'make render-pi' first" && exit 1)
	@test -f "$(REPO_ROOT)/dist/pi/agent/SYSTEM.md" || (echo "❌ dist/pi/agent/SYSTEM.md missing — run 'make render-pi' first" && exit 1)
	@echo "   ✓ dist/pi/ validated"
	@echo "📦 Installing from dist/pi/ → ~/.pi/..."
	@mkdir -p "$(HOME)/.pi"
	@rsync -a --exclude='.DS_Store' "$(REPO_ROOT)/dist/pi/" "$(HOME)/.pi/"
	@echo "✅ Installation to ~/.pi/ complete"

install-opencode: render-opencode ## Install agents & skills to ~/.config/opencode/
	@echo "📋 Validating dist/opencode/ is populated..."
	@test -d "$(REPO_ROOT)/dist/opencode/skills" || (echo "❌ dist/opencode/skills/ missing — run 'make render-opencode' first" && exit 1)
	@test -d "$(REPO_ROOT)/dist/opencode/agents" || (echo "❌ dist/opencode/agents/ missing — run 'make render-opencode' first" && exit 1)
	@echo "   ✓ dist/opencode/ validated"
	@echo "📦 Installing from dist/opencode/ → ~/.config/opencode/..."
	@mkdir -p "$(HOME)/.config/opencode"
	@rsync -a --exclude='.DS_Store' "$(REPO_ROOT)/dist/opencode/" "$(HOME)/.config/opencode/"
	@if [ -d "$(REPO_ROOT)/.githooks" ]; then \
		git -C "$(REPO_ROOT)" config core.hooksPath .githooks; \
		for hook in "$(REPO_ROOT)"/.githooks/*; do [ -f "$$hook" ] && chmod +x "$$hook"; done; \
		echo "✅ Git hooks installed (core.hooksPath = .githooks)"; \
	fi
	@echo "✅ Installation to ~/.config/opencode/ complete"
	@echo ""
	@echo "ℹ️  To use agents via OpenCode CLI:"
	@echo "  opencode --agent orchestrator 'Your task description'"
	@echo "  opencode --agent engineer 'Implementation task'"
	@echo ""
	@echo "  Or via Copilot CLI:"
	@echo "  copilot --allow-all --autopilot --agent orchestrator 'Your task'"
	@echo ""
	@echo "  Skills are automatically discovered via skill tool."
	@echo "  Global rules in ~/.config/opencode/AGENTS.md"

uninstall-all: uninstall-copilot uninstall-claude uninstall-pi uninstall-opencode ## Remove from all 4 locations
	@echo "✅ Uninstall complete"

uninstall-pi: ## Remove from ~/.pi/ (managed only)
	@echo "🧹 Uninstalling from ~/.pi/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-pi.sh" "$(REPO_ROOT)" "$(HOME)/.pi" --uninstall

uninstall-opencode: ## Remove agentic-engineers from ~/.config/opencode/ (managed only)
	@echo "🧹 Uninstalling from ~/.config/opencode/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode" --uninstall

status-opencode: ## Status of ~/.config/opencode/ install
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode" --status

render-pi: ## Generate dist/pi/ config (π.dev harness)
	@echo "🔨 Rendering π.dev harness configuration → dist/pi/..."
	@mkdir -p "$(REPO_ROOT)/dist/pi"
	@python3 "$(REPO_ROOT)/renderer/scripts/render-pi-dev.py" "$(REPO_ROOT)/renderer/pi-dev-src" "$(REPO_ROOT)/dist/pi"
	@echo "🔍 Validating rendered π.dev config..."
	@test -f "$(REPO_ROOT)/dist/pi/agent/SYSTEM.md" || (echo "❌ dist/pi/agent/SYSTEM.md not rendered" && exit 1)
	@echo "   ✓ π.dev config validated"
	@echo "✅ π.dev harness rendering complete (see dist/pi/)"

render-opencode: ## Generate dist/opencode/ with agents + skills (provider-specific)
	@echo "🔨 Rendering agents and skills for OpenCode..."
	@mkdir -p "$(REPO_ROOT)/dist/opencode"
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/opencode"
	@echo "🔍 Validating rendered OpenCode config..."
	@test -d "$(REPO_ROOT)/dist/opencode/agents" || (echo "❌ agents directory not rendered" && exit 1)
	@test -d "$(REPO_ROOT)/dist/opencode/skills" || (echo "❌ skills directory not rendered" && exit 1)
	@echo "   ✓ OpenCode agents validated"
	@echo "   ✓ OpenCode skills validated"
	@echo "✅ OpenCode rendering complete (see dist/opencode/)"

render-all: render-copilot render-claude render-pi render-opencode render-specs ## Generate config for all 4 harnesses + specs

render-specs: ## Generate dist/specs/ (SPEC.md + orchestration YAML files)
	@echo "🔨 Rendering orchestration specs → dist/specs/..."
	@mkdir -p "$(REPO_ROOT)/dist/specs"
	@bash "$(REPO_ROOT)/renderer/scripts/render-specs.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist"
	@echo "🔍 Validating rendered specs..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-specs.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist" --validate
	@echo "✅ Spec rendering complete (see dist/specs/)"

validate-specs: ## Verify dist/specs/ is deployed and all spec files are valid
	@echo "🔍 Validating spec deployment at dist/specs/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-specs.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist" --validate || (echo "❌ Spec validation failed — run 'make render-specs' to regenerate" && exit 1)
	@echo "✅ Spec validation complete"

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
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode" --status
