# Changelog

## 2026-07-18 — Governance Baseline v1.0

**Commit**: `2326ec2`

### Completed

- **Extension Boundary v1.0** — Runtime core untouched; external workers via systemd timer + oneshot; unified notification via push-gate.mjs
- **Memory Governance v1.0** — Semantic namespace (state/events/data/knowledge/cache/facts/preferences); identity isolation (燃🔥/烬🔥); writer boundary
- **Plugin Governance v1.0** — Capability registry (20 entries); contract declarations; enforcement boundary audit
- **Billing Separation** — Removed from Gateway injection; migrated to systemd timer + oneshot; Phase 2: removed internal interval scheduler (Model A)
- **Watchdog Audit** — Recovery authority violation found and disabled; demoted to pure Observer; service stopped and disabled
- **Source-Retry Audit** — External Worker boundary confirmed compliant; no governance intervention needed
- **Lottery Full Audit** — 8 timer/service pairs mapped; all oneshot/batch/exit compliant; 2 minor inconsistencies noted (P3)
- **Daily Status Report** — Deployed as systemd timer (08:07 daily); output to data/system/daily-report/
- **GitHub Sync** — `dragonfivechen/ChatGPT` established as system state anchor

### Observations

- **TUI Streaming Watchdog** (30s default) — can interrupt heavy maintenance tasks; P2 observation; no change
- **Delivery Ambiguity Case #001** — 502 Bad Gateway → send_attempt_started → Gateway correctly refused blind replay; externally confirmed delivered
- **Version Drift** — OpenClaw v2026.5.20; no upgrade planned
- **Local Model Eval** — Phase 1 token field enhancement deployed; 24h verification window
