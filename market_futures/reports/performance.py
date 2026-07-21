#!/usr/bin/env python3
"""
Futures-Sim v0.1 — reports/performance.py（绩效分析引擎）

注意: 当前结果基于 SIMULATED_MARKET（collector 状态机生成行情），
不是历史真实市场数据。不能直接等同于实盘表现。

输出:
  reports/trades.jsonl        每笔交易记录（account.py 写入）
  reports/equity_curve.jsonl  权益曲线（run_strategy.py 写入）
  reports/performance.json    核心绩效指标
  reports/strategy_compare.json 多策略对比
"""

import json
import os
import math
from collections import defaultdict

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)  # market_futures/
REPORTS_DIR = _THIS
EVENTS_PATH = os.path.join(_PROJECT, "futures_events.jsonl")


# ── 交易明细: trades.jsonl ─────────────────────────────

TRADES_PATH = os.path.join(REPORTS_DIR, "trades.jsonl")


def append_trade(trade: dict, path: str = TRADES_PATH) -> None:
    """追加一条已成交交易记录"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(trade, ensure_ascii=False) + "\n")


def load_trades(path: str = TRADES_PATH) -> list[dict]:
    """加载所有成交记录"""
    trades = []
    if not os.path.exists(path):
        return trades
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                trades.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return trades


# ── 权益曲线: equity_curve.jsonl ───────────────────────

EQUITY_PATH = os.path.join(REPORTS_DIR, "equity_curve.jsonl")


def append_equity_point(point: dict, path: str = EQUITY_PATH) -> None:
    """追加权益快照"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(point, ensure_ascii=False) + "\n")


def load_equity_curve(path: str = EQUITY_PATH) -> list[dict]:
    """加载权益曲线"""
    curve = []
    if not os.path.exists(path):
        return curve
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                curve.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return curve


# ── 核心指标计算 ────────────────────────────────────────

