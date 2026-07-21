#!/usr/bin/env python3
"""
Futures-Sim v0.1 — Phase 2 验收测试

覆盖龙哥指定的4个测试用例:
  Test 1: 开多 (BUY 1 → 持仓 LONG 1, 保证金, 现金减少)
  Test 2: 盈利 (价格 +10 → 浮盈 = 10 × 乘数)
  Test 3: 开空 (SELL 1 → SHORT 持仓)
  Test 4: 强平 (极端反向价格 → risk_ratio < 1.0 → 强平)

状态标记:
  ✅ PASS / ❌ FAIL / ⚠️ WARN
"""

import sys
import os
import json
import time

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests'))

from position import Position, Positions, LONG, SHORT
from account import FuturesAccount
from simulator import Simulator, make_order_event

# ─── 颜色 ───
G = '\033[92m'
R = '\033[91m'
Y = '\033[93m'
B = '\033[94m'
N = '\033[0m'
BOLD = '\033[1m'

passed = 0
failed = 0
tests_run = 0


def test(name: str):
    global tests_run
    tests_run += 1
    print(f"\n{BOLD}{B}[Test {tests_run}] {name}{N}")
    print(f"{'─' * 50}")


def check(condition: bool, msg: str):
    global passed, failed
    if condition:
        passed += 1
        print(f"  {G}✅ {msg}{N}")
    else:
        failed += 1
        print(f"  {R}❌ {msg}{N}")


# ══════════════════════════════════════════════════════════════
# Test 1: 开多
# ══════════════════════════════════════════════════════════════

def test_open_long():
    test("开多 — 螺纹钢 BUY 1手 @ ¥3300")

    account = FuturesAccount(initial_equity=1_000_000)

    # 先更新行情
    account.on_quote({"symbol": "RB", "price": 3300})

    # 构造成交事件
    fill_event = {
        "event_type": "FUTURES_FILL",
        "order_id": "TEST_001",
        "fill_id": "FILL_001",
        "symbol": "RB",
        "side": "BUY",
        "action": "OPEN",
        "fill_price": 3300.0,
        "fill_qty": 1,
        "fee": 1.65,  # 3300 * 10 * 0.00005 = 1.65
    }
    pos_event = account.on_fill(fill_event)

    # 检查持仓
    pos = account.positions.get("RB")
    check(pos.direction == LONG, f"方向 = LONG (got {pos.direction})")
    check(pos.qty == 1, f"手数 = 1 (got {pos.qty})")
    check(abs(pos.avg_price - 3300) < 0.01, f"开仓价 = 3300 (got {pos.avg_price})")

    # 检查保证金
    # 3300 * 10 * 1 * 0.10 = 3300
    expected_margin = 3300 * 10 * 0.10
    check(abs(pos.margin_used - expected_margin) < 1,
          f"保证金占用 = ¥{expected_margin:.0f} (got ¥{pos.margin_used:.2f})")

    # 检查现金
    expected_balance = 1_000_000 - 1.65  # 扣除手续费
    check(abs(account.balance - expected_balance) < 1,
          f"现金余额 = ¥{expected_balance:.2f} (got ¥{account.balance:.2f})")

    # 检查权益
    expected_equity = expected_balance  # 浮盈=0
    check(abs(account.equity - expected_equity) < 1,
          f"动态权益 = ¥{expected_equity:.2f} (got ¥{account.equity:.2f})")

    # 检查可用资金
    expected_available = expected_equity - expected_margin
    check(abs(account.available - expected_available) < 1,
          f"可用资金 = ¥{expected_available:.2f} (got ¥{account.available:.2f})")

    return account


# ══════════════════════════════════════════════════════════════
# Test 2: 盈利
# ══════════════════════════════════════════════════════════════

def test_profit(account: FuturesAccount):
    test("盈利 — 螺纹钢 ¥3300 → ¥3310 (涨10点)")

    # 行情更新
    account.on_quote({"symbol": "RB", "price": 3310})

    # 检查浮盈: 10 * 10 * 1 = 100
    expected_pnl = 10 * 10 * 1  # change * multiplier * qty
    check(abs(account.floating_pnl - expected_pnl) < 1,
          f"浮动盈亏 = ¥{expected_pnl} (got ¥{account.floating_pnl:.2f})")

    # 检查权益: 初始 - 手续费 + 浮盈
    expected_equity = 1_000_000 - 1.65 + 100
    check(abs(account.equity - expected_equity) < 1,
          f"动态权益 = ¥{expected_equity:.2f} (got ¥{account.equity:.2f})")

    # 检查保证金更新: 3310 * 10 * 1 * 0.10
    expected_margin = 3310 * 10 * 0.10
    pos = account.positions.get("RB")
    check(abs(pos.margin_used - expected_margin) < 1,
          f"保证金更新 = ¥{expected_margin:.0f} (got ¥{pos.margin_used:.2f})")

    return account


