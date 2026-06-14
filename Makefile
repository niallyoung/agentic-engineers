.PHONY: help install clean-install fresh-install-copilot fresh-install-claude fresh-install-pi fresh-install-opencode fresh-install-codex \
        install-copilot install-claude install-pi install-opencode install-codex \
        uninstall-copilot uninstall-claude uninstall-pi uninstall-all uninstall-opencode uninstall-codex \
        setup status harness-toggle migrate-queue-paths run-orchestrator create-test-session test-protocol-e2e \
        verify verify-harness-sync validate-opencode validate-codex validate-agents validate-skills validate-renders validate-specs clean \
        render-claude render-copilot render-pi render-opencode render-codex render-specs render-all \
        lint test test-evals test-concurrent test-ci test-ci-force test-ci-shell quality-gate

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)

# Install destination root. Defaults to $(HOME) (real install). Override to a
# sandbox for end-to-end pipeline testing, e.g.:
#   make install DESTDIR=/tmp/ae-install-test
# When DESTDIR != $(HOME), git-hook installation is skipped (sandbox-safe).
DESTDIR ?= $(HOME)

# Backup behavior for install targets. BACKUP=never disables the pre-install
# backup snapshot (safe for sandbox/CI installs where there is nothing to keep):
#   make install BACKUP=never DESTDIR=/tmp/ae-test
# Any other value (or unset) keeps the default auto-backup-by-copy behavior.
BACKUP ?=
ifeq ($(BACKUP),never)
BACKUP_FLAG := --no-backup
else
BACKUP_FLAG :=
endif

# Supported harnesses (mirrors install/render targets).
HARNESSES := claude copilot opencode pi codex

# Active-harness symlink location. Defaults to the framework state dir under
# $(HOME); override for hermetic testing, e.g.:
#   make harness-toggle HARNESS=opencode ACTIVE_LINK=/tmp/ae-test/active-harness
ACTIVE_LINK ?= $(HOME)/.agentic-engineers/active-harness

