"""
Automated Skill Standardization Update Engine

Automatically updates skills to standard format while preserving existing content.
Restructures documents, ensures consistency, and adds missing sections.

Requirements:
- Preserve all existing content
- Add missing required sections with templates
- Restructure documents for consistency
- Maintain backwards compatibility
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml
import re
from dataclasses import dataclass


@dataclass
class UpdatedSkill:
    """Represents a skill that has been updated."""
    skill_name: str
    skill_path: Path
    changes_made: List[str]
    content_before: str
    content_after: str
    sections_added: List[str]
    sections_modified: List[str]


class SkillAutoUpdater:
    """Automatically updates skills to standard format."""

    STANDARD_TEMPLATE = """---
name: {name}
description: {description}
license: {license}
compatibility: {compatibility}
metadata:
  author: {author}
  version: "{version}"
  category: {category}
  role: {role}{optional_metadata}
---

{body}"""

    MISSING_SECTIONS = {
        "Integration": """## Integration

{Provide details about how this skill integrates with other components in the agentic-engineers framework. Document inputs, outputs, and dependencies.}""",
        "Configuration": """## Configuration

{Configuration options, environment variables, and customization points for this skill.}""",
        "Examples": """## Examples

{Practical examples of using this skill in real scenarios. Include code snippets and use cases.}""",
    }

    def __init__(self):
        """Initialize the auto-updater."""
        self.updates: List[UpdatedSkill] = []

    def update_skill(self, skill_path: Path) -> Optional[UpdatedSkill]:
        """
        Update a single skill to standard format.

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            UpdatedSkill with details of changes made, or None if no update needed
        """
        if not skill_path.exists():
            return None

        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception:
            return None

        content_before = content

        # Parse existing frontmatter
        frontmatter, body = self._parse_frontmatter(content)
        if frontmatter is None:
            # If parsing fails, try to create basic frontmatter
            frontmatter = {
                "name": skill_path.parent.name,
                "description": "Skill description",
            }
            body = content

        changes_made: List[str] = []
        sections_added: List[str] = []
        sections_modified: List[str] = []

        # Ensure required fields
        if "license" not in frontmatter:
            frontmatter["license"] = "Proprietary"
            changes_made.append("Added default license")

        if "compatibility" not in frontmatter:
            frontmatter["compatibility"] = "agentic-engineers framework"
            changes_made.append("Added default compatibility")

        # Ensure metadata section
        if "metadata" not in frontmatter:
            frontmatter["metadata"] = {}
            changes_made.append("Added metadata section")

        metadata = frontmatter.get("metadata", {})
        if "author" not in metadata:
            metadata["author"] = "agentic-engineers"
            changes_made.append("Added author to metadata")

        if "version" not in metadata:
            metadata["version"] = "1.0"
            changes_made.append("Added version to metadata")

        if "category" not in metadata:
            metadata["category"] = ""
            changes_made.append("Added category field (empty)")

        if "role" not in metadata:
            metadata["role"] = ""
            changes_made.append("Added role field (empty)")

        frontmatter["metadata"] = metadata

        # Add missing sections to body
        body_sections = self._extract_sections(body)

        for section_name, template in self.MISSING_SECTIONS.items():
            if section_name not in body_sections:
                body += f"\n\n{template}"
                sections_added.append(section_name)
                changes_made.append(f"Added missing section: {section_name}")

        # Reconstruct frontmatter
        frontmatter_str = self._reconstruct_frontmatter(frontmatter)

        # Create updated content
        content_after = f"{frontmatter_str}\n{body}"

        # Save updated content
        try:
            skill_path.write_text(content_after, encoding="utf-8")
        except Exception:
            # If write fails, return the proposed changes without saving
            pass

        update = UpdatedSkill(
            skill_name=skill_path.parent.name,
            skill_path=skill_path,
            changes_made=changes_made,
            content_before=content_before,
            content_after=content_after,
            sections_added=sections_added,
            sections_modified=sections_modified,
        )

        self.updates.append(update)
        return update

    def update_all_skills(self, repository_root: Path) -> List[UpdatedSkill]:
        """
        Update all skills in repository to standard format.

        Args:
            repository_root: Root path of repository

        Returns:
            List of UpdatedSkill objects
        """
        skill_files = list(repository_root.glob("**/SKILL.md"))
        self.updates = []

        for skill_file in skill_files:
            self.update_skill(skill_file)

        return self.updates

    def _parse_frontmatter(
        self, content: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parse YAML frontmatter from content.

        Args:
            content: Full file content

        Returns:
            Tuple of (frontmatter_dict, body)
        """
        if not content.startswith("---"):
            return None, content

        lines = content.split("\n")
        end_index = None

        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index is None:
            return None, content

        try:
            frontmatter_str = "\n".join(lines[1:end_index])
            frontmatter = yaml.safe_load(frontmatter_str)
            body = "\n".join(lines[end_index + 1 :]).lstrip()
            return frontmatter, body
        except yaml.YAMLError:
            return None, content

    def _reconstruct_frontmatter(self, frontmatter: Dict[str, Any]) -> str:
        """
        Reconstruct YAML frontmatter string.

        Args:
            frontmatter: Frontmatter dictionary

        Returns:
            Reconstructed YAML frontmatter with --- delimiters
        """
        # Prepare metadata block
        metadata = frontmatter.get("metadata", {})
        optional_metadata = ""

        if metadata.get("schedule"):
            optional_metadata += f'\n  schedule: "{metadata["schedule"]}"'

        if metadata.get("tdd_phase"):
            optional_metadata += f'\n  tdd_phase: {metadata["tdd_phase"]}'

        if metadata.get("allowed_tools"):
            optional_metadata += (
                f'\n  allowed_tools: {yaml.dump(metadata["allowed_tools"]).strip()}'
            )

        frontmatter_content = f"""name: {frontmatter.get('name', '')}
description: >
  {frontmatter.get('description', '')}
license: {frontmatter.get('license', 'Proprietary')}
compatibility: {frontmatter.get('compatibility', 'agentic-engineers framework')}
metadata:
  author: {metadata.get('author', 'agentic-engineers')}
  version: "{metadata.get('version', '1.0')}"
  category: {metadata.get('category', '') or 'general'}
  role: {metadata.get('role', '') or 'engineer'}{optional_metadata}"""

        return f"---\n{frontmatter_content}\n---"

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract markdown sections from content.

        Args:
            content: Markdown content

        Returns:
            Dictionary mapping section names to their content
        """
        sections: Dict[str, str] = {}
        current_section = None
        current_content: List[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def generate_update_report(self) -> Dict[str, Any]:
        """
        Generate update summary report.

        Returns:
            Dictionary with update statistics
        """
        total_updates = len(self.updates)
        total_changes = sum(len(u.changes_made) for u in self.updates)
        avg_changes = total_changes / total_updates if total_updates > 0 else 0

        return {
            "total_skills_updated": total_updates,
            "total_changes_made": total_changes,
            "average_changes_per_skill": avg_changes,
            "skills": [
                {
                    "name": u.skill_name,
                    "path": str(u.skill_path),
                    "changes": u.changes_made,
                    "sections_added": u.sections_added,
                }
                for u in self.updates
            ],
        }
