# System Capability Observation Layer v1.0

> 能力观察层。观察系统能力声明、实现证据、覆盖完整度。
> 不参与建设、不参与决策、不自动补齐。

---

## Purpose

```text
Capability Definition
        ↓
Capability Observation  
        ↓
Integrity Analyzer Input
```

## Scope

| 观察 | 不负责 |
|:-----|:-------|
| 系统声明了哪些能力 | 自动补齐能力 |
| 能力由哪些资产提供 | 自动创建模块 |
| 证据是否存在 | 自动规划路线 |
| 覆盖是否完整 | 自动修改 Contract |
| 状态变化 | |

## 能力状态

| 状态 | 含义 |
|:-----|:------|
| available | 所有证据路径均存在 |
| partial | 部分证据路径存在 |
| declared_only | 有声明，无实现证据 |
| missing | 基线要求有，但无实现 |
| unknown | 无法判断 |

## Capability Snapshot: CAP-SNAPSHOT-001

> **Scan Time:** 2026-07-22 11:25 CST
> **Observer:** scripts/capability_observer.py v1.0
> **Scope:** FIRST_SCAN

### Summary

| Status | Count |
|:-------|:-----:|
| available | 24 |
| partial | 0 |
| declared_only | 0 |
| missing | 0 |
| unknown | 0 |
| **Total** | **24** |

### By Domain

| Domain | Capabilities |
|:-------|:-------------|
| Trading | 期货模拟交易, 期货行情采集, 量化策略回测, 历史行情重放 |
| Lottery | 彩票开奖数据采集, 彩票预测与核对, 彩票日报生成, 通知推送 |
| Runtime | Gateway 服务, 运行时上下文注入, 自愈观察, 自愈边界管控 |
| Monitoring | 系统健康传感器, Token 用量观测, TG 行为诊断, 资产观察扫描, 契约校验 |
| Infrastructure | 全量备份, Billing 计费快照, 本地模型推理 |
| Governance | 契约治理仲裁, 冻结基线管控, 治理链审计, 身份与权限隔离 |

### Detail

| ID | Capability | Status | Evidence |
|:---|:-----------|:------:|:---------|
| CAP-TRADING-001 | 期货模拟交易 | ✅ available | simulator, position, account |
| CAP-TRADING-002 | 期货行情采集 | ✅ available | collector, collector_live |
| CAP-TRADING-003 | 量化策略回测 | ✅ available | ma, breakout, rsi, run_strategy |
| CAP-TRADING-004 | 历史行情重放 | ✅ available | replay/loader, converter, historical/ |
| CAP-LOTTERY-001 | 彩票开奖数据采集 | ✅ available | worker.sh, ssq.jsonl, dlt.jsonl |
| CAP-LOTTERY-002 | 彩票预测与核对 | ✅ available | predictions/ |
| CAP-LOTTERY-003 | 彩票日报生成 | ✅ available | daily-report |
| CAP-LOTTERY-004 | 通知推送 | ✅ available | push-notify.mjs |
| CAP-RUNTIME-001 | Gateway 服务 | ✅ available | openclaw-gateway.service |
| CAP-RUNTIME-002 | 运行时上下文注入 | ✅ available | context_provider, temporal_resolver |
| CAP-RUNTIME-003 | 自愈观察 | ✅ available | observer, provider_observe |
| CAP-RUNTIME-004 | 自愈边界管控 | ✅ available | boundary_gate, config_audit |
| CAP-MONITOR-001 | 系统健康传感器 | ✅ available | collect-sensors, system-health.jsonl |
| CAP-MONITOR-002 | Token 用量观测 | ✅ available | token-metrics.sh, token-metrics.jsonl |
| CAP-MONITOR-003 | TG 行为诊断 | ✅ available | behavior_analyzer, transcript_reader |
| CAP-MONITOR-004 | 资产观察扫描 | ✅ available | asset_observer.py |
| CAP-MONITOR-005 | 契约校验 | ✅ available | contract_validator.py |
| CAP-INFRA-001 | 全量备份 | ✅ available | backup-full, audit-backup |
| CAP-INFRA-002 | Billing 计费快照 | ✅ available | billing-snapshotter |
| CAP-INFRA-003 | 本地模型推理 | ✅ available | local-task-worker, ollama-production |
| CAP-GOV-001 | 契约治理仲裁 | ✅ available | META-CONTRACT, CONTRACT-REGISTRY |
| CAP-GOV-002 | 冻结基线管控 | ✅ available | FREEZE-CONTRACT, BASELINE-CHECK |
| CAP-GOV-003 | 治理链审计 | ✅ available | EVIDENCE/DECISION/CHANGE |
| CAP-GOV-004 | 身份与权限隔离 | ✅ available | IDENTITY-CONTRACT, IDENTITY-RULES |

## Observation Events

```text
memory/data/system/
└── capability-observation.jsonl
```

Event format:

```json
{
  "type": "CAPABILITY_SNAPSHOT",
  "snapshot_id": "CAP-SNAPSHOT-001",
  "capabilities": [...],
  "status_summary": {
    "total": 24,
    "available": 24,
    "partial": 0,
    "declared_only": 0,
    "missing": 0,
    "unknown": 0
  }
}
```

## Integrity Analyzer Input

```text
Integrity Analyzer

├── Asset Observation     ✅ SYSTEM-ASSET-OBSERVATION
├── Contract Observation  ✅ CONTRACT-REGISTRY
├── Runtime Observation   ✅ Phase 8
└── Capability Observation ✅ SYSTEM-CAPABILITY-OBSERVATION (NEW)
```

## Related

- `scripts/capability_observer.py` — 观察扫描脚本
- `memory/data/system/capability-observation.jsonl` — 事件流
- `docs/SYSTEM-ASSET-OBSERVATION.md` — 资产观察层
- `memory/state/huo/CAPABILITY-REGISTRY.md` — 能力注册表
- `memory/state/huo/capability_audit_report.md` — 能力审计报告

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial. 24 capabilities, 6 domains, CAP-SNAPSHOT-001 |
