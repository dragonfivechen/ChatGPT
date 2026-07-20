# 🔒 Maintenance Runbook v1.0 — 维护执行手册

**Status:** 🔒 FROZEN (Phase 3 Validated)
**Phase:** 4/4
**冻结日期:** 2026-07-20
**Namespace:** knowledge（共享，无身份隔离）
**适用范围:** 燃🔥（终端维护） + 烬🔥（TG 受约束维护）
**触发命令:** "执行维护" / "系统检查" / "健康检查" / "基线检查" / "状态巡检"

---

## Phase 进度

```
Phase 1  Runbook Draft       ✅
Phase 2  首次维护演练       ✅ COMPLETE
Phase 3  修正规则           ✅ COMPLETE
Phase 4  FROZEN             🔒  ← 当前
```

**冻结约束:**
- ❌ 不修改核心检查流程（7 步顺序）
- ❌ 不修改分类标准（4 级模型）
- ❌ 不修改行动边界（L0/L1/L2）
- ❌ 不添加新的自动修复条目
- ✅ 允许更新版本记录
- ✅ 允许更新附录中的脚本模板（仅采集工具）
- ✅ 允许在解冻前追加观察结果到 `memory/data/system/observations/`

---

## 核心原则

```
Evidence First
不猜测
不修改历史
不自动扩大范围
不改变冻结语义
Missing ≠ Broken
Detection ≠ Repair
```

所有输出基于可复现的运行时证据，非模型推断。

### Missing ≠ Broken（不存在不等于异常）

在维护中发现组件/文件/目录不存在时，先判断：

1. 是否属于**必需组件**（Contract 要求必须存在的）
2. 是否属于**计划阶段**（设计存在，实现未就绪）
3. 是否属于**可选组件**（缓存、临时文件、观测数据）

**禁止：发现缺失 → 自动创建/修复。**
**正确流程：缺失 → 分类 → 报告 → 判断是否需要行动。**

### Detection ≠ Repair（检查与修复分离）

维护流程严格分阶段：

```
发现
 ↓
分类
 ↓
报告
 ↓
授权确认
 ↓
处理
```

任何情景下禁止跳过报告-授权阶段直接处理。

---

## 检查顺序（固定，不可跳过）

```
1. Runtime
2. Config
3. Filesystem
4. Governance
5. Identity
6. Audit
7. Report
```

**原因：** 依赖关系自底向上。Runtime 异常时上层检查不可信。

---

## 1. Runtime 状态检查

### 1.1 服务

```bash
systemctl --user status openclaw-gateway   # OpenClaw 网关
systemctl --user status ollama             # 本地模型（如启用）
```

确认：
- Active: active (running)
- 最近日志无异常退出 / OOM / crash

### 1.2 Timer

```bash
systemctl --user list-timers
```

确认：
- 关键 timer（lottery-fetch / billing / token-observe）在 NEXT 时间内
- LAST 时间合理（非几天前）

### 1.3 端口

```bash
ss -tlnp | grep -E '18789|11434'
```

确认：
- 18789 → openclaw-gateway
- 11434 → ollama（如启用）

### 1.4 资源

```bash
top -bn1 | head -5    # CPU / Load
free -h               # Memory
df -h /               # Disk
```

阈值：

| 指标 | GREEN | YELLOW | RED |
|------|-------|--------|-----|
| CPU | < 50% | 50-80% | > 80% |
| Memory | < 70% | 70-85% | > 85% |
| Disk | < 70% | 70-85% | > 85% |
| Load | < CPU count×1 | < CPU count×2 | > CPU count×2 |

### 输出格式

```text
Runtime:
  Service: 🟢/🟡/🔴
  Timer:   🟢/🟡/🔴
  Port:    🟢/🟡/🔴
  CPU:     🟢/🟡/🔴 (N%)
  Mem:     🟢/🟡/🔴 (N/MB)
  Disk:    🟢/🟡/🔴 (N%)
```

---

## 2. 配置完整性检查

### 2.1 关键配置文件存在性

