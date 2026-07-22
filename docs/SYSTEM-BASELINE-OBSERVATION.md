# System Baseline Observation Layer v1.0

> 基线观察层。观察系统当前状态相对于冻结基线的变化。
> 不修改基线，不自动补齐，不审批变更，不创建建设任务。

---

## Purpose

```text
Baseline Observation
    ↓
系统当前状态 vs 冻结基线
    ↓
Drift Evidence
    ↓
Integrity Analyzer Input
```

## Scope

| 观察 | 不负责 |
|:-----|:-------|
| 冻结契约是否存在 | 修改基线 |
| 基线分类是否漂移 | 自动补齐 |
| 能力是否退化 | 审批变更 |
| 模块冻结是否被破坏 | 创建建设任务 |

## 输入源

| 源 | 提供 |
|:---|:------|
| CONTRACT-REGISTRY.md | 冻结契约列表 |
| ASSET-SNAPSHOT | 资产分类基线 |
| CAP-SNAPSHOT | 能力状态基线 |
| PHASE_STATUS.json | 模块冻结基线 |

## 输出事件

```json
{
  "type": "BASELINE_OBSERVATION",
  "baseline_refs": {
    "frozen_contracts": 3,
    "asset_snapshot": "ASSET-SNAPSHOT-002",
    "capability_snapshot": "CAP-SNAPSHOT-001",
    "frozen_module": "market_futures"
  },
  "drift": [],
  "drift_count": 0
}
```

## Baseline Snapshot: BASELINE-SNAPSHOT-001

| 基线源 | 值 |
|:-------|:----|
| Frozen contracts | 3 (CREDENTIAL-ACCESS, PHASE-7.1-AUDIT, TRADING-RUNTIME) |
| Asset baseline | ASSET-SNAPSHOT-002 |
| Capability baseline | CAP-SNAPSHOT-001 |
| Frozen module | market_futures (baseline_status: FROZEN) |
| Drift detected | 0 |

## Integrity Analyzer 输入

```text
Integrity Analyzer

├── Asset Observation        ✅
├── Contract Observation     ✅
├── Capability Observation   ✅
├── Runtime Observation      ⚠️ partial
└── Baseline Observation     ✅ NEW
```

## Related

- `scripts/baseline_observer.py` — 基线漂移观察器
- `config/asset-roots.json` — 统一资产根路径
- `memory/state/huo/CONTRACT-REGISTRY.md` — 契约注册表

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial. Baseline diff: contracts/asset/capability/module |
