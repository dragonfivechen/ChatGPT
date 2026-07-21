"""strategy/exit/intraday_profit_exit_v1.py — 独立退出规则：盘中止盈 +1%

触发窗口: 13:00-15:00
条件: 持仓股当前价 ≥ 当日买入均价 × 1.01
动作: 全仓卖出，冷却 30 分钟防止重复买入
优先级: 止损 → +1%止盈 → 策略信号 → 收盘处理

事件记录: {"side":"SELL", "reason":"PROFIT_TAKE_1PCT", "profit_pct": ...}
"""

import os
import json
import time
from datetime import time as dtime

_WINDOW_START = dtime(13, 0)
_WINDOW_END = dtime(15, 0)
_PROFIT_THRESHOLD = 0.01  # 1%
_COOLDOWN_SEC = 1800  # 30 分钟

_PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_COOLDOWN_FILE = os.path.join(_PROJECT, ".profit_exit_cooldown.json")


def in_window(now: dtime) -> bool:
    """检查是否在止盈触发窗口"""
    return _WINDOW_START <= now <= _WINDOW_END


def load_cooldowns() -> dict[str, float]:
    if not os.path.exists(_COOLDOWN_FILE):
        return {}
    with open(_COOLDOWN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cooldowns(cd: dict[str, float]):
    os.makedirs(os.path.dirname(_COOLDOWN_FILE), exist_ok=True)
    with open(_COOLDOWN_FILE, "w", encoding="utf-8") as f:
        json.dump(cd, f, indent=2)


def check_cooldown(symbol: str) -> bool:
    """返回 True 表示仍在冷却中，不应入场"""
    cd = load_cooldowns()
    exit_ts = cd.get(symbol, 0)
    return (time.time() - exit_ts) < _COOLDOWN_SEC


def set_cooldown(symbol: str):
    cd = load_cooldowns()
    cd[symbol] = time.time()
    save_cooldowns(cd)


def check_profit_exit(
    symbol: str,
    quantity: int,
    avg_price: float,
    current_price: float,
    now: dtime,
) -> dict | None:
    """独立止盈检查。

    参数:
        symbol: 股票代码
        quantity: 持仓数量
        avg_price: 当日买入均价
        current_price: 当前行情价
        now: 当前时间

    返回:
        SELL_ALL 信号 dict，或 None
    """
    if not in_window(now):
        return None
    if quantity <= 0 or avg_price <= 0 or current_price <= 0:
        return None

    gain = (current_price - avg_price) / avg_price

    # round 以消除浮点精度误差（如 20.20 vs 20.0 计算为 0.00999996 而非 0.01）
    if round(gain, 6) >= _PROFIT_THRESHOLD:
        return {
            "event_type": "SIGNAL",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "strategy_id": "INTRADAY_PROFIT_EXIT_V1",
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "price": current_price,
            "reason": "PROFIT_TAKE_1PCT",
            "profit_pct": round(gain * 100, 2),
            "note": f"盘中止盈 +{gain*100:.1f}%",
        }

    return None
