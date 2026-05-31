"""Tests for the queue-query skill (QueueQuery + CLI).

Covers state listing, sizing, orphan detection, done-summary, format-agnostic
reads (json + yaml), session/harness isolation, and CLI dispatch.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.queue_query import QueueQuery, QueueQueryError, main  # noqa: E402

# queue_isolation provides the canonical path math used by the fixtures.
_QI_SCRIPTS = (
    _SKILL_ROOT.parent / "_meta" / "queue-isolation" / "scripts"
)
sys.path.insert(0, str(_QI_SCRIPTS))
import queue_isolation as qi  # noqa: E402

SESSION = "sess-queue-query"
HARNESS = "local"


@pytest.fixture
def queue_root(tmp_path):
    """Initialise an empty canonical queue under a temp base dir."""
    qi.init_queue_structure(SESSION, HARNESS, base_dir=tmp_path)
    return qi.get_queue_path(SESSION, HARNESS, base_dir=tmp_path)


@pytest.fixture
def query(tmp_path, queue_root):
    return QueueQuery(session_id=SESSION, harness=HARNESS, base_dir=tmp_path)


def _write_json_task(queue_root: Path, state: str, task_id: str, **fields) -> Path:
    payload = {"task_id": task_id, **fields}
    path = queue_root / state / f"{task_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_yaml_task(queue_root: Path, state: str, task_id: str, body: str) -> Path:
    path = queue_root / state / f"{task_id}.yaml"
    path.write_text(body, encoding="utf-8")
    return path


# --- construction / path resolution ---------------------------------------

def test_uses_canonical_queue_path(query, tmp_path):
    expected = qi.get_queue_path(SESSION, HARNESS, base_dir=tmp_path)
    assert query.queue_path == expected


# --- ls --------------------------------------------------------------------

def test_ls_empty_state_returns_empty_list(query):
    assert query.ls("incoming") == []


def test_ls_incoming_returns_all_pending_tasks(query, queue_root):
    _write_json_task(queue_root, "incoming", "task-a", role="engineer")
    _write_json_task(queue_root, "incoming", "task-b", role="engineer")
    ids = sorted(t["task_id"] for t in query.ls("incoming"))
    assert ids == ["task-a", "task-b"]


def test_ls_ignores_keepme_and_hidden(query, queue_root):
    # init_queue_structure already dropped .keep.me files
    _write_json_task(queue_root, "incoming", "real-task", role="engineer")
    (queue_root / "incoming" / ".hidden.json").write_text("{}", encoding="utf-8")
    tasks = query.ls("incoming")
    assert [t["task_id"] for t in tasks] == ["real-task"]


def test_ls_invalid_state_raises(query):
    with pytest.raises(QueueQueryError):
        query.ls("nonsense")


def test_ls_reads_yaml_tasks(query, queue_root):
    _write_yaml_task(
        queue_root, "incoming", "yaml-task",
        "task_id: yaml-task\nrole: engineer\nstatus: pending\n",
    )
    tasks = query.ls("incoming")
    assert tasks[0]["task_id"] == "yaml-task"
    assert tasks[0]["role"] == "engineer"


def test_ls_mixed_json_and_yaml(query, queue_root):
    _write_json_task(queue_root, "incoming", "j-task", role="engineer")
    _write_yaml_task(queue_root, "incoming", "y-task", "task_id: y-task\n")
    ids = sorted(t["task_id"] for t in query.ls("incoming"))
    assert ids == ["j-task", "y-task"]


def test_ls_attaches_file_metadata(query, queue_root):
    _write_json_task(queue_root, "done", "meta-task", status="complete")
    task = query.ls("done")[0]
    assert task["_file"] == "meta-task.json"
    assert "_mtime" in task and "_path" in task


# --- size / count ----------------------------------------------------------

def test_count_zero_for_empty(query):
    assert query.count("incoming") == 0


def test_size_counts_incoming_backlog(query, queue_root):
    for i in range(3):
        _write_json_task(queue_root, "incoming", f"t{i}", role="engineer")
    assert query.count("incoming") == 3


def test_count_by_state_reports_all_states(query, queue_root):
    _write_json_task(queue_root, "incoming", "i1")
    _write_json_task(queue_root, "processing", "p1")
    _write_json_task(queue_root, "processing", "p2")
    _write_json_task(queue_root, "done", "d1")
    counts = query.count_by_state()
    assert counts == {"incoming": 1, "processing": 2, "done": 1, "failed": 0}


# --- orphans ---------------------------------------------------------------

def test_orphans_returns_processing_older_than_threshold(query, queue_root):
    path = _write_json_task(queue_root, "processing", "stale", role="engineer")
    old = time.time() - 3600  # 1 hour ago
    os.utime(path, (old, old))
    orphans = query.find_orphans(older_than_minutes=30)
    assert [o["task_id"] for o in orphans] == ["stale"]
    assert orphans[0]["_age_minutes"] >= 30


def test_orphans_excludes_recent_processing_tasks(query, queue_root):
    _write_json_task(queue_root, "processing", "fresh", role="engineer")
    assert query.find_orphans(older_than_minutes=30) == []


def test_orphans_zero_when_processing_empty(query):
    assert query.find_orphans(older_than_minutes=0) == []


def test_orphans_negative_threshold_raises(query):
    with pytest.raises(QueueQueryError):
        query.find_orphans(older_than_minutes=-5)


def test_orphans_only_consider_processing(query, queue_root):
    path = _write_json_task(queue_root, "incoming", "old-incoming")
    old = time.time() - 3600
    os.utime(path, (old, old))
    assert query.find_orphans(older_than_minutes=1) == []


# --- summary ---------------------------------------------------------------

def test_summary_done_aggregates_status_and_next_steps(query, queue_root):
    _write_json_task(queue_root, "done", "d1", status="complete", next_steps="ship it")
    _write_json_task(queue_root, "done", "d2", status="complete")
    _write_json_task(queue_root, "done", "d3", status="partial")
    summary = query.summarize_done()
    assert summary["total"] == 3
    assert summary["by_status"] == {"complete": 2, "partial": 1}
    d1 = next(t for t in summary["tasks"] if t["task_id"] == "d1")
    assert d1["next_steps"] == "ship it"


def test_summary_empty_done(query):
    summary = query.summarize_done()
    assert summary == {"total": 0, "by_status": {}, "tasks": []}


# --- isolation -------------------------------------------------------------

def test_session_isolation_scopes_queries(tmp_path, queue_root):
    _write_json_task(queue_root, "incoming", "mine")
    # A different session sees an empty (uninitialised) queue.
    other = QueueQuery(session_id="other-session", harness=HARNESS, base_dir=tmp_path)
    assert other.count("incoming") == 0


# --- CLI -------------------------------------------------------------------

def _cli(tmp_path, *args):
    return main(["--base-dir", str(tmp_path), "--session-id", SESSION,
                 "--harness", HARNESS, *args])


def test_cli_size_dispatch(tmp_path, queue_root, capsys):
    _write_json_task(queue_root, "incoming", "c1")
    rc = _cli(tmp_path, "--json", "size", "--state", "incoming")
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"incoming": 1}


def test_cli_states_dispatch(tmp_path, queue_root, capsys):
    _write_json_task(queue_root, "processing", "p1")
    rc = _cli(tmp_path, "--json", "states")
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["processing"] == 1 and out["incoming"] == 0


def test_cli_ls_dispatch(tmp_path, queue_root, capsys):
    _write_json_task(queue_root, "incoming", "listme")
    rc = _cli(tmp_path, "ls", "--state", "incoming")
    assert rc == 0
    assert "listme" in capsys.readouterr().out


def test_cli_orphans_older_than(tmp_path, queue_root, capsys):
    path = _write_json_task(queue_root, "processing", "stale")
    old = time.time() - 7200
    os.utime(path, (old, old))
    rc = _cli(tmp_path, "--json", "orphans", "--older-than", "30")
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert [o["task_id"] for o in out] == ["stale"]


def test_cli_summary_dispatch(tmp_path, queue_root, capsys):
    _write_json_task(queue_root, "done", "d1", status="complete")
    rc = _cli(tmp_path, "--json", "summary")
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["total"] == 1


def test_cli_invalid_older_than_returns_2(tmp_path, queue_root, capsys):
    """A negative --older-than raises QueueQueryError → clean exit code 2."""
    rc = _cli(tmp_path, "orphans", "--older-than", "-5")
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_cli_human_readable_output(tmp_path, queue_root, capsys):
    """Without --json the size command prints plain 'state: count' lines."""
    _write_json_task(queue_root, "incoming", "h1")
    rc = _cli(tmp_path, "states")
    assert rc == 0
    out = capsys.readouterr().out
    assert "incoming: 1" in out
    assert "processing: 0" in out


def test_cli_human_readable_list(tmp_path, queue_root, capsys):
    """Without --json, ls prints one task_id per line."""
    _write_json_task(queue_root, "incoming", "plain-task")
    rc = _cli(tmp_path, "ls", "--state", "incoming")
    assert rc == 0
    assert "plain-task" in capsys.readouterr().out


# --- corrupt-file tolerance ------------------------------------------------

def test_corrupt_task_file_does_not_abort_query(query, queue_root):
    """A malformed task must surface as an _error entry, not crash the query."""
    _write_json_task(queue_root, "incoming", "good")
    (queue_root / "incoming" / "broken.json").write_text("{not valid json", encoding="utf-8")
    tasks = {t["task_id"]: t for t in query.ls("incoming")}
    assert "good" in tasks
    assert "_error" in tasks["broken"]


# --- fallback (installed-harness) path-math parity --------------------------

def test_fallback_used_when_queue_isolation_unavailable(tmp_path, monkeypatch):
    """When queue_isolation cannot be imported, _import_queue_isolation returns a
    drift-free fallback that yields the identical canonical layout-A path so the
    skill still works once installed (where _meta/ is excluded)."""
    import scripts.queue_query as qq

    # Simulate the meta-skill being absent: poison the module so `import
    # queue_isolation` raises ImportError inside _import_queue_isolation.
    monkeypatch.setitem(sys.modules, "queue_isolation", None)
    resolved = qq._import_queue_isolation()
    assert isinstance(resolved, qq._FallbackQueueIsolation)

    got = resolved.get_queue_path(SESSION, HARNESS, base_dir=tmp_path)
    expected = qi.get_queue_path(SESSION, HARNESS, base_dir=tmp_path)
    assert got == expected


def test_fallback_rejects_path_traversal(tmp_path):
    """The fallback validates components, blocking traversal injection."""
    from scripts.queue_query import _FallbackQueueIsolation

    fb = _FallbackQueueIsolation()
    with pytest.raises(QueueQueryError):
        fb.get_queue_path("../escape", HARNESS, base_dir=tmp_path)

