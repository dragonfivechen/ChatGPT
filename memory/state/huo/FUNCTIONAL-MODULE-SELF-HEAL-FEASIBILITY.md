# 功能模块自愈可行性分析

基于实际模块清单与可观测性验证，对照龙哥的 M1-M5 路线评估。

---

## 一、模块清单与可观测性

### 可观测模块（systemd timer 管理）— 13 个

```
market-futures-collector  ✅ systemctl show → ExecMainExitCode, Result, timestamp
market-futures-strategy   ✅ 同上
oek-billing-snapshot      ✅ 同上
oek-billing-push          ✅ 同上
oek-token-observe         ✅ 同上
oek-daily-status          ✅ 同上
source-retry              ✅ 同上
dlt-predict / dlt-check   ✅ 同上
kl8-predict / kl8-check   ✅ 同上
lottery-fetch             ✅ 同上
```

**当前已在 P1.1 的 `health_graph.py` 中覆盖。** 只需扩展状态模型。

### ⚠️ 部分可观测模块（cron 管理）— 9 个

```
backup-full                ❌ 输出重定向到 /dev/null 2>&1
collect-sensors            ❌ 同上
eval-local                 ❌ 同上
local-task-worker          ✅ 自身写入日志（"done: 8 success, 0 fail"）
context-provider           ❌ 输出重定向
memory-governance-worker   ⚠️ 追加写入 governance-pipeline.log
collect-token-metrics      ❌ 输出重定向
analyze-token-metrics      ❌ 输出重定向
contract-validator         ❌ 输出重定向
```

**9 个 cron 模块中，7 个不可观测。** stdout/stderr 全部 `>/dev/null 2>&1`。

---

## 二、核心可行性发现

### 发现 1：P1.1 已经覆盖了 13/22 模块

`health_graph.py` 的 `cron_pipeline` 节点当前检查所有 systemd-timed 服务。
扩展 9 个 cron 模块的观测不需要增加新的 Infrastructure，只需补充检查方式。

### 发现 2：cron 模块的观测缺口需要修补才能进入 M2

对于 `> /dev/null 2>&1` 的模块，当前唯一可观测的痕迹是 CRON 日志中的执行记录。
但这只能证明"CRON 调度了任务"，不能证明"任务成功完成"。

**需要的最少变更（每个 cron 模块）：**

```
# 从
cmd.sh >/dev/null 2>&1
# 改为
cmd.sh && touch /tmp/health/${name}_ok
```

或者转为 systemd timer（已有 13 个模块采用此方式，模式验证过）。

### 发现 3：状态机模型（INIT→READY→RUNNING→DEGRADED→FAILED→RECOVERING→READY）

对于 systemd oneshot 服务，真正的生命周期是：

```
timer fires
  ↓
service starts (activating)
  ↓
script runs
  ↓
service stops (inactive/dead + Result=success/failure)
  ↓
等待下一周期
```

没有 RUNNING 状态的驻留。DEGRADED 和 RECOVERING 也不由 service 直接表达。

因此龙哥的状态机需要适配 oneshot 服务的实际行为：

```
实际   : idle → executing → success/failure → idle
一般模块: IDLE → RUNNING → DONE/FAILED → IDLE

持续服务: RUNNING → DEGRADED → FAILED → RECOVERING → RUNNING
（如 TG channel、gateway 等常驻进程）
```

**状态机不能共用：** oneshot 服务和常驻进程的健康模型不同。

### 发现 4：故障类型分类可映射

| 建议分类 | systemd 可判定 | cron 可判定 |
|:--------|:-------------:|:----------:|
| 进程异常 (exit ≠ 0) | ✅ `ExecMainExitCode` | ⚠️ 仅 `local-task-worker` |
| 超时 | ✅ timer + timeout | ❌ |
| 配置异常 | ❌ 无法从 exit code 区分 | ❌ |
| 数据异常 | ❌ 同上 | ❌ |
| 网络异常 | ❌ 同上 | ❌ |
| 资源异常 | ❌ 同上 | ❌ |

**systemd 只能告诉你"exit code ≠ 0"，不能告诉你为什么。** 故障分类需要模块级日志分析或结构化的输出。

---

## 三、总体可行性

