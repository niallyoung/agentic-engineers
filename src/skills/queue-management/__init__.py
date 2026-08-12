"""Queue management skill package.

The implementation lives in scripts/queue_ops.py (atomic enqueue, audit
log, ancestry cycle/depth checks, path isolation) and is invoked via the
sys.path convention documented in SKILL.md — not imported through this
package. The former QueueManager class hierarchy was removed in the
2026-08-11 framework slimdown (see docs/spec-proposals/SPEC-2026-005.yaml).
"""
