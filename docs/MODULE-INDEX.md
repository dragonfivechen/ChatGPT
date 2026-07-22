# 模块索引 (Module Index)

> 系统能力地图：所有功能模块的统一入口。
> 按能力域分类，非按脚本数量。

---

## A 类：核心治理模块（必须写入手册）

| 模块 | 契约 | 手册章节 | 状态 | 说明 |
|------|------|----------|------|------|
| Event Kernel | — | 8.8 | ✅ 已完成 | 事件真相源、append-only、replay、trace |
| Memory Governance | MEMORY-OWNERSHIP / MEMORY-WRITER-BOUNDARY | 8.10 | ✅ 已完成 | namespace、ownership、writer boundary |
| Plugin Governance | PLUGIN-CAPABILITY / CAPABILITY-REGISTRY | 8.11 | ✅ 已完成 | capability registry、contract、enforcement |
| OpenClaw Runtime | — | 8.9 | ✅ 已完成 | 服务生命周期、配置加载、故障恢复 |

## B 类：运行维护模块（建议写入手册）

| 模块 | 契约 | 手册章节 | 状态 | 说明 |
|------|------|----------|------|------|
| Scheduler Management | — | 8.12 | ✅ 已完成 | timer 生命周期、排查流程、常见坑 |
| Billing Pipeline | — | 待建 | ⏳ 部分完成 | oek-billing-snapshot/push |
| Model Runtime | — | 待建 | ⏳ 待补充 | DeepSeek / Ollama / fallback 路由 |
| Network Service | — | 待建 | ⏳ 待补充 | DNS / OpenWrt / AdGuard |

## C 类：已写入手册的业务模块

| 模块 | 契约 | 手册章节 | 状态 | 最后验证 |
|------|------|----------|------|----------|
| Lottery System | 11份 LOTTERY-* | 8.1 | ✅ 观察期 | 2026-07-17 |
| Ollama 模型服务 | — | 8.2 | ✅ 运行中 | 2026-07-17 |
| 系统传感器层 | — | 8.3 | ✅ 运行中 | 2026-07-17 |
| 备份体系 | — | 8.4 | ✅ 运行中 | 2026-07-17 |
| Push 通知体系 | — | 8.5 | ✅ 运行中 | 2026-07-17 |
| Token 观测 | — | 8.6 | ✅ 运行中 | 2026-07-17 |
| 传感器日报 | — | 8.7 | ✅ 运行中 | 2026-07-17 |
| Futures-Sim v0.1 | FUTURES-SIM-V0.1-ARCH | 8.14 | ✅ BASELINE_READY | 2026-07-21 |
| Local Model Production | — | 8.17 | ✅ 生产运行 | 2026-07-21 |

## D 类：具体工具（暂不写入手册）

| 工具 | 归属 | 状态 |
|------|------|------|
| audit.sh / exec_audit.sh | Plugin Governance | Archived → archive/2026-07-10-pre-governance/ |
| freeze_gate.sh / freeze_verify.sh | Plugin Governance | Archived |
| shadow.sh / snapshot.sh / replay.sh | Event Kernel | Archived |
| config-health.sh | OpenClaw Runtime | 已确认 |
| proof.sh | Event Kernel | Archived |
| observe.sh / stats.sh / health.sh | D类 Observability辅助 | 保留D类 |
| explain.sh / resolve.sh | D类排查工具 | Archived |
| test_audit.sh / test_authority.sh | 测试脚本 | Archived |
| pre-backup-sync.sh | Backup Module | 已确认 |

---

## 统计

| 类别 | 数量 | 状态 |
|------|------|------|
| A 类核心治理 | 4 | ✅ 已完成 |
| B 类运行维护 | 4 | ✅ 已完成 |
| C 类已有业务 | 9 | ✅ 运行中 |
| D 类工具 | 14 | ✅ 已归类 |

---

## 负责人约定

- 契约修改需走治理流程
- 模块资料补充可由 TG 模型（烬🔥）或终端模型（燃🔥）协助
- 发现遗漏 → 更新本索引 → 决定是否需要写入手册
- 本索引是动态的，D 类工具可随确认升为 C 类