```bash
ls -la ~/.openclaw/config.yaml
ls -la ~/.openclaw/secrets.yaml        # SecretRef 文件
ls -la ~/.openclaw/workspace/.secrets/ # 外部 secret
ls -la ~/.openclaw/workspace/memory/knowledge/MAINTENANCE-RUNBOOK-v1.0.md  # Runbook 自检
```

确认：
- 文件存在
- 非空（size > 0）
- 权限符合预期

**EVIDENCE CHECK 要求：**
- 记录 `ls -la` 原始输出（包含 size、permission、timestamp）
- 对照 schema 确认每个文件大小合理（非 0 byte）
- 不输出结论"文件存在"而不附具体信息

### 2.2 备份链

```bash
ls -lt ~/.openclaw/backups/ | head -5
```

确认：
- 最近备份时间 < 24h（记录具体时间戳）
- backup-full / audit-backup 正常运行
- 备份文件名日期与当天匹配

**EVIDENCE CHECK 要求：**
- 记录 `ls -lt` 的原始输出（包含时间戳）
- 计算备份时间与当前时间的差值
- exit status 记录：`echo "backup exit: $? $(date)"`

### 2.3 权限

```bash
stat -c '%a %n' ~/.openclaw/workspace/.secrets/push-gate.json
stat -c '%a %n' ~/.openclaw/secrets.yaml
```

确认：
- secret 文件 0600
- config.yaml 0644

### 2.4 SecretRef

```bash
# 若 openclaw config secret list 可用则使用
# 否则直接检查文件内容是否包含硬编码 token
grep -n 'apiKey:' ~/.openclaw/config.yaml
grep -n 'secretRef\|keyRef' ~/.openclaw/config.yaml
```

确认：
- unresolved = 0（所有 secretRef 有对应 secrets.yaml 条目）
- 无硬编码 API key（配置文件内不应出现明文 token）
- python3 验证：`python3 -c "import yaml; c=yaml.safe_load(open('~/.openclaw/config.yaml')); ..."`

### 2.5 Pipeline Evidence

检查 cron 任务执行证据。cron 执行不等于任务成功：

```bash
echo "=== 任务最新执行时间戳 ==="
stat ~/.openclaw/token_observe.jsonl | grep Modify

echo "=== Governance Pipeline 日志 ==="
tail -3 ~/.openclaw/workspace/memory/data/system/governance-pipeline.log 2>&1

echo "=== 最近 cronjob mail ==="
ls -lt /var/mail/"$(whoami)" 2>/dev/null && tail -5 /var/mail/"$(whoami)" 2>/dev/null
```

确认：
- token_observe.jsonl 修改时间 < 1h（每小时更新）
- governance-pipeline.log 存在且有最近记录
- cron mail 无异常错误

**EVIDENCE CHECK：**
- 记录 `stat` 输出的具体时间戳
- 对比当前时间计算延迟
- 如果日志不存在，分类为 YELLOW（观察项），不提交自动修复

### 输出格式

```text
Config:
  Files:     🟢/🟡/🔴
  Backup:    🟢/🟡/🔴 (last: 2026-07-20 03:00, age: 19h)
  Perms:     🟢/🟡/🔴
  Secrets:   🟢/🟡/🔴 (unresolved: 0, hardcoded: 0)
  Pipeline:  🟢/🟡/🔴
```

---

## 3. 文件系统 / Namespace 合规检查

### 3.1 Memory 命名空间存在性

```bash
ls -d ~/.openclaw/workspace/memory/{state,events,facts,preferences,knowledge,cache} 2>&1
```

确认：
- 核心 namespace 全部存在
- 无根目录散落文件

### 3.2 Ownership 检查

```bash
ls ~/.openclaw/workspace/memory/events/huo/
ls ~/.openclaw/workspace/memory/events/jin/
```

确认：
- huo/ ← 仅燃🔥事件
- jin/ ← 仅烬🔥事件
- 无交叉写入

### 3.3 Writer 合规

检查 `memory/data/system/` 下写入者：

```bash
ls -la ~/.openclaw/workspace/memory/data/system/
```

确认：
- tg-build-log.jsonl（TG 审计日志，允许）
- governance-pipeline.log（Worker，允许）
- 无未注册 writer 写入

