"""
trading-runtime — strategies 策略包

Phase 6.4 独立实现，不引用 market_futures/strategies/
以适应 Runtime 实时行情事件调用

策略契约:
  - on_quote(quote: dict, position_info: dict) -> dict | None
    输入: FUTURES_QUOTE 事件 + 当前持仓信息
    输出: FUTURES_SIGNAL dict | None

所有策略保持: 输出触发、不接触账户、不接触成交
"""