def calc_performance(trades: list[dict],
                     equity_curve: list[dict],
                     strategy_id: str = "",
                     environment: str = "SIMULATED_MARKET",
                     data_source: str = "collector_state_machine") -> dict:
    """根据交易明细和权益曲线计算核心绩效指标

    指标:
      - 收益: total_return, return_pct, annualized_return
      - 风险: max_drawdown, volatility
      - 交易质量: win_rate, profit_factor, avg_trade, avg_win, avg_loss
      - 行为: trade_count, avg_holding_time, long_ratio, short_ratio
      - 信号频率: signal_frequency, avg_trade_interval
    """
    result = {
        "strategy": strategy_id,
        "environment": environment,
        "data_source": data_source,
        "result_type": "strategy_comparison_v0.1",
        "note": "基于模拟行情，非真实历史数据。仅供参考比较。",
        "trades": len(trades),
    }

    # ── 权益数据 ──
    if equity_curve:
        start_equity = equity_curve[0].get("equity", 0)
        end_equity = equity_curve[-1].get("equity", 0)
        result["start_equity"] = start_equity
        result["end_equity"] = end_equity
        result["total_return"] = round(end_equity - start_equity, 2)
        result["return_pct"] = round(
            (end_equity / start_equity - 1) * 100, 2
        ) if start_equity else 0

        # 最大回撤 (drawdown from peak)
        peak = start_equity
        max_dd = 0.0
        max_dd_pct = 0.0
        for pt in equity_curve:
            eq = pt.get("equity", 0)
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = dd / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        result["max_drawdown"] = round(max_dd, 2)
        result["max_drawdown_pct"] = round(max_dd_pct, 2)

        # 波动率 (return std)
        returns = []
        prev_eq = equity_curve[0].get("equity", 0)
        for pt in equity_curve[1:]:
            eq = pt.get("equity", 0)
            if prev_eq > 0:
                returns.append((eq - prev_eq) / prev_eq)
            prev_eq = eq
        if returns:
            mean_r = sum(returns) / len(returns)
            variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            result["volatility"] = round(math.sqrt(variance) * 100, 4)
        else:
            result["volatility"] = 0
    else:
        result["start_equity"] = 0
        result["end_equity"] = 0
        result["total_return"] = 0
        result["return_pct"] = 0
        result["max_drawdown"] = 0
        result["max_drawdown_pct"] = 0
        result["volatility"] = 0

    # ── 交易统计 ──
    if trades:
        pnls = [t.get("pnl", 0) for t in trades]
        fees = [t.get("fee", 0) for t in trades]
        total_pnl = sum(pnls)
        total_fee = sum(fees)

        win_trades = [t for t in trades if t.get("pnl", 0) > 0]
        loss_trades = [t for t in trades if t.get("pnl", 0) <= 0]
        wins = len(win_trades)

        result["total_pnl"] = round(total_pnl, 2)
        result["total_fee"] = round(total_fee, 2)
        result["net_pnl"] = round(total_pnl - total_fee, 2)
        result["win_count"] = wins
        result["loss_count"] = len(loss_trades)
        result["win_rate"] = round(wins / len(trades) * 100, 2) if trades else 0

        avg_trade = total_pnl / len(trades) if trades else 0
        avg_win = sum(t["pnl"] for t in win_trades) / wins if wins else 0
        avg_loss = sum(t["pnl"] for t in loss_trades) / len(loss_trades) if loss_trades else 0
        result["avg_trade_pnl"] = round(avg_trade, 2)
        result["avg_win"] = round(avg_win, 2)
        result["avg_loss"] = round(avg_loss, 2)

        # Profit factor = gross profit / gross loss
        gross_profit = sum(t["pnl"] for t in win_trades) if wins else 0
        gross_loss = abs(sum(t["pnl"] for t in loss_trades)) if loss_trades else 0
        result["profit_factor"] = round(gross_profit / gross_loss, 4) if gross_loss > 0 else float('inf')

        # 平均持仓时间
        holding_ticks = [t.get("holding_ticks", 0) for t in trades]
        avg_holding = sum(holding_ticks) / len(holding_ticks) if holding_ticks else 0
        result["avg_holding_ticks"] = round(avg_holding, 1)

        # 多空比例
        long_trades = [t for t in trades if t.get("direction") == "LONG"]
        short_trades = [t for t in trades if t.get("direction") == "SHORT"]
        result["long_count"] = len(long_trades)
        result["short_count"] = len(short_trades)
        result["long_ratio"] = round(len(long_trades) / len(trades) * 100, 2) if trades else 0
        result["short_ratio"] = round(len(short_trades) / len(trades) * 100, 2) if trades else 0

        # 信号频率 (需要 events.jsonl 数据)
        sig_count = count_signals(strategy_id)
        if sig_count > 0:
            result["signal_count"] = sig_count
            result["signal_to_trade_ratio"] = round(len(trades) / sig_count, 4)

        # 品种贡献分析
        symbol_pnl = defaultdict(float)
        symbol_trades = defaultdict(int)
        for t in trades:
            sym = t.get("symbol", "")
            symbol_pnl[sym] += t.get("pnl", 0)
            symbol_trades[sym] += 1
        result["symbol_pnl"] = {
            sym: {"trades": symbol_trades[sym], "pnl": round(symbol_pnl[sym], 2)}
            for sym in sorted(symbol_pnl.keys())
        }

    return result


def count_signals(strategy_id: str = "") -> int:
    """统计 events 中的信号数"""
    if not os.path.exists(EVENTS_PATH):
        return 0
    count = 0
    with open(EVENTS_PATH, "r") as f:
        for line in f:
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("event_type") == "FUTURES_SIGNAL":
                if not strategy_id or evt.get("strategy_id") == strategy_id:
                    count += 1
    return count


