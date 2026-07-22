# System Asset Semantic Index v1.0

> 机器资产标识 ↔ 人类语义映射 ↔ 自然语言查询入口
>
> 不替代 Asset Observation，不替代 Contract Registry，不替代 Module Handbook。
> 状态只引用 Observation，不独立管理。

```text
Observation Layer
    |
    | 提供事实 (ASSET-SNAPSHOT-002)
    ↓
Semantic Index
    |
    | 提供映射
    ↓
Human Query / Natural Language
```

---

## 1. Domain Mapping (L0)

| Domain ID | Domain | Description | Modules |
|:----------|:-------|:------------|:--------|
| DOM-GOV | Governance | 治理体系：契约、冻结、基线、身份 | META-CONTRACT, FREEZE-CONTRACT, CONTRACT-REGISTRY, Phase 6/7/8 |
| DOM-CON | Construction | 建设层：手册、索引、蓝图、设计文档 | MODULE-CONSTRUCTION-HANDBOOK, MODULE-INDEX, ASSET-OBSERVATION |
| DOM-RUN | Runtime | 运行时：Gateway 服务、自愈、上下文 | self-healing/, runtime/, openclaw-gateway |
| DOM-LOT | Lottery | 彩票系统：采集→验证→预测→核对→日报 | lottery-worker, push-notification, lottery timers |
| DOM-TRD | Trading | 交易系统：期货模拟、交易运行时 | Futures-Sim, trading-runtime |
| DOM-MON | Monitoring | 监控与观察：传感器、Token、资产扫描 | asset-observer, sensors, token-metrics |
| DOM-MEM | Memory | 记忆系统：状态/事件/数据/知识 | MEMORY.md, memory/state, memory/events |
| DOM-INF | Infrastructure | 基础设施：备份、计费、调度 | backup, billing, crontab, systemd |
| DOM-IDN | Identity | 身份：燃🔥/烬🔥 身份隔离与权限 | IDENTITY.md, IDENTITY-RULES.md |

---

## 2. Module Mapping (L1)

### 2.1 Governance

```yaml
asset_id: GOV-MODULE-001
human:
  name: 元治理契约体系
  aliases:
    - 元契约
    - meta-contract
    - 契约治理
  keywords:
    - 契约
    - 治理
    - 分类
    - 仲裁
domain:
  - Governance
contains:
  - memory/state/huo/META-CONTRACT.md
  - memory/state/huo/CONTRACT-REGISTRY.md
  - memory/state/huo/CONTRACT-LEVEL-CLASSIFICATION.md
  - memory/state/huo/CONTRACT-DECLARATION-SCHEMA.md
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: GOV-MODULE-002
human:
  name: 冻结仲裁体系
  aliases:
    - 冻结契约
    - freeze-contract
    - 基线检查
  keywords:
    - 冻结
    - 基线
    - 验收
    - 仲裁
domain:
  - Governance
contains:
  - memory/state/huo/FREEZE-CONTRACT.md
  - memory/state/huo/FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md
  - memory/state/huo/BASELINE-COMPLETENESS-SUPPLEMENT.md
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: GOV-MODULE-003
human:
  name: 治理链闭环
  aliases:
    - 证据-决策-变更
    - governance chain
    - 证据契约
  keywords:
    - 证据
    - 决策
    - 变更
    - 审计
domain:
  - Governance
contains:
  - memory/state/huo/EVIDENCE-CONTRACT.md
  - memory/state/huo/DECISION-CONTRACT.md
  - memory/state/huo/CHANGE-CONTRACT.md
  - memory/state/huo/BYPASS-REGISTER-v1.0.md
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: GOV-MODULE-004
human:
  name: 身份治理体系
  aliases:
    - 身份契约
    - identity
    - 记忆隔离
  keywords:
    - 身份
    - 权限
    - 隔离
    - 入口绑定
domain:
  - Governance
contains:
  - IDENTITY.md
  - IDENTITY-CONTRACT.md
  - IDENTITY-RULES.md
  - Maintenance-Authority-Contract-v1.0.md
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: GOV-MODULE-005
human:
  name: 领域契约组（彩票）
  aliases:
    - lottery contracts
    - 彩票契约
  keywords:
    - 彩票
    - 契约
    - 领域规则
domain:
  - Governance
  - Lottery
contains:
  - memory/state/huo/LOTTERY-CAPABILITY-CONTRACT.md
  - memory/state/huo/LOTTERY-PREDICTION-CONTRACT.md
  - memory/state/huo/LOTTERY-SOURCE-CONTRACT.md
  - memory/state/huo/LOTTERY-STATISTICS-CONTRACT.md
  - memory/state/huo/LOTTERY-WORKER-DIRECTORY-CONTRACT.md
  - (plus 6 related LOTTERY-* contracts)
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: GOV-MODULE-006
human:
  name: 领域契约组（TG）
  aliases:
    - TG contracts
    - TG 契约
  keywords:
    - TG
    - 交互模型
    - 行为诊断
    - 数据隔离
domain:
  - Governance
contains:
  - memory/state/huo/TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT.md
  - memory/state/huo/TG-IMPLEMENTATION-ALIGNMENT-CONTRACT.md
  - memory/state/huo/TG-BEHAVIOR-DATA-CONTRACT.md
status_source: ASSET-SNAPSHOT-002
```

