# System Asset Module File Mapping v1.0

> Semantic Index (L0/L1) → 具体文件路径 的关联层。
>
> 不替代 Semantic Index，不替代 Asset Observation。
> Semantic Index 负责语义入口，File Mapping 负责模块内文件定位，Observation 负责全量事实扫描。

---

## Purpose

```text
用户语义
 ↓
SYSTEM-ASSET-SEMANTIC-INDEX  (L0/L1 模块)
 ↓
SYSTEM-ASSET-MODULE-FILE-MAPPING  (L2 文件)
 ↓
具体路径
```

## 职责分界

| 层 | 粒度 | 作用 |
|:---|:----:|:-----|
| Semantic Index | L0/L1 | 人类语义定位模块 |
| File Mapping | L2 | 模块内部文件定位 |
| Observation | 全量文件 | 存在性/分类/漂移检查 |

---

## 1. Governance — Module File Mapping

### GOV-MODULE-001: 元治理契约体系

```yaml
module_id: GOV-MODULE-001
files:
  core:
    - memory/state/huo/META-CONTRACT.md
    - memory/state/huo/CONTRACT-REGISTRY.md
    - memory/state/huo/CONTRACT-LEVEL-CLASSIFICATION.md
    - memory/state/huo/CONTRACT-DECLARATION-SCHEMA.md
  registry:
    - memory/state/huo/CONTRACT-LEVEL-REGISTRY.md
    - memory/state/huo/CONTRACT-REFERENCE-ALIGNMENT-RULE.md
  schema_design:
    - memory/state/huo/context-projection-schema-design.md
    - memory/state/huo/provider-capability-schema-design.md
    - memory/state/huo/provider-capability-schema-mapping.md
evidence: ASSET-SNAPSHOT-002
```

### GOV-MODULE-002: 冻结仲裁体系

```yaml
module_id: GOV-MODULE-002
files:
  core:
    - memory/state/huo/FREEZE-CONTRACT.md
    - memory/state/huo/FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md
  supplement:
    - memory/state/huo/BASELINE-COMPLETENESS-SUPPLEMENT.md
  design:
    - memory/state/huo/CONTRACT-MANAGEMENT-PIPELINE-DESIGN.md
    - memory/state/huo/CONTRACT-ENFORCEMENT-SKELETON-DESIGN.md
    - memory/state/huo/RUNTIME-ENFORCEMENT-DESIGN.md
    - memory/state/huo/RUNTIME-ENFORCEMENT-VALIDATION.md
evidence: ASSET-SNAPSHOT-002
```

### GOV-MODULE-003: 治理链闭环

```yaml
module_id: GOV-MODULE-003
files:
  core:
    - memory/state/huo/EVIDENCE-CONTRACT.md
    - memory/state/huo/DECISION-CONTRACT.md
    - memory/state/huo/CHANGE-CONTRACT.md
  register:
    - memory/state/huo/BYPASS-REGISTER-v1.0.md
  feasibility:
    - memory/state/huo/FUNCTIONAL-MODULE-SELF-HEAL-FEASIBILITY.md
evidence: ASSET-SNAPSHOT-002
```

### GOV-MODULE-004: 身份治理体系

```yaml
module_id: GOV-MODULE-004
files:
  core:
    - IDENTITY.md
    - IDENTITY-CONTRACT.md
    - IDENTITY-RULES.md
  authority:
    - Maintenance-Authority-Contract-v1.0.md
  candidate:
    - memory/state/huo/CANDIDATE-IDENTITY-RULE.md
  identity_runtime:
    - .local/bin/identity.sh
  workspace_rules:
    - AGENTS.md
    - SOUL.md
    - USER.md
    - HEARTBEAT.md
evidence: ASSET-SNAPSHOT-002
```

### GOV-MODULE-005: 领域契约组（彩票）

```yaml
module_id: GOV-MODULE-005
files:
  core:
    - memory/state/huo/LOTTERY-CAPABILITY-CONTRACT.md
    - memory/state/huo/LOTTERY-PREDICTION-CONTRACT.md
    - memory/state/huo/LOTTERY-PREDICTION-STRATEGY-CONTRACT.md
    - memory/state/huo/LOTTERY-PREDICTION-ENGINE-CONTRACT.md
  configuration:
    - memory/state/huo/LOTTERY-PREDICTION-DIVERSITY-CONTRACT.md
    - memory/state/huo/LOTTERY-PREDICTION-COMBINATION-CONTRACT.md
    - memory/state/huo/LOTTERY-PREDICTION-ROLE-CONTRACT.md
  source:
    - memory/state/huo/LOTTERY-SOURCE-CONTRACT.md
    - memory/state/huo/LOTTERY-SOURCE-RETRY-CONTRACT.md
  statistics:
    - memory/state/huo/LOTTERY-STATISTICS-CONTRACT.md
  worker:
    - memory/state/huo/LOTTERY-WORKER-DIRECTORY-CONTRACT.md
evidence: ASSET-SNAPSHOT-002
```

