"""strategy/rank_follow_v1.py — L3 Ranking Follow 持仓策略 v1.0

核心原则:
  前端负责选股，交易层不再重新选股。
  L3负责发现强者，持仓策略负责跟随排名变化。

资金结构:
  总资金 = 70% 持仓 + 30% 备用现金（备用金不参与日常排名分配）

建仓:
  L3 Rank ≤ 5 按排名阶梯分配（占总资金比例）
  Rank 1: 25%, Rank 2: 18%, Rank 3: 12%, Rank 4: 9%, Rank 5: 6%

动态调仓表:
  排名上升/下降 → 按目标比例调整仓位
  独立风控（不依赖排名阶梯）:
    Rank 11-20 → 减仓 50%
    Rank 21-30 → 再减仓 50%
    Rank >30   → 清仓

替换:
  非持仓股进入 Top5 且当前有持仓排名 >10 → 卖弱买强

取消:
  MA3 / 突破判断 / 成交量 / 交易评分 / 多指标组合
"""

import json
import os
import time
from typing import Optional

from .base import Strategy, Signal
from .events import append_signal_event
from market.pool_provider import get_pool

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCORING_FILE = os.path.join(_PROJECT, "market", "scoring_pool.json")

# ── 资金结构 ────────────────────────────────────────────
RESERVE_RATIO = 0.30  # 30% 备用现金，不参与排名分配

# ── 排名阶梯仓位（占总资金比例） ─────────────────────────
RANK_ALLOC = {
    1: 0.25,
    2: 0.18,
    3: 0.12,
    4: 0.09,
    5: 0.06,
}

# ── 减仓/清仓风控 ──────────────────────────────────────
# (rank_gt, keep_ratio): 排名大于该值时，保留 keep_ratio 比例
REDUCE_THRESHOLDS = [
    (30, 0.0),    # rank > 30 → 清仓 (keep 0%)
    (20, 0.5),    # rank > 20 → 减半 (keep 50%)
    (10, 0.5),    # rank > 10 → 减半 (keep 50%)
]

# ── 盈利/亏损管理 ──────────────────────────────────────
# 盈利阶梯（累计，以买入价为基准）
# +10%卖20% → +15%再卖20%(累计40%) → +20%再卖30%(累计70%) → +30%留10%
PROFIT_SELL_RATIO = {
    0.05: 0.0,      # +5% 不动
    0.10: 0.20,     # +10% 卖20%
    0.15: 0.40,     # +15% 累计卖40%
    0.20: 0.70,     # +20% 累计卖70%
    0.30: 0.90,     # +30% 累计卖90%, 留10%
}

# 亏损阶梯（累计，以买入价为基准）
# -10%卖30% → -15%再卖30%(累计60%) → -20%清仓
LOSS_SELL_RATIO = {
    -0.05: 0.0,     # -5% 观察
    -0.10: 0.30,    # -10% 卖30%, 留70%
    -0.15: 0.60,    # -15% 累计卖60%, 留40%
    -0.20: 1.0,     # -20% 清仓
}

# ── 回撤止盈（以持仓最高价为基准） ────────────────────
# 从最高价回落指定比例时，卖出对应仓位
DRAWDOWN_SELL = 0.50    # 触发后卖剩余仓位的比例
DRAWDOWN_TRIGGER = 0.10  # 从最高价回撤10%触发


