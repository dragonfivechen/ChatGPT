#!/usr/bin/env python3
"""
trading-runtime — run_runtime.py

Phase 6.2 主入口: Signal → ORDER → FILL → POSITION → VALUATION → RISK

用法:
  python3 run_runtime.py [--replay-events <quotes>] [--signal-events <signals>]
                         [--save-state] [--load-state <dir>] [--resume]

流程:
  1. 行情加载 + 信号消费
  2. 信号接收: SIGNAL → ORDER
  3. 执行器: ORDER + QUOTE → FILL
  4. 账户: FILL → POSITION
  5. 行情监控: 实时价格跟踪
  6. 估值: 浮盈浮亏 + 权益 + 保证金
  7. 风险快照: 回撤 + 预警
  8. 持仓一致性校验
  9. 状态持久化 (断点恢复)
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ── 运行时模块 ──────────────────────────────────────────────
from signal_receiver import read_signals, generate_orders, write_orders
from paper_executor import PaperExecutor
from runtime_account import RuntimeAccount
from market_monitor import MarketMonitor
from valuation import PortfolioValuation
from risk_snapshot import RiskSnapshot
from position_sync import verify, report as sync_report


STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")


def load_quotes(path: str) -> list[dict]:
    """从 JSONL 加载行情事件"""
    quotes = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            quotes.append(json.loads(line))
    print(f"  📊 行情事件: {len(quotes)} 条")
    return quotes


def save_state(account: RuntimeAccount, monitor: MarketMonitor,
               risk: RiskSnapshot, label: str = ""):
    """保存运行时状态到文件 (断点恢复用)"""
    state_dir = os.path.join(STATE_DIR, label) if label else STATE_DIR
    os.makedirs(state_dir, exist_ok=True)

    # 账户: 序列化关键字段
    acct_state = {
        "balance": account.balance,
        "equity": account.equity,
        "initial_balance": account.initial_balance,
        "positions": {
            s: {"qty": p["qty"], "avg_cost": p["avg_cost"],
                "unrealized_pnl": p["unrealized_pnl"],
                "realized_pnl": p["realized_pnl"]}
            for s, p in account.positions.items()
        },
    }
    with open(os.path.join(state_dir, "account.json"), "w") as f:
        json.dump(acct_state, f, ensure_ascii=False)

    # 行情
    monitor.save_snapshot(os.path.join(state_dir, "market_snapshot.json"))

    # 风险快照 (已有 save 方法)
    risk.save(os.path.join(state_dir, "risk_snapshots.jsonl"))

    state_meta = {
        "saved_at": datetime.now().isoformat(),
        "label": label or "default",
    }
    with open(os.path.join(state_dir, "state_meta.json"), "w") as f:
        json.dump(state_meta, f, ensure_ascii=False)

    print(f"  💾 状态已保存 → {state_dir}/")


def load_state(label: str = "") -> dict:
    """恢复运行时状态"""
    state_dir = os.path.join(STATE_DIR, label) if label else STATE_DIR

    # 账户
    acct_path = os.path.join(state_dir, "account.json")
    if os.path.exists(acct_path):
        with open(acct_path) as f:
            acct_state = json.load(f)
    else:
        print(f"  ⚠️  未找到状态文件: {acct_path}")
        return {"account": None, "monitor": None, "risk": None}

    account = RuntimeAccount(initial_balance=acct_state.get("initial_balance", 1_000_000))
    account.balance = acct_state.get("balance", account.balance)
    account.equity = acct_state.get("equity", account.equity)
    for sym, p in acct_state.get("positions", {}).items():
        account.positions[sym] = {
            "qty": p["qty"],
            "avg_cost": p["avg_cost"],
            "unrealized_pnl": p.get("unrealized_pnl", 0),
            "realized_pnl": p.get("realized_pnl", 0),
        }

    # 行情
    snap = MarketMonitor.load_snapshot(os.path.join(state_dir, "market_snapshot.json"))
    monitor = MarketMonitor(initial_snapshots=snap)

    # 风险
    risk = RiskSnapshot.load(os.path.join(state_dir, "risk_snapshots.jsonl"))

    print(f"  ↻ 状态已恢复 → {state_dir}/")
    return {"account": account, "monitor": monitor, "risk": risk}


def run_pipeline(orders: list[dict], quotes: list[dict],
                 account: RuntimeAccount, monitor: MarketMonitor,
                 risk: RiskSnapshot) -> dict:
    """执行完整 Signal → Account → Valuation → Risk 流水线"""
    executor = PaperExecutor()

    # 构建 QUOTE 时间索引
    quote_index: dict[str, list[dict]] = {}
    for q in quotes:
        sym = q.get("symbol", "")
        if sym:
            quote_index.setdefault(sym, []).append(q)

    # 预灌行情 (先全量喂给 monitor, 这样任何点的 valuation 都有行情)
    for q in quotes:
        if q.get("event_type") in ("FUTURES_QUOTE", "QUOTE", "quote"):
            monitor.feed(q)

    fills = []
    events = sorted(orders, key=lambda x: x.get("ts", ""))

    pv = PortfolioValuation()

    for o in events:
        sym = o.get("symbol", "")
        ts = o.get("ts", "")

        # 找到最近的 QUOTE 喂给 executor
        best = None
        for q in quote_index.get(sym, []):
            q_ts = q.get("ts", "")
            if q_ts <= ts:
                best = q
            elif best is None:
                best = q

        if best:
            executor.feed_quote(best)

        fill = executor.execute(o)
        if fill:
            fills.append(fill)
            account.apply_fill(fill)

            # 连续盯市估值 (使用 market_monitor 的最新价格)
            pv.sync_from_account(account.positions)
            market_snap = monitor.snapshot()
            equity_info = pv.compute_equity(account.balance, market_snap)

            # 风险快照
            risk.record(equity_info, ts=ts)

    return {
        "fills": fills,
        "executor_stats": executor.report(),
        "account_summary": account.summary(),
        "risk_summary": risk.summary(),
        "pv": pv,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Futures Runtime — Phase 6.2 Paper Trading")
    parser.add_argument("--replay-events", default=None,
                        help="行情 QUOTE 事件 JSONL")
    parser.add_argument("--signal-events", default=None,
                        help="SIGNAL 事件 JSONL")
    parser.add_argument("--initial-balance", type=float, default=1_000_000)
    parser.add_argument("--output-dir", default="reports",
                        help="输出目录 (默认: reports/)")
    parser.add_argument("--verify-only", action="store_true",
                        help="仅做持仓一致性校验")
    parser.add_argument("--save-state", action="store_true",
                        help="运行结束后保存状态 (断点恢复)")
    parser.add_argument("--load-state", default=None,
                        help="从指定标签恢复状态恢复运行 (例如 --load-state session_1)")
    parser.add_argument("--resume", action="store_true",
                        help="从最近的保存状态恢复")
    args = parser.parse_args()

    workspace = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(workspace, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # ── 输入源 ─────────────────────────────────────────────
    market_dir = os.path.join(workspace, "..", "market_futures")
    replay_path = args.replay_events
    if replay_path and not os.path.exists(replay_path):
        print(f"❌ replay-events 文件不存在: {replay_path}")
        sys.exit(1)
    if not replay_path:
        candidates = [
            os.path.join(market_dir, "data", "historical", "replay_akshare_6sym.jsonl"),
            os.path.join(market_dir, "futures_events.jsonl"),
        ]
        for c in candidates:
            if os.path.exists(c):
                replay_path = c
                break
    if not replay_path or not os.path.exists(replay_path):
        print("❌ 未找到行情事件文件。使用 --replay-events 指定。")
        sys.exit(1)

    signal_path = args.signal_events
    if signal_path and not os.path.exists(signal_path):
        print(f"❌ signal-events 文件不存在: {signal_path}")
        sys.exit(1)

    # ── 状态恢复 ──────────────────────────────────────────
    restored = None
    if args.resume:
        # 找最近的 session
        if os.path.exists(STATE_DIR):
            sessions = sorted(os.listdir(STATE_DIR))
            if sessions:
                restored = load_state(sessions[-1])
    elif args.load_state:
        restored = load_state(args.load_state)

    if restored and restored["account"]:
        account = restored["account"]
        monitor = restored["monitor"]
        risk = restored["risk"]
        print(f"  ↻ 恢复前状态: 权益 ¥{account.equity:,.2f}, "
              f"持仓 {len(account.positions)} 品种")
    else:
        account = RuntimeAccount(initial_balance=args.initial_balance)
        monitor = MarketMonitor()
        risk = RiskSnapshot(initial_balance=args.initial_balance)

    quotes = load_quotes(replay_path)

    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  Phase 6.2 — Runtime Paper Trading          ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"╠══════════════════════════════════════════════╣")
    print(f"║  行情源: {os.path.relpath(replay_path, workspace)}")
    print(f"║  信号源: {signal_path or '(自动)'}")
    print(f"║  初始权益: ¥{args.initial_balance:,.0f}")
    print(f"║  模式: {'恢复' if restored else '新建'}")
    print(f"╚══════════════════════════════════════════════╝")
    print()

    # ── Step 1: 信号消费 ──────────────────────────────────
    if signal_path:
        signals = read_signals(signal_path)
        orders = generate_orders(signals)
    else:
        signals = [q for q in quotes if q.get("event_type") == "FUTURES_SIGNAL"]
        orders = generate_orders(signals)

    if not orders:
        print("⚠️  没有 ORDER 事件可执行")
        sys.exit(0)

    orders_path = os.path.join(output_dir, "runtime_orders.jsonl")
    write_orders(orders, orders_path)
    print(f"  📝 ORDER 事件: {len(orders)} 条 → {os.path.relpath(orders_path, workspace)}")
    print()

    # ── Step 2: 执行流水线 ────────────────────────────────
    result = run_pipeline(orders, quotes, account, monitor, risk)

    fills_path = os.path.join(output_dir, "runtime_fills.jsonl")
    updates_path = os.path.join(output_dir, "runtime_positions.jsonl")

    with open(fills_path, "w", encoding="utf-8") as f:
        for fill in result["fills"]:
            f.write(json.dumps(fill, ensure_ascii=False) + "\n")
    print(f"  💱 FILL 事件: {len(result['fills'])} 条 → {os.path.relpath(fills_path, workspace)}")

    account.save_updates(updates_path)

    # ── Step 3: 执行统计 ──────────────────────────────────
    stats = result["executor_stats"]
    print()
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  执行统计                                    ║")
    print(f"╠══════════════════════════════════════════════╣")
    print(f"║  处理: {stats['processed']:4d} ORDER")
    print(f"║  成交: {stats['filled']:4d} FILL")
    print(f"║  丢弃: {stats['dropped']:4d} ORDER")
    print(f"╚══════════════════════════════════════════════╝")

    # ── Step 4: 估值 + 风险 ──────────────────────────────
    risk_summary = result["risk_summary"]
    latest = risk_summary.get("current", {})
    print()
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  连续盯市估值                                ║")
    print(f"╠══════════════════════════════════════════════╣")
    print(f"║  可用资金: ¥{latest.get('free_cash', 0):>10,.2f}")
    print(f"║  未实现盈亏: ¥{latest.get('total_upnl', 0):>+8,.2f}")
    print(f"║  占用保证金: ¥{latest.get('total_margin', 0):>8,.2f}")
    print(f"║  保证金占比: {latest.get('margin_ratio', 0):>7.2f}%")
    print(f"║  当前权益: ¥{latest.get('equity', 0):>10,.2f}")
    print(f"║  权益峰值: ¥{risk_summary.get('peak_equity', 0):>10,.2f}")
    print(f"║  当前回撤: ¥{latest.get('drawdown', 0):>+8,.2f}")
    print(f"║  回撤比例: {latest.get('drawdown_pct', 0):>7.4f}%")
    print(f"╠──────────────────────────────────────────────╣")
    pos_detail = latest.get('positions', risk_summary.get('positions', {}))
    if isinstance(pos_detail, dict):
        for sym, v in sorted(pos_detail.items()):
            print(f"║  {sym:4s}  {'多' if v.get('qty',0)>0 else '空' if v.get('qty',0)<0 else '平'}"
                  f"  {abs(v.get('qty',0)):2d}手  "
                  f"成本¥{v.get('avg_cost',0):>8.1f}  "
                  f"现价¥{v.get('current_price',0):>8.1f}  "
                  f"浮盈¥{v.get('unrealized_pnl',0):>+8.2f}")
    print(f"╚══════════════════════════════════════════════╝")

    if risk_summary.get("warnings"):
        print()
        for w in risk_summary["warnings"]:
            print(f"  {w}")
        print()

    # ── Step 5: 持仓一致性校验 ────────────────────────────
    print()
    v_result = verify(account.summary()["positions"], fills_path)
    print(sync_report(v_result))
    print()

    if args.verify_only:
        return

    # ── Step 6: 保存运行时事件流 ──────────────────────────
    runtime_events_path = os.path.join(output_dir, "runtime_events.jsonl")
    with open(runtime_events_path, "w", encoding="utf-8") as f:
        for o in orders:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
        for fill in result["fills"]:
            f.write(json.dumps(fill, ensure_ascii=False) + "\n")
        for u in account.updates:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
        # 估值快照
        for s in risk.snapshots:
            f.write(json.dumps({"event_type": "VALUATION_SNAPSHOT", **s}, ensure_ascii=False) + "\n")

    print(f"📦 运行时事件流: {os.path.relpath(runtime_events_path, workspace)}")
    print()

    # ── Step 7: 状态保存 (断点恢复) ──────────────────────
    if args.save_state:
        label = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_state(account, monitor, risk, label=label)

    print(f"{'✅ Phase 6.2 Pipeline Complete':^50}")
    print(f"{'🔒 Runtime Paper Trading + Valuation + Risk':^50}")


if __name__ == "__main__":
    main()
