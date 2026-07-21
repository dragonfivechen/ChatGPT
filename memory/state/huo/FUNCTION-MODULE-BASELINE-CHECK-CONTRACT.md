# FUNCTION-MODULE-BASELINE-CHECK-CONTRACT v1.0

> ```yaml
> contract:
>   name: FUNCTION-MODULE-BASELINE-CHECK
>   version: v1.0
>   level: L1
>   parent: FREEZE-CONTRACT
>   scope: all functional modules
>   owner: 燃🔥
>   status: active
> ```
>
> 功能模块基线合规检查契约
> 来源: 2026-07-21 期货交易模块基线审计过程沉淀
> 定位: 所有未来功能模块进入冻结基线前的统一验收契约
> 关联: FREEZE-CONTRACT.md（冻结契约，本契约的上位仲裁规则）

---

## 检查目标

确认新增功能模块：

- 不侵入 Core
- 边界清晰
- 状态隔离
- 权限明确
- 可验证
- 可冻结
- 可审计

### 检查结果分级

```text
🟢 PASS      符合基线
🟡 WARNING   治理缺口，不影响运行
🔴 FAIL      违反冻结基线
```

---

## A. Extension Boundary（扩展边界）

**目的：** 确认模块属于 Extension，不是 Core 扩展。

| 检查项 | 要求 | 验证方法 |
|--------|------|----------|
| Core 代码修改 | 必须 0 | git diff / 源码搜索 |
| Core 配置修改 | 必须 0 | git diff OpenClaw 配置 |
| Core 事件污染 | 禁止 | 全局搜索 event_type 前缀 |
| Core memory 污染 | 禁止 | 确认模块不写入 memory/ |
| 独立目录 | 必须 | 模块根目录独立 |
| 独立生命周期 | 必须 | 无守护进程绑定 OpenClaw 进程 |

判定：

```text
Core unchanged = 🟢 PASS
Core modified  = 🔴 FAIL
```

**证据要求：** git diff 输出 / 目录结构 / import 依赖分析

---

## B. Ownership（模块归属）

**目的：** 明确谁负责模块。

| 项目 | 要求 |
|------|------|
| Owner | 明确身份 |
| Maintainer | 明确身份 |
| 修改权限 | 明确分级 |
| 审计角色 | 明确身份 |

禁止：

```text
观察者 = 修改者
```

例如：

```text
TG Agent
   │
   观察 / 审计
   │
   不能直接维护代码 (除非明确 P1 授权)
```

**证据要求：** MEMORY.md 或 ARCH.md 中声明 Owner 归属

---

## C. Namespace Isolation（命名空间隔离）

**目的：** 防止业务数据污染系统身份记忆。

确认所有文件/目录所属层：

| 数据类型 | 应属 | 反例 |
|----------|------|------|
| 系统事件 | OpenClaw `events/` | 模块事件写入 `events/` |
| 业务日志 | 模块自有目录 | 写入 `memory/events/` |
| 业务状态 | 模块自有目录 | 写入 `memory/state/` 非 Owned 路径 |
| 原始数据 | 模块自有目录 | 写入 `memory/data/` |
| 运行时缓存 | 模块自有目录 | 写入 `memory/cache/` |

禁止：

```text
业务状态 → OpenClaw memory namespace
```

**证据要求：** 目录结构树 / 写入路径检查

---

## D. Interface Contract（接口契约）

**目的：** 防止模块之间的隐式耦合。

| 项目 | 要求 |
|------|------|
| 输入格式 | 固定定义 |
| 输出格式 | 固定定义 |
| 字段定义 | 有 schema 文档 |
| 时间规范 | 时区 + 格式固定 |
| 错误处理 | 有约定 |

必须存在一份接口契约文档（schema.md 或等价物）：

```text
Module A
   │
   | schema v1
   │
Module B
```

不允許：

```text
A 随意输出
B 猜字段
  → 运行期才能发现不兼容
```

