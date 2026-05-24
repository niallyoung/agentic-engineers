# Changelog



## [Unreleased] - v0.35.0

### Added
- Phase 2 - Orchestrator and invoke-agent routing
- Phase 2 security hardening - PKI signing, entropy detection, agent identity, audit logging, rate limiting, budget enforcement
- Phase 3 - Test migration and multi-harness isolation
- Phase 4 - E2E, rollback, monitoring

### Fixed
- adjust CHANGELOG validation to match version-manager design
- commit renderer/lib/render-lib.sh as source
- export ArtifactMemoryStore and resolve __init__.py imports
- remove duplicate path setup in test file
- remove version from [Unreleased] (final fix)
- remove version number from [Unreleased] section
- repair versioning sync corruption and add validation
- resolve pytest import issue for nested skill modules
- resolve pytest module resolution for nested skill packages
- update CI Python 3.11 for Ubuntu 24.04 compatibility
- update upload-artifact to v4 (deprecated v3)
- use absolute REPO_ROOT paths in test_render_pipeline.py
- whitelist src/auth.py in entropy detector to reduce false positives

### Documentation
- remove [Unreleased] placeholder - versions released

## [v0.34.0] - 2026-05-24

### Added
- Phase 2 security hardening - PKI signing, entropy detection, agent identity, audit logging, rate limiting, budget enforcement
- Workflow-review skill: generates workflow diagrams, validates delegation chains
- Security hardening: 6 modules (PKI signing, entropy detection, agent identity, audit logging, rate limiting, budget enforcement)

### Fixed
- commit renderer/lib/render-lib.sh as source
- remove duplicate path setup in test file
- resolve pytest import issue for nested skill modules
- resolve pytest module resolution for nested skill packages
- fix CHANGELOG versioning sync (v0.34.0 was listed below v0.33.3, [Unreleased] had version number)

### Documentation
- docs/RENDERING.md: comprehensive harness lifecycle documentation
- docs/FEEDBACK-LOOPS.md: post-merge feedback loop patterns
- docs/SKILLS-AVAILABLE.md: skill index with 17 skills

## [v0.33.3] - 2026-05-24

### Added
- restore file-sync and pre-gate implementations (102 tests: file-sync skill + file-cleanup pre-gate framework)

### Fixed
- correct bash syntax in pre-commit hook for .pyc detection
- implement 6-layer file loss prevention framework
- fix TOCTOU race condition in concurrent HANDBACK file writes
- fix CHANGELOG update logic to track all commits
- resolve CI path evaluation errors in tests
- aggressive cleanup - delete obsolete files and reorganize
- refocus CONTRIBUTING.md on framework-based delegation
- simplify CONTRIBUTING.md — defer to framework and meta-skills

## [v0.33.2] - 2026-05-24

### Added
- Multi-harness queue isolation with session-based artifacts (`~/.agentic-engineers/artifacts/{sessionID}/{harness}/`)
- Task orchestration skill for autonomous parallel task execution (framework-level, 64 tests)
- Cost management framework TODOs (COST-001 to COST-004, June 1 deadline)

### Changed
- Consolidate repository structure: archive 28 historical docs, unify config/orchestration.yaml
- Render workflow: standardize render-to-dist, install-to-harness (all skills render to dist/ first)
- Remove automatic tag creation from CI workflow (local versioning now authoritative)
- Update orchestrator-agent.md with autonomous parallelization section

### Fixed
- Move validate_renders.py to renderer/scripts/ (SPEC.md compliance)
- Update test paths for renderer/scripts location

### Removed
- Healing Engineer role (9th role not in canonical spec, adds no proportional value)
- Spec Engineer references (not in canonical 8-role spec)
- GitHub Actions auto-tagging job (use local version-manager skill instead)

### Security
- Multi-harness queue isolation ensures complete artifact separation by sessionID/harness
- Security audit passed: no PII, no credentials, no injection risks
- Git operations skill uses safe subprocess calls with proper quoting

## [v0.33.1] - 2026-05-23

### Fixed
- add subprocess output debugging to test runner
- set explicit cwd in subprocess for CI compatibility
- use git tags as primary version source

