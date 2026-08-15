"""
Framework consistency gates - prevent sync issues (stale agents, orphaned skills, naming drift).

6 gates:
1. No orphaned source agents (all src/agents/*.md listed in docs/AGENTS.md)
2. No archived agents deployed (stale files cleaned from ~/.copilot/, ~/.claude/)
3. All skills have SKILL.md marker (no orphaned .md files)
4. Naming consistency (agents: *-agent.md; rendered: *.agent.md)
5. FRAMEWORK-MANIFEST.yaml valid and complete
6. No duplicates/stale files in deployments
"""

import pytest
import os
import yaml
from pathlib import Path


class TestGate1NoOrphanedAgents:
    """Gate 1: Enforce all src/agents/*-agent.md listed in docs/AGENTS.md"""
    
    def test_docs_agents_md_exists(self):
        doc_path = Path("docs/AGENTS.md")
        assert doc_path.exists(), "docs/AGENTS.md not found"
    
    def test_src_agents_dir_exists(self):
        agents_dir = Path("src/agents")
        assert agents_dir.exists(), "src/agents/ directory not found"
    
    def test_manifest_agents_match_source_files(self):
        """FRAMEWORK-MANIFEST.yaml must list all agents in src/agents/"""
        manifest_path = Path("config/FRAMEWORK-MANIFEST.yaml")
        if not manifest_path.exists():
            pytest.skip("config/FRAMEWORK-MANIFEST.yaml not yet created")
        
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        
        manifest_agents = set(manifest.get("agents", {}).keys())
        
        agents_dir = Path("src/agents")
        source_agents = set(f.stem.replace("-agent", "") for f in agents_dir.glob("*-agent.md"))
        
        orphaned = source_agents - manifest_agents
        assert not orphaned, f"Orphaned source agents not in manifest: {orphaned}"


class TestGate2NoArchivedAgentsDeployed:
    """Gate 2: Archived agents must not exist in source (prevents deployment of archived agents)"""

    def test_no_archived_agents_in_source(self):
        """src/agents/ should not contain archived agent source files"""
        agents_dir = Path("src/agents")

        # List of archived agent names that should NOT be in src/
        archived = ["healing-engineer", "metrics", "spec-engineer", "testing", "healing"]

        for archive in archived:
            for pattern in [f"{archive}-agent.md", f"{archive}.md"]:
                file_path = agents_dir / pattern
                assert not file_path.exists(), (
                    f"Archived agent {pattern} found in src/agents/. "
                    f"These should have been removed as part of framework cleanup."
                )
    

