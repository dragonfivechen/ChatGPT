# 功能模块建设手册 v1.1

> 系统建设知识库，用于新增、复刻、迁移功能模块时提供标准建设流程、设计边界、避坑经验。
> 定位：可复用的方法论和失败经验，非具体模块代码细节。
> **最后更新：** 2026-07-22

---

## 1. 模块建设总原则

### 1.1 先契约，后代码

```text
禁止：
需求 → 写脚本 → 出问题 → 补规则

正确：
需求 → 职责边界 → 数据契约 → 事件模型 → 实现 → 验证
```

### 1.2 契约等级体系

新建模块前，确认契约层级归属：

```
M0  META-CONTRACT         元治理级 — 新契约分类判定规则
L0  FREEZE-CONTRACT       系统仲裁级 — 冻结/修复/扩展判定
L1  FUNCTION-MODULE-BASELINE  基线治理级 — 14 项验收维度
L2  Module Adapter            模块适配级 — 模块专属契约
L3  Implementation Alignment  建设执行级 — 实现对齐约束
L4  Operational Evidence      运行证据级 — 观测数据
```

- 新模块契约不可自行声明等级，需经 META-CONTRACT 六问（Q1-Q6）+ 权限影响（Q7）分类
- 等级不可越权，L2 不能自称 L1
- 契约必须注册到 CONTRACT-REGISTRY

### 1.3 模块必须回答五个问题

| 问题 | 说明 |
|------|------|
| 输入是什么 | 数据来源 |
| 输出是什么 | 产生什么结果 |
| 谁拥有它 | 责任归属 |
| 谁可以修改 | 写入边界 |
| 如何验证 | 正确性证明 |

### 1.4 数据权威设计

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

### 1.5 代码不承担业务规则解释

代码只负责：

- 执行契约
- 产生事件
- 返回结果

---

## 2. 标准建设流程

### Phase 0：契约分类（新增）

新模块需求出现后，先走 META-CONTRACT 判定流程：

```text
Q1 它定义行为规则吗？
Q2 它产生/消费事实？
Q3 它约束运行时？
Q4 它是治理还是建设？
Q5 它归属已有模块还是新模块？
Q6 它需要冻结吗？
   ↓
Q7 权限影响（A0-A4）
   ↓
等级生成 → Registry 登记
```

- 判定结果决定这属于治理契约还是建设任务
- 建设任务才进入 Phase 1-5

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

遵循 `CONTRACT-DECLARATION-SCHEMA.md` v1.1（含 verification + binding + enforcement 块）。

实例（彩票系统 11 份契约）：

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

完成后建议走 FUNCTION-MODULE-BASELINE-CHECK-CONTRACT 14 项验收。

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
设计 → 实验 → 验证 → 冻结 → 观察 → 维护/升级
```

经过 Phase 6/7 后，该链路进一步扩展为治理闭环：

```text
发现 → 证据 → 决策 → 变更 → 维护
```

- **发现：** 审计/观察层检测到偏差
- **证据：** `EVIDENCE-CONTRACT` 格式化记录
- **决策：** `DECISION-CONTRACT` 判定是否需要变更
- **变更：** `CHANGE-CONTRACT` 执行变更并审计
- **维护：** 回归观察

禁止：

```text
出现一次异常 → 马上增加规则
发现与修复直接连接（跳过证据和决策）
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

> 当前系统共有 **9 个功能模块**（A类4 + B类2 + C类2 + 新增1），**MODULE-INDEX.md** 维护完整清单。
> 以下为写入手册的模块详情。

---

### 8.1 彩票系统 (Lottery System)