| 阶段 | 可行性 | 前提 |
|:-----|:-----:|:-----|
| M1 Module Registry | ✅ 高 | 22 个模块已有清单 |
| M2 Health Snapshot | ✅ 高 | 13/22 已有 P1.1 覆盖；9/22 需补 observerbility |
| M3 Event Audit | ⚠️ 中 | 故障类型分类依赖模块输出，非通用 |
| M4 Recovery Policy | ✅ 高 | Level 1 重复执行 = 现有 timer 已实现 |
| M5 Selective Auto Recovery | ⚠️ 中 | 取决于 M3 的证据积累 |

### 关键约束

1. **故障类型无法通用分类** — exit code 0/非 0 不能区分网络/配置/数据/资源异常
2. **cron 模块观测缺口** — 9 个模块中 7 个无输出，需要用 touch file 或 systemd timer 迁移
3. **状态机不能共用** — oneshot 服务 vs 常驻进程的健康模型不同，需分别定义

### 与 P0/P1.1 的关系

```
P1.1 health_graph（现有）                    M1-M5（功能模块）
  cron_pipeline 节点                        扩展为每个模块独立节点
     ├── 13 systemd 服务                        → nodes.${module}
     └── 判断 Result=success/failure            → 升级为生命周期状态机

扩展点：
  health_graph.py
    └── add_module_node(name, check_fn)    ← 注册新模块
    └── expand node health                  ← INIT/IDLE/RUNNING/DONE/FAILED
```

### 实际路径

```
M1  Module Registry
  └── 将 crontab + systemd 中 22 个模块注册到 health_graph
  └── file: modules.yaml（而非硬编码）

M2  Health Snapshot
  └── systemd 模块：复用现有 systemctl show
  └── cron 模块：touch-file based 或 systemd timer 迁移
  └── 状态机：oneshot 用 IDLE/RUNNING/DONE/FAILED，常驻用 RUNNING/DEGRADED/FAILED/RECOVERING

M3  Event Audit
  └── events/module_events.jsonl
  └── 每个故障记录: module, from_state, to_state, action

M4  Recovery Policy
  └── 基于故障类型分级
  └── Level 0-4 映射表

M5  Selective Auto Recovery
  └── 依赖 M3 数据积累，至少 14 天
```

---

## 四、建议

如果进入功能模块自愈，优先级调整建议：

```
P0   Repair Audit       →  FROZEN
P1.1 Health Graph       →  FROZEN
P1.2 Health State Model →  MERGE INTO M1
P3   Model Reliability  →  OBSERVE

M1-M2 功能模块健康图     →  复用 P1.1 模式扩展
M3    模块事件审计        →  等待 M1-M2 + P3 证据
M4-M5 恢复策略            →  等待 M3 证据
```

**最经济的起点：将 `health_graph.py` 的 cron_pipeline 节点扩展为 module registry，保持与 P1.1 相同的 snapshot → diff → event 模式。** 

这不增加新的监控管道，只是扩展 P1.1 已有的节点模型。

---

## Baseline B: 功能模块自愈方案基线（2026-07-22）

### 核心结论

不是先建设 Repair Engine。
正确顺序：

```
已有健康源验证
        ↓
Health Graph 接入
        ↓
Semantic State 验证
        ↓
运行证据积累
        ↓
Recovery Policy 评估
```

### 已验证的关键发现

1. **"cron 模块不可观测"假设不成立。** 7 个 cron 模块全部已有输出文件，stdout 被抑制 ≠ 业务状态不可观测。
2. **100% 健康源覆盖。** 22 模块 → 22 健康源，无需 touch-file。
3. **systemd 是 execution evidence，不是 health evidence。** exit=0 只能证明进程完成，不能证明业务成功。
4. **mtime old ≠ failed。** 需要 schedule context + semantic evaluator（ACTIVE/IDLE/STALE/FAILED）。
5. **状态机不能统一。** oneshot 服务（IDLE → RUNNING → DONE/FAILED）和常驻服务（RUNNING → DEGRADED → FAILED → RECOVERING）需要不同模型。

### 禁止提前推进

- ❌ 自动修复动作
- ❌ Recovery Policy 设计
- ❌ Provider Fallback 实现
- ❌ Output Validator 扩展
- ❌ touch-file 插入（已有输出文件，不需要）

### 当前进度

M0 完成 → 进入 M1 Module Health Observation（7天证据窗口）。