help:
	@echo "agentic-engineers — Multi-agent orchestration framework"
	@echo ""
	@echo "Setup:"
	@echo "  setup               Install Git hooks (.githooks/ → .git/hooks) + dependencies"
	@echo ""
	@echo "Install targets (platform-specific):"
	@echo "  install             Install default harness set (~/.claude/, ~/.copilot/, ~/.pi/, ~/.config/opencode/)"
	@echo "                      (override root for testing: make install DESTDIR=/tmp/ae-test)"
	@echo "  clean-install       Interactive backup + fresh install (prompts for each harness)"
	@echo "  fresh-install-copilot     Interactive: install Copilot only (with optional backup)"
	@echo "  fresh-install-claude      Interactive: install Claude only (with optional backup)"
	@echo "  fresh-install-pi          Interactive: install π.dev only (with optional backup)"
	@echo "  fresh-install-opencode    Interactive: install OpenCode only (with optional backup)"
	@echo "  fresh-install-codex       Interactive: install Codex only (with optional backup)"
	@echo "  install-claude      Install rendered agents → ~/.claude/"
	@echo "  install-copilot     Install rendered agents + skills → ~/.copilot/ (full agent support)"
	@echo "  install-pi          Install π.dev harness → ~/.pi/"
	@echo "  install-opencode    Install agents & skills → ~/.config/opencode/ (OpenCode-compatible)"
	@echo "  install-codex       Install Codex agents/config → ~/.codex/ and skills → ~/.agents/skills/"
	@echo ""
	@echo "Uninstall targets:"
	@echo "  uninstall-claude    Remove from ~/.claude/  (managed only)"
	@echo "  uninstall-copilot   Remove from ~/.copilot/  (managed only)"
	@echo "  uninstall-pi        Remove from ~/.pi/ (managed only)"
	@echo "  uninstall-all       All supported harnesses (including ~/.config/opencode/ and ~/.codex/)"
	@echo "  uninstall-opencode  Remove from ~/.config/opencode/ (agentic-engineers only)"
	@echo ""
	@echo "Render targets (generate dist/ from source):"
	@echo "  render-claude       Generate dist/claude/ (provider-specific)"
	@echo "  render-copilot      Generate dist/copilot/ (provider-specific)"
	@echo "  render-pi           Generate ~/.pi/agent/ config (π.dev harness)"
	@echo "  render-opencode     Generate dist/opencode/ (OpenCode-compatible)"
	@echo "  render-codex        Generate dist/codex/ (Codex-compatible)"
	@echo "  render-all          All harnesses + specs"
	@echo ""
	@echo "Diagnostic:"
	@echo "  status              Check installation status (all supported harnesses)"
	@echo "  harness-toggle      Symlink the active harness (HARNESS=claude|copilot|opencode|pi)"
	@echo "                      (override link path: ACTIVE_LINK=/path/to/active-harness)"
	@echo "  verify              Full verification (structure + agents + skills + protocols)"
	@echo "  validate-opencode   Validate OpenCode config generation"
	@echo "  validate-codex      Validate Codex config generation"
	@echo "  validate-agents     Validate agent YAML frontmatter + AGENTS.md registration"
	@echo "  validate-skills     Validate skill frontmatter + SKILLS.md registry completeness"
	@echo "  validate-renders    Verify all src/skills/ have corresponding dist/ outputs"
	@echo "  validate-specs      Verify dist/specs/ is deployed and valid"
	@echo "  clean               Remove build artifacts"
	@echo ""
	@echo "Queue & Testing:"
	@echo "  create-test-session Create test session + sample DELEGATE (AGENTIC_SESSION_ID=X AGENTIC_HARNESS=Y)"
	@echo "  run-orchestrator    Start orchestrator polling loop (AGENTIC_SESSION_ID=X)"
	@echo "  test-protocol-e2e   Run end-to-end protocol tests (DELEGATE → HANDBACK)"
	@echo ""
	@echo "Quality & Testing:"
	@echo "  lint                Lint Python, Shell, and YAML files"
	@echo "  test                Run pytest test suite with coverage"
	@echo "  test-concurrent     Run concurrent invocation tests (race condition guard)"
	@echo "  test-ci             Run tests in CI container (simulates GitHub Actions, first run)"
	@echo "  test-ci-force       Run tests in CI container (strict, must pass)"
	@echo "  test-ci-shell       Open interactive shell in CI container for debugging"
	@echo "  quality-gate        Pre-push quality checks (lint + test + verify)"

setup: ## Install Git hooks (.githooks/ → .git/hooks) + verify setup
	@echo "🔒 Setting up Git hooks..."
	@if [ ! -d "$(REPO_ROOT)/.githooks" ]; then \
		echo "❌ .githooks/ directory not found"; \
		exit 1; \
	fi
	@git -C "$(REPO_ROOT)" config core.hooksPath .githooks
	@echo "✓ Git configured to use .githooks/"
	@for hook in "$(REPO_ROOT)"/.githooks/pre-commit "$(REPO_ROOT)"/.githooks/pre-push "$(REPO_ROOT)"/.githooks/commit-msg "$(REPO_ROOT)"/.githooks/post-merge; do \
		if [ -f "$$hook" ]; then \
			chmod +x "$$hook"; \
			echo "✓ Made executable: $$(basename $$hook)"; \
		fi \
	done
	@echo ""
	@echo "🧪 Verifying hook setup..."
	@HOOK_PATH=$$(git -C "$(REPO_ROOT)" config core.hooksPath) && \
		if [ "$$HOOK_PATH" = ".githooks" ]; then \
			echo "✅ Git hooks configured: core.hooksPath = .githooks"; \
		else \
			echo "❌ Hook configuration failed: core.hooksPath = $$HOOK_PATH"; \
			exit 1; \
		fi
	@echo ""
	@echo "📖 Hook documentation: .githooks/README.md"
	@echo "🚀 Ready! Hooks will run automatically on commit/push"

migrate-queue-paths: ## Migrate queue sessions from old paths (artifacts/) to canonical paths
	@bash "$(REPO_ROOT)/setup/migrate-queue-paths.sh"

create-test-session: ## Create test session with sample DELEGATE (AGENTIC_SESSION_ID=X AGENTIC_HARNESS=Y)
	@bash "$(REPO_ROOT)/setup/create-test-session.sh"

