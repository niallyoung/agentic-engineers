#!/usr/bin/env python3
"""Render agentic-engineers into a Codex-compatible local harness layout.

Codex-native surfaces used by this renderer:
  - ~/.codex/AGENTS.md
  - ~/.codex/config.toml
  - ~/.codex/agents/*.toml
  - ~/.agents/skills/<skill>/SKILL.md

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


DOC_SENTINEL = "# managed by agentic-engineers render-codex.py; do not edit directly"
CONFIG_SENTINEL = "# managed by agentic-engineers render-codex.py"
SKILL_MARKER = ".agentic-engine-codex"
AGENT_MANIFEST = ".agentic-engine-codex"

CHEAP_CODEX_MODEL = "gpt-5.4-mini"
STRONG_CODEX_MODEL = "gpt-5.5"


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


def parse_agents_table(agents_md: Path) -> dict[str, dict[str, str]]:
    if not agents_md.is_file():
        return {}
    result: dict[str, dict[str, str]] = {}
    in_table = False
    for line in agents_md.read_text(encoding="utf-8").splitlines():
        if "| Role |" in line and "| Model |" in line and "| Effort |" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("|---"):
            continue
        if in_table and not line.strip().startswith("|"):
            break
        if not in_table:
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 6 or not cells[1] or cells[1] == "Role":
            continue
        role = re.sub(r"\*+", "", cells[1]).strip().lower().replace(" ", "-")
        model = re.sub(r"\*+", "", cells[2]).strip()
        effort = re.sub(r"\*+", "", cells[3]).strip().lower()
        description = re.sub(r"\*+", "", cells[5]).strip()
        if role and model and effort:
            result[role] = {
                "model": model,
                "effort": effort,
                "description": description,
            }
    return result


def copy_skill(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", ".DS_Store", "__pycache__"}}

    shutil.copytree(src, dst, ignore=ignore)
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
        effort = docs_meta.get("effort") or str(agent.frontmatter.get("effort") or "medium")
        description = (
            docs_meta.get("description")
            or str(agent.frontmatter.get("description") or "")
            or agent.body.strip().splitlines()[0]
        )
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
- Prefer Orchestrator-first routing. Do not bypass the Orchestrator unless the user explicitly asks for direct specialist work.
- Return concise HANDBACK-style results with status, deliverables, verification, residual risks, and metrics when available.
- Do not invent queue work when the queue is empty.
- When independent work can be parallelized, summarize what can safely fan out and what must remain sequential.
- You are not alone in the codebase. Preserve user changes and other agents' changes; never revert work you did not make.

## Protocol Metadata

- role: {meta["role"]}
- accepts: {accepts_text}
- returns: {returns_text}
- intended_model: {meta["model"]}
- reasoning_effort: {meta["reasoning"]}

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
                "nickname_candidates = []",
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
`~/.agents/skills/`.

## Operating Model

- Orchestrator-first: route broad user work through the `orchestrator` custom agent.
- Structured protocol: use DELEGATE YAML for assigned work and HANDBACK YAML for results.
- Cheap-first routing: Orchestrator and Engineer use `{CHEAP_CODEX_MODEL}`; planning,
  review, security, quality, and model optimization use `{STRONG_CODEX_MODEL}`.
- Parallelize independent work, but keep git history, migrations, and same-file edits coordinated.
- Pause for genuine product/security decisions. Do not invent work when the queue is empty.

## Codex Usage

Codex custom agents are spawned only when explicitly requested. For example:

```text
Use the agentic-engineers orchestrator. Create DELEGATEs for this work, spawn
specialist agents where independent, wait for HANDBACKs, then summarize status.
```

## Queue Convention

Use `~/.agentic-engineers/{{session-id}}/codex/queue/` for Codex queue partitions
with `incoming/`, `processing/`, `done/`, and `failed/` states. Queue writes must
go through the queue-management skill when available.
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
            if "gpt-5.2" in text or "gpt-5.3-codex" in text:
                errors.append(f"{path.name} uses deprecated Codex model")
        if not (self.codex_home / "AGENTS.md").is_file():
            errors.append("missing AGENTS.md")
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
    parser.add_argument("--repo-root", dest="repo_root_flag")
    parser.add_argument("--dest", dest="codex_home_flag")
    parser.add_argument("--skills-root", dest="skills_root")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root_flag or args.repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    codex_home = Path(args.codex_home_flag or args.codex_home or Path.home() / ".codex").expanduser().resolve()
    skills_root = Path(args.skills_root).expanduser().resolve() if args.skills_root else codex_home / "skills"

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
