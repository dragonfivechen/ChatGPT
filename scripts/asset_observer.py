#!/usr/bin/env python3
"""
System Asset Observation Layer v1.2 — Full Scan + Asset Classification v1.1

分类优先级: deprecated → idle → duplicate → incomplete → frozen → active → unknown
unknown ≠ active
"""

import json, os, subprocess, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

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
SYSTEMD_DIR = resolve_root("systemd")
OPENCLAW_CONFIG = resolve_root("openclaw_config")
OUTPUT = os.path.join(WORKSPACE, "memory/data/system/asset-observation.jsonl")
CST = timezone(timedelta(hours=8))

def ts_now(): return datetime.now(CST).isoformat()
def fmt_path(p):
    if p.startswith(WORKSPACE + "/"): return p[len(WORKSPACE)+1:]
    return p

# ─── deprecated 匹配模式 ───
DEPRECATED_PATTERNS = [
    "archive", "backup", "legacy", ".old", "deprecated",
    "shadow", "proof", "snapshot", "resolve", "audit",
]
DEPRECATED_EXT = [".bak"]
DEPRECATED_PREFIX = ["v1.0-pre", "pre-"]

def matches_deprecated(name, path):
    name_lower = name.lower()
    path_lower = path.lower()
    for p in DEPRECATED_PATTERNS:
        if p in path_lower:
            return True
    for ext in DEPRECATED_EXT:
        if name_lower.endswith(ext):
            return True
    for pref in DEPRECATED_PREFIX:
        if name_lower.startswith(pref) or pref in name_lower:
            return True
    return False

def is_incomplete(name):
    n = name.lower()
    return any(kw in n for kw in ["proposal", "draft", "todo", "test-contract", "candidate", "feasibility"])

def is_duplicate_stem(name, known_set):
    stem = os.path.splitext(name)[0]
    return stem in known_set

# ─── 从 Contract Registry 读取冻结状态 ───
def load_contract_registry_status():
    """Parse CONTRACT-REGISTRY.md table to get contract → status mapping."""
    registry_path = os.path.join(WORKSPACE, "memory/state/huo/CONTRACT-REGISTRY.md")
    mapping = {}
    if not os.path.isfile(registry_path):
        return mapping
    with open(registry_path, "r") as f:
        content = f.read()
    # Find the table rows: | `filename.md` | ... | ... | ... | ... | status |
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| `") or not line.endswith("|"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 7:
            continue
        # col 1 = filename (backtick-wrapped)
        fname = cols[1].strip("`").strip()
        # col 6 = status column
        status = cols[6].strip().lower()
        if status in ("frozen", "active", "proposal", "archived"):
            mapping[fname] = status
    return mapping

CONTRACT_REGISTRY_STATUS = load_contract_registry_status()

# ─── Scanners ───

def scan_docs():
    entries = []
    for base in [os.path.join(WORKSPACE, "docs"), os.path.join(WORKSPACE, "archive/docs")]:
        if not os.path.isdir(base): continue
        for f in sorted(os.listdir(base)):
            fp = os.path.join(base, f)
            if f.endswith(".md") and os.path.isfile(fp):
                entries.append({"name": f, "path": fmt_path(fp)})
    return entries

def scan_contracts():
    path = os.path.join(WORKSPACE, "memory/state/huo")
    entries = []
    if not os.path.isdir(path): return entries
    for f in sorted(os.listdir(path)):
        fp = os.path.join(path, f)
        if not f.endswith(".md") or not os.path.isfile(fp): continue
        if "CONTRACT" in f.upper(): subtype = "contract"
        elif f.startswith("PHASE-"): subtype = "phase"
        else: subtype = "doc"
        entries.append({"name": f, "path": fmt_path(fp), "type": subtype})
    return entries

def scan_modules():
    entries = []
    for d in ["market_futures", "self-healing", "runtime"]:
        fp = os.path.join(WORKSPACE, d)
        if os.path.isdir(fp):
            entries.append({"name": d, "path": fmt_path(fp)})
    return entries

def scan_scripts():
    entries = []
    for label in ["scripts", "tools", "local_bin"]:
        if label == "local_bin":
            base = os.path.expanduser("~/.local/bin")
        else:
            base = os.path.join(WORKSPACE, label)
        if not os.path.isdir(base): continue
        for f in sorted(os.listdir(base)):
            fp = os.path.join(base, f)
            if not os.path.isfile(fp): continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".sh", ".py", ".mjs"): continue
            if "__pycache__" in fp: continue
            entries.append({"name": f, "path": fmt_path(fp), "origin": label, "ext": ext.lstrip(".")})
    return entries

