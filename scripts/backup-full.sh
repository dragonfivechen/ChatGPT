#!/usr/bin/env bash
# 全量系统备份 — OpenClaw + Ollama 完整恢复单元
# 目标: 一条命令重建系统
set -euo pipefail

BACKUP_DIR="/backup"
RETENTION=7
TS=$(TZ='Asia/Shanghai' date +"%Y%m%d_%H%M%S")
BACKUP_NAME="openclaw-full-${TS}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
TARBALL="${BACKUP_DIR}/${BACKUP_NAME}.tar.zst"
HOME_DIR="/home/dragonfive"
OC_DIR="${HOME_DIR}/.openclaw"

mkdir -p "$BACKUP_PATH"
echo "[$(date)] === 全量备份开始: ${BACKUP_NAME} ==="

# ── 1. OpenClaw 核心配置 ──
cp -a "${OC_DIR}/openclaw.json" "${BACKUP_PATH}/" 2>/dev/null
mkdir -p "${BACKUP_PATH}/openclaw-config-history"
cp -a "${OC_DIR}/openclaw.json.bak"* "${BACKUP_PATH}/openclaw-config-history/" 2>/dev/null || true
cp -a "${OC_DIR}/openclaw.json.last-good" "${BACKUP_PATH}/openclaw-config-history/" 2>/dev/null || true

# ── 2. 工作区 ──
cp -a "${OC_DIR}/workspace" "${BACKUP_PATH}/openclaw-workspace" 2>/dev/null

# ── 3. 认证 + 身份 ──
mkdir -p "${BACKUP_PATH}/openclaw-auth"
cp -a "${OC_DIR}/agents/main/agent/auth-profiles.json" "${BACKUP_PATH}/openclaw-auth/" 2>/dev/null || true
cp -a "${OC_DIR}/agents/main/agent/auth-state.json" "${BACKUP_PATH}/openclaw-auth/" 2>/dev/null || true
cp -a "${OC_DIR}/agents/main/agent/models.json" "${BACKUP_PATH}/openclaw-auth/" 2>/dev/null || true
cp -a "${OC_DIR}/credentials" "${BACKUP_PATH}/openclaw-credentials" 2>/dev/null
cp -a "${OC_DIR}/identity" "${BACKUP_PATH}/openclaw-identity" 2>/dev/null

# ── 4. Telegram bot 状态 ──
cp -a "${OC_DIR}/telegram" "${BACKUP_PATH}/openclaw-telegram" 2>/dev/null

# ── 5. 会话历史 ──
if [ -d "${OC_DIR}/agents/main/sessions" ]; then
  mkdir -p "${BACKUP_PATH}/openclaw-sessions"
  cp -a "${OC_DIR}/agents/main/sessions/"*.jsonl "${BACKUP_PATH}/openclaw-sessions/" 2>/dev/null || true
  cp -a "${OC_DIR}/agents/main/sessions/"sessions.json* "${BACKUP_PATH}/openclaw-sessions/" 2>/dev/null || true
fi

# ── 6. 内存数据库 (SQLite) ──
if [ -d "${OC_DIR}/memory" ]; then
  mkdir -p "${BACKUP_PATH}/openclaw-db"
  cp -a "${OC_DIR}/memory/main.sqlite" "${BACKUP_PATH}/openclaw-db/" 2>/dev/null || true
  cp -a "${OC_DIR}/memory/main.sqlite-wal" "${BACKUP_PATH}/openclaw-db/" 2>/dev/null || true
  cp -a "${OC_DIR}/memory/main.sqlite-shm" "${BACKUP_PATH}/openclaw-db/" 2>/dev/null || true
fi

# ── 7. 运行时状态 ──
mkdir -p "${BACKUP_PATH}/openclaw-state"
for f in billing_state.json daily_state.json daily_history.jsonl token_observe.jsonl \
         update-check.json exec-approvals.json gateway-supervisor-restart-handoff.json; do
  [ -f "${OC_DIR}/$f" ] && cp -a "${OC_DIR}/$f" "${BACKUP_PATH}/openclaw-state/"
done
cp -a "${OC_DIR}/logs/config-health.json" "${BACKUP_PATH}/openclaw-state/" 2>/dev/null || true
cp -a "${OC_DIR}/balance_snapshots.jsonl" "${BACKUP_PATH}/openclaw-state/" 2>/dev/null || true

# ── 8. Cron 任务 ──
mkdir -p "${BACKUP_PATH}/openclaw-cron"
cp -a "${OC_DIR}/cron/"jobs*.json "${BACKUP_PATH}/openclaw-cron/" 2>/dev/null || true
cp -a "${OC_DIR}/cron/"*-state.json "${BACKUP_PATH}/openclaw-cron/" 2>/dev/null || true

# ── 9. 投递队列 ──
[ -d "${OC_DIR}/delivery-queue" ] && cp -a "${OC_DIR}/delivery-queue" "${BACKUP_PATH}/openclaw-delivery-queue" 2>/dev/null || true

