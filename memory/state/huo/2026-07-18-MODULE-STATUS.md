# Module Status (2026-07-18)

> 燃🔥 维护域模块运行状态。
> 移出 MEMORY.md，仅终端身份读取。

---

## 外卖点餐系统

| 字段 | 值 |
|------|-----|
| 状态 | 方案阶段 |
| 方向 | 微信小程序 |
| 备注 | 待龙哥定方案 |

---

## Ollama 调优

| 字段 | 值 |
|------|-----|
| 状态 | 已出方案 |
| 方案 | OLLAMA_NUM_THREADS=4 + Nice=10 |
| 备注 | 待龙哥执行 |

---

## 彩票系统 v1.1

| 字段 | 值 |
|------|-----|
| 状态 | 冻结 |
| 契约 | 11份，`memory/state/huo/LOTTERY-*.md` |
| 脚本 | `.local/bin/lottery/` (engine/checker/fetch/daily/retry) |
| 推送 | `hooks/oek-ci-gate/push-notify.mjs` |
| Owner | 燃🔥 |
| Assist | 烬🔥 |

### Timer

| 彩票 | 预测 | 核对 |
|------|------|------|
| SSQ | 二/四/日 18:15 | 二/四/日 22:15 |
| DLT | 一/三/六 18:25 | 一/三/六 22:25 |
| KL8 | 每天 18:30 | 每天 22:30 |

| 任务 | 时间 |
|------|------|
| 数据采集 | 每天 21:00 |
| 日报 | 每天 22:35 |
| 重试 | 每小时:05 |

### 日志
- `memory/events/huo/2026-07-17.md` — 全量建设记录
- `memory/events/huo/2026-07-18.md` — 治理修复
- `memory/data/lottery/` — 彩票原始数据
