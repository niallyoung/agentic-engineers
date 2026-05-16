"""
Unit tests for Copilot CLI streaming renderer.

Tests cover:
- StreamEvent serialization
- StreamingRenderer._list_source_skills
- StreamingRenderer.render_skill (foreign skill protection)
- StreamingRenderer.render_all (summary, cancellation)
- main() CLI entry point
"""

import json
import pytest
from pathlib import Path
from src.harnesses.copilot_cli.streaming import StreamEvent, StreamingRenderer, main


class TestStreamEvent:
    """Tests for StreamEvent dataclass and serialization."""

    def test_stream_event_to_json_complete(self):
        """StreamEvent.to_json() produces valid JSON."""
        event = StreamEvent(
            type="complete",
            skill="ab-testing",
            timestamp="2026-05-16T12:00:00Z",
            data={"duration_ms": 120, "bytes": 4096},
        )
        parsed = json.loads(event.to_json())
        assert parsed["type"] == "complete"
        assert parsed["skill"] == "ab-testing"
        assert parsed["data"]["bytes"] == 4096

    def test_stream_event_summary_skill_is_none(self):
        """Summary events have skill=null."""
        event = StreamEvent(
            type="summary",
            skill=None,
            timestamp="2026-05-16T12:00:00Z",
            data={"count": 14},
        )
        parsed = json.loads(event.to_json())
        assert parsed["skill"] is None
        assert parsed["data"]["count"] == 14

    def test_stream_event_start_has_empty_data(self):
        """Start events have empty data dict."""
        event = StreamEvent(
            type="start",
            skill="voice-notify",
            timestamp="2026-05-16T12:00:00Z",
        )
        parsed = json.loads(event.to_json())
        assert parsed["data"] == {}

    def test_stream_event_error_has_message(self):
        """Error events include message in data."""
        event = StreamEvent(
            type="error",
            skill="agent-creator",
            timestamp="2026-05-16T12:00:00Z",
            data={"message": "rsync failed with exit 1"},
        )
        parsed = json.loads(event.to_json())
        assert "message" in parsed["data"]


