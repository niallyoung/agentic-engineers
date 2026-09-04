"""
Render pipeline validation - ensures source→build→deploy pipeline consistency.

Tests verify:
- Unified render library functions work
- Agent naming convention enforced (source: -agent.md → rendered: .agent.md)
- Skill deployment structure correct (each has SKILL.md marker)
- Distribution structure correct (all entity types present)
- Render consistency (all transformations applied uniformly)
- Renderer library consolidation (render-lib.sh is the single unified lib;
  the renderer/scripts/lib.sh shim has been deleted)
- Spec deployment pipeline (dist/specs/ deployed and valid)
- Harness lifecycle documentation exists
"""

import pytest
from pathlib import Path

# Use absolute paths anchored to repo root.
# Some tests in the suite call os.chdir() without restoring, which would make
# relative Path("...") lookups fail.  Anchoring to __file__ is safe regardless
# of the current working directory at test execution time.
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module", autouse=True)
def _render_all(render_all):
    """Opt this module in to the session-scoped render (tests/conftest.py).

    Required because the dist/ presence checks below are hard assertions rather
    than skips: without a guaranteed render, a local `make test` would have
    reported them as passing-by-skipping.
    """
    yield


class TestRenderLibrary:
    """Verify unified render library exists and provides required functions"""
    
    def test_render_lib_exists(self):
        lib_path = REPO_ROOT / "renderer/lib/render-lib.sh"
        assert lib_path.exists(), "renderer/lib/render-lib.sh not found"
    
    def test_list_source_skills(self):
        """render-lib.sh should have list_source_skills function"""
        lib_path = REPO_ROOT / "renderer/lib/render-lib.sh"
        content = lib_path.read_text()
        assert "list_source_skills" in content, "list_source_skills function not found in render-lib.sh"
    
    def test_list_source_agents(self):
        """render-lib.sh should have list_source_agents function"""
        lib_path = REPO_ROOT / "renderer/lib/render-lib.sh"
        content = lib_path.read_text()
        assert "list_source_agents" in content, "list_source_agents function not found in render-lib.sh"


class TestAgentNamingConvention:
    """Enforce agent naming convention: src/*-agent.md → rendered/*.agent.md"""
    
    def test_agent_source_files_exist(self):
        agents_dir = REPO_ROOT / "src/agents"
        agent_files = list(agents_dir.glob("*-agent.md"))
        assert len(agent_files) > 0, "No *-agent.md files found in src/agents/"
    
    def test_agent_frontmatter_has_name_field(self):
        """All agents must have 'name:' field in YAML frontmatter"""
        agents_dir = REPO_ROOT / "src/agents"
        
        for agent_file in agents_dir.glob("*-agent.md"):
            content = agent_file.read_text()
            assert "name:" in content, f"{agent_file.name} missing 'name:' in frontmatter"
    
    def test_agent_name_field_matches_source_basename(self):
        """Agent 'name:' field should match source filename (without -agent.md)"""
        agents_dir = REPO_ROOT / "src/agents"
        
        for agent_file in agents_dir.glob("*-agent.md"):
            content = agent_file.read_text()
            
            # Extract name from frontmatter
            lines = content.split("\n")
            name_line = next((l for l in lines if l.startswith("name:")), None)
            if not name_line:
                continue
            
            # name: Engineer
            agent_name = name_line.split(":", 1)[1].strip().lower()
            
            # Source: engineer-agent.md → extract: engineer
            source_name = agent_file.stem.replace("-agent", "").lower()
            
            # They should match (allowing for spacing)
            assert agent_name.replace(" ", "") == source_name.replace(" ", ""), \
                f"{agent_file.name}: name field '{agent_name}' doesn't match source '{source_name}'"
    
    def test_agent_frontmatter_completeness(self):
        """All agents must have required frontmatter fields"""
        agents_dir = REPO_ROOT / "src/agents"
        required_fields = ["name", "description", "model"]
        
        for agent_file in agents_dir.glob("*-agent.md"):
            content = agent_file.read_text()
            for field in required_fields:
                assert f"{field}:" in content, f"{agent_file.name} missing '{field}' in frontmatter"


