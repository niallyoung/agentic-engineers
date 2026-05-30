"""
Dashboard Generator for Continuous CI/CD Pipeline

Generates HTML dashboards with heatmaps, trends, and regression timelines.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import math


class DashboardGenerator:
    """Generates HTML dashboard for evaluation results."""

    def __init__(self, results: Dict[str, Any], baseline: Optional[Dict[str, Any]] = None, regressions: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize dashboard generator.

        Args:
            results: Current evaluation results
            baseline: Baseline results for comparison
            regressions: List of detected regressions
        """
        self.results = results
        self.baseline = baseline
        self.regressions = regressions or []

    def generate(self, output_path: str) -> str:
        """
        Generate HTML dashboard.

        Args:
            output_path: Path to write HTML file

        Returns:
            Path to generated HTML file
        """
        html = self._build_html()

        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def _build_html(self) -> str:
        """Build complete HTML dashboard."""
        timestamp = datetime.utcnow().isoformat()
        summary = self.results.get("summary", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Framework Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .status-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .status-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        
        .status-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        
        .status-card .label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .status-card.success .value {{
            color: #4caf50;
        }}
        
        .status-card.warning .value {{
            color: #ff9800;
        }}
        
        .status-card.danger .value {{
            color: #f44336;
        }}
        
        .section {{
            margin-bottom: 40px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            background: #fafafa;
        }}
        
        .section h2 {{
            font-size: 20px;
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .heatmap {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 8px;
            margin-top: 15px;
        }}
        
        .heatmap-cell {{
            aspect-ratio: 1;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .heatmap-cell:hover {{
            transform: scale(1.1);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        .heatmap-cell.pass {{
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
        }}
        
        .heatmap-cell.fail {{
            background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
        }}
        
        .heatmap-cell.timeout {{
            background: linear-gradient(135deg, #ff9800 0%, #e68900 100%);
        }}
        
        .heatmap-cell.error {{
            background: linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%);
        }}
        
        .heatmap-cell.skipped {{
            background: linear-gradient(135deg, #9e9e9e 0%, #757575 100%);
        }}
        
        .trend-chart {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 15px;
            margin-top: 15px;
            height: 200px;
            display: flex;
            align-items: flex-end;
            gap: 8px;
        }}
        
        .trend-bar {{
            flex: 1;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px 4px 0 0;
            position: relative;
            min-height: 5%;
            transition: all 0.3s ease;
        }}
        
        .trend-bar:hover {{
            opacity: 0.8;
        }}
        
        .trend-bar-label {{
            position: absolute;
            bottom: -25px;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 11px;
            color: #666;
        }}
        
        .regression-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: white;
        }}
        
        .regression-table th {{
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
            color: #333;
        }}
        
        .regression-table td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .regression-table tr:hover {{
            background: #fafafa;
        }}
        
        .severity-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .severity-critical {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .severity-high {{
            background: #fff3e0;
            color: #e65100;
        }}
        
        .severity-medium {{
            background: #f3e5f5;
            color: #6a1b9a;
        }}
        
        .severity-low {{
            background: #e8f5e9;
            color: #1b5e20;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f5f5f5;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Evaluation Framework Dashboard</h1>
            <p>Generated: {timestamp}</p>
        </div>
        
        <div class="content">
{self._build_status_cards(summary)}
{self._build_comparison_section(summary)}
{self._build_harness_heatmap()}
{self._build_regression_section()}
{self._build_trend_section()}
        </div>
        
        <div class="footer">
            <p>Continuous CI/CD Pipeline · Automated Nightly Evaluation Framework</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_status_cards(self, summary: Dict[str, Any]) -> str:
        """Build status cards section."""
        total = summary.get("total_tests", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        pass_rate = summary.get("pass_rate", 0)

        pass_class = "success" if pass_rate >= 95 else "warning" if pass_rate >= 80 else "danger"

        return f"""            <div class="status-grid">
                <div class="status-card success">
                    <div class="label">✓ Passed</div>
                    <div class="value">{passed}</div>
                </div>
                <div class="status-card danger">
                    <div class="label">✗ Failed</div>
                    <div class="value">{failed}</div>
                </div>
                <div class="status-card {pass_class}">
                    <div class="label">📊 Pass Rate</div>
                    <div class="value">{pass_rate:.1f}%</div>
                </div>
                <div class="status-card">
                    <div class="label">⏱️ Total Tests</div>
                    <div class="value">{total}</div>
                </div>
            </div>"""

    def _build_comparison_section(self, summary: Dict[str, Any]) -> str:
        """Build baseline comparison section."""
        if not self.baseline:
            return ""

        baseline_summary = self.baseline.get("results", {}).get("summary", {})
        baseline_pass_rate = baseline_summary.get("pass_rate", 0)
        current_pass_rate = summary.get("pass_rate", 0)
        change = current_pass_rate - baseline_pass_rate

        change_indicator = "🔴" if change < -2 else "🟡" if change < 0 else "🟢"

        return f"""
            <div class="section">
                <h2>📈 Baseline Comparison</h2>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="border-bottom:1px solid #e0e0e0;">
                        <th style="text-align:left;padding:10px;">Metric</th>
                        <th style="text-align:center;padding:10px;">Baseline</th>
                        <th style="text-align:center;padding:10px;">Current</th>
                        <th style="text-align:center;padding:10px;">Change</th>
                    </tr>
                    <tr style="background:#fafafa;">
                        <td style="padding:10px;">Pass Rate</td>
                        <td style="text-align:center;padding:10px;">{baseline_pass_rate:.1f}%</td>
                        <td style="text-align:center;padding:10px;">{current_pass_rate:.1f}%</td>
                        <td style="text-align:center;padding:10px;">{change_indicator} {change:+.1f}%</td>
                    </tr>
                </table>
            </div>"""

    def _build_harness_heatmap(self) -> str:
        """Build harness heatmap section."""
        summary = self.results.get("summary", {})
        by_harness = summary.get("by_harness", {})

        if not by_harness:
            return ""

        heatmap_html = '<div class="heatmap">'
        for harness, stats in by_harness.items():
            passed = stats.get("passed", 0)
            failed = stats.get("failed", 0)
            total = passed + failed
            pass_rate = (passed / total * 100) if total > 0 else 0

            if pass_rate >= 95:
                cell_class = "pass"
            elif pass_rate >= 80:
                cell_class = "warning"
            else:
                cell_class = "fail"

            heatmap_html += f'<div class="heatmap-cell {cell_class}" title="{harness}: {pass_rate:.0f}%">{harness[:3].upper()}</div>'

        heatmap_html += '</div>'

        return f"""
            <div class="section">
                <h2>🔥 Harness Heatmap</h2>
{heatmap_html}
            </div>"""

    def _build_regression_section(self) -> str:
        """Build regression section."""
        if not self.regressions:
            return '<div class="section"><h2>✅ Regressions</h2><p>No regressions detected.</p></div>'

        critical = [r for r in self.regressions if r.get("severity") == "critical"]
        high = [r for r in self.regressions if r.get("severity") == "high"]

        table_html = '<table class="regression-table"><thead><tr><th>Test ID</th><th>Type</th><th>Severity</th><th>Baseline</th><th>Current</th><th>Change</th></tr></thead><tbody>'

        for regression in self.regressions[:20]:  # Show top 20
            severity = regression.get("severity", "medium")
            reg_type = regression.get("regression_type", "unknown")
            table_html += f"""<tr>
                <td>{regression.get('test_id', 'unknown')}</td>
                <td>{reg_type}</td>
                <td><span class="severity-badge severity-{severity}">{severity}</span></td>
                <td>{regression.get('baseline_value', 0):.2f}</td>
                <td>{regression.get('current_value', 0):.2f}</td>
                <td>{regression.get('change_percent', 0):+.1f}%</td>
            </tr>"""

        table_html += '</tbody></table>'

        return f"""
            <div class="section">
                <h2>🚨 Regressions ({len(self.regressions)} total, {len(critical)} critical, {len(high)} high)</h2>
{table_html}
            </div>"""

    def _build_trend_section(self) -> str:
        """Build trend section."""
        return """
            <div class="section">
                <h2>📉 Quality Trends</h2>
                <p style="color:#666;font-size:14px;margin-bottom:10px;">Trends over time will be populated from baseline history.</p>
                <div class="trend-chart" style="height:150px;"></div>
            </div>"""
