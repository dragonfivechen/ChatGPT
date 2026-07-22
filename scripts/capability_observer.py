#!/usr/bin/env python3
"""
Capability Observation Layer v1.0 — Capability Observer

读取能力声明来源 + 资产观察证据 → 生成能力快照。
不参与建设，不参与决策，不自动补齐。

Output: memory/data/system/capability-observation.jsonl
"""

import json, os
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
OUTPUT = os.path.join(WORKSPACE, "memory/data/system/capability-observation.jsonl")
CST = timezone(timedelta(hours=8))

def ts_now():
    return datetime.now(CST).isoformat()

# ─── 能力定义（可扩展） ───
# 来源: CAPABILITY-REGISTRY / 领域 Contract / Semantic Index modules
CAPABILITY_DEFS = [
    {
        "id": "CAP-TRADING-001",
        "name": "期货模拟交易",
        "domain": "Trading",
        "module": "TRD-MODULE-001",
        "evidence_paths": [
            "market_futures/simulator.py",
            "market_futures/position.py",
            "market_futures/account.py",
        ],
    },
    {
        "id": "CAP-TRADING-002",
        "name": "期货行情采集",
        "domain": "Trading",
        "module": "TRD-MODULE-001",
        "evidence_paths": [
            "market_futures/collector.py",
            "market_futures/collector_live.py",
        ],
    },
    {
        "id": "CAP-TRADING-003",
        "name": "量化策略回测",
        "domain": "Trading",
        "module": "TRD-MODULE-001",
        "evidence_paths": [
            "market_futures/strategies/ma.py",
            "market_futures/strategies/breakout.py",
            "market_futures/strategies/rsi.py",
            "market_futures/run_strategy.py",
        ],
    },
    {
        "id": "CAP-TRADING-004",
        "name": "历史行情重放",
        "domain": "Trading",
        "module": "TRD-MODULE-001",
        "evidence_paths": [
            "market_futures/replay/loader.py",
            "market_futures/replay/converter.py",
            "market_futures/data/historical/",
        ],
    },
    {
        "id": "CAP-LOTTERY-001",
        "name": "彩票开奖数据采集",
        "domain": "Lottery",
        "module": "LOT-MODULE-001",
        "evidence_paths": [
            ".local/bin/lottery-worker.sh",
            "memory/events/lottery/ssq.jsonl",
            "memory/events/lottery/dlt.jsonl",
        ],
    },
    {
        "id": "CAP-LOTTERY-002",
        "name": "彩票预测与核对",
        "domain": "Lottery",
        "module": "LOT-MODULE-001",
        "evidence_paths": [
            "memory/cache/lottery/predictions/",
        ],
    },
    {
        "id": "CAP-LOTTERY-003",
        "name": "彩票日报生成",
        "domain": "Lottery",
        "module": "LOT-MODULE-001",
        "evidence_paths": [
            "memory/data/system/daily-report/latest.md",
        ],
    },
    {
        "id": "CAP-LOTTERY-004",
        "name": "通知推送",
        "domain": "Lottery",
        "module": "LOT-MODULE-001",
        "evidence_paths": [
            "hooks/oek-ci-gate/push-notify.mjs",
        ],
    },
    {
        "id": "CAP-RUNTIME-001",
        "name": "Gateway 服务",
        "domain": "Runtime",
        "module": "RUN-MODULE-001",
        "evidence_paths": [
            "~/.config/systemd/user/openclaw-gateway.service",
        ],
    },
    {
        "id": "CAP-RUNTIME-002",
        "name": "运行时上下文注入",
        "domain": "Runtime",
        "module": "RUN-MODULE-003",
        "evidence_paths": [
            "runtime/context_provider.py",
            "runtime/temporal_resolver.py",
        ],
    },
    {
        "id": "CAP-RUNTIME-003",
        "name": "自愈观察",
        "domain": "Runtime",
        "module": "RUN-MODULE-002",
        "evidence_paths": [
            "self-healing/observer.py",
            "self-healing/provider_observe.py",
        ],
    },
    {
        "id": "CAP-RUNTIME-004",
        "name": "自愈边界管控",
        "domain": "Runtime",
        "module": "RUN-MODULE-002",
        "evidence_paths": [
            "self-healing/boundary_gate.py",
            "self-healing/config_audit.py",
        ],
    },
    {
        "id": "CAP-MONITOR-001",
        "name": "系统健康传感器",
        "domain": "Monitoring",
        "module": "MON-MODULE-002",
        "evidence_paths": [
            "scripts/collect-sensors.sh",
            "memory/data/system/system-health.jsonl",
        ],
    },
    {
        "id": "CAP-MONITOR-002",
        "name": "Token 用量观测",
        "domain": "Monitoring",
        "module": "MON-MODULE-003",
        "evidence_paths": [
            "scripts/collect-token-metrics.sh",
            "memory/data/system/token-metrics.jsonl",
        ],
    },
    {
        "id": "CAP-MONITOR-003",
        "name": "TG 行为诊断",
        "domain": "Monitoring",
        "module": "MON-MODULE-004",
        "evidence_paths": [
            "tools/tg_behavior_analyzer.py",
            "tools/tg_transcript_reader.py",
        ],
    },
    {
        "id": "CAP-MONITOR-004",
        "name": "资产观察扫描",
        "domain": "Monitoring",
        "module": "MON-MODULE-001",
        "evidence_paths": [
            "scripts/asset_observer.py",
        ],
    },
    {
        "id": "CAP-MONITOR-005",
        "name": "契约校验",
        "domain": "Monitoring",
        "module": "MON-MODULE-005",
        "evidence_paths": [
            "tools/contract_validator.py",
        ],
    },
    {
        "id": "CAP-INFRA-001",
        "name": "全量备份",
        "domain": "Infrastructure",
        "module": "INF-MODULE-001",
        "evidence_paths": [
            "scripts/backup-full.sh",
            "scripts/audit-backup.sh",
        ],
    },
    {
        "id": "CAP-INFRA-002",
        "name": "Billing 计费快照",
        "domain": "Infrastructure",
        "module": "INF-MODULE-002",
        "evidence_paths": [
            "hooks/oek-ci-gate/billing-snapshotter.mjs",
        ],
    },
    {
        "id": "CAP-INFRA-003",
        "name": "本地模型推理",
        "domain": "Infrastructure",
        "module": "INF-MODULE-003",
        "evidence_paths": [
            "scripts/local-task-worker.sh",
            "memory/events/huo/ollama-production.jsonl",
        ],
    },
    {
        "id": "CAP-GOV-001",
        "name": "契约治理仲裁",
        "domain": "Governance",
        "module": "GOV-MODULE-001",
        "evidence_paths": [
            "memory/state/huo/META-CONTRACT.md",
            "memory/state/huo/CONTRACT-REGISTRY.md",
        ],
    },
    {
        "id": "CAP-GOV-002",
        "name": "冻结基线管控",
        "domain": "Governance",
        "module": "GOV-MODULE-002",
        "evidence_paths": [
            "memory/state/huo/FREEZE-CONTRACT.md",
            "memory/state/huo/FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md",
        ],
    },
    {
        "id": "CAP-GOV-003",
        "name": "治理链审计（证据-决策-变更）",
        "domain": "Governance",
        "module": "GOV-MODULE-003",
        "evidence_paths": [
            "memory/state/huo/EVIDENCE-CONTRACT.md",
            "memory/state/huo/DECISION-CONTRACT.md",
            "memory/state/huo/CHANGE-CONTRACT.md",
        ],
    },
    {
        "id": "CAP-GOV-004",
        "name": "身份与权限隔离",
        "domain": "Governance",
        "module": "GOV-MODULE-004",
        "evidence_paths": [
            "IDENTITY-CONTRACT.md",
            "IDENTITY-RULES.md",
        ],
    },
]

