#!/usr/bin/env python3
"""Render agentic-engineers into a Codex-compatible local harness layout.

Codex-native surfaces used by this renderer:
  - ~/.codex/AGENTS.md
  - ~/.codex/config.toml
  - ~/.codex/agentic-engineers-orchestrator.config.toml
  - ~/.codex/agents/*.toml
  - ~/.codex/skills/<skill>/SKILL.md

The renderer is marker-aware and refuses to overwrite foreign user files.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Canonical Agent Roster table parser — the Python twin of parse_agents_md()
# in renderer/lib/render-lib.sh. Pinned together by
# tests/test_agents_table_parity.py. See renderer/lib/agents_table.py for the
# full table-format contract.
_LIB_DIR = Path(__file__).resolve().parent.parent / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
from agents_table import parse_agents_table as _parse_agents_table_rows  # type: ignore


DOC_SENTINEL = "# managed by agentic-engineers render-codex.py; do not edit directly"
CONFIG_SENTINEL = "# managed by agentic-engineers render-codex.py"
SKILL_MARKER = ".agentic-engine-codex"
AGENT_MANIFEST = ".agentic-engine-codex"
ORCHESTRATOR_PROFILE = "agentic-engineers-orchestrator"

CHEAP_CODEX_MODEL = "gpt-5.4-mini"
STRONG_CODEX_MODEL = "gpt-5.5"


ROLE_ROUTING_TABLE = """- orchestrator: intake, routing, task management, synthesis, metrics.
- engineer: bounded implementation with a clear plan and low/medium complexity.
- senior-engineer: complex implementation, diagnosis, or work needing judgment.
- lead-engineer: planning review, integration review, and medium architectural guidance.
- quality-engineer: post-change quality gates, test gaps, regression review.
- security-engineer: defensive security review and vulnerability analysis.
- principal-engineer: cross-system architecture and high-impact design choices.
- model-engineer: model/cost/routing analysis and A/B experiment design."""


STRICT_ORCHESTRATOR_MODE = """- The root Codex session is an orchestrator only; it does not implement user tasks itself.
- Convert every substantive user request into one or more DELEGATE YAML blocks and hand them to subagents.
- If there is no pending or in-flight delegated work, do not invent work; report idle or ask for the next task.
- Root-thread work is limited to intake, routing, dispatch coordination, Git coordination, final verification, and synthesis of HANDBACKs.
- Never resolve a user task in the root session when a specialist role exists."""


DELEGATE_GRAMMAR = """When the user starts a message with `delegate:` or `DELEGATE:`, treat it as an explicit request to use Codex subagents.

Parse the text after the prefix as semicolon-separated tasks; also accept newline bullets or numbered lists as task separators. For each task:
1. Assign a stable task_id such as `codex-001`, `codex-002`, preserving user wording in `scope`.
2. Choose the narrowest appropriate custom agent using the routing table.
3. Build a canonical DELEGATE payload with the fields needed for protocol validation: `handoff_type: DELEGATE`, `task_id`, `agent`, `skill`, `model`, `effort`, `scope`, `context`, `plan`, and `success_criteria`.
4. Spawn independent tasks in parallel where file ownership and dependencies do not conflict; keep same-file edits coordinated.
5. Wait for all spawned agents needed for the current turn, then synthesize a final HANDBACK-style summary.

If a task is ambiguous, route discovery/planning to `lead-engineer` or `senior-engineer` instead of guessing. If there is no pending or in-flight delegated work, do not invent work."""


HANDBACK_CONTRACT = """Return results in this shape whenever you were spawned with a DELEGATE:

```yaml
handoff_type: HANDBACK
task_id: <same task_id>
agent: <your agent name>
status: success | failure | partial | blocked | escalate
summary: <short outcome>
deliverables:
  - <files changed, findings, or artifacts>
verification:
  - <commands run or checks performed>
risks:
  - <remaining risks, conflicts, or unknowns>
next_steps:
  - <follow-up work, if any>
metrics:
  model: <model if known>
  effort: <reasoning effort if known>
```

