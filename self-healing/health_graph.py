#!/usr/bin/env python3
"""
self-healing/health_graph.py — M0 System Health Graph

Collects health signals from 22 modules via:
  - file_output: cron jobs that write to known paths
  - systemd:     oneshot services
  - channel_state: P0 channel health cache

Semantic evaluation:
  ACTIVE  — age < 2x schedule
  IDLE    — 2x ≤ age < 4x schedule
  STALE   — age ≥ 4x schedule
  FAILED  — file missing / empty / parse error

Reuses P0 pattern: snapshot → diff → event.
"""

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml

STATE_DIR = Path("/home/dragonfive/.openclaw/self-healing/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)
HEALTH_GRAPH_PREV = STATE_DIR / "health_graph_prev.json"
MODULES_YAML = Path(__file__).parent / "modules.yaml"
P0_CHANNEL_STATE = STATE_DIR / "channel_state.json"
EVENTS_DIR = Path("/home/dragonfive/.openclaw/events")

# Semantic health states
ACTIVE = "active"
IDLE = "idle"
STALE = "stale"
FAILED = "failed"
UNKNOWN = "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_ms() -> int:
    return int(time.time() * 1000)


def load_json(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, default=str))


def load_modules() -> list[dict]:
    """Load module registry from modules.yaml."""
    if not MODULES_YAML.exists():
        print(f"[health_graph] modules.yaml not found at {MODULES_YAML}", file=sys.stderr)
        return []
    try:
        with open(MODULES_YAML) as f:
            data = yaml.safe_load(f)
        return data.get("modules", [])
    except Exception as e:
        print(f"[health_graph] failed to parse modules.yaml: {e}", file=sys.stderr)
        return []


def evaluate_semantic(age_min: float | None, schedule_min: int) -> str:
    """Map file age to semantic health state using schedule period."""
    if age_min is None:
        return FAILED
    period = max(schedule_min, 1)
    ratio = age_min / period
    if ratio < 2:
        return ACTIVE
    elif ratio < 4:
        return IDLE
    else:
        return STALE


# ─── Health Source Collectors ──────────────────────────────


def check_file_source(mod: dict, now_ms: int) -> dict:
    """Check a file_output module's health via mtime + schedule."""
    path = Path(mod.get("path", ""))
    schedule_min = mod.get("schedule_min", 60)

    if not path.exists():
        return {"state": FAILED, "reason": "file_missing", "age_min": None, "mtime_ms": None}

    try:
        mtime_s = path.stat().st_mtime
    except OSError:
        return {"state": FAILED, "reason": "io_error", "age_min": None, "mtime_ms": None}

    age_min = (now_ms / 1000 - mtime_s) / 60
    state = evaluate_semantic(age_min, schedule_min)

    # Determine reason string
    if state == ACTIVE:
        reason = f"updated_{int(age_min)}m_ago"
    elif state == IDLE:
        reason = f"idle_{int(age_min)}m_since_last_update"
    elif state == STALE:
        reason = f"stale_{int(age_min)}m_since_last_update"
    else:
        reason = "unknown"

    return {
        "state": state,
        "reason": reason,
        "age_min": round(age_min, 1),
        "mtime_ms": int(mtime_s * 1000),
        "schedule_min": schedule_min,
    }


def check_systemd_source(mod: dict) -> dict:
    """Check a systemd module's health via systemctl show (reuses existing logic)."""
    unit = mod["id"]
    now_ms = utc_now_ms()

    try:
        unit_name = f"{mod.get('systemd_unit', unit)}.service"
        show = subprocess.run(
                ["systemctl", "--user", "show", unit_name,
                 "-p", "ActiveState,SubState,Result,ExecMainStartTimestamp,ExecMainExitCode"],
                capture_output=True, text=True, timeout=5,
            )
        props = {}
        for line in show.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v

        active = props.get("ActiveState", "unknown")
        substate = props.get("SubState", "unknown")
        result = props.get("Result", "")
        exit_code = props.get("ExecMainExitCode", "")
        last_start_str = props.get("ExecMainStartTimestamp", "")

        # Parse last run timestamp
        last_run_ms = None
        if last_start_str:
            try:
                dt = datetime.strptime(last_start_str.strip(), "%a %Y-%m-%d %H:%M:%S %Z")
                last_run_ms = int(dt.timestamp() * 1000)
            except ValueError:
                pass

        # Health judgment
        schedule_min = mod.get("schedule_min", 60)

        if active == "active" or (active == "inactive" and substate == "dead" and result == "success"):
            state = ACTIVE
            reason = "completed_ok"
        elif active == "activating":
            state = ACTIVE
            reason = "running"
        elif substate == "failed" or result == "failed" or (exit_code and exit_code != "0"):
            state = FAILED
            reason = f"failed_result_{result}"
        else:
            # Check staleness by last run time
            if last_run_ms:
                age_min = (now_ms - last_run_ms) / 60000
                state = evaluate_semantic(age_min, schedule_min * 2)  # wider tolerance for systemd
                if state != ACTIVE:
                    reason = f"{state}_{int(age_min)}m"
                else:
                    reason = f"ok_{int(age_min)}m_ago"
            else:
                state = UNKNOWN
                reason = f"{active}_{substate}"

        return {
            "state": state,
            "reason": reason,
            "active": active,
            "substate": substate,
            "result": result,
            "exit_code": exit_code,
            "last_run_ms": last_run_ms,
        }

    except subprocess.TimeoutExpired:
        return {"state": FAILED, "reason": "systemctl_timeout"}
    except FileNotFoundError:
        return {"state": FAILED, "reason": "systemctl_not_found"}