### GOV-MODULE-006: 领域契约组（TG）

```yaml
module_id: GOV-MODULE-006
files:
  baseline:
    - memory/state/huo/TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT.md
  alignment:
    - memory/state/huo/TG-IMPLEMENTATION-ALIGNMENT-CONTRACT.md
  data:
    - memory/state/huo/TG-BEHAVIOR-DATA-CONTRACT.md
evidence: ASSET-SNAPSHOT-002
```

### 附加治理契约

```yaml
module_id: GOV-MODULE-007
human_name: 访问控制契约组
files:
  - memory/state/huo/PRIVILEGE-CONTROL-CONTRACT.md
  - memory/state/huo/TOOL-CALL-GATEWAY-CONTRACT.md
  - memory/state/huo/REASONING-ISOLATION-CONTRACT.md
  - memory/state/huo/CREDENTIAL-ACCESS-CONTRACT.md
  - memory/state/huo/TERMINAL-MODEL-EXECUTION-CONTRACT.md
evidence: ASSET-SNAPSHOT-002
```

```yaml
module_id: GOV-MODULE-008
human_name: 供给者/上下文契约组
files:
  - memory/state/huo/PROVIDER-CAPABILITY-CONTRACT.md
  - memory/state/huo/FACT-SOURCE-CONTRACT.md
  - memory/state/huo/EVENT-SOURCE-CONTRACT.md
  - memory/state/huo/CONFIG-SOURCE-CONTRACT.md
  - memory/state/huo/CONTEXT-PROJECTION-CONTRACT.md
  - memory/state/huo/METADATA-CONTRACT.md
  - memory/state/huo/PLUGIN-CAPABILITY-CONTRACT.md
  - memory/state/huo/CAPABILITY-REGISTRY.md
evidence: ASSET-SNAPSHOT-002
```

```yaml
module_id: GOV-MODULE-009
human_name: 附加治理文档
files:
  - memory/state/huo/MODEL-CONSTRAINT-MAP.md
  - memory/state/huo/P1.2-HEALTH-STATE-MODEL-PROPOSAL.md
  - memory/state/huo/OBSERVER-ABSTRACTION-LAYER-v1.0.md
  - memory/state/huo/DIAGNOSTICS-BEHAVIOR-LAYER.md
  - memory/state/huo/MEMORY-OWNERSHIP-CONTRACT.md
  - memory/state/huo/MEMORY-WRITER-BOUNDARY.md
  - memory/state/huo/MEMORY-WRITER-BOUNDARY.md (duplicate)
  - memory/state/huo/CAPABILITY-REGISTRY.md
evidence: ASSET-SNAPSHOT-002
```

---

## 2. Construction — Module File Mapping

### CON-MODULE-001: 模块建设手册

```yaml
module_id: CON-MODULE-001
files:
  handbook:
    - docs/MODULE-CONSTRUCTION-HANDBOOK.md
    - docs/MODULE-INDEX.md
  runbook:
    - memory/knowledge/MAINTENANCE-RUNBOOK-v1.0.md
  tg_knowledge:
    - memory/knowledge/TG-AGENT-OPERATION-RULES.md
    - memory/knowledge/TG-BUILD-BOUNDARIES.md
  patterns:
    - memory/knowledge/behavior_correction_patterns.md
    - memory/knowledge/CONVERSATION-MAINTENANCE-OBSERVATION.md
    - memory/knowledge/conversation-maintenance/feedback/N1-N6-summary.md
evidence: ASSET-SNAPSHOT-002
```

### CON-MODULE-002: 系统资产观察层

```yaml
module_id: CON-MODULE-002
files:
  observation_doc:
    - docs/SYSTEM-ASSET-OBSERVATION.md
    - docs/SYSTEM-ASSET-SEMANTIC-INDEX.md
    - docs/SYSTEM-ASSET-MODULE-FILE-MAPPING.md
  observer_script:
    - scripts/asset_observer.py
  observation_data:
    - memory/data/system/asset-observation.jsonl
evidence: ASSET-SNAPSHOT-002
```

### CON-MODULE-003: 架构蓝图