### 3.4 Observations 目录检查（Phase 8 组件）

```bash
ls -la ~/.openclaw/workspace/memory/data/system/observations/ 2>&1
```

确认规则（应用 Missing ≠ Broken）：
- 不存在 → YELLOW（Phase 8 设计存在但未部署，非故障）
- 存在但有缺失文件 → 🟡（观察项，不自动填充）
- 分类注明：`Missing Artifact — Phase 8 未部署`

### 输出格式

```text
Filesystem:
  Namespace:   🟢/🟡/🔴
  Ownership:   🟢/🟡/🔴
  Writer:      🟢/🟡/🔴
  Phase8 Obs:  🟡/🟢 (Pending Implementation / Missing Artifact)
```

---

## 4. Governance 冻结状态检查

### 4.1 冻结契约存在性

| 契约 | 路径 | 期望状态 |
|------|------|----------|
| Architecture Milestones | `state/huo/ARCHITECTURE.md` | 🔒 FROZEN |
| Freeze Contract | `state/huo/FREEZE-CONTRACT.md` | 🔒 FROZEN |
| Writer Boundary | `state/huo/MEMORY-WRITER-BOUNDARY.md` | 🔒 FROZEN |
| Ownership Contract | `state/huo/MEMORY-OWNERSHIP-CONTRACT.md` | 🔒 FROZEN |
| Runtime Context | `state/huo/ARCHITECTURE.md §Runtime Context Layer` | 🔒 FROZEN |
| TG Build Boundaries | `knowledge/TG-BUILD-BOUNDARIES.md` | 🔒 FROZEN |

### 4.2 Phase 进度检查

检查各 Phase 的实际文档状态与期望状态：

```bash
grep -n 'Status:' ~/.openclaw/workspace/memory/state/huo/PHASE-*.md 2>/dev/null
grep -n 'Status:' ~/.openclaw/workspace/memory/state/huo/PHASE-7.5-INTEGRITY-FREEZE.md
grep -n 'Status:' ~/.openclaw/workspace/memory/state/huo/PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md
```

确认：
- Phase 7.5 标记为 FROZEN 或 CLOSED
- Phase 8 标记为设计阶段（非故障，即使实现不存在）

### 4.3 未登记架构变化

对照 ARCHITECTURE.md 检查：
- 是否有新 service 未在"运行中组件"表中登记
- 是否有新 namespace 未被任何契约覆盖
- 是否有新 bypass path

**发现未登记变化 → 必须 escalate，不自动修复。**

### 输出格式

```text
Governance:
  Contracts:   🟢/🟡/🔴
  Phase7.5:    🔒 FROZEN
  Phase8:      🟡 Design Only (Pending Implementation)
  Drift:       🟢/🟡/🔴 (发现 X 项未登记)
```

---

## 5. Identity 路由检查

### 5.1 当前身份确认

```bash
# 对照入口判断：
# shell / webchat → 燃🔥
# telegram        → 烬🔥
```

### 5.2 读取范围确认

| 身份 | 可读 | 禁止 |
|------|------|------|
| 燃🔥 | 全部 | 无 |
| 烬🔥 | `knowledge/`, `workspace/` | `state/huo/`, `events/huo/`, `state/` |

### 5.3 写入边界确认

对应 TG-BUILD-BOUNDARIES L0/L1/L2 三级判定。

### 输出格式

```text
Identity:
  Current:     燃🔥/烬🔥
  Route:       🟢/🟡/🔴
  Bound:       🟢/🟡/🔴
```

---

## 6. 审计链检查

### 6.1 TG Build Log

```bash
tail -5 ~/.openclaw/workspace/memory/data/system/tg-build-log.jsonl
```

确认：
- 最近记录时间合理
- 无 L2 越权静默执行
- escalation 记录有对应处理

### 6.2 Token Observe

```bash
echo "=== 最近 3 条 token 观测 ==="
tail -3 ~/.openclaw/token_observe.jsonl

echo "=== 今日观测数 ==="
grep -c "$(date +%Y-%m-%d)" ~/.openclaw/token_observe.jsonl
```

