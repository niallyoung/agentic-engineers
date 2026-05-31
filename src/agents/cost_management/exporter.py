"""
Multi-format exporter for multi-provider cost data.

Supports export to:
- CSV: Row per provider with key metrics
- JSON: Hierarchical structure with full metadata
- Markdown: Formatted tables with summaries
- HTML: Interactive dashboard view

Author: COST-002 Implementation Lead
"""

from enum import Enum
from typing import Dict, List, Optional
import html
import json
import csv
from io import StringIO
from datetime import datetime

from .provider_tracker import ProviderTracker, ProviderType


# Characters that trigger formula evaluation in spreadsheet applications
# (Excel, LibreOffice, Google Sheets). Cells beginning with any of these must
# be neutralised to prevent CSV injection (a.k.a. formula injection).
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: object) -> str:
    """Neutralise spreadsheet formula injection in a CSV cell value.

    Untrusted strings (e.g. model or provider names) that begin with a formula
    trigger character are prefixed with a single quote so spreadsheet programs
    treat them as literal text rather than executable formulas.
    """
    text = str(value)
    if text and text[0] in _CSV_INJECTION_PREFIXES:
        return "'" + text
    return text


def _md_safe(value: object) -> str:
    """Escape a value for safe inclusion in a Markdown table cell.

    Escapes pipe characters (which would break table structure) and neutralises
    HTML/newline injection so untrusted strings cannot alter the rendered
    document or inject markup when the Markdown is rendered to HTML.
    """
    text = str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    text = text.replace("\r", " ").replace("\n", " ")
    # Neutralise raw HTML that many Markdown renderers pass through verbatim.
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class CostExporter:
    """Export multi-provider cost data in various formats."""

    def __init__(self, tracker: ProviderTracker):
        """Initialize exporter with a cost tracker."""
        self.tracker = tracker

    def export(self, format: ExportFormat) -> str:
        """Export cost data in the specified format."""
        if format == ExportFormat.CSV:
            return self.export_csv()
        elif format == ExportFormat.JSON:
            return self.export_json()
        elif format == ExportFormat.MARKDOWN:
            return self.export_markdown()
        elif format == ExportFormat.HTML:
            return self.export_html()
        else:
            raise ValueError(f"Unknown export format: {format}")

    def export_csv(self) -> str:
        """Export provider metrics to CSV format."""
        output = StringIO()
        
        metrics = self.tracker.get_all_metrics()
        active_metrics = [
            (provider_name, m)
            for provider_name, m in metrics.items()
            if m.total_requests > 0
        ]

        if not active_metrics:
            return "provider,total_requests,total_cost_usd,total_tokens,cost_per_token\n"

        fieldnames = [
            "provider",
            "total_requests",
            "successful_requests",
            "failed_requests",
            "error_rate",
            "total_cost_usd",
            "total_input_tokens",
            "total_output_tokens",
            "total_cached_tokens",
            "total_tokens",
            "avg_cost_per_request",
            "avg_tokens_per_request",
            "cost_per_token",
            "min_cost_per_token",
            "max_cost_per_token",
            "total_duration_ms",
            "models_used",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for provider_name, metrics in active_metrics:
            writer.writerow({
                "provider": _csv_safe(provider_name),
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "error_rate": f"{metrics.error_rate:.4f}",
                "total_cost_usd": f"{metrics.total_cost_usd:.6f}",
                "total_input_tokens": metrics.total_input_tokens,
                "total_output_tokens": metrics.total_output_tokens,
                "total_cached_tokens": metrics.total_cached_tokens,
                "total_tokens": metrics.total_tokens,
                "avg_cost_per_request": f"{metrics.avg_cost_per_request:.6f}",
                "avg_tokens_per_request": metrics.avg_tokens_per_request,
                "cost_per_token": f"{metrics.cost_per_token:.8f}",
                "min_cost_per_token": f"{metrics.min_cost_per_token:.8f}",
                "max_cost_per_token": f"{metrics.max_cost_per_token:.8f}",
                "total_duration_ms": metrics.total_duration_ms,
                "models_used": ";".join(
                    _csv_safe(f"{m}({c})") for m, c in metrics.models_used.items()
                ),
            })

        return output.getvalue()

    def export_json(self) -> str:
        """Export all data to JSON with hierarchical structure."""
        metrics_dict = self.tracker.get_all_metrics()
        
        return json.dumps({
            "export_timestamp": datetime.now().isoformat(),
            "session_id": self.tracker.session_id,
            "session_start": self.tracker.session_start.isoformat(),
            "session_duration_ms": int(
                (datetime.now() - self.tracker.session_start).total_seconds() * 1000
            ),
            "summary": {
                "total_requests": len(self.tracker.requests),
                "total_cost_usd": round(self.tracker.get_total_cost(), 6),
                "total_tokens": self.tracker.get_total_tokens(),
                "providers_active": sum(
                    1 for m in metrics_dict.values() if m.total_requests > 0
                ),
            },
            "providers": {
                provider_name: metrics.to_dict()
                for provider_name, metrics in metrics_dict.items()
            },
            "efficiency": self.tracker.get_efficiency_metrics(),
            "comparison": self.tracker.get_comparison(),
            "cost_by_provider": self.tracker.get_cost_by_provider(),
            "cost_by_model": self.tracker.get_cost_by_model(),
            "cost_trends": {
                "hourly": self.tracker.get_cost_trend("hourly"),
                "daily": self.tracker.get_cost_trend("daily"),
            },
        }, indent=2)

    def export_markdown(self) -> str:
        """Export data to Markdown with formatted tables."""
        lines = []
        
        # Header
        lines.append("# Cost Aggregation Report")
        lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Session ID:** {_md_safe(self.tracker.session_id)}")
        
        # Summary
        efficiency = self.tracker.get_efficiency_metrics()
        if efficiency:
            lines.append("\n## Summary")
            lines.append(f"- **Total Requests:** {efficiency['total_requests']}")
            lines.append(f"- **Success Rate:** {efficiency['success_rate']:.2%}")
            lines.append(f"- **Total Cost:** ${efficiency['total_cost_usd']:.6f}")
            lines.append(f"- **Total Tokens:** {efficiency['total_tokens']:,}")
            lines.append(f"- **Avg Cost/Token:** ${efficiency['avg_cost_per_token']:.8f}")
        
        # Provider Metrics Table
        metrics = self.tracker.get_all_metrics()
        active_metrics = [
            (provider_name, m)
            for provider_name, m in metrics.items()
            if m.total_requests > 0
        ]

        if active_metrics:
            lines.append("\n## Provider Metrics")
            lines.append(
                "| Provider | Requests | Cost ($) | Tokens | Cost/Token | Avg/Request |"
            )
            lines.append("|----------|----------|----------|--------|-----------|------------|")

            for provider_name, m in active_metrics:
                lines.append(
                    f"| {_md_safe(provider_name)} | {m.total_requests} | "
                    f"${m.total_cost_usd:.6f} | {m.total_tokens:,} | "
                    f"${m.cost_per_token:.8f} | ${m.avg_cost_per_request:.6f} |"
                )

        # Model Usage
        cost_by_model = self.tracker.get_cost_by_model()
        if cost_by_model:
            lines.append("\n## Cost by Model")
            lines.append("| Model | Cost ($) |")
            lines.append("|-------|----------|")
            for model, cost in sorted(
                cost_by_model.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"| {_md_safe(model)} | ${cost:.6f} |")

        # Rankings
        comparison = self.tracker.get_comparison()
        if comparison.get("rankings"):
            lines.append("\n## Rankings")
            rankings = comparison["rankings"]
            if rankings.get("cheapest_provider"):
                lines.append(
                    f"- **Cheapest:** {_md_safe(rankings['cheapest_provider'])} "
                    f"(${rankings['cheapest_cost_per_token']:.8f}/token)"
                )
            if rankings.get("fastest_provider"):
                lines.append(
                    f"- **Fastest:** {_md_safe(rankings['fastest_provider'])} "
                    f"({rankings['fastest_avg_ms']:.2f}ms avg)"
                )

        # Cost Trends
        trends = self.tracker.get_cost_trend("daily")
        if trends:
            lines.append("\n## Daily Cost Trends")
            lines.append("| Date | Cost ($) |")
            lines.append("|------|----------|")
            for date_str, providers in sorted(trends.items()):
                total = sum(providers.values())
                lines.append(f"| {date_str} | ${total:.6f} |")

        return "\n".join(lines)

    def export_html(self) -> str:
        """Export data to HTML with interactive dashboard view."""
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '  <title>Cost Aggregation Dashboard</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }',
            '    .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }',
            '    h1, h2 { color: #333; }',
            '    .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }',
            '    .card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
            '    .card h3 { margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }',
            '    .card .value { font-size: 24px; font-weight: bold; }',
            '    table { width: 100%; border-collapse: collapse; margin: 20px 0; }',
            '    table thead { background-color: #f8f9fa; }',
            '    table th, table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }',
            '    table tr:hover { background-color: #f9f9f9; }',
            '    .positive { color: #28a745; }',
            '    .negative { color: #dc3545; }',
            '    .footer { color: #666; font-size: 12px; margin-top: 30px; text-align: center; }',
            '  </style>',
            '</head>',
            '<body>',
            '  <div class="container">',
            '    <h1>Cost Aggregation Dashboard</h1>',
            f'    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Session: {html.escape(str(self.tracker.session_id))}</p>',
        ]

        # Summary cards
        efficiency = self.tracker.get_efficiency_metrics()
        if efficiency:
            html_parts.extend([
                '    <div class="summary">',
                f'      <div class="card"><h3>Total Requests</h3><div class="value">{efficiency["total_requests"]}</div></div>',
                f'      <div class="card"><h3>Total Cost</h3><div class="value">${efficiency["total_cost_usd"]:.2f}</div></div>',
                f'      <div class="card"><h3>Total Tokens</h3><div class="value">{efficiency["total_tokens"]:,}</div></div>',
                f'      <div class="card"><h3>Cost per Token</h3><div class="value">${efficiency["avg_cost_per_token"]:.8f}</div></div>',
                '    </div>',
            ])

        # Provider metrics table
        metrics = self.tracker.get_all_metrics()
        active_metrics = [
            (provider_name, m)
            for provider_name, m in metrics.items()
            if m.total_requests > 0
        ]

        if active_metrics:
            html_parts.extend([
                '    <h2>Provider Metrics</h2>',
                '    <table>',
                '      <thead><tr><th>Provider</th><th>Requests</th><th>Cost ($)</th><th>Tokens</th><th>Cost/Token</th><th>Error Rate</th></tr></thead>',
                '      <tbody>',
            ])

            for provider_name, m in active_metrics:
                error_class = "positive" if m.error_rate == 0 else "negative"
                html_parts.append(
                    f'        <tr><td><strong>{html.escape(str(provider_name))}</strong></td><td>{m.total_requests}</td>'
                    f'<td>${m.total_cost_usd:.6f}</td><td>{m.total_tokens:,}</td>'
                    f'<td>${m.cost_per_token:.8f}</td>'
                    f'<td class="{error_class}">{m.error_rate:.2%}</td></tr>'
                )

            html_parts.extend(['      </tbody>', '    </table>'])

        # Cost by Model
        cost_by_model = self.tracker.get_cost_by_model()
        if cost_by_model:
            html_parts.extend(['    <h2>Cost by Model</h2>', '    <table>',
                '      <thead><tr><th>Model</th><th>Cost ($)</th></tr></thead>',
                '      <tbody>'])
            for model, cost in sorted(cost_by_model.items(), key=lambda x: x[1], reverse=True):
                html_parts.append(f'        <tr><td>{html.escape(str(model))}</td><td>${cost:.6f}</td></tr>')
            html_parts.extend(['      </tbody>', '    </table>'])

        # Rankings
        comparison = self.tracker.get_comparison()
        if comparison.get("rankings"):
            rankings = comparison["rankings"]
            html_parts.extend(['    <h2>Rankings</h2>', '    <ul>'])
            if rankings.get("cheapest_provider"):
                html_parts.append(
                    f'      <li><strong>Cheapest:</strong> {html.escape(str(rankings["cheapest_provider"]))} '
                    f'(${rankings["cheapest_cost_per_token"]:.8f}/token)</li>'
                )
            if rankings.get("fastest_provider"):
                html_parts.append(
                    f'      <li><strong>Fastest:</strong> {html.escape(str(rankings["fastest_provider"]))} '
                    f'({rankings["fastest_avg_ms"]:.2f}ms avg)</li>'
                )
            html_parts.append('    </ul>')

        html_parts.extend([
            '    <div class="footer">',
            '      <p>Multi-Provider Cost Aggregation Report</p>',
            '    </div>',
            '  </div>',
            '</body>',
            '</html>',
        ])

        return '\n'.join(html_parts)