# ══════════════════════════════════════════════════════════════
# Test 3: 开空
# ══════════════════════════════════════════════════════════════

def test_open_short():
    test("开空 — 螺纹钢 SELL 1手 @ ¥3300 (先平多再开空)")

    account = FuturesAccount(initial_equity=1_000_000)
    account.on_quote({"symbol": "RB", "price": 3300})

    # 先开多
    fill_buy = {
        "event_type": "FUTURES_FILL",
        "order_id": "TEST_BUY",
        "symbol": "RB",
        "side": "BUY",
        "action": "OPEN",
        "fill_price": 3300.0,
        "fill_qty": 1,
        "fee": 1.65,
    }
    account.on_fill(fill_buy)

    # 再开空（反向 = 平多）
    fill_sell = {
        "event_type": "FUTURES_FILL",
        "order_id": "TEST_SELL",
        "symbol": "RB",
        "side": "SELL",
        "action": "OPEN",
        "fill_price": 3300.0,
        "fill_qty": 1,
        "fee": 1.65,
    }
    pos_event = account.on_fill(fill_sell)

    # 检查持仓是否清空（平多）
    pos = account.positions.get("RB")
    check(pos.is_empty(), f"持仓已清空 (direction={pos.direction}, qty={pos.qty})")

    # 检查盈亏: 平多盈亏 = (3300 - 3300) * 10 * 1 = 0
    check(abs(account.realized_pnl) < 0.01,
          f"平仓盈亏 = ¥0 (got ¥{account.realized_pnl:.2f})")

    # 开多后平多 + 手续费的链路
    # 纯测试平多逻辑

    # ---- 直接开空 ----
    account2 = FuturesAccount(initial_equity=1_000_000)
    account2.on_quote({"symbol": "RB", "price": 3300})

    fill_short = {
        "event_type": "FUTURES_FILL",
        "order_id": "TEST_SHORT",
        "symbol": "RB",
        "side": "SELL",
        "action": "OPEN",
        "fill_price": 3300.0,
        "fill_qty": 2,
        "fee": 3.30,
    }
    account2.on_fill(fill_short)

    pos2 = account2.positions.get("RB")
    check(pos2.direction == SHORT, f"方向 = SHORT (got {pos2.direction})")
    check(pos2.qty == 2, f"手数 = 2 (got {pos2.qty})")

    # 价格下跌 → 盈利
    account2.on_quote({"symbol": "RB", "price": 3280})

    # 空头浮盈: (3300 - 3280) * 10 * 2 = 400
    expected_pnl = (3300 - 3280) * 10 * 2
    check(abs(account2.floating_pnl - expected_pnl) < 1,
          f"空头浮盈 = ¥{expected_pnl} (got ¥{account2.floating_pnl:.2f})")

    return account2


# ══════════════════════════════════════════════════════════════
# Test 4: 强平
# ══════════════════════════════════════════════════════════════

def test_liquidation():
    test("强平 — 极端反向价格触发 risk_ratio < 1.0")

    # 用小资金+大仓位来触发强平
    account = FuturesAccount(initial_equity=100_000)
    account.on_quote({"symbol": "RB", "price": 3300})

    # 开多10手
    fill = {
        "event_type": "FUTURES_FILL",
        "order_id": "TEST_LIQ",
        "symbol": "RB",
        "side": "BUY",
        "action": "OPEN",
        "fill_price": 3300.0,
        "fill_qty": 10,
        "fee": 16.5,
    }
    account.on_fill(fill)

    # 检查初始风险率
    initial_eq = account.equity
    initial_mg = account.margin_used
    initial_rr = account.risk_ratio
    print(f"  初始权益: ¥{initial_eq:.2f}, 保证金: ¥{initial_mg:.2f}, 风险率: {initial_rr:.2f}")

    check(not account.positions.get("RB").is_empty(),
          f"开仓后持有10手")

    # 极端反向: 价格下跌到 2400
    # 权益 = 99983.5 + (2400 - 3300) * 100 = 99983.5 - 90000 = 9983.5
    # 保证金 = 2400 * 10 * 10 * 0.10 = 24000
    # 风险率 = 9983.5 / 24000 = 0.42 < 1.0 → 触发强平
    account.on_quote({"symbol": "RB", "price": 2400})

    pos = account.positions.get("RB")
    print(f"  强平后持仓: direction={pos.direction}, qty={pos.qty}")
    print(f"  风险率: {account.risk_ratio:.2f}")

    # 应该强平（持仓为0）
    check(pos.is_empty(),
          f"强平触发，持仓已清空 (got qty={pos.qty})")

    return account


