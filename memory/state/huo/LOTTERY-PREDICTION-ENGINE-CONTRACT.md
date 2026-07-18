# LOTTERY-PREDICTION-ENGINE-CONTRACT.md v1.0

> 预测引擎契约：定义特征提取、策略接口、候选池、评分、熵扰动、反常识的边界。
> 定位：Prediction Engine v3，叶节点增强，不改事实链。

---

## 1. 数据流

```
events/lottery/*.jsonl (N=100期)
         |
         v
  Feature Extractor
  (频率/遗漏/分布)
         |
         +-------------------+
         |                   |
  趋势策略池           扰动策略池
  A:趋势平衡           熵扰动(+20组)
  B:冷热混合           反常识(+10组)
  C:遗漏补偿
  D:分布约束
         |                   |
         +---------+---------+
                   |
            80 candidates
                   |
                   v
            Scoring Layer
    distribution + diversity + entropy + anti_pattern
                   |
                   v
            Top 5 → Telegram
```

---

## 2. Feature Extractor

输入：`events/lottery/{game}.jsonl` 最近 N 期
窗口：N=100 期（或全部，取较小值）

提取：

| 特征 | 说明 |
|------|------|
| frequency | 单号出现次数（热/温/冷分类） |
| omission | 连续未出现期数 |
| odd_even_ratio | 历史奇偶比分布 |
| big_small_ratio | 历史大小比分布 |
| range_dist | 三区间号码分布 |
| sum_range | 和值范围 (均值±σ) |
| pair_freq | 连号出现频率 |
| same_tail_freq | 同尾号出现频率 |

热/温/冷定义：
- 热号：频率 > 均值+0.5σ
- 温号：均值±0.5σ 范围内
- 冷号：频率 < 均值-0.5σ

---

## 3. 策略接口

每个策略接收 feature dict + game + issue + count，输出 N 组候选。

```yaml
strategy:
  input:
    - features (来自 Feature Extractor)
    - game (SSQ/DLT/KL8)
    - issue (目标期号)
    - count (每组输出数，默认10)
  output:
    - candidates[]
    - metadata (策略描述)
```

### Strategy A: 趋势平衡

基于热/温/冷分类的组合生成。
- 从热/温/冷各池按比例采样
- 约束奇偶/区间平衡
- 输出 10 组

### Strategy B: 冷热混合

固定结构：2热 + 3温 + 1冷（SSQ）/ 2热 + 2温 + 1冷（DLT）

### Strategy C: 遗漏补偿

长遗漏号码更高概率被选入组合。

### Strategy D: 分布约束

以目标分布（奇偶3:3 / 大小3:3 / 三区2:2:2）为约束条件生成。

---

## 4. 熵扰动

在候选池层面操作，不是独立策略。

```
基础候选池 (50组)
      ↓
mutation_rate = 20%
      ↓
对每组候选随机替换 N 个位置:
- 随机选 1 个号码替换为相同区间的另一号码
- 或交换热号↔冷号
      ↓
+20组扰动候选
```

控制参数：
- mutation_rate: 10%-30%（默认20%）
- 可替换位置数: 1-2
- 替换源: 同区间/同奇偶的号码

---

## 5. 反常识策略

### 定义

寻找人类选号偏好模式，生成避开这些模式的组合。

人类偏好示例：
- 生日号：1-31 区间集中
- 整齐号：5,10,15,20 倍数号
- 对称：01-06-11-16-21-26 等差数列
- 过度均匀：三区各2个
- 连号偏好：喜欢包含连号

### 策略规则

```
anti_pattern_count = 10组

对每组:
1. 避免 3 个以上号码集中在 1-31（SSQ）
2. 避免 2 个以上号码是 5 的倍数
3. 避免等差数列（公差>5）
4. 避免三区间严格 2:2:2
5. 至少包含 1 个 > 31 的号码
```

### 边界声明

❌ 反常识 ≠ 更容易中奖
✅ 反常识 = 降低候选同质化的机制

---

## 6. 评分维度

```text
Score =
    distribution_score (0-30)   奇偶/大小/区间覆盖度
  + diversity_score  (0-25)    候选间差异度（避免重复）
  + entropy_score    (0-25)    号码离散度（非聚集程度）
  + anti_pattern_score (0-20)  反常识符合度
```

| 维度 | 权重 | 说明 |
|------|------|------|
| distribution_score | 30 | 奇偶/大小/区间分布偏离度越小分越高 |
| diversity_score | 25 | 与其他候选的号码重复越少分越高 |
| entropy_score | 25 | 号码在数轴上的离散程度 |
| anti_pattern_score | 20 | 反常识规则符合数 |

总分范围 0-100，越高表示越适合入选。

**禁止**：中奖概率评分、历史命中预测、模式概率宣称。

---

## 7. 最终输出

```
80 candidates → 去重 → 排序 → Top 5
```

保存：`cache/lottery/predictions/{game}_{issue}_{id}.json`

---

## 8. 不做清单

- ❌ 评分解释为"中奖概率"
- ❌ 策略自动权重学习
- ❌ 策略淘汰/生成（元学习）
- ❌ 基于核对反馈自动调参
- ❌ 反常识玄学化（如"生肖号""幸运号"）

---

## 9. 依赖关系

```yaml
lottery.generate.v3:
  description: 多策略预测引擎（趋势+熵扰动+反常识）
  depends_on:
    - event.read (100期特征)
  produces:
    - cache/lottery/predictions/*
  lifecycle: 每次开奖前执行
```

---

## 10. v3.1 补充：Top-K Diversity Score

### 10.1 目标

单组号码可以均衡，五组号码必须保持结构多样性。

### 10.2 选择算法

贪心多样性选择：

```text
候选池 (70组)
    ↓
第1组: 最高单组评分
    ↓
第2组: 与第1组差异最大 中最高评分
    ↓
第3组: 与前2组差异最大 中最高评分
    ↓
...
    ↓
第k组
```

### 10.3 差异度量

| 维度 | 度量 | 权重 |
|------|------|------|
| 区间结构 | 三区间分布不同的 L1 距离 | 0.4 |
| 号码重叠 | 1 - (交集/并集) 的 Jaccard 距离 | 0.3 |
| 和值偏离 | 和值差归一化 | 0.2 |
| 策略来源 | 不同策略加分，同策略扣分 | 0.1 |

### 10.4 策略分布约束

```yaml
topk_diversity:
  max_same_strategy: 2
```

同一策略最多入选 2 组。

### 10.5 不修改

- Feature Extraction
- 策略池（4策略 + 熵扰动 + 反常识）
- 70候选池
- Scorer 单组评分
- Checker
- Event 链
