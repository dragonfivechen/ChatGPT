# report_pipeline_v2 — 统一日报数据管道设计

> 目标：将两路日报合并为单一日志出口，消除 22:15/22:25/22:30 三次简报 + 22:35 完整版的冗余。

---

## 当前状态（迁移前）

```
22:10 fetch_only
 │
 ├─ 22:15 ssq-check → worker(A) → check → worker(B-2简报) → notify "开奖日报"  ❌
 ├─ 22:25 dlt-check → worker(A) → check → worker(B-2简报) → notify "开奖日报"  ❌
 ├─ 22:30 kl8-check → worker(A) → check → worker(B-2简报) → notify "开奖日报"  ❌
 │
 └─ 22:35 daily → compute_stats → check_prediction → daily_report_gen → notify "彩票日报"
```

A-4 → events/*.jsonl
C-2 → analysis/*.json
C-3 → statistics/*.json
B-2 → last_report.txt → B-3 notify

daily_report.sh 内部又执行一次 compute_stats + check_prediction（与前面重复）。

---

## 两份日报能力对照

| 模块 | Worker B-2 简报 | daily_report_gen.py |
|------|----------------|---------------------|
| 彩种覆盖 | SSQ, DLT | SSQ, DLT, **KL8** |
| 开奖号码 | ✅ | ✅ |
| 奇偶/和值 | ✅ | ❌ |
| 热号TOP5 | ✅ | ❌ |
| 区间分布 | ✅(SSQ only) | ❌ |
| 数据源验证 | ❌ | ✅ (source + validation字段) |
| 期号校验 | ❌ | ✅ |
| 预测核验命中 | ❌ | ✅ |
| 系统事件统计 | ❌ | ✅ |
| 数据输入 | analysis + statistics | events + check |
| 调用时机 | worker C-2/C-3 后立即 | daily_report.sh 内 |

**结论：互补，非重复。** Daily_report_gen 有事件事实面，B-2 有统计面。

---

## 统一日报模型 report_schema_v2（已定稿，6模块）

```
A: HEADER — 标题/日期
B: DRAW RESULTS — SSQ/DLT/KL8 开奖号码
C: DATA VERIFICATION — source / issue_check / number_check
D: DRAW ANALYSIS — 奇偶、和值、热号TOP5、区间分布
E: PREDICTION VERIFICATION — hit / grade
F: SYSTEM STATUS — 事件文件/总数
```

---

## 数据源映射

| 报表模块 | 数据源 | 当前写入者 | 产生时间 |
|----------|--------|-----------|----------|
| B 开奖号码 | events/*.jsonl | worker A-4 | 22:10 fetch |
| C 数据验证 | events/*.jsonl.validation | worker A-4 | 22:10 fetch |
| D 奇偶/和值 | analysis/*.json | worker C-2 | 22:10 fetch |
| D 热号TOP5 | statistics/*_latest.json | worker C-3 | 22:10 fetch |
| D 区间分布 | statistics/*_latest.json.ranges | worker C-3 | 22:10 fetch |
| E 预测核验 | check/*.json | check_prediction.sh | 22:15/22:25/22:30 |
| F 系统状态 | events dir stat | — | 实时 |

**所有数据源在 22:30 前全部就位。** 统一日报只需在最后读取。

---

## 目标状态（迁移后）

```
22:10 fetch_only
 │
 ├─ 22:15 ssq-check → worker(A) → check → [B-2/B-3 SKIP]
 ├─ 22:25 dlt-check → worker(A) → check → [B-2/B-3 SKIP]
 ├─ 22:30 kl8-check → worker(A) → check → [B-2/B-3 SKIP]
 │
 └─ 22:35 daily → report_pipeline_v2 → notify
                │                   │
                ├ events/*.jsonl     └ 单次 push "🎰 彩票日报"
                ├ analysis/*.json
                ├ statistics/*.json
                └ check/*.json
```

关键变化：
| 项目 | 前 | 后 |
|------|----|-----|
| B-2/B-3 | 每个 check timer 产生一次 | SKIP_REPORT=true |
| daily_report.sh | 内部重复 compute_stats + check_prediction | 不再重复 |
| 日报生成 | daily_report_gen.py（缺 analysis） | **新统一生成器** |
| 输出次数 | 3~4 次通知 | **1 次通知** |

---

## 执行步骤

### Step 3-a: 编写 unified_report_gen.py

输入：
- events/ssq.jsonl, events/dlt.jsonl, events/kl8.jsonl
- analysis/ssq.json, analysis/dlt.json
- statistics/ssq_latest.json, statistics/dlt_latest.json
- check/*.json（所有预测核验结果）

输出：
- stdout → 格式化的完整日报文本

实现方式：
- 以 daily_report_gen.py 为骨架
- 注入 analysis 统计段（奇偶/和值/热号/区间）
- 保持 KL8 支持
- 保持 validation/check 部分

### Step 3-b: 修改 daily_report.sh

- 去掉重复的 compute_stats 调用（worker C-3 已生成）
- 去掉重复的 check_prediction 调用（check timer 已执行）
- 替换 daily_report_gen.py → unified_report_gen.py

### Step 4: 关闭旧出口

- worker.sh B-2/B-3: 统一由 `SKIP_REPORT=true` 控制
- fetch_only 已有 SKIP_REPORT=true（不受影响）
- check service 注入 SKIP_REPORT=false（通过 systemd service 的 Environment=）
  - 初期保持 SKIP_REPORT=false 以观察
  - 待 unified_report_gen.py 验证通过后改为 true
