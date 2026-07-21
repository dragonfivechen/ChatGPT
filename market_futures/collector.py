#!/usr/bin/env python3
"""
Futures-Sim v0.1 — collector.py（行情生成器）

职责: 生成 FUTURES_QUOTE 事件，写入 futures_events.jsonl。
类型: 纯数据层，不涉及交易逻辑。

输出事件 Schema:
{
  "event_type": "FUTURES_QUOTE",
  "ts": "ISO-8601",
  "symbol": "RB",
  "price": float,
  "open": float,
  "high": float,
  "low": float,
  "pre_close": float,
  "volume": int,
  "oi": int
}

两种模式:
  simulate  — 模拟行情（趋势状态机+随机游走）
  replay    — 历史重放（加载分钟K线逐时间推进）

用法:
  python3 collector.py --mode simulate --duration 30m
  python3 collector.py --mode simulate --steps 500
  python3 collector.py --mode replay --data kline.csv
"""

import os
import sys
import json
import time
import math
import random
import argparse
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional

# ─── 路径 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_PATH = os.path.join(BASE_DIR, "futures_contracts.json")
EVENTS_PATH = os.path.join(BASE_DIR, "futures_events.jsonl")

# ─── 事件 Schema ───
EVENT_TYPES = frozenset({
    "FUTURES_QUOTE",
    "FUTURES_SIGNAL",
    "FUTURES_ORDER",
    "FUTURES_FILL",
    "FUTURES_POSITION",
    "FUTURES_SETTLEMENT",
    "FUTURES_RISK",
})


