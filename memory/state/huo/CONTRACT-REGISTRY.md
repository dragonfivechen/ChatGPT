# CONTRACT-REGISTRY v1.0

> 契约注册表 — M0 META-CONTRACT 的管理索引
> 目的: META-CONTRACT 通过此文件稳定识别所有已纳入治理体系的契约对象
> 管理原则: 只登记身份，不定义规则

---

## 已登记契约

| 文件名 | 等级 | Parent | Scope | Owner | 状态 | 声明块 |
|--------|:----:|--------|-------|:-----:|:----:|:------:|
| `META-CONTRACT.md` | M0 | — | contract governance | 燃🔥 | active | ✅ |
| `CONTRACT-LEVEL-CLASSIFICATION.md` | L0 | — | all contracts | 燃🔥 | active | ✅ |
| `FREEZE-CONTRACT.md` | L0 | — | system freeze rules | 燃🔥 | active | ✅ |
| `FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md` | L1 | FREEZE-CONTRACT | all functional modules | 燃🔥 | active | ✅ |
| `TOOL-CALL-GATEWAY-CONTRACT.md` | L1 | FREEZE-CONTRACT | system-wide tool call flow | 燃🔥 | active | ✅ |
| `EVENT-SOURCE-CONTRACT.md` | L1 | FREEZE-CONTRACT | event truth source | 燃🔥 | active | ✅ |
| `EVIDENCE-CONTRACT.md` | L1 | FREEZE-CONTRACT | analysis evidence governance | 燃🔥 | active | ✅ |
| `DECISION-CONTRACT.md` | L1 | FREEZE-CONTRACT | observation-to-action decision rules | 燃🔥 | active | ✅ |
| `CHANGE-CONTRACT.md` | L1 | DECISION-CONTRACT | change record and verification | 燃🔥 | active | ✅ |
| `CREDENTIAL-ACCESS-CONTRACT.md` | L1 | FREEZE-CONTRACT | credential operations | 燃🔥 | frozen | ✅ |
| `CONFIG-SOURCE-CONTRACT.md` | L1 | FREEZE-CONTRACT | config truth source | 燃🔥 | proposal | ✅ |
| `MEMORY-OWNERSHIP-CONTRACT.md` | L1 | FREEZE-CONTRACT | memory namespace ownership | 燃🔥 | active | ✅ |
| `PLUGIN-CAPABILITY-CONTRACT.md` | L1 | FREEZE-CONTRACT | plugin capability model | 燃🔥 | active | ✅ |
| `PROVIDER-CAPABILITY-CONTRACT.md` | L1 | FREEZE-CONTRACT | provider/model capability governance | 燃🔥 | active | ✅ |
| `REASONING-ISOLATION-CONTRACT.md` | L1 | FREEZE-CONTRACT | reasoning content isolation | 燃🔥 | active | ✅ |
| `CONTEXT-PROJECTION-CONTRACT.md` | L1 | FREEZE-CONTRACT | context projection for LLM | 龙哥 | active | ✅ |
| `FACT-SOURCE-CONTRACT.md` | L1 | FREEZE-CONTRACT | fact truth source | 燃🔥 | proposal | ✅ |
| `PHASE-7.1-AUDIT-CONTRACT.md` | L1 | FREEZE-CONTRACT | phase contract verification | 燃🔥 | frozen | ✅ |
| `PRIVILEGE-CONTROL-CONTRACT.md` | L1 | FREEZE-CONTRACT | privileged operations (root/sudo/credential) | 燃🔥 | active | ✅ |
| `LOTTERY-CAPABILITY-CONTRACT.md` | L2 | FUNCTION-MODULE-BASELINE-CHECK | lottery module capability | 燃🔥 | active | ✅ |
| `LOTTERY-SOURCE-CONTRACT.md` | L2 | FUNCTION-MODULE-BASELINE-CHECK | lottery data source | 燃🔥 | active | ✅ |
| `LOTTERY-PREDICTION-CONTRACT.md` | L2 | FUNCTION-MODULE-BASELINE-CHECK | lottery prediction boundary | 燃🔥 | active | ✅ |
| `LOTTERY-STATISTICS-CONTRACT.md` | L2 | FUNCTION-MODULE-BASELINE-CHECK | lottery statistics boundary | 燃🔥 | active | ✅ |
| `LOTTERY-WORKER-DIRECTORY-CONTRACT.md` | L3 | FUNCTION-MODULE-BASELINE-CHECK | lottery worker directory implementation | 燃🔥 | active | ✅ |
| `TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT.md` | L2 | FUNCTION-MODULE-BASELINE-CHECK | TG model module | 燃🔥 | active | ✅ |
| `TRADING-RUNTIME-V0.5-ARCH.md` | L2 | FUNCTION-MODULE-BASELINE-CHECK | paper trading runtime | 燃🔥 | frozen | ✅ |
| `TG-IMPLEMENTATION-ALIGNMENT-CONTRACT.md` | L3 | FUNCTION-MODULE-BASELINE-CHECK | TG module construction | 燃🔥 | active | ✅ |
| `DIAGNOSTICS-BEHAVIOR-LAYER.md` | L2 | FREEZE-CONTRACT | cross-agent behavior diagnostics | 燃🔥 | active | ✅ |
| `TG-BEHAVIOR-DATA-CONTRACT.md` | L2 | FREEZE-CONTRACT | TG behavior data isolation | 燃🔥 | active | ✅ |

