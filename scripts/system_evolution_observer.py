#!/usr/bin/env python3
"""
System Evolution Observation Layer v1.0

汇总已有观察源 → 系统整体状态画像。
不重新扫描，不治理，不规划，不优化。

输入: asset-observation / capability-observation / baseline-observation
输出: system-evolution-observation.jsonl
"""

import json, os, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
OUTPUT = os.path.join(WORKSPACE, "memory/data/system/system-evolution-observation.jsonl")
CST = timezone(timedelta(hours=8))

def ts_now(): return datetime.now(CST).isoformat()
def load_json(path):
    if os.path.isfile(path):
        with open(path) as f:
            try: return json.load(f)
            except: return None
    return None

def read_last_event(path):
    """Read last event from a jsonl file."""
    if not os.path.isfile(path): return None
    with open(path) as f:
        last = None
        for line in f:
            line = line.strip()
            if line:
                try: last = json.loads(line)
                except: pass
    return last

# ─── Input sources ───

def get_asset_state():
    e = read_last_event(os.path.join(WORKSPACE, "memory/data/system/asset-observation.jsonl"))
    if e and e.get("type") == "ASSET_SNAPSHOT":
        return {
            "total": sum(e.get("assets", {}).values()),
            "assets": e.get("assets"),
            "classification": e.get("classification"),
            "snapshot_id": e.get("snapshot_id"),
        }
    return None

def get_capability_state():
    e = read_last_event(os.path.join(WORKSPACE, "memory/data/system/capability-observation.jsonl"))
    if e and e.get("type") == "CAPABILITY_SNAPSHOT":
        caps = e.get("capabilities", [])
        by_domain = defaultdict(lambda: {"total": 0, "available": 0})
        for c in caps:
            d = c.get("domain", "unknown")
            by_domain[d]["total"] += 1
            if c.get("status") == "available":
                by_domain[d]["available"] += 1
        return {
            "total": e.get("status_summary", {}).get("total", 0),
            "available": e.get("status_summary", {}).get("available", 0),
            "by_domain": {k: dict(v) for k, v in by_domain.items()},
        }
    return None

def get_baseline_state():
    e = read_last_event(os.path.join(WORKSPACE, "memory/data/system/baseline-observation.jsonl"))
    if e and e.get("type") == "BASELINE_OBSERVATION":
        return {
            "drift_count": e.get("drift_count", 0),
            "drifts": [d["detail"] for d in e.get("drift", [])],
            "contracts_frozen": e.get("baseline_refs", {}).get("frozen_contracts", 0),
            "asset_snapshot": e.get("baseline_refs", {}).get("asset_snapshot"),
            "capability_snapshot": e.get("baseline_refs", {}).get("capability_snapshot"),
        }
    return None

def get_construction_delta():
    """Count files by type in workspace (lightweight approximation)."""
    counts = {"docs": 0, "scripts": 0, "configs": 0, "timers": 0}
    docs_dir = os.path.join(WORKSPACE, "docs")
    scripts_dir = os.path.join(WORKSPACE, "scripts")
    config_dir = os.path.join(WORKSPACE, "config")
    timer_dir = os.path.join(WORKSPACE, "config/systemd")

    if os.path.isdir(docs_dir):
        counts["docs"] = len([f for f in os.listdir(docs_dir) if f.endswith(".md")])
    if os.path.isdir(scripts_dir):
        counts["scripts"] = len([f for f in os.listdir(scripts_dir) if f.endswith((".py", ".sh"))])
    if os.path.isdir(config_dir):
        counts["configs"] = len([f for f in os.listdir(config_dir) if f.endswith((".json", ".yaml", ".toml"))])
    if os.path.isdir(timer_dir):
        counts["timers"] = len([f for f in os.listdir(timer_dir) if f.endswith(".timer")])
    return counts

# ─── Main ───

def main():
    print("[EVOLUTION-OBS] v1.0 — System Evolution Observation")
    print()

    asset = get_asset_state()
    cap = get_capability_state()
    baseline = get_baseline_state()
    construction = get_construction_delta()

    # Domain capability coverage
    cap_coverage = {}
    if cap and "by_domain" in cap:
        for domain, info in cap["by_domain"].items():
            cap_coverage[domain] = f"{info['available']}/{info['total']}"

    # Build event
    event = {
        "type": "SYSTEM_EVOLUTION",
        "version": "1.0",
        "ts": ts_now(),
        "system_size": {
            "assets_total": asset["total"] if asset else 0,
            "modules": asset["assets"].get("modules", 0) if asset and asset.get("assets") else 0,
            "contracts": asset["assets"].get("contracts", 0) if asset and asset.get("assets") else 0,
            "scripts": asset["assets"].get("scripts", 0) if asset and asset.get("assets") else 0,
            "services": asset["assets"].get("services", 0) if asset and asset.get("assets") else 0,
            "timers": asset["assets"].get("timers", 0) if asset and asset.get("assets") else 0,
            "capabilities": cap["total"] if cap else 0,
        },
        "state_distribution": {
            "asset_classification": asset["classification"] if asset and asset.get("classification") else {},
            "capability_available": f"{cap['available']}/{cap['total']}" if cap else "N/A",
        },
        "capability_coverage": cap_coverage,
        "construction": {
            "doc_files": construction["docs"],
            "script_files": construction["scripts"],
            "config_files": construction["configs"],
            "timer_files": construction["timers"],
        },
        "drift_summary": {
            "total_drifts": baseline["drift_count"] if baseline else 0,
            "drift_details": baseline["drifts"] if baseline else [],
            "baseline_snapshot": baseline["asset_snapshot"] if baseline else None,
        },
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # Print summary
    print("[SYSTEM SIZE]")
    for k, v in event["system_size"].items():
        print(f"  {k}: {v}")
    print()
    print(f"[CAPABILITY COVERAGE]")
    for d, c in cap_coverage.items():
        print(f"  {d}: {c}")
    print()
    print(f"[DRIFT] {event['drift_summary']['total_drifts']} drifts")
    print()
    print(f"[DONE] system-evolution-observation.jsonl")

    summary = {
        "assets": event["system_size"]["assets_total"],
        "capabilities": f"{event['state_distribution']['capability_available']}",
        "drifts": event["drift_summary"]["total_drifts"],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
