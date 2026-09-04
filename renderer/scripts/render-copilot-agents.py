#!/usr/bin/env python3
"""
Copilot CLI Agent Renderer
Converts src/agents/*.md to dist/copilot/agents/*.agent.md with Copilot CLI spec compliance
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml


def _dump_scalar_field(key: str, value: str) -> str:
    """Render a single "key: value" YAML mapping entry via yaml.safe_dump(),
    deliberately avoiding yaml.dump()'s bare-scalar code path (see call site
    in render_agent() for why: it appends a stray '...' document-end marker
    for any plain scalar that doesn't need quoting). safe_dump({key: value})
    goes through YAML's mapping-emission path instead, which never emits a
    document terminator for a single key. Returns the line(s) with the
    trailing newline stripped, ready to embed inside a hand-built frontmatter
    block; long values may wrap across a continuation line indented two
    spaces, which is valid YAML for a plain scalar and re-parses to the same
    single-line string.
    """
    dumped = yaml.safe_dump({key: value}, default_flow_style=False, allow_unicode=True)
    return dumped.rstrip("\n")


class CopilotAgentRenderer:
    """Renders source agent definitions to Copilot CLI agent profiles"""
    
    # Sidecar manifest listing the agent base-names this renderer manages, so we
    # can detect (and refuse to overwrite) a user's own foreign agent files.
    # Mirrors the marker/manifest approach used by render-claude.sh.
    MANIFEST_NAME = ".agentic-engine-copilot"

    def __init__(self, src_dir: str, dest_dir: str):
        self.src_dir = Path(src_dir)
        self.dest_dir = Path(dest_dir)

        # Ensure destination exists
        self.dest_dir.mkdir(parents=True, exist_ok=True)

        self.manifest_path = self.dest_dir / self.MANIFEST_NAME
        # Names previously managed by us (from a prior install). Used to decide
        # whether an existing dest file is ours (safe to overwrite) or foreign.
        self.managed_names = self._load_manifest()

    def _load_manifest(self) -> set:
        names = set()
        if self.manifest_path.is_file():
            for line in self.manifest_path.read_text().splitlines():
                name = line.strip()
                if name:
                    names.add(name)
        return names
    
    def extract_frontmatter(self, content: str) -> Tuple[Dict[str, str], str]:
        """Extract YAML frontmatter and body from markdown"""
        # Match frontmatter: --- at start, YAML, --- separator
        match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if not match:
            raise ValueError("File must start with YAML frontmatter (---)")

        yaml_block = match.group(1)
        body = match.group(2)

        # Parse YAML using yaml.safe_load (supports folded scalars and complex types)
        frontmatter = yaml.safe_load(yaml_block) or {}
        if not isinstance(frontmatter, dict):
            raise ValueError("Frontmatter must be a YAML mapping")

        return frontmatter, body
    
    def validate_frontmatter(self, frontmatter: Dict[str, str]) -> None:
        """Ensure required YAML fields are present"""
        required = ['name', 'description', 'model']
        missing = [f for f in required if f not in frontmatter]
        
        if missing:
            raise ValueError(f"Missing required frontmatter fields: {missing}")
    
    def render_agent(self, src_file: Path) -> str:
        """Render a single source agent to Copilot CLI format.

        Returns "rendered" on success, or "skipped-foreign" when the destination
        file already exists and was not created by us (no manifest entry) — so a
        user's own agent file is never silently overwritten.
        """

        with open(src_file, 'r') as f:
            content = f.read()

        # Extract and validate
        frontmatter, body = self.extract_frontmatter(content)
        self.validate_frontmatter(frontmatter)

        # Build output filename: engineer.md → engineer.agent.md
        agent_name = src_file.stem
        dest_file = self.dest_dir / f"{agent_name}.agent.md"

        # Foreign-file protection: if the dest exists but we have a manifest that
        # does NOT list this agent, it belongs to the user — do not overwrite it.
        # (When no manifest exists yet, treat existing files as ours for a clean
        #  first install, matching the dist-rsync behavior this replaces.)
        if (
            dest_file.exists()
            and self.manifest_path.is_file()
            and agent_name not in self.managed_names
        ):
            print(f"⚠️  Skipping {agent_name}.agent.md — foreign (not managed by us)")
            return "skipped-foreign"
        
        # Protocol declaration: pass through machine-readable capability keys so
        # the harness can detect DELEGATE/HANDBACK protocol support.
        def _as_inline_array(value):
            if isinstance(value, list):
                return "[" + ", ".join(value) + "]"
            return value

        protocol_lines = []
        if frontmatter.get('accepts'):
            protocol_lines.append(f"accepts: {_as_inline_array(frontmatter['accepts'])}")
        if frontmatter.get('returns'):
            protocol_lines.append(f"returns: {_as_inline_array(frontmatter['returns'])}")
        role_val = frontmatter.get('role') or agent_name
        protocol_lines.append(f"role: {role_val}")
        protocol_block = "\n".join(protocol_lines)

        # Rebuild with clean frontmatter (spec-compliant). Render the description
        # via _dump_scalar_field() rather than a bare yaml.dump(description) —
        # yaml.dump() of a bare string hits YAML's plain-scalar-document code
        # path, which appends a trailing '...\n' document-end marker for any
        # value that does NOT need quoting (most plain-English descriptions).
        # .strip() only removes whitespace, not the literal '...' text, so it
        # was leaking into the frontmatter as a stray mid-block YAML document
        # terminator. safe_dump({'description': value}) instead renders a
        # "description: value" mapping entry, which never hits that code path.
        description = frontmatter.get('description', '')
        output = f"""---