class RankFollowV1(Strategy):
    """L3 Ranking Follow 持仓策略 v1.0"""

    def __init__(self):
        super().__init__("RANK_FOLLOW_V1")
        self._pool_size = 50
        self._prices: dict[str, float] = {}
        self._signal_queue: list[Signal] = []
        self._evaluated_this_batch = False
        self._last_batch_minute = ""
        self._score_rank_map: dict[str, int] = {}
        self._score_map: dict[str, float] = {}
        self._generated_at = ""
        self._max_prices: dict[str, float] = {}  # 持仓以来最高价

    # ── 数据加载 ──────────────────────────────────────────

    def _load_rankings(self) -> bool:
        if not os.path.exists(_SCORING_FILE):
            return False
        try:
            with open(_SCORING_FILE) as f:
                data = json.load(f)
            gen = data.get("generated_at", "")
            if gen and gen == self._generated_at:
                return True
            self._generated_at = gen
            self._score_rank_map.clear()
            self._score_map.clear()
            for d in data.get("details", []):
                sym = d.get("symbol", "").strip()
                rank = d.get("rank", 0)
                score = d.get("score", 0)
                if sym and rank > 0:
                    self._score_rank_map[sym] = rank
                    self._score_map[sym] = score
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def _get_rank(self, symbol: str) -> int:
        self._load_rankings()
        return self._score_rank_map.get(symbol, 999)

    def _get_top5(self) -> list[tuple[str, int, float]]:
        self._load_rankings()
        sorted_syms = sorted(
            self._score_rank_map.items(),
            key=lambda x: x[1],
        )
        return [
            (sym, rank, self._score_map.get(sym, 0))
            for sym, rank in sorted_syms[:5]
        ]

    # ── 价格跟踪 ──────────────────────────────────────────

    def feed_history(self, quotes: list[dict]):
        for q in quotes:
            sym = q.get("symbol", "")
            price = q.get("data", {}).get("price", 0)
            if price > 0:
                self._prices[sym] = price

    # ── 核心: 目标仓位计算 ─────────────────────────────

    def _target_qty(self, rank: int, total_equity: float, price: float) -> int:
        """按排名阶梯计算目标持仓数量（基于总权益而非现金余额）"""
        alloc_pct = RANK_ALLOC.get(rank)
        if alloc_pct is None or rank <= 0 or rank > 5:
            return 0
        target_value = total_equity * alloc_pct
        return int(target_value / price / 100) * 100

    # ── 信号生成 ──────────────────────────────────────────

    def _evaluate(self, portfolio: dict) -> list[Signal]:
        signals: list[Signal] = []

        if not self._load_rankings():
            return signals

        total_cash = portfolio.get("cash", 0)
        positions = portfolio.get("positions", {})
        total_equity = portfolio.get("equity", total_cash)
        active = {
            sym: info for sym, info in positions.items()
            if isinstance(info, dict) and info.get("quantity", 0) > 0
        }
        held = set(active.keys())

        # 本次卖出标记（用于后续建仓计算）
        selling = set()

        # ── 1. 持仓票: 盈利/亏损/排名统一计算 ──
        # 对每只持仓票，计算三维卖出后的剩余数量
        remaining_qty_by_stock = {}
        for sym, info in list(active.items()):
            rank = self._get_rank(sym)
            qty = info.get("quantity", 0)
            price = self._prices.get(sym, 0)
            avg_cost = info.get("avg_cost", 0)
            if price <= 0 or qty <= 0:
                remaining_qty_by_stock[sym] = qty
                continue

            return_pct = (price / avg_cost - 1) if avg_cost > 0 else 0

            # ① 止损阶梯（累计卖出比例）
            eps = 1e-3
            sell_ratio = 0.0
            for thr in sorted(LOSS_SELL_RATIO.keys(), reverse=True):
                if return_pct <= thr + eps:
                    sell_ratio = LOSS_SELL_RATIO[thr]

            # ② 止盈阶梯（无止损时，累计卖出比例）
            if sell_ratio <= 0:
                for thr in sorted(PROFIT_SELL_RATIO.keys(), reverse=True):
                    if return_pct >= thr - eps:
                        sell_ratio = PROFIT_SELL_RATIO[thr]
                        break

            # 初始剩余：按止盈/止损比例计算（round避免浮点精度）
            remaining = qty
            if sell_ratio >= 1.0:
                remaining = 0
            elif sell_ratio > 0:
                keep_ratio = round(1.0 - sell_ratio, 2)
                remaining = int(qty * keep_ratio / 100) * 100

            # ③ 回撤止盈：从持仓最高价回撤
            eps = 1e-3
            if remaining > 0:
                max_price = self._max_prices.get(sym, price)
                if price > max_price:
                    max_price = price
                self._max_prices[sym] = max_price
                drawdown = (max_price - price) / max_price if max_price > 0 else 0
                if drawdown >= DRAWDOWN_TRIGGER - eps and max_price > avg_cost:
                    # 从最高价已回落，且最高价高于成本（有盈利在保护）
                    remaining = int(remaining * (1 - DRAWDOWN_SELL) / 100) * 100

            # ④ L3 排名减仓（对止盈/止损/回撤后的剩余量）
            if remaining > 0:
                for gt, keep in sorted(REDUCE_THRESHOLDS, key=lambda x: -x[0]):
                    if rank > gt:
                        remaining = int(remaining * keep / 100) * 100
                        break

            # 统一卖出信号（一次计算，一条信号）
            remaining_qty_by_stock[sym] = remaining
            sell_qty = qty - remaining
            if sell_qty >= 100:
                parts = []
                if sell_ratio > 0:
                    side = "止损" if return_pct < 0 else "止盈"
                    parts.append(f"{side}{return_pct*100:.0f}%卖{int(sell_ratio*100)}%")
                # 回撤标记
                mp = self._max_prices.get(sym, price)
                dd_from_peak = (mp - price) / mp if mp > 0 else 0
                rank_sell = int(qty * sell_ratio / 100) * 100 if sell_ratio > 0 else 0
                after_pnl = qty - max(rank_sell, 0)
                if remaining < after_pnl and dd_from_peak >= DRAWDOWN_TRIGGER - 1e-3:
                    parts.append(f"从最高回撤{dd_from_peak*100:.0f}%")
                elif remaining < after_pnl:
                    parts.append(f"rank={rank}减调")
                note = " ".join(parts) if parts else f"{return_pct*100:.0f}% rank={rank} 卖{int((1-remaining/qty)*100)}%"
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    symbol=sym,
                    action="SELL",
                    quantity=sell_qty,
                    confidence=0.8,
                    note=note,
                ))
                if remaining == 0:
                    # 清仓：清理最高价锚
                    self._max_prices.pop(sym, None)
                    selling.add(sym)

        # ── 2. 持仓票: 按排名阶梯调整（仅对未触发盈亏管理的票）──
        # 止盈/止损已处理的票跳过，避免重复信号
        adjusted_in_step1 = {
            sym for sym in held
            if remaining_qty_by_stock.get(sym, 0) < active[sym].get("quantity", 0)
        }
        for sym in (held - selling - adjusted_in_step1):
            rank = self._get_rank(sym)
            current_qty = remaining_qty_by_stock.get(sym, 0)
            price = self._prices.get(sym, 0)
            if price <= 0 or current_qty <= 0:
                continue
            target_qty = self._target_qty(rank, total_equity, price)
            if target_qty <= 0:
                continue

            diff = target_qty - current_qty
            diff_rounded = int(diff / 100) * 100

            if diff_rounded >= 100:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    symbol=sym,
                    action="BUY",
                    quantity=diff_rounded,
                    confidence=0.7,
                    note=f"rank={rank} 加仓至{int(RANK_ALLOC.get(rank,0)*100)}%",
                ))
            elif diff_rounded <= -100:
                signals.append(Signal(
                    strategy_id=self.strategy_id,
                    symbol=sym,
                    action="SELL",
                    quantity=abs(diff_rounded),
                    confidence=0.7,
                    note=f"rank={rank} 减仓至{int(RANK_ALLOC.get(rank,0)*100)}%",
                ))

        # ── 3. Top5 新票建仓 ──
        after_sell = held - selling
        current_count = len(after_sell)

        top5 = self._get_top5()
        top5_symbols = {s[0] for s in top5}
        unheld_top5 = [s for s in top5 if s[0] not in after_sell and s[0] not in selling]

        available_slots = 5 - current_count

        if unheld_top5 and available_slots > 0:
            for sym, rank, score in unheld_top5[:available_slots]:
                price = self._prices.get(sym, 0)
                if price <= 0:
                    continue
                qty = self._target_qty(rank, total_equity, price)
                if qty >= 100:
                    # 新仓：初始化最高价锚 = 买入价
                    self._max_prices[sym] = price
                    signals.append(Signal(
                        strategy_id=self.strategy_id,
                        symbol=sym,
                        action="BUY",
                        quantity=qty,
                        confidence=0.85,
                        note=f"rank={rank} 建仓{int(RANK_ALLOC.get(rank,0)*100)}%",
                    ))

        # ── 4. 卖弱买强 ──
        elif unheld_top5 and available_slots <= 0:
            self._replace_weakest(unheld_top5[0], active, signals, total_equity)

        return signals

    def _replace_weakest(
        self, new_entry: tuple[str, int, float],
        active_positions: dict,
        signals: list,
        total_equity: float,
    ):
        new_sym, new_rank, _ = new_entry
        candidates = []
        for sym, info in active_positions.items():
            r = self._get_rank(sym)
            if r > 10:
                candidates.append((r, sym, info.get("quantity", 0)))
        if not candidates:
            return
        candidates.sort(key=lambda x: -x[0])
        worst_rank, worst_sym, worst_qty = candidates[0]
        if worst_qty >= 100:
            # 卖出旧票：清理最高价锚
            self._max_prices.pop(worst_sym, None)
            signals.append(Signal(
                strategy_id=self.strategy_id,
                symbol=worst_sym,
                action="SELL",
                quantity=worst_qty,
                confidence=0.9,
                note=f"替换: rank={worst_rank}>10 → {new_sym}",
            ))
            price = self._prices.get(new_sym, 0)
            if price > 0:
                qty = self._target_qty(new_rank, total_equity, price)
                if qty >= 100:
                    # 新仓：初始化最高价锚 = 买入价
                    self._max_prices[new_sym] = price
                    signals.append(Signal(
                        strategy_id=self.strategy_id,
                        symbol=new_sym,
                        action="BUY",
                        quantity=qty,
                        confidence=0.8,
                        note=f"替换增量: rank={new_rank} {new_sym}",
                    ))

    # ── 接口实现 ──────────────────────────────────────────

    def on_quote(self, quote: dict, portfolio: dict) -> Optional[Signal]:
        sym = quote.get("symbol", "")
        price = quote.get("data", {}).get("price", 0)
        ts = quote.get("timestamp", "")

        if price > 0:
            self._prices[sym] = price

        batch_minute = ts[:16]
        if batch_minute != self._last_batch_minute:
            self._last_batch_minute = batch_minute
            self._evaluated_this_batch = False

        if self._signal_queue:
            return self._signal_queue.pop(0)

        if len(self._prices) < self._pool_size or self._evaluated_this_batch:
            return None

        self._evaluated_this_batch = True
        all_signals = self._evaluate(portfolio)

        if not all_signals:
            return None

        self._signal_queue = all_signals[1:]
        return all_signals[0]

    def start(self):
        super().start()
        self._load_rankings()
        _, meta = get_pool()
        self._pool_size = meta.get("total", 50)


