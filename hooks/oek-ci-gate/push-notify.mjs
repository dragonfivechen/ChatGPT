// push-notify.mjs — CLI 推送入口
// Usage: node push-notify.mjs <title> <body> [parse_mode]

import { notify } from "./push-gate.mjs";

const title = process.argv[2] || "";
const body = process.argv[3] || "";
const parseMode = process.argv[4] || "";

if (!title && !body) {
  console.error("[PUSH-NOTIFY] usage: node push-notify.mjs <title> <body> [parse_mode]");
  process.exit(1);
}

await notify(title, body, parseMode ? { parse_mode: parseMode } : {});
