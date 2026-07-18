import fs from "node:fs";
import path from "node:path";
import os from "node:os";

// ── DeepSeek API key from secrets ──
const __dirname = path.dirname(new URL(import.meta.url).pathname);
let DS_KEY = "";
try {
  const secrets = JSON.parse(
    fs.readFileSync(path.join(__dirname, "../../.secrets/push-gate.json"), "utf-8")
  );
  DS_KEY = secrets.deepseek_api_key || "";
} catch {
  console.error("[OEK:BILLING] failed to load deepseek_api_key from secrets");
}

const DS_API = "https://api.deepseek.com/user/balance";
const DATA_DIR = path.join(os.homedir(), ".openclaw");
const SNAPSHOTS_FILE = path.join(DATA_DIR, "balance_snapshots.jsonl");
const BILLING_FILE = path.join(DATA_DIR, "billing_state.json");
const DAILY_FILE = path.join(DATA_DIR, "daily_state.json");
const DAILY_HISTORY_FILE = path.join(DATA_DIR, "daily_history.jsonl");
const LOCKS_DIR = path.join(os.homedir(), ".openclaw/locks");

let running = false;
let dailyState = null;

// ── Load persisted state on startup ──
dailyState = loadDailyState();

// ── Helpers ──

function todayCST() {
  const now = new Date();
  const off = 8 * 60;
  const local = new Date(now.getTime() + off * 60 * 1000);
  return local.toISOString().slice(0, 10);
}

function nowCST() {
  return new Date().toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" });
}

function ceil10(v) {
  return Math.ceil(v / 10) * 10;
}

// ── Daily State Persistence ──

function loadDailyState() {
  try {
    if (!fs.existsSync(DAILY_FILE)) return null;
    const raw = fs.readFileSync(DAILY_FILE, "utf-8").trim();
    if (!raw) return null;
    const state = JSON.parse(raw);
    if (state.date !== todayCST()) return null;
    return state;
  } catch { return null; }
}

function saveDailyState(state) {
  try {
    fs.writeFileSync(DAILY_FILE, JSON.stringify(state, null, 2) + "\n");
  } catch (e) {
    console.error("[OEK:BILLING] saveDailyState failed:", e.message);
  }
}

function appendHistory(state) {
  try {
    fs.mkdirSync(path.dirname(DAILY_HISTORY_FILE), { recursive: true });
    fs.appendFileSync(DAILY_HISTORY_FILE,
      JSON.stringify({
        date: state.date,
        start_balance: state.start_balance,
        end_balance: state.current_balance,
        anchor_balance: state.anchor_balance,
        today_consumption: state.today_consumption,
        recharge: state.recharge,
        archived_at: new Date().toISOString(),
      }) + "\n");
  } catch (e) {
    console.error("[OEK:BILLING] appendHistory failed:", e.message);
  }
}

function initDailyState(latestBalance) {
  const today = todayCST();
  let startBal = latestBalance;
  let consumption = 0;
  let recharge = 0;

  try {
    if (fs.existsSync(SNAPSHOTS_FILE)) {
      const lines = fs.readFileSync(SNAPSHOTS_FILE, "utf-8").split("\n").filter(l => l.trim());
      function utcTsToCstDate(utcTs) {
        const d = new Date(utcTs);
        const cst = new Date(d.getTime() + 8 * 60 * 60 * 1000);
        return cst.toISOString().slice(0, 10);
      }
      const todaySnaps = lines
        .map(l => JSON.parse(l))
        .filter(s => utcTsToCstDate(s.ts) === today)
        .map(s => s.total_balance);

      if (todaySnaps.length > 1) {
        startBal = todaySnaps[0];
        for (let i = 1; i < todaySnaps.length; i++) {
          const delta = parseFloat((todaySnaps[i] - todaySnaps[i - 1]).toFixed(3));
          if (delta < -0.001) {
            consumption = parseFloat((consumption + Math.abs(delta)).toFixed(3));
          } else if (delta > 0.001) {
            recharge = parseFloat((recharge + ceil10(delta)).toFixed(3));
          }
        }
      }
    }
  } catch {}

  return {
    date: today,
    start_balance: startBal,
    anchor_balance: parseFloat((startBal + recharge).toFixed(3)),
    current_balance: latestBalance,
    today_consumption: consumption,
    recharge: recharge,
  };
}

// ── API ──

async function fetchBalance() {
  const res = await fetch(DS_API, {
    headers: { "Authorization": "Bearer " + DS_KEY, "Accept": "application/json" },
  });
  if (!res.ok) throw new Error("HTTP " + res.status);
  const data = await res.json();
  if (data.balance_infos && data.balance_infos[0]) {
    return {
      balance: parseFloat(data.balance_infos[0].total_balance),
      currency: data.balance_infos[0].currency,
      available: data.is_available,
    };
  }
  throw new Error("unexpected response");
}

// ── Core: Snapshot + Delta Update ──

