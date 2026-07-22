# Asset Query Guide v1.0

> 模型引用资产查询链的入口说明。
>
> 当用户请求涉及资产定位时，按此链查询。

---

## When to Use

用户问以下问题类型时触发：

```text
"XX 模块在哪里"
"XX 文件在哪"
"哪个系统负责 XX"
"盘点 XX 资产"
"XX 的资产有哪些"
```

## Query Chain

```text
用户表述
   ↓
SYSTEM-ASSET-SEMANTIC-INDEX.md
  (aliases / keywords → Module ID)
   ↓
SYSTEM-ASSET-MODULE-FILE-MAPPING.md
  (Module ID → 具体文件路径)
   ↓
SYSTEM-ASSET-OBSERVATION.md
  (状态 / 分类 / 漂移证据)
```

## Steps

### Step 1: 语义定位

读取 `docs/SYSTEM-ASSET-SEMANTIC-INDEX.md`：

- 匹配 `human.aliases`（精确别名）
- 匹配 `keywords`（语义关键词）
- 得到 Domain (L0) → Module ID (L1)

### Step 2: 文件定位

读取 `docs/SYSTEM-ASSET-MODULE-FILE-MAPPING.md`：

- 按 `module_id` 找到对应块
- `files` 下按分类列举路径

### Step 3: 状态证据

读取 `docs/SYSTEM-ASSET-OBSERVATION.md`：

- `status_source: ASSET-SNAPSHOT-002`
- 分类统计、一致性检查

## Example

```text
用户: "期货策略文件在哪"

Step 1 → Semantic Index
  aliases: ["期货", "futures", "futures-sim"]
  keywords: ["策略", "回测", "行情"]
  → TRD-MODULE-001 (Trading Domain)

Step 2 → File Mapping
  → market_futures/strategies/ma.py
  → market_futures/strategies/breakout.py
  → market_futures/strategies/rsi.py
  → market_futures/strategies/signal.py

Step 3 → Observation
  → status: frozen (core sim), active (live collector/strategy)
  → evidence: ASSET-SNAPSHOT-002
```

## Index Files

| File | Purpose |
|:-----|:--------|
| `docs/SYSTEM-ASSET-SEMANTIC-INDEX.md` | L0/L1 模块语义映射 |
| `docs/SYSTEM-ASSET-MODULE-FILE-MAPPING.md` | L2 模块文件路径 |
| `docs/SYSTEM-ASSET-OBSERVATION.md` | 资产快照 + 分类 + 一致性检查 |
| `memory/data/system/asset-observation.jsonl` | ASSET_SNAPSHOT 事件流 |

## Non-Goals

```
Asset Query Guide
    ≠ 资产管理体系
    ≠ 生命周期控制
    ≠ 自动修复入口
```

---

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial. 触发条件 + 查询链 + 三步流程 + 示例 |