# ── 10. 其他 OpenClaw 配置 ──
mkdir -p "${BACKUP_PATH}/openclaw-etc"
for d in completions plugin-skills tui tasks locks; do
  [ -d "${OC_DIR}/$d" ] && cp -a "${OC_DIR}/$d" "${BACKUP_PATH}/openclaw-etc/"
done
[ -f "${OC_DIR}/observe-token.sh" ] && cp -a "${OC_DIR}/observe-token.sh" "${BACKUP_PATH}/openclaw-etc/"

# ── 11. Ollama 模型 ──
if sudo -n test -d /usr/share/ollama/.ollama/models/blobs 2>/dev/null; then
  echo "[$(date)] 拷贝模型文件..."
  mkdir -p "${BACKUP_PATH}/ollama-models"
  sudo -n cp -a /usr/share/ollama/.ollama/models/blobs "${BACKUP_PATH}/ollama-models/" || echo "[$(date)] WARNING: 模型blobs拷贝失败"
  sudo -n cp -a /usr/share/ollama/.ollama/models/manifests "${BACKUP_PATH}/ollama-models/" 2>/dev/null || true
  sudo -n chown -R dragonfive:dragonfive "${BACKUP_PATH}/ollama-models/" 2>/dev/null || true
fi

# ── 12. Ollama 用户配置 ──
cp -a "${HOME_DIR}/.ollama" "${BACKUP_PATH}/ollama-user-config" 2>/dev/null || true

# ── 13. Systemd 服务配置 ──
mkdir -p "${BACKUP_PATH}/systemd"
for f in /etc/systemd/system/ollama.service /etc/systemd/system/oc-watchdog-stream.service; do
  [ -f "$f" ] && cp -a "$f" "${BACKUP_PATH}/systemd/"
done
[ -d /etc/systemd/system/ollama.service.d ] && cp -a /etc/systemd/system/ollama.service.d "${BACKUP_PATH}/systemd/" 2>/dev/null || true

mkdir -p "${BACKUP_PATH}/systemd-user"
cp -a "${HOME_DIR}/.config/systemd/user/openclaw-gateway.service" "${BACKUP_PATH}/systemd-user/" 2>/dev/null || true

# ── 14. 自定义脚本 ──
[ -d "${HOME_DIR}/.local/bin" ] && cp -a "${HOME_DIR}/.local/bin" "${BACKUP_PATH}/local-bin" 2>/dev/null || true

# ── 15. 用户 crontab ──
crontab -l 2>/dev/null > "${BACKUP_PATH}/crontab.txt" || true

# ── 16. 恢复说明 (先于 MANIFEST) ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed "s/{HOSTNAME}/${HOSTNAME}/g; s/{TS}/${TS}/g" \
  "${SCRIPT_DIR}/restore-template.md" > "${BACKUP_PATH}/RESTORE.md"
# 在备份包根目录放 README + 身份定位 + 记忆引导 + 系统快照
# 源文件由 workspace 管理（随 workspace 自动备份）
for f in README IDENTITY MEMORY-GUIDE SYSTEM-SNAPSHOT; do
  src="${SCRIPT_DIR}/backup-${f}.md"
  dst="${BACKUP_PATH}/${f}.md"
  [ -f "$src" ] && cp -a "$src" "$dst"
  # 同步到 /backup/ 目录（入口可见性）
  cp -a "$src" "/backup/${f}.md" 2>/dev/null || true
done

# ── 17. 备份清单 ──
find "${BACKUP_PATH}" -type f | sed "s|${BACKUP_PATH}/||" | sort > "${BACKUP_PATH}/MANIFEST.txt"
FILE_COUNT=$(wc -l < "${BACKUP_PATH}/MANIFEST.txt")
echo "[$(date)] 文件总数: ${FILE_COUNT}"

# ── 18. 打包 ──
echo "[$(date)] 打包中..."
cd "$BACKUP_DIR"
tar --zstd -cf "${TARBALL}" "${BACKUP_NAME}"
rm -rf "${BACKUP_PATH}"
zstd -t "${TARBALL}" 2>/dev/null || true

# ── 19. 清理旧备份 ──
COUNT=$(ls -1 "${BACKUP_DIR}/openclaw-full-"*.tar.zst 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$RETENTION" ]; then
  ls -1t "${BACKUP_DIR}/openclaw-full-"*.tar.zst | tail -n $(( COUNT - RETENTION )) | xargs rm -f
fi

# ── 20. 记录事件 ──
SIZE=$(ls -lh "${TARBALL}" | awk '{print $5}')
echo "{\"ts\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",\"event\":\"backup\",\"file\":\"${TARBALL}\",\"size\":\"${SIZE}\",\"files\":$FILE_COUNT,\"status\":\"ok\"}" \
  >> "${OC_DIR}/workspace/memory/data/system/backup-events.jsonl"

echo "[$(date)] === 备份完成: ${TARBALL} (${SIZE}, ${FILE_COUNT} files) ==="
