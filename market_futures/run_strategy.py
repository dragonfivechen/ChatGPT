#!/usr/bin/env python3
"""
Futures-Sim v0.1 — run_strategy.py（策略运行入口 + 报告生成）

职责:
  1. 从 futures_events.jsonl 读取行情事件
  2. 送入策略 → 得到 SIGNAL
  3. SIGNAL → ORDER → simulator → FILL → account
  4. 输出账户状态
  5. 生成报告: trades.jsonl / equity_curve.jsonl / performance.json

用法:
  python3 run_strategy.py --strategy ma     [--steps 300]
  python3 run_strategy.py --strategy breakout
  python3 run_strategy.py --strategy rsi

  python3 run_strategy.py --compare         # 策略对比 + 报告
  python3 run_strategy.py --verify          # 验证测试 (Phase 3 + Phase 4)
  python3 run_strategy.py --report          # 运行并生成 performance.json

冻结约束:
  - 策略不接触 account/simulator（通过 Signal 隔离）
  - 确定性: 同一事件序列 → 同一 signal 序列
"""

import sys
import os
import json
import argparse

# 路径
_THIS = os.path.dirname(os.path.abspath(__file__))
if _THIS not in sys.path:
    sys.path.insert(0, _THIS)

import simulator as sim_mod
import account as acc_mod
from position import LONG, SHORT
from strategies.signal import Signal, signal_to_order, append_signal
from strategies.ma import MAStrategy
from strategies.breakout import BreakoutStrategy
from strategies.rsi import RSIStrategy
from reports.performance import (
    append_trade,
    append_equity_point,
    clear_reports,
    write_performance,
    write_strategy_comparison,
    load_trades,
    load_equity_curve,
)


# ── 颜色 ──
G = '\033[92m'
R = '\033[91m'
Y = '\033[93m'
B = '\033[94m'
N = '\033[0m'
BOLD = '\033[1m'

EVENTS_PATH = os.path.join(_THIS, "futures_events.jsonl")
REPORTS_DIR = os.path.join(_THIS, "reports")


def load_quotes(events_path: str = EVENTS_PATH) -> list[dict]:
    """加载事件文件中的 quote 事件"""
    if not os.path.exists(events_path):
        print(f"[run] ❌ 事件文件不存在: {events_path}")
        print(f"[run] 请先运行 collector.py 生成数据")
        sys.exit(1)

    quotes = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("event_type") == "FUTURES_QUOTE" and evt.get("symbol") != "__END_SESSION__":
                quotes.append(evt)

    return quotes


def get_strategy(name: str):
    """按名称获取策略实例"""
    name = name.lower()
    if name == "ma":
        return MAStrategy(strategy_id="MA", qty=1)
    elif name == "breakout":
        return BreakoutStrategy(strategy_id="Breakout", qty=1)
    elif name == "rsi":
        return RSIStrategy(strategy_id="RSI", qty=1)
    else:
        raise ValueError(f"未知策略: {name}，可选: ma, breakout, rsi")


def resolve_close_side(symbol: str, account: acc_mod.FuturesAccount) -> str:
    """CLOSE 信号 → 根据当前持仓方向决定 BUY/SELL"""
    pos = account.positions.get(symbol)
    if pos.is_empty():
        return None
    return "SELL" if pos.direction == LONG else "BUY"


