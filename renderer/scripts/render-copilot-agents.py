#!/usr/bin/env python3
"""
Copilot CLI Agent Renderer
Converts src/agents/*.md to dist/copilot/agents/*.agent.md with Copilot CLI spec compliance
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Tuple

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

        # Parse YAML manually. Supports `key: value` scalars and block lists:
        #   key:
        #     - item1
        #     - item2
        # Block-list values are stored as Python lists; scalars as strings.
        frontmatter = {}
        lines = yaml_block.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # Skip blank lines and comments at column 0.
            if not stripped or stripped.startswith('#'):
                i += 1
                continue
            # Only treat column-0 `key:` lines as new keys.
            if re.match(r'^[A-Za-z0-9_]+:', line) and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if value:
                    frontmatter[key] = value
                else:
                    # Possible block list — collect following `  - item` lines.
                    items = []
                    j = i + 1
                    while j < len(lines):
                        nxt = lines[j]
                        m = re.match(r'^[ \t]+-[ \t]*(.*)$', nxt)
                        if m:
                            items.append(m.group(1).strip())
                            j += 1
                        elif nxt.strip() == '':
                            j += 1
                        else:
                            break
                    frontmatter[key] = items if items else ''
                    i = j
                    continue
            i += 1

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

        # Rebuild with clean frontmatter (spec-compliant)
        output = f"""---
name: {frontmatter['name']}
description: {frontmatter['description']}
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
        
        # Get all .md files except README files
        all_files = list(self.src_dir.glob('*.md'))
        agent_files = [f for f in all_files if f.name != 'README.md' and not f.name.endswith('README.md')]
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

        # Persist the manifest of names we manage so future installs/uninstalls
        # can distinguish our files from the user's. Keep any previously-managed
        # names whose source agent still exists (they were rendered this run).
        if newly_managed:
            self._write_manifest(newly_managed)

        print(f"\n✅ Rendering complete!")
        print(f"   {rendered} agents rendered, {skipped} skipped (foreign), {errors} errors")

        if errors > 0:
            return 1

        return 0

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

def main():
    # Parse arguments. Optional trailing --uninstall removes managed agents.
    args = [a for a in sys.argv[1:] if a != "--uninstall"]
    uninstall = "--uninstall" in sys.argv[1:]

    if len(args) < 1:
        # Default: operate on ~/.copilot/agents
        src_dir = 'src/agents'
        dest_dir = os.path.expanduser('~/.copilot/agents')
    else:
        src_dir = args[0]
        dest_dir = args[1] if len(args) > 1 else os.path.expanduser('~/.copilot/agents')

    # Get absolute paths
    repo_root = Path(__file__).parent.parent.parent  # ../../ from scripts/
    if Path(src_dir).is_absolute():
        src_path = Path(src_dir).resolve()
    else:
        src_path = (repo_root / src_dir).resolve()
    dest_path = Path(dest_dir).expanduser().resolve()

    print(f"\n{'='*60}")
    print(f"Copilot CLI Agent Renderer")
    print(f"{'='*60}\n")

    renderer = CopilotAgentRenderer(str(src_path), str(dest_path))

    if uninstall:
        return renderer.uninstall()

    exit_code = renderer.render_all()

    if exit_code == 0:
        print(f"✅ All agents ready for Copilot CLI!")
        print(f"📍 Location: {dest_path}")
        print(f"\nUsage in Copilot CLI:")
        print(f"  /agent                      # Select agent interactively")
        print(f"  copilot --agent=engineer    # Explicit selection")
        print(f"  Use the security-engineer   # Auto-inference in prompts")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
