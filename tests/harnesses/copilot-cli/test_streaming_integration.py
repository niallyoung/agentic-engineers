"""
Integration tests for Copilot CLI streaming renderer.

Tests run against the actual src/skills/ directory (read-only) and a temporary destination.
"""

import json
import pytest
from pathlib import Path
from src.harnesses.copilot_cli.streaming import StreamingRenderer, main

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SRC_SKILLS = REPO_ROOT / "src" / "skills"


@pytest.mark.skipif(not SRC_SKILLS.is_dir(), reason="src/skills not available")
class TestIntegrationRenderAllSkills:
    """Integration tests rendering all canonical skills."""

    def test_integration_renders_all_skills(self, tmp_path):
        """Full integration: render all canonical skills to tmp dir."""
        renderer = StreamingRenderer(
            str(SRC_SKILLS),
            str(tmp_path / "skills"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_all())
        summary = next(e for e in events if e.type == "summary")

        # Should have rendered at least some skills
        assert summary.data["count"] > 0
        assert summary.data["errors"] == []
        assert summary.data["total_bytes"] > 0

    def test_integration_marker_written_after_render(self, tmp_path):
        """Marker file must exist for each rendered skill."""
        renderer = StreamingRenderer(
            str(SRC_SKILLS),
            str(tmp_path / "skills"),
            ".agentic-engine{service-name}",
        )
        list(renderer.render_all())

        # Check that marker files exist for all rendered skills
        skills_dir = tmp_path / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    marker = skill_dir / ".agentic-engine{service-name}"
                    assert marker.exists(), f"Marker missing for {skill_dir.name}"

    def test_integration_json_lines_parseable(self, tmp_path, capsys):
        """All stdout lines from main() must be valid JSON."""
        result = main([
            str(SRC_SKILLS),
            str(tmp_path / "skills"),
            ".agentic-engine{service-name}",
        ])
        assert result == 0

        captured = capsys.readouterr()
        lines = captured.out.strip().splitlines()
        assert len(lines) > 0

        # Every line must be valid JSON
        for line in lines:
            obj = json.loads(line)
            assert "type" in obj
            assert "timestamp" in obj
            assert "skill" in obj
            assert "data" in obj

    def test_integration_summary_event_present(self, tmp_path):
        """Integration test must emit summary event."""
        renderer = StreamingRenderer(
            str(SRC_SKILLS),
            str(tmp_path / "skills"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_all())
        summaries = [e for e in events if e.type == "summary"]
        assert len(summaries) == 1

    def test_integration_all_events_have_timestamp(self, tmp_path):
        """All events must have valid ISO8601 timestamp."""
        renderer = StreamingRenderer(
            str(SRC_SKILLS),
            str(tmp_path / "skills"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_all())
        for event in events:
            assert event.timestamp
            # Basic ISO8601 format check
            assert "T" in event.timestamp
            assert "Z" in event.timestamp
