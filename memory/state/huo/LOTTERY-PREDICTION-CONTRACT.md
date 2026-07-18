# LOTTERY-PREDICTION-CONTRACT.md v1.0

> 预测验证闭环契约：定义预测号码的生成、存储、验证边界。
> 定位：Phase C → C-2 Prediction Checker

---

## 1. 预测 vs 事实 边界

| 实体 | 存储位置 | 类型 | 是否事实 |
|------|----------|------|----------|
| 开奖事件 | `events/lottery/` | event | ✅ 是 |
| 预测号码 | `cache/lottery/predictions/` | derived | ❌ 否 |
| 核对结果 | `cache/lottery/check/` | derived | ❌ 否 |

**核心约束**：预测和核对结果均为衍生数据（derived result），不进入 events。

---

## 2. 预测来源

目前支持的预测来源：

| Source ID | 生成方式 | 状态 |
|-----------|----------|------|
| strategy-v1 | 内置策略（可选：随机/热号/遗漏） | pending |
| external-import | 外部文件 / 手动创建 | pending |

---

## 3. 预测格式

```json
{
  "game": "SSQ",
  "issue": "2026081",
  "prediction_id": "p001",
  "generated_at": "2026-07-17T15:00:00Z",
  "source": "strategy-v1",
  "strategy_version": "1.0",
  "red": [6, 10, 18, 22, 24, 30],
  "blue": 12
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| game | string | ✅ | SSQ / DLT / KL8 |
| issue | string | ✅ | 目标期号 |
| prediction_id | string | ✅ | 预测唯一标识 |
| generated_at | datetime | ✅ | 生成时间 |
| source | string | ✅ | 来源标识 |
| strategy_version | string | ✅ | 策略版本 |
| red / front | int[] | ✅ | 对应彩种的前区号码 |
| blue / back | int / int[] | ✅ | 对应彩种的后区号码 |
| numbers | int[] | ✅ | KL8 专用，20个号码 |

---

## 4. 核对输出格式

```json
{
  "game": "SSQ",
  "issue": "2026081",
  "prediction_id": "p001",
  "result": {
    "red_hit": 3,
    "blue_hit": 1,
    "total_hit": 4,
    "grade": "四等奖",
    "red_matched": [6, 10, 24],
    "blue_matched": true
  },
  "checked_at": "2026-07-17T16:00:00Z"
}
```

存放路径：`cache/lottery/check/{prediction_id}.json`

---

## 5. 验证规则

Checker 执行：

1. 读取 `events/lottery/{game}.jsonl` 匹配 `issue`
2. 按游戏规则比对号码
3. 写入 `cache/lottery/check/`

校验：

- 号码范围：SSQ 红球 1-33，蓝球 1-16
- DLT 前区 1-35，后区 1-12
- KL8 1-80
- 目标期号必须存在对应的开奖事件
- 不存在的期号 → 错误输出，不进入缓存

---

## 6. 依赖关系

```yaml
lottery.check:
  description: compare prediction with lottery event
  depends_on:
    - event.read
  produces:
    - cache/lottery/check/*
  lifecycle: stateless per run
```


---

## 10. 预测身份（Prediction Identity）

每条预测在生成时即确定身份标签：

```json
{
  "game": "SSQ",
  "issue": "2026082",
  "prediction_id": "pred-ssq-2026082-01",
  "purpose": "official",
  "status": "published",
  "generated_at": "2026-07-17T18:15:00Z"
}
```

### purpose 定义

| 值 | 说明 | 参与自动核对 |
|------|------|-------------|
| official | 正式预测（timer 定时生成） | ✅ |
| test | 手工/调试/回归测试 | ❌ |
| manual | 用户手动输入验证 | ❌ |

### status 定义

| 值 | 说明 |
|------|------|
| published | 已发布，可参与核对 |
| superseded | 被后续预测取代（补跑时） |
| cancelled | 失效 |

---

## 11. 核对锚定规则

开奖核对只能锚定唯一的官方预测，不依赖时间顺序。

```
Anchor:
  lottery: SSQ
  issue: 2026082
  purpose: official
    ↓
checker 精确匹配
    ↓
输出核对结果
```

任何 purpose=test/manual 的预测均不得参与自动核对。
