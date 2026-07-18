// billing-loader.mjs — 单用途 preload: 仅加载 billing-snapshotter
// 幂等锁：O_EXCL 原子创建（POSIX 保证，跨执行环境有效）
import fs from "node:fs";
import path from "node:path";

const LOCK = "/tmp/openclaw-billing-snapshotter.lock";
let acquired = false;

try {
  fs.mkdirSync(path.dirname(LOCK), { recursive: true });
  const fd = fs.openSync(
    LOCK,
    fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_WRONLY,
    0o644
  );
  fs.writeSync(fd, JSON.stringify({
    pid: process.pid,
    time: Date.now(),
    module: "billing-loader"
  }) + "\n");
  fs.closeSync(fd);
  acquired = true;
} catch (err) {
  if (err.code === "EEXIST") {
    console.log("[OEK:BILLING-LOADER] duplicate execution blocked by lock (pid=" + process.pid + ")");
  } else {
    throw err;
  }
}

if (acquired) {
  console.log("[OEK:BILLING-LOADER] loaded pid=" + process.pid + " ts=" + Date.now() + " lock=" + LOCK);
  await import("./billing-snapshotter.mjs");
}