```yaml
module_id: CON-MODULE-003
files:
  blueprint:
    - memory/knowledge/ARCHITECTURE-BLUEPRINT-v1.md
  milestones:
    - memory/state/huo/ARCHITECTURE.md
  scan:
    - memory/state/huo/SCAN-BLUEPRINT-v2.md
  trading_deploy:
    - docs/TRADING-SYSTEM-QUICK-DEPLOY.md
  archive_docs:
    - archive/docs/ASSET-INDEX.md
  legacy:
    - docs/test-contract.md
    - docs/ARCHITECTURE.md
evidence: ASSET-SNAPSHOT-002
```

---

## 3. Runtime — Module File Mapping

### RUN-MODULE-001: Gateway 运行时

```yaml
module_id: RUN-MODULE-001
files:
  config:
    - ~/.openclaw/openclaw.json
    - ~/.openclaw/secrets.json
    - ~/.openclaw/exec-approvals.json
  service:
    - ~/.config/systemd/user/openclaw-gateway.service
  state:
    - ~/.openclaw/billing_state.json
    - ~/.openclaw/daily_state.json
    - ~/.openclaw/update-check.json
evidence: ASSET-SNAPSHOT-002
```

### RUN-MODULE-002: 自愈系统

```yaml
module_id: RUN-MODULE-002
files:
  observer:
    - self-healing/observer.py
    - self-healing/provider_observe.py
    - self-healing/boundary_observe.py
  enforcement:
    - self-healing/boundary_gate.py
    - self-healing/config_audit.py
    - self-healing/event_writer.py
  analytics:
    - self-healing/health_diff.py
    - self-healing/health_graph.py
  config:
    - self-healing/modules.yaml
  schema:
    - self-healing/schemas/self-healing-event.json
evidence: ASSET-SNAPSHOT-002
```

### RUN-MODULE-003: 运行时上下文

```yaml
module_id: RUN-MODULE-003
files:
  provider:
    - runtime/context_provider.py
    - runtime/context_validator.py
    - runtime/temporal_resolver.py
  data:
    - runtime/time_context.json
  contract:
    - runtime/context_contract.md
evidence: ASSET-SNAPSHOT-002
```

---

## 4. Lottery — Module File Mapping

### LOT-MODULE-001: 彩票系统

```yaml
module_id: LOT-MODULE-001
files:
  worker:
    - .local/bin/lottery-worker.sh
  notification:
    - hooks/oek-ci-gate/push-notify.mjs
    - hooks/oek-ci-gate/push-gate.mjs
    - .local/bin/daily_integrity_push.sh
  events:
    - memory/events/lottery/ssq.jsonl
    - memory/events/lottery/dlt.jsonl
    - memory/events/lottery/kl8.jsonl
  data:
    - memory/data/lottery/ssq.jsonl
    - memory/data/lottery/dlt.jsonl
    - memory/data/lottery/kl8.jsonl
  predictions:
    - memory/cache/lottery/predictions/
  systemd_timers:
    - lotery-fetch.timer / lotery-fetch.service
    - lotery-daily.timer / lotery-daily.service
    - ssq-predict.timer / ssq-predict.service
    - ssq-check.timer / ssq-check.service
    - dlt-predict.timer / dlt-predict.service
    - dlt-check.timer / dlt-check.service
    - kl8-predict.timer / kl8-predict.service
    - kl8-check.timer / kl8-check.service
    - source-retry.timer / source-retry.service
evidence: ASSET-SNAPSHOT-002
```

---

## 5. Trading — Module File Mapping

### TRD-MODULE-001: 期货模拟交易模块

```yaml
module_id: TRD-MODULE-001
files:
  core_sim:
    - market_futures/futures_contracts.json
    - market_futures/collector.py
    - market_futures/position.py
    - market_futures/account.py
    - market_futures/simulator.py
  run:
    - market_futures/run_strategy.py
    - market_futures/run_phase5_verify.py
    - market_futures/strategy_live.py
    - market_futures/collector_live.py
  strategies:
    - market_futures/strategies/__init__.py
    - market_futures/strategies/ma.py
    - market_futures/strategies/breakout.py
    - market_futures/strategies/rsi.py
    - market_futures/strategies/signal.py
  replay:
    - market_futures/replays/__init__.py
    - market_futures/replays/converter.py
    - market_futures/replays/loader.py
  reports:
    - market_futures/reports/performance.py
    - market_futures/reports/equity_curve_ma_akshare_6sym.jsonl
    - market_futures/reports/trades_ma_akshare_6sym.jsonl
  historical:
    - market_futures/data/historical/schema.md
    - market_futures/data/historical/README.md
    - market_futures/data/historical/RB_2022-2026.csv
    - market_futures/data/historical/I_2022-2026.csv
    - market_futures/data/historical/JM_2022-2026.csv
    - market_futures/data/historical/CU_2022-2026.csv
    - market_futures/data/historical/AL_2022-2026.csv
    - market_futures/data/historical/SC_2022-2026.csv
    - market_futures/data/historical/replay_akshare_6sym.jsonl
    - market_futures/data/historical/sample_20260106.csv
  state:
    - market_futures/data/account_state.json
    - market_futures/state/live_ma.json
    - market_futures/futures_events.jsonl
  validation:
    - market_futures/PHASE_STATUS.json
    - market_futures/FUTURES-SIM-VALIDATION-NOTE.md
  docs:
    - memory/state/huo/FUTURES-SIM-V0.1-ARCH.md
    - memory/state/huo/TRADING-RUNTIME-V0.5-ARCH.md
  test:
    - market_futures/tests/test_phase2.py
  data_import:
    - tools/futures_data_import/akshare_export.py
  legacy:
    - market_futures/run_phase5_verify.py
  systemd_timers:
    - market-futures-collector.timer / market-futures-collector.service
    - market-futures-strategy.timer / market-futures-strategy.service
evidence: ASSET-SNAPSHOT-002
```