---

## Pending（待确认身份的历史文件）

以下文件名含 `-CONTRACT` 但尚未经 META-CONTRACT 五问分类，暂未纳入契约治理体系：

| 文件名 | 初步判断 | 下一步 |
|--------|----------|--------|
| `CONFIG-SOURCE-CONTRACT.md` | ✅ 已迁移 → L1 proposal | P1 第一批完成 |
| `CONTEXT-PROJECTION-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第二批完成 |
| `CREDENTIAL-ACCESS-CONTRACT.md` | ✅ 已迁移 → L1 frozen | P1 第一批完成 |
| `EVENT-SOURCE-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第一批完成 |
| `FACT-SOURCE-CONTRACT.md` | ✅ 已迁移 → L1 proposal | P1 第二批完成 |
| `LOTTERY-CAPABILITY-CONTRACT.md` | ✅ 已迁移 → L2 active | Lottery 批完成 |
| `LOTTERY-PREDICTION-COMBINATION-CONTRACT.md` | ❌ SPECIFICATION | Lottery 批排除 |
| `LOTTERY-PREDICTION-CONTRACT.md` | ✅ 已迁移 → L2 active | Lottery 批完成 |
| `LOTTERY-PREDICTION-DIVERSITY-CONTRACT.md` | ❌ SPECIFICATION | Lottery 批排除 |
| `LOTTERY-PREDICTION-ENGINE-CONTRACT.md` | ❌ SPECIFICATION | Lottery 批排除 |
| `LOTTERY-PREDICTION-ROLE-CONTRACT.md` | ❌ SPECIFICATION | Lottery 批排除 |
| `LOTTERY-PREDICTION-STRATEGY-CONTRACT.md` | ❌ SPECIFICATION | Lottery 批排除 |
| `LOTTERY-SOURCE-CONTRACT.md` | ✅ 已迁移 → L2 active | Lottery 批完成 |
| `LOTTERY-SOURCE-RETRY-CONTRACT.md` | ❌ SPECIFICATION | Lottery 批排除 |
| `LOTTERY-STATISTICS-CONTRACT.md` | ✅ 已迁移 → L2 active | Lottery 批完成 |
| `LOTTERY-WORKER-DIRECTORY-CONTRACT.md` | ✅ 已迁移 → L3 active | Lottery 批完成 |
| `MEMORY-OWNERSHIP-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第二批完成 |
| `METADATA-CONTRACT.md` | ❌ SPECIFICATION — 字段格式规范，非治理规则 | P1 排除 |
| `PLUGIN-CAPABILITY-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第二批完成 |
| `PROVIDER-CAPABILITY-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第二批完成 |
| `REASONING-ISOLATION-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第二批完成 |
| `TOOL-CALL-GATEWAY-CONTRACT.md` | ✅ 已迁移 → L1 active | P1 第一批完成 |
| `PHASE-7.1-AUDIT-CONTRACT.md` | ✅ 已迁移 → L1 audit_verification | P1 第三批完成 |

