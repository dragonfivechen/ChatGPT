# 全量恢复说明 — {HOSTNAME}

备份时间: {TS}
主机用户: dragonfive

> ⚠️ **在开始恢复之前，先读同目录下的 MEMORY-GUIDE.md 确认你的身份。**
> 系统有两个模型身份（燃🔥/烬🔥），记忆严格隔离，读错会导致逻辑污染。

## 前置条件

1. 安装基础软件（如尚未安装）：
   - OpenClaw: `npm install -g openclaw`
   - Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. 确保 DEEPSEEK_API_KEY 环境变量已设置（可从 openclaw-auth/auth-profiles.json 获取）
3. 当前工作目录为备份包解压后的根目录（即 RESTORE.md 所在目录）

> 恢复前建议先对现有系统做一次快照：`cp -a ~/.openclaw ~/.openclaw.bak`

---

## 步骤 1 — 恢复 OpenClaw 运行态

```bash
# 停止 gateway
systemctl --user stop openclaw-gateway 2>/dev/null || echo "gateway 未运行，跳过"

# 确保目标目录存在
mkdir -p ~/.openclaw/agents/main/agent
mkdir -p ~/.openclaw/agents/main/sessions

# 恢复全部 (保持原有权限)
cp -a openclaw.json ~/.openclaw/
cp -a openclaw-config-history/*.bak* ~/.openclaw/ 2>/dev/null
cp -a openclaw-workspace ~/.openclaw/
cp -a openclaw-auth/* ~/.openclaw/agents/main/agent/
cp -a openclaw-credentials ~/.openclaw/
cp -a openclaw-identity ~/.openclaw/
cp -a openclaw-telegram ~/.openclaw/
cp -a openclaw-sessions/* ~/.openclaw/agents/main/sessions/
cp -a openclaw-state/* ~/.openclaw/
cp -a openclaw-cron/* ~/.openclaw/cron/
cp -a openclaw-db/* ~/.openclaw/memory/ 2>/dev/null
cp -a openclaw-delivery-queue ~/.openclaw/ 2>/dev/null
cp -a openclaw-etc/* ~/.openclaw/ 2>/dev/null

# 从 auth-profiles.json 中提取 API key
AUTH_FILE=~/.openclaw/agents/main/agent/auth-profiles.json
if [ -f "$AUTH_FILE" ]; then
  KEY=$(python3 -c "import json; profiles=json.load(open('$AUTH_FILE')).get('profiles',{}); [print(p.get('key','')) for p in profiles.values() if p.get('key')]" 2>/dev/null | head -1)
  if [ -n "$KEY" ]; then
    echo "DEEPSEEK_API_KEY=$KEY" >> ~/.openclaw/.env 2>/dev/null || true
    export DEEPSEEK_API_KEY="$KEY"
    echo "API key 已恢复"
  fi
fi

# 写入恢复标记（确保所有模型在下次会话启动时感知到恢复）
MEM=~/.openclaw/workspace/MEMORY.md
cat >> "$MEM" << MARK

## ⚠️ 系统恢复记录

- 系统于 {TS} 从全量备份恢复
- 当前为恢复后运行态，所有记忆/会话/配置已恢复
- 如果你正在处理系统维护任务，确认你读到的是正确的身份记忆
- 不要交叉读取 huo/ 和 jin/ 两个身份的记忆文件

MARK
echo "恢复标记已写入 MEMORY.md"

# 启动
systemctl --user daemon-reload
systemctl --user start openclaw-gateway
```

---

## 步骤 2 — 恢复 Ollama

```bash
sudo systemctl stop ollama 2>/dev/null || echo "ollama 未安装"

# systemd 配置
sudo cp -a systemd/ollama.service /etc/systemd/system/
sudo cp -a systemd/ollama.service.d /etc/systemd/system/ 2>/dev/null
sudo systemctl daemon-reload

# 模型文件
sudo mkdir -p /usr/share/ollama/.ollama/models
sudo cp -a ollama-models/blobs /usr/share/ollama/.ollama/models/
sudo cp -a ollama-models/manifests /usr/share/ollama/.ollama/models/
sudo chown -R ollama:ollama /usr/share/ollama/.ollama/models/

sudo systemctl start ollama
```