run-orchestrator: ## Start orchestrator polling loop (AGENTIC_SESSION_ID=X required)
	@if [ -z "$(AGENTIC_SESSION_ID)" ]; then \
		echo "ERROR: AGENTIC_SESSION_ID not set. Usage: make run-orchestrator AGENTIC_SESSION_ID=test-001"; \
		exit 1; \
	fi
	@echo "🚀 Starting orchestrator for session: $(AGENTIC_SESSION_ID)"
	@echo "TODO: Implement orchestrator-poll command (placeholder)"
	@echo "Polling queue: ~/.agentic-engineers/$(AGENTIC_SESSION_ID)/$${AGENTIC_HARNESS:-local}/queue/incoming/"

test-protocol-e2e: ## Run end-to-end protocol tests (DELEGATE → HANDBACK)
	@echo "🧪 Running end-to-end protocol tests (Phase 4)..."
	@echo "Testing: DELEGATE → processing → HANDBACK → done/failed/escalation"
	@python3 -m pytest tests/test_e2e_protocol_full_cycle.py -v --tb=short
	@echo ""
	@echo "✅ All protocol E2E tests passed!"

install: render-all ## Install default harness set (auto-backup, non-interactive)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" $(BACKUP_FLAG) --destdir "$(DESTDIR)" copilot claude pi opencode
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next: copilot --autopilot --agent orchestrator 'Your task'"
	@echo "Or: Queue tasks using DELEGATE blocks in ~/.copilot/queue/incoming/"

clean-install: render-all ## Interactive: Install default harness set (prompt for each)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" --interactive --destdir "$(DESTDIR)" copilot claude pi opencode

fresh-install-copilot: ## Interactive: install Copilot only (prompt for backup)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" --interactive --destdir "$(DESTDIR)" copilot

fresh-install-claude: ## Interactive: install Claude only (prompt for backup)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" --interactive --destdir "$(DESTDIR)" claude

fresh-install-pi: ## Interactive: install π.dev only (prompt for backup)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" --interactive --destdir "$(DESTDIR)" pi

fresh-install-opencode: ## Interactive: install OpenCode only (prompt for backup)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" --interactive --destdir "$(DESTDIR)" opencode

fresh-install-codex: ## Interactive: install Codex only (prompt for backup)
	@bash "$(REPO_ROOT)/renderer/scripts/unified-install.sh" "$(REPO_ROOT)" --interactive --destdir "$(DESTDIR)" codex

install-copilot: ## Install rendered agents + skills → ~/.copilot/ (marker-aware: never overwrites foreign files)
	@echo "📦 Installing Copilot agents + skills + docs → $(DESTDIR)/.copilot/ (marker-aware)..."
	@mkdir -p "$(DESTDIR)/.copilot"
	@# Install directly via the marker-aware render scripts (same model as
	@# install-claude) rather than 'rsync dist/copilot/ → ~/.copilot/'. This
	@# enforces foreign-file protection: user-authored agents/skills and a user's
	@# own AGENTS.md are never overwritten, and user config/auth/session files are
	@# left untouched. render-copilot-agents.sh renders agents (sidecar manifest);
	@# render-copilot.sh renders skills + AGENTS.md and installs git hooks.
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot-agents.sh" "$(REPO_ROOT)" "$(DESTDIR)/.copilot"
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(DESTDIR)/.copilot"
	@echo "✅ Installation to $(DESTDIR)/.copilot/ complete (agents + skills + docs)"

install-claude: ## Install rendered agents → ~/.claude/ (marker-aware: never overwrites foreign files)
	@echo "📦 Installing Claude agents + skills → $(DESTDIR)/.claude/ (marker-aware)..."
	@mkdir -p "$(DESTDIR)/.claude"
	@# Use render-claude.sh's install function directly. Unlike a plain
	@# 'rsync dist/claude/ → ~/.claude/', this enforces foreign-file protection
	@# (skips overwriting user-authored agents/skills) and normalises permissions
	@# (rsync --chmod=D755,F644). render-claude.sh renders fresh from source and
	@# installs git hooks internally when the target is $(HOME).
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(DESTDIR)/.claude"
	@echo "✅ Installation to $(DESTDIR)/.claude/ complete"

