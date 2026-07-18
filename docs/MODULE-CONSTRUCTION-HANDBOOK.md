# 功能模块建设手册 v1.0

> 系统建设知识库，用于新增、复刻、迁移功能模块时提供标准建设流程、设计边界、避坑经验。
> 定位：可复用的方法论和失败经验，非具体模块代码细节。

---

## 1. 模块建设总原则

### 1.1 先契约，后代码

```text
禁止：
需求 → 写脚本 → 出问题 → 补规则

正确：
需求 → 职责边界 → 数据契约 → 事件模型 → 实现 → 验证
```

### 1.2 模块必须回答五个问题

| 问题 | 说明 |
|------|------|
| 输入是什么 | 数据来源 |
| 输出是什么 | 产生什么结果 |
| 谁拥有它 | 责任归属 |
| 谁可以修改 | 写入边界 |
| 如何验证 | 正确性证明 |

### 1.3 数据权威设计

每次新增模块先确定：

```text
谁是真相源？
```

实例（彩票系统）：

```text
错误：
期号 → 所有预测 → 随机挑一个核对

正确：
Official Prediction Anchor → Checker
```

### 1.4 代码不承担业务规则解释

代码只负责：

- 执行契约
- 产生事件
- 返回结果

---

## 2. 标准建设流程

### Phase 1：需求定义

先定义：

```text
功能目标
输入
输出
异常情况
生命周期
```

### Phase 2：契约设计

建立 `XXX-CONTRACT.md`，至少包含：

```yaml
identity:
owner:
writer:
reader:
source:
validation:
```

实例（彩票系统 8 份契约）：

```
LOTTERY-CAPABILITY-CONTRACT.md
LOTTERY-PREDICTION-CONTRACT.md
LOTTERY-PREDICTION-STRATEGY-CONTRACT.md
LOTTERY-PREDICTION-ENGINE-CONTRACT.md
LOTTERY-PREDICTION-DIVERSITY-CONTRACT.md
LOTTERY-PREDICTION-COMBINATION-CONTRACT.md
LOTTERY-PREDICTION-ROLE-CONTRACT.md
LOTTERY-SOURCE-CONTRACT.md
LOTTERY-SOURCE-RETRY-CONTRACT.md
LOTTERY-STATISTICS-CONTRACT.md
LOTTERY-WORKER-DIRECTORY-CONTRACT.md
```

### Phase 3：数据权威设计

明确谁产生事实、谁消费事实。

### Phase 4：实现

代码只实现契约定义的逻辑。

### Phase 5：验证

每个模块必须有：

```text
正常路径测试
异常路径测试
恢复测试
重复执行测试
```

---

## 3. 模块类型模板

新增模块时复制此模板：

```markdown
# XXX 模块

## 目标

## 边界

负责：
-

不负责：
-

## 输入

来源：
格式：
权限：

## 输出

事件：
文件：
通知：

## 状态

状态机：

## 契约

## 验证方法

## 已知坑

## 后续扩展
```

---

## 4. 避坑知识库

### 4.1 Timer 模块

```text
错误：
修改 timer → daemon-reload → 认为完成

实际：
daemon-reload 不会自动恢复 enable 状态

标准流程：
daemon-reload
systemctl enable xxx.timer
systemctl restart xxx.timer
systemctl status xxx.timer
systemctl list-timers xxx.timer
```

排查链：

```text
1. systemctl list-unit-files xxx.timer — 是否存在
2. systemctl is-active xxx.timer — 是否 active
3. ls timers.target.wants/xxx.timer — 是否在调度队列
4. journalctl -u xxx.timer — 到点是否触发
5. journalctl -u xxx.service — service 是否执行
```

### 4.2 数据核验模块

```text
错误：按期号找预测（导致测试数据污染）

正确：期号 + 官方预测身份 + 发布状态
```

预测必须有身份标签：

```json
{
  "game": "SSQ",
  "issue": "2026082",
  "prediction_id": "pred-ssq-2026082-01",
  "purpose": "official",
  "status": "published"
}
```