确认：
- 每小时有采集点（24h 应约 24 条）
- 无异常 token 增长（对比上一小时）

### 6.3 事件链

```bash
ls -lt ~/.openclaw/workspace/memory/events/huo/ | head -5
```

确认：
- 事件文件持续追加
- 时间连续，无断裂

### 输出格式

```text
Audit:
  TG Log:      🟢/🟡/🔴
  Token:       🟢/🟡/🔴 (今日 N 条)
  Events:      🟢/🟡/🔴
```

---

## 7. 报告输出

### 7.1 汇总状态

```text
┌─────────────────────────────────────┐
│        Maintenance Report           │
├─────────────────────────────────────┤
│ Runtime:     🟢                     │
│ Config:      🟢/🟡/🔴              │
│ Filesystem:  🟢/🟡/🔴              │
│ Governance:  🟢/🟡/🔴              │
│ Identity:    🟢                     │
│ Audit:       🟢/🟡/🔴              │
├─────────────────────────────────────┤
│ Overall:     🟢/🟡/🔴              │
└─────────────────────────────────────┘
```

### 7.2 发现列表（Governance Gap Classification）

每条发现必须标注类型和状态，格式统一：

```
<GREEN|YELLOW|RED|UNKNOWN> [🏗Gap|⚖️Violation|🔍Obs] <项> — <说明>
  证据: <原始证据引用>
  判定: <为什么归入这个发现类型和状态>
  行动: <补规则 / 修复 / 观察 / escalate>
```

### 7.3 行动列表

按分类列出需要处理的项目：

```
Actions:
- [NONE] 当前无需修复         ← 全部 GREEN
- [OBSERVE] 标记观察项        ← 含 YELLOW 项
- [CONFIRM] 需要终端确认      ← 含 UNKNOWN 或需决策项
- [FIX] 需要处理              ← 含 RED 项
```

**禁止：自动执行 Action，必须输出到报告等待指令。**

---

## 8. 治理缺口分类（Governance Gap Classification）

**审计的目标不是发现异常，而是验证治理能力完整性。任何缺口必须完成根因定位；若根因为治理定义缺失，则优先补齐治理定义，再执行修复。**

治理审计的三个核心发现类型，取代传统 Bug/Warning/Observation 模型：

| 类型 | 含义 | 动作 |
|:----:|------|------|
| 🏗 Governance Gap | 规则/边界/契约缺失 | 补齐治理定义 → 验证 → 修复 |
| ⚖️ Governance Violation | 已有规则但运行偏离 | 定位责任 → 恢复一致性 |
| 🔍 Valid Observation | 行为符合设计，需长期观测 | 记录 → 持续观察 |

### 8.0 审计判断流程（Evidence First Audit Procedure）

**未知不是观察理由。未知本身就是需要调查的状态。**

审计不靠经验推断设计意图。检查前必须先查阅已批准的设计来源。

```
1. 收集事实                         ← 运行时证据，非模型推断
2. 查阅权威设计来源                 ← 契约 / 设计文档 / schema / 源码
3. 比对实际状态与设计定义           ← 差异即发现
4. 判断类型：
   ┌───────────────────────┐
   │ 设计是否存在？         │
   ├───────────┬───────────┤
   │ 有         │ 无        │
   ↓           ↓           │
   验证一致性   治理缺口     │
   ├───────────┴───────────┤
   │ 一致 → Valid Obs      │
   │ 偏离 → Violation      │
   └───────────────────────┘
5. 制定治理动作
6. 执行修复或补齐规则
7. 验证闭环
```

**禁止跳过第 2 步。** 设计未知不能作为观察理由，必须先查设计来源。

**缺失设计定义本身也是治理缺口（Governance Gap），不能永久搁置。**

### 8.0.1 根因追溯（Root Cause Analysis）

每个 Governance Gap 必须完成根因定位。禁止停留在表象层。

```yaml
root_cause:
  type:
    - missing_contract      责任层: Governance Layer
    - contract_violation    责任层: Governance Layer
    - implementation_drift  责任层: Implementation Layer
    - lifecycle_missing     责任层: Data Contract / Pipeline
    - ownership_unclear     责任层: Identity / Ownership
```