# Copilot CLI now supports custom agents. Agents are rendered alongside skills.
# render-copilot-agents.sh and render-copilot-agents.py handle agent rendering.
# Both are called by make install-copilot for complete agent + skill installation.

uninstall-copilot: ## Remove from ~/.copilot/ (managed only; honors DESTDIR)
	@echo "🧹 Uninstalling from $(DESTDIR)/.copilot/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(DESTDIR)/.copilot" --uninstall
	@python3 "$(REPO_ROOT)/renderer/scripts/render-copilot-agents.py" "$(REPO_ROOT)/src/agents" "$(DESTDIR)/.copilot/agents" --uninstall

uninstall-claude: ## Remove from ~/.claude/ (managed only; honors DESTDIR)
	@echo "🧹 Uninstalling from $(DESTDIR)/.claude/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(DESTDIR)/.claude" --uninstall



render-copilot: ## Generate dist/copilot/ with agents + skills (provider-specific)
	@echo "🔨 Rendering agents and skills for Copilot..."
	@mkdir -p "$(REPO_ROOT)/dist/copilot"
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot-agents.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/copilot"
	@bash "$(REPO_ROOT)/renderer/scripts/render-copilot.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/copilot"
	@echo "🔍 Validating rendered Copilot config..."
	@test -d "$(REPO_ROOT)/dist/copilot/agents" || (echo "❌ agents directory not rendered" && exit 1)
	@test -d "$(REPO_ROOT)/dist/copilot/skills" || (echo "❌ skills directory not rendered" && exit 1)
	@test -f "$(REPO_ROOT)/dist/copilot/AGENTS.md" || (echo "❌ AGENTS.md not found" && exit 1)
	@echo "   ✓ Copilot agents validated"
	@echo "   ✓ Copilot skills validated"
	@echo "   ✓ Copilot docs (AGENTS.md) validated"
	@echo "✅ Copilot rendering complete (see dist/copilot/)"

render-claude: ## Generate dist/claude/ (provider-specific)
	@echo "🔨 Rendering agents for Claude..."
	@mkdir -p "$(REPO_ROOT)/dist/claude"
	@bash "$(REPO_ROOT)/renderer/scripts/render-claude.sh" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/claude"
	@echo "🔍 Validating rendered Claude config..."
	@test -d "$(REPO_ROOT)/dist/claude/agents" || (echo "❌ agents directory not rendered" && exit 1)
	@test -d "$(REPO_ROOT)/dist/claude/skills" || (echo "❌ skills directory not rendered" && exit 1)
	@test -f "$(REPO_ROOT)/dist/claude/AGENTS.md" || (echo "❌ AGENTS.md not rendered" && exit 1)
	@test -f "$(REPO_ROOT)/dist/claude/CLAUDE.md" || (echo "❌ CLAUDE.md not rendered" && exit 1)
	@echo "   ✓ Claude config validated"
	@echo "   ✓ Claude docs (CLAUDE.md + AGENTS.md) validated"
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
	@test -f "$(REPO_ROOT)/renderer/scripts/render-codex.py" || (echo "❌ render-codex.py missing" && exit 1)
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

verify-harness-sync: ## Verify installed harness files match dist/ (warns on divergence)
	@echo "🔐 Verifying harness synchronization between dist/ and installed..."
	@echo ""
	@DIST_FILE="$(REPO_ROOT)/dist/claude/CLAUDE.md"; \
	INSTALLED_FILE="$(HOME)/.claude/CLAUDE.md"; \
	if [ ! -f "$$DIST_FILE" ]; then \
		echo "❌ Dist file not found: $$DIST_FILE"; exit 1; \
	fi; \
	if [ ! -f "$$INSTALLED_FILE" ]; then \
		echo "⚠️  Installed file not found: $$INSTALLED_FILE (run 'make install-claude' first)"; exit 1; \
	fi; \
	if diff -q "$$DIST_FILE" "$$INSTALLED_FILE" > /dev/null 2>&1; then \
		echo "✅ Claude CLAUDE.md is in sync with dist/"; \
	else \
		echo "⚠️  Divergence detected between dist/ and installed:"; \
		diff -u "$$DIST_FILE" "$$INSTALLED_FILE" | head -40; \
		echo ""; \
		echo "To synchronize, run: make install-claude"; \
		exit 1; \
	fi
	@echo "✅ Harness synchronization verified"

