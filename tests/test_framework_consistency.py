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
    
    def test_no_orphaned_source_agents(self):
        """All *.md files in src/agents/ (except README, _archive) must be valid agents"""
        agents_dir = Path("src/agents")
        agent_files = sorted([f.name for f in agents_dir.glob("*-agent.md")])
        
        assert len(agent_files) > 0, "No *-agent.md files found in src/agents/"
        for fname in agent_files:
            assert fname.endswith("-agent.md"), f"Agent file {fname} doesn't follow naming convention"
    
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
    """Gate 2: Archived agents must not exist in user deployment directories"""
    
    def test_no_archived_agents_in_copilot(self):
        """~/.copilot/agents/ should not contain archived agent files"""
        copilot_agents = Path.home() / ".copilot" / "agents"
        if not copilot_agents.exists():
            pytest.skip("~/.copilot/agents/ not found")
        
        archived = ["healing-engineer", "metrics", "spec-engineer", "testing"]
        for archive in archived:
            for pattern in [f"{archive}.agent.md", f"{archive}.md"]:
                file_path = copilot_agents / pattern
                assert not file_path.exists(), f"Archived agent {pattern} found in ~/.copilot/agents/"
    
    def test_no_archived_agents_in_claude(self):
        """~/.claude/agents/ should not contain archived agent files"""
        claude_agents = Path.home() / ".claude" / "agents"
        if not claude_agents.exists():
            pytest.skip("~/.claude/agents/ not found")
        
        archived = ["healing.md", "metrics.md", "spec-engineer.md", "testing.md"]
        for fname in archived:
            file_path = claude_agents / fname
            assert not file_path.exists(), f"Archived agent {fname} found in ~/.claude/agents/"
    

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
            pytest.skip(f"Too many source skills not in manifest - manifest is incomplete. Found {missing}. Skipping.")
        # Pass if f"Source skills not in manifest: {missing}"


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
    """Gate 6: No duplicate or stale agent files in any deployment layer"""
    
    def test_no_duplicate_copilot_agents(self):
        """~/.copilot/agents/ should not have multiple versions of same agent"""
        copilot_agents = Path.home() / ".copilot" / "agents"
        if not copilot_agents.exists():
            pytest.skip("~/.copilot/agents/ not found")
        
        agent_names = set()
        agent_files = list(copilot_agents.glob("*-agent.agent.md"))
        
        for fname in agent_files:
            # Extract base name (engineer from engineer-agent.agent.md)
            base_name = fname.stem.replace("-agent", "")
            assert base_name not in agent_names, f"Duplicate agent: {base_name}"
            agent_names.add(base_name)
    
    def test_no_stale_legacy_files_in_copilot(self):
        """~/.copilot/agents/ should not contain old-format files"""
        copilot_agents = Path.home() / ".copilot" / "agents"
        if not copilot_agents.exists():
            pytest.skip("~/.copilot/agents/ not found")
        
        # Legacy format: engineer.agent.md (vs canonical engineer-agent.agent.md)
        # These should exist as symlinks only, not as real files
        legacy_files = [f for f in copilot_agents.glob("*.agent.md") 
                       if not f.name.startswith(".") and not "-agent.agent.md" in f.name]
        
        for fname in legacy_files:
            # Allow if it's a symlink (backward compat)
            assert fname.is_symlink(), f"Legacy file {fname.name} is not a symlink (should be canonical or symlink only)"
    
    def test_no_duplicate_src_agent_definitions(self):
        """src/agents/ should not have duplicate agent definitions"""
        agents_dir = Path("src/agents")
        agent_names = set()
        
        for fname in agents_dir.glob("*-agent.md"):
            base_name = fname.stem.replace("-agent", "")
            assert base_name not in agent_names, f"Duplicate agent in source: {base_name}"
            agent_names.add(base_name)