def scan_services():
    sd = SYSTEMD_DIR
    entries = []
    if not os.path.isdir(sd): return entries, []
    for f in sorted(os.listdir(sd)):
        fp = os.path.join(sd, f)
        if not os.path.isfile(fp): continue
        if f.endswith(".timer"): entries.append({"name": f, "path": fp, "type": "timer"})
        elif f.endswith(".service"): entries.append({"name": f, "path": fp, "type": "service"})
    active = []
    try:
        r = subprocess.run(["systemctl","--user","list-timers"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split("\n"):
            if ".timer" in line:
                for p in line.strip().split():
                    if p.endswith(".timer"): active.append(p); break
    except: pass
    return entries, active

def scan_data_sources():
    entries = []
    for label, base in [
        ("memory_data", os.path.join(WORKSPACE, "memory/data")),
        ("memory_events", os.path.join(WORKSPACE, "memory/events")),
    ]:
        if not os.path.isdir(base): continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for f in sorted(files):
                if f.startswith(".") or f.endswith(".pyc"): continue
                fp = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower()
                if ext not in (".jsonl",".json",".csv",".md",".log"): continue
                entries.append({"name": f, "path": fmt_path(fp), "category": label, "ext": ext.lstrip("."), "mtime": os.path.getmtime(fp)})
    return entries

def scan_configs():
    entries = []
    for f in sorted(os.listdir(WORKSPACE)):
        fp = os.path.join(WORKSPACE, f)
        if not os.path.isfile(fp): continue
        if f.endswith((".yaml",".yml",".toml")): entries.append({"name": f, "path": fmt_path(fp)})
    for fp in [os.path.join(OPENCLAW_CONFIG, "openclaw.json"), os.path.join(OPENCLAW_CONFIG, "secrets.json")]:
        if os.path.isfile(fp): entries.append({"name": os.path.basename(fp), "path": fp})
    return entries

def scan_tests():
    entries = []
    td = os.path.join(WORKSPACE, "market_futures/tests")
    if os.path.isdir(td):
        for f in sorted(os.listdir(td)):
            fp = os.path.join(td, f)
            if os.path.isfile(fp) and f.endswith(".py"): entries.append({"name": f, "path": fmt_path(fp)})
    return entries

# ─── Classification Engine ───

def classify_all(docs, contracts, modules, scripts, services, data_sources, configs, tests):
    """Apply priority-based classification to all assets."""
    result = {c: 0 for c in ("active","frozen","duplicate","idle","deprecated","incomplete","unknown")}
    details = defaultdict(list)

    # Collect known active runtime timers for idle detection
    _, active_timers = scan_services()
    active_timer_set = set(active_timers)

    # Gather all script names for duplicate stem detection
    all_script_names = [s["name"] for s in scripts]
    script_stems = set()
    for n in all_script_names:
        stem = os.path.splitext(n)[0]
        if stem: script_stems.add(stem)

    def classify_one(asset, category):
        """Assign single classification per asset. First match wins."""
        name = asset["name"]
        path = asset.get("path", "")

        # 1. deprecated
        if matches_deprecated(name, path):
            result["deprecated"] += 1
            details["deprecated"].append(f"[{category}] {name}")
            return

        # 2. idle: exists, but no runtime entry, stale mtime, has replacement
        if category == "scripts":
            # Check if this script is referenced by any timer
            origin = asset.get("origin", "")
            # .local/bin scripts not in timer path → idle
            if origin == "local_bin":
                # Check: is this script referenced by any timer ExecStart?
                result["idle"] += 1
                details["idle"].append(f"[scripts] {name}")
                return
            # tools/ scripts → active (governance workers run via cron)
            if origin == "tools":
                result["active"] += 1
                details["active"].append(f"[scripts] {name}")
                return
            # scripts/ with .bak → deprecated (already caught above)
            result["active"] += 1
            details["active"].append(f"[scripts] {name}")
            return

        if category == "docs":
            # test-contract → incomplete
            if is_incomplete(name):
                result["incomplete"] += 1
                details["incomplete"].append(f"[docs] {name}")
                return
            # All other docs → active (they're referenced by handbook/index)
            result["active"] += 1
            details["active"].append(f"[docs] {name}")
            return

        if category == "contracts":
            # Check CONTRACT-REGISTRY for authoritative status
            registry_status = CONTRACT_REGISTRY_STATUS.get(name)
            if registry_status == "frozen":
                result["frozen"] += 1
                details["frozen"].append(f"[contracts] {name}")
            elif registry_status == "proposal":
                result["incomplete"] += 1
                details["incomplete"].append(f"[contracts] {name}")
            elif name.startswith("PHASE-") or name.startswith("phase-"):
                # Phase docs: check for COMPLETE/FROZEN in content
                fp = os.path.join(WORKSPACE, asset.get("path",""))
                try:
                    with open(fp) as fh: content = fh.read()
                    if "FROZEN" in content or "COMPLETE" in content:
                        result["frozen"] += 1
                        details["frozen"].append(f"[phase] {name}")
                    else:
                        result["active"] += 1
                        details["active"].append(f"[phase] {name}")
                except:
                    result["unknown"] += 1
                    details["unknown"].append(f"[phase] {name}")
            else:
                # Not in registry, unknown status
                result["unknown"] += 1
                details["unknown"].append(f"[contracts] {name}")
            return

        if category == "services":
            asset_type = asset.get("type", "")
            if asset_type == "timer":
                result["active"] += 1
                details["active"].append(f"[services] {name}")
            elif asset_type == "service":
                base_name = name.replace(".service", "")
                if base_name in ("openclaw-gateway", "oc-watchdog-stream"):
                    result["active"] += 1
                    details["active"].append(f"[services] {name}")
                else:
                    timer_match = base_name + ".timer"
                    if any(s["name"] == timer_match for s in services):
                        result["active"] += 1
                        details["active"].append(f"[services] {name}")
                    else:
                        result["idle"] += 1
                        details["idle"].append(f"[services] {name}")
            return

        if category == "modules":
            if name == "market_futures":
                result["frozen"] += 1
                details["frozen"].append(f"[modules] {name}")
            else:
                result["active"] += 1
                details["active"].append(f"[modules] {name}")
            return

        if category == "data":
            now = datetime.now().timestamp()
            age_days = (now - asset["mtime"]) / 86400
            cat = asset.get("category", "")
            # memory_events → active (append-only)
            if cat == "memory_events":
                result["active"] += 1
                details["active"].append(f"[data] {name}")
            elif age_days < 7:
                result["active"] += 1
                details["active"].append(f"[data] {name}")
            else:
                result["idle"] += 1
                details["idle"].append(f"[data] {name}")
            return

        if category == "configs":
            result["active"] += 1
            details["active"].append(f"[configs] {name}")
            return

        if category == "tests":
            result["incomplete"] += 1
            details["incomplete"].append(f"[tests] {name}")
            return

        # Catch-all
        result["unknown"] += 1
        details["unknown"].append(f"[{category}] {name}")

    for d in docs: classify_one(d, "docs")
    for c in contracts: classify_one(c, "contracts")
    for m in modules: classify_one(m, "modules")
    for s in scripts: classify_one(s, "scripts")
    for s in services: classify_one(s, "services")
    for d in data_sources: classify_one(d, "data")
    for c in configs: classify_one(c, "configs")
    for t in tests: classify_one(t, "tests")

    return result, details

# ─── Duplicate Detection ───

def detect_duplicates():
    dups = []
    # Root-level standalone files vs module directories
    # futures_sim.py (root) vs market_futures/ (module dir)
    root_futures = os.path.join(WORKSPACE, "futures_sim.py")
    if os.path.isfile(root_futures):
        dups.append({
            "function": "futures_sim",
            "candidates": ["futures_sim.py", "market_futures/"],
            "note": "standalone root file vs module directory (idle candidate)",
        })
    # Check same-name scripts across dirs
    by_stem = defaultdict(list)
    for base, label in [
        (os.path.join(WORKSPACE, "tools"), "tools"),
        (os.path.join(WORKSPACE, "scripts"), "scripts"),
        (USER_BIN, "local_bin"),
    ]:
        if not os.path.isdir(base): continue
        for f in os.listdir(base):
            fp = os.path.join(base, f)
            if os.path.isfile(fp) and f.endswith((".sh",".py",".mjs")):
                stem = os.path.splitext(f)[0]
                by_stem[stem].append(f"{label}/{f}")
    for stem, paths in by_stem.items():
        if len(paths) > 1:
            dirs = set(p.split("/")[0] for p in paths)
            if len(dirs) > 1:
                dups.append({
                    "function": stem,
                    "candidates": paths,
                    "note": f"same stem across {len(dirs)} directories",
                })
    return dups

# ─── Consistency ───

def check_consistency(docs):
    issues = []
    found = {d["name"] for d in docs}
    if "MODULE-CONSTRUCTION-HANDBOOK.md" not in found:
        issues.append({"type":"missing","detail":"MODULE-CONSTRUCTION-HANDBOOK.md"})
    if "MODULE-INDEX.md" not in found:
        issues.append({"type":"missing","detail":"MODULE-INDEX.md"})
    if "SYSTEM-ASSET-OBSERVATION.md" not in found:
        issues.append({"type":"missing","detail":"SYSTEM-ASSET-OBSERVATION.md"})
    return {
        "path_check": "PASS" if not issues else "FAIL",
        "issues": issues,
    }

# ─── Main ───

def main(mode="full"):
    SNAPSHOT_ID = "ASSET-SNAPSHOT-002"
    print(f"[OBSERVER] v1.3 — Mode: {mode}")
    print(f"[OBSERVER] Classification: deprecated→idle→duplicate→incomplete→frozen→active→unknown")
    print()

    # Light: only check paths and service changes
    if mode == "light":
        docs = scan_docs()
        services, active_timers = scan_services()
        print("[LIGHT] path_check:", "PASS" if check_consistency(docs)["path_check"] == "PASS" else "FAIL")
        print(f"[LIGHT] docs: {len(docs)}, timers: {len(active_timers)}, services: {len([s for s in services if s['type']=='service'])}")
        return

    # Full scan always runs for medium and full
    docs = scan_docs()
    contracts = scan_contracts()
    modules = scan_modules()
    scripts = scan_scripts()
    services, active_timers = scan_services()
    data_sources = scan_data_sources()
    configs = scan_configs()
    tests = scan_tests()

    contract_count = len([c for c in contracts if c["type"] == "contract"])
    phase_count = len([c for c in contracts if c["type"] == "phase"])
    timer_count = len([s for s in services if s["type"] == "timer"])
    service_count = len([s for s in services if s["type"] == "service"])

    print("[SCAN]")
    print(f"  docs:            {len(docs)}")
    print(f"  contracts:       {contract_count}")
    print(f"  phase docs:      {phase_count}")
    print(f"  state docs:      {len(contracts)-contract_count-phase_count}")
    print(f"  modules:         {len(modules)}")
    print(f"  scripts:         {len(scripts)}")
    print(f"  services/timers: {service_count}s / {timer_count}t")
    print(f"  data sources:    {len(data_sources)}")
    print(f"  configs:         {len(configs)}")
    print(f"  tests:           {len(tests)}")
    print()

    classification, details = classify_all(docs, contracts, modules, scripts, services, data_sources, configs, tests)
    duplicates = detect_duplicates()
    classification["duplicate"] += len(duplicates)

    print("[CLASSIFICATION]")
    for k in ("active","frozen","duplicate","idle","deprecated","incomplete","unknown"):
      print(f"  {k:12s}: {classification[k]}")
    print()

    if duplicates:
        print("[DUPLICATE CANDIDATES]")
        for d in duplicates:
            print(f"  {d['function']}: {d['note']}")
            for p in d["candidates"]:
                print(f"    - {p}")
        print()

    consistency = check_consistency(docs)
    print(f"[CONSISTENCY] path_check: {consistency['path_check']}")
    for iss in consistency["issues"]:
        print(f"  [ISSUE] {iss['detail']}")
    print()

    event = {
        "type": "ASSET_SNAPSHOT",
        "version": "1.2",
        "scope": "FULL_SYSTEM",
        "snapshot_id": SNAPSHOT_ID,
        "ts": ts_now(),
        "classification_rule": "v1.1 (deprecated→idle→duplicate→incomplete→frozen→active→unknown)",
        "assets": {
            "docs": len(docs),
            "contracts": contract_count,
            "phase_docs": phase_count,
            "state_docs": len(contracts)-contract_count-phase_count,
            "modules": len(modules),
            "scripts": len(scripts),
            "services": service_count,
            "timers": timer_count,
            "active_timers": len(active_timers),
            "data_sources": len(data_sources),
            "configs": len(configs),
            "tests": len(tests),
        },
        "classification": classification,
        "duplicates": duplicates,
        "consistency": {
            "path_check": consistency["path_check"],
            "issues": consistency["issues"],
        },
        "labels": {
            "has_classification_v1.1": True,
            "is_baseline": True,
        },
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    print(f"[DONE] {SNAPSHOT_ID} → {OUTPUT}")
    summary = {
        "snapshot_id": SNAPSHOT_ID,
        "total_assets": sum(event["assets"].values()),
        "classification": classification,
    }
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    import sys
    mode = "full"
    for arg in sys.argv[1:]:
        for prefix in ("--mode=", "--depth=", "--mode", "--depth"):
            if arg.startswith(prefix):
                val = arg.replace(prefix, "").strip()
                if val in ("light", "medium", "full"):
                    mode = val
    main(mode)
