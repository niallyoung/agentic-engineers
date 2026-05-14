"""
Result Aggregator Module

Aggregates results from child tasks into a unified parent HANDBACK.

Algorithm:
  1. Collect all @output fields from child HANDBACKs.
  2. Compute weighted quality score (effort-weighted average).
  3. Sum tokens and costs across children.
  4. Identify failures and build children_failed list.
  5. Determine result_aggregation_status.
  6. Return aggregated HANDBACK dict.
"""

import time
from typing import Any, Dict, List, Optional


# Effort weights for quality score calculation
_EFFORT_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
}
_DEFAULT_WEIGHT = 2  # fallback if effort not present


class ResultAggregator:
    """Aggregate results from child tasks into a parent HANDBACK."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate(
        self,
        parent_task_id: str,
        child_handbacks: List[Dict],
        failure_mode: str = "partial",
    ) -> Dict:
        """
        Aggregate child results into a parent HANDBACK structure.

        Args:
            parent_task_id:   Task ID of the parent task.
            child_handbacks:  List of HANDBACK dicts from completed child tasks.
            failure_mode:     How to handle failed children:
                                "all_or_nothing" – fail parent if any child fails
                                "partial"        – continue with partial results (default)
                                "retry"          – mark failures for retry (not yet
                                                   implemented; behaves like "partial")

        Returns:
            Dict with aggregated HANDBACK fields:
              children_created           – all child task_ids
              children_results           – per-child {status, output, quality}
              children_failed            – ids of failed/blocked children
              result_aggregation_status  – all_complete | partial | timed_out
              metrics                    – aggregated tokens, costs, quality
        """
        if not child_handbacks:
            return self._empty_aggregate(parent_task_id)

        children_results: Dict[str, Any] = {}
        children_failed: List[str] = []
        children_created: List[str] = []

        total_tokens_in = 0
        total_tokens_out = 0
        total_cost = 0.0
        quality_numerator = 0.0
        quality_denominator = 0.0

        for hb in child_handbacks:
            task_id = hb.get("task_id", "unknown")
            status = hb.get("status", "unknown")
            quality = float(hb.get("quality_score", 0))
            effort = hb.get("effort", "medium")
            weight = _EFFORT_WEIGHTS.get(effort, _DEFAULT_WEIGHT)

            children_created.append(task_id)
            children_results[task_id] = {
                "status": status,
                "output": hb.get("output", hb.get("deliverables")),
                "quality": quality,
            }

            if status in ("failed", "blocked"):
                children_failed.append(task_id)

            # Weighted quality accumulation
            quality_numerator += quality * weight
            quality_denominator += weight

            # Token / cost aggregation
            total_tokens_in += hb.get("tokens_in", 0)
            total_tokens_out += hb.get("tokens_out", 0)
            total_cost += float(hb.get("cost", 0.0))

        # Overall quality: weighted average
        aggregated_quality = (
            round(quality_numerator / quality_denominator, 2)
            if quality_denominator > 0
            else 0.0
        )

        # Determine aggregation status
        agg_status = self._determine_aggregation_status(
            child_handbacks, children_failed, failure_mode
        )

        # Top-level HANDBACK status
        if agg_status == "all_complete" and not children_failed:
            top_status = "complete"
        elif children_failed and failure_mode == "all_or_nothing":
            top_status = "failed"
        else:
            top_status = "partial" if children_failed else "complete"

        return {
            "task_id": parent_task_id,
            "status": top_status,
            "children_created": children_created,
            "children_results": children_results,
            "children_failed": children_failed,
            "result_aggregation_status": agg_status,
            "metrics": {
                "quality": aggregated_quality,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "total_tokens": total_tokens_in + total_tokens_out,
                "cost": round(total_cost, 6),
                "children_count": len(child_handbacks),
                "children_failed_count": len(children_failed),
            },
        }

    def calculate_quality_score(self, child_handbacks: List[Dict]) -> float:
        """
        Compute effort-weighted average quality score.

        Weight mapping:
          high   → 3×
          medium → 2×
          low    → 1×
          (absent) → 2× (default)

        Args:
            child_handbacks: List of HANDBACK dicts.

        Returns:
            Weighted-average quality score (float, 0–100).
        """
        if not child_handbacks:
            return 0.0

        numerator = 0.0
        denominator = 0.0

        for hb in child_handbacks:
            quality = float(hb.get("quality_score", 0))
            effort = hb.get("effort", "medium")
            weight = _EFFORT_WEIGHTS.get(effort, _DEFAULT_WEIGHT)
            numerator += quality * weight
            denominator += weight

        return round(numerator / denominator, 2) if denominator > 0 else 0.0

    def handle_child_failures(
        self,
        child_failures: List[Dict],
        failure_mode: str = "partial",
    ) -> Dict:
        """
        Handle failed child tasks.

        Options (failure_mode):
          "all_or_nothing" – parent should fail; returns status="failed"
          "partial"        – parent continues with remaining children
          "retry"          – mark for retry (returns status="partial" + retry hints)

        Args:
            child_failures: List of failed HANDBACK dicts.
            failure_mode:   Strategy for handling failures.

        Returns:
            Dict with:
              status          – "failed" | "partial"
              failed_task_ids – list of failed task IDs
              failure_summary – brief description
              retry_hints     – (only for "retry" mode) list of task IDs to retry
        """
        failed_ids = [hb.get("task_id", "unknown") for hb in child_failures]
        failure_reasons = [
            hb.get("notes", hb.get("failure_reason", "no reason provided"))
            for hb in child_failures
        ]

        if failure_mode == "all_or_nothing":
            return {
                "status": "failed",
                "failed_task_ids": failed_ids,
                "failure_summary": (
                    f"{len(failed_ids)} child task(s) failed; "
                    f"parent fails in all_or_nothing mode. "
                    f"Reasons: {'; '.join(failure_reasons[:3])}"
                ),
            }

        result = {
            "status": "partial",
            "failed_task_ids": failed_ids,
            "failure_summary": (
                f"{len(failed_ids)} child task(s) failed; "
                f"continuing with partial results."
            ),
        }

        if failure_mode == "retry":
            result["retry_hints"] = failed_ids
            result["failure_summary"] = (
                f"{len(failed_ids)} child task(s) failed and are queued for retry."
            )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _determine_aggregation_status(
        self,
        child_handbacks: List[Dict],
        children_failed: List[str],
        failure_mode: str,
    ) -> str:
        """Return the result_aggregation_status string."""
        if not children_failed:
            return "all_complete"

        if failure_mode == "all_or_nothing":
            return "partial"  # caller will set top status=failed

        return "partial"

    @staticmethod
    def _empty_aggregate(parent_task_id: str) -> Dict:
        """Return an empty aggregate structure when there are no children."""
        return {
            "task_id": parent_task_id,
            "status": "complete",
            "children_created": [],
            "children_results": {},
            "children_failed": [],
            "result_aggregation_status": "all_complete",
            "metrics": {
                "quality": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "children_count": 0,
                "children_failed_count": 0,
            },
        }


class ChildWaiter:
    """
    Poll the queue until all children of a parent task have completed.

    Used by OrchestratorAgent.wait_for_children().
    """

    def __init__(self, queue_ops, poll_interval: float = 1.0):
        """
        Args:
            queue_ops:      QueueOperations instance (for query_tasks).
            poll_interval:  Seconds between polls (default 1.0 for tests;
                            production should use ~5s).
        """
        self.queue_ops = queue_ops
        self.poll_interval = poll_interval

    def wait(
        self,
        parent_task_id: str,
        expected_children: List[str],
        timeout_seconds: float = 3600.0,
    ) -> Dict:
        """
        Wait until all expected children reach done/ or failed/.

        Args:
            parent_task_id:    Parent task ID (used for labelling only).
            expected_children: List of child task IDs to wait for.
            timeout_seconds:   Maximum wait time (default 3600 = 1 hour).

        Returns:
            {
                status:           "all_complete" | "partial" | "timed_out",
                children_results: {task_id: handback_dict, ...},
                children_failed:  [task_ids],
                completion_time:  float (seconds elapsed),
            }
        """
        start = time.monotonic()
        remaining = set(expected_children)
        children_results: Dict[str, Dict] = {}
        children_failed: List[str] = []

        while remaining:
            elapsed = time.monotonic() - start
            if elapsed >= timeout_seconds:
                # Timed out — collect whatever we have
                for task_id in list(remaining):
                    children_results[task_id] = {
                        "task_id": task_id,
                        "status": "timed_out",
                        "output": None,
                        "quality_score": 0,
                    }
                    children_failed.append(task_id)
                return {
                    "status": "timed_out",
                    "children_results": children_results,
                    "children_failed": children_failed,
                    "completion_time": elapsed,
                }

            # Check done/ and failed/ for each remaining child
            for task_id in list(remaining):
                done_tasks = self.queue_ops.query_tasks("done")
                failed_tasks = self.queue_ops.query_tasks("failed")

                done_ids = {t.get("task_id") for t in done_tasks}
                failed_ids = {t.get("task_id") for t in failed_tasks}

                if task_id in done_ids:
                    matching = [
                        t for t in done_tasks if t.get("task_id") == task_id
                    ]
                    children_results[task_id] = matching[0] if matching else {
                        "task_id": task_id,
                        "status": "complete",
                        "output": None,
                        "quality_score": 0,
                    }
                    remaining.discard(task_id)

                elif task_id in failed_ids:
                    matching = [
                        t for t in failed_tasks if t.get("task_id") == task_id
                    ]
                    result = matching[0] if matching else {
                        "task_id": task_id,
                        "status": "failed",
                        "output": None,
                        "quality_score": 0,
                    }
                    children_results[task_id] = result
                    children_failed.append(task_id)
                    remaining.discard(task_id)

            if remaining:
                time.sleep(self.poll_interval)

        elapsed = time.monotonic() - start
        agg_status = "all_complete" if not children_failed else "partial"

        return {
            "status": agg_status,
            "children_results": children_results,
            "children_failed": children_failed,
            "completion_time": elapsed,
        }