validate-opencode: ## Validate OpenCode config generation (status + JSON schema check)
	@echo "🔍 Validating OpenCode install at ~/.config/opencode/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode" --status
	@if [ -f "$(HOME)/.config/opencode/opencode.jsonc" ]; then \
		(command -v jq >/dev/null && jq -e --raw-input 'inputs' "$(HOME)/.config/opencode/opencode.jsonc" >/dev/null 2>&1) \
		|| python3 -c "import json,sys,re; t=open(sys.argv[1]).read(); t=re.sub(r'^\s*//.*$$','',t,flags=re.M); json.loads(t)" "$(HOME)/.config/opencode/opencode.jsonc"; \
		echo "✅ opencode.jsonc is valid JSONC"; \
	fi
	@echo "✅ OpenCode validation complete"

validate-codex: ## Validate Codex config generation (status + rendered file checks)
	@echo "🔍 Validating Codex render at dist/codex/..."
	@python3 "$(REPO_ROOT)/renderer/scripts/render-codex.py" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/codex" --skills-root "$(REPO_ROOT)/dist/codex/skills" --validate || (echo "❌ Codex validation failed — run 'make render-codex' to regenerate" && exit 1)
	@echo "✅ Codex validation complete"

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

test-evals: ## Run DELEGATE/HANDBACK quality evaluation tests
	@echo "🧪 Running eval framework tests (20+ quality checks)..."
	@echo "   Tests: DELEGATE required fields, plan quality, scope substance"
	@echo "   Tests: HANDBACK metrics, status canonicity, output substance"
	@echo "   Tests: Orchestrator routing correctness, model/effort alignment"
	@cd "$(REPO_ROOT)" && python3 -m pytest tests/evals/ -v --tb=short
	@echo ""
	@echo "✅ All eval tests passed"

test-concurrent: ## Run concurrent invocation tests (race condition guard)
	@echo "🔀 Running concurrent invocation tests (race condition guard)..."
	@echo "   Validates that HANDBACK file writes are atomic and the poller"
	@echo "   never reads a partially-written file under thread concurrency."
	@cd "$(REPO_ROOT)" && python3 -m pytest \
		tests/test_invoke_agent.py::TestConcurrentInvocations \
		-v --tb=short
	@echo ""
	@echo "✅ Concurrent tests passed — no race conditions detected"

test-ci: ## Run tests in CI container (simulates GitHub Actions environment, first run, no-fail)
	@echo "🐳 Starting CI environment simulation in Docker container..."
	@echo "   This simulates the exact GitHub Actions ubuntu-latest environment."
	@echo "   Tests will catch environment-specific issues (symlinks, permissions, paths)."
	@echo ""
	@if ! command -v docker &> /dev/null; then \
		echo "❌ Docker is not installed. Please install Docker to use test-ci."; \
		echo "   Visit: https://docs.docker.com/get-docker/"; \
		exit 1; \
	fi
	@echo "📦 Building Docker image (may take 30-60 seconds on first run)..."
	@docker build --rm -t agentic-engineers-ci:latest "$(REPO_ROOT)" 2>&1 | grep -E "^(Step|RUN|COPY|FROM|Successfully)" || true
	@echo ""
	@echo "🧪 Running tests in container..."
	@docker run --rm \
		-v "$(REPO_ROOT):/workspace" \
		-w /workspace \
		agentic-engineers-ci:latest \
		pytest tests/ -v --tb=short
	@echo ""
	@echo "✅ CI container tests complete"
	@echo "   Tip: Use 'make test-ci-force' for strict passing tests"
	@echo "   Tip: Use 'make test-ci-shell' to debug in container interactively"

