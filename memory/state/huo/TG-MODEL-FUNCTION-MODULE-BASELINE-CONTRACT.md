# TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT v1.0

> ```yaml
> contract:
>   name: TG-MODEL-FUNCTION-MODULE-BASELINE
>   version: v1.0
>   level: L2
>   parent: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
>   scope: TG model module
>   owner: 燃🔥
>   status: active
> ```
>
> TG Model 功能模块建设验收契约
> 定位: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT 的 TG 适配实例
> 上位契约:
>   FREEZE-CONTRACT → FUNCTION-MODULE-BASELINE-CHECK-CONTRACT → 本契约
> 核心原则: TG 模型作为 Extension Module 接入，不改变 Core、不突破权限、不污染 Memory、不替代决策链

---

## ① Extension Boundary（扩展边界）

**目的：** 确认 TG 模型是外挂能力模块，不是 Core 扩展。

| 项目 | 要求 |
|------|------|
| OpenClaw Core 修改 | 0 |
| Governance 修改 | 0 |
| Event Kernel 修改 | 0 |
| Memory Kernel 修改 | 0 |
| 独立模块目录 | 必须 |

结构：

```text
OpenClaw Core
      │
      └── tg-model-module/    ← 独立目录
```

禁止：

```text
tg-model → 修改 Core 行为
```

**判定：** 🟢 PASS = Core 零修改

---

## ② Module Ownership（模块归属）

| 项目 | 要求 |
|------|------|
| Owner | 明确身份 |
| 维护者 | 明确身份 |
| 生命周期 | 独立于 OpenClaw 生命周期 |
| 修改责任 | 模块维护者承担 |

TG 模型属于：

```text
Module Owner → TG Model
```

不是：

```text
TG Model → OpenClaw Owner（反向归属）
```

**判定：** 🟢 PASS = Owner 明确，归属方向正确

---

## ③ Memory Namespace Isolation（记忆隔离）

**目的：** 防止 TG 输出自动写入系统记忆。

TG 模型产生的信息分类：

| 类型 | 去向 | 限制 |
|------|------|------|
| 原始输出 (analysis/result) | `module/reports/` | 允许 |
| 分析结果 | `module/data/` | 允许 |
| 系统事实断言 | 系统 `memory/` | 禁止自动写入 |
| 长期规则/偏好 | 系统 `memory/` | 须经治理流程确认 |

禁止：

```text
TG response → memory/（自动提升）
```

**判定：** 🟢 PASS = 输出模块本地，不自动写 Memory

---

## ④ Interface Contract（接口契约）

**目的：** 输入输出格式固定，不隐式耦合。

TG 模块必须明确定义：

### 输入

```json
{
  "context": "当前上下文/系统状态",
  "task": "分析/总结/分类/评估/建议",
  "metadata": "附加信息（时间、来源、版本）"
}
```

### 输出

```json
{
  "type": "analysis | summary | classification | evaluation | suggestion",
  "result": "结构化结果内容",
  "confidence": "置信度 (0.0-1.0)",
  "error": "错误状态（如有）"
}
```

必须明确：

| 项目 | 要求 |
|------|------|
| 输入来源 | 定义哪些模块可调用 |
| 输出格式 | 固定 schema，有版本号 |
| 版本号 | schema version |
| 错误状态 | 定义 error code 集合 |

**判定：** 🟢 PASS = 输入输出 schema 固定

---

## ⑤ Capability Boundary（能力边界）

**目的：** 明确 TG 模型提供什么能力，禁止什么能力。

允许：

```text
分析     ✅
总结     ✅
分类     ✅
评估     ✅
建议     ✅
```

默认禁止（除非明确授权）：

```text
修改配置     ❌
修改代码     ❌
修改状态     ❌
执行交易     ❌
改变规则     ❌
```

能力声明格式：

```yaml
capabilities:
  analysis: true          # 数据分析
  summary: true           # 文本总结
  classification: true    # 分类
  evaluation: true        # 评估
  suggestion: true        # 建议
  memory_write: false     # 禁止自动写 Memory
  core_modify: false      # 禁止修改 Core
  execution: false        # 禁止执行交易/操作
  config_modify: false    # 禁止修改配置
  state_modify: false     # 禁止修改运行时状态
```

**判定：** 🟢 PASS = 能力声明完整，禁止项明确

---

## ⑥ Decision Boundary（决策边界）

**目的：** TG 模型定位为决策支持，非决策权。

链路——正确：

```text
System Data
      │
      v
TG Model
      │
      v
Suggestion
      │
      v
Human / Rule Engine（最终决策）
```

禁止：

```text
TG Model → Execute（跳过人工/规则）
```

**判定：** 🟢 PASS = 输出建议，不执行

---

## ⑦ Tool Boundary（工具调用边界）

**目的：** TG 如需调工具必须经 Tool Gateway，不得直通 Shell。

如果 TG 需要工具调用能力：

```text
TG
 │
 v
Tool Gateway（OpenClaw 标准网关）
 │
 v
Tool（白名单约束）
```

| 检查项 | 要求 |
|--------|------|
| 工具白名单 | 必须预先定义 |
| 参数验证 | Gateway 层校验 |
| 调用记录 | 必须记录到事件日志 |
| 权限控制 | 按 Terminal Authority 分级 |

禁止：

```text
TG → shell / root 级别执行
```

