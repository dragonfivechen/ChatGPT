"""
trading-runtime — preloader.py (盘前预采集)

职责:
  - 盘前指定时间加载历史行情 (策略预热窗口)
  - 恢复上一交易日的账户/持仓/风险状态
  - 准备策略运行时需要的所有数据
  - 不产生交易, 只做准备

使用:
  preloader = Preloader(session_config)
  data = preloader.prepare()  # → {state, history, status}
"""

import csv
import json
import os
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
WORKSPACE = os.path.dirname(os.path.abspath(__file__))


def _find_latest_state(state_dir: str = None) -> str | None:
    """查找最新的状态保存目录"""
    if state_dir is None:
        state_dir = os.path.join(WORKSPACE, "state")
    if not os.path.isdir(state_dir):
        return None
    dirs = sorted([
        d for d in os.listdir(state_dir)
        if d.startswith("session_") and
        os.path.isdir(os.path.join(state_dir, d))
    ])
    return os.path.join(state_dir, dirs[-1]) if dirs else None


def load_state_from_dir(state_path: str) -> dict:
    """加载状态目录中的所有文件"""
    result = {}

    acct_path = os.path.join(state_path, "account.json")
    if os.path.exists(acct_path):
        with open(acct_path, "r", encoding="utf-8") as f:
            result["account"] = json.load(f)

    meta_path = os.path.join(state_path, "state_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            result["state_meta"] = json.load(f)

    risk_path = os.path.join(state_path, "risk_snapshots.jsonl")
    if os.path.exists(risk_path):
        snapshots = []
        with open(risk_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    snapshots.append(json.loads(line))
        result["risk_snapshots"] = snapshots

    return result


def load_history_csv(csv_path: str, max_rows: int = 120) -> list[dict]:
    """加载历史行情CSV的前N行"""
    result = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                result.append(row)
    except (FileNotFoundError, StopIteration):
        pass
    return result


class Preloader:
    """盘前预采集器"""

    def __init__(self, config: dict, data_dir: str = None,
                 state_dir: str = None):
        """
        Args:
            config: session_config.json 内容
            data_dir: 历史行情目录 (默认 market_futures/data/historical)
            state_dir: 状态目录 (默认 state/)
        """
        self.config = config
        self.data_dir = data_dir or os.path.join(
            WORKSPACE, "..", "market_futures", "data", "historical")
        self.state_dir = state_dir or os.path.join(WORKSPACE, "state")
        self._prepared = False
        self._prepared_data = None

    def prepare(self, symbols: list[str] = None,
                lookback: int = None) -> dict:
        """
        执行盘前准备 — 加载行情历史 + 恢复状态

        Returns:
            dict: {
                "prepared_at": "ISO时间",
                "symbols": [...],
                "state_restored": bool,
                "state_path": str | None,
                "history": {sym: [rows...], ...},
                "state": {...} | None,
                "status": "OK" | "PARTIAL" | "FAILED"
            }
        """
        lookback = lookback or self.config.get("data", {}).get(
            "history_lookback", 120)
        symbols = symbols or self.config.get("data", {}).get(
            "symbols", ["RB", "I", "JM", "CU", "AL", "SC"])

        result = {
            "prepared_at": datetime.now(BJT).isoformat(),
            "symbols": symbols,
            "state_restored": False,
            "state_path": None,
            "history": {},
            "state": None,
            "status": "OK",
        }

        # ── 加载行情历史 ──
        loaded_count = 0
        for sym in symbols:
            csv_path = os.path.join(self.data_dir, f"{sym}_2022-2026.csv")
            rows = load_history_csv(csv_path, lookback)
            if rows:
                result["history"][sym] = rows
                loaded_count += 1
            else:
                print(f"[preloader] ⚠️ 未找到 {sym} 历史数据: {csv_path}")

        if loaded_count == 0:
            result["status"] = "FAILED"
            print("[preloader] ❌ 无历史数据加载")

        # ── 恢复状态 ──
        latest = _find_latest_state(self.state_dir)
        if latest:
            state_data = load_state_from_dir(latest)
            if state_data:
                result["state_restored"] = True
                result["state_path"] = latest
                result["state"] = state_data
                print(f"[preloader] 🔄 状态恢复: {latest}")
            else:
                print(f"[preloader] ⚠️ 状态目录存在但内容为空: {latest}")
        else:
            print("[preloader] 🔄 无历史状态, 全新启动")

        self._prepared = True
        self._prepared_data = result

        print(f"[preloader] ✅ 盘前准备完成: "
              f"{loaded_count}/{len(symbols)} 品种, "
              f"{'状态恢复' if result['state_restored'] else '无状态'}")

        return result

    @property
    def prepared(self) -> bool:
        return self._prepared

    @property
    def prepared_data(self) -> dict | None:
        return self._prepared_data

    def summary(self) -> dict:
        """准备结果摘要"""
        if not self._prepared_data:
            return {"status": "NOT_PREPARED"}
        d = self._prepared_data
        return {
            "status": d["status"],
            "prepared_at": d["prepared_at"],
            "symbols_loaded": len(d.get("history", {})),
            "total_bars": sum(len(v) for v in d.get("history", {}).values()),
            "state_restored": d["state_restored"],
            "state_path": d["state_path"],
        }
