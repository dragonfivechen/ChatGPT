#!/usr/bin/env bash
# 备份完整性审计 — 每日备份后自动检查关键路径
set -euo pipefail

BACKUP_DIR="/backup"
LATEST=$(ls -1t "${BACKUP_DIR}/openclaw-full-"*.tar.zst 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
  echo "[$(date)] ❌ 无备份文件"
  exit 1
fi

echo "[$(date)] === 审计: $(basename $LATEST) ==="

# 先解出 MANIFEST 到临时目录
TMPDIR=$(mktemp -d)
tar --zstd -xf "$LATEST" -C "$TMPDIR" --wildcards '*/MANIFEST.txt' 2>/dev/null
MANIFEST=$(find "$TMPDIR" -name MANIFEST.txt 2>/dev/null | head -1)

if [ -z "$MANIFEST" ]; then
  echo "  ❌ MANIFEST.txt 未找到"
  rm -rf "$TMPDIR"
  exit 1
fi

MISSING=0
TOTAL=$(wc -l < "$MANIFEST")

MUST_HAVE=(
  "openclaw.json"
  "openclaw-auth/auth-profiles.json"
  "openclaw-credentials/telegram-main-allowFrom.json"
  "openclaw-identity/device.json"
  "openclaw-telegram/bot-info-main.json"
  "openclaw-workspace/SOUL.md"
  "openclaw-workspace/AGENTS.md"
  "openclaw-workspace/.secrets/push-gate.json"
  "openclaw-workspace/scripts/backup-full.sh"
  "openclaw-workspace/scripts/audit-backup.sh"
  "openclaw-workspace/scripts/collect-sensors.sh"
  "openclaw-workspace/scripts/eval-local.sh"
  "openclaw-workspace/scripts/push-daily-report.sh"
  "openclaw-workspace/memory/data/system/system-health.jsonl"
  "openclaw-workspace/memory/data/system/service-state.jsonl"
  "openclaw-workspace/memory/data/system/memory-snapshot.jsonl"
  "openclaw-workspace/memory/events/huo/ollama-eval.jsonl"
  "openclaw-workspace/memory/data/system/backup-events.jsonl"
  "systemd/ollama.service"
  "systemd/ollama.service.d/override.conf"
  "systemd-user/openclaw-gateway.service"
  "systemd/oc-watchdog-stream.service"
  "ollama-models/manifests/registry.ollama.ai/library/qwen2.5/3b"
  "MEMORY-GUIDE.md"
  "RESTORE.md"
  "MANIFEST.txt"
  "crontab.txt"
)

for path in "${MUST_HAVE[@]}"; do
  if grep -Fxq "$path" "$MANIFEST"; then
    echo "  ✅ $path"
  else
    echo "  ❌ MISSING: $path"
    MISSING=$((MISSING + 1))
  fi
done

echo ""
if [ "$MISSING" -eq 0 ]; then
  echo "✅ 审计通过: 全部 ${#MUST_HAVE[@]} 项关键路径存在"
  echo "   文件总数: ${TOTAL}"
else
  echo "❌ 审计失败: ${MISSING}/${#MUST_HAVE[@]} 项缺失"
fi

rm -rf "$TMPDIR"
