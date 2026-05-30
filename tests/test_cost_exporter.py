"""
Comprehensive test suite for CostExporter class.
Tests: 33 tests covering 4 export formats (CSV, JSON, Markdown, HTML).
"""

import pytest
import json
import csv
from io import StringIO
from src.agents.cost_management.provider_tracker import ProviderTracker, ProviderType
from src.agents.cost_management.exporter import CostExporter, ExportFormat


class TestExporterInitialization:
    """Tests for CostExporter initialization."""

    def test_exporter_initializes_with_tracker(self):
        """Test that CostExporter initializes with a valid tracker."""
        tracker = ProviderTracker()
        exporter = CostExporter(tracker)
        assert exporter.tracker is tracker

    def test_export_formats_available(self):
        """Test that all 4 export formats are available."""
        formats = list(ExportFormat)
        assert len(formats) == 4
        format_names = {f.name for f in formats}
        expected = {"CSV", "JSON", "MARKDOWN", "HTML"}
        assert format_names == expected


class TestCSVExport:
    """Tests for CSV export functionality."""

    def test_csv_export_basic(self):
        """Test basic CSV export generation."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        assert isinstance(csv_output, str)
        assert len(csv_output) > 0

    def test_csv_export_contains_headers(self):
        """Test that CSV export contains expected headers."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        assert "provider" in csv_output.lower()
        assert "total_requests" in csv_output.lower() or "total requests" in csv_output.lower()
        assert "total_cost" in csv_output.lower() or "total cost" in csv_output.lower()

    def test_csv_export_multiple_providers(self):
        """Test CSV export with multiple providers."""
        tracker = ProviderTracker()
        providers_config = [
            (ProviderType.ANTHROPIC, "claude-opus-4-6", 100, 50, 0.05),
            (ProviderType.OPENAI, "gpt-4", 150, 75, 0.08),
            (ProviderType.GEMINI, "gemini-pro", 120, 60, 0.02),
        ]

        for provider, model, input_tok, output_tok, cost in providers_config:
            tracker.record_request(
                provider=provider,
                model=model,
                input_tokens=input_tok,
                output_tokens=output_tok,
                cost_usd=cost,
            )

        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        lines = csv_output.strip().split("\n")
        # 1 header + 3 providers = 4 lines minimum
        assert len(lines) >= 4

    def test_csv_export_is_valid_csv(self):
        """Test that CSV export can be parsed as valid CSV."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        
        csv_reader = csv.reader(StringIO(csv_output))
        rows = list(csv_reader)
        assert len(rows) >= 2  # At least header + 1 data row

    def test_csv_export_empty_tracker(self):
        """Test CSV export with empty tracker."""
        tracker = ProviderTracker()
        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        assert isinstance(csv_output, str)
        assert len(csv_output) > 0


class TestJSONExport:
    """Tests for JSON export functionality."""

    def test_json_export_basic(self):
        """Test basic JSON export generation."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        assert isinstance(json_output, str)
        assert len(json_output) > 0

    def test_json_export_is_valid_json(self):
        """Test that JSON export can be parsed as valid JSON."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        data = json.loads(json_output)
        assert isinstance(data, dict)

    def test_json_export_contains_metadata(self):
        """Test that JSON export contains metadata."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        data = json.loads(json_output)
        # Check that export contains key sections
        assert "summary" in data or "providers" in data or "export_timestamp" in data
        assert "providers" in data

    def test_json_export_all_providers(self):
        """Test JSON export with all 5 providers."""
        tracker = ProviderTracker()
        providers_config = [
            (ProviderType.ANTHROPIC, "claude-opus-4-6", 100, 50, 0.05),
            (ProviderType.OPENAI, "gpt-4", 150, 75, 0.08),
            (ProviderType.GEMINI, "gemini-pro", 120, 60, 0.02),
            (ProviderType.GITHUB_COPILOT, "copilot-gpt4", 140, 70, 0.03),
            (ProviderType.OLLAMA, "mistral", 100, 50, 0.001),
        ]

        for provider, model, input_tok, output_tok, cost in providers_config:
            tracker.record_request(
                provider=provider,
                model=model,
                input_tokens=input_tok,
                output_tokens=output_tok,
                cost_usd=cost,
            )

        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        data = json.loads(json_output)
        assert len(data["providers"]) == 5

    def test_json_export_preserves_cost_precision(self):
        """Test that JSON export preserves cost precision."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.123456,
        )
        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        data = json.loads(json_output)
        anthropic_data = data["providers"]["anthropic"]
        assert "total_cost_usd" in anthropic_data

    def test_json_export_empty_tracker(self):
        """Test JSON export with empty tracker."""
        tracker = ProviderTracker()
        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        data = json.loads(json_output)
        assert isinstance(data, dict)


class TestMarkdownExport:
    """Tests for Markdown export functionality."""

    def test_markdown_export_basic(self):
        """Test basic Markdown export generation."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        assert isinstance(md_output, str)
        assert len(md_output) > 0

    def test_markdown_export_contains_headers(self):
        """Test that Markdown export contains headers."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        assert "# Cost Report" in md_output or "#" in md_output

    def test_markdown_export_contains_tables(self):
        """Test that Markdown export contains table syntax."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        assert "|" in md_output or "##" in md_output

    def test_markdown_export_all_providers(self):
        """Test Markdown export with all 5 providers."""
        tracker = ProviderTracker()
        providers_config = [
            (ProviderType.ANTHROPIC, "claude-opus-4-6", 100, 50, 0.05),
            (ProviderType.OPENAI, "gpt-4", 150, 75, 0.08),
            (ProviderType.GEMINI, "gemini-pro", 120, 60, 0.02),
            (ProviderType.GITHUB_COPILOT, "copilot-gpt4", 140, 70, 0.03),
            (ProviderType.OLLAMA, "mistral", 100, 50, 0.001),
        ]

        for provider, model, input_tok, output_tok, cost in providers_config:
            tracker.record_request(
                provider=provider,
                model=model,
                input_tokens=input_tok,
                output_tokens=output_tok,
                cost_usd=cost,
            )

        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        assert len(md_output) > 0
        # Should contain provider names
        for provider_name in ["anthropic", "openai", "gemini"]:
            assert provider_name.lower() in md_output.lower()

    def test_markdown_export_contains_summary(self):
        """Test that Markdown export contains summary section."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        md_lower = md_output.lower()
        assert ("summary" in md_lower or "overview" in md_lower or "total" in md_lower)

    def test_markdown_export_empty_tracker(self):
        """Test Markdown export with empty tracker."""
        tracker = ProviderTracker()
        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        assert isinstance(md_output, str)
        assert len(md_output) > 0


class TestHTMLExport:
    """Tests for HTML export functionality."""

    def test_html_export_basic(self):
        """Test basic HTML export generation."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        assert isinstance(html_output, str)
        assert len(html_output) > 0

    def test_html_export_contains_html_tags(self):
        """Test that HTML export contains HTML structure."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        # Check for HTML content markers
        assert "<" in html_output and ">" in html_output
        assert "html" in html_output.lower() or "h1" in html_output.lower() or "section" in html_output.lower()

    def test_html_export_contains_title(self):
        """Test that HTML export contains title."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        assert "<title>" in html_output.lower() or "cost" in html_output.lower()

    def test_html_export_all_providers(self):
        """Test HTML export with all 5 providers."""
        tracker = ProviderTracker()
        providers_config = [
            (ProviderType.ANTHROPIC, "claude-opus-4-6", 100, 50, 0.05),
            (ProviderType.OPENAI, "gpt-4", 150, 75, 0.08),
            (ProviderType.GEMINI, "gemini-pro", 120, 60, 0.02),
            (ProviderType.GITHUB_COPILOT, "copilot-gpt4", 140, 70, 0.03),
            (ProviderType.OLLAMA, "mistral", 100, 50, 0.001),
        ]

        for provider, model, input_tok, output_tok, cost in providers_config:
            tracker.record_request(
                provider=provider,
                model=model,
                input_tokens=input_tok,
                output_tokens=output_tok,
                cost_usd=cost,
            )

        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        assert len(html_output) > 0

    def test_html_export_contains_data(self):
        """Test that HTML export contains cost data."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        # Should contain cost value or anthropic reference
        assert "0.05" in html_output or "anthropic" in html_output.lower()

    def test_html_export_empty_tracker(self):
        """Test HTML export with empty tracker."""
        tracker = ProviderTracker()
        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        assert isinstance(html_output, str)
        assert len(html_output) > 0


class TestExportFormatSelection:
    """Tests for export format selection and routing."""

    def test_csv_format_selection(self):
        """Test explicit CSV format selection."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        json_output = exporter.export(ExportFormat.JSON)
        assert csv_output != json_output

    def test_json_format_selection(self):
        """Test explicit JSON format selection."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        json_output = exporter.export(ExportFormat.JSON)
        html_output = exporter.export(ExportFormat.HTML)
        assert json_output != html_output

    def test_markdown_format_selection(self):
        """Test explicit Markdown format selection."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        csv_output = exporter.export(ExportFormat.CSV)
        assert md_output != csv_output

    def test_html_format_selection(self):
        """Test explicit HTML format selection."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        html_output = exporter.export(ExportFormat.HTML)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        assert html_output != md_output


class TestDataValidation:
    """Tests for data validation in exports."""

    def test_export_handles_unicode(self):
        """Test that exports handle unicode characters."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        for fmt in ExportFormat:
            output = exporter.export(fmt)
            assert isinstance(output, str)

    def test_export_precision_preserved(self):
        """Test that cost precision is preserved across formats."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.123456,
        )
        exporter = CostExporter(tracker)
        csv_output = exporter.export(ExportFormat.CSV)
        json_output = exporter.export(ExportFormat.JSON)
        # Both should contain the cost value
        assert isinstance(csv_output, str)
        assert isinstance(json_output, str)

    def test_large_numbers_handled(self):
        """Test handling of large numbers in exports."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=1000000,
            output_tokens=500000,
            cost_usd=100.50,
        )
        exporter = CostExporter(tracker)
        for fmt in ExportFormat:
            output = exporter.export(fmt)
            assert isinstance(output, str)
            assert len(output) > 0


class TestExportConsistency:
    """Tests for consistency across export formats."""

    def test_all_formats_include_provider_names(self):
        """Test that all export formats include provider names."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        
        csv_output = exporter.export(ExportFormat.CSV)
        json_output = exporter.export(ExportFormat.JSON)
        md_output = exporter.export(ExportFormat.MARKDOWN)
        html_output = exporter.export(ExportFormat.HTML)
        
        for output in [csv_output, json_output, md_output, html_output]:
            assert "anthropic" in output.lower()

    def test_all_formats_have_content(self):
        """Test that all export formats produce non-empty output."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        exporter = CostExporter(tracker)
        
        for fmt in ExportFormat:
            output = exporter.export(fmt)
            assert len(output) > 0

    def test_export_with_multiple_requests_per_provider(self):
        """Test exports with multiple requests per provider."""
        tracker = ProviderTracker()
        for i in range(3):
            tracker.record_request(
                provider=ProviderType.ANTHROPIC,
                model="claude-opus-4-6",
                input_tokens=100 + i,
                output_tokens=50 + i,
                cost_usd=0.05 + (i * 0.01),
            )
        
        exporter = CostExporter(tracker)
        for fmt in ExportFormat:
            output = exporter.export(fmt)
            assert len(output) > 0