### 2.2 Construction

```yaml
asset_id: CON-MODULE-001
human:
  name: 模块建设手册
  aliases:
    - 建设手册
    - handbook
    - module handbook
  keywords:
    - 建设
    - 模块
    - 方法
    - 避坑
    - 流程
domain:
  - Construction
contains:
  - docs/MODULE-CONSTRUCTION-HANDBOOK.md
  - docs/MODULE-INDEX.md
  - memory/knowledge/MAINTENANCE-RUNBOOK-v1.0.md
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: CON-MODULE-002
human:
  name: 系统资产观察层
  aliases:
    - asset observation
    - 资产观察
    - 资产盘点
  keywords:
    - 观察
    - 资产
    - 快照
    - 分类
    - 漂移
domain:
  - Construction
  - Monitoring
contains:
  - docs/SYSTEM-ASSET-OBSERVATION.md
  - docs/SYSTEM-ASSET-SEMANTIC-INDEX.md
  - scripts/asset_observer.py
  - memory/data/system/asset-observation.jsonl
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: CON-MODULE-003
human:
  name: 架构蓝图
  aliases:
    - architecture blueprint
    - 架构设计
  keywords:
    - 架构
    - 设计
    - 蓝图
    - 扫描
domain:
  - Construction
contains:
  - memory/knowledge/ARCHITECTURE-BLUEPRINT-v1.md
  - memory/state/huo/ARCHITECTURE.md
  - memory/state/huo/SCAN-BLUEPRINT-v2.md
status_source: ASSET-SNAPSHOT-002
```

### 2.3 Runtime

```yaml
asset_id: RUN-MODULE-001
human:
  name: OpenClaw Gateway 运行时
  aliases:
    - Gateway
    - 核心引擎
    - openclaw-gateway
  keywords:
    - 运行时
    - 服务
    - 引擎
    - 核心
domain:
  - Runtime
contains:
  - openclaw-gateway.service (systemd)
  - ~/.openclaw/openclaw.json
  - ~/.openclaw/secrets.json
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: RUN-MODULE-002
human:
  name: 自愈系统
  aliases:
    - self-healing
    - 自愈观察器
    - 边界网关
  keywords:
    - 自愈
    - 观察
    - 边界
    - 配置审计
domain:
  - Runtime
contains:
  - self-healing/observer.py
  - self-healing/provider_observe.py
  - self-healing/boundary_gate.py
  - self-healing/config_audit.py
  - self-healing/modules.yaml
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: RUN-MODULE-003
human:
  name: 运行时上下文
  aliases:
    - context provider
    - 上下文注入
  keywords:
    - 上下文
    - 时间
    - 会话
    - 投影
domain:
  - Runtime
contains:
  - runtime/context_provider.py
  - runtime/context_validator.py
  - runtime/temporal_resolver.py
  - runtime/time_context.json
status_source: ASSET-SNAPSHOT-002
```