async function snapshot() {
  if (running) return;
  running = true;
  try {
    const info = await fetchBalance();
    const bal = info.balance;
    const ts = new Date().toISOString();

    // 1. Raw snapshot (permanent)
    fs.mkdirSync(path.dirname(SNAPSHOTS_FILE), { recursive: true });
    fs.appendFileSync(SNAPSHOTS_FILE, JSON.stringify({
      ts, date: ts.slice(0, 10), total_balance: bal,
      granted_balance: 0, topped_up_balance: bal, trajectory_cost: 0,
    }) + "\n");

    // 2. billing_state.json
    fs.writeFileSync(BILLING_FILE, JSON.stringify({
      balance: bal, total_spent: 0, last_updated: ts,
      provider: "deepseek", currency: info.currency,
    }, null, 2) + "\n");

    // 3. Daily state (delta-based)
    let state = loadDailyState();
    if (!state) {
      // 跨日归档：memory 或文件中的旧日数据都不可丢弃
      if (dailyState && dailyState.date !== todayCST()) {
        appendHistory(dailyState);
      } else {
        // memory 为空但文件有旧数据（如 daemon 重启后跨日）
        try {
          const oldRaw = fs.readFileSync(DAILY_FILE, 'utf-8').trim();
          if (oldRaw) {
            const oldState = JSON.parse(oldRaw);
            if (oldState.date && oldState.date !== todayCST()) {
              appendHistory(oldState);
            }
          }
        } catch {}
      }
      state = initDailyState(bal);
    } else {
      const prev = state.current_balance;
      const delta = parseFloat((bal - prev).toFixed(3));
      state.current_balance = bal;
      if (delta < -0.001) {
        state.today_consumption = parseFloat((state.today_consumption + Math.abs(delta)).toFixed(3));
      } else if (delta > 0.001) {
        state.recharge = parseFloat((state.recharge + ceil10(delta)).toFixed(3));
        state.anchor_balance = parseFloat((state.start_balance + state.recharge).toFixed(3));
      }
    }
    saveDailyState(state);
    dailyState = state;

    console.log("[OEK:BILLING] snapshotted " + info.currency + " " + bal.toFixed(2)
      + " | today=" + state.today_consumption.toFixed(3) + " recharge=" + state.recharge);
  } catch (e) {
    console.error("[OEK:BILLING] snapshot failed:", e.message);
  } finally {
    running = false;
  }
}

// ── Push Report ──
let lastPushTs = 0;
const PUSH_COOLDOWN = 3_600_000; // 1小时

async function pushReport() {
  const state = dailyState || loadDailyState();
  if (!state) return;

  // 防重复：同一次消费变化只推一次
  const now = Date.now();
  if (now - lastPushTs < 1_800_000) { // 30分钟内不重复推
    console.log("[OEK:BILLING] push skipped (cooldown)");
    return;
  }
  lastPushTs = now;

  const bal = state.current_balance;
  const dateStr = new Date().toLocaleDateString("zh-CN", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit"
  }).replace(/\//g, "/");
  const timeStr = new Date().toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit"
  });

  // 上一日消耗（取 daily_history.jsonl 最新归档）
  let yesterdayStr = "";
  try {
    const now = new Date();
    const cstOffset = 8 * 60;
    const cstNow = new Date(now.getTime() + cstOffset * 60 * 1000);
    const yesterdayIso = new Date(cstNow.getTime() - 86400000).toISOString().slice(0, 10);

    if (fs.existsSync(DAILY_HISTORY_FILE)) {
      const lines = fs.readFileSync(DAILY_HISTORY_FILE, "utf-8").split("\n").filter(l => l.trim());
      const yesterdayEntries = lines
        .map(l => JSON.parse(l))
        .filter(e => e.date === yesterdayIso);
      if (yesterdayEntries.length > 0) {
        const lastEntry = yesterdayEntries[yesterdayEntries.length - 1];
        yesterdayStr = "\ud83d\udcc9 \u6628\u65e5:" + lastEntry.today_consumption.toFixed(3) + "\n";
      }
    }
  } catch {}

  const body = "\ud83d\udcb0 \u4f59\u989d:" + bal.toFixed(2) + "\n"
    + "\ud83d\udcc9 \u4eca\u65e5:" + state.today_consumption.toFixed(3) + "\n"
    + yesterdayStr
    + "\ud83d\udcc8 \u5145\u503c:" + state.recharge.toFixed(3) + "\n"
    + "\ud83c\udfc1 \u8d77\u59cb:" + state.start_balance.toFixed(2) + "\n"
    + "\u2693 \u951a\u70b9:" + state.anchor_balance.toFixed(2);

  const title = "DeepSeek\u8d26\u5355";
  try {
    const { notify } = await import("./push-gate.mjs");
    console.log("[OEK:BILLING] pushing report, bal=" + bal + " today=" + state.today_consumption);
    await notify(title, body);
    console.log("[OEK:BILLING] push done");
  } catch (e) {
    console.error("[OEK:BILLING] push failed:", e.message);
  }
}

// 幂等保护：process 全局变量（跨 ESM 模块实例共享）
if (!process.__oekBillingStarted) {
  process.__oekBillingStarted = true;

  // Phase 2: interval 调度已移除，调度权回归 systemd timer
  // 保留初始 snapshot 作为数据预热（入口 worker 会再次调用主函数）
  snapshot();
}

export { snapshot, fetchBalance, pushReport };