# ─── 能力状态判定 ───

def check_evidence(path):
    """Check if evidence path exists on filesystem."""
    if path.startswith("~/"):
        full_path = os.path.expanduser(path)
    elif path.startswith(".local/") or path.startswith(".local/bin/"):
        full_path = os.path.join(USER_BIN, os.path.basename(path))
    elif path.startswith("/"):
        full_path = path
    else:
        full_path = os.path.join(WORKSPACE, path)
    return os.path.exists(full_path)


def classify_capability(cap):
    """Determine capability status from evidence."""
    ev_paths = cap.get("evidence_paths", [])
    if not ev_paths:
        return "unknown"

    results = [check_evidence(p) for p in ev_paths]
    found = sum(results)
    total = len(results)

    if found == total:
        return "available"
    elif found > 0:
        return "partial"
    else:
        return "declared_only"


def scan():
    """Main scan: evaluate all capabilities."""
    print(f"[CAP-OBSERVER] v1.0 — Capability Observation Scan")
    print(f"[CAP-OBSERVER] {len(CAPABILITY_DEFS)} capabilities defined")
    print()

    results = []
    status_counts = {}

    for cap in CAPABILITY_DEFS:
        status = classify_capability(cap)
        ev_paths = cap.get("evidence_paths", [])
        ev_check = {p: check_evidence(p) for p in ev_paths}

        entry = {
            "id": cap["id"],
            "name": cap["name"],
            "domain": cap["domain"],
            "module": cap["module"],
            "status": status,
            "evidence": ev_check,
        }
        results.append(entry)
        status_counts[status] = status_counts.get(status, 0) + 1

    # Print summary
    print("[CAPABILITY STATUS]")
    for s in ("available", "partial", "declared_only", "missing", "unknown"):
        c = status_counts.get(s, 0)
        if c > 0:
            print(f"  {s:15s}: {c}")

    print()
    print("[DETAILS]")
    for r in results:
        found = sum(1 for v in r["evidence"].values() if v)
        total = len(r["evidence"])
        marker = "✅" if r["status"] == "available" else "⚠️" if r["status"] == "partial" else "📄"
        print(f"  {marker} {r['id']}: {r['name']} ({found}/{total})")

    # Build event
    event = {
        "type": "CAPABILITY_SNAPSHOT",
        "version": "1.0",
        "scope": "FIRST_SCAN",
        "snapshot_id": "CAP-SNAPSHOT-001",
        "ts": ts_now(),
        "capabilities": results,
        "status_summary": {
            "total": len(results),
            "available": status_counts.get("available", 0),
            "partial": status_counts.get("partial", 0),
            "declared_only": status_counts.get("declared_only", 0),
            "missing": status_counts.get("missing", 0),
            "unknown": status_counts.get("unknown", 0),
        },
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    print()
    print(f"[DONE] CAP-SNAPSHOT-001 → {OUTPUT}")
    return event


if __name__ == "__main__":
    scan()