Keep the result concise, include file paths for code changes, and explicitly say when verification was not run."""


AGENT_NAME_TO_REGISTRY_ROLE = {
    "orchestrator": "general_orchestrator",
    "engineer": "engineer",
    "senior-engineer": "senior_engineer",
    "lead-engineer": "lead_engineer",
    "quality-engineer": "quality_engineer",
    "principal-engineer": "principal_engineer",
    "security-engineer": "security_engineer",
    "model-engineer": "model_engineer",
}


CODEX_MODEL_BY_ROLE = {
    "general_orchestrator": CHEAP_CODEX_MODEL,
    "engineer": CHEAP_CODEX_MODEL,
    "senior_engineer": STRONG_CODEX_MODEL,
    "lead_engineer": STRONG_CODEX_MODEL,
    "quality_engineer": STRONG_CODEX_MODEL,
    "principal_engineer": STRONG_CODEX_MODEL,
    "security_engineer": STRONG_CODEX_MODEL,
    "model_engineer": STRONG_CODEX_MODEL,
}


REASONING_BY_EFFORT = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "max": "high",
}


@dataclass(frozen=True)
class AgentSource:
    name: str
    path: Path
    frontmatter: dict[str, Any]
    body: str


def _use_color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m" if _use_color() else text


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m" if _use_color() else text


def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m" if _use_color() else text


def toml_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\t", "\\t")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def toml_multiline(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""\n{escaped.rstrip()}\n"""'


def slugify_agent_name(name: str) -> str:
    return name.strip().lower().replace("_", "-").replace(" ", "-")


def extract_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path} must start with YAML frontmatter")
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} frontmatter must be a mapping")
    return data, match.group(2)


def list_source_agents(src_agents: Path) -> list[AgentSource]:
    agents: list[AgentSource] = []
    for path in sorted(src_agents.glob("*-agent.md")):
        frontmatter, body = extract_frontmatter(path)
        name = slugify_agent_name(str(frontmatter.get("name") or path.stem.removesuffix("-agent")))
        agents.append(AgentSource(name=name, path=path, frontmatter=frontmatter, body=body))
    return agents


def list_source_skills(src_skills: Path) -> list[Path]:
    return sorted(path for path in src_skills.iterdir() if (path / "SKILL.md").is_file())


def warn_on_local_only_codex_skills(repo_root: Path, skills_root: Path) -> list[str]:
    """Return warnings for local Codex skills missing from the repo source tree."""
    warnings: list[str] = []
    src_skills_dir = repo_root / "src" / "skills"
    if not skills_root.exists() or not src_skills_dir.exists():
        return warnings

    source_names = {path.name for path in list_source_skills(src_skills_dir)}
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        if skill_dir.name.startswith("."):
            continue
        if skill_dir.name not in source_names:
            warnings.append(
                f"Local-only Codex skill '{skill_dir.name}' exists in {skills_root} "
                f"but not in {src_skills_dir}"
            )
    return warnings


def parse_agents_table(agents_md: Path) -> dict[str, dict[str, str]]:
    """Codex-local adapter: canonical row list -> dict keyed by kebab-case role.

    The actual parsing lives in renderer/lib/agents_table.py — the canonical
    Python parser, pinned to the canonical bash parser (parse_agents_md in
    renderer/lib/render-lib.sh) by tests/test_agents_table_parity.py. This
    wrapper only reshapes the row list into the dict-by-role lookup shape
    this renderer's call sites expect (render-copilot-agents.py has no
    equivalent shared-parser call site: it does not parse this table at all
    — it takes each agent's model straight from that agent's own
    src/agents/*-agent.md frontmatter). Effort is lowercased for the lookups
    below (REASONING_BY_EFFORT keys); the canonical table already stores
    effort lowercase, so this is a no-op in practice and kept only to
    preserve the prior contract.
    """
    return {
        row["role"]: {
            "model": row["model"],
            "effort": row["effort"].lower(),
            "description": row["description"],
        }
        for row in _parse_agents_table_rows(agents_md)
    }