### Changed
- remove stale VERSION file, make versioning git-tag-only

### Miscellaneous
- cleanup: remove debug traces from render-pi-dev.py
- debug: add detailed execution traces for CI troubleshooting
- debug: improve error diagnostics with [DEBUG] markers to stderr

## [v0.33.0] - 2026-05-23

### Added
- add semantic versioning with automatic releases

### Fixed
- add enhanced error diagnostics for CI/CD troubleshooting
- configure git core.hooksPath in CI workflow
- mark render_pi_dev_args tests as xfail for CI
- remove remaining underscore queue_management imports
- resolve SPEC paths and mark incomplete tests
- resolve symlink and environment issues in render-pi-dev.py
- robust path resolution for pi-dev-src in all environments
- use importlib for hyphenated skill package imports in all tests

### Miscellaneous
- debug: add verbose path resolution logging to diagnose CI failures

## [v0.32.4] - 2026-05-23

### Fixed
- configure git to preserve symlinks in CI
- enable symlinks in workflow checkout
- remove symlinks and use importlib for hyphenated package imports
- use importlib for hyphenated skill package imports in all tests

### Documentation
- update WORKFLOW.md with accurate test status

### Miscellaneous
- ci: copy githooks to .git/hooks for test execution
- ci: remove WORKFLOW.md
- ci: set PYTHONPATH in Makefile test target
- ci: use pip install -e . instead of PYTHONPATH wrapper
- ci: use run_pytest.sh wrapper to ensure proper PYTHONPATH


## [v0.32.3] - 2026-05-23
### Fixed
- ensure all 4 harnesses follow consistent render→install chain

### Documentation
- add support/sponsorship section with Bitcoin & Lightning QR codes

### Miscellaneous
- ci: add GitHub Actions CI/CD workflow with semantic versioning
- ci: add pytest.ini to auto-configure pythonpath
- ci: fix pytest module imports in CI environment
- ci: improve conftest.py robustness with PYTHONPATH env
- ci: pass PYTHONPATH explicitly to make test command
- license: add MIT license


## [v0.32.2] - 2026-05-23
### Fixed
- cleanup documentation from CLI-PERMISSIONS

### Documentation
- add support/sponsorship section with Bitcoin & Lightning QR codes
- cleanup README, verify technical claims, cleanup documentation
- fix Copilot CLI documentation - agents are supported

### Miscellaneous
- cleanup: remove repo-specific repository references
- security: remove personal filesystem paths from archived documentation


## [v0.32.1] - 2026-05-23
### Documentation
- add quick benefits summary to Key Benefits section
- move benefits summary to top of README after 'What It Is'
- remove status line from README
- reorder harness options in README installation guide
- sort roles table by cost+thinking+effort


## [v0.32.0] - 2026-05-23
### Added
- validate result metrics schema in agent validator

### Fixed
- correct Category 12 skill count to 13 (was 12)
- patch symlink traversal vulnerability in validate_skills

### Changed
- document TODO.md commit strategy

### Documentation
- add CONTRIBUTING.md — dev workflow and contribution guide


## [v0.31.0] - 2026-05-22
### Added
- add AGENTS.md — formal agent roster and packet protocol
- add CLI-PERMISSIONS.md — tool access matrix by role
- add TODO.md.template — canonical task tracking format
- add agent and skill validators
- add validators and enhance verify target


## [v0.30.3] - 2026-05-22
### Documentation
- Add TOKEN_METRICS.md — cost tracking specification and format
- Simplify Example section and fix harness terminology
- Update TODO.md with README refactoring completion
- add autonomous decision framework and high-water mark principles
- add documentation, core protocols, and installation verification sections to README


## [v0.30.2] - 2026-05-20
### Documentation
- Add Copilot CLI alias tip to Quick Start section
- Add Examples, Advanced Examples, and expand Roles table
- Add Key Benefits & Discoveries and Model Configuration
- Expand CLI alias hints with both commands
- Remove outdated task creation and orchestrator examples


