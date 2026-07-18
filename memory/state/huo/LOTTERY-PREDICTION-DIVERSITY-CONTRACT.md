# LOTTERY-PREDICTION-DIVERSITY-CONTRACT.md v1.0

> Diversity Selection Layer 契约：定义 Top5 候选之间的组间多样性约束。
> 位置：Prediction Engine v3.1 — 最终选择阶段，不修改生成层/评分层。

---

## 1. 定位

```
70候选池 → Feature Score → Diversity Filter → Top5
                                    ↑
                             新增，不改变上游
```

**不改**：策略生成、熵扰动、反常识、单组评分、70候选池、Checker、Event链。

---

## 2. 多样性约束指标

### 2.1 红球重合惩罚

| 两两交集数 | 惩罚 |
|-----------|------|
| 0-2       | 0    |
| 3         | -15  |
| 4+        | -30  |

目标：Top5 组间红球交集 ≤2。

### 2.2 和值分散约束

将和值区间三等分：

SSQ: 60-100 / 100-120 / 120-160
DLT: 50-90 / 90-110 / 110-150

Top5 至少覆盖 2 个区间。

### 2.3 奇偶结构差异

避免全部相同结构。

| 同结构组数 | 惩罚 |
|-----------|------|
| 3组相同   | -10  |
| 4组相同   | -20  |
| 5组相同   | -30  |

### 2.4 蓝球/后区分散

| 同一蓝球重复次数 | 惩罚 |
|----------------|------|
| 2次            | -5   |
| 3次            | -10  |
| 4次            | -20  |
| 5次            | -30  |

---

## 3. 选择算法

```
selected = []

第1组: 最高单组评分

第2-5组: 贪心选择
  candidate = max(
    remaining,
    key = base_score + diversity_bonus - overlap_penalty
  )
  selected.append(candidate)
```

**diversity_bonus**:
- 与已选所有组的 Jaccard 距离（1-交集/并集）
- 和值区间覆盖奖励（覆盖新区间 +5）
- 奇偶结构差异奖励（不同 +3）

**overlap_penalty**:
- 红球重合惩罚
- 蓝球重复惩罚
- 奇偶同结构惩罚

---

## 4. 输出目标

```
1号: 均衡型（2-2-2）
2号: 低区偏重（3-2-1 或 4-1-1）
3号: 高区偏重（1-2-3 或 1-1-4）
4号: 冷热混合
5号: 熵扰动型
```

**不是**：5个高分近邻。

---

## 5. 不做清单

- ❌ 不修改 70 候选池
- ❌ 不修改单组评分
- ❌ 不修改事实链
- ❌ 不修改策略生成
- ❌ 不修改 Checker

---

## 6. 依赖关系

```yaml
lottery.diversity:
  description: Top5 组间多样性约束
  depends_on:
    - lottery.generate (70候选池)
  produces:
    - cache/lottery/predictions/* (经过多样性过滤)
  lifecycle: 每次预测生成时执行
```