### 2.4 Lottery

```yaml
asset_id: LOT-MODULE-001
human:
  name: 彩票系统
  aliases:
    - 彩票
    - lottery
    - 开奖
  keywords:
    - 彩票
    - 开奖
    - SSQ
    - DLT
    - KL8
    - 预测
    - 核对
    - 日报
domain:
  - Lottery
contains:
  - .local/bin/lottery-worker.sh
  - hooks/oek-ci-gate/push-notify.mjs
  - hooks/oek-ci-gate/push-gate.mjs
  - memory/events/lottery/
  - memory/data/lottery/
  - memory/cache/lottery/predictions/
  - systemd timers: lottery-fetch, lottery-daily, {ssq,dlt,kl8}-{predict,check}, source-retry
status_source: ASSET-SNAPSHOT-002
```

### 2.5 Trading

```yaml
asset_id: TRD-MODULE-001
human:
  name: 期货模拟交易模块
  aliases:
    - 期货
    - 期货模拟
    - futures
    - futures-sim
  keywords:
    - 交易
    - 量化
    - 策略
    - 回测
    - 行情
    - 期货
    - 保证金
    - 盯市
domain:
  - Trading
contains:
  - market_futures/
  - futures_sim.py
  - memory/state/huo/FUTURES-SIM-V0.1-ARCH.md
  - memory/state/huo/TRADING-RUNTIME-V0.5-ARCH.md
  - systemd timers: market-futures-{collector,strategy}
status_source: ASSET-SNAPSHOT-002
```

### 2.6 Monitoring

```yaml
asset_id: MON-MODULE-001
human:
  name: 系统资产观察扫描器
  aliases:
    - asset observer
    - 资产扫描
  keywords:
    - 资产
    - 观察
    - 扫描
    - 盘点
    - 快照
domain:
  - Monitoring
contains:
  - scripts/asset_observer.py
  - docs/SYSTEM-ASSET-OBSERVATION.md
  - memory/data/system/asset-observation.jsonl
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: MON-MODULE-002
human:
  name: 系统传感器
  aliases:
    - sensors
    - 健康检查
    - 监控
  keywords:
    - 传感器
    - CPU
    - 内存
    - 磁盘
    - 负载
    - 健康
domain:
  - Monitoring
contains:
  - scripts/collect-sensors.sh
  - memory/data/system/system-health.jsonl
  - memory/data/system/service-state.jsonl
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: MON-MODULE-003
human:
  name: Token 观测
  aliases:
    - token observer
    - Token 指标
  keywords:
    - token
    - 用量
    - 会话
    - 成本
domain:
  - Monitoring
contains:
  - scripts/collect-token-metrics.sh
  - scripts/analyze-token-metrics.py
  - memory/data/system/token-metrics.jsonl
  - ~/.openclaw/observe-token.sh
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: MON-MODULE-004
human:
  name: TG 行为诊断
  aliases:
    - TG diagnostics
    - TG 诊断
    - 行为分析
  keywords:
    - TG
    - 诊断
    - 行为
    - 分析
    - 异常检测
domain:
  - Monitoring
contains:
  - tools/tg_transcript_reader.py
  - tools/tg_behavior_analyzer.py
  - tools/tg_maintenance_queue.py
  - diagnostics/agent_behavior/telegram/
  - registry/diagnostic/
status_source: ASSET-SNAPSHOT-002
```

### 2.7 Infrastructure