class TestRenderedAgentNaming:
    """Verify rendered agents follow correct naming convention"""
    
    def test_python_renderer_produces_correct_filenames(self):
        """render-copilot-agents.py must produce *.agent.md files (using name field)"""
        renderer_path = REPO_ROOT / "renderer/scripts/render-copilot-agents.py"
        
        assert renderer_path.exists(), \
            "renderer/scripts/render-copilot-agents.py not found — the copilot renderer is required"

        content = renderer_path.read_text()
        
        # Should extract name from frontmatter, not use source filename
        assert "name" in content and ("get" in content or "extract" in content), \
            "Renderer doesn't use 'name' field from frontmatter"
    
    def test_rendered_agent_frontmatter_valid(self):
        """Rendered agents must have valid YAML frontmatter"""
        dist_agents = REPO_ROOT / "dist/copilot/agents"
        
        assert dist_agents.is_dir(), \
            "dist/copilot/agents/ not found — run 'make render-all'"

        agent_files = list(dist_agents.glob("*-agent.agent.md"))
        
        for agent_file in agent_files:
            content = agent_file.read_text()
            # Must start with --- and have closing ---
            assert content.startswith("---"), f"{agent_file.name} doesn't start with --- (invalid frontmatter)"
            assert content.count("---") >= 2, f"{agent_file.name} missing closing --- (invalid frontmatter)"