checker 只核对 `purpose=official` 的预测。

### 4.3 日报/聚合模块

日报不判断业务，只聚合事件。

```text
错误：
日报自己判断：今天开什么彩票、哪个预测有效、是否核验完成

正确：
业务模块产生事件
日报只聚合事件
```

日报消费条件：

```text
开奖事件存在
核验事件已完成
当天彩种白名单通过
```

### 4.4 事件修改原则

```text
写入后不修改
错误数据不删除，由修正事件补充
历史推送不撤回
```

---

## 5. 模块生命周期管理

```text
设计 → 实验 → 验证 → 冻结 → 观察 → 升级
```

禁止：

```text
出现一次异常 → 马上增加规则
```

观察期至少跑过完整事件周期后再决定是否调整。

---

## 6. 复刻检查清单

复制一个模块时逐项确认：

```
□ 是否有契约文件
□ 是否定义数据源
□ 是否定义写入者
□ 是否有唯一身份
□ 是否有验证方法
□ 是否隔离测试数据
□ 是否有恢复路径
□ 是否有日志入口
□ 是否有停止条件
```

---

## 7. 文件归属

```text
ARCHITECTURE.md           ← 系统治理原则
MODULE-CONSTRUCTION-HANDBOOK.md  ← 模块建设方法（本文件）
memory/state/huo/XXX-CONTRACT.md ← 各模块领域规则
```

三份文档互相引用，不重复。

---

## 8. 已建设功能模块

---

### 8.1 彩票系统 (Lottery System)

| 项目 | 状态 |
|------|------|
| 当前版本 | v1.1 |
| 契约 | 11 份 ✅ 冻结 |
| Timer | 8 个 ✅ 运行中 |
| 生产闭环 | 100% ✅ |
| 观察期 | ⏳ 进行中 |

#### 边界

- 负责：开奖数据采集 → 验证 → 事件存储 → 统计 → 预测 → 核对 → 通知
- 不负责：预测中奖概率、用户投注、资金管理、选号建议

#### 输入

- 开奖源：500.com (Chrome headless) / cwl.gov.cn (JSON API) / mock (测试)
- 配置：`memory/state/huo/LOTTERY-*.md` (11份契约)

#### 输出

- 事件文件：`memory/events/lottery/{ssq,dlt,kl8}.jsonl`
- 预测缓存：`memory/cache/lottery/predictions/`
- 核对结果：`memory/cache/lottery/check/`
- 统计数据：`memory/cache/lottery/statistics/`
- 通知：Telegram (预测/核对/日报)

#### 子模块清单

| 子模块 | 状态 | 说明 |
|--------|------|------|
| Source Adapter | ✅ 完成 | 500m primary, cwl fallback, mock test |
| Issue Validator | ✅ 完成 | 三重校验(格式/时间/连续性) |
| Cross-Source Verify | ✅ 完成 | SSQ 双源交叉验证(500m + cwl) |
| Event Append + Provenance | ✅ 完成 | source + validation 元数据 |
| Retry Controller | ✅ 完成 | 12×1h, 失败告警 |
| Statistics Engine | ✅ 完成 | 频率/奇偶/区间/和值 |
| Prediction Engine | ✅ v3 冻结 | 4策略+熵扰动+反常识→70候选→角色选择→Top5 |
| Checker | ✅ 完成 | 预测 vs 开奖→命中统计 |
| Daily Report | ✅ 完成 | 22:35唯一出口 |
| Source Health | 📝 待完善 | source_health.jsonl |
| 策略效果观测 | ⏳ 待建设 | 策略贡献度/候选多样性/命中分布 |

#### 避坑记录

- Timer daemon-reload 后必须显式 reenable（见 4.1）
- 预测必须有 purpose 身份隔离，checker 只认 official（见 4.2）
- 日报不判断业务逻辑，只聚合事件（见 4.3）

#### 关键路径

