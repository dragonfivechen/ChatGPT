#!/usr/bin/env python3
"""
self-healing/observer.py — P0 Self-Healing Audit Observer Layer Main Loop

Polls openclaw health --json for channel state,
polls openclaw config get for config diff,
writes self-healing events to events/self_healing.jsonl.

Run modes:
  --once       One cycle (for cron)
  --daemon     Continuous loop (for systemd timer, 5min interval)
  --watch      One-shot with verbose output
  --status     Show self-healing summary report
  --tail N     Show last N events
"""

import json
import sys
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from health_diff import run as run_health_diff
from config_audit import run as run_config_audit
from health_graph import run as run_health_graph
from boundary_observe import run as run_boundary_observe
from event_writer import write_events, count_events

DEFAULT_INTERVAL_S = 300
EVENTS_FILE = Path("/home/dragonfive/.openclaw/events/self_healing.jsonl")


def cycle() -> dict:
    events = []

    # P0: Channel restart + recovery tracking
    health_events = run_health_diff()
    events.extend(health_events)

    # P0: Config repair detection
    config_events = run_config_audit()
    events.extend(config_events)

    # P1: Pipeline health graph (state transitions + node health changes)
    graph_events = run_health_graph()
    events.extend(graph_events)

    # Boundary: model isolation violations + gate verification
    boundary_events = run_boundary_observe()
    from boundary_gate import verify as run_boundary_gate
    gate_violations = run_boundary_gate()
    boundary_events += gate_violations
    # boundary_events are deduplicated in boundary_gate; count = new violations only

    if events:
        write_events(events)

    return {
        "health_events": len(health_events),
        "config_events": len(config_events),
        "graph_events": len(graph_events),
        "boundary_events": len(boundary_events),
        "events_written": len(events),
        "total_events": count_events(),
    }


def run_once() -> dict:
    t0 = time.time()
    result = cycle()
    result["cycle_duration_s"] = round(time.time() - t0, 2)
    return result


def run_daemon(interval_s: int = DEFAULT_INTERVAL_S):
    print(f"[observer] daemon mode: interval={interval_s}s", file=sys.stderr)
    while True:
        t0 = time.time()
        result = cycle()
        elapsed = time.time() - t0
        result["cycle_duration_s"] = round(elapsed, 2)
        if result["events_written"] > 0:
            print(
                f"[observer] {result['health_events']}h+{result['config_events']}c "
                f"→ {result['events_written']} written "
                f"(total: {result['total_events']}, cycle: {result['cycle_duration_s']}s)",
                file=sys.stderr,
            )
        sleep_s = max(1, interval_s - elapsed)
        time.sleep(sleep_s)


def load_events() -> list[dict]:
    """Load all events from events file."""
    if not EVENTS_FILE.exists():
        return []
    events = []
    with open(EVENTS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def show_status():
    """Show P0.2 self-healing summary report."""
    events = load_events()
    if not events:
        print("No self-healing events recorded yet.")
        return

    # Filters
    detected = [e for e in events if e.get("action") == "detected"]
    restarts = [e for e in events if e.get("action") == "restart"]
    recovered = [e for e in events if e.get("action") == "recovered"]
    errors = [e for e in events if e.get("action") == "error"]
    repairs = [e for e in events if e.get("action") == "repair"]

    # Component breakdown
    comp_counter = Counter(e.get("component", "unknown") for e in events)

    # Duration stats
    durations = [e.get("duration_ms") for e in recovered if e.get("duration_ms") is not None]
    avg_ms = sum(durations) / len(durations) if durations else 0
    max_ms = max(durations) if durations else 0

    # Detected but not yet recovered
    detected_keys = set(e.get("trace_id") for e in detected)
    recovered_keys = set(e.get("details", {}).get("paired_trace") for e in recovered if e.get("details"))
    unrecovered = detected_keys - recovered_keys

    print("=" * 50)
    print("Self-Healing Audit Summary")
    print("=" * 50)
    print(f"Total events:           {len(events)}")
    print(f"  detected (failure):   {len(detected)}")
    print(f"  restart:              {len(restarts)}")
    print(f"  recovered (with dur): {len(recovered)}")
    print(f"  error changes:        {len(errors)}")
    print(f"  config repairs:       {len(repairs)}")
    print()
    print("Duration (recovery):")
    if durations:
        print(f"  avg:    {avg_ms:.0f}ms ({avg_ms/1000:.1f}s)")
        print(f"  max:    {max_ms:.0f}ms ({max_ms/1000:.1f}s)")
        print(f"  count:  {len(durations)}")
    else:
        print("  (no recovery duration data yet)")
    print()
    print("Component breakdown:")
    for comp, count in comp_counter.most_common():
        print(f"  {comp}: {count}")
    print()
    pending = len(unrecovered)
    print(f"Pending recovery:        {pending}")
    print(f"Unrecovered failures:    {pending}")
    print(f"Recovery failure rate:   {0 if not detected else pending / len(detected) * 100:.1f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S)
    parser.add_argument("--count", action="store_true")
    parser.add_argument("--tail", type=int)

    args = parser.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

    if args.count:
        print(count_events())
        sys.exit(0)

    if args.tail:
        if EVENTS_FILE.exists():
            with open(EVENTS_FILE) as f:
                lines = f.readlines()
            for line in lines[-args.tail:]:
                try:
                    r = json.loads(line.strip())
                    etype = r.get('event_type', '?')
                    if etype == 'health_change':
                        print(
                            f"{r.get('timestamp','?')} | "
                            f"{r.get('group','?')}/{r.get('node_id','?')} | "
                            f"{r.get('from_health','?')}->{r.get('to_health','?')} | "
                            f"{r.get('reason','')[:30]}"
                        )
                    else:
                        print(
                            f"{r.get('timestamp','?')} | "
                            f"{r.get('component','?')}/{r.get('action','?')} | "
                            f"{r.get('result','?')} | "
                            f"dur={r.get('duration_ms','?')}ms"
                        )
                except json.JSONDecodeError:
                    print(f"[invalid] {line.strip()[:80]}")
        else:
            print("No events yet")
        sys.exit(0)

    if args.daemon:
        run_daemon(args.interval)
    elif args.watch or args.once:
        result = run_once()
        print(json.dumps(result, indent=2))
    else:
        result = run_once()
        sys.exit(0 if result["events_written"] == 0 else 1)