## [v0.30.1] - 2026-05-20
### Documentation
- Add Gastown framework to market comparison
- Add orchestrator session summary (2026-05-19)
- add Gastown comparison task to TODO
- update TODO with Phase H/I and skills delegation

### Miscellaneous
- Update TODO.md: Mark 3 skills complete, plan Phase H retry (TIER 1/2/3)


## [v0.30.0] - 2026-05-18
### Added
- add distributed caching layer (2026-05-17-caching-layer)

### Changed
- remove standalone daemon

### Documentation
- add comprehensive market comparison to README
- archive outdated docs
- update TODO status


## [v0.29.1] - 2026-05-17
### Fixed
- resolve null pointer exception with error handling

### Documentation
- Architecture audit — identify consolidation opportunities
- Phase 6 validation complete — 137 tests passing, production ready

### Miscellaneous
- 2026-05-27-phase6-complete: final summary and sign-off
- Add Phase 6 validation tests with sample tasks


## [v0.29.0] - 2026-05-17
### Added
- Phase 2 integration with schemas and engines
- add end-to-end tests for protocol expansion (Phase 5)

### Documentation
- Execution log for protocol expansion Phase 1
- Self-defense for config protection

### Miscellaneous
- 2026-05-27-phase6-deployment: regression tests, polling fix


## [v0.28.0] - 2026-05-17
### Added
- Complete testing, validation, production readiness
- Phase 3 Week 4-5 Token Visibility Integration complete
- Simplification, docs, routing, quality, cost

### Documentation
- Protocol expansion initiative
- Task lifecycle visualization


## [v0.27.0] - 2026-05-16
### Added
- Phase 3 Week 2 harness implementations complete
- Phase 3 Week 3-4 Orchestrator improvements (3/4 complete)
- implement Copilot CLI streaming output feature
- implement dry-run mode for orchestrator

### Documentation
- Phase 3 Week 1 implementation specs complete


## [v0.26.1] - 2026-05-16
### Testing
- Test 1 PASS — 50 agents in 2m 39s

### Documentation
- Phase 3 implementation plan — ready for execution
- consolidation phase complete — 12 parallel agents
- create comprehensive testing roadmap for concurrent agents
- integrate token visibility into workflow documentation


## [v0.26.0] - 2026-05-16
### Added
- SDLC enforcement via git hooks and OpenCode

### Documentation
- add parallel delegation documentation
- add post-hook-implementation status and enforcement summary

### Miscellaneous
- Add OpenCode token visibility plugin & max subagent analysis
- Investigate actual concurrent subagent capacity — no artificial limits


## [v0.25.0] - 2026-05-16
### Added
- implement SDLC enforcement via git hooks and OpenCode commands

### Miscellaneous
- Add comprehensive AI frameworks research and integration strategy
- Add framework integration pause mechanism with explicit opt-in requirement
- Phase 2: Consolidate framework research and planning into README, TODO, and docs
- Repository cleanup: .gitignore, .env.production, artifacts/, and documentation


## [v0.24.1] - 2026-05-16
### Changed
- cleanup src/skills/ directory - remove duplicates, organize documentation
- consolidate render script duplication into shared lib.sh
- render-claude.sh reads canonical agent definitions from docs/AGENTS.md

### Miscellaneous
- Comprehensive harness equalization and documentation consolidation (2026-05-16)
- Sync π.dev source files with canonical 8-role model and current model IDs


## [v0.24.0] - 2026-05-16
### Added
- add claude-opus-4.6 to github-copilot provider via custom model config
- render default_agent: orchestrator in opencode.jsonc

### Fixed
- add agent.orchestrator model override to opencode.jsonc
- add global model field to opencode.jsonc for orchestrator default

### Documentation
- add comprehensive harness review and comparison table to README


## [v0.23.0] - 2026-05-16
### Added
- rewrite OpenCode renderer as bash sibling of render-claude.sh

### Fixed
- emit opencode.jsonc with comment-based sentinel to satisfy strict schema
- orchestrator agent uses mode: all so --agent orchestrator works

### Changed
- remove uninstall-opencode-legacy (~/.opencode/ not a documented OpenCode path)