---

## 6. Monitoring — Module File Mapping

### MON-MODULE-001: 系统资产观察扫描器

```yaml
module_id: MON-MODULE-001
files:
  scan:
    - scripts/asset_observer.py
  data:
    - memory/data/system/asset-observation.jsonl
evidence: ASSET-SNAPSHOT-002
```

### MON-MODULE-002: 系统传感器

```yaml
module_id: MON-MODULE-002
files:
  scripts:
    - scripts/collect-sensors.sh
    - scripts/collect-daily-status.sh
    - scripts/push-daily-report.sh
  data:
    - memory/data/system/system-health.jsonl
    - memory/data/system/service-state.jsonl
    - memory/data/system/memory-snapshot.jsonl
    - memory/data/system/task-runtime.jsonl
    - memory/data/system/daily-report/latest.md
    - memory/data/system/daily-report/archive/
evidence: ASSET-SNAPSHOT-002
```

### MON-MODULE-003: Token 观测

```yaml
module_id: MON-MODULE-003
files:
  scripts:
    - scripts/collect-token-metrics.sh
    - scripts/analyze-token-metrics.py
  data:
    - memory/data/system/token-metrics.jsonl
    - memory/data/system/daily-token-report.jsonl
  observe:
    - ~/.openclaw/observe-token.sh
    - ~/.openclaw/token_observe.jsonl
evidence: ASSET-SNAPSHOT-002
```

### MON-MODULE-004: TG 行为诊断

```yaml
module_id: MON-MODULE-004
files:
  tools:
    - tools/tg_transcript_reader.py
    - tools/tg_behavior_analyzer.py
    - tools/tg_maintenance_queue.py
  findings:
    - diagnostics/agent_behavior/telegram/findings/
  maintenance:
    - diagnostics/agent_behavior/telegram/maintenance/
  raw:
    - diagnostics/agent_behavior/telegram/raw/
  registry:
    - registry/diagnostic/rules_behavior_analyzer.md
    - registry/diagnostic/rules_c0_c4_inline.md
    - registry/diagnostic/rules_duplicate_filter.md
  corrections:
    - diagnostics/correction/regression_cases/
evidence: ASSET-SNAPSHOT-002
```

### MON-MODULE-005: 治理监控工具

```yaml
module_id: MON-MODULE-005
files:
  contract:
    - tools/contract_validator.py
  governance:
    - tools/memory_governance_worker.py
    - tools/memory_candidate_extract.py
    - tools/memory_dedup.py
    - tools/memory_promote.py
    - tools/memory_feedback_detect.py
  source:
    - tools/event_source.py
    - tools/fact_source.py
    - tools/config_source.py
    - tools/check_boundary.py
  data:
    - memory/data/system/governance-pipeline.jsonl
    - memory/data/system/governance-pipeline.log
    - memory/data/system/governance-state.json
    - memory/data/system/governance-last.json
    - memory/data/system/contract_violation.jsonl
    - memory/data/system/error-events.jsonl
    - memory/data/system/authority-baseline.json
    - memory/data/system/memory-search-status.json
    - memory/data/system/backup-events.jsonl
    - memory/data/system/tg-build-log.jsonl
  audit:
    - audit/authority-review/
    - audit/constraint-verification/
    - memory/data/system/authority-audit-report.md
evidence: ASSET-SNAPSHOT-002
```

---

## 7. Infrastructure — Module File Mapping

### INF-MODULE-001: 系统备份体系

