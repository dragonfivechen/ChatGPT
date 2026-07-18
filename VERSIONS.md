# Version Inventory

> 系统关键依赖版本记录。用于环境恢复和跨版本排查。

## Runtime

| 组件 | 版本 |
|------|------|
| OpenClaw | v2026.5.20 (e510042) |
| Node.js | v22.23.1 |
| npm | (bundled with Node) |
| Python | 3.x |
| Ollama | latest (systemd service) |

## OS

| 项目 | 值 |
|------|-----|
| OS | Linux 6.17.0-40-generic (x64) |
| Distribution | Ubuntu (or衍生) |
| Host | dragonfive-HP-MP9-G4-Retail-System-AMS |
| CPU | Intel i5-8500 (6 cores) |
| RAM | 8GB (7.7GB usable) |

## Models

| Model | Source | Role |
|-------|--------|------|
| DeepSeek V4 Flash | API (deepseek) | Primary conversation model |
| qwen2.5:3b | Ollama (local) | Fallback / evaluation / observation |

## Storage

| Path | Purpose |
|------|---------|
| `~/.openclaw/` | OpenClaw runtime data (config, sessions, delivery-queue, telegram spool) |
| `~/.openclaw/workspace/` | Agent workspace (scripts, contracts, events, memory) |
| `/backup/` | Daily full backups (tar.zst, 7-day retention) |
| `~/.local/archive/` | Legacy design assets (07-10 pre-governance batch) |