**证据要求：** schema 文件 / 事件定义 / 序列化格式文档

---

## E. State Ownership（状态所有权）

**目的：** 确认持久化状态归属。

模块级 `state/` 目录中的每一类状态必须有明确的 Owner：

| 状态类型 | 示例 | Owner 要求 |
|----------|------|-----------|
| 配置状态 | config.json | 模块维护者 |
| 运行状态 | session snapshot | 模块维护者 |
| 缓存状态 | cache.bin | 模块维护者 |
| 检查点 | checkpoint data | 模块维护者 |

原则：

```text
一个 state 目录只有一个 Owner
```

**证据要求：** state/ 目录结构 + Owner 声明

---

## F. Data Provenance（数据来源）

**目的：** 保证结果可解释。

| 项目 | 要求 |
|------|------|
| 来源 | 记录原始数据源 |
| 采集时间 | 记录获取时间窗 |
| 数据版本 | 显式版本标识 |
| 处理过程 | 可追踪 transform 链 |

形成可追溯的链条：

```text
Source
 ↓
Transform (清洗/归一化)
 ↓
Output
```

**证据要求：** 元数据文件 / provenance 文档 / 处理脚本

---

## G. Determinism（确定性）

**目的：** 验证模块行为是否可重复。

同样输入（input + config + version）必须得到同样输出。

| 场景 | 要求 |
|------|------|
| 生产路径 | 必须确定 |
| 模拟随机 | 允许，但随机边界须明确声明 |
| 测试随机 | 允许，但须在 test doc 中注明 |

随机因素必须明确声明哪些路径是非确定的：

```text
collector.py: 使用 random（无 seed）
  → 模拟行情生成，非生产路径
  → 生产路径 (CSV replay) 完全确定性
```

**证据要求：** determinism check 测试 / 随机因素声明

---

## H. Authority Boundary（权限边界）

**目的：** 确认模块不能越权。

| 权限 | 是否允许 |
|------|---------|
| 修改 Core 代码/配置 | ❌ |
| 修改其他模块状态 | ❌ |
| 输出业务结果 | ✅ |
| 请求外部服务 (HTTP/API) | 按授权，需声明 |

**证据要求：** 权限声明文件 / 代码检查

---

## I. Risk Boundary（风险边界）

**目的：** 确认观察(Observe)、决策(Decision)、执行(Execute)三层隔离。

```text
Observe
   │
   v
Decision
   │
   v
Execute
```

必须检查每一层是否有越权。例如：

允许：

```text
Risk → Report（观察层）
```

不一定允许：

```text
Risk → Execute（除非明确授权）
```

| 检查项 | 要求 |
|--------|------|
| 观察层是否产生执行意图 | 禁止（除非授权） |
| 决策层是否跳过执行 | 禁止（除非授权） |
| 执行层是否不经过决策 | 禁止（除非授权） |

**证据要求：** 模块调用链分析 / 接口方法搜索

---

## J. Recovery Capability（恢复能力）

**目的：** 确认模块异常后可恢复。

验证流程：

```text
Save (保存状态)
 ↓
Stop (停止)
 ↓
Restore (恢复)
 ↓
Continue (继续)
```

验证点：

| 项目 | 要求 |
|------|------|
| 状态恢复 | 恢复后与保存前一致 |
| 数据连续性 | 不丢、不重复 |
| 日志连续性 | 恢复后日志时间线完整 |

**证据要求：** recovery test / 状态持久化代码

---

## K. Test Evidence（测试证据）

**目的：** 证明模块冻结状态的可信度。

每次验证必须记录：

```text
测试结果: 🟢 PASS / 🔴 FAIL
时间: 2026-07-21T03:29:00+08:00
版本: v0.1 (commit abc1234)
环境: Python 3.12, Linux 7.0.0
覆盖: 37 tests (Phase 2 automated + Phase 3-5 manual)
```

不是说"测试过"，而是：

```text
什么版本，在什么环境，通过什么测试
结果是否可复现
```