### Documentation
- rewrite OpenCode install guide for managed install + correct provider IDs


## [v0.22.0] - 2026-05-16
### Added
- Add π.dev (Pi) harness support to agentic-engineers

### Fixed
- Integrate opencode renderer into main install/uninstall/status targets

### Miscellaneous
- Add π.dev harness renderer and system prompt integration
- Phase 4: Final validation, documentation, and cleanup
- consolidate: canonical agents/skills, archive non-canonical


## [v0.21.4] - 2026-05-14
### Miscellaneous
- Cleanup: Remove local artifacts and optimize repository
- Phase 1: Move documentation to docs/ subdirectories
- Phase 2: Consolidate configuration and specs
- Phase 3: Remove root-level duplicate directories
- cleanup: Delete model documentation stubs (content consolidated into docs/architecture/model-optimization.md)


## [v0.21.3] - 2026-05-13
### Miscellaneous
- cleanup: Consolidate model documentation (6 files → docs/architecture/model-optimization.md)
- cleanup: Consolidate protocol documentation (PROTOCOL-QUICK-REFERENCE → PROTOCOL.md, queue-enforcement-* → QUEUE-PROTOCOL.md)
- cleanup: Remove internal process/session documentation (22 files)
- cleanup: Rename architecture files with architectural naming, move to docs/architecture/ and docs/guides/
- cleanup: Update cross-references to renamed/deleted documentation files


## [v0.21.2] - 2026-05-13
### Miscellaneous
- cleanup: Remove PHASE-* implementation stage documentation (51 files)
- cleanup: Remove archive/ directory (historical session notes)
- cleanup: Remove artifacts/ directory (historical DELEGATE/HANDBACK metadata)
- cleanup: Remove operational data & update .gitignore
- cleanup: Remove orchestration/ documentation duplicates (49 .md files, keep .py source)


## [v0.21.1] - 2026-05-10
### Changed
- Remove runtime logs from tracking

### Miscellaneous
- cleanup: Remove legacy root-level markdown files
- sanitize: Complete removal of company service references
- sanitize: Fix remaining personal paths and company references
- sanitize: Remove personal paths and company-specific references


## [v0.21.0] - 2026-05-10
### Added
- Complete Phase 1 infrastructure skills implementation

### Testing
- fix subprocess.Popen mock leak in TestConcurrentInvocations

### Documentation
- Update README with consolidated documentation structure

### Miscellaneous
- Merge: Sync with GitHub and prepare for cleanup
- consolidate: Move root markdown files to organized docs structure


## [v0.20.7] - 2026-05-09
### Fixed
- add run_poll_cycle() method to OrchestratorAgent
- fix criterion matching for 'without error' and 'vulnerab*' patterns; add 'decision' to config description
- recreate bin/run-automation-controller.sh entrypoint script

### Testing
- fix test_pre_commit_hook_exists path detection
- update test_queue_manager_state_transitions to use QueueManager.get_incoming_queue_dir()


## [v0.20.6] - 2026-05-09
### Changed
- remove stale src/docs/AGENTS.md per LF standard

### Testing
- agents-md-location

### Documentation
- add comprehensive design documents from research phase
- add queue-management skill to Phase 2 tasks
- add repo-init skill task to TODO.md


## [v0.20.5] - 2026-05-09
### Changed
- optimize repository structure - move AGENTS.md, models.yaml, and config to src/

### Documentation
- add comprehensive audit final summary
- add comprehensive implementation TODO.md with all phases and dependencies
- add repository structure documentation and architecture decisions

### Miscellaneous
- cleanup: remove unnecessary tracked directories and archive files


## [v0.20.4] - 2026-05-09
### Fixed
- update test_model_resolver.py import to use new src.orchestration.agents path

### Changed
- consolidate repository structure
- move CLEANUP-SECURITY-LOG.md to docs/, fix test_model_resolver import

### Documentation
- Add comprehensive security cleanup log for PII removal

### Miscellaneous
- Week 4: Complete protocol documentation and finalization


