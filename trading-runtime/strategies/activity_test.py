"""
trading-runtime — strategies/activity_test.py (活动测试策略)

目的: 不是赚钱, 是验证交易链路持续产生数据

规则:
  1. 行情驱动: 每 N 根 QUOTE 触发一次检查
  2. 无持仓 → BUY 1手 (随机选一个品种)
  3. 有持仓 → 价格朝有利方向移动 X% → CLOSE
  4. 有持仓 → 价格朝不利方向移动 Y% → CLOSE (止损退出)
  5. 循环

行为保证:
  - 只要有行情输入, 就稳定产生 SIGNAL
  - 不受市场趋势/震荡影响
  - 适合验证 QUOTE → SIGNAL → ORDER → FILL → POSITION 闭环

输入: FUTURES_QUOTE dict (单条)
输出: FUTURES_SIGNAL dict | None
"""

from collections import deque
from typing import Optional
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# 品种优先级 (按波动率排序, 优先选活跃品种)
PREFERRED_SYMBOLS = ["SC", "CU", "I", "RB", "JM", "AL"]


class ActivityTest:
    """
    活动测试策略 — 高频触发验证

    状态机: IDLE → (N行情) → OPENING → (已开仓) → HOLDING → (达成条件) → CLOSING → IDLE
    """

    def __init__(self, strategy_id: str = "ActivityTest",
                 entry_every_n: int = 3,
                 take_profit_pct: float = 0.5,
                 stop_loss_pct: float = -0.3,
                 max_hold_bars: int = 10,
                 qty: int = 1):
        """
        Args:
            entry_every_n: 每 N 根 QUOTE 尝试开仓
            take_profit_pct: 浮盈达此百分比, 平仓
            stop_loss_pct: 浮亏达此百分比, 平仓
            max_hold_bars: 持仓超过 N 根 QUOTE, 强制平仓
            qty: 每笔交易手数
        """
        self.strategy_id = strategy_id
        self.entry_every_n = entry_every_n
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_bars = max_hold_bars
        self.qty = qty

        # 品种状态
        self._quote_count: dict[str, int] = {}
        self._position: dict[str, dict] = {}       # symbol → {"entry_price": float, "bars_held": int}
        self._last_signal_ts: dict[str, str] = {}

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[dict]:
        """
        收到单条行情 → 返回策略信号 or None

        Args:
            quote: FUTURES_QUOTE event dict
            position_info: 当前运行时持仓信息 {symbol: {"qty": int, ...}}

        Returns:
            FUTURES_SIGNAL dict or None
        """
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        # 更新引号计数
        self._quote_count[symbol] = self._quote_count.get(symbol, 0) + 1

        # ── 持仓检查 ──
        current_pos = None
        if position_info and isinstance(position_info, dict):
            pos = position_info.get(symbol)
            if pos and pos.get("qty", 0) != 0:
                current_pos = pos

        # ── 有持仓: 检查平仓条件 ──
        if symbol in self._position:
            entry = self._position[symbol]
            entry_price = entry["entry_price"]
            entry["bars_held"] = entry.get("bars_held", 0) + 1
            bars_held = entry["bars_held"]

            # 计算收益率 (基于开仓价)
            pnl_pct = (price - entry_price) / entry_price * 100

            # 条件: 止盈 / 止损 / 超时
            if pnl_pct >= self.take_profit_pct:
                del self._position[symbol]
                return self._make_signal(symbol, "CLOSE",
                                         f"止盈 {pnl_pct:+.2f}% (目标{self.take_profit_pct:+.1f}%)")

            if pnl_pct <= self.stop_loss_pct:
                del self._position[symbol]
                return self._make_signal(symbol, "CLOSE",
                                         f"止损 {pnl_pct:+.2f}% (阈值{self.stop_loss_pct:+.1f}%)")

            if bars_held >= self.max_hold_bars:
                del self._position[symbol]
                return self._make_signal(symbol, "CLOSE",
                                         f"超时平仓 (持仓{bars_held}条)")

            return None  # 继续持有

        # ── 无持仓: 检查开仓条件 ──
        if current_pos is None:
            if self._quote_count[symbol] >= self.entry_every_n:
                self._quote_count[symbol] = 0
                self._position[symbol] = {
                    "entry_price": price,
                    "bars_held": 0,
                }
                return self._make_signal(symbol, "BUY",
                                         f"开仓 ¥{price:.1f}")

        return None

    def sync_positions(self, position_info: dict):
        """
        从运行时账户同步持仓状态

        如果账户中有持仓但本策略未记录, 同步进来。
        如果本策略标记了持仓但账户中已没有, 清除策略状态。
        """
        if not position_info:
            return

        # 清除账户中已平的持仓
        for sym in list(self._position.keys()):
            pos = position_info.get(sym)
            if pos is None or pos.get("qty", 0) == 0:
                del self._position[sym]

    def _make_signal(self, symbol: str, action: str, note: str) -> dict:
        return {
            "event_type": "FUTURES_SIGNAL",
            "ts": datetime.now(BJT).isoformat(),
            "strategy_id": self.strategy_id,
            "symbol": symbol,
            "action": action,
            "qty": self.qty,
            "confidence": 0.5,
            "note": note,
        }

    def reset(self):
        self._quote_count.clear()
        self._position.clear()
        self._last_signal_ts.clear()

    def summary(self) -> dict:
        """当前状态"""
        return {
            "watch_symbols": list(self._quote_count.keys()),
            "open_positions": {
                sym: {
                    "entry_price": v["entry_price"],
                    "bars_held": v.get("bars_held", 0),
                }
                for sym, v in self._position.items()
            },
            "total_quotes_observed": sum(self._quote_count.values()),
        }