name: {frontmatter['name']}
{_dump_scalar_field('description', description)}
model: {frontmatter['model']}
{protocol_block}
---

{body}"""
        
        # Write to destination
        with open(dest_file, 'w') as f:
            f.write(output)

        print(f"✅ Rendered: {src_file.name} → {dest_file.name}")
        return "rendered"
    
    def render_all(self) -> int:
        """Render all source agents"""

        if not self.src_dir.exists():
            print(f"❌ Source directory not found: {self.src_dir}")
            return 1

        # Get all .md agent definition files
        agent_files = list(self.src_dir.glob('*.md'))
        if not agent_files:
            print(f"❌ No agent definitions found in {self.src_dir}")
            return 1

        print(f"🎨 Rendering {len(agent_files)} agents from {self.src_dir}")
        print(f"📁 Output: {self.dest_dir}\n")

        rendered = 0
        skipped = 0
        errors = 0
        newly_managed = set()

        for src_file in sorted(agent_files):
            try:
                status = self.render_agent(src_file)
                if status == "rendered":
                    rendered += 1
                    newly_managed.add(src_file.stem)
                elif status == "skipped-foreign":
                    skipped += 1
            except Exception as e:
                print(f"❌ Error rendering {src_file.name}: {e}")
                errors += 1

        # Prune orphaned managed agents BEFORE overwriting the manifest:
        # self.managed_names still holds the PREVIOUS run's manifest here.
        current_source_names = {f.stem for f in agent_files}
        self._prune_orphaned_agents(current_source_names)

        # Persist the manifest of names we manage so future installs/uninstalls
        # can distinguish our files from the user's. Keep any previously-managed
        # names whose source agent still exists (they were rendered this run).
        if newly_managed:
            self._write_manifest(newly_managed)

        print("\n✅ Rendering complete!")
        print(f"   {rendered} agents rendered, {skipped} skipped (foreign), {errors} errors")

        if errors > 0:
            return 1

        return 0

    def _prune_orphaned_agents(self, current_source_names: set) -> list:
        """Remove managed agent files whose source agent was since renamed
        or deleted from the source directory.

        Mirrors prune_orphaned_agents() in renderer/lib/render-lib.sh (the
        bash twin used by render-claude.sh/render-opencode.sh), adapted for
        this renderer's manifest-only trust model: render_agent()'s foreign-
        file guard already treats manifest membership as the ours-vs-foreign
        boundary (a dest file is refused only when it exists AND is NOT
        listed in self.managed_names, the manifest loaded at __init__ time —
        i.e. BEFORE this run). By that same construction, every name in
        self.managed_names is one we installed, so if its source has since
        disappeared it is safe to prune without any separate per-file marker.

        Unconditionally removes (no dry-run mode) and always prints a report
        line, mirroring prune_orphaned_skills()'s wording convention.
        """
        pruned = []
        for name in sorted(self.managed_names):
            if name in current_source_names:
                continue
            # Defend against a tampered/corrupted manifest line before it is
            # ever used to build a deletion path (LOW1 — path traversal
            # hardening): a name like "../../x" must never reach unlink().
            # Same safe-charset check as uninstall() below.
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                print(f"⚠️  Skipping invalid manifest entry (unsafe name): {name}")
                continue
            dest_file = self.dest_dir / f"{name}.agent.md"
            if dest_file.exists():
                dest_file.unlink()
                pruned.append(name)
        if pruned:
            print(f"🧹 pruned {len(pruned)} orphaned managed agent(s): {', '.join(pruned)}")
        else:
            print("🧹 pruned 0 orphaned managed agent(s)")
        return pruned

    def _write_manifest(self, managed_names: set) -> None:
        """Write the sidecar manifest listing the agent base-names we manage."""
        content = "\n".join(sorted(managed_names)) + "\n"
        self.manifest_path.write_text(content)

    def uninstall(self) -> int:
        """Remove only the agent files we manage (per the manifest), then the
        manifest itself. Foreign/user agent files are never touched."""
        if not self.manifest_path.is_file():
            print(f"ℹ️  No manifest at {self.manifest_path} — nothing to uninstall")
            return 0
        removed = 0
        for name in sorted(self.managed_names):
            # Defend against a tampered manifest: only simple base-names.
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                print(f"⚠️  Skipping invalid manifest entry: {name}")
                continue
            dest_file = self.dest_dir / f"{name}.agent.md"
            if dest_file.exists():
                dest_file.unlink()
                removed += 1
        self.manifest_path.unlink()
        print(f"✅ Removed {removed} managed agent(s)")
        return 0

def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="render-copilot-agents.py",
        description="Render agentic-engineers source agents for the Copilot CLI",
    )
    parser.add_argument("src_dir", help="Source agents directory (src/agents)")
    parser.add_argument(
        "dest_dir",
        nargs="?",
        default=os.path.expanduser("~/.copilot/agents"),
        help="Destination agents directory (default: ~/.copilot/agents)",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove managed agents instead of rendering",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None):
    # Previously this indexed sys.argv[1:] directly, so a bare invocation died
    # with an unhandled IndexError and no usage message. argparse mirrors
    # render-codex.py and prints usage on a missing argument instead.
    args = parse_args(argv if argv is not None else sys.argv[1:])
    uninstall = args.uninstall

    src_dir = args.src_dir
    dest_dir = args.dest_dir

    # Get absolute paths
    repo_root = Path(__file__).parent.parent.parent  # ../../ from scripts/
    if Path(src_dir).is_absolute():
        src_path = Path(src_dir).resolve()
    else:
        src_path = (repo_root / src_dir).resolve()
    dest_path = Path(dest_dir).expanduser().resolve()

    print(f"\n{'='*60}")
    print("Copilot CLI Agent Renderer")
    print(f"{'='*60}\n")

    renderer = CopilotAgentRenderer(str(src_path), str(dest_path))

    if uninstall:
        return renderer.uninstall()

    exit_code = renderer.render_all()

    if exit_code == 0:
        print("✅ All agents ready for Copilot CLI!")
        print(f"📍 Location: {dest_path}")
        print("\nUsage in Copilot CLI:")
        print("  /agent                      # Select agent interactively")
        print("  copilot --agent=engineer    # Explicit selection")
        print("  Use the security-engineer   # Auto-inference in prompts")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