# ─── 加载合约 ───
def load_contracts(path: str = CONTRACTS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["contracts"]


# ─── 事件写入（线程安全） ───
_lock = threading.Lock()


def append_event(event: dict, path: str = EVENTS_PATH):
    """追加事件到 futures_events.jsonl"""
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def make_quote(
    symbol: str,
    price: float,
    open_p: float,
    high: float,
    low: float,
    pre_close: float,
    volume: int,
    oi: int,
) -> dict:
    """构造 FUTURES_QUOTE 事件"""
    return {
        "event_type": "FUTURES_QUOTE",
        "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "symbol": symbol,
        "price": round(price, 2),
        "open": round(open_p, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "pre_close": round(pre_close, 2),
        "volume": volume,
        "oi": oi,
    }


# ==============================================================
#  模 拟 行 情 生 成 器
# ==============================================================

class MarketState:
    """市场状态机"""

    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    SIDEWAYS = "sideways"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    HIGH_VOL = "high_vol"

    def __init__(self):
        self.regime = self.SIDEWAYS
        self.strength = 0.3       # 趋势强度 0~1
        self.duration = 0         # 当前状态持续ticks
        self.max_duration = random.randint(20, 60)

    def update(self):
        """每 tick 更新一次状态"""
        self.duration += 1

        # 状态切换
        if self.duration >= self.max_duration:
            self._switch()

    def _switch(self):
        """切换到新状态"""
        regimes = [
            self.TREND_UP, self.TREND_DOWN, self.SIDEWAYS,
            self.BREAKOUT_UP, self.BREAKOUT_DOWN, self.HIGH_VOL,
        ]
        weights = [0.20, 0.20, 0.30, 0.10, 0.10, 0.10]
        self.regime = random.choices(regimes, weights=weights, k=1)[0]
        self.strength = random.uniform(0.2, 0.8)
        self.duration = 0
        self.max_duration = random.randint(15, 80)

        if self.regime in (self.BREAKOUT_UP, self.BREAKOUT_DOWN):
            self.max_duration = random.randint(5, 20)  # 突破持续时间短
        elif self.regime == self.HIGH_VOL:
            self.strength = random.uniform(0.6, 1.0)

    def get_drift(self, vol: float) -> float:
        """返回当前状态的漂移量"""
        base = random.gauss(0, vol * 0.3)

        if self.regime == self.TREND_UP:
            return base + vol * 0.4 * self.strength
        elif self.regime == self.TREND_DOWN:
            return base - vol * 0.4 * self.strength
        elif self.regime == self.BREAKOUT_UP:
            return base + vol * 0.8 * self.strength
        elif self.regime == self.BREAKOUT_DOWN:
            return base - vol * 0.8 * self.strength
        elif self.regime == self.HIGH_VOL:
            return random.gauss(0, vol * 0.8)
        else:  # sideways
            return base * 0.5


class SimMarket:
    """模拟行情市场

    对每个合约独立运行状态机，产生价格序列。
    """

    def __init__(self, contracts: dict):
        self.contracts = contracts
        self.states: dict[str, MarketState] = {}
        self.prices: dict[str, float] = {}
        self.prices_open: dict[str, float] = {}
        self.prices_high: dict[str, float] = {}
        self.prices_low: dict[str, float] = {}
        self.prices_prev: dict[str, float] = {}
        self.volumes: dict[str, int] = {}
        self.oi: dict[str, int] = {}
        self.ticks: int = 0

        for code, cfg in contracts.items():
            self.states[code] = MarketState()
            base = cfg["base_price"]
            noise = random.uniform(-cfg.get("limit_pct", 0.05) * 0.1 * base,
                                    cfg.get("limit_pct", 0.05) * 0.1 * base)
            self.prices[code] = base + noise
            self.prices_open[code] = self.prices[code]
            self.prices_high[code] = self.prices[code]
            self.prices_low[code] = self.prices[code]
            self.prices_prev[code] = base
            self.volumes[code] = 0
            self.oi[code] = random.randint(50000, 500000)

    def tick(self) -> list[dict]:
        """推进一个 tick，返回所有合约的 quote 事件列表"""
        self.ticks += 1
        quotes = []

        for code, cfg in self.contracts.items():
            state = self.states[code]
            state.update()

            prev = self.prices[code]
            vol_ratio = cfg.get("limit_pct", 0.05) * cfg["base_price"]
            drift = state.get_drift(vol_ratio * 0.1)

            # 均值回归力（防止价格跑飞）
            center = self.prices_prev[code]
            reversion = (center - prev) * 0.003
            change = drift + reversion

            new_price = prev + change

            # 涨跌停限制
            limit = cfg["base_price"] * cfg.get("limit_pct", 0.05)
            low_limit = center - limit
            high_limit = center + limit
            new_price = max(low_limit, min(high_limit, new_price))

            # tick 对齐
            tick = cfg["tick_size"]
            decimals = cfg.get("price_decimals", 0)
            factor = 10 ** decimals
            new_price = round(round(new_price * factor / tick) * tick / factor, decimals)

            # 高波动时放量
            vol_mult = 1.0
            if state.regime in (MarketState.HIGH_VOL, MarketState.BREAKOUT_UP, MarketState.BREAKOUT_DOWN):
                vol_mult = 2.0 + random.random() * 2.0
            elif state.regime == MarketState.SIDEWAYS:
                vol_mult = 0.3 + random.random() * 0.4

            base_vol = random.randint(200, 3000)
            volume = int(base_vol * vol_mult)

            self.prices[code] = new_price
            self.prices_high[code] = max(self.prices_high[code], new_price)
            self.prices_low[code] = min(self.prices_low[code], new_price)
            self.volumes[code] += volume

            quote = make_quote(
                symbol=code,
                price=new_price,
                open_p=self.prices_open[code],
                high=self.prices_high[code],
                low=self.prices_low[code],
                pre_close=self.prices_prev[code],
                volume=self.volumes[code],
                oi=self.oi[code],
            )
            quotes.append(quote)

        return quotes

    def get_state_summary(self) -> list[dict]:
        """调试用：打印当前市场状态"""
        summaries = []
        for code, state in self.states.items():
            summaries.append({
                "symbol": code,
                "regime": state.regime,
                "strength": round(state.strength, 2),
                "duration": state.duration,
            })
        return summaries


# ==============================================================
#  运 行 入 口
# ==============================================================

def run_simulate(contracts: dict,
                 steps: int = 300,
                 interval_s: float = 2.0,
                 realtime: bool = True):
    """运行模拟行情，生成 FUTURES_QUOTE 事件"""
    market = SimMarket(contracts)

    # 清空事件文件（仅用于独立运行模式）
    if os.path.exists(EVENTS_PATH):
        os.remove(EVENTS_PATH)

    print(f"[collector] 模拟行情启动 | 品种数={len(contracts)} | 步数={steps} | 间隔={interval_s}s")
    print(f"[collector] 事件输出: {EVENTS_PATH}")

    for i in range(steps):
        quotes = market.tick()

        # 写入事件文件
        for q in quotes:
            append_event(q)

        # 控制台输出（每10tick打印一次状态）
        if i % 10 == 0:
            states = market.get_state_summary()
            sample = random.choice(states)
            sample_q = random.choice(quotes)
            print(f"  tick {i:>4d} | {sample_q['symbol']} "
                  f"¥{sample_q['price']:<8.2f} "
                  f"vol={sample_q['volume']:<8d} "
                  f"| {sample['regime']:<14} "
                  f"strength={sample['strength']:.2f}")

        if realtime and i < steps - 1:
            time.sleep(interval_s)

    # 写入完成标记
    final_event = {
        "event_type": "FUTURES_QUOTE",
        "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "symbol": "__END_SESSION__",
        "price": 0,
        "message": f"Session complete: {steps} ticks, {len(contracts)} contracts",
    }
    append_event(final_event)
    print(f"\n[collector] ✅ 完成！共 {steps} ticks, 写入 {(steps) * len(contracts)} 条事件")


def verify_events(path: str = EVENTS_PATH):
    """验证事件文件完整性"""
    if not os.path.exists(path):
        print(f"[verify] ❌ 事件文件不存在: {path}")
        return False

    count = 0
    errors = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                if evt.get("event_type") not in EVENT_TYPES:
                    errors += 1
                    print(f"[verify] ⚠️ 未知事件类型: {evt.get('event_type')}")
            except json.JSONDecodeError as e:
                errors += 1
                print(f"[verify] ❌ JSON 解析错误: {e}")
            count += 1

    print(f"\n[verify] 事件文件: {path}")
    print(f"[verify] 总事件数: {count}")
    print(f"[verify] 错误数: {errors}")
    print(f"[verify] 状态: {'✅ PASS' if errors == 0 else '❌ FAIL'}")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description="Futures-Sim 行情生成器")
    parser.add_argument("--mode", choices=["simulate", "replay", "verify"],
                        default="simulate", help="运行模式")
    parser.add_argument("--steps", type=int, default=300,
                        help="模拟步数 (simulate 模式)")
    parser.add_argument("--duration", type=str, default="",
                        help="模拟时长, 如 30m/2h (simulate 模式)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="tick 间隔秒数, 0=无延迟")
    parser.add_argument("--realtime", action="store_true", default=False,
                        help="实时延迟（默认 false = 快速模式）")
    parser.add_argument("--data", type=str, default="",
                        help="历史数据文件路径 (replay 模式)")
    args = parser.parse_args()

    contracts = load_contracts()

    if args.mode == "verify":
        verify_events()
        return

    if args.mode == "simulate":
        steps = args.steps
        if args.duration:
            unit = args.duration[-1]
            val = int(args.duration[:-1])
            if unit == "m":
                # 假设每个tick 2秒
                steps = val * 60 // int(args.interval or 2)
            elif unit == "h":
                steps = val * 3600 // int(args.interval or 2)
        run_simulate(contracts, steps=steps, interval_s=args.interval,
                     realtime=args.realtime)

    elif args.mode == "replay":
        print("[collector] replay 模式待实现")
        # 预留


if __name__ == "__main__":
    main()
