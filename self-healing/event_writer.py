#!/usr/bin/env python3
"""
self-healing/event_writer.py — Write self-healing + health-graph events
to Event Source of Truth with source provenance.

All events include:
  source_model: huo | jin | system (which identity triggered this)
  agent: main | tg-agent | system
  channel: terminal | telegram | system
  data_class: production | experiment | system

Output: /home/dragonfive/.openclaw/events/self_healing.jsonl (append-only)
"""

import json
from datetime import datetime, timezone
from pathlib import Path


EVENTS_FILE = Path("/home/dragonfive/.openclaw/events/self_healing.jsonl")
EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def resolve_source(event: dict) -> dict:
    """
    Derive source_model / agent / channel / data_class from event context.
    Producers can override by setting event['source_model'] etc.
    Fallback: system (for automated observation events).
    """
    source = event.get("source_model")
    agent = event.get("agent")
    channel = event.get("channel")
    data_class = event.get("data_class")

    # If source_model provided directly, use all provided overrides
    if source:
        return {
            "source_model": source,
            "agent": agent or "system",
            "channel": channel or "system",
            "data_class": data_class or "system",
        }

    # Try to infer from session_id if present
    session_id = event.get("session_id", "")
    if "telegram:" in session_id or session_id.startswith("agent:main:telegram"):
        return {
            "source_model": "jin",
            "agent": "tg-agent",
            "channel": "telegram",
            "data_class": "experiment",
        }
    if "cron:" in session_id:
        return {
            "source_model": "system",
            "agent": "system",
            "channel": "system",
            "data_class": "system",
        }

    # Default: system-level events (health checks, self-healing, etc.)
    return {
        "source_model": "system",
        "agent": "system",
        "channel": "system",
        "data_class": "system",
    }


def write_event(event: dict):
    """Append a single event to the JSONL stream with source provenance."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    etype = event.get("event_type", "self_healing")
    src = resolve_source(event)

    record = {
        "event_type": etype,
        "timestamp": event.get("timestamp", now),
        "trace_id": event.get("trace_id", "unknown"),
        "source_model": src["source_model"],
        "agent": src["agent"],
        "channel": src["channel"],
        "data_class": src["data_class"],
        "_written_at": now,
    }

    if etype == "health_change":
        record["group"] = event.get("group", "unknown")
        record["node_id"] = event.get("node_id", "unknown")
        record["type"] = event.get("type", "unknown")
        record["from_health"] = event.get("from_health", "unknown")
        record["to_health"] = event.get("to_health", "unknown")
        record["reason"] = event.get("reason", "")
        record["details"] = event.get("details", {})
    else:
        record["component"] = event.get("component", "unknown")
        record["account"] = event.get("account", "default")
        record["action"] = event.get("action", "unknown")
        record["result"] = event.get("result", "unknown")
        record["reason"] = event.get("reason", "")
        record["before_state"] = event.get("before_state", "")
        record["after_state"] = event.get("after_state", "")
        record["verified"] = event.get("verified", False)
        record["details"] = event.get("details", {})
        record["changes"] = event.get("changes", [])
        record["duration_ms"] = event.get("duration_ms")

    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def write_events(events: list[dict]) -> list[dict]:
    if not events:
        return []
    return [write_event(e) for e in events]


def count_events() -> int:
    if not EVENTS_FILE.exists():
        return 0
    count = 0
    with open(EVENTS_FILE) as f:
        for _ in f:
            if _.strip():
                count += 1
    return count


def load_events() -> list[dict]:
    if not EVENTS_FILE.exists():
        return []
    out = []
    with open(EVENTS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--count":
        print(count_events())
    elif not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line:
                try:
                    evt = json.loads(line)
                    record = write_event(evt)
                    print(f"written: {record.get('trace_id', '?')[:36]} src={record.get('source_model','?')}")
                except json.JSONDecodeError as e:
                    print(f"skip invalid: {e}", file=sys.stderr)
    else:
        print(f"Usage: echo '<event_json>' | {sys.argv[0]}")
        print(f"       {sys.argv[0]} --count")