```text
脚本:    .local/bin/lottery-worker.sh
引擎:    .local/bin/lottery/predict_engine.sh
推送:    hooks/oek-ci-gate/push-notify.mjs
Timer:   ~/.config/systemd/user/{ssq,dlt,kl8}-{predict,check}.timer
         ~/.config/systemd/user/lottery-{fetch,daily}.timer
         ~/.config/systemd/user/source-retry.timer
```

---

### 8.2 Ollama 模型服务

| 项目 | 状态 |
|------|------|
| 当前版本 | v0.32.1 |
| 生产运行 | ✅ 运行中 |

#### 边界

- 负责：本地大模型推理服务
- 不负责：外部 API 代理、负载均衡

#### 配置

```ini
CPUQuota=350%
Nice=10
MemoryHigh=4G
```

#### 已安装模型

| 模型 | 用途 | 状态 |
|------|------|------|
| qwen2.5:3b | OpenClaw fallback | ✅ |
| qwen3:4b | 评估基准 | ✅（已替换为 2.5:3b） |

#### 待完善

- [ ] 模型版本管理策略
- [ ] 自动 fallback 切换验证

---

### 8.3 系统传感器层

| 项目 | 状态 |
|------|------|
| 采集频率 | 每小时 (crontab) |
| 生产运行 | ✅ 运行中 |

#### 传感器清单

| 传感器 | 输出文件 | 说明 |
|--------|---------|------|
| system-health | `memory/events/system-health.jsonl` | CPU/内存/磁盘/负载 |
| service-state | `memory/events/service-state.jsonl` | 关键服务状态 |
| memory-snapshot | `memory/events/memory-snapshot.jsonl` | 内存快照 |
| ollama-eval | `memory/events/ollama-eval.jsonl` | 模型评估 |

#### 触发方式

```text
crontab:
0 * * * * collect-sensors.sh && eval-local.sh
```

---

### 8.4 备份体系

| 项目 | 状态 |
|------|------|
| 执行时间 | 每日 03:00 (crontab) |
| 保留份数 | 7 |
| 生产运行 | ✅ 运行中 |

#### 边界

- 负责：全量备份 + 完整性审计 + 恢复入口
- 不负责：增量备份、异地容灾

#### 脚本

| 脚本 | 说明 |
|------|------|
| `scripts/backup-full.sh` | 全量备份 (tar.zst, 169文件) |
| `scripts/audit-backup.sh` | 27项关键路径检查 |

#### 输出

```text
/backup/openclaw-full-*.tar.zst   (保留7份)
/backup/README.md                 恢复入口
/backup/IDENTITY.md
/backup/MEMORY-GUIDE.md
/backup/SYSTEM-SNAPSHOT.md
```

#### 待完善

- [ ] 恢复演练流程
- [ ] 备份完整性自动告警

---

### 8.5 Push 通知体系

| 项目 | 状态 |
|------|------|
| 统一出口 | ✅ push-gate.mjs |
| 生产运行 | ✅ 运行中 |

#### 边界

- 负责：所有 External Worker 的统一通知出口
- 不负责：Token 管理、通知去重

#### 通道

| 通道 | 说明 | 状态 |
|------|------|------|
| Telegram Bot | `pushToTelegram()` | ✅ |
| GitHub Gist | `pushToGist()` | ✅ |

#### 安全策略

- Token 存储在独立 `.secrets/` 目录
- Worker 脚本零硬编码 token
- 只通过 `push-notify.mjs` CLI 调用

---

### 8.6 Token 观测

| 项目 | 状态 |
|------|------|
| 采集频率 | 每小时 (crontab) |
| 生产运行 | ✅ 运行中 |

#### 输出

```text
~/.openclaw/token_observe.jsonl
```

#### 指标

```text
session_count
total_tokens_k
transcript_bytes
trajectory_bytes
compaction/prune 事件数
```

---

### 8.7 传感器日报

| 项目 | 状态 |
|------|------|
| 触发时间 | 09:00 / 21:00 (crontab) |
| 生产运行 | ✅ 运行中 |

#### 输出