## [v0.20.3] - 2026-05-09
### Miscellaneous
- Week 3: Implement 70–79 gray-zone manual review gate
- Week 4: Complete protocol documentation and finalization


## [v0.20.2] - 2026-05-09
### Miscellaneous
- Week 1: Implement protocol pre-flight validation system
- Week 2: Implement routing & metrics system
- Week 3: Implement 70–79 gray-zone manual review gate for Lead Engineer oversight


## [v0.20.1] - 2026-05-09
### Miscellaneous
- Consolidation: Principal Engineer review & team engineering baseline
- Protocol review complete: quality gates, validation, and architecture design
- Week 1: Implement protocol pre-flight validation system


## [v0.20.0] - 2026-05-09
### Added
- consolidate engineer skills and create shared quality baseline

### Documentation
- integrate dog-food philosophy into README

### Miscellaneous
- Fix three blocking validation issues


## [v0.19.0] - 2026-05-03
### Added
- implement full-cycle quality gates with dog-food philosophy
- implement session-id based queue partitioning for Orchestrator

### Documentation
- integrate dog-food philosophy into README


## [v0.18.6] - 2026-05-03
### Documentation
- consolidate session artifacts into README.md

### Miscellaneous
- Phase 5 Pure Orchestrator Refactor COMPLETE: 90+ tests, zero business logic
- Phase 6 Model Centralization COMPLETE: 63/63 tests passing, all 6 phases delivered


## [v0.18.5] - 2026-05-03
### Miscellaneous
- Phase 3 Quality Gates Integration COMPLETE: 3-layer validation with 158/158 tests passing
- Phase 4 Queue Enforcement Middleware COMPLETE: 38/38 tests, ORCHESTRATOR-FIRST enforced
- Phase 5 Pure Orchestrator Refactor COMPLETE: 90+ tests, zero business logic


## [v0.18.4] - 2026-05-03
### Miscellaneous
- Orchestrator polling cycle: 8 tasks delegated and completed successfully
- Phase 1 Continuous Polling Automation COMPLETE: AutomationController with 32/32 tests passing
- Phase 2 Continuous Polling Automation COMPLETE: Production integration with 19/19 tests passing


## [v0.18.3] - 2026-05-03
### Miscellaneous
- Add pre-commit hook: prevent external script regression
- Orchestrator polling cycle: 8 tasks delegated and completed successfully
- Remove deprecated scripts: analyze_usage_trends.py, usage_budget_check.py (violated SPEC constraints)


## [v0.18.2] - 2026-05-03
### Miscellaneous
- Fix SPEC.md line 604: Remove 'trivial fixes' exception (contradicts line 112)
- Fix SPEC.md lines 218 & 113: Define external systems; prohibit direct queue writes
- Fix model names to use dot notation for Copilot CLI compatibility


## [v0.18.1] - 2026-05-03
### Miscellaneous
- Fix model names to use dot notation for Copilot CLI compatibility
- Implement TODO.md-based agent autonomy model and remove co-author trailer requirement
- Principal Engineer Final Quality Review: Fix SPEC violations and documentation


## [v0.18.0] - 2026-05-02
### Added
- enable make install for fresh system bootstrap

### Miscellaneous
- Consolidate build system: single 'make install' target
- Remove all Orchestrator script implementations - only AGENTS.md definition remains


## [v0.17.2] - 2026-05-02
### Miscellaneous
- Implement Orchestrator task delegation: move_task() and invoke_agent()
- Remove all Orchestrator script implementations - only AGENTS.md definition remains
- Update TODO.md with Phase 5.10.1 enforcement tasks


## [v0.17.1] - 2026-05-02
### Changed
- remove direct Python implementations, defer to SKILLs

### Documentation
- add Queue State Transitions and Agent Invocation SKILLs to orchestration/SKILLS.md

### Miscellaneous
- Revert "feat: implement Orchestrator agent invocation workflow"


## [v0.17.0] - 2026-05-02
### Added
- implement Orchestrator agent invocation workflow
- implement task routing and delegation logging in Orchestrator

### Miscellaneous
- Revert "feat: implement Orchestrator agent invocation workflow"


