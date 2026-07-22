#!/usr/bin/env python3
"""
self-healing/provider_observe.py — P3 Model Reliability Observation

Tracks provider-level success/failure metrics from sessions.json.
Outputs per-session detail lines + cumulative stats.

Per-session records capture the complete call lifecycle:
  provider, model, status, runtime_ms, tokens

Constraints:
  - Read-only: never writes sessions.json
  - Append-only: outputs to events/provider_observe.jsonl
  - No blocking: does not intercept model calls

Error type mapping (from session status):
  done     → success
  timeout  → timeout
  failed   → unknown (no further granularity from sessions.json)
  running  → active (incomplete)
  ?        → unknown (no terminal status)
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

SESSIONS_FILE = Path("/home/dragonfive/.openclaw/agents/main/sessions/sessions.json")
STATE_FILE = Path("/home/dragonfive/.openclaw/self-healing/state/provider_observe.json")
OUTPUT_FILE = Path("/home/dragonfive/.openclaw/events/provider_observe.jsonl")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# Error type mapping
STATUS_TO_ERROR = {
    "done": "success",
    "timeout": "timeout",
    "failed": "unknown_error",
    "error": "unknown_error",
    "cancelled": "cancelled",
    "interrupted": "interrupted",
    "running": None,     # not terminal
    "?": None,           # not terminal
}


def load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        try:
            return json.loads(SESSIONS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "last_session_count": 0,
        "written_ids": [],  # session ids already written per-call
    }


def save_state(state: dict):
    # Trim written_ids to prevent unbounded growth
    if len(state.get("written_ids", [])) > 10000:
        state["written_ids"] = state["written_ids"][-1000:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def compute_session_fingerprint(sid: str, s: dict) -> str:
    """Deterministic fingerprint for a session row to detect changes."""
    key = f"{sid}|{s.get('status','?')}|{s.get('runtimeMs','')}|{s.get('totalTokens','')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def run() -> int:
    """One cycle: diff sessions → write per-session records → return count."""
    sessions = load_sessions()
    if not sessions:
        return 0

    state = load_state()
    written_ids = set(state.get("written_ids", []))
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_records = []

    for sid, s in sessions.items():
        fp = compute_session_fingerprint(sid, s)
        if fp in written_ids:
            continue

        status = s.get("status", "?")
        provider = s.get("modelProvider") or "unknown"
        model = s.get("model") or "?"
        runtime_ms = s.get("runtimeMs")
        total_tokens = s.get("totalTokens") or 0
        started_at = s.get("startedAt")
        ended_at = s.get("endedAt")
        error_type = STATUS_TO_ERROR.get(status, "unknown")

        # Compute input/output tokens if available (sessions.json may or may not have split)
        input_tokens = s.get("inputTokens")
        output_tokens = s.get("outputTokens")
        if input_tokens is None or output_tokens is None:
            # totalTokens only — no split available from sessions.json
            input_tokens = None
            output_tokens = None

        # Derive source model from session key
        if "telegram:" in sid or sid.startswith("agent:main:telegram"):
            src_model, src_agent, src_chan, src_class = "jin", "tg-agent", "telegram", "experiment"
        elif "cron:" in sid:
            src_model, src_agent, src_chan, src_class = "system", "system", "system", "system"
        else:
            src_model, src_agent, src_chan, src_class = "huo", "main", "terminal", "production"

        record = {
            "event_type": "provider_call",
            "ts": now_utc,
            "session_id": sid[:48],
            "source_model": src_model,
            "agent": src_agent,
            "channel": src_chan,
            "data_class": src_class,
            "provider": provider,
            "model": model,
            "status": status,
            "error_type": error_type,
            "runtime_ms": runtime_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "retry_count": None,  # sessions.json does not expose retry count
            "started_at": started_at,
            "ended_at": ended_at,
            "_fingerprint": fp,
        }
        new_records.append(record)

    if new_records:
        # Write per-session records
        with open(OUTPUT_FILE, "a") as f:
            for rec in new_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Update written_ids
        updated_ids = set(written_ids)
        for rec in new_records:
            updated_ids.add(rec["_fingerprint"])
        state["written_ids"] = list(updated_ids)
        state["last_session_count"] = len(sessions)
        state["last_observed_at"] = now_utc
        save_state(state)

    return len(new_records)


def show_summary() -> dict:
    """Aggregate all provider_call events for status display.

    Failure rate is calculated on terminal sessions only:
    done + timeout + failed = denominator.
    "?" (no status) and "running" are excluded from failure rate.
    """
    if not OUTPUT_FILE.exists():
        return {"records": 0}

    records = []
    with open(OUTPUT_FILE) as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    total = len(records)
    if total == 0:
        return {"records": 0}

    by_provider = {}
    by_status = Counter()
    runtimes = []
    tokens_total = 0

    terminal_statuses = {"done", "timeout", "failed", "error", "cancelled"}

    by_source = Counter()
    for r in records:
        src = r.get("source_model", "?")
        by_source[src] += 1

        prov = r.get("provider", "?")
        if prov not in by_provider:
            by_provider[prov] = {"success": 0, "timeout": 0, "failure": 0, "active": 0, "incomplete": 0}

        status = r.get("status", "?")
        error_type = r.get("error_type", "unknown")

        by_status[status] += 1

        if error_type == "success":
            by_provider[prov]["success"] += 1
        elif error_type == "timeout":
            by_provider[prov]["timeout"] += 1
        elif status in ("failed", "error", "cancelled", "interrupted"):
            by_provider[prov]["failure"] += 1
        elif status == "running":
            by_provider[prov]["active"] += 1
        else:
            by_provider[prov]["incomplete"] += 1

        rt = r.get("runtime_ms")
        if rt and rt > 0:
            runtimes.append(rt)

        tk = r.get("total_tokens", 0) or 0
        tokens_total += tk

    result = {"records": total}
    for prov, counts in sorted(by_provider.items()):
        terminal = counts["success"] + counts["timeout"] + counts["failure"]
        rate = round((counts["timeout"] + counts["failure"]) / terminal * 100, 1) if terminal > 0 else 0
        result[prov] = {
            **counts,
            "terminal": terminal,
            "failure_rate_pct": rate,
            "note": "failure_rate = (timeout+failure) / terminal_sessions" if terminal > 0 else "no_terminal_sessions",
        }

    result["by_status"] = dict(by_status.most_common())
    result["by_source"] = dict(by_source.most_common())
    result["token_total_k"] = round(tokens_total / 1000, 1)

    if runtimes:
        runtimes.sort()
        n = len(runtimes)
        result["runtime"] = {
            "count": n,
            "avg_ms": round(sum(runtimes) / n),
            "p50_ms": runtimes[n // 2],
            "p95_ms": runtimes[int(n * 0.95)],
            "p99_ms": runtimes[int(n * 0.99)],
            "max_ms": runtimes[-1],
        }

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        summary = show_summary()
        print(json.dumps(summary, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "--tail":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                lines = f.readlines()
            for line in lines[-n:]:
                r = json.loads(line.strip())
                et = r.get('error_type') or '-'
                rt = r.get('runtime_ms')
                rt_str = f'{rt}ms' if rt else '-'
                tk = r.get('total_tokens', 0) or 0
                print(
                    f"{r.get('ts','?')} | {r.get('provider','?'):12s} "
                    f"| {r.get('status','?'):8s} | {et:12s} "
                    f"| {rt_str:>10s} | tk={tk}"
                )
        else:
            print("no data")
    else:
        n = run()
        if n > 0:
            print(f"wrote {n} new records")
        else:
            print("no new data")
