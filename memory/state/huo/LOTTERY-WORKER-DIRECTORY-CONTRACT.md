# Lottery Worker Directory Contract v1.0

```yaml
contract:
  name: LOTTERY-WORKER-DIRECTORY
  version: v1.0
  level: L3
  parent: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
  scope: lottery worker directory implementation
  owner: 燃🔥
  status: active
```

**Phase: External Worker Boundary — 非源码改动**
**Date:** 2026-07-17

---

## 前置说明

本 Contract 定义 lottery-worker 在 External Worker 边界中的目录归属、权限范围、Writer 角色及数据生命周期。

依赖链：
```
Lottery Capability Contract v1.0
        ↓ 定义能力身份
Capability Registry              → lottery.* 已注册
        ↓ 定义能力元数据
Memory Writer Boundary v1.0      → external-event-producer 已新增
        ↓ 定义 Writer 权限
Lottery Worker Directory Contract v1.0  ← 本文件
        ↓ 定义目录/归属/边界
Worker Runtime (systemd timer)
```

---

## Section 1: Worker Identity

```yaml
worker:

  id: lottery-worker

  type:
    external_worker

  class:
    external-event-producer
```

### class 说明

`external-event-producer` 是 Worker Writer 的一种特殊身份（定义见 MEMORY-WRITER-BOUNDARY.md）。

区别：

| 维度 | worker (默认) | external-event-producer |
|------|--------------|------------------------|
| 默认写入域 | cache | events/<owned-domain> |
| 写入规则 | disposable | append-only, immutable |
| 事实链贡献 | 否 | 是 |

---

## Section 2: Ownership

```yaml
ownership:

  domain:
    lottery

  owned_namespace:
    - events/lottery

  not_owned:
    - events/*                # 不拥有其他 events 子域
    - events                  # 不拥有 events 根域
    - state/*
    - facts/*
    - memory/*
    - cache/*                 # 可读写但非拥有
```

### 说明

- `domain`：lottery-worker 的职责领域标识
- `owned_namespace`：worker 拥有写入权的 namespace（受 `append-only` 约束）
- `not_owned`：显式拒绝的 namespace，防止能力越界

---

## Section 3: Writer Role

```yaml
writer:

  role:
    producer

  permissions:

    append:
      - events/lottery/ssq
      - events/lottery/dlt
      - events/lottery/klb

    read:
      - events/lottery/*
      - cache/lottery/*

    write:
      - cache/lottery/*       # 状态缓存, disposable

  denied:
    - events/*                # 除 lottery 外的 events 子域
    - events/state/*
    - state/*
    - facts/*
    - memory/*
    - runtime/*
```

### 角色说明

| 角色 | 权限 | 说明 |
|------|------|------|
| producer | append | 产生开奖事件候选，经 validator 后写入 |
| observer | read | 可读取历史开奖事件用于分析 |
| state keeper | read/write | 缓存抓取状态（可清理） |

---

## Section 4: Storage Layout

### 事件存储（事实层）

```
events/
  lottery/
    ssq.jsonl        ← 双色球开奖事件
    dlt.jsonl        ← 大乐透开奖事件
    klb.jsonl        ← 快乐8开奖事件
```

记录格式：

```json
{
  "event_id":"lottery-20260717-001",
  "type":"LOTTERY_DRAW",
  "source":"china-lottery",
  "game":"SSQ",
  "issue":"2026078",
  "numbers":{
     "red":[3,8,12,19,25,31],
     "blue":7
  },
  "timestamp":"2026-07-17T21:30:00",
  "hash":"sha256:xxx"
}
```

### 状态缓存（运行时层）

```
cache/
  lottery/
    last_fetch.json       ← 上次抓取状态
    source_status.json    ← 数据源健康状态
    retry_state.json      ← 重试信息
```

### 生命周期

| 存储 | 创建者 | 生命周期 | 可删除 |
|------|--------|---------|--------|
| events/lottery/* | lottery-worker + validator | 永久 | ❌ |
| cache/lottery/* | lottery-worker | 短期 | ✅ |

---

## Section 5: Execution Boundary

```yaml
execution_boundary:

  allowed:
    - collect          # 从外部源抓取开奖数据
    - validate         # 校验数据格式/完整性/重复
    - analyze          # 对历史事件做统计分析
    - report           # 生成开奖报告
    - notify           # 推送至通知渠道

  forbidden:
    - modify_event     # 修改已写入的事件
    - delete_event     # 删除已写入的事件
    - alter_runtime    # 改变 Gateway Runtime 状态
    - escalate         # 自行获取未声明能力
    - auto_bet         # 自动下注
    - predict          # 预测开奖号码
```

### 禁止操作说明

| 禁止操作 | 风险 | 原因 |
|---------|------|------|
| modify_event | 高 | 破坏事件 immutable 原则 |
| delete_event | 高 | 破坏事件审计链 |
| alter_runtime | 高 | Worker 不应触碰 Runtime |
| escalate | 中 | 违反三条铁律 |
| auto_bet | 高 | 财务风险，超出系统边界 |
| predict | 中 | 无证据支撑，误导用户 |

---

## Section 6: Trust Boundary

```yaml
trust_boundary:

  producer:
    lottery-worker              # 提交事件候选

  validator:
    deterministic-validator     # 格式/重复/时间校验

  authority:
    event-store                 # 事件保存方（不可变事实链）

  consumer:
    analyzer                    # 只读历史事件，不产生事实
    reporter                    # 基于分析结果生成报告
    notifier                    # 将报告推送到通知渠道
```

### 数据流

```
开奖源
  ↓ (fetch)
lottery-worker
  ↓ (原始数据)
deterministic-validator
  ↓ (校验通过)
events/lottery/*.jsonl  ← 事实链（append only）
  ↓ (read)
analyzer
  ↓ (统计结果)
reporter
  ↓ (报告)
notifier → Telegram
```

---

## Section 7: 与现有治理契约的关系

| 契约 | 关系 |
|------|------|
| Memory Ownership Contract | lottery 事件归 events 管，遵守 event immutable 规则 |
| Memory Writer Boundary | lottery-worker 以 external-event-producer 身份写入 events/lottery |
| Capability Registry | 5 项 lottery.* 能力已注册，category 映射到 io/event/provider/notification |
| Plugin Capability Contract | Worker 声明继承三条铁律 |
| Lottery Capability Contract | 定义能力身份和风险级别 |

---

## 冻结范围

### 包含

- Worker 身份声明
- 目录所有权
- 写入/读取/拒绝权限
- 存储布局
- 执行边界（允许/禁止）
- 信任链

### 明确排除

- 具体采集逻辑（属实现层）
- API 接口定义（属实现层）
- 数据源配置（属实现层）
- Worker 生命周期管理（属 systemd timer）

治理链到此完整，下一步是实现层。