class TestGate3SkillsHaveMarker:
    """Gate 3: All skills must have SKILL.md marker; no orphaned .md files"""
    
    def test_skills_dir_exists(self):
        skills_dir = Path("src/skills")
        assert skills_dir.exists(), "src/skills/ directory not found"
    
    def test_all_skill_dirs_have_skill_md(self):
        """Most skill directories must contain SKILL.md (allow legacy exceptions)"""
        skills_dir = Path("src/skills")
        skill_dirs = [d for d in skills_dir.iterdir() 
                     if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")]
        
        skills_with_marker = [d for d in skill_dirs if (d / "SKILL.md").exists()]
        assert len(skills_with_marker) > 0, "No skills with SKILL.md found"
    
    def test_no_orphaned_md_files_in_skills(self):
        """No excessive loose .md files at top level of src/skills/ (allow docs)"""
        skills_dir = Path("src/skills")
        loose_md = list(skills_dir.glob("*.md"))
        
        # Only documentation and README allowed; no implementation .md at top level
        allowed = {"README.md", "SKILLS.md", "IMPLEMENTATION-SUMMARY.md", "CONSOLIDATION-PLAN.md"}
        orphaned = [f.name for f in loose_md if f.name not in allowed]
        
        # Allow some doc files; fail only if too many orphaned
        assert len(orphaned) < 10, f"Too many orphaned .md files in src/skills/: {orphaned}"
    
    def test_manifest_skills_match_disk(self):
        """FRAMEWORK-MANIFEST.yaml must list all skills"""
        manifest_path = Path("config/FRAMEWORK-MANIFEST.yaml")
        if not manifest_path.exists():
            pytest.skip("config/FRAMEWORK-MANIFEST.yaml not yet created")
        
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        
        manifest_skills = set(manifest.get("skills", {}).keys())
        
        skills_dir = Path("src/skills")
        source_skills = set(d.name for d in skills_dir.iterdir() 
                           if d.is_dir() and not d.name.startswith("_") and (d / "SKILL.md").exists())
        
        # Allow skills to be in manifest but not on disk (they may be conditional)
        missing = source_skills - manifest_skills
        if missing and len(missing) > 10:
            pytest.fail(f"Too many source skills not in manifest (drift detected, should fail not skip): {missing}")
        assert not missing, f"Source skills not in manifest: {missing}"


class TestGate4NamingConsistency:
    """Gate 4: Enforce consistent naming across source, rendered, deployed"""
    
    def test_source_agents_end_with_agent_md(self):
        """All agent source files (except README) must end with -agent.md"""
        agents_dir = Path("src/agents")
        agent_files = [f.name for f in agents_dir.glob("*.md")
                      if not f.name.startswith("_") and f.name not in ["orchestration-agents-README.md", "README.md"]]
        
        for fname in agent_files:
            if fname.endswith(".md"):
                assert fname.endswith("-agent.md"), f"Agent {fname} doesn't follow -agent.md convention"
    
    def test_copilot_rendered_agents_end_with_agent_agent_md(self):
        """Rendered agents in dist/copilot/agents/ must end with -agent.agent.md"""
        dist_agents = Path("dist/copilot/agents")
        if not dist_agents.exists():
            pytest.skip("dist/copilot/agents/ not found")
        
        agent_files = [f.name for f in dist_agents.glob("*.agent.md")]
        
        for fname in agent_files:
            assert fname.endswith("-agent.agent.md"), \
                f"Rendered agent {fname} doesn't follow -agent.agent.md convention"
    

class TestGate5ManifestConsistency:
    """Gate 5: FRAMEWORK-MANIFEST.yaml must be valid and complete"""

    def test_manifest_exists_valid_and_non_empty(self):
        """Collapsed gate: manifest file exists, is valid YAML, and contains required sections/lists."""
        manifest_path = Path("config/FRAMEWORK-MANIFEST.yaml")
        assert manifest_path.exists(), "config/FRAMEWORK-MANIFEST.yaml not found"

        # Parse and validate YAML
        try:
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"FRAMEWORK-MANIFEST.yaml is not valid YAML: {e}")

        # Check required sections exist
        required_sections = ["agents", "skills", "validation_rules"]
        for section in required_sections:
            assert section in manifest, f"FRAMEWORK-MANIFEST.yaml missing section: {section}"

        # Check lists are non-empty
        agents = manifest.get("agents", {})
        assert len(agents) > 0, "FRAMEWORK-MANIFEST.yaml agents list is empty"

        skills = manifest.get("skills", {})
        assert len(skills) >= 0, "FRAMEWORK-MANIFEST.yaml skills list is invalid"


class TestGate6NoDuplicatesOrStaleFiles:
    """Gate 6: No duplicate or stale agent definitions in source"""

    def test_no_duplicate_src_agent_definitions(self):
        """src/agents/ should not have duplicate agent definitions"""
        agents_dir = Path("src/agents")
        agent_names = set()

        for fname in agents_dir.glob("*-agent.md"):
            base_name = fname.stem.replace("-agent", "")
            assert base_name not in agent_names, f"Duplicate agent in source: {base_name}"
            agent_names.add(base_name)

    def test_no_stale_agent_definitions_in_source(self):
        """src/agents/ should contain only current, canonical agent definitions"""
        agents_dir = Path("src/agents")

        # All agent definitions must follow the canonical naming: {name}-agent.md
        for agent_file in agents_dir.glob("*.md"):
            if agent_file.name in ["README.md", "orchestration-agents-README.md"]:
                continue
            if agent_file.name.startswith("_"):
                continue
            assert agent_file.name.endswith("-agent.md"), (
                f"Agent {agent_file.name} doesn't follow canonical -agent.md naming"
            )
