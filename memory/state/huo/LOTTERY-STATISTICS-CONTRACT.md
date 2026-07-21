# LOTTERY-STATISTICS-CONTRACT.md v1.0

```yaml
contract:
  name: LOTTERY-STATISTICS
  version: v1.0
  level: L2
  parent: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
  scope: lottery statistics boundary
  owner: 燃🔥
  status: active
```

> 开奖统计契约：定义描述性统计的范围、格式和边界。
> 定位：Phase C → C-3 Production Statistics

---

## 1. 统计 vs 预测 边界

| 实体 | 行为 | 是否做 |
|------|------|--------|
| 号码出现频率 | 计数统计 | ✅ |
| 奇偶比例 | 分布统计 | ✅ |
| 和值/区间分布 | 描述统计 | ✅ |
| 热号推荐 | 基于频率的选号建议 | ❌ |
| 冷号追踪策略 | 基于遗漏的预测 | ❌ |
| AI选号 | 模型生成号码 | ❌ |
| 中奖概率宣称 | 声称某种模式提高中奖率 | ❌ |

**核心原则**：统计 = 描述已发生事实。不做预测、不做推荐、不做概率宣称。

---

## 2. 统计范围

### SSQ 双色球

| 指标 | 说明 | 窗口 |
|------|------|------|
| 红球频率 | 1-33 单号出现次数 | 全部 / 最近30期 |
| 蓝球频率 | 1-16 单号出现次数 | 全部 / 最近30期 |
| 奇偶比分布 | 红球奇偶比例统计 | 全部 / 最近30期 |
| 大小比分布 | 红球大小(17为界) | 全部 / 最近30期 |
| 区间分布 | 1-11/12-22/23-33 三区间 | 全部 / 最近30期 |
| 和值统计 | 红球和值分布 | 全部 / 最近30期 |
| 连号统计 | 相邻号码出现情况 | 全部 / 最近30期 |

### DLT 大乐透

| 指标 | 说明 | 窗口 |
|------|------|------|
| 前区频率 | 1-35 单号出现次数 | 全部 / 最近30期 |
| 后区频率 | 1-12 单号出现次数 | 全部 / 最近30期 |
| 前区奇偶 | 前区奇偶比分布 | 全部 / 最近30期 |
| 后区奇偶 | 后区奇偶比分布 | 全部 / 最近30期 |
| 前区和值 | 前区号码和分布 | 全部 / 最近30期 |
| 后区和值 | 后区号码和分布 | 全部 / 最近30期 |

### KL8 快乐8

（暂不做统计，与 SSQ/DLT 优先）

---

## 3. 输出格式

```json
{
  "game": "SSQ",
  "generated_at": "2026-07-17T16:00:00Z",
  "period": "latest",
  "total_draws": 1,

  "red_frequency": {
    "total": 1,
    "counts": {"1": 0, "2": 0, ..., "33": 0},
    "top5": [{"num": 6, "count": 1}, ...],
    "bottom5": [{"num": 1, "count": 0}, ...]
  },

  "blue_frequency": {
    "total": 1,
    "counts": {"1": 0, ..., "16": 0}
  },

  "odd_even": {
    "ratio_counts": {"2:4": 1, "3:3": 0, ...},
    "current": "2:4"
  },

  "big_small": {
    "ratio_counts": {"3:3": 0, "2:4": 1, ...},
    "current": "2:4"
  },

  "ranges": {
    "range1_count": 1,
    "range2_count": 4,
    "range3_count": 1
  },

  "sum_red": {
    "min": 94,
    "max": 94,
    "avg": 94.0,
    "current": 94
  }
}
```

存放：`cache/lottery/statistics/{game}_{period}.json`

---

## 4. 依赖关系

```yaml
lottery.statistics:
  description: 基于事件事实的描述性统计
  depends_on:
    - event.read
  produces:
    - cache/lottery/statistics/*
  lifecycle: 每次开奖后更新
```

---

## 5. 不做清单（明确排除）

- ❌ 热号推荐 / 冷号追踪
- ❌ 预测号码生成
- ❌ AI / ML 模型
- ❌ 中奖概率计算
- ❌ 选号模板 / 策略推荐
- ❌ 自学习 / 自适应统计