```text
脚本: scripts/push-daily-report.sh
推送: push-notify.mjs → Telegram
内容: 系统健康 / 服务状态 / Ollama 评估摘要
```

---

### 8.8 Event Execution Kernel

| 项目 | 状态 |
|------|------|
| 类型 | A 类核心治理 |
| 手册状态 | ✅ 文档完成，运行时验证中 |

#### 模块定位

系统事实源。所有业务模块产生的事件最终存储于此。

#### 边界

```text
负责：
- 事件的 append-only 写入
- 事件溯源（Event Sourcing）
- replay / recovery
- 事件 schema 定义

不负责：
- 事件业务语义（由各模块契约定义）
- 事件消费顺序（消费者自行处理）
```

#### 核心能力

| 能力 | 说明 | 状态 |
|------|------|------|
| Append | 事件追加到 events/ 目录，禁止修改已写入事件 | ✅ |
| Execute | 事件触发后的副作用执行 | ✅ |
| Replay | 通过事件重放恢复系统状态 | ⏳ 待完善 |
| Recover | 故障后通过事件还原 | ⏳ 待完善 |

#### 写入原则

```text
写入后不修改
错误数据不删除，由修正事件补充
事件是事实源，不是缓存
```

当前实现的 appender（lottery-worker.sh validator 部分）：

```python
event = {
    'event_id': 'lottery-ssq-2026081',
    'type': 'LOTTERY_DRAW',
    'game': 'SSQ',
    'source': {'primary': '500m', 'verified_by': 'cwl'},
    'validation': {'issue_check': 'pass', 'number_check': 'pass'},
    'payload': { ... },
    'timestamp': '...'
}
```

#### 验证方法

- Replay-v2 oracle
- fingerprint 校验
- DAG validation

#### 依赖

```text
依赖: none（根模块）
被依赖: 所有业务模块
```

#### 已知坑

- 事件格式变更需要版本化迁移，不能直接修改历史
- 跨模块事件关联需要统一的 event_id 生成规则
- 当前没有全局事件索引，按 game/file 分文件存储

---

### 8.9 Runtime Boundary

| 项目 | 状态 |
|------|------|
| 类型 | A 类核心治理 |
| 手册状态 | ⏳ 待补充运行时验证细节 |

#### 模块定位

定义 OpenClaw 运行时核心与外部 Worker 的边界。

#### 边界

```text
Runtime（openclaw-gateway.service）:
负责：
- 核心执行引擎
- 插件加载
- Session 管理
- 工具调度

禁止：
- 外部业务生命周期侵入
- LLM 直接改变运行时状态

External Worker（systemd timer / oneshot）:
负责：
- 周期任务（彩票采集、传感器、备份）
- 报表生成
- 消息推送
- 数据采集

禁止：
- 注册 HTTP 路由
- 修改 Gateway 运行时
```

#### 扩展边界规则（摘自 TOOLS.md）

```text
Runtime 核心不动 — Gateway/Plugin/Hook/Agent 不改源码
外部工作走标准模式 — systemd timer + oneshot worker，不长期 daemon
通知统一出口 — 所有推送走 push-gate.mjs，不能各自持有 token
Secrets 隔离 — 独立 .secrets/ 目录，脚本零硬编码
```

#### 验证

- 是否存在 NODE_OPTIONS 注入
- 是否存在外部 Worker 对 Runtime 的生命周期污染

---

### 8.10 Memory Governance

| 项目 | 状态 |
|------|------|
| 类型 | A 类核心治理 |
| 手册状态 | ✅ 契约已冻结，文档已完成 |

#### 模块定位

定义 Memory 的命名空间、所有权、写入边界和 metadata。

#### 目录结构

```text
memory/
├── state/      ← 系统状态 / 契约 / 架构文档（所有权: Runtime/Agent）
├── events/     ← 事件日志（所有权: Runtime/Agent，append-only）
├── facts/      ← 事实数据（所有权: Human/Confirmed Agent）
├── preferences/ ← 偏好配置（所有权: User）
├── knowledge/  ← 知识库（所有权: Importer/Human）
└── cache/      ← 缓存（无所有权保证）
```