---

## 步骤 3 — 恢复自定义服务 + 脚本

```bash
# Watchdog
sudo cp -a systemd/oc-watchdog-stream.service /etc/systemd/system/
sudo systemctl daemon-reload

# 自定义脚本
mkdir -p ~/.local/bin
cp -a local-bin/* ~/.local/bin/

# 用户 crontab (全部定时任务)
crontab crontab.txt
echo "当前 crontab:"
crontab -l
```

---

## 步骤 4 — 完整验证

```bash
echo "=== 服务状态 ==="
systemctl --user status openclaw-gateway --no-pager | head -3
sudo systemctl status ollama --no-pager | head -3
systemctl status oc-watchdog-stream --no-pager 2>/dev/null | head -3

echo ""
echo "=== 模型 ==="
ollama list

echo ""
echo "=== 传感器数据 ==="
ls -lh ~/.openclaw/workspace/memory/events/

echo ""
echo "=== 记忆文件 ==="
ls ~/.openclaw/workspace/memory/*.md 2>/dev/null
ls ~/.openclaw/workspace/MEMORY.md 2>/dev/null || echo "(MEMORY.md 尚未创建)"

echo ""
echo "=== 记忆自检 ==="
FILES=$(ls ~/.openclaw/workspace/memory/*.md ~/.openclaw/workspace/SOUL.md ~/.openclaw/workspace/AGENTS.md ~/.openclaw/workspace/USER.md 2>/dev/null | wc -l)
echo "身份/记忆文件数: $FILES"
echo "首次对话时模型将自动加载这些记忆。"

echo ""
echo "=== 推送测试 ===
node ~/.openclaw/workspace/hooks/oek-ci-gate/push-notify.mjs "恢复验证" "系统已从 {TS} 备份恢复"
```

---

## 记忆恢复说明

OpenClaw 的记忆系统是文件驱动的。恢复工作区后，记忆已自动就位：

| 文件 | 作用 | 加载方式 |
|------|------|---------|
| MEMORY.md | 长期记忆（偏好/决策/事实） | 每次 DM 对话自动加载 |
| memory/YYYY-MM-DD.md | 日记/上下文 | 当天+昨天自动加载 |
| memory/events/*.jsonl | 传感器事实数据 | 通过 memory_search 查询 |
| SOUL.md / AGENTS.md / USER.md | 身份/规则 | 每次会话启动自动加载 |

**记忆不需要额外激活。** 文件存在→OpenClaw 启动时自动读取→新模型感知到记忆。

验证：恢复后首次对话，模型应能回答自己的身份、用户名字、系统状态。

---

## 回滚

如果恢复后系统异常，回退到备份前的状态：

```bash
systemctl --user stop openclaw-gateway
sudo systemctl stop ollama

if [ -d ~/.openclaw.bak ]; then
  rm -rf ~/.openclaw
  mv ~/.openclaw.bak ~/.openclaw
  echo "已回退到备份前状态"
fi

systemctl --user start openclaw-gateway
```

---

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| gateway 启动失败 | API key 未设置 | `export DEEPSEEK_API_KEY` |
| gateway 启动失败 | systemd user service 丢失 | 见步骤 3 |
| ollama 无模型 | 模型路径权限错误 | `sudo chown -R ollama:ollama /usr/share/ollama/.ollama/models/` |
| 传感器数据空白 | 恢复后未到整点 | 等待下一个整点或手动执行 collect-sensors.sh |
| 推送失败 | push-gate.json 权限 | `chmod 600 ~/.openclaw/workspace/.secrets/push-gate.json` |