```yaml
asset_id: INF-MODULE-001
human:
  name: 系统备份体系
  aliases:
    - backup
    - 备份
  keywords:
    - 备份
    - 恢复
    - 审计
    - 完整性
domain:
  - Infrastructure
contains:
  - scripts/backup-full.sh
  - scripts/audit-backup.sh
  - scripts/restore-verify.sh
  - /backup/
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: INF-MODULE-002
human:
  name: Billing Pipeline
  aliases:
    - billing
    - 计费
  keywords:
    - 计费
    - 快照
    - 推送
    - 成本
domain:
  - Infrastructure
contains:
  - hooks/oek-ci-gate/billing-{snapshotter,push-worker,loader}.mjs
  - systemd timers: oek-billing-{snapshot,push}
status_source: ASSET-SNAPSHOT-002
```

```yaml
asset_id: INF-MODULE-003
human:
  name: 本地模型服务
  aliases:
    - Ollama
    - 本地模型
    - local model
  keywords:
    - 模型
    - Ollama
    - 推理
    - 本地
domain:
  - Infrastructure
contains:
  - scripts/local-task-worker.sh
  - scripts/eval-local.sh
  - Ollama service (systemd)
  - qwen2.5:3b / qwen3:4b
status_source: ASSET-SNAPSHOT-002
```

---

## 3. Asset Alias Dictionary

> 自然语言 → 机器命名的快速查找表。

| 用户说 | 匹配 Machine ID | 解析路径 |
|:-------|:----------------|:---------|
| 期货 / 期货模拟 / futures | TRD-MODULE-001 | Trading → Futures-Sim |
| 彩票 / 开奖 / SSQ / DLT / KL8 | LOT-MODULE-001 | Lottery → 彩票系统 |
| 契约 / 治理 / 冻结 | GOV-MODULE-001/002 | Governance → 契约体系 |
| 身份 / 隔离 / 权限 | GOV-MODULE-004 | Governance → 身份治理 |
| 建设手册 / 方法论 | CON-MODULE-001 | Construction → 模块建设手册 |
| 资产观察 / 盘点 / 快照 | MON-MODULE-001 | Monitoring → Asset Observer |
| Gateway / 运行时 | RUN-MODULE-001 | Runtime → Gateway |
| 自愈 / 边界 | RUN-MODULE-002 | Runtime → Self-Healing |
| 传感器 / 健康 / 监控 | MON-MODULE-002 | Monitoring → 系统传感器 |
| Token / 用量 / 成本 | MON-MODULE-003 | Monitoring → Token 观测 |
| TG行为 / 诊断 | MON-MODULE-004 | Monitoring → TG Diagnostics |
| 备份 / 恢复 | INF-MODULE-001 | Infrastructure → Backup |
| 计费 / billing | INF-MODULE-002 | Infrastructure → Billing |
| 模型 / Ollama / 推理 | INF-MODULE-003 | Infrastructure → Local Model |

---

## 4. Semantic Keywords Index

> 按关键词反查模块。

