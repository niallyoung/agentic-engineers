#!/usr/bin/env python3
"""
Lead Engineer Gray-Zone Review CLI

Interactive tool for reviewing 70–79 HANDBACK decisions.

Usage:
    python3 orchestration/tools/lead_review_cli.py list
    python3 orchestration/tools/lead_review_cli.py review <task_id>
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Project root detection
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REVIEWS_FILE = PROJECT_ROOT / "data" / "gray_zone_reviews.json"


def list_pending_reviews() -> None:
    """Show all gray-zone HANDBACKs waiting for Lead Engineer review."""
    reviews = _load_reviews()
    pending = [r for r in reviews.values() if r.get("status") == "pending"]
    if not pending:
        print("✅ No pending gray-zone reviews.")
        return
    print(f"\n=== PENDING GRAY-ZONE REVIEWS ({len(pending)}) ===")
    for r in pending:
        print(f"  • {r['task_id']}  score={r.get('score', '?')}  risk={r.get('risk_level', '?')}")
    print()


def review_handback(task_id: str) -> None:
    """Interactive review workflow for a gray-zone HANDBACK."""
    reviews = _load_reviews()
    review = reviews.get(task_id, {
        "task_id": task_id,
        "score": "?",
        "risk_level": "?",
        "criteria_met": "?",
        "coverage": "?",
        "status": "pending",
    })

    print(f"\n=== GRAY-ZONE REVIEW: {task_id} ===")
    print(f"Score: {review.get('score', '?')}/100")
    print(f"Risk Level: {review.get('risk_level', '?')}")
    print(f"Criteria Met: {review.get('criteria_met', '?')}")
    print(f"Coverage: {review.get('coverage', '?')}%")
    reasoning = review.get("reasoning", "")
    if reasoning:
        print(f"\nAnalysis: {reasoning}")
    print("\n--- DECISION ---")

    while True:
        choice = input("(A)ccept / (C)onditional / (R)ework / (V)iew details? [a/c/r/v]: ").strip().lower()
        if choice == "v":
            print(json.dumps(review, indent=2))
            continue
        elif choice == "a":
            notes = input("Notes (Enter to use default): ").strip() or "Accepted despite 70–79 score; verified low risk"
            save_review_decision(task_id, "ACCEPT", notes)
            print(f"\n✅ Review recorded: ACCEPT\nNotes: {notes}\n")
            break
        elif choice == "c":
            notes = input("Conditional notes: ").strip()
            items_raw = input("Follow-up items (comma-separated): ").strip()
            items = [i.strip() for i in items_raw.split(",") if i.strip()]
            save_review_decision(task_id, "CONDITIONAL", notes)
            if items:
                generate_follow_up_issue(task_id, items)
            print(f"\n⚠️  Review recorded: CONDITIONAL\nNotes: {notes}\n")
            break
        elif choice == "r":
            notes = input("Rework reason: ").strip()
            save_review_decision(task_id, "REWORK", notes)
            print(f"\n❌ Review recorded: REWORK\nReason: {notes}\n")
            break
        else:
            print("Please enter a, c, r, or v.")


def save_review_decision(task_id: str, decision: str, notes: str) -> None:
    """Persist a review decision to the reviews file."""
    REVIEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    reviews = _load_reviews()
    reviews[task_id] = {
        **reviews.get(task_id, {"task_id": task_id}),
        "decision": decision,
        "notes": notes,
        "status": "reviewed",
        "reviewed_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(REVIEWS_FILE, "w") as f:
        json.dump(reviews, f, indent=2)


def generate_follow_up_issue(task_id: str, items: list) -> None:
    """Create a GitHub issue for CONDITIONAL approval follow-up items."""
    title = f"{task_id}: Conditional approval follow-up"
    body = "## Follow-up items from gray-zone conditional approval\n\n"
    body += "\n".join(f"- [ ] {item}" for item in items)
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body,
             "--label", "follow-up,technical-debt"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"📋 GitHub issue created: {result.stdout.strip()}")
        else:
            print(f"⚠️  Could not create GitHub issue: {result.stderr.strip()}")
            print("Follow-up items:\n" + body)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"⚠️  gh CLI unavailable ({e}). Follow-up items:\n{body}")


def _load_reviews() -> dict:
    """Load existing reviews from the reviews file."""
    if REVIEWS_FILE.exists():
        with open(REVIEWS_FILE) as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        list_pending_reviews()
    elif cmd == "review" and len(sys.argv) >= 3:
        review_handback(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
