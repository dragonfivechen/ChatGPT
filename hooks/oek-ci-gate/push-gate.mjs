// OEK Push Gate - 推送接口 (Telegram + GitHub Gist)
// Token 从独立 secrets 文件读取，不硬编码

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const secretsPath = join(__dirname, "../../.secrets/push-gate.json");

let secrets;
try {
  secrets = JSON.parse(readFileSync(secretsPath, "utf-8"));
} catch {
  console.error("[OEK:PUSH] missing or unreadable secrets file:", secretsPath);
  secrets = {};
}

const GITHUB_TOKEN = secrets.github_token || "";
const GIST_API = "https://api.github.com/gists";
const TG_BOT_TOKEN = secrets.telegram_bot_token || "";
const TG_API = "https://api.telegram.org/bot" + TG_BOT_TOKEN + "/sendMessage";
const MY_CHAT_ID = secrets.telegram_chat_id || "";

async function pushToGist(title, body) {
  if (!GITHUB_TOKEN) return null;
  const description = "[OEK] " + title;
  const res = await fetch(GIST_API, {
    method: "POST",
    headers: { "Authorization": "Bearer " + GITHUB_TOKEN, "Content-Type": "application/json" },
    body: JSON.stringify({ description, public: false, files: { "n.md": { content: body } } }),
  });
  if (!res.ok) return null;
  return (await res.json()).html_url;
}

async function pushToTelegram(text, opts = {}) {
  if (!TG_BOT_TOKEN || !MY_CHAT_ID) return false;
  const payload = { chat_id: MY_CHAT_ID, text: String(text).slice(0, 4000) };
  if (opts.parse_mode) payload.parse_mode = opts.parse_mode;
  const res = await fetch(TG_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.ok;
}

export async function notify(title, body, opts = {}) {
  const content = "🧾 " + title + "\n" + body;
  const [gistUrl] = await Promise.all([
    pushToGist(title, body).catch(() => null),
    pushToTelegram(content, opts).catch(() => null),
  ]);
  return gistUrl;
}