---

## 非契约文件（不纳入）

以下文件属于设计笔记、方案、报告、证据，不含 `-CONTRACT` 后缀，按原有分类管理：

```
2026-07-18-MODULE-STATUS.md
ARCHITECTURE.md
BASELINE-COMPLETENESS-SUPPLEMENT.md  (L4 evidence)
BYPASS-REGISTER-v1.0.md
CANDIDATE-IDENTITY-RULE.md
capability_audit_report.md
CAPABILITY-REGISTRY.md
context-projection-schema-design.md
FUTURES-SIM-V0.1-ARCH.md
MEMORY-WRITER-BOUNDARY.md
MODEL-CONSTRAINT-MAP.md
PHASE-6.2-AUDIT-REPORT.md
PHASE-6.3.2-EVENT-INTEGRATION-DESIGN.md
PHASE-6.3.3-RUNTIME-INTEGRATION-DESIGN.md
PHASE-6.3-VALIDATION.md
PHASE-6.4.1-SCHEMA-DESIGN.md
PHASE-6.4.2-RUNTIME-INTEGRATION-DESIGN.md
PHASE-6.4.3-VALIDATION.md
PHASE-7.2-BOUNDARY-MATRIX.md
PHASE-7.3.2-GAP-DECISION-FRAMEWORK.md
PHASE-7.3.3-PLUGIN-BOUNDARY-DECISION.md
PHASE-7.3-CLOSURE-REPORT.md
PHASE-7.4.1-VERIFICATION-SCOPE-LOCK.md
PHASE-7.4.2-RUNTIME-VERIFICATION-STAGE1.md
PHASE-7.4.2-RUNTIME-VERIFICATION-STAGE2.md
PHASE-7.4.2-RUNTIME-VERIFICATION-STAGE3.md
PHASE-7.4-RUNTIME-VERIFICATION-REPORT.md
PHASE-7.5-INTEGRITY-FREEZE.md
PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md
PROVIDER-CAPABILITY-REGISTRY-DESIGN.md
provider-capability-schema-design.md
provider-capability-schema-mapping.md
report_pipeline_v2.md
RUNTIME-ENFORCEMENT-DESIGN.md
RUNTIME-ENFORCEMENT-VALIDATION.md
SCAN-BLUEPRINT-v2.md
```

---

## 注册表维护规则

| 操作 | 要求 |
|------|------|
| 新增契约 | 经 META-CONTRACT 五问分类后，添加一行 |
| 契约状态变更 | 更新状态列（active / frozen / archived） |
| 契约归档 | 移入 archived 区段 |
| Pending 判定 | 逐文件完成后移入"已登记"或"非契约" |

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始注册表，7 个核心契约已登记，23 个 Pending 待分析 |
| v1.0 | 2026-07-21 | P1 第一批迁移完成：TOOL-CALL-GATEWAY, CREDENTIAL-ACCESS, EVENT-SOURCE, CONFIG-SOURCE → L1 |
| v1.0 | 2026-07-21 | P1 第二批迁移完成：MEMORY-OWNERSHIP, PLUGIN-CAPABILITY, PROVIDER-CAPABILITY, REASONING-ISOLATION, CONTEXT-PROJECTION, FACT-SOURCE → L1. METADATA 排除为 SPECIFICATION |
| v1.0 | 2026-07-21 | P1 第三批完成：PHASE-7.1-AUDIT-CONTRACT → L1 audit_verification (frozen) |
| v1.0 | 2026-07-21 | Lottery 批完成：5 Contract (4 L2 + 1 L3), 6 SPECIFICATION 排除 |
| v1.0 | 2026-07-21 | 新增 PRIVILEGE-CONTROL (L1 A3)，META-CONTRACT v1.2 Q7 框架 |