class TestSkillDeploymentStructure:
    """Verify skill deployment structure is correct (SKILL.md markers)"""
    
    def test_all_skills_have_skill_md(self):
        """Every skill directory must contain SKILL.md — it is the renderer's entry point.

        This previously skipped when fewer than 50% of skills had SKILL.md, i.e. it
        disabled itself on exactly the condition it exists to catch, and its remaining
        assertion (`> 0`) could not fail while any single skill was well-formed. Post
        SPEC-2026-005 slimdown all 8 skill dirs carry SKILL.md, so this is now exact.
        """
        skills_dir = REPO_ROOT / "src/skills"
        skill_dirs = [d for d in skills_dir.iterdir()
                     if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")]

        assert skill_dirs, "No skill directories found under src/skills/"
        missing = sorted(d.name for d in skill_dirs if not (d / "SKILL.md").exists())
        assert missing == [], f"Skill directories missing SKILL.md: {missing}"
    
    def test_skill_frontmatter_has_required_fields(self):
        """SKILL.md files should have name/title and description"""
        skills_dir = REPO_ROOT / "src/skills"
        
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            content = skill_md.read_text()
            # Accept either 'name:' or 'title:' (legacy variation)
            has_name = "name:" in content or "title:" in content
            has_description = "description:" in content
            
            assert has_name, f"Skill {skill_dir.name}/SKILL.md missing 'name' or 'title'"
            assert has_description, f"Skill {skill_dir.name}/SKILL.md missing 'description'"


class TestDistDeployment:
    """Verify distribution layer (dist/) is correct"""
    
    def test_dist_copilot_agents_exist(self):
        dist_agents = REPO_ROOT / "dist/copilot/agents"
        assert dist_agents.exists(), "dist/copilot/agents/ not found"
        
        agent_files = list(dist_agents.glob("*-agent.agent.md"))
        assert len(agent_files) > 0, "No agents found in dist/copilot/agents/"
    
    def test_dist_agent_files_follow_naming_convention(self):
        """All dist/copilot/agents/*.agent.md files must end with -agent.agent.md"""
        dist_agents = REPO_ROOT / "dist/copilot/agents"
        assert dist_agents.is_dir(), \
            "dist/copilot/agents/ not found — run 'make render-all'"

        for fname in dist_agents.glob("*.agent.md"):
            assert fname.name.endswith("-agent.agent.md"), \
                f"Agent {fname.name} doesn't follow -agent.agent.md convention"
    
    def test_dist_copilot_skills_exist(self):
        dist_skills = REPO_ROOT / "dist/copilot/skills"
        assert dist_skills.exists(), "dist/copilot/skills/ not found"
        
        skill_dirs = [d for d in dist_skills.iterdir() if d.is_dir()]
        assert len(skill_dirs) > 0, "No skill directories found in dist/copilot/skills/"
    
    def test_dist_skill_dirs_have_skill_md(self):
        """All skill directories in dist/ must have SKILL.md"""
        dist_skills = REPO_ROOT / "dist/copilot/skills"
        assert dist_skills.is_dir(), \
            "dist/copilot/skills/ not found — run 'make render-all'"
        
        for skill_dir in dist_skills.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"Skill {skill_dir.name} in dist/ missing SKILL.md"


class TestSpecDeployment:
    """Verify spec deployment pipeline (dist/specs/)"""

    def test_dist_specs_directory_exists(self):
        """dist/specs/ directory must exist after render-specs"""
        dist_specs = REPO_ROOT / "dist/specs"
        assert dist_specs.exists(), \
            "dist/specs/ not found — run 'make render-specs' to generate"

    def test_dist_specs_has_spec_md(self):
        """dist/specs/SPEC.md must be deployed"""
        dist_specs = REPO_ROOT / "dist/specs"
        assert dist_specs.is_dir(), "dist/specs/ not found — run 'make render-all'"
        assert (dist_specs / "SPEC.md").exists(), "dist/specs/SPEC.md not found — SPEC.md not deployed"

    def test_dist_specs_has_framework_manifest(self):
        """dist/specs/FRAMEWORK-MANIFEST.yaml must be deployed"""
        dist_specs = REPO_ROOT / "dist/specs"
        assert dist_specs.is_dir(), "dist/specs/ not found — run 'make render-all'"
        assert (dist_specs / "FRAMEWORK-MANIFEST.yaml").exists(), \
            "dist/specs/FRAMEWORK-MANIFEST.yaml not found — manifest not deployed"

    def test_dist_specs_has_orchestration_yaml(self):
        """dist/specs/orchestration.yaml must be deployed"""
        dist_specs = REPO_ROOT / "dist/specs"
        assert dist_specs.is_dir(), "dist/specs/ not found — run 'make render-all'"
        assert (dist_specs / "orchestration.yaml").exists(), "dist/specs/orchestration.yaml not found"

    def test_dist_specs_marker_exists(self):
        """dist/specs/ must have the management marker file"""
        dist_specs = REPO_ROOT / "dist/specs"
        assert dist_specs.is_dir(), "dist/specs/ not found — run 'make render-all'"
        assert (dist_specs / ".agentic-engine-specs").exists(), \
            "dist/specs/.agentic-engine-specs marker missing — run 'make render-specs'"

    def test_spec_md_has_frontmatter(self):
        """Deployed SPEC.md must have valid YAML frontmatter"""
        spec_file = REPO_ROOT / "dist/specs/SPEC.md"
        assert spec_file.is_file(), "dist/specs/SPEC.md not found — run 'make render-all'"
        content = spec_file.read_text()
        assert content.startswith("---"), \
            "dist/specs/SPEC.md does not start with frontmatter (---)"
        assert content.count("---") >= 2, \
            "dist/specs/SPEC.md missing closing frontmatter delimiter (---)"

    def test_framework_manifest_is_valid_yaml(self):
        """FRAMEWORK-MANIFEST.yaml must be parseable YAML"""
        import yaml
        manifest = REPO_ROOT / "dist/specs/FRAMEWORK-MANIFEST.yaml"
        assert manifest.is_file(), \
            "dist/specs/FRAMEWORK-MANIFEST.yaml not found — run 'make render-all'"
        try:
            data = yaml.safe_load(manifest.read_text())
            assert isinstance(data, dict), "FRAMEWORK-MANIFEST.yaml parsed but is not a dict"
            assert "agents" in data, "FRAMEWORK-MANIFEST.yaml missing 'agents' section"
        except yaml.YAMLError as e:
            pytest.fail(f"FRAMEWORK-MANIFEST.yaml is invalid YAML: {e}")

    def test_spec_source_matches_deployed(self):
        """Deployed SPEC.md must match source docs/SPEC.md"""
        src = REPO_ROOT / "docs/SPEC.md"
        dst = REPO_ROOT / "dist/specs/SPEC.md"
        assert src.is_file(), "docs/SPEC.md not found — the SPEC source is required"
        assert dst.is_file(), "dist/specs/SPEC.md not found — run 'make render-all'"
        assert src.read_text() == dst.read_text(), \
            "dist/specs/SPEC.md is out of sync with docs/SPEC.md — run 'make render-specs'"