def check_channel_source() -> dict:
    """Check telegram channel health from P0 state (reuses existing logic)."""
    chan = load_json(P0_CHANNEL_STATE)
    if not chan:
        return {}

    nodes = {}
    for key, state in chan.items():
        running = state.get("running") is True
        connected = state.get("connected") is True
        if running and connected:
            nodes[key] = {"state": ACTIVE, "reason": "running"}
        elif running and not connected:
            nodes[key] = {"state": IDLE, "reason": "running_but_disconnected"}
        else:
            nodes[key] = {"state": FAILED, "reason": "not_running"}
    return nodes


# ─── Snapshot ──────────────────────────────────────────────


def take_snapshot() -> dict:
    """Take a full system health snapshot by iterating module registry."""
    modules = load_modules()
    now_ms = utc_now_ms()
    snapshot = {"_taken_at": utc_now(), "_taken_ms": now_ms}

    for mod in modules:
        mid = mod["id"]
        stype = mod.get("source", "unknown")
        mtype = mod.get("type", "job")

        # Channel (special type: P0 state file)
        if stype == "channel_state":
            nodes = check_channel_source()
            snapshot[mid] = {"type": mtype, "source": stype, "nodes": nodes}
            continue

        # Systemd services
        if stype == "systemd":
            result = check_systemd_source(mod)
            snapshot[mid] = {"type": mtype, "source": stype, "nodes": {mid: result}}
            continue

        # File output jobs
        if stype == "file":
            result = check_file_source(mod, now_ms)
            snapshot[mid] = {"type": mtype, "source": stype, "nodes": {mid: result}}
            continue

        # Unknown source type
        snapshot[mid] = {"type": mtype, "source": stype, "nodes": {mid: {"state": UNKNOWN, "reason": f"unknown_source_{stype}"}}}

    return snapshot


# ─── Diff ──────────────────────────────────────────────────


def diff_snapshots(prev: dict, curr: dict) -> list[dict]:
    """Compare two snapshots, return health_change events."""
    events = []
    now_utc = utc_now()

    for mod_id, curr_group in curr.items():
        if mod_id.startswith("_"):
            continue

        prev_group = prev.get(mod_id, {})
        curr_nodes = curr_group.get("nodes", {})
        prev_nodes = prev_group.get("nodes", {})

        for node_id, curr_node in curr_nodes.items():
            prev_node = prev_nodes.get(node_id, {})
            prev_state = prev_node.get("state")
            curr_state = curr_node.get("state")

            if prev_state and curr_state and prev_state != curr_state:
                trace_id = str(uuid.uuid4())
                events.append({
                    "event_type": "health_change",
                    "trace_id": f"{trace_id}-{mod_id}-{node_id}",
                    "timestamp": now_utc,
                    "module": mod_id,
                    "node_id": node_id,
                    "type": curr_group.get("type", "job"),
                    "source": curr_group.get("source", "unknown"),
                    "from_state": prev_state,
                    "to_state": curr_state,
                    "reason": curr_node.get("reason", ""),
                    "details": {
                        "previous": prev_node,
                        "current": curr_node,
                    },
                })

    return events


# ─── Public API ────────────────────────────────────────────


def run() -> list[dict]:
    """One observation cycle: snapshot → diff → return events."""
    prev = load_json(HEALTH_GRAPH_PREV)
    curr = take_snapshot()

    if not prev:
        save_json(HEALTH_GRAPH_PREV, curr)
        count = sum(1 for k, v in curr.items() if not k.startswith("_"))
        print(f"[health_graph] baseline: {count} modules registered", file=sys.stderr)
        return []

    events = diff_snapshots(prev, curr)
    save_json(HEALTH_GRAPH_PREV, curr)

    return events


def show_registry():
    """Print current module registry status."""
    modules = load_modules()
    print(f"\nM0 Health Source Registry — {len(modules)} modules")
    print(f"{'ID':30s} {'Type':8s} {'Source':14s} {'Period':>8s}")
    print("-" * 64)
    for m in modules:
        sched = f"{m.get('schedule_min', '?')}min"
        print(f"{m['id']:30s} {m.get('type','?'):8s} {m.get('source','?'):14s} {sched:>8s}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", action="store_true", help="Show module registry")
    parser.add_argument("--snapshot", action="store_true", help="Take one snapshot and print health summary")
    args = parser.parse_args()

    if args.registry:
        show_registry()
        sys.exit(0)

    if args.snapshot:
        snap = take_snapshot()
        print(json.dumps({k: v for k, v in snap.items() if not k.startswith("_")}, indent=2))
        sys.exit(0)

    events = run()
    if events:
        print(json.dumps(events, indent=2))
    else:
        print(json.dumps([]))
