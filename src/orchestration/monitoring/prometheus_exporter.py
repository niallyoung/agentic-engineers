"""
Prometheus Exporter — Export metrics in Prometheus text format.

Generates the standard Prometheus exposition format (text/plain; version=0.0.4)
for scraping by Prometheus server.

Usage:
    registry = MetricsRegistry()
    # ... register metrics ...
    exporter = PrometheusExporter(registry)
    text = exporter.export()
    # serve text at /metrics endpoint
"""

import time
from typing import Dict, Optional
from .metrics import MetricsRegistry, Counter, Gauge, Histogram


class PrometheusExporter:
    """Export MetricsRegistry contents in Prometheus text format."""

    def __init__(self, registry: MetricsRegistry):
        self.registry = registry

    def export(self) -> str:
        """
        Generate Prometheus text format output.

        Returns:
            String in Prometheus exposition format.
        """
        lines = []
        metrics = self.registry.get_all()

        # Group metrics by base name for HELP/TYPE headers
        seen_names = set()

        for key, metric in metrics.items():
            if isinstance(metric, Counter):
                name = metric.name
                if name not in seen_names:
                    if metric.description:
                        lines.append(f"# HELP {name} {metric.description}")
                    lines.append(f"# TYPE {name} counter")
                    seen_names.add(name)
                label_str = self._format_labels(metric.labels)
                lines.append(f"{name}{label_str} {metric.value}")

            elif isinstance(metric, Gauge):
                name = metric.name
                if name not in seen_names:
                    if metric.description:
                        lines.append(f"# HELP {name} {metric.description}")
                    lines.append(f"# TYPE {name} gauge")
                    seen_names.add(name)
                label_str = self._format_labels(metric.labels)
                lines.append(f"{name}{label_str} {metric.value}")

            elif isinstance(metric, Histogram):
                name = metric.name
                if name not in seen_names:
                    if metric.description:
                        lines.append(f"# HELP {name} {metric.description}")
                    lines.append(f"# TYPE {name} histogram")
                    seen_names.add(name)
                label_str = self._format_labels(metric.labels)
                base_labels = metric.labels

                # Bucket lines
                for bound, count in sorted(metric.bucket_counts.items()):
                    if bound == float("inf"):
                        le = "+Inf"
                    else:
                        le = str(bound)
                    bucket_labels = {**base_labels, "le": le}
                    bl = self._format_labels(bucket_labels)
                    lines.append(f"{name}_bucket{bl} {count}")

                # Sum and count
                lines.append(f"{name}_sum{label_str} {metric.sum}")
                lines.append(f"{name}_count{label_str} {metric.count}")

        lines.append("")  # trailing newline
        return "\n".join(lines)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels dict as Prometheus label string."""
        if not labels:
            return ""
        pairs = ", ".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return "{" + pairs + "}"

    def export_to_file(self, filepath: str) -> None:
        """Write Prometheus metrics to a file."""
        content = self.export()
        with open(filepath, "w") as f:
            f.write(content)
