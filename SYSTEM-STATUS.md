# OpenClaw System Status

> 系统状态摘要 — 人阅读入口，不替代源文件。
> Source of Truth: `dragonfivechen/ChatGPT commit 2326ec2` (2026-07-18)

## Baseline

| 项目 | 值 |
|------|-----|
| OpenClaw | v2026.5.20 (e510042) |
| Runtime | Node.js v22.23.1 |
| OS | Linux 6.17.0-40-generic (x64) |
| Host | dragonfive-HP-MP9-G4 (i5-8500, 8GB) |
| Primary Model | DeepSeek V4 Flash (api-key) |
| Fallback Model | Ollama qwen2.5:3b (local) |
| Gateway Port | 18789 (loopback) |
| TG Agent | 烬🔥 (tg-agent) |
| Terminal Agent | 燃🔥 (main) |

## Governance State

| Layer | Status |
|-------|--------|
| Extension Boundary | ✅ FROZEN v1.0 |
| Memory Governance | ✅ FROZEN v1.0 |
| Plugin Governance | ✅ FROZEN v1.0 |
| Data Authority Layer | ✅ Archived (07-10 pre-governance) |
| Delivery Recovery Policy | ✅ Observed (ambiguity protection active) |

## Completed Phases

- Token Observer → deployed, observing
- Watchdog → Recovery disabled, demoted to Observer
- Source-Retry → External Worker boundary compliant
- Lottery → Full topology audit, compliant
- Billing → Lifecycle fixed, returned to systemd-owned oneshot
- Daily Status Report → deployed (timer 08:07 daily)
- GitHub sync → `dragonfivechen/ChatGPT` commit `2326ec2`

## Active Observations

| Item | Status |
|------|--------|
| Local Model Eval (ollama-eval) | Phase 1 token field deployed, 24h observation |
| Daily Status Report | First automated run: 2026-07-19 08:07 |
| Version Drift | Observing — no upgrade planned |
| TUI Streaming Watchdog (30s) | P2 observation — no action |

## Running Workers

| Service | Type | Schedule |
|---------|------|----------|
| oek-billing-snapshot | oneshot | every 5min |
| oek-billing-push | oneshot | every 1h |
| oek-token-observe | oneshot | hourly |
| oek-daily-status | oneshot | daily 08:07 |
| source-retry | oneshot | hourly :05 |
| lottery-{ssq,dlt,kl8}-{predict,check} | oneshot | per game schedule |
| lottery-fetch | oneshot | daily 21:03 |
| lottery-daily | oneshot | daily 22:35 |
| collect-sensors + eval-local | cron | hourly |
| backup-full + audit-backup | cron | daily 03:00 |
| push-daily-report | cron | 09:00, 21:00 |