## [v0.16.0] - 2026-05-02
### Added
- implement Orchestrator continuous polling loop with signal handling

### Fixed
- Orchestrator polls ~/.copilot/queue/ instead of artifacts/queue/

### Documentation
- close SPEC loopholes and add deprecation notice


## [v0.15.1] - 2026-05-02
### Documentation
- close SPEC loopholes and add deprecation notice

### Miscellaneous
- CRITICAL: remove ALL external scripts and cron jobs - SPEC enforcement
- CRITICAL: remove scanner.py files with subprocess - SPEC violation


## [v0.15.0] - 2026-05-02
### Added
- implement Orchestrator with RED-GREEN TDD

### Miscellaneous
- enforce: remove external scripts, ensure Makefile SPEC compliance
- queue: move completed orchestrator tasks to done/


## [v0.14.0] - 2026-05-02
### Added
- implement Orchestrator with RED-GREEN TDD

### Miscellaneous
- Implement Orchestrator agent with comprehensive TDD testing
- queue: add Orchestrator task with idle timeout failsafe


## [v0.13.3] - 2026-05-02
### Documentation
- enforce Orchestrator-first execution model in SPEC
- enhance Orchestrator SKILL specification in orchestration/SKILLS.md

### Miscellaneous
- queue: three tasks for Orchestrator-first spec enforcement (AGENTS only)


## [v0.13.2] - 2026-05-02
### Documentation
- update TODO.md with Phase 5.10 completion status

### Miscellaneous
- observability: capture orchestrator execution traces and metrics
- queue: three tasks for Orchestrator-first spec enforcement (AGENTS only)


## [v0.13.1] - 2026-05-02
### Documentation
- Extract and document current implementation specification (Phase 5.10)
- establish Orchestrator-first as canonical execution model
- queue spec extraction and validation tasks via DELEGATE


## [v0.13.0] - 2026-05-02
### Added
- Phase 5.10 Objective 2 - span capture & indexing via AGENTS SKILLS only

### Documentation
- queue spec extraction and validation tasks via DELEGATE

### Miscellaneous
- build: generate dist/ with full roles and skills


## [v0.12.4] - 2026-05-01
### Fixed
- include skills/ and models.json in distribution renders
- remove --delete flag from rsync to preserve extra files during updates
- remove Red-Green TDD enforcement from documentation


## [v0.12.3] - 2026-05-01
### Fixed
- remove --delete flag from rsync to preserve extra files during updates

### Changed
- update installation scripts with smart rsync-based updates

### Documentation
- add comprehensive installation and documentation status review


## [v0.12.2] - 2026-05-01
### Changed
- simplify to queue-based delegation with Orchestrator as harness agent

### Documentation
- add queue integration summary for quick reference
- update README to reflect queue-based architecture and installation instructions


## [v0.12.1] - 2026-05-01
### Changed
- implement queue-based orchestration with mandatory Red-Green TDD
- make install the default target, remove install-all
- simplify to queue-based delegation with Orchestrator as harness agent


## [v0.12.0] - 2026-04-30
### Added
- add platform-specific install scripts for ~/.claude/ and ~/.copilot/

### Documentation
- add comprehensive installation guide for platform-specific harnesses
- add workflow diagram section to README


## [v0.11.1] - 2026-04-30
### Documentation
- add comprehensive workflow diagram with example flow and DELEGATE/HANDBACK protocol
- add quick reference guide for agentic engineers workflow
- add workflow diagram section to README


## [v0.11.0] - 2026-04-30
### Added
- add consolidated Quality Orchestrator agent

### Changed
- Restore all original agents from orchestration/agents/ (no changes, no removals)
- remove superseded quality-gate-orchestrator-agent (consolidated into quality-orchestrator)


## [v0.10.0] - 2026-04-30
### Added
- Complete agentic-engineers phases 6.1, 7, 8 + integration framework
- rename enforcement→renderer, add Copilot+Claude render targets

### Changed
- Restore all original agents from orchestration/agents/ (no changes, no removals)


## [v0.9.0] - 2026-04-29
### Added
- Phase 6 Infrastructure Complete + Automated Spec Review System

