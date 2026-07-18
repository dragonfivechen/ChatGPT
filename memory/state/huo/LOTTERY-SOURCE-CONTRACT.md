# LOTTERY-SOURCE-CONTRACT.md v1.0

> Lottery Source Layer 契约：定义外部数据源的边界、信任模型和失败处理。
> 位置：治理层（Governance Layer）

---

## 1. 源清单

| Source ID     | Type     | Games          | Method               | Priority | Fallback       |
|---------------|----------|----------------|----------------------|----------|----------------|
| 500-headless  | external | SSQ / DLT / KL8| Browser render (DOM) | primary  | cwl, mock      |
| cwl           | external | SSQ            | JSON API             | fallback | mock           |
| mock          | internal | SSQ / DLT / KL8| Local random gen     | fallback | —              |

---

## 2. 信任模型

### 500-headless

- **数据生产者**: 500.com（移动端页面）
- **获取方式**: Chromium headless → DOM extraction
- **信任边界**: 观察层（observation），非事实权限
- **验证者**: lottery-validator（确认号码格式、范围、完整性）

### cwl

- **数据生产者**: 中国福利彩票发行管理中心（官方）
- **获取方式**: HTTPS JSON API
- **信任边界**: 官方权威源，可直接进入 validator
- **验证者**: lottery-validator（格式检查）

### mock

- **生产者**: 本地 pseudo-random
- **用途**: 测试/开发商/故障降级
- **信任边界**: 仅开发环境使用

---

## 3. 事实链

```
[external source]  →  raw payload  →  validator  →  event append  →  events/lottery/
       ↑                    ↑               ↑              ↑
   observation         未验证         规则验证       事实固化
```

关键约束：**source 输出 raw payload，validator 产生 event fact**。

---

## 4. 失败处理

| 故障场景                | 行为                                                   |
|------------------------|--------------------------------------------------------|
| 500.com 超时/不可达     | 5s 超时 → 切 cwl（SSQ）/ mock（DLT/KL8）              |
| cwl API 异常           | 切 mock                                                |
| Chrome 崩溃            | 自动重试 1次 → 切 fallback                              |
| 所有源都不可用          | mock fallback → events 标记 source=mock                  |
| 号码格式异常           | validator 拒绝 → 写入拒绝日志 → 通知                     |

---

## 5. 降级链

```
500-headless  →  cwl (SSQ only)  →  mock
     ↑                  ↑               ↑
   primary           fallback         last resort
```

---

## 6. Issue Contract

### 6.1 期号来源约束

期号必须来自开奖源，禁止由系统推算。

| 彩种 | 格式 | 示例 | 有效范围 |
|------|------|------|----------|
| SSQ  | YYYYNNN | 2026081 | 7位，年+3位序列 |
| DLT  | YYYYNNN | 2026079 | 7位，年+3位序列 |
| KL8  | YYYYNNN | 2026187 | 7位，年+3位序列 |

```json
{
  "game": "SSQ",
  "issue": "2026081",      // 必须来自数据源
  "draw_date": "2026-07-16",
  "source": "500-headless"
}
```

### 6.2 期号三重校验

**第一层 — 格式校验**
- 7位数字
- 前4位为有效年份
- 后3位为数字
- 拒绝不符合格式的数据

**第二层 — 时间校验**
- issue 的前4位应与 draw_date 的年份一致
- 差异超过1年 → reject + log

**第三层 — 连续性校验**
- 读取 events/lottery/{game}.jsonl 最新 event
- 新 issue >= 最后 issue：正常
- 新 issue > 最后 issue + 1：WARNING（丢期），仍接受
- 新 issue < 最后 issue：REJECT（期号回滚）

### 6.3 双源交叉验证（推荐）

SSQ 已有双源：
- primary: 500-headless
- cross-check: cwl

流程：
```
500: issue=2026081, numbers=06 10 12 15 24 27 + 12
cwl:  issue=2026081, numbers=06 10 12 15 24 27 + 12
      ↓
compare: issue_equal=true, numbers_equal=true
      ↓
进入events（带provenance）
```

不一致 → 阻断 append → 告警。

---

## 7. Event Provenance

每个事件包含来源验证元数据：

```json
{
  "event_id": "lottery-ssq-2026081",
  "type": "LOTTERY_DRAW",
  "game": "SSQ",
  "issue": "2026081",
  "source": {
    "primary": "500-headless",
    "verified_by": "cwl"
  },
  "validation": {
    "issue_check": "pass",
    "number_check": "pass",
    "continuity": "ok"
  },
  "payload": { ... }
}
```

---

## 8. 源方法约束

- 外部源只通过 `sources/` 脚本访问，不直接写入 events
- 所有 external source 输出必须经过 validator
- mock 源仅在开发/故障降级时使用
- 新增外部源需更新本契约 + CAPABILITY-REGISTRY.md