| 项目 | 状态 |
|------|------|
| 当前版本 | v1.1 |
| 契约 | 11 份 ✅ 冻结 |
| Timer | 8 个 ✅ 运行中 |
| 预测引擎 | v3 ✅ FROZEN |
| 生产闭环 | 100% ✅ |
| 观察期 | ⏳ 持续（加入策略效果观测待建设） |

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
| 手册状态 | ✅ 已冻结 |
| Phase 6 | ✅ COMPLETE（Runtime Intelligence Layer v1）|

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
| audit.sh / exec_audit.sh | Plugin Governance | Archived |
| freeze_gate.sh / freeze_verify.sh | Plugin Governance | Archived |
| shadow.sh / snapshot.sh / replay.sh | Event Kernel | Archived |
| config-health.sh | OpenClaw Runtime | 已确认 |
| proof.sh | Event Kernel | Archived |
| observe.sh / stats.sh / health.sh | Observability 辅助 | 保留D类 |
| explain.sh / resolve.sh | 排查工具 | Archived |
| test_audit.sh / test_authority.sh | 测试脚本 | Archived |
| pre-backup-sync.sh | Backup Module | 已确认 |

分类原则：按能力归属（治理边界），不按文件名。不因归属某领域而升级模块。

---

### 8.14 Futures-Sim v0.1（期货模拟系统）

| 项目 | 状态 |
|------|------|
| 类型 | C 类业务模块 |
| 基线 | 🟢 BASELINE_READY |
| Phase 1-5 | ✅ 全线通过并冻结 |
| 合约 | 15 个品种（螺纹钢/铁矿石/沪铜/原油等） |

#### 边界

- 负责：期货合约建模、多空双向持仓、保证金/盯市结算/强平、模拟/历史双行情源、策略回测
- 不负责：实盘交易、行情采集（模拟生成或 CSV 导入）

#### 关键决策

- 与 stock-sim 镜像设计但不复用代码（期货=保证金+双向+T+0+盯市结算）
- 事件契约 100% 兼容 FUTURES_QUOTE
- AkShare 历史数据集 6 品种 × 967 bar（2022-2026）

#### 验证记录

```
Breakout 模拟 +179.83% → 真实 -95.93%
→ 确认模拟行情偏置严重，Phase 6 需分析差异
```

#### 文件结构

```
market_futures/
├── futures_contracts.json, collector.py       ← Phase 1
├── position.py, account.py, simulator.py     ← Phase 2
├── strategies/ (MA, breakout, rsi)            ← Phase 3
├── run_strategy.py                            ← Phase 4
├── reports/performance.py                     ← Phase 4
├── replay/loader.py, converter.py             ← Phase 5
├── data/historical/                           ← Phase 5.1
└── PHASE_STATUS.json                          ← FROZEN
```

#### 文档

- 架构：`memory/state/huo/FUTURES-SIM-V0.1-ARCH.md`
- 验证差异：`FUTURES-SIM-VALIDATION-NOTE.md`

---

### 8.15 Trading Runtime v0.5

| 项目 | 状态 |
|------|------|
| 类型 | B 类运行维护 |
| 基线合规 | 🟢 PASS |
| 文档 | ✅ 独立架构文档已闭环 |

#### 边界

- 负责：交易运行时环境、策略调度、状态管理
- 不负责：行情源、交易执行（由 collector/simulator 分别负责）

#### 基线审计结果

```
Extension Boundary     🟢 PASS
Memory Namespace       🟢 PASS
Terminal Authority     🟢 PASS
Module Ownership       🟢 PASS
Freeze Integrity       🟢 PASS
Overall:               GREEN
```

#### 文档

- 架构：`memory/state/huo/TRADING-RUNTIME-V0.5-ARCH.md`

---

### 8.16 TG Agent Behavior Diagnostics（离线观察层）

| 项目 | 状态 |
|------|------|
| 类型 | D 类| 离线观察工具（非系统运行时） |
| 工具 | 3 个 Python 脚本 |

#### 边界

- 负责：TG 交互历史的离线分析、行为模式检测、异常识别
- 不负责：实时监控、自动修复、运行时干预

#### 工具清单

| 工具 | 功能 |
|:-----|:------|
| `tools/tg_transcript_reader.py` | session 抽取 |
| `tools/tg_behavior_analyzer.py` | 6 类检测（响应稳定性/推理边界/用户反馈/意图满足/回归） |
| `tools/tg_maintenance_queue.py` | findings → queue |

#### 隔离规则（TG-BEHAVIOR-DATA-CONTRACT）

- TG transcript → Memory → 终端模型行为融合 🚫 **永久阻断**
- 分析结果不写入 memory/rules/SOUL
- 观察层发现 → Human Review → 决定是否治理

