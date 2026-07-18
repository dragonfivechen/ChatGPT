# LOTTERY-PREDICTION-STRATEGY-CONTRACT.md v1.0

> 预测策略契约：定义多策略候选池 → 评分 → 选择的边界和格式。
> 定位：Prediction Engine v2，叶节点增强，不改事实链。

---

## 1. 边界

```
事实链（不动）      预测链（扩展）
500m/cwl           strategy pool
  ↓                     ↓
validator              candidates
  ↓                     ↓
events/lottery         scoring
  ↓                     ↓
statistics / check     top 5 → Telegram
```

**核心规则**：
- 预测链不产生 event fact
- 策略不反向修改架构
- 评分不解释为"中奖概率"

---

## 2. 策略输出格式

每个策略输出 10 组候选号码，格式：

```json
{
  "strategy_id": "frequency_v1",
  "game": "SSQ",
  "issue": "2026082",
  "generated_at": "2026-07-17T11:15:00Z",
  "candidates": [
    {
      "candidate_id": "c001",
      "red": [1, 5, 12, 18, 23, 31],
      "blue": 7
    }
  ],
  "metadata": {
    "version": "1.0",
    "description": "基于历史频率加权的随机采样"
  }
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| strategy_id | ✅ | 唯一标识，如 `frequency_v1` |
| game | ✅ | SSQ / DLT / KL8 |
| issue | ✅ | 目标期号 |
| generated_at | ✅ | 生成时间 UTC |
| candidates[] | ✅ | 候选号码数组，每组独立 |
| candidate_id | ✅ | 候选唯一标识 |
| red / front / numbers | ✅ | 对应彩种的号码 |
| blue / back | ✅ | 后区号码 |
| metadata | ✅ | 策略描述 |

---

## 3. 第一版策略池

| Strategy ID | 方法 | 说明 |
|-------------|------|------|
| frequency_v1 | 频率加权 | 历史高频号码更高概率被选中 |
| distribution_v1 | 区间均衡 | 保证三区间均匀覆盖 |
| omission_v1 | 遗漏追踪 | 长时间未出号码优先 |
| random_balance_v1 | 随机平衡 | 纯随机但约束奇偶/大小/和值 |
| pattern_v1 | 组合结构 | 基于常见组合模式（连号/同尾） |

每个策略输出 10 组 → 50 组候选池。

---

## 4. 评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 奇偶平衡 | 0.2 | 最佳 3:3 或 2:4 |
| 区间覆盖 | 0.2 | 三区间号码分布均匀度 |
| 和值范围 | 0.15 | 在历史和值均值 ±2σ 内 |
| 重复度惩罚 | 0.15 | 与其他候选重复越低越好 |
| 分布偏离度 | 0.15 | 偏离历史分布的代价 |
| 遗漏分 | 0.15 | 包含遗漏号码加分 |

总分 = Σ(维度分 × 权重)，范围 0-100。

**注意**：评分是选择排序指标，不代表中奖概率。

---

## 5. Final Selector

```
50 candidates
      ↓
scoring
      ↓
rank by score
      ↓
top 5
      ↓
Telegram
```

输出写入 `cache/lottery/predictions/{game}_{issue}_*.json`，
供 checker 开奖后验证。

---

## 6. 不做清单

- ❌ 评分 → 中奖概率宣称
- ❌ 结果反馈 → 自动修改策略权重
- ❌ 策略自动演化/生成
- ❌ 策略元优化（RL/贝叶斯）
- ❌ 自学习架构变更

---

## 7. 依赖关系

```yaml
lottery.generate:
  description: 基于多策略候选池生成预测号码
  depends_on:
    - event.read (for statistics input)
    - memory.read (for strategy config)
  produces:
    - cache/lottery/predictions/*
  lifecycle: 每次开奖前执行
```
