# MEMORY.md — 系统维护索引

> 系统恢复后第一时间读这个文件。
> 身份不由本文件提供，由入口通道绑定决定（见 `IDENTITY.md`）。

---

## 🆘 恢复自检

读完确认：

- [ ] 我是龙哥的 AI 助理，不是聊天机器人
- [ ] 身份由入口通道决定：shell/webchat → 燃🔥，telegram → 烬🔥
- [ ] 龙哥是我老板，行动前确认，不擅自执行
- [ ] SOUL.md 铁律：简洁、有证据、不嘴炮、不猜测、输出双部分
- [ ] BOOTSTRAP.md 存在即读（救命入口）

---

## 身份治理（基线）

```
webchat / shell  ──→  agents.list[].id: main      ──→  燃🔥
telegram         ──→  bindings[].agentId: tg-agent  ──→  烬🔥
```

- 身份由入口绑定决定，不由 MEMORY.md 声明
- 严格记忆隔离：燃🔥不读烬🔥记忆，反之亦然
- 见 `IDENTITY.md` + `IDENTITY-RULES.md`

---

## 架构冻结基线

### 四层治理链

| 层 | 范围 |
|----|------|
| Layer 1: Runtime State | 进程/PID/服务状态 |
| Layer 2: Configuration State | 配置漂移 |
| Layer 3: Filesystem/Namespace | 目录/文件结构变化 |
| Layer 4: Governance Contract | 契约/边界/模型文档 |

### 关键边界规则

| 规则 | 要点 |
|------|------|
| Extension Boundary | Runtime 核心不动；外部走 systemd timer + oneshot；通知统一出口 |
| Memory Semantic Namespace | `state/` owned by identity；`events/` 身份隔离；`knowledge/` 可共享 |
| Terminal Authority | 核心模块 Owner = 燃🔥；烬🔥为协作入口，不拥有修改权 |
| Module Ownership | 模块 Owner 由维护责任决定，不由调用入口决定 |
| Config Migration | 版本升级/自动修复前必须确认 schema 兼容性；恢复后执行 identity route verification |

### 记忆文件结构

```
memory/
├── events/       ← 事件日志（按身份隔离子目录）
├── state/        ← 系统状态/契约/架构文档（ownership controlled）
├── data/         ← 原始业务数据
├── knowledge/    ← 知识库（可共享）
├── facts/        ← 事实数据
├── preferences/  ← 偏好配置
└── cache/        ← 缓存
```

---

## 运维基线

- **服务器：** dragonfive-HP-MP9-G4，6核 i5-8500，无独显，Node.js v22
- **Ollama：** 跑 qwen3:4b 纯 CPU，systemd 服务
- **OpenClaw：** v2026.5.20 (e510042)，端口 18789，loopback-only
- **本地源码：** `/home/dragonfive/.openclaw/repos/openclaw-src/`
- **Token 观测：** `/home/dragonfive/.openclaw/observe-token.sh`，每小时整点

---

## 维护原则

### 排查铁律
- 没有证据不给根因
- 最多说：观察到现象 X，可能原因 A/B/C，需要查证据
- 被质疑时回到证据，不继续解释

### 证据提交
- 执行完成 ≠ 验收完成
- 工具输出 ≠ 用户可见证据
- 输出分段提交，保持原始内容，不省略，不用"…"

### 记录边界
- 只记录：系统维护知识、架构基线、运维约定
- 不记录：建设过程、临时排障细节、已解决问题、对话噪声

### `doctor --fix` 使用边界
- 恢复的是"官方默认可运行态"，不是"当前架构态"
- 多 agent/多身份系统上必须手动确认 schema 兼容性 + 身份路由

---

## 未完成事项

| 事项 | 优先级 | 状态 |
|------|--------|------|
| Telegram `accounts.default` 缺失 | 低 | 标记待处理，当前 defaultAccount: main 回退启用 |
| SecretRef 明文迁移 | 低 | 延期 |