class TestListSourceSkills:
    """Tests for StreamingRenderer._list_source_skills()."""

    @pytest.fixture
    def skill_tree(self, tmp_path):
        """Create a minimal skill tree for testing."""
        src_dir = tmp_path / "src"
        for name in ["ab-testing", "agent-creator", "voice-notify"]:
            skill_dir = src_dir / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")
        # Add a non-skill dir (no SKILL.md)
        (src_dir / "_docs").mkdir()
        return tmp_path

    def test_list_source_skills_returns_sorted(self, skill_tree, tmp_path):
        """_list_source_skills returns sorted list of skill names."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )
        skills = renderer._list_source_skills()
        assert skills == ["ab-testing", "agent-creator", "voice-notify"]

    def test_list_source_skills_excludes_non_skill_dirs(self, skill_tree, tmp_path):
        """_list_source_skills excludes dirs without SKILL.md."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )
        skills = renderer._list_source_skills()
        assert "_docs" not in skills

    def test_list_source_skills_raises_on_missing_src(self, tmp_path):
        """_list_source_skills raises FileNotFoundError if src dir missing."""
        renderer = StreamingRenderer(
            str(tmp_path / "nonexistent"),
            str(tmp_path / "dst"),
            ".marker",
        )
        with pytest.raises(FileNotFoundError):
            renderer._list_source_skills()

    def test_list_source_skills_empty_dir(self, tmp_path):
        """_list_source_skills returns empty list for empty src dir."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        renderer = StreamingRenderer(
            str(src_dir),
            str(tmp_path / "dst"),
            ".marker",
        )
        skills = renderer._list_source_skills()
        assert skills == []


class TestRenderSkillForeignProtection:
    """Tests for StreamingRenderer.render_skill() foreign skill protection."""

    @pytest.fixture
    def skill_tree(self, tmp_path):
        """Create a minimal skill tree for testing."""
        src_dir = tmp_path / "src"
        for name in ["ab-testing", "agent-creator"]:
            skill_dir = src_dir / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")
        return tmp_path

    def test_render_skill_skips_foreign_skill(self, skill_tree, tmp_path):
        """A skill dir without a marker file must be skipped."""
        dst = tmp_path / "dst"
        foreign = dst / "ab-testing"
        foreign.mkdir(parents=True)
        # No marker file written → foreign skill

        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(dst),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_skill("ab-testing"))
        types = [e.type for e in events]
        assert "skip" in types
        assert "complete" not in types

    def test_render_skill_overwrites_managed_skill(self, skill_tree, tmp_path):
        """A skill dir WITH a marker file must be overwritten."""
        dst = tmp_path / "dst"
        managed = dst / "ab-testing"
        managed.mkdir(parents=True)
        (managed / ".agentic-engine{service-name}").write_text("2026-01-01T00:00:00Z\n")

        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(dst),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_skill("ab-testing"))
        types = [e.type for e in events]
        assert "complete" in types
        assert "skip" not in types

    def test_render_skill_marker_written_after_success(self, skill_tree, tmp_path):
        """Marker file is written only after successful render."""
        dst = tmp_path / "dst"
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(dst),
            ".agentic-engine{service-name}",
        )
        list(renderer.render_skill("ab-testing"))
        marker_path = dst / "ab-testing" / ".agentic-engine{service-name}"
        assert marker_path.exists()
        assert marker_path.read_text().strip()  # Has timestamp


class TestRenderAll:
    """Tests for StreamingRenderer.render_all()."""

    @pytest.fixture
    def skill_tree(self, tmp_path):
        """Create a minimal skill tree for testing."""
        src_dir = tmp_path / "src"
        for name in ["ab-testing", "agent-creator", "voice-notify"]:
            skill_dir = src_dir / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")
        return tmp_path

    def test_render_all_emits_summary(self, skill_tree, tmp_path):
        """render_all() emits a summary event at the end."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_all())
        summary = [e for e in events if e.type == "summary"]
        assert len(summary) == 1
        assert summary[0].data["count"] == 3

    def test_render_all_summary_has_correct_count(self, skill_tree, tmp_path):
        """Summary count matches number of successfully rendered skills."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_all())
        summary = next(e for e in events if e.type == "summary")
        assert summary.data["count"] == 3
        assert summary.data["errors"] == []

    def test_render_all_emits_start_complete_per_skill(self, skill_tree, tmp_path):
        """render_all() emits start and complete for each skill."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer.render_all())
        starts = [e for e in events if e.type == "start"]
        completes = [e for e in events if e.type == "complete"]
        assert len(starts) == 3
        assert len(completes) == 3

    def test_render_all_cancellation_stops_rendering(self, skill_tree, tmp_path):
        """Cancellation after first skill stops further rendering."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )

        events = []
        for event in renderer.render_all():
            events.append(event)
            if event.type == "complete":
                renderer.cancel()
                break

        # Should have stopped; only 1 complete event
        complete_events = [e for e in events if e.type == "complete"]
        assert len(complete_events) == 1

    def test_render_all_summary_cancelled_flag(self, skill_tree, tmp_path):
        """Summary includes cancelled flag when cancellation occurs."""
        renderer = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )

        for event in renderer.render_all():
            if event.type == "complete":
                renderer.cancel()
                break

        # Re-render to get summary
        renderer2 = StreamingRenderer(
            str(skill_tree / "src"),
            str(tmp_path / "dst"),
            ".agentic-engine{service-name}",
        )
        events = list(renderer2.render_all())
        summary = next(e for e in events if e.type == "summary")
        assert "cancelled" in summary.data


class TestMainCLI:
    """Tests for main() CLI entry point."""

    def test_main_missing_args_returns_2(self):
        """main() returns 2 when args are missing."""
        assert main([]) == 2
        assert main(["only_one"]) == 2
        assert main(["one", "two"]) == 2

    def test_main_missing_src_returns_1(self, tmp_path):
        """main() returns 1 when source dir doesn't exist."""
        result = main([
            str(tmp_path / "nonexistent"),
            str(tmp_path / "dst"),
            ".marker",
        ])
        assert result == 1

    def test_main_with_valid_args_returns_0(self, tmp_path):
        """main() returns 0 on success."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test-skill").mkdir()
        (src_dir / "test-skill" / "SKILL.md").write_text("# Test\n")

        result = main([
            str(src_dir),
            str(tmp_path / "dst"),
            ".marker",
        ])
        assert result == 0

    def test_main_emits_json_lines(self, tmp_path, capsys):
        """main() emits valid JSON-lines to stdout."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test-skill").mkdir()
        (src_dir / "test-skill" / "SKILL.md").write_text("# Test\n")

        main([
            str(src_dir),
            str(tmp_path / "dst"),
            ".marker",
        ])

        captured = capsys.readouterr()
        lines = captured.out.strip().splitlines()
        assert len(lines) > 0
        # Each line must be valid JSON
        for line in lines:
            obj = json.loads(line)
            assert "type" in obj
            assert "timestamp" in obj


class TestDirSizeBytes:
    """Tests for StreamingRenderer._dir_size_bytes()."""

    def test_dir_size_bytes_empty_dir(self, tmp_path):
        """_dir_size_bytes returns 0 for empty dir."""
        renderer = StreamingRenderer(
            str(tmp_path / "src"),
            str(tmp_path / "dst"),
            ".marker",
        )
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert renderer._dir_size_bytes(empty_dir) == 0

    def test_dir_size_bytes_single_file(self, tmp_path):
        """_dir_size_bytes returns correct size for single file."""
        renderer = StreamingRenderer(
            str(tmp_path / "src"),
            str(tmp_path / "dst"),
            ".marker",
        )
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        test_file = test_dir / "file.txt"
        test_file.write_text("hello")  # 5 bytes
        assert renderer._dir_size_bytes(test_dir) == 5

    def test_dir_size_bytes_multiple_files(self, tmp_path):
        """_dir_size_bytes sums all files recursively."""
        renderer = StreamingRenderer(
            str(tmp_path / "src"),
            str(tmp_path / "dst"),
            ".marker",
        )
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("hello")  # 5 bytes
        (test_dir / "file2.txt").write_text("world")  # 5 bytes
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("!")  # 1 byte
        assert renderer._dir_size_bytes(test_dir) == 11