#### 契约

- `memory/state/huo/TG-BEHAVIOR-DATA-CONTRACT.md` — 数据隔离规则
- `memory/state/huo/DIAGNOSTICS-BEHAVIOR-LAYER.md` — 工作笔记

---

### 8.17 Local Model Production Trial v1.0

| 项目 | 状态 |
|------|------|
| 类型 | C 类业务模块 |
| 生产运行 | ✅ active（scoped） |
| 总调用 | 232 条生产数据，0 失败 |

#### 架构定位

本地模型不作为云端降级替代。通过 `local-task-worker.sh` 处理 8 类确定型生产任务。
复杂推理/主任务 → DeepSeek；确定型任务 → Ollama qwen2.5:3b。

#### 任务清单

---

### 8.18 Asset Observation Layer

| 项目 | 状态 |
|------|------|
| 类型 | B 类运行维护 |
| 扫描器 | `scripts/asset_observer.py` |
| 配置 | `config/asset-roots.json` |
| 快照 | ASSET-SNAPSHOT-002 (247 assets) |

#### 边界

- 负责：资产存在性发现、分类统计（7 类）、一致性检查、漂移记录
- 不负责：自动修复、资产生命周期管理、权限控制

#### 调度

| 级别 | 周期 | 范围 |
|:-----|:----:|:-----|
| Light | 1d | 文件/路径/服务变化 |
| Medium | 3d | 模块映射校验 |
| Full | 7d | 全量扫描+分类+快照 |

#### 依赖

- `config/asset-roots.json` — 统一扫描根路径
- systemd timers: asset-observer-{light,medium,full}

#### 文档

- `docs/SYSTEM-ASSET-OBSERVATION.md`
- `docs/SYSTEM-ASSET-SEMANTIC-INDEX.md`
- `docs/SYSTEM-ASSET-MODULE-FILE-MAPPING.md`
- `docs/SYSTEM-ASSET-SCAN-SCHEDULE.md`
- `docs/ASSET-QUERY-GUIDE.md`

---

### 8.19 Capability Observation Layer

| 项目 | 状态 |
|------|------|
| 类型 | B 类运行维护 |
| 扫描器 | `scripts/capability_observer.py` |
| 快照 | CAP-SNAPSHOT-001 (24 capabilities, 6 domains) |

#### 边界

- 负责：能力声明→证据→覆盖完整度观察
- 不负责：自动补齐能力、自动创建模块、自动规划路线

#### 能力状态

| 状态 | 含义 |
|:-----|:------|
| available | 所有证据路径存在 |
| partial | 部分证据存在 |
| declared_only | 有声明无实现 |
| missing | 基线要求但无实现 |
| unknown | 无法判断 |

#### 调度

- 周期：每日 (`capability-observer.timer`)

#### 依赖

- CAPABILITY-REGISTRY.md、领域 Contract
- Semantic Index 模块定义

#### 文档

- `docs/SYSTEM-CAPABILITY-OBSERVATION.md`

---

### 8.20 Baseline Observation Layer

| 项目 | 状态 |
|------|------|
| 类型 | B 类运行维护 |
| 扫描器 | `scripts/baseline_observer.py` |
| 快照 | BASELINE-SNAPSHOT-001 (0 drifts) |

#### 边界

- 负责：冻结契约→资产基线→能力基线→模块基线的漂移检测
- 不负责：修改基线、自动补齐、审批变更

#### 观察维度

| 维度 | 检查项 |
|:-----|:--------|
| Contract drift | frozen contract 文件是否丢失 |
| Asset drift | unknown > 30% 触发 classification_drift |
| Capability drift | available < total 触发 capability_drift |
| Module drift | FROZEN module 是否被破坏 |

#### 调度

- 周期：每日 (`baseline-observer.timer`)

#### 依赖

- CONTRACT-REGISTRY.md
- ASSET-SNAPSHOT、CAP-SNAPSHOT
- PHASE_STATUS.json

#### 文档

- `docs/SYSTEM-BASELINE-OBSERVATION.md`

