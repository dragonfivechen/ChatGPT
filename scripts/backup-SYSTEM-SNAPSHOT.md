# 系统快照

备份时间: 2026-07-17 12:54 CST
生成方式: 每份备份包内携带

## 硬件

| 项 | 值 |
|---|------|
| 型号 | HP MP9 G4 Retail System |
| CPU | Intel Core i5-8500 (6核, 3.0GHz) |
| 内存 | 8GB (7.5GiB) |
| 磁盘 | 125GB NVMe SSD |
| GPU | Intel UHD Graphics 630 (集显, 不用于推理) |

## 软件

| 组件 | 版本 | 运行方式 |
|------|------|---------|
| Ubuntu | 24.04 (noble) | 系统 |
| OpenClaw | 2026.5.20 | user systemd |
| Ollama | 0.32.1 | system systemd |
| Node.js | v22.23.1 | 运行环境 |

## 服务

| 服务 | 状态 | 类型 |
|------|------|------|
| openclaw-gateway | active | user service (port 18789) |
| ollama | active | system service (port 11434) |
| oc-watchdog-stream | inactive | system service (按需启动) |

## 模型

| 模型 | 角色 | 来源 |
|------|------|------|
| deepseek/deepseek-v4-flash | 主力 (云端) | DeepSeek API |
| ollama/qwen2.5:3b | 灾备 (本地) | Ollama, ~1.9GB |

## 用户

- 系统用户: dragonfive
- OpenClaw agent: main
- 推送: Telegram bot (push-gate)

## 网络

- 网关: 192.168.88.1 (OpenWrt)
- DNS: systemd-resolved (127.0.0.53)
- 有线/无线均可

## 定时任务

| 时间 | 任务 |
|------|------|
| 每小时整点 | 传感器采集 + 本地模型评估 |
| 09:00 / 21:00 | 日报推送 (Telegram) |
| 每日 03:00 | 全量备份 + 审计 |

## 关键路径

| 路径 | 说明 |
|------|------|
| ~/.openclaw/ | OpenClaw 全部配置 |
| ~/.openclaw/workspace/memory/ | 记忆 + 传感器数据 |
| ~/.openclaw/workspace/scripts/ | 自定义脚本 |
| /usr/share/ollama/.ollama/models/ | Ollama 模型文件 |
| /backup/ | 备份目录 |