判断顺序：

```
表象问题
 ↓
设计/契约是否存在？
 ├── 有 → contract_violation 或 implementation_drift
 └── 无 → missing_contract
          ↓
          lifecycle 是否存在？
           ├── 无 → lifecycle_missing
           └── 有 → 继续追
```

禁止模式：

```
发现：没有规则
结论：无法判断
处理：继续观察
```

正确：

```
发现：没有规则
判断：missing_contract（治理能力缺失）
动作：建立规则
然后：重新验证系统
```

### 8.1 状态分级（5 级）

状态等级仍沿用，但含义映射到治理发现类型：

| 状态 | 含义 | 映射到发现类型 | 后续行动 |
|:----:|------|:-------------:|----------|
| 🟢 GREEN | 正常 | Valid Observation | 无动作 |
| 🟡 YELLOW | 需关注 | Governance Gap / Violation / Valid Obs | 见 8.3 分层 |
| 🔴 RED | 需要处理 | Governance Violation（严重） | 报告后等待授权 |
| ⚪ UNKNOWN | 升级确认 | 无法通过已有来源判定 | escalate |

### 8.2 常见分类判定指南

**GREEN：**

```
- 服务 active (running)
- 资源阈值 GREEN 区间
- 配置文件存在且权限正确
- SecretRef unresolved = 0
- 冻结契约全部 FROZEN
```

**Governance Gap（YELLOW-A）：**

```
- 系统出现行为，但设计体系没有完整描述如何处理
- 规则不存在 / 边界未定义 / 契约覆盖不足
- 生命周期缺失 / 验证机制不足
```

**Governance Violation（YELLOW-B / RED）：**

```
- 已有明确规则，但运行违反
- 契约要求必须有，实际不存在
- 配置文件权限 777
- 身份路由不匹配
- 冻结契约被解冻或修改
```

**Valid Observation（YELLOW-C）：**

```
- 行为存在，但符合设计定义
- 性能波动在设计阈值内
- 无足够证据判断的类型（暂挂）
```

**UNKNOWN：**

```
- 观察到新组件但无法确定其 ownership
- 存在多个矛盾证据源
- 无已批准设计来源可查阅
```

### 8.3 YELLOW 内部分层（按发现类型）

| 分层 | 发现类型 | 含义 | 动作 |
|:----:|:--------:|------|------|
| YELLOW-A | 🏗 Governance Gap | 规则缺失 — 需补齐治理定义 | 补契约/规则/边界 → 验证 |
| YELLOW-B | ⚖️ Governance Violation | 执行偏差 — 有规则未遵循 | 定位责任 → 恢复一致性 |
| YELLOW-C | 🔍 Valid Observation | 行为符合设计，需长期观测 | 记录 → 持续观察 |

**YELLOW-C 仅适用于：** 已查阅设计来源，设计确实允许当前行为，但需要长期验证是否属于预期波动。

**YELLOW-C 不适用于：** 设计未定义、设计来源不可达、未查阅设计来源。

**YELLOW-C 转 A/B 的条件：** 当观察积累足够证据确认属于规则缺失或执行偏差时，应升级处理，不永久搁置。

### 8.4 Missing Artifact 分类规则

| 场景 | 分类 | 判定依据 |
|------|------|----------|
| 设计存在，实现不存在 | 🟡 YELLOW | Missing ≠ Broken |
| Contract 要求必须有，不存在 | 🔴 RED | 架构违约 |
| 临时/缓存/观测数据，不存在 | 🟢 GREEN | 可选组件，不要求存在 |
| 新要求但未登记在任何契约中 | ⚪ UNKNOWN | 需确认是否属于架构变更 |

---

## 9. 维护行动边界（Maintenance Action Boundary）

### 9.1 行动等级

| 等级 | 权限 | 内容 |
|------|------|------|
| L0 自动 | ✅ 无需确认 | 采集、检查、报告、日志轮转、缓存清理 |
| L1 需确认 | ⏳ 等待指令 | 删除、修改、部署、迁移、重新采集 |
| L2 禁止自动 | 🚫 仅终端 | 修改冻结文档、变更 writer 权限、修改 runtime 配置、变更身份规则 |

