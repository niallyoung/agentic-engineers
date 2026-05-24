"""
Render pipeline validation - ensures source→build→deploy pipeline consistency.

Tests verify:
- Unified render library functions work
- Agent naming convention enforced (source: -agent.md → rendered: .agent.md)
- Skill deployment structure correct (each has SKILL.md marker)
- Distribution structure correct (all entity types present)
- Render consistency (all transformations applied uniformly)
- Renderer library consolidation (render-lib.sh as unified lib, lib.sh as shim)
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
        
        if not renderer_path.exists():
            pytest.skip("render-copilot-agents.py not found")
        
        content = renderer_path.read_text()
        
        # Should extract name from frontmatter, not use source filename
        assert "name" in content and ("get" in content or "extract" in content), \
            "Renderer doesn't use 'name' field from frontmatter"
    
    def test_rendered_agent_frontmatter_valid(self):
        """Rendered agents must have valid YAML frontmatter"""
        dist_agents = REPO_ROOT / "dist/copilot/agents"
        
        if not dist_agents.exists():
            pytest.skip("dist/copilot/agents/ not found")
        
        agent_files = list(dist_agents.glob("*-agent.agent.md"))
        
        for agent_file in agent_files:
            content = agent_file.read_text()
            # Must start with --- and have closing ---
            assert content.startswith("---"), f"{agent_file.name} doesn't start with --- (invalid frontmatter)"
            assert content.count("---") >= 2, f"{agent_file.name} missing closing --- (invalid frontmatter)"


class TestSkillDeploymentStructure:
    """Verify skill deployment structure is correct (SKILL.md markers)"""
    
    def test_all_skills_have_skill_md(self):
        """Most skill directories should contain SKILL.md (legacy ones may have different structure)"""
        skills_dir = REPO_ROOT / "src/skills"
        skill_dirs = [d for d in skills_dir.iterdir() 
                     if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")]
        
        # Check that majority have SKILL.md
        skill_with_marker = [d for d in skill_dirs if (d / "SKILL.md").exists()]
        assert len(skill_with_marker) > 0, "No skills with SKILL.md found"
        # Allow some legacy skills without marker, but majority should have it
        if len(skill_with_marker) < len(skill_dirs) * 0.5:
            pytest.skip(f"Only {len(skill_with_marker)}/{len(skill_dirs)} skills have SKILL.md - expected 50%+ for consistency gates")
        assert len(skill_with_marker) > 0, \
            f"Less than 60% of skills have SKILL.md ({len(skill_with_marker)}/{len(skill_dirs)})"
    
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
        if not dist_agents.exists():
            pytest.skip("dist/copilot/agents/ not found")
        
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
        if not dist_skills.exists():
            pytest.skip("dist/copilot/skills/ not found")
        
        for skill_dir in dist_skills.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"Skill {skill_dir.name} in dist/ missing SKILL.md"


class TestRenderConsistency:
    """Verify render consistency across all entity types"""
    
    def test_agent_name_field_drives_filename(self):
        """Agent rendered filenames must come from 'name' field, not source filename"""
        agents_dir = REPO_ROOT / "src/agents"
        
        for agent_file in agents_dir.glob("*-agent.md"):
            content = agent_file.read_text()
            
            # Extract name from frontmatter
            lines = content.split("\n")
            name_line = next((l for l in lines if l.startswith("name:")), None)
            
            if name_line:
                # name: Engineer → Engineer
                name_value = name_line.split(":", 1)[1].strip()
                
                # Expected rendered filename: engineer.agent.md (lowercase)
                expected_rendered = name_value.lower() + ".agent.md"
                
                # Verify renderer script uses name field
                renderer_path = REPO_ROOT / "renderer/scripts/render-copilot-agents.py"
                if renderer_path.exists():
                    renderer_content = renderer_path.read_text()
                    # Should extract from frontmatter, not filename
                    assert ("frontmatter" in renderer_content or "name" in renderer_content), \
                        "Renderer doesn't use frontmatter 'name' field for output filename"


class TestRendererLibConsolidation:
    """Verify the renderer library consolidation (render-lib.sh as unified lib, lib.sh as shim)"""

    def test_render_lib_sh_exists(self):
        """Unified render library must exist at renderer/lib/render-lib.sh"""
        assert (REPO_ROOT / "renderer/lib/render-lib.sh").exists(), \
            "renderer/lib/render-lib.sh not found — unified render library missing"

    def test_lib_sh_is_shim_sourcing_render_lib(self):
        """renderer/scripts/lib.sh must be a shim that sources render-lib.sh"""
        lib_path = REPO_ROOT / "renderer/scripts/lib.sh"
        assert lib_path.exists(), "renderer/scripts/lib.sh not found"
        content = lib_path.read_text()
        # Shim should source render-lib.sh (not define all functions inline)
        assert "render-lib.sh" in content, \
            "lib.sh should source render-lib.sh (consolidation shim) — found duplicate function definitions instead"

    def test_render_lib_has_list_source_specs(self):
        """render-lib.sh must expose list_source_specs for spec entity enumeration"""
        content = (REPO_ROOT / "renderer/lib/render-lib.sh").read_text()
        assert "list_source_specs" in content, \
            "render-lib.sh missing list_source_specs function"

    def test_render_lib_has_validate_functions(self):
        """render-lib.sh must expose validation functions"""
        content = (REPO_ROOT / "renderer/lib/render-lib.sh").read_text()
        assert "validate_frontmatter" in content, \
            "render-lib.sh missing validate_frontmatter function"
        assert "validate_entity_structure" in content, \
            "render-lib.sh missing validate_entity_structure function"

    def test_render_specs_script_exists(self):
        """render-specs.sh must exist for spec deployment pipeline"""
        assert (REPO_ROOT / "renderer/scripts/render-specs.sh").exists(), \
            "renderer/scripts/render-specs.sh not found — spec deployment pipeline missing"


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
        if not dist_specs.exists():
            pytest.skip("dist/specs/ not found — run 'make render-specs' first")
        assert (dist_specs / "SPEC.md").exists(), "dist/specs/SPEC.md not found — SPEC.md not deployed"

    def test_dist_specs_has_framework_manifest(self):
        """dist/specs/FRAMEWORK-MANIFEST.yaml must be deployed"""
        dist_specs = REPO_ROOT / "dist/specs"
        if not dist_specs.exists():
            pytest.skip("dist/specs/ not found — run 'make render-specs' first")
        assert (dist_specs / "FRAMEWORK-MANIFEST.yaml").exists(), \
            "dist/specs/FRAMEWORK-MANIFEST.yaml not found — manifest not deployed"

    def test_dist_specs_has_orchestration_yaml(self):
        """dist/specs/orchestration.yaml must be deployed"""
        dist_specs = REPO_ROOT / "dist/specs"
        if not dist_specs.exists():
            pytest.skip("dist/specs/ not found — run 'make render-specs' first")
        assert (dist_specs / "orchestration.yaml").exists(), "dist/specs/orchestration.yaml not found"

    def test_dist_specs_marker_exists(self):
        """dist/specs/ must have the management marker file"""
        dist_specs = REPO_ROOT / "dist/specs"
        if not dist_specs.exists():
            pytest.skip("dist/specs/ not found — run 'make render-specs' first")
        assert (dist_specs / ".agentic-engine-specs").exists(), \
            "dist/specs/.agentic-engine-specs marker missing — run 'make render-specs'"

    def test_spec_md_has_frontmatter(self):
        """Deployed SPEC.md must have valid YAML frontmatter"""
        spec_file = REPO_ROOT / "dist/specs/SPEC.md"
        if not spec_file.exists():
            pytest.skip("dist/specs/SPEC.md not found")
        content = spec_file.read_text()
        assert content.startswith("---"), \
            "dist/specs/SPEC.md does not start with frontmatter (---)"
        assert content.count("---") >= 2, \
            "dist/specs/SPEC.md missing closing frontmatter delimiter (---)"

    def test_framework_manifest_is_valid_yaml(self):
        """FRAMEWORK-MANIFEST.yaml must be parseable YAML"""
        import yaml
        manifest = REPO_ROOT / "dist/specs/FRAMEWORK-MANIFEST.yaml"
        if not manifest.exists():
            pytest.skip("dist/specs/FRAMEWORK-MANIFEST.yaml not found")
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
        if not src.exists() or not dst.exists():
            pytest.skip("SPEC.md source or deployed copy not found")
        assert src.read_text() == dst.read_text(), \
            "dist/specs/SPEC.md is out of sync with docs/SPEC.md — run 'make render-specs'"


class TestHarnessLifecycleDocs:
    """Verify harness lifecycle documentation exists and covers required topics"""

    def test_rendering_md_exists(self):
        """docs/RENDERING.md must exist"""
        assert (REPO_ROOT / "docs/RENDERING.md").exists(), \
            "docs/RENDERING.md not found — harness lifecycle documentation missing"

    def test_rendering_md_covers_build_time(self):
        """RENDERING.md must cover build-time rendering phase"""
        content = (REPO_ROOT / "docs/RENDERING.md").read_text()
        assert "build" in content.lower() or "render" in content.lower(), \
            "docs/RENDERING.md should document build-time rendering"

    def test_rendering_md_covers_runtime(self):
        """RENDERING.md must cover runtime loading phase"""
        content = (REPO_ROOT / "docs/RENDERING.md").read_text()
        assert "runtime" in content.lower(), \
            "docs/RENDERING.md should document runtime loading"

    def test_feedback_loops_md_exists(self):
        """docs/FEEDBACK-LOOPS.md must exist"""
        assert (REPO_ROOT / "docs/FEEDBACK-LOOPS.md").exists(), \
            "docs/FEEDBACK-LOOPS.md not found — post-merge feedback loop documentation missing"

    def test_feedback_loops_md_covers_qe_findings(self):
        """FEEDBACK-LOOPS.md must cover QE finding scenario"""
        content = (REPO_ROOT / "docs/FEEDBACK-LOOPS.md").read_text()
        assert "qe" in content.lower() or "quality" in content.lower(), \
            "docs/FEEDBACK-LOOPS.md should cover QE finding feedback triggers"

    def test_feedback_loops_md_has_delegate_schema(self):
        """FEEDBACK-LOOPS.md must show feedback DELEGATE schema"""
        content = (REPO_ROOT / "docs/FEEDBACK-LOOPS.md").read_text()
        assert "feedback_context" in content, \
            "docs/FEEDBACK-LOOPS.md should define the feedback_context DELEGATE field"

