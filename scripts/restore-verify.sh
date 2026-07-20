#!/usr/bin/env bash
# restore-verify.sh — 恢复后完整性校验
# 用法: ./restore-verify.sh /path/to/backup/dir
set -euo pipefail

BACKUP="${1:-/backup/openclaw-full-$(date +%Y%m%d_)*}"
MANIFEST="$BACKUP/backup-manifest.json"
UNIT_LIST="$BACKUP/systemd-user/units.list"

if [ -f "$MANIFEST" ]; then
  echo "=== 校验: backup-manifest.json ==="
  python3 -c "
import json
with open('$MANIFEST') as f:
    m = json.load(f)
print(f'  备份时间: {m.get(\"timestamp\",\"?\")}')
print(f'  文件总数: {m.get(\"file_count\",\"?\")}')
print(f'  Systemd services: {m.get(\"systemd_services\",\"?\")}')
print(f'  Systemd timers: {m.get(\"systemd_timers\",\"?\")}')
print(f'  Cron entries: {m.get(\"cron_entries\",\"?\")}')
print(f'  Models: {m.get(\"models\",\"?\")}')
"
else
  echo "⚠️  无 backup-manifest.json (旧版备份)"
fi

echo ""
echo "=== 校验: Systemd units ==="
if [ -f "$UNIT_LIST" ]; then
  EXPECTED=$(wc -l < "$UNIT_LIST")
  INSTALLED=$(ls -1 ~/.config/systemd/user/*.service ~/.config/systemd/user/*.timer 2>/dev/null | wc -l)
  echo "  备份记录: ${EXPECTED} units"
  echo "  当前安装: ${INSTALLED} units"
  if [ "$EXPECTED" != "$INSTALLED" ]; then
    echo "  ❌ 数量不匹配"
    # 列出缺失
    while IFS= read -r unit; do
      [ ! -f "$HOME/.config/systemd/user/$unit" ] && echo "  缺失: $unit"
    done < "$UNIT_LIST"
  else
    echo "  ✅ 数量匹配"
  fi
else
  echo "  ⚠️  无 units.list (旧版备份)"
fi

echo ""
echo "=== 校验: Crond ==="
CURRENT_CRON=$(crontab -l 2>/dev/null | grep -c -v '^#' | grep -v '^$' || true)
BACKUP_CRON=$(grep -c -v '^#' "$BACKUP/crontab.txt" 2>/dev/null || true)
echo "  备份: ${BACKUP_CRON:-0} entries"
echo "  当前: ${CURRENT_CRON:-0} entries"

echo ""
echo "=== 校验: Ollama ==="
if command -v ollama &>/dev/null; then
  ollama list 2>/dev/null | tail -n +2
else
  echo "  Ollama 未安装"
fi

echo ""
echo "=== 校验: OpenClaw ==="
if command -v openclaw &>/dev/null; then
  openclaw status 2>&1 | head -3
fi

echo ""
echo "=== 校验: Secrets ==="
SECRET_COUNT=$(ls -1 "$BACKUP/openclaw-workspace/.secrets/" 2>/dev/null | wc -l)
echo "  备份 secrets: ${SECRET_COUNT} files"

echo ""
echo "恢复校验完成。"
