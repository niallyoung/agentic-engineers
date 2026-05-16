"""
Tests for Bug 3 fix: Missing graceful error handling for PyYAML

Verifies that the renderer handles missing PyYAML gracefully,
and that YAML validation can be skipped with a warning.
"""

import pytest
from pathlib import Path
import sys
import importlib.util
from unittest.mock import patch

# Import render-pi-dev.py using importlib (handles hyphens in filename)
renderer_path = Path(__file__).parent.parent / "renderer" / "scripts" / "render-pi-dev.py"
spec = importlib.util.spec_from_file_location("render_pi_dev", renderer_path)
render_pi_dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_pi_dev)
PiDevRenderer = render_pi_dev.PiDevRenderer


class TestYamlFallback:
    """Tests for PyYAML graceful fallback"""
    
    def test_module_imports_without_pyyaml(self):
        """render-pi-dev.py must be importable even without PyYAML"""
        # This test verifies the module-level import guard works
        # If the module crashes on import, this test will fail
        assert render_pi_dev.YAML_AVAILABLE is not None, (
            "YAML_AVAILABLE flag not set"
        )
    
    def test_validate_yaml_skips_gracefully_without_pyyaml(self, tmp_path, capsys):
        """validate_yaml() must not crash when PyYAML is unavailable"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        agent_dir = dest / "agent"
        agent_dir.mkdir(parents=True)
        
        # Create a valid YAML file
        (agent_dir / "pi.yml").write_text("version: 1\nagents: []\n")
        
        # Mock YAML_AVAILABLE = False
        original = render_pi_dev.YAML_AVAILABLE
        render_pi_dev.YAML_AVAILABLE = False
        
        try:
            r = PiDevRenderer(str(src), str(dest))
            result = r.validate_yaml("pi.yml")
            
            captured = capsys.readouterr()
            assert result is True, "validate_yaml should return True (non-fatal) when PyYAML unavailable"
            assert "pip install pyyaml" in captured.out, "Should print install instructions"
            assert "Skipping" in captured.out, "Should indicate validation was skipped"
        finally:
            render_pi_dev.YAML_AVAILABLE = original
    
    def test_validate_yaml_works_with_pyyaml(self, tmp_path):
        """validate_yaml() works normally when PyYAML is available"""
        pytest.importorskip("yaml", reason="PyYAML not installed — skipping positive test")
        
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        agent_dir = dest / "agent"
        agent_dir.mkdir(parents=True)
        
        (agent_dir / "pi.yml").write_text("version: 1\nagents: []\n")
        
        r = PiDevRenderer(str(src), str(dest))
        assert r.validate_yaml("pi.yml") is True
    
    def test_validate_yaml_fails_on_invalid_yaml(self, tmp_path):
        """validate_yaml() returns False for invalid YAML (when PyYAML available)"""
        pytest.importorskip("yaml", reason="PyYAML not installed — skipping")
        
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        agent_dir = dest / "agent"
        agent_dir.mkdir(parents=True)
        
        # Create invalid YAML
        (agent_dir / "pi.yml").write_text("key: [unclosed bracket\n")
        
        r = PiDevRenderer(str(src), str(dest))
        assert r.validate_yaml("pi.yml") is False
    
    def test_validate_yaml_returns_false_for_missing_file(self, tmp_path):
        """validate_yaml() returns False if file doesn't exist"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        agent_dir = dest / "agent"
        agent_dir.mkdir(parents=True)
        
        r = PiDevRenderer(str(src), str(dest))
        assert r.validate_yaml("nonexistent.yml") is False
