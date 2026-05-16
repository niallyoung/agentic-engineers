"""
Tests for Bug 2 fix: Premature mkdir in __init__

Verifies that PiDevRenderer does not create directories in __init__,
and that mkdir is deferred to render_all() only.
"""

import pytest
from pathlib import Path
import sys
import importlib.util

# Import render-pi-dev.py using importlib (handles hyphens in filename)
renderer_path = Path(__file__).parent.parent / "renderer" / "scripts" / "render-pi-dev.py"
spec = importlib.util.spec_from_file_location("render_pi_dev", renderer_path)
render_pi_dev_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_pi_dev_module)
PiDevRenderer = render_pi_dev_module.PiDevRenderer


class TestPrematureMkdir:
    """Tests for premature mkdir bug fix"""
    
    def test_init_does_not_create_directory(self, tmp_path):
        """Constructor must not create agent_dir"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        
        # agent_dir should NOT exist after construction
        assert not renderer.agent_dir.exists(), (
            f"agent_dir {renderer.agent_dir} was created by __init__ — "
            "this is the premature mkdir bug"
        )
    
    def test_status_does_not_create_directory(self, tmp_path):
        """--status on clean system must not create agent_dir"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        renderer.status()
        
        assert not renderer.agent_dir.exists(), (
            "status() created agent_dir — should be read-only"
        )
    
    def test_status_reports_not_installed_on_clean_system(self, tmp_path, capsys):
        """--status on clean system must report 'Not installed', not false positive"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        rc = renderer.status()
        
        captured = capsys.readouterr()
        assert "Not installed" in captured.out or rc == 1, (
            "status() returned false positive on clean system"
        )
    
    def test_uninstall_does_not_create_directory(self, tmp_path):
        """--uninstall on clean system must not create agent_dir"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        renderer.uninstall()
        
        assert not renderer.agent_dir.exists(), (
            "uninstall() created agent_dir on clean system"
        )
    
    def test_render_all_creates_directory(self, tmp_path):
        """render_all() must create agent_dir (install operation)"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        # Create minimal source files
        for f in ["SYSTEM.md", "AGENTS.md", "settings.json", "pi.yml", "SUB_AGENT_SETUP.md"]:
            if f.endswith(".md"):
                (src / f).write_text(f"# {f}\n")
            elif f.endswith(".json"):
                (src / f).write_text('{"model": "test"}')
            else:
                (src / f).write_text("version: 1\n")
        
        renderer = PiDevRenderer(str(src), str(dest))
        renderer.render_all()
        
        assert renderer.agent_dir.exists(), (
            "render_all() did not create agent_dir — install broken"
        )