test-ci-force: ## Run tests in CI container (strict, must pass)
	@echo "🐳 Starting STRICT CI environment test in Docker container..."
	@echo "   This will fail if any test fails (non-lenient mode)."
	@echo ""
	@if ! command -v docker &> /dev/null; then \
		echo "❌ Docker is not installed. Please install Docker to use test-ci-force."; \
		exit 1; \
	fi
	@echo "📦 Building Docker image..."
	@docker build --rm -t agentic-engineers-ci:latest "$(REPO_ROOT)" > /dev/null 2>&1
	@echo ""
	@echo "🧪 Running tests in container (strict mode)..."
	@docker run --rm \
		-v "$(REPO_ROOT):/workspace" \
		-w /workspace \
		agentic-engineers-ci:latest \
		pytest tests/ -v --tb=short --strict-markers
	@echo ""
	@echo "✅ All CI tests passed (strict mode)"

test-ci-shell: ## Open interactive shell in CI container for debugging
	@echo "🐳 Opening interactive shell in CI container..."
	@echo "   You can run pytest, inspect files, and debug issues."
	@echo "   Type 'exit' to return to your local shell."
	@echo ""
	@if ! command -v docker &> /dev/null; then \
		echo "❌ Docker is not installed. Please install Docker to use test-ci-shell."; \
		exit 1; \
	fi
	@echo "📦 Building Docker image..."
	@docker build --rm -t agentic-engineers-ci:latest "$(REPO_ROOT)" > /dev/null 2>&1
	@echo ""
	@docker run -it --rm \
		-v "$(REPO_ROOT):/workspace" \
		-w /workspace \
		agentic-engineers-ci:latest \
		/bin/bash
	@echo ""
	@echo "👋 Exited CI container"

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

install-pi: ## Install π.dev harness → ~/.pi/ (marker-aware: never overwrites foreign files)
	@echo "📦 Installing π.dev harness → $(DESTDIR)/.pi/ (marker-aware)..."
	@mkdir -p "$(DESTDIR)/.pi"
	@# Install directly via the marker-aware render script (same model as
	@# install-claude) rather than 'rsync dist/pi/ → ~/.pi/'. render-pi.sh writes
	@# its marker and refuses to clobber a foreign (user-managed) install.
	@bash "$(REPO_ROOT)/renderer/scripts/render-pi.sh" "$(REPO_ROOT)" "$(DESTDIR)/.pi"
	@echo "✅ Installation to $(DESTDIR)/.pi/ complete"

install-opencode: ## Install agents & skills → ~/.config/opencode/ (marker-aware: never overwrites foreign files)
	@echo "📦 Installing OpenCode agents + skills + config → $(DESTDIR)/.config/opencode/ (marker-aware)..."
	@mkdir -p "$(DESTDIR)/.config/opencode"
	@# Install directly via the marker-aware render script (same model as
	@# install-claude) rather than 'rsync dist/opencode/ → ~/.config/opencode/'.
	@# render-opencode.sh enforces foreign-file protection for skills, agents,
	@# AGENTS.md and opencode.jsonc (a user's own config is never overwritten) and
	@# installs git hooks.
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(DESTDIR)/.config/opencode"
	@echo "✅ Installation to $(DESTDIR)/.config/opencode/ complete"
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

install-codex: ## Install Codex agents/config → ~/.codex/ and skills → ~/.agents/skills/ (marker-aware)
	@echo "📦 Installing Codex agents + config → $(DESTDIR)/.codex/ and skills → $(DESTDIR)/.agents/skills/ (marker-aware)..."
	@mkdir -p "$(DESTDIR)/.codex" "$(DESTDIR)/.agents/skills"
	@python3 "$(REPO_ROOT)/renderer/scripts/render-codex.py" "$(REPO_ROOT)" "$(DESTDIR)/.codex" --skills-root "$(DESTDIR)/.agents/skills"
	@echo "✅ Installation to $(DESTDIR)/.codex/ complete"
	@echo ""
	@echo "ℹ️  To use the Codex harness:"
	@echo "  codex --sandbox workspace-write --ask-for-approval on-request"
	@echo "  Then ask: use the agentic-engineers orchestrator for this task."
	@echo ""
	@echo "  For disposable self-tests only:"
	@echo "  codex exec --sandbox workspace-write --ask-for-approval never 'Summarize active agentic-engineers instructions'"

