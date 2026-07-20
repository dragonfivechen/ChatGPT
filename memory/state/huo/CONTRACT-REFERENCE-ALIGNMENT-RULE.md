# Contract Reference Alignment Rule v1.0

**Governance Gap Closure — GAP-001**
**Date:** 2026-07-20
**Source:** FREEZE-CONTRACT.md § 审计闭环

---

## §1 Purpose

Ensure all cross-references between governance contracts resolve to valid, existing files with consistent naming. Prevent reference drift without modifying contract content.

## §2 Rule

```
Every contract reference must:
1. Resolve to an existing file path
2. Use the exact filename as the target file
3. Be verifiable by: stat(fn) → exists

Exceptions:
- Relative paths within the same directory are preferred
- Absolute paths used only when crossing namespace boundaries
```

## §3 Scope

All `.md` files in `memory/state/huo/` and `memory/knowledge/`.

## §4 Violations

| Severity | Definition | Action |
|----------|------------|--------|
| MISMATCH | Reference filename ≠ actual filename | Fix reference to match actual file |
| BROKEN | Reference points to non-existent file | Restore file or update reference |
| STALE | File exists but reference outdated | Update reference |

## §5 Audit Procedure

```bash
# Scan: for each .md file, extract all [text](path) and backtick references
# Resolve: check if file exists at the referenced path
# Report: list all MISMATCH / BROKEN / STALE items
```

## §6 Closure Criteria

```
- Zero MISMATCH references
- Zero BROKEN references
- Audit record committed
```

---

## Audit Record: GAP-001

| Field | Value |
|-------|-------|
| Issue | PHASE-7.5-INTEGRITY-FREEZE.md line 25 |
| Reference | `PHASE-6.1-REASONING-ISOLATION-CONTRACT.md` |
| Actual file | `REASONING-ISOLATION-CONTRACT.md` |
| Resolution | Fixed reference to match actual filename |
| Result | ✅ CLOSED |