def calc_all_metrics(strategy_id: str = "MA", environment: str = "SIMULATED_MARKET",
                     data_source: str = "collector_state_machine",
                     trades_path: str = "",
                     equity_path: str = "") -> dict:
    """读取现有的 trades + equity_curve ，计算 performance.json"""
    if not trades_path:
        trades_path = os.path.join(REPORTS_DIR, f"trades_{strategy_id.lower()}.jsonl")
    if not equity_path:
        equity_path = os.path.join(REPORTS_DIR, f"equity_curve_{strategy_id.lower()}.jsonl")
    trades = load_trades(trades_path)
    equity = load_equity_curve(equity_path)
    return calc_performance(trades, equity, strategy_id, environment, data_source)


def write_performance(strategy_id: str, path: str = "",
                      environment: str = "SIMULATED_MARKET",
                      data_source: str = "collector_state_machine",
                      trades_path: str = "",
                      equity_path: str = "") -> dict:
    """读取当前报告数据 → 计算 → 写入 performance.json"""
    if not path:
        path = os.path.join(REPORTS_DIR, f"performance_{strategy_id.lower()}.json")
    perf = calc_all_metrics(strategy_id, environment, data_source, trades_path, equity_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(perf, f, ensure_ascii=False, indent=2)
    return perf


def clear_reports(strategy_filter: str = "") -> None:
    """清除报告文件（供验证用）"""
    for suffix in ["", "_ma", "_breakout", "_rsi"]:
        for fname in [f"trades{suffix}.jsonl", f"equity_curve{suffix}.jsonl",
                      f"performance{suffix}.json"]:
            fpath = os.path.join(REPORTS_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
    # strategy_compare.json
    fpath = os.path.join(REPORTS_DIR, "strategy_compare.json")
    if os.path.exists(fpath):
        os.remove(fpath)


# ── 策略对比 ────────────────────────────────────────────

def write_strategy_comparison(results: dict[str, dict],
                              path: str = "") -> dict:
    """合并多个策略的 performance.json 为 strategy_compare.json"""
    if not path:
        path = os.path.join(REPORTS_DIR, "strategy_compare.json")

    compare = {
        "environment": "SIMULATED_MARKET",
        "data_source": "collector_state_machine",
        "result_type": "strategy_comparison_v0.1",
        "note": "基于模拟行情，非真实历史数据。仅供参考比较。",
        "generated_at": __import__('datetime',
                                    fromlist=['datetime']).datetime.now().strftime(
                                        "%Y-%m-%dT%H:%M:%S+08:00"),
        "strategies": {},
    }

    for name, perf in results.items():
        compare["strategies"][name] = {
            "total_return": perf.get("total_return", 0),
            "return_pct": perf.get("return_pct", 0),
            "max_drawdown_pct": perf.get("max_drawdown_pct", 0),
            "volatility": perf.get("volatility", 0),
            "win_rate": perf.get("win_rate", 0),
            "profit_factor": perf.get("profit_factor", 0),
            "avg_trade_pnl": perf.get("avg_trade_pnl", 0),
            "trade_count": perf.get("trades", 0),
            "avg_holding_ticks": perf.get("avg_holding_ticks", 0),
            "long_ratio": perf.get("long_ratio", 0),
            "short_ratio": perf.get("short_ratio", 0),
            "signal_count": perf.get("signal_count", 0),
            "signal_to_trade_ratio": perf.get("signal_to_trade_ratio", 0),
        }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(compare, f, ensure_ascii=False, indent=2)

    return compare



if __name__ == "__main__":
    import sys
    if "--clear" in sys.argv:
        clear_reports()
        print("✅ 报告已清除")
    elif "--report" in sys.argv:
        strategy = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv \
                   and len(sys.argv) > sys.argv.index("--report") + 1 else "MA"
        perf = write_performance(strategy)
        print(f"✅ {strategy} performance.json 已生成")
        print(json.dumps(perf, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 performance.py [--clear | --report <strategy>]")