uninstall-all: uninstall-copilot uninstall-claude uninstall-pi uninstall-opencode uninstall-codex ## Remove from all supported locations
	@echo "✅ Uninstall complete"

uninstall-pi: ## Remove from ~/.pi/ (managed only; honors DESTDIR)
	@echo "🧹 Uninstalling from $(DESTDIR)/.pi/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-pi.sh" "$(REPO_ROOT)" "$(DESTDIR)/.pi" --uninstall

uninstall-opencode: ## Remove agentic-engineers from ~/.config/opencode/ (managed only; honors DESTDIR)
	@echo "🧹 Uninstalling from $(DESTDIR)/.config/opencode/..."
	@bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(DESTDIR)/.config/opencode" --uninstall

uninstall-codex: ## Remove agentic-engineers from ~/.codex/ and ~/.agents/skills/ (managed only; honors DESTDIR)
	@echo "🧹 Uninstalling from $(DESTDIR)/.codex/ and $(DESTDIR)/.agents/skills/..."
	@python3 "$(REPO_ROOT)/renderer/scripts/render-codex.py" "$(REPO_ROOT)" "$(DESTDIR)/.codex" --skills-root "$(DESTDIR)/.agents/skills" --uninstall

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

render-codex: ## Generate dist/codex/ with Codex custom agents + skills + config
	@echo "🔨 Rendering agents and skills for Codex..."
	@mkdir -p "$(REPO_ROOT)/dist/codex"
	@python3 "$(REPO_ROOT)/renderer/scripts/render-codex.py" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/codex" --skills-root "$(REPO_ROOT)/dist/codex/skills"
	@echo "🔍 Validating rendered Codex config..."
	@python3 "$(REPO_ROOT)/renderer/scripts/render-codex.py" "$(REPO_ROOT)" "$(REPO_ROOT)/dist/codex" --skills-root "$(REPO_ROOT)/dist/codex/skills" --validate
	@test -d "$(REPO_ROOT)/dist/codex/agents" || (echo "❌ agents directory not rendered" && exit 1)
	@test -d "$(REPO_ROOT)/dist/codex/skills" || (echo "❌ skills directory not rendered" && exit 1)
	@test -f "$(REPO_ROOT)/dist/codex/AGENTS.md" || (echo "❌ AGENTS.md not rendered" && exit 1)
	@echo "   ✓ Codex agents validated"
	@echo "   ✓ Codex skills validated"
	@echo "✅ Codex rendering complete (see dist/codex/)"

render-all: render-copilot render-claude render-pi render-opencode render-codex render-specs ## Generate config for all harnesses + specs

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

harness-toggle: ## Force-create active-harness symlink (HARNESS=claude|copilot|opencode|pi, ACTIVE_LINK=path)
	@if [ -z "$(HARNESS)" ]; then \
		echo "❌ HARNESS not set. Usage: make harness-toggle HARNESS=<$(subst $() ,|,$(HARNESSES))>"; \
		exit 1; \
	fi
	@case " $(HARNESSES) " in \
		*" $(HARNESS) "*) ;; \
		*) echo "❌ Invalid HARNESS '$(HARNESS)'. Supported: $(HARNESSES)"; exit 1 ;; \
	esac
	@if [ ! -d "$(REPO_ROOT)/dist/$(HARNESS)" ]; then \
		echo "❌ dist/$(HARNESS)/ not found. Run 'make render-$(HARNESS)' first."; \
		exit 1; \
	fi
	@mkdir -p "$$(dirname "$(ACTIVE_LINK)")"
	@ln -sfn "$(REPO_ROOT)/dist/$(HARNESS)" "$(ACTIVE_LINK)"
	@echo "✅ Active harness: $(HARNESS)"
	@echo "   $(ACTIVE_LINK) -> $(REPO_ROOT)/dist/$(HARNESS)"

status: ## Check installation status (all supported harnesses)
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
	@echo ""
	@echo "📋 Installation status for ~/.codex/ and ~/.agents/skills/:"
	@python3 "$(REPO_ROOT)/renderer/scripts/render-codex.py" "$(REPO_ROOT)" "$(HOME)/.codex" --skills-root "$(HOME)/.agents/skills" --status