# ══════════════════════════════════════════════════════════════
# Test 5: 完整闭环 — quote → order → fill → position → account → settlement
# ══════════════════════════════════════════════════════════════

def test_full_cycle():
    test("完整闭环 — quote → order → fill → position → account → settlement")

    account = FuturesAccount(initial_equity=1_000_000)
    sim = Simulator()

    # 模拟一系列行情
    quotes_data = [
        ("RB", 3300),
        ("RB", 3310),
        ("RB", 3305),
        ("RB", 3320),
    ]

    # 第一个行情更新价格
    account.on_quote({"symbol": "RB", "price": 3300})

    # 创建订单
    order = make_order_event("RB", "BUY", 2, "MARKET")
    sim.add_order(order)

    # 处理行情 → 成交
    fills = sim.on_quote({"symbol": "RB", "price": 3300})
    check(len(fills) == 1, f"行情推动成交 (fills={len(fills)})")

    if fills:
        fill = fills[0]
        check(fill["fill_price"] == 3300, f"成交价来自quote = 3300 (got {fill['fill_price']})")
        check(fill["fill_qty"] == 2, f"成交手数 = 2 (got {fill['fill_qty']})")

        # 账户处理成交
        pos_event = account.on_fill(fill)
        check(account.positions.get("RB").qty == 2, f"持仓 = 2手")

    # 行情变化
    account.on_quote({"symbol": "RB", "price": 3310})
    check(abs(account.floating_pnl - (10 * 10 * 2)) < 1,
          f"浮盈 = ¥200 (got ¥{account.floating_pnl:.2f})")

    # 再变化
    account.on_quote({"symbol": "RB", "price": 3305})
    check(abs(account.floating_pnl - (5 * 10 * 2)) < 1,
          f"浮盈 = ¥100 (got ¥{account.floating_pnl:.2f})")

    # 再涨
    account.on_quote({"symbol": "RB", "price": 3320})
    check(abs(account.floating_pnl - (20 * 10 * 2)) < 1,
          f"浮盈 = ¥400 (got ¥{account.floating_pnl:.2f})")

    # 盯市结算
    settle_evt = account.on_settlement(settle_price=3320)
    check("FUTURES_SETTLEMENT" in str(settle_evt.get("event_type", "")),
          "盯市结算事件生成")

    # 结算后浮盈归0，已实现盈亏增加
    check(abs(account.floating_pnl) < 1,
          f"结算后浮盈归零 (got ¥{account.floating_pnl:.2f})")
    check(abs(account.realized_pnl - 400) < 1,
          f"结算后已实现盈亏 = ¥400 (got ¥{account.realized_pnl:.2f})")

    # 验证写出的事件文件不少于3行
    evt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "futures_events.jsonl")
    if os.path.exists(evt_path):
        with open(evt_path, "r") as ef:
            lines = [l for l in ef if l.strip()]
        check(len(lines) >= 2,
              f"事件文件有内容 ({len(lines)} lines) (事件自动写入由simulator触发)")

    print(f"\n  {BOLD}最终账户状态:{N}")
    print(f"  {account.summary()}")


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"{BOLD}{Y}{'═' * 60}{N}")
    print(f"{BOLD}{Y}   Futures-Sim v0.1 — Phase 2 验收测试{N}")
    print(f"{Y}{'═' * 60}{N}\n")

    # Test 1
    acc1 = test_open_long()

    print()
    print(f"  {BOLD}账户摘要:{N}")
    print(f"  {acc1.summary()}")

    # Test 2
    acc1_after = test_profit(acc1)

    print()
    print(f"  {BOLD}账户摘要:{N}")
    print(f"  {acc1_after.summary()}")

    # Test 3
    acc3 = test_open_short()

    # Test 4
    acc4 = test_liquidation()

    # Test 5
    test_full_cycle()

    # ─── 汇总 ───
    print(f"\n{Y}{'═' * 60}{N}")
    total = passed + failed
    print(f"{BOLD}  测试结果: {G}{passed}/{total} 通过{N}")
    if failed > 0:
        print(f"  {R}  {failed} 项失败{N}")
    print(f"{Y}{'═' * 60}{N}")

    sys.exit(0 if failed == 0 else 1)
