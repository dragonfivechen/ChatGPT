# Rule Registry: C0-C4 Inline Rules (实验规则 v0.1)

## File Info

- **Source:** 测试阶段临时规则（内嵌于 audit 脚本，未独立成文件）
- **Version:** v0.1 (2026-07-21)
- **Status:** experimental
- **Owner:** 燃🔥

---

## Rule C0: Correction Candidate (Entry Gate)

| Field | Value |
|-------|-------|
| Rule ID | C0-ENTRY-001 |
| Status | experimental |
| Purpose | 全量入口，筛选所有疑似用户纠偏消息 |

### Match Logic
```
不要
别 
不对
不是[^因]
我说的是
你搞错了
你理解错了
你误会了
重新回答
不需要你
我没说
谁让你
你凭什么
我只问你
不需要解释
不要说
别说了
我问的是
你少来
不应该
不行
错了
不对吧
哪有
不是这样
```

Any match → candidate enters C1-C4 classification.

### Exclusion
None — C0 is entry gate, not filter.

### Evidence Output
```
session_id, timestamp, matched_text
```

### Known Limitations
- "不是这样" 在 "不是这样设计的" 中命中，但用户只是在讨论方案
- "不对" 在 "时间不对应" 中命中，但不是纠偏
- "错了" 在用户自述中命中

---

## Rule C1: Content Correction

| Field | Value |
|-------|-------|
| Rule ID | C1-CONT-001 |
| Status | experimental |
| Purpose | 用户纠正模型输出内容 |

### Match Logic
```
时间不对
数据不对
数字错了
事实错误
信息有误
日期不对
价格不对
错了
不对
不对吧
```

### Exclusion
- 用户说"我说的不对"（自述）
- 用户说"这里不对应"（不是否定）

### Evidence Output
```
session_id, timestamp, matched_text
```

### Known Limitations
- "不对" 过于宽泛，大量非纠偏场景命中
- 无法区分"你错了"（行为）和"这个数据错了"（内容）

---

## Rule C2: Strategy Correction

| Field | Value |
|-------|-------|
| Rule ID | C2-STRAT-001 |
| Status | experimental |
| Purpose | 用户纠正方案方向 |

### Match Logic
```
方案不对
设计问题
方向不对
架构不合理
不应该这样设计
不是这样设计
```

### Exclusion
None specified.

### Evidence Output
```
session_id, timestamp, matched_text
```

### Known Limitations
- 命中率极低，当前全量数据中 0 次命中
- 覆盖不足，真实方案讨论可能使用不同措辞

---

## Rule C3: Behavior Correction

| Field | Value |
|-------|-------|
| Rule ID | C3-BEHAV-001 |
| Status | experimental |
| Purpose | 用户否定模型行为模式（重点） |

### Match Logic
```
不要.*(做|执行|说|问|提|讲|用|拿|改|动|碰|再|总是)
别.*(给我|再去|又来|老|动不动|拿|用)
不需要你
谁让你
你凭什么
我没让你
没让你
你搞错了
你理解错了
你弄错
```

### Exclusion
- "不要" 后跟名词短语（"不要解释" → 格式问题, 不是行为纠正）
- "你搞错了" 可能指内容错误而非行为

### Evidence Output
```
session_id, timestamp, matched_text, context_before, context_after
```

### Known Limitations
- "你搞错了" 经常是内容纠正被误标为行为纠正
- "不要讲" （"不要讲故事" vs "不要讲这个话题"）歧义
- 无法区分"不要做X"（行为）和"不用做X"（建议）

---

## Rule C4: Format / Interaction Correction

| Field | Value |
|-------|-------|
| Rule ID | C4-FMT-001 |
| Status | experimental |
| Purpose | 用户纠正回复方式/交互风格 |

### Match Logic
```
不要.*(解释|问|说|回复|发|分|拆)
别.*回复
不需要解释
不要说
别说了
直接
简洁
```

### Exclusion
- "直接" 在 "直接部署" 中不是格式纠正
- "简洁" 在 "简洁高效" 中不是格式纠正

### Evidence Output
```
session_id, timestamp, matched_text
```

### Known Limitations
- "直接" 是高频词，大量误报（当前 42 次命中中多数是误报）
- "简洁" 在句中做形容词时误标
- 无法区分"要求简洁输出"和"描述简洁这个特点"