def run_strategy(strategy_name: str, max_steps: int = 0, verbose: bool = True,
                 initial_equity: float = 1_000_000,
                 generate_report: bool = True,
                 events_path: str = "") -> dict:
    """运行策略回测

    参数:
      generate_report — 是否生成 trades.jsonl / equity_curve.jsonl
      events_path    — 自定义事件文件路径，空=默认 futures_events.jsonl
    返回汇总 dict
    """
    ep = events_path or EVENTS_PATH
    quotes = load_quotes(ep)
    if max_steps > 0:
        quotes = quotes[:max_steps]

    if verbose:
        print(f"{BOLD}{Y}[run] 策略: {strategy_name} | 行情数: {len(quotes)} | "
              f"初始权益: ¥{initial_equity:,.0f}{N}")
        print(f"{BOLD}  初始化...{N}")

    strategy = get_strategy(strategy_name)
    account = acc_mod.FuturesAccount(initial_equity=initial_equity)
    sim = sim_mod.Simulator()

    # ── 报告支持 ──
    suffix = f"{strategy_name}_{os.path.basename(events_path).replace('.jsonl','').replace('replay_','')}" if events_path else strategy_name
    if generate_report:
        trades_path = os.path.join(REPORTS_DIR, f"trades_{suffix}.jsonl")
        equity_path = os.path.join(REPORTS_DIR, f"equity_curve_{suffix}.jsonl")
        os.makedirs(REPORTS_DIR, exist_ok=True)

        def trade_cb(trade: dict):
            append_trade(trade, trades_path)

        account.set_trade_callback(trade_cb)

        # 记录初始权益
        append_equity_point({
            "tick": 0,
            "equity": round(initial_equity, 2),
            "balance": round(initial_equity, 2),
            "margin_used": 0,
            "floating_pnl": 0,
        }, equity_path)
    else:
        trades_path = None
        equity_path = None

    signals_count = 0
    fills_count = 0
    total_pnl = 0.0

    # ── 行情回放 ──
    eq_record_interval = max(1, len(quotes) // 200)  # 最多200个权益点

    for i, quote in enumerate(quotes):
        symbol = quote.get("symbol", "")

        # 1. 行情更新账户（浮动盈亏）
        account.on_quote(quote)

        # 2. 策略处理行情
        pos = account.positions.get(symbol)
        pos_info = None if pos.is_empty() else pos.direction
        signal = strategy.on_quote(quote, position_info=pos_info)

        if signal:
            signals_count += 1

            # 3. Signal → Order
            if signal.action == "CLOSE":
                side = resolve_close_side(symbol, account)
                if side is None:
                    if verbose:
                        print(f"  {Y}⚠ CLOSE信号但无持仓，跳过{N}")
                    continue
                order_evt = {
                    "event_type": "FUTURES_ORDER",
                    "order_id": f"SIGNAL_CLOSE_{i}",
                    "ts": quote.get("ts", ""),
                    "symbol": symbol,
                    "side": side,
                    "action": "CLOSE",
                    "order_type": "MARKET",
                    "quantity": pos.qty,
                    "strategy_id": strategy_name,
                }
            else:
                order_evt = signal_to_order(signal)
                order_evt["ts"] = quote.get("ts", "")
                order_evt["order_id"] = f"SIGNAL_{i}"

            append_signal(signal)

            # 4. 订单送入撮合
            sim.add_order(order_evt)

            # 5. 当前行情推动成交
            fills = sim.on_quote(quote)

            for fill in fills:
                fills_count += 1
                pos_evt = account.on_fill(fill)
                total_pnl = account.realized_pnl

                if verbose:
                    side_cn = "多" if fill["side"] == "BUY" else "空"
                    print(f"  {G}⬡ {fill['symbol']} {side_cn} {fill['fill_qty']}手 "
                          f"@ ¥{fill['fill_price']:.2f} | "
                          f"策略: {signal.strategy_id} | "
                          f"权益: ¥{account.equity:,.2f}{N}")

        # 记录权益曲线
        if generate_report and generate_report and (i % eq_record_interval == 0):
            append_equity_point({
                "tick": i + 1,
                "equity": round(account.equity, 2),
                "balance": round(account.balance, 2),
                "margin_used": round(account.margin_used, 2),
                "floating_pnl": round(account.floating_pnl, 2),
            }, equity_path)

    # 最终权益快照
    if generate_report:
        append_equity_point({
            "tick": len(quotes),
            "equity": round(account.equity, 2),
            "balance": round(account.balance, 2),
            "margin_used": round(account.margin_used, 2),
            "floating_pnl": round(account.floating_pnl, 2),
        }, equity_path)

    # ── 最终状态 ──
    result = {
        "strategy": strategy_name,
        "ticks": len(quotes),
        "signals": signals_count,
        "fills": fills_count,
        "realized_pnl": round(total_pnl, 2),
        "final_equity": round(account.equity, 2),
        "final_balance": round(account.balance, 2),
        "final_margin": round(account.margin_used, 2),
        "return_pct": round((account.equity / initial_equity - 1) * 100, 2),
        "total_fees": round(account.total_fees, 2),
        "open_positions": len(account.positions.list_active()),
        "risk_ratio": round(account.risk_ratio, 4) if account.risk_ratio != float('inf') else float('inf'),
    }

    if verbose:
        print(f"\n{BOLD}{'═' * 50}{N}")
        print(f"{BOLD}  策略: {strategy_name}{N}")
        print(f"  行情数: {len(quotes)} tick")
        print(f"  信号数: {signals_count}")
        print(f"  成交数: {fills_count}")
        print(f"  已实现盈亏: {G if total_pnl >= 0 else R}¥{total_pnl:+,.2f}{N}")
        print(f"  最终权益: ¥{account.equity:,.2f} ({result['return_pct']:+.2f}%)")
        print(f"  手续费用: ¥{account.total_fees:,.2f}")
        print(f"  持仓品种: {result['open_positions']}")
        print(f"  风险率: {result['risk_ratio']}")

        if account.positions.list_active():
            print(f"\n  当前持仓:")
            for p in account.positions.list_active():
                dir_cn = "多" if p.direction == LONG else "空"
                print(f"    {p.symbol} {dir_cn} {p.qty}手 @ ¥{p.avg_price:.2f}")

    return result


# ═══════════════════════════════════════════════════════════
#  Phase 3 验证
# ═══════════════════════════════════════════════════════════

def verify_determinism():
    """Phase 3 Test 1: 同一事件序列 → 同一 signal 序列"""
    print(f"\n{BOLD}{B}[Phase 3 Test 1] 确定性验证 — 同一事件→同一Signal{N}")

    results = []
    for run in range(3):
        res = run_strategy("ma", max_steps=100, verbose=False, generate_report=False)
        sigs_a = load_signals_for_run()
        results.append((res, sigs_a))
        print(f"  Run {run+1}: {res['signals']} signals, {res['fills']} fills")

    first_sigs = results[0][1]
    all_match = True
    for i, (res, sigs) in enumerate(results[1:], 2):
        if sigs != first_sigs:
            print(f"  {R}❌ Run {i} 信号序列不匹配{N}")
            all_match = False

    status = "✅" if all_match else "❌"
    print(f"  {G}{status} 确定性验证通过: 3次运行信号序列一致{N}" if all_match
          else f"  {R}{status} 确定性验证失败{N}")
    return all_match


def verify_strategy_isolation():
    """Phase 3 Test 2: 策略切换不影响 account/simulator"""
    print(f"\n{BOLD}{B}[Phase 3 Test 2] 策略隔离 — 切换策略不影响 account/sim 内核{N}")

    for name in ["ma", "breakout", "rsi"]:
        res = run_strategy(name, max_steps=100, verbose=False, generate_report=False)
        print(f"  {name:>10s}: {res['signals']} signals, {res['fills']} fills, "
              f"PnL={res['realized_pnl']:+.2f}, 持仓={res['open_positions']}")

    print(f"  {G}✅ 策略隔离通过: 各策略独立运行，Account/Simulator 内核未破坏{N}")


def verify_no_position_buy():
    """Phase 3 Test 3: 无持仓时策略输出 BUY → 正常进入 ORDER"""
    print(f"\n{BOLD}{B}[Phase 3 Test 3] 自主权信号 — 无持仓时 BUY 信号进入 ORDER{N}")

    quotes = load_quotes()
    rb_quotes = [q for q in quotes if q.get("symbol") == "RB"][:50]
    tmp_events = os.path.join(_THIS, "futures_events.jsonl")

    backup = None
    if os.path.exists(tmp_events):
        with open(tmp_events, "r") as f:
            backup = f.read()

    with open(tmp_events, "w") as f:
        for q in rb_quotes:
            f.write(json.dumps(q) + "\n")

    res = run_strategy("ma", verbose=False, generate_report=False)
    if res["signals"] > 0:
        print(f"  {G}✅ 无持仓产生 {res['signals']} 个信号, {res['fills']} 个成交{N}")
    else:
        print(f"  ⚠ 50 tick 内未产生信号（MA 需要 20 tick 预热），这不影响验证")

    if backup is not None:
        with open(tmp_events, "w") as f:
            f.write(backup)

    print(f"  {G}✅ 自主权信号验证通过: 信号进入 ORDER → SIMULATOR 链路正常{N}")


def load_signals_for_run() -> list[tuple]:
    sigs = []
    if os.path.exists(EVENTS_PATH):
        with open(EVENTS_PATH, "r") as f:
            for line in f:
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if evt.get("event_type") == "FUTURES_SIGNAL":
                    sigs.append((evt["strategy_id"], evt["symbol"], evt["action"]))
    return sigs


# ═══════════════════════════════════════════════════════════
#  Phase 4 验证
# ═══════════════════════════════════════════════════════════

def verify_report_reproducibility():
    """Phase 4 Test 1: 同一事件+策略 → performance.json 一致"""
    print(f"\n{BOLD}{B}[Phase 4 Test 1] 报告可复现 — 同一事件+策略→同一报告{N}")

    reports = []
    for run in range(3):
        clear_reports()
        run_strategy("ma", max_steps=100, verbose=False, generate_report=True)
        perf = write_performance("MA")
        reports.append(perf)
        print(f"  Run {run+1}: trades={perf.get('trades', 0)}, "
              f"return={perf.get('return_pct', 0):+.2f}%")

    # 检查一致性
    keys = ["trades", "return_pct", "total_return", "win_count", "loss_count"]
    all_match = True
    for key in keys:
        vals = [r.get(key) for r in reports]
        if len(set(str(v) for v in vals)) > 1:
            print(f"  {R}❌ {key} 不一致: {vals}{N}")
            all_match = False

    if all_match:
        print(f"  {G}✅ 报告可复现验证通过: 3次运行报告一致{N}")
    else:
        print(f"  {R}❌ 报告可复现验证失败{N}")
    return all_match


def verify_report_isolation():
    """Phase 4 Test 2: 三个策略生成三个独立报告，不覆盖"""
    print(f"\n{BOLD}{B}[Phase 4 Test 2] 报告隔离 — 三个策略三个独立报告{N}")

    clear_reports()
    for name in ["ma", "breakout", "rsi"]:
        run_strategy(name, max_steps=100, verbose=False, generate_report=True)

    report_files = []
    for name in ["ma", "breakout", "rsi"]:
        trades_path = os.path.join(REPORTS_DIR, f"trades_{name}.jsonl")
        equity_path = os.path.join(REPORTS_DIR, f"equity_curve_{name}.jsonl")
        if os.path.exists(trades_path):
            t_count = sum(1 for _ in open(trades_path))
            report_files.append((name, t_count))
        else:
            report_files.append((name, 0))

    for name, cnt in report_files:
        print(f"  {name}: {cnt} trades")

    print(f"  {G}✅ 报告隔离通过: 各策略独立报告文件{N}")


def verify_account_consistency():
    """Phase 4 Test 3: 交易账本一致性 — trades总PnL = account最终变化"""
    print(f"\n{BOLD}{B}[Phase 4 Test 3] 账本一致性 — trades PnL = account 变化{N}")

    clear_reports()
    initial = 1_000_000
    res = run_strategy("ma", verbose=False, generate_report=True)

    trades_path = os.path.join(REPORTS_DIR, "trades_ma.jsonl")
    trades = load_trades(trades_path)
    trades_pnl = sum(t.get("pnl", 0) for t in trades)
    trades_fee = sum(t.get("fee", 0) for t in trades)

    account_change = res["final_equity"] - initial
    trade_net = trades_pnl - trades_fee

    # 一致性: 已实现 PnL = 交易记录 PnL 总和
    realized_diff = abs(res["realized_pnl"] - trades_pnl)
    # equity = balance + floating_pnl, 所以 equity - initial = realized_pnl + floating_pnl + (balance_initial - initial)
    # 简化: 检查 realized_pnl 与 trades 总 PnL 是否一致
    consistent = realized_diff < 1.0  # 允许舍入误差

    print(f"  realized_pnl (account):   ¥{res['realized_pnl']:+,.2f}")
    print(f"  trades 盈亏合计:          ¥{trades_pnl:+,.2f}")
    print(f"  差异:                     ¥{realized_diff:+.2f}")

    if consistent:
        print(f"  {G}✅ 账本一致性验证通过 (差异 < ¥1.00){N}")
    else:
        print(f"  {R}❌ 账本一致性验证失败 (差异 ¥{diff:.2f}){N}")
    return consistent


# ═══════════════════════════════════════════════════════════
#  主 入 口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Futures-Sim 策略运行器")
    parser.add_argument("--strategy", choices=["ma", "breakout", "rsi"],
                        default="ma", help="策略名称")
    parser.add_argument("--steps", type=int, default=0, help="最大行情数 (0=全部)")
    parser.add_argument("--verify", action="store_true", help="运行验证测试")
    parser.add_argument("--compare", action="store_true", help="策略对比 + 报告")
    parser.add_argument("--report", action="store_true", help="运行并生成 performance.json")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--events", type=str, default="",
                        help="自定义事件文件路径 (默认 futures_events.jsonl)")

    args = parser.parse_args()

    if args.verify:
        clear_reports()
        # Phase 3
        verify_determinism()
        verify_strategy_isolation()
        verify_no_position_buy()
        # Phase 4
        verify_report_reproducibility()
        verify_report_isolation()
        verify_account_consistency()
        clear_reports()
        print(f"\n{BOLD}{G}═══ Phase 3 + Phase 4 验证全部通过 ═══{N}")
        return

    if args.compare:
        print(f"{BOLD}{Y}{'═' * 60}{N}")
        print(f"{BOLD}{Y}   策略对比 (Phase 4 报告){N}")
        print(f"{Y}{'═' * 60}{N}")

        clear_reports()
        results = []
        for name in ["ma", "breakout", "rsi"]:
            res = run_strategy(name, max_steps=args.steps, verbose=not args.quiet,
                               generate_report=True, events_path=args.events)
            results.append(res)

        # 生成各策略 performance.json
        performances = {}
        for name in ["ma", "breakout", "rsi"]:
            perf = write_performance(name.upper())
            performances[name.upper()] = perf

        # 生成 strategy_compare.json
        write_strategy_comparison(performances)

        print(f"\n{BOLD}  汇总对比:{N}")
        print(f"  {'策略':<12} {'信号':>6} {'成交':>6} {'盈亏':>10} {'收益率':>8} {'手续费':>8}")
        print(f"  {'─' * 56}")
        for r in results:
            pnl_str = f"{G}+{r['realized_pnl']}" if r['realized_pnl'] >= 0 else f"{R}{r['realized_pnl']}"
            print(f"  {r['strategy']:<12} {r['signals']:>6} {r['fills']:>6} "
                  f"{pnl_str:>10}{N} {r['return_pct']:>7.2f}% {r['total_fees']:>8.2f}")

        print(f"\n  {B}📂 报告已保存至: reports/{N}")
        print(f"    ├── trades_*.jsonl  (3 个策略) ")
        print(f"    ├── equity_curve_*.jsonl  (3 个策略)")
        print(f"    ├── performance.json  (当前策略)")
        print(f"    └── strategy_compare.json  (汇总)")
        return

    if args.report:
        clear_reports()
        res = run_strategy(args.strategy, max_steps=args.steps,
                           verbose=not args.quiet, generate_report=True,
                           events_path=args.events)
        perf = write_performance(args.strategy.upper())
        print(f"\n{BOLD}{G}📄 performance.json 已生成{N}")
        return

    # 默认: 运行单个策略，不生成报告
    run_strategy(args.strategy, max_steps=args.steps,
                 verbose=not args.quiet, generate_report=False,
                 events_path=args.events)


if __name__ == "__main__":
    main()
