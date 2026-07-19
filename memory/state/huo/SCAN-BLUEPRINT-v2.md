# OpenClaw Scan Blueprint v2

**Version:** 1.0
**Status:** BLUEPRINT — not implemented, no runtime impact
**Owner:** 燃🔥 (system maintenance)
**Created:** 2026-07-20 02:44 CST
**Relation:** Phase 8 Observation Layer extension

---

## Objective

Phase 1 scan (v1) verified:

- Runtime health
- Config file existence
- Namespace compliance
- Contract inventory
- Cron/scheduler state
- Session activity
- Basic security

v2 upgrade: from **Contract Existence Audit** to **Authority Enforcement Audit**.

The core question shifts from:

> Does the contract exist?

To:

> Is the contract being followed at runtime?

---

## Guiding Principle

**Audit does not own repair.**

```
Audit
  ↓
Evidence
  ↓
Human / maintenance decision
  ↓
Change
```

No automatic mutation. No auto-fix. Observation-only, consistent with Phase 8 freeze.

---

## Audit Modules

### 1. Truth Boundary Audit ⭐⭐⭐⭐⭐

**Purpose:** Verify that consumers access Truth Sources only through the designated Reader, not via direct file I/O.

**Sources (what to protect):**

| Source | Path |
|--------|------|
| Event | `memory/events/` |
| Config | `openclaw.json` |
| Fact | `memory/facts/` |

**Allowed readers (defined by existing contracts):**

- `event_source.py` — Event Truth Source reader
- `config_source.py` — Config Truth Source reader
- `fact_source.py` — Fact Truth Source reader
- Governance pipeline (`memory_governance_worker.py`)
- Backup scripts (read-only, archiving use case)

**Scan targets (potential consumers):**

- `scripts/`
- `tools/`
- `hooks/`
- `plugins/`

**Detection patterns (direct I/O signals):**

```
open()
cat (subprocess/shell)
jq
grep (on source files)
pathlib.Path.read_text()
json.load(open())
```

**Output:**

```
Truth Boundary Audit

Event:
  direct_access:  <count>
  violations:     <list of [path, caller, reading]>
  baseline_diff:  <added/removed since last scan>

Config:
  direct_access:  <count>
  violations:     <list>

Fact:
  direct_access:  <count>
  violations:     <list>
```

**Relation:** Extends Phase 7.3 Bypass Closure — verifies the 15 closed paths remain closed over time.

---

### 2. Write Boundary Audit ⭐⭐⭐⭐⭐

**Purpose:** Verify that only authorized writers can append or modify Truth Sources.

**Targets:**

| Target | Path |
|--------|------|
| Events | `memory/events/` |
| Facts | `memory/facts/` |
| Config | `openclaw.json` |
| Rules | `memory/rules/` |

**Allowed writers (by contract):**

| Target | Allowed | Forbidden |
|--------|---------|-----------|
| `events/` | `event_writer`, `collector`, `worker` | LLM, report generator, notification |
| `facts/` | `fact_promoter` (via Candidate → Validation → Fact pipeline) | Direct model output |
| `rules/` | Governance pipeline, human maintainer | LLM auto-write |
| `openclaw.json` | Human (terminal) via config tools | Scripts, agents |

**Detection patterns:**

- File metadata check (last modified by unauthorized process)
- Commit/change log audit on tracked files
- Unexpected writer PID / process name correlation

**Output:**

```
Write Boundary Audit

events:
  writer:      <process>
  target:      <path>
  allowed:     <yes/no>
  status:      <PASS/VIOLATION>

facts:
  writer:      <process>
  target:      <path>
  allowed:     <yes/no>
  status:      <PASS/VIOLATION>

rules:
  writer:      <process>
  target:      <path>
  allowed:     <yes/no>
  status:      <PASS/VIOLATION>
```

**Key risk:** Fact Source contamination via direct model output write to `memory/facts/`.

---

### 3. Event Integrity Audit ⭐⭐⭐⭐

**Purpose:** Verify that the event log — the sole Truth Source — is structurally sound.

**Checks:**

| Check | Condition | Violation signal |
|-------|-----------|------------------|
| trace_id | Every event MUST have non-null trace_id | Missing trace_id |
| Timestamp order | Events chronological within file | Out-of-order entries |
| event_id uniqueness | No duplicate event_id in scope | Collision |
| Append-only | File mtime = ctime (no in-place modification) | mtime > ctime for historical entries |
| File integrity | Not truncated, valid parse | Parse failure |

**Scope:** All files under `memory/events/` (all identity subdirectories).

**Output:**

```
Event Integrity Audit

total_events:          <count>
trace_id_valid:        <count>
timestamp_ordered:     <yes/no>
event_id_collisions:   <count>
append_only_violations: <count>
file_corruption:       <list>

overall:               <PASS / VIOLATION>
```