#### 核心原则

```text
目录 = 分类
Ownership = 权力边界
目录说明"这是什么"
Contract 说明"谁能改、怎么改、能否回滚"
```

#### 写入边界（Writer Classification）

| Class | ID | 允许写入 |
|-------|-----|---------|
| Runtime Writer | runtime | state, events |
| Generated Memory | generated | 从 session 提取 |
| Worker Writer | worker | cache |
| External Event Producer | external-event-producer | 指定 events/ 子域 |
| Human Writer | human | facts, preferences |
| Agent Direct Writer | agent-direct | ❌ 禁止 |

#### 契约

```text
memory/state/huo/MEMORY-OWNERSHIP-CONTRACT.md
memory/state/huo/MEMORY-WRITER-BOUNDARY.md
```

---

### 8.11 Plugin Capability Governance

| 项目 | 状态 |
|------|------|
| 类型 | A 类核心治理 |
| 手册状态 | ✅ 契约已冻结，文档已完成 |

#### 模块定位

定义插件能力的声明、注册、验证和权限分级。

#### 能力链

```text
Capability 声明 → Registry 注册 → Contract 约束 → Enforcement 执行
```

#### Capability 命名空间

| Category | 示例 | 风险等级 |
|----------|------|----------|
| runtime | tool.register, hook.subscribe, http.route | high |
| memory | memory.read, memory.provider | medium |
| event | event.subscribe, event.emit, event.append | medium |
| io | web.fetch, web.search | low |
| notification | channel.register | medium |
| provider | model.provider, speech.provider | medium |
| security | audit.collector, tool.policy | high |

#### 当前状态

```text
Capability Registry: 已完成（CAPABILITY-REGISTRY.md）
Plugin Contract: 已完成（PLUGIN-CAPABILITY-CONTRACT.md）
Enforcement: ⏳ Phase 3.4（运行时权限校验）

当前只有二元权限：插件启用/禁用（allowlist）
无细粒度"此插件可 registerTool 但不可 registerChannel"机制
```

#### 契约

```text
memory/state/huo/PLUGIN-CAPABILITY-CONTRACT.md
memory/state/huo/CAPABILITY-REGISTRY.md
```

---

### 8.12 Scheduler Management

| 项目 | 状态 |
|------|------|
| 类型 | B 类运行维护 |
| 手册状态 | ✅ 完成 |

#### 边界

- 负责：systemd timer 生命周期管理、排查、维护
- 不负责：定时任务业务逻辑

#### Timer 清单

参见 `docs/MODULE-INDEX.md` C 类。

#### 避坑（务必阅读）

```text
修改 timer 文件后：
1. daemon-reload
2. systemctl enable xxx.timer    ← 必须，reload 会丢失 enable
3. systemctl restart xxx.timer
4. systemctl status xxx.timer
5. systemctl list-timers xxx.timer  ← 确认出现在排班中
```

排查链见 4.1 节。

---

### 8.13 D 类工具

| 工具 | 归属 | 状态 |
|------|------|------|
| audit.sh / exec_audit.sh | Plugin Governance | Archived → archive/2026-07-10-pre-governance/ |
| freeze_gate.sh / freeze_verify.sh | Plugin Governance（架构冻结辅助） | Archived |
| shadow.sh / snapshot.sh / replay.sh | Event Kernel | Archived |
| config-health.sh | OpenClaw Runtime | 已确认 |
| proof.sh | Event Kernel（Evidence Provenance） | Archived |
| observe.sh / stats.sh / health.sh | D类 Observability辅助工具 | 保留D类 |
| explain.sh / resolve.sh | D类排查工具 | Archived |
| test_audit.sh / test_authority.sh | 测试脚本 | Archived |
| pre-backup-sync.sh | Backup Module | 已确认 |

分类原则：按能力归属（治理边界），不按文件名。不因归属某领域而升级模块。
