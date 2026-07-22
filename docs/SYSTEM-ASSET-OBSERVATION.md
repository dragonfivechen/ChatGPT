# System Asset Observation Layer v1.2

> 系统资产观察统计层。对账系统当前存在的资产状态。
> 不参与建设、不参与治理、不参与决策 — 只读、只记录、不修复。

---

## Purpose

```
全系统
  ↓
资产发现
  ↓
分类统计 (deprecated→idle→duplicate→incomplete→frozen→active→unknown)
  ↓
生成 Asset Snapshot
  ↓
建立 baseline
```

## Classification Rules

| Class | Priority | Rule |
|:------|:--------:|:-----|
| deprecated | 1 | archive/, *.bak, pre-*, legacy, shadow/, proof/, snapshot/, resolve/, audit/ |
| idle | 2 | exists + no runtime entry + stale mtime + has replacement |
| duplicate | 3 | stem collision across directories, root vs module overlap |
| incomplete | 4 | proposal, draft, TODO, test-contract, unverified phase |
| frozen | 5 | CONTRACT-REGISTRY status=frozen, PHASE_STATUS=FROZEN |
| active | 6 | confirmed running service/timer, active contract, fresh data |
| unknown | 7 | cannot determine status |

**Core: unknown ≠ active**

---

## Asset Snapshot: ASSET-SNAPSHOT-002

> **Scan Time:** 2026-07-22 10:35 CST
> **Observer:** scripts/asset_observer.py v1.2
> **Classification Rule:** v1.1
> **Scope:** FULL_SYSTEM

### Inventory

| Category | Count |
|:---------|:-----:|
| 📄 docs | 7 |
| 📜 contracts | 41 |
| 📑 phase docs | 18 |
| 📋 state docs | 23 |
| 🧩 modules | 3 |
| ⚡ scripts | 51 |
| 🖥 services | 19 |
| ⏱ timers | 17 (19 active) |
| 💾 data sources | 45 |
| ⚙️ configs | 2 |
| 🧪 tests | 1 |
| **Total** | **246** |

### Classification

| Class | Count | Significance |
|:------|:-----:|:-------------|
| active | 103 | confirmed running services, active tools, fresh data |
| frozen | 19 | contracts in registry marked frozen, phase docs, market_futures |
| duplicate | 1 | futures_sim.py vs market_futures/ (candidate) |
| idle | 22 | .local/bin legacy scripts, stale data, orphan services |
| deprecated | 21 | archive docs, .bak, pre-version, shadow/audit/proof scripts |
| incomplete | 4 | test-contract, proposal contracts, test files |
| unknown | 58 | state/huo docs not in CONTRACT-REGISTRY, unclassified |

### Duplicate Candidates

| Function | Candidates | Note |
|:---------|:-----------|:-----|
| futures_sim | `futures_sim.py`, `market_futures/` | root standalone vs module: idle candidate |

### Consistency

| Check | Status |
|:------|:------:|
| path_check | ✅ PASS |

---

## Observation History

| Snapshot | Date | Rule | Total | Active | Frozen | Unknown | Note |
|:---------|:----:|:----|:-----:|:------:|:------:|:------:|:-----|
| ASSET-SNAPSHOT-001 | 2026-07-22 10:28 | v1.0 (no classification) | 298 | — | — | — | Raw inventory, no classification |
| ASSET-SNAPSHOT-002 | 2026-07-22 10:35 | v1.1 (priority-based) | 246 | 103 | 19 | 58 | unknown ≠ active |

---

## Related

- `MODULE-INDEX.md` — 模块能力分类
- `MODULE-CONSTRUCTION-HANDBOOK.md` — 模块建设方法
- `scripts/asset_observer.py` — 扫描脚本 v1.2
- Phase 8 / Integrity Observation

---

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial — asset category definition + conceptual snapshot |
| v1.1 | 2026-07-22 | ASSET-SNAPSHOT-001 — first full scan, inventory + consistency |
| v1.2 | 2026-07-22 | ASSET-SNAPSHOT-002 — classification v1.1 (priority rules), duplicate detection, unknown≠active |
