# Rule Registry: Duplicate Filter (重复检测规则 v1)

## File Info

- **Source:** 内嵌于维护测试脚本（`python3 << 'PYEOF'`）
- **Version:** v1.0 (2026-07-21)
- **Status:** active
- **Owner:** 燃🔥

---

## Rule R1: Expected Repeat Exclusion

| Field | Value |
|-------|-------|
| Rule ID | R1-EXCL-001 |
| Status | active |
| Purpose | 排除预期的周期性重复（状态报告/推送/确认），不被视为缺陷 |

### Match Logic

如果重复文本的前 100 字符匹配以下任一关键词，排除：
```
开盘
收盘
持仓
成交
平仓
信号
timer
定时
推送.*完成
系统.*启动
模块.*上线
日报
周报
已部署
已推送
状态.*正常
守护.*运行
```

### Exclusion
本规则本身就是排除规则。

### Evidence Output
```
session_id, timestamp, text_snippet, matched_keyword
```

### Known Limitations
- 关键词列表可能覆盖不足（遗漏某些周期性消息类型）
- 某些状态推送确实被用户视为干扰，不应完全排除

---

## Rule R2: Short Burst Duplicate

| Field | Value |
|-------|-------|
| Rule ID | R2-BURST-001 |
| Status | active |
| Purpose | 检测短时间窗口内的重复回复 |

### Match Logic
```
1. 同一 session 中连续两条 assistant 消息
2. 前 60 字符完全相同
3. 未被 R1 排除
4. 时间间隔 < 60 秒
```

### Exclusion
- R1 预期重复排除
- 不同类型消息（如 tool result 后跟 assistant 回复）

### Evidence Output
```
session_id, timestamp_prev, timestamp_curr, interval_seconds, text_snippet
```

### Known Limitations
- 60 字符前缀相同不一定代表完全重复（长文本前 60 字相同概率高）
- 60 秒窗口可能过于宽泛
- 无法区分生成重复和发送重复

---

## Rule R3: Semantic Duplicate (实验)

| Field | Value |
|-------|-------|
| Rule ID | R3-SEM-001 |
| Status | experimental |
| Purpose | 检测信息重复但文字不同的情况 |

### Match Logic
```
1. 同一 session 中相邻两条 assistant 消息
2. 前 60 字符不同（通过 R2 检查的跳过）
3. 中文/英文词的 Jaccard 相似度 > 0.5
4. 长度差 < 200 字符
```

Jaccard similarity on 2-char+ n-grams:
```
overlap = |words(A) ∩ words(B)| / |words(A) ∪ words(B)|
threshold: > 0.5
```

### Exclusion
- 已经 R2 匹配的跳过
- 模板化回复

### Evidence Output
```
session_id, text_a, text_b, similarity_score
```

### Known Limitations
- 实验性规则，当前全量数据仅命中 2 次
- Jaccard 阈值 0.5 需要校准
- 无法处理同义词替换

---

## Derived Metric: Burst Duplicate Rate

| Field | Value |
|-------|-------|
| Metric | BURST-RATE-001 |
| Formula | R2 命中数 / 总 assistant 消息数 |
| Purpose | 衡量输出异常的总体比例 |
| Current | ~21% |