**Why P1:** Event is the single Truth Source. If events are corrupt, everything downstream is suspect.

---

### 4. Config Drift Audit ⭐⭐⭐

**Purpose:** Detect mismatch between Config Registry (the declared truth) and runtime loaded configuration.

**Comparison:**

```
Config Registry (documented)
          |
          |  diff
          v
Runtime loaded config (active)
```

**What to check:**

| Check | Detail |
|-------|--------|
| Missing keys | In registry but absent at runtime |
| Unknown keys | Present at runtime but not in registry |
| Changed values | Value differs between registry and runtime |
| Manual overrides | Environment variables, systemd drop-ins, `.env` |
| Secret replacements | Plaintext present where SecretRef expected |

**Scope:**

- `openclaw.json`
- Systemd user service environment
- `.env` files (if any)
- `.secrets/` directory
- Active model provider config

**Output:**

```
Config Drift Audit

registered_only:   <keys>
runtime_only:      <keys>
changed_values:    <key: registered → runtime>
manual_overrides:  <source, key, value>
secret_violations: <list>

overall:           <PASS / DRIFT>
```

---

### 5. Secret Boundary Audit ⭐⭐⭐

**Purpose:** Prevent secrets from leaking into audit-visible surfaces (events, memory, logs, backups).

**Scan targets:**

- `memory/events/`
- `memory/` (general)
- `logs/`
- `events/` (OpenClaw runtime events)
- `backup/` archives

**Detection patterns:**

```
sk-[a-zA-Z0-9]{20,}
api(_)?key\s*[=:]\s*['"][a-zA-Z0-9_-]{16,}
token\s*[=:]\s*['"][a-zA-Z0-9._-]{20,}
secret\s*[=:]\s*['"][a-zA-Z0-9]{8,}
password\s*[=:]\s*['"][^'"]{4,}
```

**Exclusions:**

- `.secrets/` directory (intentional storage)
- `secrets.json` (intentional storage)
- `exec-approvals.json` (operational, scoped)

**Output:**

```
Secret Boundary Audit

scanned_paths:     <list>
matches_found:     <count>
matches_detail:    <path, line, pattern, severity>
severity_breakdown:
  critical:        <count> (API keys, tokens)
  high:            <count> (secrets, passwords)
  low:             <count> (noise)

overall:           <PASS / LEAK>
```

---

## Execution Policy

| Property | Value |
|----------|-------|
| Mode | read-only |
| Auto-repair | prohibited |
| Frequency | manual initial baseline, then periodic observation |
| Trigger | human-initiated (no cron auto-trigger in v1) |

### Audit Pipeline Contract

```
Trigger (manual)
  ↓
Load Allow List
  ↓
Run Audits (1-5)
  ↓
Collect Evidence (jsonl, append-only)
  ↓
Report (human-readable)
  ↓
Human Decision (repair / ignore / update Allow List)
```

### Alignment with Phase 8

Phase 8 Observation Layer defined:

```
System runs → Evidence (jsonl) → Integrity Analyzer → State → Maintenance Queue → Human Governance
```

v2 audits extend this by adding **evidence from the authority domain**:

```
Current Phase 8 evidence:  system health, memory governance, service state
v2 adds:                  authority boundary compliance, event integrity, config drift, secret leakage
```

All evidence feeds the same `memory/data/system/system-health.jsonl` pipeline.

---

## Baseline Registration

Before first execution:

1. Register current `scripts/` and `tools/` inventory as baseline
2. Register current `memory/events/` writer identities as baseline
3. Snapshot current `openclaw.json` as Config Registry truth
4. Snapshot current backup manifest

After baseline, each subsequent run produces `diff` against baseline, not full rescan.

---

## What This Does NOT Do

- ❌ Replace Phase 7/8 contracts
- ❌ Introduce runtime components
- ❌ Auto-fix any violation
- ❌ Add new cron/crontab entries
- ❌ Modify system state in any way
- ❌ Scan for code quality, file counts, or documentation completeness

---

## Relation to Existing Files

| File | Relation |
|------|----------|
| `PHASE-7.5-INTEGRITY-FREEZE.md` | v2 operates within the frozen boundary, does not modify |
| `PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md` | v2 extends evidence collection domain |
| `CONFIG-SOURCE-CONTRACT.md` | v2 Config Drift audit validates this contract |
| `EVENT-SOURCE-CONTRACT.md` | v2 Truth + Event audits validate this contract |
| `FACT-SOURCE-CONTRACT.md` | v2 Truth + Write audits validate this contract |
| `TOOL-CALL-GATEWAY-CONTRACT.md` | Tool-level reader/writer enforcement (separate scope) |
| `BYpass-REGISTER-v1.0.md` | v2 Truth Boundary audit verifies bypasses remain closed |
