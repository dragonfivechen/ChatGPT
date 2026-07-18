# LOTTERY-SOURCE-RETRY-CONTRACT.md v1.0

> Source Retry Contract：定义 fetch 失败后的重试策略和边界。
> 位置：Source Layer，不触及 Validator / Event Append。

---

## 1. 重试边界

```
check timer (22:15/22:25)
    |
    v
fetch attempt #1
    |
    +-- 成功 → Validator → Cross Verify → Event Append
    |
    +-- 失败 → source-status (attempt=1, status=retrying)
                  |
                  v
            retry timer (每小时)
                  |
                  v
            fetch attempt #2..12
                  |
                  v
            成功 → Validator → Cross Verify → Event Append
            失败12次 → Telegram 告警
```

**核心规则**：重试在 Source Layer 完成，成功后才进入 Validator → Event Append。

---

## 2. Retry 参数

```yaml
retry:
  enabled: true
  interval: 1h
  max_attempts: 12
  stop_condition:
    success: true
    exhausted: true
  append_event:
    only_after_validation: true
```

---

## 3. 状态记录

存放：`cache/lottery/source-status/`

### 重试中

```json
{
  "game": "SSQ",
  "target_issue": "2026081",
  "attempt": 3,
  "max_attempts": 12,
  "last_error": "500m timeout",
  "last_try": "2026-07-17T23:15:00Z",
  "next_retry": "2026-07-18T00:15:00Z",
  "status": "retrying"
}
```

### 已完成

```json
{
  "game": "SSQ",
  "target_issue": "2026081",
  "attempt": 4,
  "status": "completed",
  "completed_at": "2026-07-17T23:18:00Z"
}
```

### 失败

```json
{
  "game": "SSQ",
  "target_issue": "2026081",
  "attempts": 12,
  "status": "failed",
  "reason": "source unavailable after 12 attempts",
  "last_error": "500m + cwl both failed"
}
```

---

## 4. 失败处理

12 次全部失败：

- 不再写入 events（宁可缺一期，不写错一期）
- Telegram 告警：源不可用
- 等待人工处理

---

## 5. 双源策略

| 情况 | 行为 |
|------|------|
| 500成功，cwl成功 | 正常进入事件 |
| 500成功，cwl失败 | verify_pending，等待重试 verify |
| 500失败 | 重试 500 |
| 500重试成功，cwl恢复 | 补充 verify |
| 全部失败 | 缺一期 |

**不自动切源**：500 失败时不自动用 cwl 主写入，保持 primary/verify 关系。

---

## 6. 不碰的边界

- ❌ 不直接写入 events
- ❌ 不自动切换源
- ❌ 不修改 EVent Provenance
- ❌ 不在失败时生成 mock 数据替代