**证据要求：** 测试记录文件 / CI 输出 / 时间戳+版本号

---

## L. Configuration Governance（配置治理）

| 项目 | 要求 |
|------|------|
| 配置版本化 | ✅ 随代码版本管理 |
| secrets 隔离 | ✅ 独立 `.secrets/` 目录 |
| 默认配置 | ✅ 提供默认值 |
| 环境差异 | ✅ dev/staging/prod 有区分 |

禁止：

```text
token、密码、API Key 写入代码
```

**证据要求：** 配置文件列表 / secrets 检查

---

## M. Audit Trail（审计链）

**目的：** 实现可回放、可解释。

完整事件链必须可追溯：

```text
Input (request / tick / event)
 ↓
Processing
 ↓
Decision (选哪个策略/路径)
 ↓
Action (执行了什么)
 ↓
Result (结果是什么)
```

每个环节必须包含：

| 字段 | 要求 |
|------|------|
| timestamp | ✅ ISO-8601 格式 |
| event_type | ✅ 标识环节 |
| trace id / correlation id | ✅ 跨环节关联（如适用） |

**证据要求：** 事件日志文件 / 字段定义 / 关联链验证

---

## N. Freeze Integrity（冻结完整性）

**目的：** 确认检查过程本身没有破坏冻结状态。

| 项目 | 要求 |
|------|------|
| Phase 状态 | 未改变 |
| 代码 | 未修改 |
| 功能 | 未扩展 |
| 文档 | 可补充（不受冻结限制） |

**证据要求：** git status / PHASE_STATUS.json 前后对比

---

## 最终模块检查模板

```text
MODULE BASELINE CHECK
=====================
Module:   <名称>
Version:  <版本>
Date:     <检查日期>

A  Extension Boundary     🟢/🟡/🔴  证据: <来源>
B  Ownership              🟢/🟡/🔴  证据: <来源>
C  Namespace              🟢/🟡/🔴  证据: <来源>
D  Interface Contract     🟢/🟡/🔴  证据: <来源>
E  State Ownership        🟢/🟡/🔴  证据: <来源>
F  Data Provenance        🟢/🟡/🔴  证据: <来源>
G  Determinism            🟢/🟡/🔴  证据: <来源>
H  Authority Boundary     🟢/🟡/🔴  证据: <来源>
I  Risk Boundary          🟢/🟡/🔴  证据: <来源>
J  Recovery               🟢/🟡/🔴  证据: <来源>
K  Test Evidence          🟢/🟡/🔴  证据: <来源>
L  Config Governance      🟢/🟡/🔴  证据: <来源>
M  Audit Trail            🟢/🟡/🔴  证据: <来源>
N  Freeze Integrity       🟢/🟡/🔴  证据: <来源>

Final:  🟢 PASS / 🟡 WARNING / 🔴 FAIL
```

---

## 补充说明

### 与 FREEZE-CONTRACT.md 的关系

本契约是 FREEZE-CONTRACT.md 的下位执行契约：

```text
FREEZE-CONTRACT.md       ← 上位仲裁规则
  └── 定义了：
       - 什么是冻结
       - 什么是修复 vs 扩展
       - 审计发现的三类判定
       - YELLOW-A/B/C 分层

FUNCTION-MODULE-BASELINE- ← 下位执行契约
CHECK-CONTRACT.md
  └── 定义了：
       - 新模块验收的 14 项检查维度
       - 每项的判定标准和证据要求
       - 检查模板
```

### 检查顺序建议

按检查成本从低到高：

```text
Top-down:  A → B → C → D → E   (架构层，快速通过/失败)
Bottom-up: N → K → J → G       (实现层，已有证据)
Middle:    F → H → I → L → M   (数据/权限层，需要深入检查)
```

若 A (Extension Boundary) 或 N (Freeze Integrity) 为 🔴 FAIL，其他检查无需继续。

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始版本，从期货模块审计实践沉淀 |
