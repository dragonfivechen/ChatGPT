# 🛟 OpenClaw 全量系统备份

## 系统崩溃了？从这里开始

1. **找到最新备份**
   ```bash
   ls -1t /backup/openclaw-full-*.tar.zst | head -1
   ```

2. **解压**
   ```bash
   tar --zstd -xf /backup/openclaw-full-最新时间戳.tar.zst
   ```

3. **读里面的 RESTORE.md**
   ```bash
   cat openclaw-full-*/RESTORE.md
   ```

4. **按步骤恢复**（共 4 步，约 10 分钟）

---

## 恢复后可以期待什么

| 项目 | 是否恢复 |
|------|---------|
| 对话历史 | ✅ 全部会话 |
| 记忆文件 | ✅ MEMORY.md + 日记 |
| API 凭证 | ✅ auth-profiles |
| Telegram bot 状态 | ✅  |
| Ollama 模型 (qwen2.5:3b) | ✅  |
| 系统定时任务 | ✅ crontab |
| 传感器数据 | ✅ 每小时采集 |
| 自定义脚本 | ✅ .local/bin |

---

## 如果恢复失败

看 RESTORE.md 末尾的故障排查表。还不行？回到 `~/.openclaw.bak` 快照。

---

## 备份周期

每日 03:00 自动全量，保留最近 7 份。