def make_signal(sig: Signal) -> dict:
    d = sig.to_dict()
    d["timestamp"] = time.strftime(
        "%Y-%m-%dT%H:%M:%S+08:00", time.localtime()
    )
    return d


if __name__ == "__main__":
    s = RankFollowV1()
    s.start()
    print(f"Strategy: {s.strategy_id}")
    print(f"Pool size: {s._pool_size}")
    print(f"Scored symbols: {len(s._score_rank_map)}")

    top5 = s._get_top5()
    print(f"\nL3 Top5:")
    for sym, rank, score in top5:
        alloc = RANK_ALLOC.get(rank, 0) * 100
        print(f"  rank={rank:>3}  score={score:>5.1f}  {sym}  alloc={alloc:.0f}%")

    print(f"\n资金结构: 持仓70% / 备用30%")
    print(f"Rank 1: 25%  Rank 2: 18%  Rank 3: 12%  Rank 4: 9%  Rank 5: 6%")

    # 模拟建仓
    pf = {"cash": 10_000_000, "equity": 10_000_000, "positions": {}}
    s._prices = {
        "002440": 11.78,
        "000759": 7.22,
        "600722": 9.38,
        "600227": 3.37,
        "300759": 37.30,
    }
    sigs = s._evaluate(pf)
    print(f"\n模拟建仓信号 ({len(sigs)}):")
    for sig in sigs:
        print(f"  {sig}")