| Keyword | Related Modules |
|:--------|:----------------|
| 量化 | TRD-MODULE-001 (交易) |
| 策略 | TRD-MODULE-001 (交易) |
| 回测 | TRD-MODULE-001 (交易) |
| 行情 | TRD-MODULE-001 (交易), LOT-MODULE-001 (彩票) |
| 预测 | LOT-MODULE-001 (彩票) |
| 核对 | LOT-MODULE-001 (彩票) |
| 日报 | LOT-MODULE-001 (彩票) |
| 通知 | LOT-MODULE-001 (彩票) |
| 推送 | LOT-MODULE-001 (彩票) |
| 冻结 | GOV-MODULE-002 (冻结仲裁) |
| 基线 | GOV-MODULE-002 (冻结仲裁) |
| 审计 | GOV-MODULE-003 (治理链) |
| 证据 | GOV-MODULE-003 (治理链) |
| 身份 | GOV-MODULE-004 (身份) |
| 隔离 | GOV-MODULE-004 (身份) |
| 入口 | GOV-MODULE-004 (身份) |
| 服务 | RUN-MODULE-001 (Gateway) |
| 引擎 | RUN-MODULE-001 (Gateway) |
| 上下文 | RUN-MODULE-003 (运行时上下文) |
| 时间 | RUN-MODULE-003 (运行时上下文) |
| 会话 | RUN-MODULE-003 (运行时上下文) |
| 配置 | RUN-MODULE-002 (自愈), GOV-MODULE-001 (契约) |
| 资产 | MON-MODULE-001 (资产观察), CON-MODULE-002 (观察层) |
| 扫描 | MON-MODULE-001 (资产观察) |
| 观察 | MON-MODULE-001 (资产观察), RUN-MODULE-002 (自愈) |
| 漂移 | CON-MODULE-002 (观察层) |
| 成本 | MON-MODULE-003 (Token), INF-MODULE-002 (Billing) |
| 备份 | INF-MODULE-001 (备份) |
| 恢复 | INF-MODULE-001 (备份) |
| 模型 | INF-MODULE-003 (本地模型) |
| 推理 | INF-MODULE-003 (本地模型) |
| 诊断 | MON-MODULE-004 (TG诊断) |
| 行为 | MON-MODULE-004 (TG诊断) |
| 异常 | MON-MODULE-004 (TG诊断) |
| 计费 | INF-MODULE-002 (Billing) |

---

## 5. Relationship Mapping

> 跨域关系：模块间的依赖/引用/所属关系。

```yaml
TRD-MODULE-001 (期货模拟):
  depends_on:
    - RUN-MODULE-003 (运行时上下文) — 时间解析依赖
  referenced_by:
    - CON-MODULE-001 (建设手册 §8.14)
    - CON-MODULE-003 (架构蓝图)
  status_source: ASSET-SNAPSHOT-002

LOT-MODULE-001 (彩票系统):
  depends_on:
    - INF-MODULE-002 (Billing Pipeline) — 通知推送
  referenced_by:
    - CON-MODULE-001 (建设手册 §8.1)
    - GOV-MODULE-005 (领域契约组-彩票)
  status_source: ASSET-SNAPSHOT-002

MON-MODULE-001 (资产观察):
  referenced_by:
    - CON-MODULE-002 (系统资产观察层)
    - docs/SYSTEM-ASSET-OBSERVATION.md
  status_source: ASSET-SNAPSHOT-002

GOV-MODULE-005 (领域契约组-彩票):
  governs:
    - LOT-MODULE-001 (彩票系统)
  status_source: ASSET-SNAPSHOT-002

GOV-MODULE-006 (领域契约组-TG):
  governs:
    - MON-MODULE-004 (TG 行为诊断)
  status_source: ASSET-SNAPSHOT-002
```

---

## 6. Evidence Reference

语义索引的映射来源：

| Source | Type | Provides |
|:-------|:-----|:---------|
| ASSET-SNAPSHOT-002 | Asset Observation | 资产存在性证明 + 分类统计 |
| MODULE-CONSTRUCTION-HANDBOOK.md | Module Handbook | 模块定义 + 边界 + 避坑 |
| MODULE-INDEX.md | Module Index | A/B/C/D 分类 |
| CONTRACT-REGISTRY.md | Contract Registry | 契约身份 + 状态 |
| PHASE_STATUS.json | Phase Status | 模块冻结基线状态 |

---

## Query Examples

```text
Q: "量化策略相关资产"
  → keywords: ["量化", "策略"]
  → TRD-MODULE-001 (Futures-Sim)
  → Contains: market_futures/, futures_sim.py
  → Status: ASSET-SNAPSHOT-002 → frozen (core) + active (live)


Q: "资产观察层有哪些模块"
  → keywords: ["资产", "观察"]
  → MON-MODULE-001 (Asset Observer)
  → CON-MODULE-002 (System Asset Observation)
  → Related: RUN-MODULE-002 (Self-Healing)
```

---

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial. 9 Domains, 21 Modules, Alias Dictionary, Keywords Index, Relationship Mapping, Evidence Reference |
