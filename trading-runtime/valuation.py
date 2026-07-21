#!/usr/bin/env python3
"""
trading-runtime — valuation.py

职责: 持仓估值 — 基于行情快照计算浮盈浮亏、权益、保证金

输入: 持仓字典 + 行情快照
      持仓: {"RB": {"qty": 1, "avg_cost": 3300}, ...}
      行情: {"RB": {"price": 3320}, ...}

输出: ValuationResult
      {
        "symbol": "RB",
        "qty": 1,
        "direction": "LONG",
        "avg_cost": 3300.0,
        "current_price": 3320.0,
        "unrealized_pnl": 200.0,
        "margin_used": 3300.0,
        "risk_ratio": 0.0033,
      }

合约乘数和保证金率与 runtime_account 保持一致
"""

from runtime_account import CONTRACT_MULTIPLIER, MARGIN_RATE


class PositionValuation:
    """单品种持仓估值"""

    def __init__(self, symbol: str, qty: int, avg_cost: float):
        self.symbol = symbol
        self.qty = qty               # 正=多, 负=空
        self.avg_cost = avg_cost
        self.multiplier = CONTRACT_MULTIPLIER.get(symbol, 10)

    def value(self, current_price: float) -> dict:
        """计算当前估值"""
        direction = "LONG" if self.qty > 0 else "SHORT"
        pnl_per_unit = (current_price - self.avg_cost) if self.qty > 0 else (self.avg_cost - current_price)

        unrealized_pnl = round(pnl_per_unit * abs(self.qty) * self.multiplier, 2)
        margin_used = round(abs(self.qty) * self.avg_cost * self.multiplier * MARGIN_RATE, 2)
        notional = round(current_price * abs(self.qty) * self.multiplier, 2)
        risk_ratio = round(0 if notional == 0 else margin_used / notional, 4)

        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "direction": direction,
            "avg_cost": round(self.avg_cost, 2),
            "current_price": round(current_price, 2),
            "unrealized_pnl": unrealized_pnl,
            "margin_used": margin_used,
            "notional": notional,
            "risk_ratio": risk_ratio,
            "pnl_pct": round((current_price / self.avg_cost - 1) * 100 * (1 if self.qty > 0 else -1), 2),
        }

    def __repr__(self):
        return f"PositionValuation({self.symbol}: qty={self.qty}, cost={self.avg_cost})"


class PortfolioValuation:
    """组合估值 — 所有品种汇总"""

    def __init__(self, positions: dict[str, dict] | None = None):
        # positions: symbol → {"qty": int, "avg_cost": float}
        self.positions: dict[str, PositionValuation] = {}
        if positions:
            for sym, p in positions.items():
                if p.get("qty", 0) != 0:
                    self.positions[sym] = PositionValuation(
                        symbol=sym,
                        qty=p["qty"],
                        avg_cost=p.get("avg_cost", 0),
                    )

    def sync_from_account(self, account_positions: dict[str, dict]):
        """从 RuntimeAccount 同步持仓"""
        self.positions = {}
        for sym, p in account_positions.items():
            if p.get("qty", 0) != 0:
                self.positions[sym] = PositionValuation(
                    symbol=sym,
                    qty=p["qty"],
                    avg_cost=p.get("avg_cost", 0),
                )

    def value_all(self, market_snapshot: dict[str, dict]) -> list[dict]:
        """估值所有持仓"""
        results = []
        for sym, pv in self.positions.items():
            price_entry = market_snapshot.get(sym)
            if not price_entry:
                continue
            current_price = price_entry.get("price")
            if current_price is None:
                continue
            results.append(pv.value(current_price))
        return results

    def summary(self, market_snapshot: dict[str, dict] = None) -> dict:
        """估值汇总"""
        if market_snapshot is None:
            market_snapshot = {}

        valuations = self.value_all(market_snapshot)

        total_upnl = round(sum(v["unrealized_pnl"] for v in valuations), 2)
        total_margin = round(sum(v["margin_used"] for v in valuations), 2)

        return {
            "total_unrealized_pnl": total_upnl,
            "total_margin_used": total_margin,
            "positions": {v["symbol"]: v for v in valuations},
        }

    def compute_equity(self, balance: float, market_snapshot: dict[str, dict]) -> dict:
        """计算总权益"""
        vs = self.summary(market_snapshot)
        equity = round(balance + vs["total_unrealized_pnl"], 2)
        free_cash = round(equity - vs["total_margin_used"], 2)
        return {
            "balance": round(balance, 2),
            "equity": equity,
            "total_unrealized_pnl": vs["total_unrealized_pnl"],
            "total_margin_used": vs["total_margin_used"],
            "free_cash": free_cash,
            "margin_ratio": round(vs["total_margin_used"] / equity * 100, 2) if equity > 0 else 0,
        }