| 任务 | 状态 |
|:---|:---:|
| system_status_brief | ✅ |
| log_summary | ✅ |
| config_explain | ✅ |
| event_classify | ⚠️ 38% 逐行分类（prompt 歧义，需收敛格式） |
| json_validate | ✅ 修复后观察中 |
| event_tagging | ✅ 修复后观察中 |
| change_summary | ✅ 修复后观察中 |
| report_format | ✅ 修复后观察中 |

#### 避坑

引号 Bug（2026-07-21）：`local-task-worker.sh` 中 4 个任务生成函数 echo JSON 时 key 双引号未转义，导致 44 条空类型记录混入生产数据。修复后重新进入观察期。

#### 文档

- 生产证据：`ollama-production.jsonl`
- Worker：`local-task-worker.sh`

---

## 9. 治理框架变更参考

> 本节记录手册写完后发生的治理层重大变更，供后续修订时参考。

### 9.1 Phase 6 — Runtime Intelligence Layer ✅ COMPLETE

- Event Integration (§6.3.2)
- Runtime Integration (§6.3.3)
- Schema Design (§6.4.1)
- Runtime Enforcement (§6.4.2 + §6.4.3)

### 9.2 Phase 7 — Boundary Integrity ✅ FROZEN

- 7.1 Audit Contract → 7.2 Boundary Matrix → 7.3 Gap Closure → 7.4 Verification → 7.5 Integrity Freeze
- 15 bypass paths 全部治理分类完成
- 进入 Observe/Evidence Accumulation 周期

### 9.3 Phase 8 — Runtime Observation Layer 🔒 FROZEN

- Integrity Analyzer（10 项确定性检查 + 阈值 config）
- Capability Contract（6 能力契约替代业务事件模型）
- Maintenance Queue（Writer + Viewer + 日报集成）
- 输出：`integrity_observe.jsonl`（append-only）

### 9.4 契约体系（M0-L4）

契约从本手册 v1.0 的 11 份 Lottery 契约膨胀至 27 份。

| 等级 | 数量 | 代表 |
|------|:----:|------|
| M0 META-CONTRACT | 1 | 元治理契约 |
| L0 FREEZE-CONTRACT | 1 | 系统仲裁 |
| L1 基线治理 | 9 | EVIDENCE/DECISION/CHANGE/BASELINE-CHECK 等 |
| L2 模块适配 | 11 | LOTTERY-* / TG-* / PLUGIN / MEMORY 等 |
| L3 建设执行 | 5 | 实现对齐/执行契约 |
| L4 运行证据 | 0 | （暂无可注册实体） |

完整列表见 `memory/state/huo/CONTRACT-REGISTRY.md`

### 9.5 治理链闭环

```
发现  →  证据  →  决策  →  变更  →  维护
✅      ✅       ✅       ✅       ⚠️
```

- 发现：事件源/审计/观察层
- 证据：`EVIDENCE-CONTRACT` v1.0
- 决策：`DECISION-CONTRACT` v1.0
- 变更：`CHANGE-CONTRACT` v1.0
- 维护：Phase 8 能力已有，真实违反案例后考虑契约化

**当前状态：关闭扩张周期，进入 Observe 阶段。**

### 9.6 Memory 命名空间

```
memory/
├── state/     ← 系统状态 / 契约 / 架构文档（ownership controlled）
├── events/    ← 事件日志（身份隔离 / append-only）
├── data/      ← 原始业务数据（无身份归属）
├── knowledge/ ← 知识库（可共享）
├── facts/     ← 事实数据
├── preferences/ ← 偏好配置
└── cache/     ← 缓存
```

详细的 Memory Governance 见 §8.10 及契约文件。

### 9.7 MODULE-INDEX.md

系统能力地图（A/B/C/D 四类），作为本手册的轻量入口：

- A 类核心治理（4 个）→ 本手册 §8.8-8.11
- B 类运行维护（7 个）→ 本手册 §8.12 + §8.15 + §8.18 + §8.19 + §8.20
- C 类业务模块 → 本手册 §8.1-8.7 + §8.14 + §8.17 + §8.21（待分配）
- D 类工具 → 本手册 §8.13

详见 `docs/MODULE-INDEX.md`
