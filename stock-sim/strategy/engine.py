"""strategy/engine.py — 策略引擎

管理策略注册、行情分发、信号收集。
"""

from typing import Optional
from .base import Strategy, Signal
from .events import signal_event


class StrategyEngine:
    """策略引擎。持有已注册策略列表，接收行情并分发给所有活跃策略。"""

    def __init__(self):
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        """注册策略"""
        sid = strategy.strategy_id
        if sid in self._strategies:
            return
        self._strategies[sid] = strategy
        strategy.start()

    def unregister(self, strategy_id: str) -> None:
        """注销策略"""
        if strategy_id in self._strategies:
            self._strategies[strategy_id].stop()
            del self._strategies[strategy_id]

    def on_quote(self, quote: dict, portfolio: dict) -> list[dict]:
        """分发行情给所有活跃策略，收集信号"""
        signals = []
        for sid, strategy in self._strategies.items():
            if not strategy.is_active:
                continue
            try:
                sig = strategy.on_quote(quote, portfolio)
            except Exception as e:
                print(f"[engine] {sid} error: {e}")
                continue
            if sig is not None:
                evt = signal_event(sig)
                signals.append(evt)
        return signals

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._strategies.values() if s.is_active)

    @property
    def registered_ids(self) -> list[str]:
        return list(self._strategies.keys())

    def summary(self) -> str:
        return (
            f"StrategyEngine({len(self._strategies)} registered, "
            f"{self.active_count} active)"
        )