### 9.2 修复规则明细

**L0 自动允许：**

```
日志轮转（log 裁剪 / 归档，保留最近 N 天）
临时缓存清理（__pycache__ / memory/cache/ 的临时文件）
重新采集状态（非修改，仅 re-read）
生成报告（格式化输出，不写回系统）
```

**L1 必须确认后执行：**

```
删除任何文件（含 session 文件、缓存、日志）
修改 writer 路径或权限
部署新脚本或 service
迁移 namespace 结构
创建任何目录/文件（除非是本手册明确定义的必需组件）
```

**L2 禁止自动（仅终端）：**

```
修改任何 FROZEN 文档
变更 writer 权限
修改 runtime 服务/配置
变更身份路由规则
解冻任何 Phase 6 契约
回滚备份
```

### 9.3 自动修复禁止清单

以下情景即使看起来"明显正确"，也**禁止自动执行**，必须报告等待确认：

```
发现异常进程 → 自动 kill
发现缺失目录 → 自动 mkdir
发现错误权限 → 自动 chmod
发现配置缺失 → 自动写入
发现 session 文件过多 → 自动删除
发现日志过大 → 自动 truncate
```

原因：任何自动修复都可能：
- 覆盖用户意图
- 破坏正在进行的操作
- 触发级联故障
- 掩盖真实问题

---

## 附录 A：评估脚本模板

```bash
#!/bin/bash
# maintenance-check.sh — 本手册的自动化版本
# 不进行任何修改操作，只输出证据供分类

echo "=== Runtime ==="
systemctl --user is-active openclaw ollama 2>&1
free -h
df -h /

echo "=== Config ==="
ls -la ~/.openclaw/config.yaml
ls -lt ~/.openclaw/backups/ | head -3
stat -c '%a %n' ~/.openclaw/workspace/.secrets/*.json 2>/dev/null

echo "=== Filesystem ==="
ls -d ~/.openclaw/workspace/memory/{state,events,facts,preferences,knowledge,cache} 2>&1

echo "=== Governance ==="
grep -n 'Status:' ~/.openclaw/workspace/memory/state/huo/PHASE-*.md 2>/dev/null

echo "=== Audit ==="
tail -3 ~/.openclaw/token_observe.jsonl 2>/dev/null || echo "token_observe: MISSING (YELLOW)"
```

---

## 附录 B：与 TOOLS.md 的引用关系

本手册定义**如何执行维护**（流程）。
TOOLS.md 定义**系统架构边界**（审计四层、Extension Boundary、Memory Semantic Namespace）。
执行维护时应交叉引用 TOOLS.md 中的结构审计四层作为检查清单。

---

## Version 记录

| Version | Date | Change | Author |
|---------|------|--------|--------|
| v1.0-draft | 2026-07-20 | 初始创建，7 步检查流程 | 龙哥 → 燃🔥 |
| v1.0-draft-p3 | 2026-07-20 | Phase 3 修正：Missing ≠ Broken, Detection ≠ Repair, 四级分类, 行动边界, Config/Pipeline 证据增强 | 龙哥 → 燃🔥 |
| v1.0-frozen | 2026-07-20 | Phase 4 FROZEN。冻结约束写入文档头。后续修改需解冻流程。 | 燃🔥 |
| v1.0-frozen-audit-fix | 2026-07-20 | 审计修正：Evidence First Audit Procedure 加入 §8.0；YELLOW-A/B/C 内部分层加入 §8.3。不修改核心检查流程、不修改 4 级分类，不修改 L0/L1/L2 边界。 | 龙哥 → 燃🔥 |
| v1.0-frozen-root-cause | 2026-07-20 | 根因追溯：Root Cause Analysis 加入 §8.0.1。审计最高原则写入。 | 龙哥 → 燃🔥 |

---

*本手册位于 `memory/knowledge/`（共享命名空间）。不替代 `memory/state/huo/` 中的治理契约，不视为系统真相源。*