### Fixed
- copy files into ~/.github/ instead of symlinking

### Miscellaneous
- Session 2026-04-29: Complete Summary - Specification Extraction, Validation, Phase 6 Implementation Setup


## [v0.8.1] - 2026-04-29
### Miscellaneous
- Phase 6 Implementation Infrastructure: Agent Patterns, Testing Framework, Reference Implementations
- Phase 6 Kickoff: Spec Extraction, Validation, Implementation Roadmap
- Session 2026-04-29: Complete Summary - Specification Extraction, Validation, Phase 6 Implementation Setup


## [v0.8.0] - 2026-04-28
### Added
- Quality Gate Orchestrator activator + OpenTelemetry telemetry schema
- implement 5 core agents (Orchestrator + 4 sub-agents + Model Engineer)

### Documentation
- Phase 5.10 completion summary - architecture ready for testing
- comprehensive feedback loop architecture and Phase 5.10-7 roadmap
- integration guide + updated TODO status


## [v0.7.0] - 2026-04-28
### Added
- Week 2 implementation - 7 agent skills complete

### Fixed
- delete out-of-band quality-gate-orchestration.sh

### Documentation
- Add artifact storage documentation and Week 1 Principal delegation
- Add refactoring summary and progress record

### Miscellaneous
- artifacts: Week 2 completion - 7 engineer HANDBACK records


## [v0.6.0] - 2026-04-28
### Added
- Create Week 2 engineer delegation tasks (7 agents)
- Week 1 Principal Engineer designs 7 agent specifications

### Documentation
- Add Week 2 implementation roadmap and engineer delegation guide

### Miscellaneous
- audit: Comprehensive architecture compliance review (CRITICAL FINDINGS)
- plan: 4-week architecture remediation via agentic-engineers


## [v0.5.0] - 2026-04-28
### Added
- Add CloudWatch integration to quality-gate-orchestration.sh
- Add CloudWatch setup script for monitoring infrastructure
- Monitoring & Continuous Improvement framework

### Documentation
- Add comprehensive monitoring documentation

### Miscellaneous
- MAJOR: Phase 5.10 architectural correction - agent-based orchestration


## [v0.4.1] - 2026-04-28
### Documentation
- Add Phase 5.8 final completion summary
- Add Phase 5.8 session summary
- Add Phase 5.8f comprehensive testing report
- Add quality gates quick reference guide for developers
- add comprehensive SDLC orchestrator and agent flow diagrams


## [v0.4.0] - 2026-04-28
### Added
- Quality gate orchestration integration framework
- add 12 Phase 5 Quality Engineer + Self-Healing skills (implementation complete)
- complete Phase 5 Quality Engineer framework (13 skills + master orchestrator)

### Documentation
- add Phase 5 completion summary - all 13 skills complete
- add quick-reference index and navigation guide


## [v0.3.1] - 2026-04-27
### Documentation
- add Phase 5.1 Quality Engineer + Self-Healing Architecture Design
- add complete Phase 5 skill specifications for implementation
- add executive summary
- add orchestrator status report
- create orchestration briefs for 5 parallel skill-building tracks


## [v0.3.0] - 2026-04-27
### Added
- Add spec-extract Copilot Skill
- Phase 3 complete - Skill implementation and documentation
- add 'need your help' voice phrase for user input scenarios
- add engineer-execution and implementation-workflow skills
- add plan-iterate multi-stage expert review pattern


## [v0.2.0] - 2026-04-27
### Added
- add ERS configuration, CICD monitoring, and voice notification skills
- add cleanup & consolidation skill for post-task maintenance
- add planning-standard enforcement and update skills index

### Documentation
- document optimized 60s polling for all 8 ERS services
- update documentation for enforcement consolidation and monitoring improvements


## [v0.1.0] - 2026-04-26
### Added
- Add safe install with backup and restore
- Initialize agentic-engineers as standalone repository

### Changed
- Shift to explicit loading model (no auto-init)
- consolidate {service-name} into agentic-engineers/enforcement

### Documentation
- Add installation guide for ~/.agents/ setup