**判定：** 🟢 PASS = 工具调用经 Gateway，不走直通

---

## ⑧ Data Provenance（数据来源）

**目的：** TG 使用的输入数据可追溯。

| 项目 | 要求 |
|------|------|
| 输入来源 | 记录调用方/事件来源 |
| 时间 | 记录调用时间 |
| 版本 | 记录模型版本 + prompt 版本 |
| 上下文 | 记录输入上下文引用 |

```text
Input Source
      │
      v
TG Processing
      │
      v
Output
```

**判定：** 🟢 PASS = 来源可追溯

---

## ⑨ Determinism（行为验证）

**目的：** 同输入验证输出稳定性。

| 项目 | 要求 |
|------|------|
| 稳定 | 同上下文+同prompt+同模型版本 → 输出逻辑一致 |
| 可解释 | 输出有 reasoning 或 confidence |
| 随机因素 | 记录（temperature, seed 等配置值） |

允许模型概率波动（LLM 特性），但必须记录：

```text
model_version: "gpt-4o-2026-05"
prompt_version: "v1.2"
config: { temperature: 0.3, seed: null }
```

**判定：** 🟢 PASS = 波动可记录，不隐藏随机因素

---

## ⑩ Audit Trail（审计）

**目的：** 每次 TG 调用可追溯。

必须记录：

```json
{
  "timestamp": "ISO-8601",
  "model": "模型标识 + 版本",
  "input_ref": "输入上下文引用 / hash",
  "output_type": "analysis|summary|...",
  "result_hash": "输出摘要 hash（可选）"
}
```

记录内容：

```text
✅ 调用事实（什么输入 → 什么输出）
❌ 不记录私有推理链（原始 token 序列）
```

**判定：** 🟢 PASS = 调用记录完整，不泄露内部

---

## ⑪ Test Evidence（测试）

**目的：** 模块上线前通过充分测试。

| 测试类型 | 要求 |
|----------|------|
| 输入测试 | 合法/边界/异常输入覆盖 |
| 输出测试 | 输出格式符合 schema |
| 越权测试 | 确认不能越界操作 |
| 异常测试 | 模型不可用/超时/返回异常 |
| 回归测试 | 版本升级后关键场景一致 |

**判定：** 🟢 PASS = 5 类测试覆盖

---

## ⑫ Configuration Governance（配置治理）

| 项目 | 要求 |
|------|------|
| 模型版本 | 配置化，不硬编码 |
| Prompt 版本 | 配置化/文件化 |
| 参数配置 | temperature, max_tokens, seed 等 |
| Provider 配置 | API endpoint, keyRef |

禁止：

```text
代码内硬编码模型行为或参数
```

**判定：** 🟢 PASS = 全配置化

---

## ⑬ Recovery（恢复）

**目的：** TG 不可用时系统继续运行。

| 场景 | 要求 |
|------|------|
| TG 超时 | 调用方有 timeout + retry |
| 模型不可用 | 有 fallback 机制 |
| 结果异常 | 调用方能识别 error 状态 |
| 单点故障 | TG 不应成为 Core 单点故障 |

```text
TG failure
      │
      v
fallback（降级/缓存/默认值）
      │
      v
system continue（核心功能不受阻断）
```

**判定：** 🟢 PASS = TG 故障不影响 Core 运行

---

## ⑭ Freeze Integrity（冻结完整性）

**目的：** 确认检查和建设不破坏冻结状态。

冻结内容：

```text
TG Module Version     🔒
Model                 🔒
Prompt                🔒
Schema                🔒
Capability Declaration 🔒
Config                🔒
```

冻结后变动规则：

```text
Change Request → Review → Approved → Execute
```

**判定：** 🟢 PASS = 冻结后经变更流程

---

## TG 模块验收模板

```text
TG MODEL MODULE BASELINE CHECK
===============================
Module:   <模块名称>
Version:  <版本>
Date:     <检查日期>

①  Extension Boundary       🟢/🟡/🔴
②  Ownership                🟢/🟡/🔴
③  Namespace Isolation      🟢/🟡/🔴
④  Interface Contract       🟢/🟡/🔴
⑤  Capability Boundary      🟢/🟡/🔴
⑥  Decision Boundary        🟢/🟡/🔴
⑦  Tool Boundary            🟢/🟡/🔴
⑧  Data Provenance          🟢/🟡/🔴
⑨  Determinism              🟢/🟡/🔴
⑩  Audit Trail              🟢/🟡/🔴
⑪  Test Evidence            🟢/🟡/🔴
⑫  Config Governance        🟢/🟡/🔴
⑬  Recovery                 🟢/🟡/🔴
⑭  Freeze Integrity         🟢/🟡/🔴

Final:  🟢 PASS / 🟡 WARNING / 🔴 FAIL
```

---

## 契约层级总图

```text
FREEZE-CONTRACT.md
   └── 仲裁规则：冻结定义 / 修复vs扩展 / 发现分类
         │
         v
FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md v1.0
   └── 通用框架：14 项维度 + 检查模板
         │
         ├── trading-runtime（已审核，🟢 PASS）
         │
         ├── lottery-module（适用，待审核）
         │
         └── TG-model-module ← 本契约
               └── TG 特定适配：Capability / Decision /
                   Tool Boundary 约束强化
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始契约，FUNCTION-MODULE-BASELINE-CHECK-CONTRACT 的 TG 适配实例 |