def copy_skill(src: Path, dst: Path) -> None:
    # Nested-precedence contract (docs/RENDERING.md): no src skill ships its
    # own AGENTS.md, so any AGENTS.md found under an already-installed skill
    # dir is user-authored. rmtree()+copytree() would otherwise wipe it on
    # every re-render (unlike rsync --delete + --exclude in the other
    # renderers, this copy path has no equivalent "leave it alone" flag) —
    # so stash and restore any such files verbatim around the copy.
    preserved: dict[Path, bytes] = {}
    if dst.exists():
        for path in dst.rglob("AGENTS.md"):
            preserved[path.relative_to(dst)] = path.read_bytes()
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = {".git", ".DS_Store", "__pycache__", ".coverage", ".pytest_cache", "tests"}
        return {name for name in names if name in ignored or name.endswith(".pyc")}

    shutil.copytree(src, dst, ignore=ignore)
    for rel_path, content in preserved.items():
        target = dst / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (dst / SKILL_MARKER).write_text("managed by agentic-engineers render-codex.py\n", encoding="utf-8")


class CodexRenderer:
    def __init__(self, repo_root: Path, codex_home: Path, skills_root: Path):
        self.repo_root = repo_root
        self.codex_home = codex_home
        self.skills_root = skills_root
        self.src_agents = repo_root / "src" / "agents"
        self.src_skills = repo_root / "src" / "skills"
        self.src_agents_md = repo_root / "src" / "AGENTS.md"
        self.agents_dir = codex_home / "agents"
        self.manifest = self.agents_dir / AGENT_MANIFEST
        self.canonical = parse_agents_table(self.src_agents_md)

    def managed_names(self) -> set[str]:
        if not self.manifest.is_file():
            return set()
        return {line.strip() for line in self.manifest.read_text(encoding="utf-8").splitlines() if line.strip()}

    def metadata_for(self, agent: AgentSource) -> dict[str, str]:
        docs_meta = self.canonical.get(agent.name, {})
        role = AGENT_NAME_TO_REGISTRY_ROLE.get(agent.name, agent.name.replace("-", "_"))
        effort = docs_meta.get("effort", "medium")
        description = docs_meta.get("description", "")
        return {
            "role": role,
            "effort": effort,
            "description": description,
            "model": CODEX_MODEL_BY_ROLE.get(role, STRONG_CODEX_MODEL),
            "reasoning": REASONING_BY_EFFORT.get(effort, "medium"),
        }

    def agent_instructions(self, agent: AgentSource, meta: dict[str, str]) -> str:
        accepts = agent.frontmatter.get("accepts") or []
        returns = agent.frontmatter.get("returns") or []
        accepts_text = ", ".join(accepts) if isinstance(accepts, list) else str(accepts)
        returns_text = ", ".join(returns) if isinstance(returns, list) else str(returns)
        return f"""# Agentic Engineers Role: {agent.name}

You are a Codex custom subagent rendered from agentic-engineers.

## Harness Contract

- Follow the repository's AGENTS.md and the agentic-engineers DELEGATE/HANDBACK protocol.
- Prefer Orchestrator-first routing.
- The Orchestrator does not do implementation work itself; it decomposes tasks and delegates them.
- Never bypass the Orchestrator for root-thread task execution.
- When spawned with a DELEGATE, execute only that scope and return the HANDBACK YAML shape below.
- Do not invent work when there is nothing pending or in flight.
- When independent work can be parallelized, summarize what can safely fan out and what must remain sequential.
- You are not alone in the codebase. Preserve user changes and other agents' changes; never revert work you did not make.

## Protocol Metadata

- role: {meta["role"]}
- accepts: {accepts_text}
- returns: {returns_text}
- intended_model: {meta["model"]}
- reasoning_effort: {meta["reasoning"]}

## HANDBACK Contract

{HANDBACK_CONTRACT}

## Source Role Definition

{agent.body.rstrip()}
"""

    def render_agent(self, agent: AgentSource, managed_before: set[str]) -> bool:
        dst = self.agents_dir / f"{agent.name}.toml"
        if dst.exists() and self.manifest.exists() and agent.name not in managed_before:
            print(f"  {_yellow('WARNING')} skipping agent {agent.name} - foreign at {dst}")
            return False
        if dst.exists() and not self.manifest.exists():
            print(f"  {_yellow('WARNING')} skipping agent {agent.name} - pre-existing file with no manifest")
            return False

        meta = self.metadata_for(agent)
        instructions = self.agent_instructions(agent, meta)
        content = "\n".join(
            [
                CONFIG_SENTINEL,
                f"name = {toml_string(agent.name)}",
                f"description = {toml_string(meta['description'])}",
                f"model = {toml_string(meta['model'])}",
                f"model_reasoning_effort = {toml_string(meta['reasoning'])}",
                f"developer_instructions = {toml_multiline(instructions)}",
                "",
            ]
        )
        dst.write_text(content, encoding="utf-8")
        return True

    def write_agents_doc(self) -> None:
        dst = self.codex_home / "AGENTS.md"
        if dst.exists() and not dst.read_text(encoding="utf-8", errors="ignore").startswith(DOC_SENTINEL):
            print(f"  {_yellow('WARNING')} skipping AGENTS.md - foreign at {dst}")
            return
        dst.write_text(
            f"""{DOC_SENTINEL}

# Agentic Engineers Framework - Codex Integration

This Codex installation is managed by agentic-engineers. The framework renders
specialist Codex custom agents under `agents/` and reusable skills under
`~/.codex/skills/`.

For the intended startup path, launch Codex with:

```bash
codex --profile {ORCHESTRATOR_PROFILE} --sandbox workspace-write --ask-for-approval on-request
```

## Operating Model

- Orchestrator-only: the root Codex session acts as dispatcher, not worker.
- Structured protocol: use DELEGATE YAML for assigned work and HANDBACK YAML for results.
- Cheap-first routing: Orchestrator and Engineer use `{CHEAP_CODEX_MODEL}`; planning,
  review, security, quality, and model optimization use `{STRONG_CODEX_MODEL}`.
- Parallelize independent work, but keep git history, migrations, and same-file edits coordinated.
- Pause for genuine product/security decisions. Do not invent work when there is nothing pending or in flight.
{STRICT_ORCHESTRATOR_MODE}

## Codex Usage

Codex custom agents are spawned only when explicitly requested. For example:

```text
delegate: inspect the renderer for missing Codex startup integration; review
the generated custom-agent HANDBACK contract; update docs for the new launch flow
```

## Delegate Prefix

{DELEGATE_GRAMMAR}

## Role Routing

{ROLE_ROUTING_TABLE}

## HANDBACK Contract

{HANDBACK_CONTRACT}

## Dispatch Model

Every DELEGATE is passed directly as a spawned subagent's prompt; the HANDBACK
returns synchronously as that spawn's result, in-context. There is no queue to
poll or write — the Codex session transcript is the durable record of every
DELEGATE/HANDBACK pair.
""",
            encoding="utf-8",
        )

    def orchestrator_profile_instructions(self) -> str:
        return f"""# Agentic Engineers Orchestrator Startup Profile

You are operating as the agentic-engineers Orchestrator for this Codex session.

## Startup Behavior

- Treat broad engineering work as Orchestrator-owned intake, routing, coordination, and synthesis.
- Do not do implementation work in the root session.
- Every substantive task must be converted to one or more DELEGATEs and handed to subagents.
- Use Codex subagents whenever there is work to do; the root session coordinates instead of executing.
- Prefer the rendered custom agents in `~/.codex/agents/` over built-in generic agents when a role matches.
- Keep the root thread responsible for git coordination, integration decisions, final verification, and final user-facing synthesis.
- Do not spawn recursive subagents unless the user explicitly requests nested delegation.

## Strict Orchestrator Mode

{STRICT_ORCHESTRATOR_MODE}

## Delegate Prefix

{DELEGATE_GRAMMAR}

## Role Routing

{ROLE_ROUTING_TABLE}

## HANDBACK Contract

{HANDBACK_CONTRACT}
"""

    def write_orchestrator_profile(self) -> None:
        dst = self.codex_home / f"{ORCHESTRATOR_PROFILE}.config.toml"
        if dst.exists() and not dst.read_text(encoding="utf-8", errors="ignore").startswith(CONFIG_SENTINEL):
            print(f"  {_yellow('WARNING')} skipping {dst.name} - foreign at {dst}")
            return

        dst.write_text(
            f"""{CONFIG_SENTINEL}
# Startup profile for agentic-engineers Orchestrator mode.
# Select with:
#   codex --profile {ORCHESTRATOR_PROFILE}

model = "{CHEAP_CODEX_MODEL}"
model_reasoning_effort = "low"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "cached"
developer_instructions = {toml_multiline(self.orchestrator_profile_instructions())}

[features]
multi_agent = true

[sandbox_workspace_write]
network_access = false

[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800
""",
            encoding="utf-8",
        )

    def write_config(self) -> None:
        dst = self.codex_home / "config.toml"
        out = dst
        if dst.exists() and not dst.read_text(encoding="utf-8", errors="ignore").startswith(CONFIG_SENTINEL):
            out = self.codex_home / "agentic-engineers.config.toml"
            print(f"  {_yellow('WARNING')} foreign config.toml found - managed reference written to {out.name}")

        out.write_text(
            f"""{CONFIG_SENTINEL}
# Merge these settings into config.toml if this file was written as a reference.

model = "{CHEAP_CODEX_MODEL}"
model_reasoning_effort = "medium"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "cached"

[features]
multi_agent = true

[sandbox_workspace_write]
network_access = false

[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800

# Autopilot-style self-tests can use:
#   codex exec --sandbox workspace-write --ask-for-approval never "<task>"
#
# True YOLO/full access is:
#   codex --dangerously-bypass-approvals-and-sandbox
# Use that only inside disposable, externally isolated environments.
""",
            encoding="utf-8",
        )

    def install(self) -> int:
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.skills_root.mkdir(parents=True, exist_ok=True)

        print(f"Writing Codex config -> {self.codex_home}")
        self.write_agents_doc()
        self.write_config()
        self.write_orchestrator_profile()

        print(f"Rendering Codex custom agents -> {self.agents_dir}")
        managed_before = self.managed_names()
        managed_now: list[str] = []
        for agent in list_source_agents(self.src_agents):
            if self.render_agent(agent, managed_before):
                managed_now.append(agent.name)
                print(f"  {_green('OK')} agent {agent.name}")
        self.manifest.write_text("\n".join(sorted(managed_now)) + "\n", encoding="utf-8")

        print(f"Rendering Codex skills -> {self.skills_root}")
        count_s = 0
        for skill in list_source_skills(self.src_skills):
            dst = self.skills_root / skill.name
            if dst.exists() and not (dst / SKILL_MARKER).exists():
                print(f"  {_yellow('WARNING')} skipping skill {skill.name} - foreign")
                continue
            copy_skill(skill, dst)
            count_s += 1
        print(f"{_green('OK')} Rendered {len(managed_now)} agent(s), {count_s} skill(s)")
        return 0

    def uninstall(self) -> int:
        removed_agents = 0
        if self.manifest.is_file():
            for name in sorted(self.managed_names()):
                if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                    print(f"  {_yellow('WARNING')} invalid manifest entry skipped: {name}")
                    continue
                path = self.agents_dir / f"{name}.toml"
                if path.exists():
                    path.unlink()
                    removed_agents += 1
            self.manifest.unlink()

        removed_skills = 0
        for skill in list_source_skills(self.src_skills):
            dst = self.skills_root / skill.name
            if (dst / SKILL_MARKER).exists():
                shutil.rmtree(dst)
                removed_skills += 1

        removed_docs = 0
        for path in [
            self.codex_home / "AGENTS.md",
            self.codex_home / "config.toml",
            self.codex_home / "agentic-engineers.config.toml",
            self.codex_home / f"{ORCHESTRATOR_PROFILE}.config.toml",
        ]:
            if path.is_file() and path.read_text(encoding="utf-8", errors="ignore").startswith(
                (DOC_SENTINEL, CONFIG_SENTINEL)
            ):
                path.unlink()
                removed_docs += 1

        print(f"{_green('OK')} Removed {removed_agents} agent(s), {removed_skills} skill(s), {removed_docs} doc/config file(s)")
        return 0

    def status(self) -> int:
        missing = 0
        for path, label in [
            (self.codex_home / "AGENTS.md", "AGENTS.md"),
            (self.codex_home / "config.toml", "config.toml"),
            (self.codex_home / f"{ORCHESTRATOR_PROFILE}.config.toml", f"{ORCHESTRATOR_PROFILE}.config.toml"),
        ]:
            if not path.exists():
                print(f"  {_red('MISSING')} {label}")
                missing += 1
            elif path.read_text(encoding="utf-8", errors="ignore").startswith((DOC_SENTINEL, CONFIG_SENTINEL)):
                print(f"  {_green('OK')} {label}")
            else:
                print(f"  {_yellow('FOREIGN')} {label}")

        managed = self.managed_names()
        for agent in list_source_agents(self.src_agents):
            path = self.agents_dir / f"{agent.name}.toml"
            if not path.exists():
                print(f"  {_red('MISSING')} agent {agent.name}")
                missing += 1
            elif agent.name in managed:
                print(f"  {_green('OK')} agent {agent.name}")
            else:
                print(f"  {_yellow('FOREIGN')} agent {agent.name}")

        for skill in list_source_skills(self.src_skills):
            path = self.skills_root / skill.name
            if not path.exists():
                print(f"  {_red('MISSING')} skill {skill.name}")
                missing += 1
            elif (path / SKILL_MARKER).exists():
                print(f"  {_green('OK')} skill {skill.name}")
            else:
                print(f"  {_yellow('FOREIGN')} skill {skill.name}")
        return 1 if missing else 0

    def validate(self) -> int:
        errors: list[str] = []
        agents = list_source_agents(self.src_agents)
        if not agents:
            errors.append("no source agents found")
        for agent in agents:
            path = self.agents_dir / f"{agent.name}.toml"
            if not path.is_file():
                errors.append(f"missing rendered agent {path}")
                continue
            text = path.read_text(encoding="utf-8")
            for field in ("name =", "description =", "model =", "model_reasoning_effort =", "developer_instructions ="):
                if field not in text:
                    errors.append(f"{path.name} missing {field}")
        if not (self.codex_home / "AGENTS.md").is_file():
            errors.append("missing AGENTS.md")
        else:
            agents_doc = (self.codex_home / "AGENTS.md").read_text(encoding="utf-8")
            for required in (
                "Agentic Engineers Framework - Codex Integration",
                "Orchestrator-only",
                "Delegate Prefix",
                "Dispatch Model",
            ):
                if required not in agents_doc:
                    errors.append(f"AGENTS.md missing {required}")
        profile_path = self.codex_home / f"{ORCHESTRATOR_PROFILE}.config.toml"
        if not profile_path.is_file():
            errors.append(f"missing {ORCHESTRATOR_PROFILE}.config.toml")
        else:
            profile_text = profile_path.read_text(encoding="utf-8")
            if not profile_text.startswith(CONFIG_SENTINEL):
                errors.append(f"{ORCHESTRATOR_PROFILE}.config.toml is foreign or unmanaged")
            for required in (
                "developer_instructions =",
                "Agentic Engineers Orchestrator Startup Profile",
                "Delegate Prefix",
                "multi_agent = true",
            ):
                if required not in profile_text:
                    errors.append(f"{ORCHESTRATOR_PROFILE}.config.toml missing {required}")
        if not (self.codex_home / "config.toml").is_file() and not (
            self.codex_home / "agentic-engineers.config.toml"
        ).is_file():
            errors.append("missing config.toml or agentic-engineers.config.toml")
        expected_skill_count = len(list_source_skills(self.src_skills))
        skill_count = len([p for p in self.skills_root.iterdir() if (p / "SKILL.md").is_file()]) if self.skills_root.exists() else 0
        if skill_count != expected_skill_count:
            errors.append(f"expected {expected_skill_count} rendered skills, found {skill_count}")

        if errors:
            for error in errors:
                print(f"{_red('ERROR')} {error}")
            return 1
        print(f"{_green('OK')} Codex render validated")
        return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render agentic-engineers for Codex")
    parser.add_argument("repo_root", nargs="?", help="Repository root")
    parser.add_argument("codex_home", nargs="?", help="Codex home/output directory")
    parser.add_argument("--skills-root", dest="skills_root")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    codex_home = Path(args.codex_home or Path.home() / ".codex").expanduser().resolve()
    skills_root = (
        Path(args.skills_root).expanduser().resolve()
        if args.skills_root
        else codex_home / "skills"
    )

    for warning in warn_on_local_only_codex_skills(repo_root, skills_root):
        print(_yellow(f"⚠️  {warning}"))

    renderer = CodexRenderer(repo_root, codex_home, skills_root)
    if args.uninstall:
        return renderer.uninstall()
    if args.status:
        return renderer.status()
    if args.validate:
        return renderer.validate()
    return renderer.install()


if __name__ == "__main__":
    raise SystemExit(main())
