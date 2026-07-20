# Contract Observations — 2026-07-20

Source: 契约检查 (Contract Check) — 冻结后首次治理基线核查
Cross-reference: MAINTENANCE-RUNBOOK-v1.0 🔒

---

## YELLOW-001 — Reasoning Contract Filename Drift

| Field | Value |
|-------|-------|
| Type | 🏗 **Governance Gap** |
| Contract | Phase 6.1 Reasoning Isolation |
| Issue | PHASE-7.5 引用 `PHASE-6.1-REASONING-ISOLATION-CONTRACT.md`，实际文件 `REASONING-ISOLATION-CONTRACT.md` |
| Design defined? | 引用路径规范存在但未对齐 |
| Impact | 引用路径不一致，内容完整存在 |
| Classification | 🟡 YELLOW-A — 规则/引用一致性缺口 |
| Note | 非内容缺失，非安全问题。属引用路径一致性问题。 |
| Action | 补齐 Contract Reference Alignment Rule → 更新引用路径 → 保留审计记录 |

---

## YELLOW-002 — Lottery Dedup Rule Missing

| Field | Value |
|-------|-------|
| Type | 🏗 **Governance Gap** |
| Contract | LOTTERY-SOURCE-CONTRACT v1.0 |
| Issue | DLT 2026080 被写入 6 次。合同定义了源清单、信任模型、回退策略，但缺少 deduplication 条款。 |
| Design defined? | 有源契约，但事件唯一性约束未定义 |
| Impact | 数据冗余，不阻塞流程，事件源可恢复。 |
| Classification | 🟡 YELLOW-A — 治理缺口（契约覆盖不足） |
| Note | ❌ 非 RED 数据污染。规则缺失，不是数据源不可恢复。 |
| Action | 补 LOTTERY-SOURCE-CONTRACT dedup 条款 → 执行清理 → 验证 |

---

## YELLOW-003 — Governance Candidate Regeneration

| Field | Value |
|-------|-------|
| Type | 🏗 **Governance Gap** |
| Component | Governance Pipeline (memory_governance_worker.py + memory_dedup.py) |
| Issue | rule-candidate-001 + 004 (score=0.825) 重复生成 48 轮 |
| Terminal State | 0 pending, 23 rules, 19 rejected, 7 promoted |

**Evidence First 核查:**

| 核查项 | 结果 |
|--------|------|
| candidate 唯一标识定义 | ❌ 未定义 — 无 fingerprint 或 source-event 映射 |
| 去重策略 | 内容相似度 (SequenceMatcher > 0.55) + 关键词重叠 (> 0.4) |
| 候选与源事件绑定 | ❌ 未定义 — 每轮重新扫描事件 → 新生成候选文件 |
| 幂等性设计 | ❌ 未定义 — 同一事件每轮产生不同 candidate ID |

**判定:**

代码实现了内容去重但未定义候选身份。同一事件每轮扫描 → 新 candidate ID → 内容相似 → 合并 → 升级。合并后原候选被标记 duplicate，但下一轮重新生成。

```
设计未定义 candidate identity / source-event fingerprint
 ↓
Governance Gap
 ↓
需补充：candidate identity 定义 → lifecycle → fingerprint → 源事件映射
```

| Action | 补设计规则 → 实现 → 验证 |

---

## Gap Closure Summary

| Gap | Type | Root Cause | Responsibility Layer | Status |
|:---:|:----:|-----------|:-------------------:|:------:|
| GAP-001 | 🏗 Governance Gap | missing_contract — 缺少 Contract Reference Alignment 约束 | Governance Layer | ✅ CLOSED |
| GAP-002 | 🏗 Governance Gap | missing_contract — Source Event Identity 未定义 | Data Contract Layer | ✅ CLOSED |
| GAP-003 | 🏗 Governance Gap | lifecycle_missing — Candidate Identity 生命周期缺失 | Memory Governance Pipeline | ✅ CLOSED |

### GAP-001 Verification

**Root Cause:** 缺少 Contract Reference Alignment 约束（`missing_contract`）

**Rule added:** CONTRACT-REFERENCE-ALIGNMENT-RULE.md
```
Rule:  CONTRACT-REFERENCE-ALIGNMENT-RULE.md
Scan:  Zero MISMATCH references (PHASE-7.5 line 25 fixed)
File:  REASONING-ISOLATION-CONTRACT.md @ 11614 bytes
```

### GAP-002 Verification

**Root Cause:** Source Event Identity 未定义（`missing_contract` — Data Contract Layer）

```
Rule:  LOTTERY-SOURCE-CONTRACT.md §8 Event Uniqueness Constraint
Index: events/lottery/dedup-index.json (8 fingerprints, 4 with duplicates)
Test:  Re-import → accepted(1st) / deduped(2nd) ✅
```

### GAP-003 Verification

**Root Cause:** Candidate Identity 生命周期缺失（`lifecycle_missing` — Memory Governance Pipeline）

```
Rule:  CANDIDATE-IDENTITY-RULE.md
Code:  memory_candidate_extract.py (identity compute + find + migrate)
Data:  27 candidates, 100% with identity, 0 identity duplicates
Test:  Re-scan 7 days → 19 signals matched existing, 0 new candidates
```

### Governance Pipeline Integrity
```
Pipeline dry-run: exit=0
Candidates pending: 0
Rules on file: 23
No regression
```

## Cross-reference

```
FREEZE-CONTRACT 原则验证:

审计识别缺口 → 补齐治理定义 → 修复 → 验证 → 关闭   ✅ 全程
基线架构不扩展                                      ✅ 未新增能力
边界覆盖补齐                                        ✅ 全部在已有契约责任范围内
历史数据不篡改 (events = source of truth)            ✅ 标记不删除
```

## 系统治理状态 (2026-07-20 23:35)

```
Runtime              🟢
Truth Layer          🟢
Memory Governance    🟢
Identity Isolation   🟢
Freeze Contract      🟢
Maintenance          🟢
Governance Gap       🟢 (3 items — ✅ CLOSED)
```

Governance Gap Closure complete. All three gaps resolved within freeze boundary.

**Audit trail:**
- `CONTRACT-REFERENCE-ALIGNMENT-RULE.md` — 新增
- `LOTTERY-SOURCE-CONTRACT.md` — §8 新增
- `CANDIDATE-IDENTITY-RULE.md` — 新增
- `memory_candidate_extract.py` — 更新
- `events/lottery/dedup-index.json` — 新增
- `candidates/` — 27 candidates with identity, 2 merged

