#!/usr/bin/env python3
"""
Futures-Sim v0.1 — account.py（期货账户）

职责:
  - 管理现金余额、保证金、动态权益
  - 处理成交入账（FUTURES_FILL → 更新持仓+资金）
  - 逐日盯市结算（FUTURES_SETTLEMENT）
  - 风险率计算 + 强平触发
  - 交易记录追踪（trades.jsonl 回调）

依赖:
  - position.py (Position / Positions / LONG / SHORT)
  - futures_contracts.json（合约定义）

冻结约束:
  - 每个品种单一方向净持仓
  - 保证金 = 最新价 × 乘数 × 手数 × 保证金率
  - 风险率 < 1.0 → 强平
  - 不支持锁仓
"""

from __future__ import annotations
import json
import os
from typing import Optional, Callable
from position import Position, Positions, LONG, SHORT


# ─── 合约加载 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_PATH = os.path.join(BASE_DIR, "futures_contracts.json")


def _load_contract(symbol: str) -> dict:
    """加载单个合约配置"""
    with open(CONTRACTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["contracts"][symbol]


DEFAULT_INITIAL_EQUITY = 1_000_000.0


class FuturesAccount:
    """模拟期货账户

    核心属性:
      balance        — 现金余额（含已实现盈亏，不含浮动盈亏）
      positions      — 持仓集合 (Positions)
      floating_pnl   — 浮动盈亏（按最新价计算）
      margin_used    — 保证金占用
      equity         — 动态权益 = balance + floating_pnl
      available      — 可用资金 = equity - margin_used
      risk_ratio     — 风险率 = equity / margin_used (∞ 当无持仓)

    事件驱动的状态更新:
      on_fill(fill_event)          — 成交入账
      on_settlement(settle_price)  — 盯市结算
      update_market_price(quote)   — 浮动盈亏刷新
    """

    def __init__(self,
                 initial_equity: float = DEFAULT_INITIAL_EQUITY,
                 on_liquidation: Optional[Callable] = None):
        self.initial_equity = initial_equity
        self.balance = initial_equity
        self.positions = Positions()
        self.realized_pnl = 0.0
        self.total_fees = 0.0
        self._latest_prices: dict[str, float] = {}

        # 强平回调: on_liquidation(position, reason) → 模拟强平操作
        self._on_liquidation = on_liquidation

        # ── 交易记录支持 ──
        self._entry_ticks: dict[str, int] = {}  # symbol → tick at position open
        self._trade_callback: Optional[Callable] = None
        self._global_tick = 0

    def set_trade_callback(self, cb: Callable):
        """设置成交记录回调，用于写入 trades.jsonl"""
        self._trade_callback = cb

    def _record_trade(self, symbol: str, direction: str, entry_price: float,
                      exit_price: float, qty: int, pnl: float, fee: float,
                      action: str):
        """记录一条完整交易到 trades.jsonl（通过回调）"""
        if not self._trade_callback:
            return
        entry_tick = self._entry_ticks.get(symbol, 0)
        holding = self._global_tick - entry_tick
        trade = {
            "event_type": "FUTURES_TRADE",
            "symbol": symbol,
            "direction": direction,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "qty": qty,
            "pnl": round(pnl, 2),
            "fee": round(fee, 2),
            "holding_ticks": max(holding, 0),
            "action": action,
        }
        self._trade_callback(trade)

    # ─── 计算属性 ───

    @property
    def floating_pnl(self) -> float:
        total = 0.0
        for pos in self.positions.list_active():
            price = self._latest_prices.get(pos.symbol, 0)
            if price == 0:
                continue
            cfg = _load_contract(pos.symbol)
            mult = cfg["multiplier"]
            if pos.direction == LONG:
                total += (price - pos.avg_price) * mult * pos.qty
            else:
                total += (pos.avg_price - price) * mult * pos.qty
        return total

    @property
    def margin_used(self) -> float:
        total = 0.0
        for pos in self.positions.list_active():
            price = self._latest_prices.get(pos.symbol, 0)
            if price == 0:
                continue
            cfg = _load_contract(pos.symbol)
            total += price * cfg["multiplier"] * pos.qty * cfg["margin_rate"]
        return total

    @property
    def equity(self) -> float:
        return self.balance + self.floating_pnl

    @property
    def available(self) -> float:
        return self.equity - self.margin_used

    @property
    def risk_ratio(self) -> float:
        """风险率 = equity / margin_used，无持仓时返回 ∞"""
        mg = self.margin_used
        if mg <= 0:
            return float('inf')
        return self.equity / mg

    # ─── 市场事件处理 ───

    def update_market_price(self, symbol: str, price: float):
        """更新最新价（用于计算浮动盈亏和保证金）"""
        self._latest_prices[symbol] = price
        # 同时更新持仓的保证金
        pos = self.positions.get(symbol)
        if not pos.is_empty():
            cfg = _load_contract(symbol)
            pos.margin_used = price * cfg["multiplier"] * pos.qty * cfg["margin_rate"]

    def on_quote(self, quote: dict):
        """处理一条 FUTURES_QUOTE"""
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)
        if symbol and price > 0:
            self._global_tick += 1
            self.update_market_price(symbol, price)
        # 检查强平
        self._check_liquidation()

    def on_fill(self, fill_event: dict) -> dict:
        """处理一条 FUTURES_FILL — 成交入账

        返回 position_change event dict
        """
        symbol = fill_event["symbol"]
        side = fill_event["side"]       # BUY / SELL
        qty = fill_event["fill_qty"]
        price = fill_event["fill_price"]
        fee = fill_event.get("fee", 0.0)
        action = fill_event.get("action", "")

        cfg = _load_contract(symbol)
        pos = self.positions.get(symbol)
        mult = cfg["multiplier"]

        # 扣手续费
        self.balance -= fee
        self.total_fees += fee

        direction = LONG if side == "BUY" else SHORT
        event_pnl = 0.0
        trade_direction = None
        entry_price = 0

        if pos.is_empty():
            # 开新仓
            pos.direction = direction
            pos.qty = qty
            pos.avg_price = price
            self._entry_ticks[symbol] = self._global_tick

        elif pos.direction == direction:
            # 同向加仓，加权均价
            old_cost = pos.avg_price * pos.qty
            new_cost = price * qty
            pos.qty += qty
            pos.avg_price = (old_cost + new_cost) / pos.qty

        else:
            # 反向操作 = 平仓
            close_qty = min(qty, pos.qty)
            trade_direction = pos.direction
            entry_price = pos.avg_price

            if pos.direction == LONG:
                event_pnl = (price - pos.avg_price) * mult * close_qty
            else:
                event_pnl = (pos.avg_price - price) * mult * close_qty

            self.balance += event_pnl
            self.realized_pnl += event_pnl
            pos.qty -= close_qty

            # 记录交易
            self._record_trade(
                symbol=symbol,
                direction=trade_direction,
                entry_price=entry_price,
                exit_price=price,
                qty=close_qty,
                pnl=event_pnl,
                fee=fee * (close_qty / qty) if qty > 0 else 0,
                action="CLOSE" if pos.qty <= 0 else "PARTIAL_CLOSE",
            )

            if pos.qty <= 0:
                # 全部平仓，重置
                remaining = qty - close_qty
                if remaining > 0:
                    # 有余量，开反向新仓
                    pos.direction = direction
                    pos.qty = remaining
                    pos.avg_price = price
                    self._entry_ticks[symbol] = self._global_tick
                else:
                    pos.direction = None
                    pos.qty = 0
                    pos.avg_price = 0.0
                    pos.margin_used = 0.0
            else:
                # 部分平仓，还有剩余头寸
                pass

        # 更新保证金
        price_now = self._latest_prices.get(symbol, price)
        if pos.qty > 0 and pos.direction is not None:
            pos.margin_used = price_now * mult * pos.qty * cfg["margin_rate"]

        # 构造 position change event
        pos_event = {
            "event_type": "FUTURES_POSITION",
            "symbol": symbol,
            "direction": pos.direction,
            "qty": pos.qty,
            "avg_price": round(pos.avg_price, 2) if pos.qty > 0 else 0,
            "margin_used": round(pos.margin_used, 2),
            "fill_pnl": round(event_pnl, 2),
            "fill_fee": round(fee, 2),
        }

        # 强平检查
        self._check_liquidation()

        return pos_event

    def on_settlement(self, settle_price: float = None):
        """盯市结算: 确定浮动盈亏 → 入账 balance → 重置开仓价到结算价

        结算后浮动盈亏归零（因为开仓价已更新为结算价）。
        """
        # 用指定结算价或当前最新价
        settle = settle_price
        if settle is None and self.positions.list_active():
            pos = self.positions.list_active()[0]
            settle = self._latest_prices.get(pos.symbol, 0)

        total_pnl = self.floating_pnl
        self.balance += total_pnl
        self.realized_pnl += total_pnl

        # 关键: 开仓价更新为结算价 → 浮动盈亏归零
        for pos in self.positions.list_active():
            price = settle or self._latest_prices.get(pos.symbol, 0)
            if price > 0:
                pos.avg_price = price

        settlement_event = {
            "event_type": "FUTURES_SETTLEMENT",
            "settle_price": round(settle, 2) if settle else 0,
            "floating_pnl_settled": round(total_pnl, 2),
            "balance_after": round(self.balance, 2),
            "margin_used": round(self.margin_used, 2),
            "risk_ratio": round(self.risk_ratio, 4) if self.risk_ratio != float('inf') else float('inf'),
            "positions": self.positions.to_dict(),
        }

        return settlement_event

    def _check_liquidation(self):
        """强平检查: 风险率 < 1.0 → 触发强平"""
        if self.risk_ratio < 1.0 and self.positions.active_count > 0:
            # 从最大持仓开始强平
            active = sorted(
                self.positions.list_active(),
                key=lambda p: p.margin_used,
                reverse=True
            )
            for pos in active:
                symbol = pos.symbol
                price = self._latest_prices.get(symbol, 0)
                cfg = _load_contract(symbol)
                mult = cfg["multiplier"]

                if pos.direction == LONG:
                    pnl = (price - pos.avg_price) * mult * pos.qty
                else:
                    pnl = (pos.avg_price - price) * mult * pos.qty

                self.balance += pnl
                self.realized_pnl += pnl

                # 记录强平交易
                self._record_trade(
                    symbol=symbol,
                    direction=pos.direction,
                    entry_price=pos.avg_price,
                    exit_price=price,
                    qty=pos.qty,
                    pnl=pnl,
                    fee=0,
                    action="LIQUIDATION",
                )

                # 重置持仓
                pos.direction = None
                pos.qty = 0
                pos.avg_price = 0.0
                pos.margin_used = 0.0

                if self._on_liquidation:
                    self._on_liquidation(pos, "risk_ratio_below_1.0")

            # 检查是否仍有持仓，如果还有但仍有风险则继续平
            if self.risk_ratio < 1.0 and self.positions.active_count > 0:
                self._check_liquidation()

    # ─── 状态输出 ───

    def to_dict(self) -> dict:
        mg = self.margin_used
        return {
            "initial_equity": self.initial_equity,
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "margin_used": round(mg, 2),
            "available": round(self.available, 2),
            "floating_pnl": round(self.floating_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_fees": round(self.total_fees, 2),
            "risk_ratio": round(self.risk_ratio, 4) if self.risk_ratio != float('inf') else "∞",
            "positions": self.positions.to_dict(),
        }

    def summary(self) -> str:
        d = self.to_dict()
        pos_str = ""
        for sym, p in d["positions"].items():
            dir_cn = "多" if p["direction"] == "LONG" else "空"
            pos_str += f"\n    {sym} {dir_cn} {p['qty']}手 @ ¥{p['avg_price']:.2f} 保证金¥{p['margin_used']:.2f}"

        rr = d["risk_ratio"]
        rr_str = f"{rr:.2f}" if rr != "∞" else "∞"

        return (
            f"FuturesAccount\n"
            f"  初始权益: ¥{d['initial_equity']:,.2f}\n"
            f"  当前权益: ¥{d['equity']:,.2f}\n"
            f"  余  额:  ¥{d['balance']:,.2f}\n"
            f"  保证金:   ¥{d['margin_used']:,.2f}\n"
            f"  可用资金: ¥{d['available']:,.2f}\n"
            f"  浮动盈亏: ¥{d['floating_pnl']:+,.2f}\n"
            f"  已实现盈亏: ¥{d['realized_pnl']:+,.2f}\n"
            f"  总手续费: ¥{d['total_fees']:,.2f}\n"
            f"  风险率:   {rr_str}\n"
            f"  持仓:{pos_str if pos_str else ' ∅'}"
        )