```yaml
module_id: INF-MODULE-001
files:
  scripts:
    - scripts/backup-full.sh
    - scripts/audit-backup.sh
    - scripts/restore-verify.sh
    - scripts/restore-template.md
  output:
    - /backup/openclaw-full-*.tar.zst (retention 7)
    - /backup/README.md
    - /backup/IDENTITY.md
    - /backup/MEMORY-GUIDE.md
    - /backup/SYSTEM-SNAPSHOT.md
  helper:
    - .local/bin/pre-backup-sync.sh
  cron:
    - "0 3 * * * backup-full.sh && audit-backup.sh"
evidence: ASSET-SNAPSHOT-002
```

### INF-MODULE-002: Billing Pipeline

```yaml
module_id: INF-MODULE-002
files:
  hooks:
    - hooks/oek-ci-gate/billing-snapshotter.mjs
    - hooks/oek-ci-gate/billing-push-worker.mjs
    - hooks/oek-ci-gate/billing-loader.mjs
  systemd:
    - oek-billing-snapshot.timer / oek-billing-snapshot.service
    - oek-billing-push.timer / oek-billing-push.service
  archive:
    - hooks/oek-ci-gate/billing-snapshotter.mjs.v1.0-pre-phase2
evidence: ASSET-SNAPSHOT-002
```

### INF-MODULE-003: 本地模型服务

```yaml
module_id: INF-MODULE-003
files:
  worker:
    - scripts/local-task-worker.sh
  eval:
    - scripts/eval-local.sh
    - memory/events/huo/ollama-eval.jsonl
  production:
    - memory/events/huo/ollama-production.jsonl
  model_variants:
    - qwen2.5:3b (production)
    - qwen3:4b (eval base)
  legacy:
    - scripts/eval-local.sh.v1.0-pre-token
evidence: ASSET-SNAPSHOT-002
```

### INF-MODULE-004: Crontab 调度

```yaml
module_id: INF-MODULE-004
files:
  crontab:
    - "0 3 * * * backup-full.sh + audit-backup.sh"
    - "0 * * * * collect-sensors.sh + eval-local.sh + local-task-worker.sh"
    - "*/5 * * * * context_provider.py"
    - "*/30 * * * * memory_governance_worker.py"
    - "0 * * * * collect-token-metrics.sh"
    - "55 7 * * * analyze-token-metrics.py"
    - "30 * * * * contract_validator.py"
    - "*/5 * * * * observer.py --once"
    - "0 * * * * provider_observe.py"
evidence: ASSET-SNAPSHOT-002
```

---

## 8. Legacy / Unmapped Scripts

以下 `.local/bin/` 遗留脚本未归属具体模块，标记为 idle/deprecated，供参考：

```yaml
module_id: LEGACY-SCRIPTS
files:
  deprecated:
    - .local/bin/audit.sh
    - .local/bin/shadow.sh
    - .local/bin/snapshot.sh
    - .local/bin/proof.sh
    - .local/bin/explain.sh
    - .local/bin/resolve.sh
    - .local/bin/test_audit.sh
  idle:
    - .local/bin/balance.sh
    - .local/bin/billing-detail.sh
    - .local/bin/events.sh
    - .local/bin/health.sh
    - .local/bin/observe.sh
    - .local/bin/stats.sh
    - .local/bin/status.sh
    - .local/bin/syslog.sh
    - .local/bin/system-report.sh
    - .local/bin/timeline.sh
    - .local/bin/config-health.sh
evidence: ASSET-SNAPSHOT-002
```

---

## 9. Memory — Directory Level

memory 目录不做文件级展开（Observation Layer 已覆盖），仅供参考：

```yaml
module_id: MEM-ALL
directories:
  state: memory/state/huo/ (82 files — 41 contracts + 18 phase + 23 other)
  events_hou: memory/events/huo/ (daily logs + eval/production data)
  events_jin: memory/events/jin/ (TG daily logs)
  events_lottery: memory/events/lottery/ (SSQ/DLT/KL8 event streams)
  events_lco: memory/events/lco/ (production trial data)
  data_system: memory/data/system/ (26 files — telemetry/audit/governance)
  data_lottery: memory/data/lottery/ (3 files — statistics)
  cache: memory/cache/lottery/predictions/ (prediction cache)
  knowledge: memory/knowledge/ (7 files — architecture/runbook/patterns)
  facts: memory/facts/ (empty)
evidence: ASSET-SNAPSHOT-002
```

---

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial. 全模块文件映射: Governance(9) / Construction(3) / Runtime(3) / Lottery(1) / Trading(1) / Monitoring(5) / Infrastructure(4) + Legacy + Memory |
