#!/usr/bin/env python3
"""
self-healing/health_diff.py — P0 Self-Healing Audit
Channel restart detection via health cache polling.

Detects:
  - Channel stop (running=true→false) → self_heal_detected
  - Channel restart (running=false→true) → self_heal_recovered (with duration_ms)
  - Channel connection loss (connected=false)
  - Error state changes

Tracks recovery duration by pairing detected→recovered events.
"""

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


HEALTH_CMD = ["openclaw", "health", "--json"]
STATE_DIR = Path("/home/dragonfive/.openclaw/self-healing/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)
CHANNEL_STATE_FILE = STATE_DIR / "channel_state.json"
PENDING_RECOVERY_FILE = STATE_DIR / "pending_recovery.json"
OBSERVER_STATE_FILE = STATE_DIR / "observer_state.json"


def fetch_health() -> dict | None:
    try:
        result = subprocess.run(HEALTH_CMD, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[health_diff] fetch failed: {e}", file=sys.stderr)
        return None


def load_json(path: Path):
    """Load any JSON file (dict or list)."""
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_json(path: Path, data):
    """Save data to JSON file (dict or list)."""
    path.write_text(json.dumps(data, indent=2, default=str))


def build_channel_snapshot(health: dict) -> dict:
    snapshot = {}
    for channel_id, channel_data in health.get("channels", {}).items():
        if "running" in channel_data:
            key = f"{channel_id}/{channel_data.get('accountId', 'default')}"
            snapshot[key] = {
                "running": channel_data.get("running"),
                "connected": channel_data.get("connected"),
                "lastStartAt": channel_data.get("lastStartAt"),
                "lastStopAt": channel_data.get("lastStopAt"),
                "lastError": channel_data.get("lastError"),
                "restartPending": channel_data.get("restartPending", False),
            }
        accounts = channel_data.get("accounts", {})
        for acc_id, acc_data in accounts.items():
            key = f"{channel_id}/{acc_id}"
            snapshot[key] = {
                "running": acc_data.get("running"),
                "connected": acc_data.get("connected"),
                "lastStartAt": acc_data.get("lastStartAt"),
                "lastStopAt": acc_data.get("lastStopAt"),
                "lastError": acc_data.get("lastError"),
                "restartPending": acc_data.get("restartPending", False),
            }
    return snapshot


def check_observer_initialized() -> bool:
    """Check if first baseline snapshot has been taken."""
    state = load_json(OBSERVER_STATE_FILE)
    return state.get("baseline_created") is True


def mark_observer_initialized():
    save_json(OBSERVER_STATE_FILE, {
        "baseline_created": True,
        "initialized_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def detect_events(prev: dict, curr: dict) -> tuple[list[dict], list[dict]]:
    """
    Compare two snapshots and return self-healing events.
    Returns: (events_to_emit, events_to_track_recovery)
    events_to_emit: ready for immediate write
    events_to_track_recovery: failures tracked for pairing with future recovery
    """
    events = []
    track_recovery = []
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ms = int(time.time() * 1000)
    trace_id = str(uuid.uuid4())

    all_keys = set(prev.keys()) | set(curr.keys())
    for key in sorted(all_keys):
        prev_state = prev.get(key, {})
        curr_state = curr.get(key, {})
        channel, account = key.split("/", 1)

        # First run baseline: skip event generation
        if not prev_state or prev_state == {}:
            continue

        # Detect stop: running=true → running=false
        if prev_state.get("running") and not curr_state.get("running"):
            detected_event = {
                "event_type": "self_healing",
                "trace_id": f"{trace_id}-detected-{key.replace('/', '-')}",
                "timestamp": now_utc,
                "component": channel,
                "account": account,
                "action": "detected",
                "result": "unknown",
                "reason": curr_state.get("lastError") or "channel_stopped",
                "before_state": json.dumps({"running": True, "connected": prev_state.get("connected")}),
                "after_state": json.dumps({"running": False, "connected": curr_state.get("connected")}),
                "verified": False,
                "details": {
                    "lastError": curr_state.get("lastError"),
                    "lastStopAt": curr_state.get("lastStopAt"),
                    "phase": "detected",
                },
            }
            events.append(detected_event)
            track_recovery.append({
                "key": key,
                "detected_at": now_utc,
                "detected_ms": now_ms,
                "trace_id": f"{trace_id}-detected-{key.replace('/', '-')}",
                "reason": curr_state.get("lastError") or "channel_stopped",
            })

        # Detect restart: running=false → running=true
        if not prev_state.get("running") and curr_state.get("running"):
            restart_event = {
                "event_type": "self_healing",
                "trace_id": f"{trace_id}-restart-{key.replace('/', '-')}",
                "timestamp": now_utc,
                "component": channel,
                "account": account,
                "action": "restart",
                "result": "success",
                "reason": "channel_restart_detected",
                "before_state": json.dumps({"running": False, "connected": prev_state.get("connected")}),
                "after_state": json.dumps({"running": True, "connected": curr_state.get("connected")}),
                "verified": curr_state.get("connected") is True,
                "details": {
                    "lastStartAt": curr_state.get("lastStartAt"),
                    "lastStopAt": prev_state.get("lastStopAt"),
                    "phase": "recovered",
                },
            }
            events.append(restart_event)

        # Detect error state change
        prev_err = prev_state.get("lastError")
        curr_err = curr_state.get("lastError")
        if prev_err != curr_err and curr_err is not None:
            events.append({
                "event_type": "self_healing",
                "trace_id": f"{trace_id}-error-{key.replace('/', '-')}",
                "timestamp": now_utc,
                "component": channel,
                "account": account,
                "action": "error",
                "result": "unknown",
                "reason": f"error_state_changed: {curr_err[:200]}",
                "before_state": json.dumps({"lastError": prev_err}),
                "after_state": json.dumps({"lastError": curr_err}),
                "verified": False,
                "details": {"error": curr_err, "phase": "detected"},
            })

    return events, track_recovery


def compute_recovery_duration(
    events: list[dict], pending: list[dict]
) -> tuple[list[dict], list[dict]]:
    """
    Pair detected→recovered events to compute duration_ms.
    Returns: (updated_events, remaining_pending)
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ms = int(time.time() * 1000)

    # Build set of recovered keys from this cycle
    recovered_keys = set()
    for evt in events:
        if evt.get("action") == "restart" and evt.get("result") == "success":
            key = f"{evt['component']}/{evt['account']}"
            recovered_keys.add(key)

    remaining = []
    paired = []

    for pend in pending:
        if pend["key"] in recovered_keys:
            duration_ms = now_ms - pend.get("detected_ms", now_ms)
            pair = {
                "event_type": "self_healing",
                "trace_id": pend["trace_id"].replace("-detected-", "-recovered-"),
                "timestamp": now_utc,
                "component": pend["key"].split("/")[0],
                "account": pend["key"].split("/")[1] if "/" in pend["key"] else "default",
                "action": "recovered",
                "result": "success",
                "reason": f"recovery_complete: {pend.get('reason', '')}",
                "duration_ms": max(0, duration_ms),
                "detected_at": pend["detected_at"],
                "verified": True,
                "details": {"paired_trace": pend["trace_id"]},
            }
            paired.append(pair)
        else:
            remaining.append(pend)

    return paired, remaining


def run() -> list[dict]:
    """One cycle: fetch → diff → compute recovery → return events."""
    health = fetch_health()
    if not health:
        print("[health_diff] no health data", file=sys.stderr)
        return []

    # First run initialization
    if not check_observer_initialized():
        prev = {}
        curr = build_channel_snapshot(health)
        save_json(CHANNEL_STATE_FILE, curr)
        mark_observer_initialized()
        print("[health_diff] baseline initialized, no events", file=sys.stderr)
        return []

    prev = load_json(CHANNEL_STATE_FILE)
    curr = build_channel_snapshot(health)
    raw_pending = load_json(PENDING_RECOVERY_FILE)
    pending = raw_pending if isinstance(raw_pending, list) else []

    events, new_pending = detect_events(prev, curr)

    # Match pending failures with new recoveries
    recovery_events, remaining_pending = compute_recovery_duration(events, pending)
    events.extend(recovery_events)

    # Track new failures for future pairing
    remaining_pending.extend(new_pending)
    save_json(PENDING_RECOVERY_FILE, remaining_pending)
    save_json(CHANNEL_STATE_FILE, curr)

    return events


if __name__ == "__main__":
    events = run()
    if events:
        print(json.dumps(events, indent=2))
    else:
        print(json.dumps([]))
