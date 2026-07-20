# Candidate Identity Rule v1.0

**Governance Gap Closure — GAP-003**
**Date:** 2026-07-20
**Source:** FREEZE-CONTRACT.md § 审计闭环 + LOTTERY-SOURCE-CONTRACT.md §8 (Event Dedup Rule pattern)

---

## §1 Purpose

Define a stable identity for governance rule candidates, replacing content-based dedup with identity-based dedup. Ensure each unique feedback signal produces at most one active candidate.

## §2 Candidate Identity Formula

```
candidate_identity = candidate:{source_event_hash}:{rule_type}:{category}

其中:
  source_event_hash = SHA256(source_event_text)[:16]
  rule_type         = correction_explicit / correction_implicit / principle
  category          = interaction / project / architecture
```

## §3 Generation Flow

```
反馈事件到达
 ↓
提取规则文本
 ↓
计算 candidate_identity
 ↓
memory/candidates/ 中 identity 已存在？
 ├── 是 → 更新已有候选（命中数+1，置信度取 max）
 └── 否 → 创建新候选（identity 写入候选文件 metadata）
```

### vs 旧的流程

```
旧: 提取规则文本 → 内容相似度比较 → 去重
新: 提取规则文本 → 计算身份 → 身份存在？ → 更新/创建
```

## §4 Candidate File Format

```json
{
  "id": "rule-candidate-{date}-{seq}",
  "identity": "candidate:a1b2c3d4e5f6a7b8:principle:architecture",
  "source_event_hash": "a1b2c3d4e5f6a7b8",
  "rule_type": "principle",
  "category": "architecture",
  "candidate": "...",
  "confidence": 0.85,
  "hit_count": 3,
  "score": 0.825,
  "state": "pending"
}
```

## §5 Existing Candidate Migration

Scan existing `memory/candidates/rule-candidate-*.json`:

- Compute identity for each
- Add `identity` field if missing
- Remove true duplicates (same identity, same content)
- Merge hit_count for same identity

## §6 Closure Criteria

```
- All existing candidates have identity field
- Re-running governance pipeline on same events:
  - New candidates created: 0 (all deduped by identity)
  - Existing candidates updated (hit_count incremented)
- Zero duplicate candidates with different IDs for the same fingerprint
```
