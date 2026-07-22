#!/usr/bin/env python3
"""
self-healing/config_audit.py — P0 Self-Healing Audit
Doctor repair detection via config snapshot diff.

Detects config changes between observation cycles.
Captures changes from doctor --fix or manual config edits.

Use:
  1. Take config snapshot A
  2. Wait for doctor or config change
  3. Take config snapshot B
  4. Diff A vs B → audit event
"""

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


CONFIG_PATH = Path("/home/dragonfive/.openclaw/openclaw.yaml")
STATE_DIR = Path("/home/dragonfive/.openclaw/self-healing/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_SNAPSHOT_FILE = STATE_DIR / "config_snapshot.json"


def fetch_config_snapshot() -> dict | None:
    """Fetch current config via openclaw CLI (non-sensitive)."""
    try:
        # Use openclaw config get to fetch current values
        result = subprocess.run(
            ["openclaw", "config", "get"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            # Config get returns YAML; we use it as-is for diff
            return {
                "raw": result.stdout,
                "fetched_at": datetime.now(timezone.utc).timestamp(),
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def load_snapshot() -> dict | None:
    """Load previous config snapshot."""
    if CONFIG_SNAPSHOT_FILE.exists():
        try:
            return json.loads(CONFIG_SNAPSHOT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_snapshot(snap: dict):
    """Persist current config snapshot."""
    CONFIG_SNAPSHOT_FILE.write_text(json.dumps(snap, indent=2))


def detect_changes(prev: dict, curr: dict) -> list[dict]:
    """Compare config snapshots, detect doctor repair events."""
    if not prev or not curr:
        return []

    prev_raw = prev.get("raw", "")
    curr_raw = curr.get("raw", "")

    if prev_raw == curr_raw:
        return []

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    trace_id = str(uuid.uuid4())

    # Simple line-based diff
    prev_lines = prev_raw.splitlines()
    curr_lines = curr_raw.splitlines()
    import difflib
    diff = list(difflib.unified_diff(
        prev_lines, curr_lines,
        fromfile="before", tofile="after",
        n=2,  # context lines
    ))

    # Summarize: extract only the changed lines (starting with + or -)
    changes = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            changes.append(f"ADDED: {line[1:].strip()}")
        elif line.startswith("-") and not line.startswith("---"):
            changes.append(f"REMOVED: {line[1:].strip()}")

    if not changes:
        return []

    return [{
        "event_type": "self_healing",
        "trace_id": f"{trace_id}-config",
        "timestamp": now_utc,
        "component": "config",
        "account": "system",
        "action": "repair",
        "result": "success",
        "reason": "config_change_detected",
        "before_state": "config_snapshot_before",
        "after_state": "config_snapshot_after",
        "verified": True,
        "details": {
            "diff_lines": len(diff),
            "changes_count": len(changes),
        },
        "changes": changes[:50],  # cap at 50 changes
    }]


def run() -> list[dict]:
    """One cycle: snapshot → compare → return events."""
    curr = fetch_config_snapshot()
    if not curr:
        return []

    prev = load_snapshot()
    events = detect_changes(prev, curr)
    save_snapshot(curr)
    return events


if __name__ == "__main__":
    events = run()
    if events:
        print(json.dumps(events, indent=2))
    else:
        print(json.dumps([]))
