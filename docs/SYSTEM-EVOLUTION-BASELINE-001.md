# System Evolution Baseline v001

> **确认日期:** 2026-07-22 12:05 CST
> **来源:** EVOLUTION-SNAPSHOT-001（首次系统演化快照）
> **状态:** 🔒 FROZEN — 后续所有演化判断以此锚点为准
> **定位:** 不是一个治理层级，是一个确认过的锚点。只回答"是否偏离"，不回答"是否要改"。

---

## 1. 系统规模基线

| 指标 | 值 | 说明 |
|:-----|:---|:------|
| assets_total | 265 | 包含 docs/contracts/modules/scripts/services/timers/data/configs/tests |
| capabilities | 24 | 6 个域 |
| domains | 6 | Trading / Lottery / Runtime / Monitoring / Infrastructure / Governance |
| contracts | 41 | memory/state/huo/ 下 *CONTRACT*.md |
| modules (L1) | 21 | Semantic Index 登记的模块级实体 |
| observers | 6 | asset / capability / baseline / system-evolution / self-healing / provider |
| systemd timers | 22 | 含 gateway/watchdog 等连续服务 |
| systemd services | 23 | |

## 2. 能力覆盖基线

| Domain | Coverage | Available/Total |
|:-------|:--------:|:---------------:|
| Governance | ✅ 100% | 4/4 |
| Runtime | ✅ 100% | 4/4 |
| Observation (Monitoring) | ✅ 100% | 5/5 |
| Trading | ✅ 100% | 4/4 |
| Lottery | ✅ 100% | 4/4 |
| Infrastructure | ✅ 100% | 3/3 |

## 3. 架构边界基线

### 包含

```
✅ Asset Observation
✅ Capability Observation
✅ Baseline Observation
✅ System Evolution Observation
✅ Semantic Index (L0/L1)
✅ Module File Mapping (L2)
✅ Integrity Analyzer (6 输入源)
✅ Asset Root Registry
```

### 不包含

```
❌ 自动治理
❌ 自动修复
❌ 自动扩展
❌ 生命周期管理（建设/归档/删除）
❌ 变更审批
❌ 权限控制
```

> 未来若新增能力超出以上"包含"范围，须标记为架构边界漂移。

## 4. 建设状态基线

| 状态 | 含义 | 当前资产 |
|:-----|:------|:---------|
| active | 当前运行能力 | Asset Observer, Capability Observer, Baseline Observer, Evolution Observer, Self-Healing, Provider Observe |
| frozen | 不应随意变化 | CONTRACT-REGISTRY frozen=3, market_futures(baseline_status=FROZEN), Phase 7.5 integrity baseline |
| incomplete | 已知未完成 | Runtime Observation (Phase 8 Stage 1-3 未实现), 部分 contract design doc 未接 Registry |
| unknown | 待确认 | 58 state/huo 资产未在 CONTRACT-REGISTRY 登记 |
| deprecated | 废弃待归档 | 21 项 (archive docs, .bak, pre-version, shadow/audit/snapshot legacy) |
| idle | 无活动证据 | 22 项 (.local/bin 遗留脚本 + 旧数据缓存 + 孤立服务) |

## 5. 演化规则基线

### 正常演化（只记录，不标记）

```
+ 文档更新
+ 观察数据增长（jsonl 事件数增加）
+ 新模块建设记录
+ 新能力补齐
+ 新 observer 加入
+ 现有 observer 深度扩展
```

### 需要标记为 Drift

```
⚠️ 大量重复资产（duplicate 增长）
⚠️ 绕过契约或冻结状态
⚠️ 冻结内容变化（frozen→active）
⚠️ 观察层变为治理层
⚠️ 自动修复/自动补齐引入
⚠️ 路径回归硬编码（新 observer 未用 resolve_root）
⚠️ unknown 比例持续增长（>30%）
⚠️ 能力覆盖率下降（available < total）
```

### 需要标记为 Evolution Event

```
📌 首次出现：
  - 架构边界外行为
  - 新治理层建立
  - 自主决策链引入
```

---

## 偏差判定流程

```text
Evolution Snapshot
    ↓
对比 SYSTEM-EVOLUTION-BASELINE-001
    ↓
+── 正常演化 → 仅记录
│
+── 能力缺口 → 记录为 observation
│
+── 基线偏离 → 记录为 drift event
│
+── 架构越界 → 记录为 boundary_violation event
```

---

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v001 | 2026-07-22 | Initial. 5 维度基线: 规模/能力/边界/建设状态/演化规则 |
