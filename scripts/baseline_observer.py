#!/usr/bin/env python3
"""
Baseline Observation Layer v1.0

观察系统当前状态相对于冻结基线的变化。
不修改基线，不自动补齐，不审批变更。

输入:
  - CONTRACT-REGISTRY.md (frozen contracts)
  - PHASE_STATUS.json (frozen module status)
  - ASSET-SNAPSHOT events
  - CAP-SNAPSHOT events

输出: baseline-observation.jsonl
"""

import json, os, re
from datetime import datetime, timezone, timedelta

# ─── Asset Root Registry ───
ROOT_REGISTRY = os.path.join(os.path.expanduser("~/.openclaw/workspace"), "config/asset-roots.json")
def resolve_root(key):
    with open(ROOT_REGISTRY) as f: reg = json.load(f)
    e = reg["roots"][key]
    p = e["path"]
    if e.get("resolve") == "home": return os.path.expanduser(p)
    return p

WORKSPACE = resolve_root("workspace")
USER_BIN = resolve_root("user_bin")
ROOT_REG = ROOT_REGISTRY
OUTPUT = os.path.join(WORKSPACE, "memory/data/system/baseline-observation.jsonl")
CST = timezone(timedelta(hours=8))

def ts_now(): return datetime.now(CST).isoformat()

def load_json(path):
    if os.path.isfile(path):
        with open(path) as f: return json.load(f)
    return None

def read_file(path):
    if os.path.isfile(path):
        with open(path) as f: return f.read()
    return ""

# ─── 基线来源 ───

def get_frozen_contracts():
    """Parse CONTRACT-REGISTRY.md for status=frozen entries."""
    content = read_file(os.path.join(WORKSPACE, "memory/state/huo/CONTRACT-REGISTRY.md"))
    frozen = []
    for line in content.split("\n"):
        if "|" not in line or not line.strip().startswith("| `"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 7:
            continue
        fname = cols[1].strip("`")
        status = cols[6].strip().lower()
        if status == "frozen":
            frozen.append(fname)
    return sorted(frozen)


def get_baseline_snapshots():
    """Read latest ASSET_SNAPSHOT and CAPABILITY_SNAPSHOT events."""
    asset_path = os.path.join(WORKSPACE, "memory/data/system/asset-observation.jsonl")
    cap_path = os.path.join(WORKSPACE, "memory/data/system/capability-observation.jsonl")

    asset = None
    cap = None

    if os.path.isfile(asset_path):
        with open(asset_path) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    if e.get("type") == "ASSET_SNAPSHOT":
                        asset = e
                except: pass

    if os.path.isfile(cap_path):
        with open(cap_path) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    if e.get("type") == "CAPABILITY_SNAPSHOT":
                        cap = e
                except: pass

    return asset, cap


def get_phase_status():
    """Frozen modules from PHASE_STATUS.json."""
    ps = load_json(os.path.join(WORKSPACE, "market_futures/PHASE_STATUS.json"))
    if ps:
        phase_keys = [k for k in ps if k.startswith("phase")]
        all_pass = all(ps.get(k) == "PASS" for k in phase_keys)
        baseline = ps.get("baseline_status") == "FROZEN"
        return {"module": "market_futures", "phases": len(phase_keys), "all_pass": all_pass, "baseline_frozen": baseline}
    return None


# ─── Drift 检查 ───

def check_contract_drift(frozen_contracts):
    """Check if frozen contracts still exist on disk."""
    dir_path = os.path.join(WORKSPACE, "memory/state/huo")
    drifts = []
    for fname in frozen_contracts:
        fp = os.path.join(dir_path, fname)
        if not os.path.isfile(fp):
            drifts.append({
                "type": "baseline_missing",
                "item": fname,
                "expected_location": f"memory/state/huo/{fname}",
                "detail": "冻结契约文件不存在",
            })
    return drifts


def check_snapshot_drift(asset, cap):
    """Compare latest snapshots — flag if classification dropped."""
    drifts = []
    if asset:
        cls = asset.get("classification", {})
        if cls:
            # If unknown > 60, that's a drift signal
            unknown_pct = cls.get("unknown", 0) / max(sum(cls.values()), 1) * 100
            if unknown_pct > 30:
                drifts.append({
                    "type": "classification_drift",
                    "source": "ASSET_SNAPSHOT",
                    "detail": f"unknown assets > 30% ({unknown_pct:.0f}%)",
                    "current": cls,
                })

    if cap:
        summary = cap.get("status_summary", {})
        available = summary.get("available", 0)
        total = summary.get("total", 1)
        if available < total:
            drifts.append({
                "type": "capability_drift",
                "source": "CAPABILITY_SNAPSHOT",
                "detail": f"capabilities degraded: {available}/{total} available",
                "current": summary,
            })
    return drifts


def check_module_drift(phase_status):
    """Check frozen module status."""
    drifts = []
    if phase_status:
        if not phase_status.get("baseline_frozen"):
            drifts.append({
                "type": "baseline_status_changed",
                "module": "market_futures",
                "expected": "FROZEN",
                "current": phase_status,
            })
    return drifts


# ─── Main ───

def main():
    print("[BASELINE-OBS] v1.0 — Baseline Observation Scan")
    print()

    frozen_contracts = get_frozen_contracts()
    asset_snap, cap_snap = get_baseline_snapshots()
    phase_status = get_phase_status()

    print(f"[INPUT] Frozen contracts:  {len(frozen_contracts)}")
    print(f"[INPUT] Asset snapshot:    {'ASSET-SNAPSHOT-002' if asset_snap else 'MISSING'}")
    print(f"[INPUT] Capability snap:   {'CAP-SNAPSHOT-001' if cap_snap else 'MISSING'}")
    print(f"[INPUT] Module status:     {'market_futures' if phase_status else 'MISSING'}")
    print()

    contract_drifts = check_contract_drift(frozen_contracts)
    snap_drifts = check_snapshot_drift(asset_snap, cap_snap)
    module_drifts = check_module_drift(phase_status)

    all_drifts = contract_drifts + snap_drifts + module_drifts

    print("[DRIFT CHECK]")
    if all_drifts:
        for d in all_drifts:
            print(f"  ⚠️  {d['type']}: {d['detail']}")
    else:
        print("  ✅ No drift detected")
    print()

    event = {
        "type": "BASELINE_OBSERVATION",
        "version": "1.0",
        "ts": ts_now(),
        "baseline_refs": {
            "frozen_contracts": len(frozen_contracts),
            "asset_snapshot": asset_snap.get("snapshot_id", "N/A") if asset_snap else None,
            "capability_snapshot": cap_snap.get("snapshot_id", "N/A") if cap_snap else None,
            "frozen_module": "market_futures" if phase_status else None,
        },
        "drift": all_drifts,
        "drift_count": len(all_drifts),
        "observation": {
            "contracts_checked": len(frozen_contracts),
            "contracts_missing": len(contract_drifts),
            "capabilities_available": cap_snap.get("status_summary", {}).get("available", 0) if cap_snap else 0,
            "capabilities_total": cap_snap.get("status_summary", {}).get("total", 0) if cap_snap else 0,
            "asset_classification": asset_snap.get("classification") if asset_snap else None,
        },
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    print(f"[DONE] baseline-observation.jsonl — {len(all_drifts)} drifts")
    summary = {
        "drift_count": len(all_drifts),
        "contracts_frozen": len(frozen_contracts),
        "drift_types": list(set(d["type"] for d in all_drifts)) if all_drifts else [],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
