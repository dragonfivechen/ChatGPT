# SYSTEM-EVOLUTION-BASELINE-001

> **系统发展坐标系，不是资产快照。**
> 回答：当前系统处于什么阶段，具备什么结构，未来变化是否属于正常演化，还是偏离方向或缺少建设。
>
> **状态:** PROPOSAL — 待审核后冻结
> **来源:** ASSET-SNAPSHOT-002 / CAP-SNAPSHOT-001 / CONTRACT-REGISTRY / PHASE_STATUS / SYSTEM-BASELINE-OBSERVATION

---

## 1. 系统规模基线（System Scale）

| 维度 | 值 |
|:-----|:----|
| assets_total | 247 |
| asset_categories | 7 (active/frozen/duplicate/idle/deprecated/incomplete/unknown) |
| modules (L1) | 21 |
| domains (L0) | 9 |
| documents | 7 |
| scripts | 51 |
| services | 19 |
| timers | 17 |
| contracts | 41 |

**用途：** 检测无控制增长、大量孤立资产、文档/代码比例异常。

---

## 2. 能力覆盖基线（Capability Coverage）

| 维度 | 值 |
|:-----|:----|
| capability_domains | 6 |
| capabilities_total | 24 |
| available | 24 |
| domain_coverage | Governance 4/4, Runtime 4/4, Monitoring 5/5, Trading 4/4, Lottery 4/4, Infrastructure 3/3 |

**用途：** 新增模块后检查是否产生能力缺口。不是追踪能力数量增长，而是追踪模块→能力的映射是否完整。

---

## 3. 架构边界基线（Architecture Boundary）

| 维度 | 值 |
|:-----|:----|
| frozen_contracts | 3 (CREDENTIAL-ACCESS, PHASE-7.1-AUDIT, TRADING-RUNTIME) |
| frozen_modules | market_futures (baseline_status: FROZEN) |
| governance_version | stable |

**演化路径：** proposal → implementation → freeze

**异常：** frozen state 被直接修改 → 产生 drift

---

## 4. 观察体系基线（Observation Coverage）

| 观察层 | 状态 |
|:-------|:----:|
| asset_observation | ✅ |
| capability_observation | ✅ |
| contract_observation | ✅ |
| runtime_observation | ⚠️ partial |
| baseline_observation | ✅ |
| system_evolution_observation | ✅ |
| semantic_index | ✅ |
| file_mapping | ✅ |

**用途：** 系统复杂度增加时，观察能力是否同步跟上。若 assets 翻倍但 observers 不变 → Observation Coverage Drift。

---

## 5. 建设阶段基线（Evolution Stage）

```json
{
  "stage": "stabilization",
  "phase": "observation",
  "description": "建设 → 冻结 → 观察 → 证据驱动演化"
}
```

当前不是扩张阶段。若后续出现大量新模块、新治理层、新系统层建设，需确认是否偏离当前阶段。

---

## 6. 增长规则（Growth Rules）

### 正常演化（只记录）

```text
+ 文档更新
+ 观察数据增长
+ 新模块建设记录
+ 能力补齐
+ 新 observer 加入
+ observer 深度扩展
+ proposal → implementation → freeze
```

### 建设缺口（输出 CAPABILITY_GAP）

```text
+ 新增模块
  → capability mapping missing
```

### 基线漂移（输出 BASELINE_DRIFT）

```text
⚠️ frozen contract changed
⚠️ runtime boundary changed
⚠️ frozen module state changed
⚠️ 大量重复资产 (duplicate growth)
⚠️ unknown 比例持续 >30%
⚠️ 能力覆盖率下降 (available < total)
⚠️ 路径回归硬编码
⚠️ 观察层变为治理层
⚠️ 自动修复/自动补齐引入
```

---

## 后续 Diff 类型

```text
EVOLUTION_SNAPSHOT
    ↓
对比 SYSTEM-EVOLUTION-BASELINE-001
    ↓
+── 正常演化 → 记录
│
+── 建设缺口 → CAPABILITY_GAP event
│
+── 基线漂移 → BASELINE_DRIFT event
```

---

## 生命周期

```text
EVOLUTION-SNAPSHOT-001
  ↓
SYSTEM-EVOLUTION-BASELINE-001 (PROPOSAL)
  ↓  人工审核
BASELINE FROZEN
  ↓
system-evolution-observer 自动 diff
```

---

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v001 | 2026-07-22 | Initial. 6 维度：规模/能力/边界/观察/阶段/规则。状态 PROPOSAL。 |
