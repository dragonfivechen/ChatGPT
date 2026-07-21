#!/usr/bin/env python3
"""
trading-runtime — runtime_account.py

职责: 消费 FILL 事件 → 维护持仓/账户/保证金 → 产出 POSITION_UPDATE

输入: FILL 事件流
      {
        "event_type": "FILL",
        "ts": "...", "symbol": "RB",
        "action": "BUY", "price": 3295, "qty": 1
      }

输出:
  - 内部状态: position, avg_cost, unrealized_pnl, balance
  - POSITION_UPDATE 事件 (可选写入 JSONL)
      {
        "event_type": "POSITION_UPDATE",
        "ts": "...",
        "symbol": "RB",
        "qty": 1,
        "avg_cost": 3295.0,
        "unrealized_pnl": 0.0
      }

规则:
  - BUY  → 增加多头 (qty > 0)
  - SELL → 增加空头 (qty < 0)
  - CLOSE → 平仓 (qty → 0)
  - 支持双向同时开仓（净持仓模式）
  - 保证金按品种合约乘数 x 价格 x 比率计算
  - 基于已实现盈亏更新 balance
"""

import json
import os
from typing import Optional

# ── 品种参数（与市场仿真一致）────────────────────────────────
CONTRACT_MULTIPLIER = {
    "RB": 10,   # 螺纹钢 10吨/手
    "I":  100,  # 铁矿石 100吨/手
    "JM": 60,   # 焦煤 60吨/手
    "CU": 5,    # 沪铜 5吨/手
    "AL": 5,    # 沪铝 5吨/手
    "SC": 1000, # 原油 1000桶/手
}

MARGIN_RATE = 0.10  # 默认保证金率 10%


class RuntimeAccount:
    """实时仿真账户"""

    def __init__(self, initial_balance: float = 1_000_000):
        self.balance = initial_balance          # 可用资金
        self.equity = initial_balance           # 总权益
        self.initial_balance = initial_balance

        # 持仓: symbol → {"qty": int, "avg_cost": float, "unrealized_pnl": float, "realized_pnl": float}
        self.positions: dict[str, dict] = {}
        self.position_log: list[dict] = []       # 每笔 FILL 后的快照
        self.updates: list[dict] = []             # POSITION_UPDATE 事件

    def apply_fill(self, fill: dict) -> dict:
        """处理一笔 FILL, 返回 POSITION_UPDATE"""
        sym = fill["symbol"]
        action = fill["action"].upper()
        price = float(fill["price"])
        qty = int(fill["qty"])
        ts = fill.get("ts", "")

        if sym not in self.positions:
            self.positions[sym] = {
                "qty": 0,
                "avg_cost": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
            }

        pos = self.positions[sym]
        multiplier = CONTRACT_MULTIPLIER.get(sym, 10)

        if action == "BUY":
            # 多头开仓
            total_cost = pos["avg_cost"] * abs(pos["qty"]) + price * qty
            pos["qty"] += qty
            pos["avg_cost"] = total_cost / abs(pos["qty"]) if pos["qty"] != 0 else 0

        elif action == "SELL":
            # 空头开仓
            total_cost = pos["avg_cost"] * abs(pos["qty"]) + price * qty
            pos["qty"] -= qty
            pos["avg_cost"] = total_cost / abs(pos["qty"]) if pos["qty"] != 0 else 0

        elif action == "CLOSE":
            # 平仓
            current_qty = pos["qty"]
            if current_qty == 0:
                return self._snapshot(sym, ts)

            direction = 1 if current_qty > 0 else -1
            close_qty = min(abs(current_qty), qty) * direction

            # 已实现盈亏
            if abs(close_qty) > 0:
                realized = (price - pos["avg_cost"]) * (-close_qty) * multiplier
                pos["realized_pnl"] += realized
                self.balance += realized
                pos["qty"] += close_qty  # 向零方向移动

            if pos["qty"] == 0:
                pos["avg_cost"] = 0.0

        # 记录快照
        snap = self._snapshot(sym, ts)
        self.position_log.append(snap)

        # 生成 UPDATE 事件
        update = {
            "event_type": "POSITION_UPDATE",
            "ts": ts,
            "symbol": sym,
            "qty": pos["qty"],
            "avg_cost": pos["avg_cost"],
            "realized_pnl": round(pos["realized_pnl"], 2),
            "account_balance": round(self.balance, 2),
            "account_equity": round(self.equity, 2),
        }
        self.updates.append(update)
        return update

    def mark_to_market(self, symbol: str, current_price: float):
        """按市价更新未实现盈亏（标记到市价）"""
        if symbol not in self.positions:
            return
        pos = self.positions[symbol]
        multiplier = CONTRACT_MULTIPLIER.get(symbol, 10)
        pos["unrealized_pnl"] = round(
            (current_price - pos["avg_cost"]) * pos["qty"] * multiplier, 2
        )

        # 总权益 = 可用资金 + 全部未实现盈亏
        total_upnl = sum(
            p["unrealized_pnl"] for p in self.positions.values()
        )
        self.equity = round(self.balance + total_upnl, 2)

    def get_margin(self, symbol: str) -> float:
        """计算某一品种的占用保证金"""
        if symbol not in self.positions or self.positions[symbol]["qty"] == 0:
            return 0.0
        pos = self.positions[symbol]
        multiplier = CONTRACT_MULTIPLIER.get(symbol, 10)
        return round(
            abs(pos["qty"]) * pos["avg_cost"] * multiplier * MARGIN_RATE, 2
        )

    def total_margin(self) -> float:
        return round(sum(self.get_margin(s) for s in self.positions), 2)

    def summary(self) -> dict:
        """账户总览"""
        return {
            "initial_balance": self.initial_balance,
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "total_margin": self.total_margin(),
            "free_cash": round(self.equity - self.total_margin(), 2),
            "total_realized_pnl": round(
                sum(p["realized_pnl"] for p in self.positions.values()), 2
            ),
            "positions": {
                s: {"qty": p["qty"], "avg_cost": p["avg_cost"],
                    "unrealized_pnl": p["unrealized_pnl"],
                    "realized_pnl": round(p["realized_pnl"], 2)}
                for s, p in self.positions.items() if p["qty"] != 0
            },
        }

    def save_updates(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for u in self.updates:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")
        print(f"[runtime_account] 💾 {len(self.updates)} POSITION_UPDATE → {path}")

    def _snapshot(self, symbol: str, ts: str) -> dict:
        pos = self.positions.get(symbol, {"qty": 0, "avg_cost": 0.0})
        return {
            "ts": ts,
            "symbol": symbol,
            "qty": pos["qty"],
            "avg_cost": pos["avg_cost"],
        }
