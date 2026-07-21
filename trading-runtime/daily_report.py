"""
trading-runtime — daily_report.py (收盘日报)

职责:
  - 收盘后生成交易日报
  - 汇总当日成交/持仓/盈亏/风险数据
  - 输出 JSON + 文本摘要 (用于控制台/TG推送)

格式 (JSON):
  {
    "date": "2026-07-21",
    "initial_cash": 10000000,
    "final_equity": 10035200,
    "daily_pnl": 35200,
    "daily_pnl_pct": 0.35,
    "trades": 18,
    "win_rate": 55.5,
    "positions": 3,
    "max_drawdown_pct": 1.8,
    "winning_trades": 10,
    "losing_trades": 8,
    "symbol_stats": {
      "RB": {"trades": 8, "pnl": 12000},
      "CU": {"trades": 10, "pnl": 23200}
    }
  }
"""

import json
import os
from datetime import datetime, date, timezone, timedelta

BJT = timezone(timedelta(hours=8))


def _load_signal_log_strategy_stats(strategy_runner=None) -> dict:
    """从 strategy_runner 获取策略统计"""
    if strategy_runner and hasattr(strategy_runner, "signal_stats"):
        return strategy_runner.signal_stats()
    return {"total_signals": 0, "by_strategy": {}}


def _compute_daily_pnl(account_start: float, account_end: float) -> float:
    """计算日盈亏"""
    return account_end - account_start


class DailyReport:
    """收盘日报生成器"""

    def __init__(self, config: dict = None,
                 output_dir: str = None):
        """
        Args:
            config: session_config.json
            output_dir: 日报输出目录
        """
        self.config = config or {}
        report_cfg = self.config.get("daily_report", {})
        self._enabled = report_cfg.get("enable", True)

        if output_dir:
            self._output_dir = output_dir
        elif config:
            self._output_dir = config.get("daily_report", {}).get(
                "output_dir", "reports/daily")
        else:
            self._output_dir = "reports/daily"

        self._report_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self._output_dir)

        self._today = date.today()
        self._report = None

    def generate(self, account, risk_snapshot=None,
                 fills: list[dict] = None,
                 strategy_runner=None) -> dict:
        """
        生成收盘日报

        Args:
            account: RuntimeAccount 实例
            risk_snapshot: RiskSnapshot 实例
            fills: 当日成交列表
            strategy_runner: StrategyRunner 实例 (可选)

        Returns:
            dict: 日报数据结构
        """
        if not self._enabled:
            return {"status": "DISABLED"}

        account_summary = account.summary()

        # ── 基础数据 ──
        initial_cash = account.initial_balance
        final_equity = account.equity
        total_realized_pnl = account_summary.get("total_realized_pnl", 0)
        unrealized_pnl = sum(
            p.get("unrealized_pnl", 0)
            for p in account_summary.get("positions", {}).values()
        )
        daily_pnl = _compute_daily_pnl(initial_cash, final_equity)

        # ── 成交统计 ──
        fills = fills or []
        total_trades = len(fills)
        winning_trades = sum(
            1 for f in fills if f.get("realized_pnl", 0) > 0)
        losing_trades = sum(
            1 for f in fills if f.get("realized_pnl", 0) < 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # ── 品种统计 ──
        symbol_stats = {}
        for f in fills:
            sym = f.get("symbol", "")
            if sym not in symbol_stats:
                symbol_stats[sym] = {"trades": 0, "pnl": 0.0}
            symbol_stats[sym]["trades"] += 1
            symbol_stats[sym]["pnl"] += f.get("realized_pnl", 0)

        # ── 持仓 ──
        positions_data = {}
        for sym, p in account_summary.get("positions", {}).items():
            if p["qty"] != 0:
                positions_data[sym] = {
                    "qty": p["qty"],
                    "avg_cost": p["avg_cost"],
                    "unrealized_pnl": p.get("unrealized_pnl", 0),
                    "market_value": p.get("market_value", 0),
                }

        # ── 风险数据 ──
        risk_data = {}
        if risk_snapshot:
            risk_summary = risk_snapshot.summary()
            risk_data = {
                "peak_equity": risk_snapshot.peak_equity,
                "max_drawdown": risk_summary.get("total_drawdown", 0),
                "max_drawdown_pct": risk_summary.get("total_drawdown_pct", 0),
                "current_drawdown": risk_summary.get("current", {}).get(
                    "drawdown", 0),
                "current_drawdown_pct": risk_summary.get("current", {}).get(
                    "drawdown_pct", 0),
            }

        # ── 策略统计 ──
        strategy_stats = {}
        if strategy_runner:
            sig_stats = _load_signal_log_strategy_stats(strategy_runner)
            for sid, st in sig_stats.get("by_strategy", {}).items():
                strategy_stats[sid] = {
                    "signals": st["signals"],
                    "actions": st["actions"],
                }

        # ── 组装 ──
        self._report = {
            "report_type": "DAILY",
            "date": self._today.isoformat(),
            "generated_at": datetime.now(BJT).isoformat(),
            "initial_cash": initial_cash,
            "final_equity": round(final_equity, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(
                daily_pnl / initial_cash * 100 if initial_cash > 0 else 0, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 1),
            "positions": len(positions_data),
            "position_details": positions_data,
            "symbol_stats": symbol_stats,
            **risk_data,
            "strategy_stats": strategy_stats,
        }

        # 写入文件
        self._save()

        return self._report

    def _save(self):
        """保存日报文件"""
        if not self._report:
            return

        os.makedirs(self._report_dir, exist_ok=True)
        filename = f"daily_{self._today.isoformat()}.json"
        path = os.path.join(self._report_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._report, f, ensure_ascii=False, indent=2)

        print(f"[daily_report] 💾 日报 → {path}")

    def text_summary(self, report: dict = None) -> str:
        """生成可读的文本摘要"""
        r = report or self._report
        if not r:
            return "(无日报数据)"

        lines = []
        lines.append(f"📊 {r['date']} 交易总结")
        lines.append("─" * 30)

        # 盈亏
        pnl = r["daily_pnl"]
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        lines.append(f"{pnl_emoji} 收益: {pnl:+.0f} ({r['daily_pnl_pct']:+.2f}%)")
        lines.append(f"💰 权益: ¥{r['final_equity']:,.0f}")

        # 成交
        lines.append(f"💱 交易: {r['trades']}笔 "
                     f"(胜率 {r['win_rate']:.1f}% "
                     f"{r['winning_trades']}/{r['losing_trades']})")

        # 最大回撤
        mdd = r.get("max_drawdown_pct", 0)
        lines.append(f"📉 最大回撤: {mdd:+.2f}%")

        # 持仓
        pos_count = r.get("positions", 0)
        lines.append(f"📦 持仓: {pos_count}个品种")
        for sym, pd in r.get("position_details", {}).items():
            dir_str = "多" if pd["qty"] > 0 else "空"
            lines.append(f"   {sym}: {dir_str} {abs(pd['qty'])}手 "
                         f"浮盈¥{pd['unrealized_pnl']:+.0f}")

        # 策略统计
        strat_stats = r.get("strategy_stats", {})
        if strat_stats:
            lines.append(f"📡 策略信号:")
            for sid, st in strat_stats.items():
                acts = ", ".join(f"{a}={c}" for a, c in st["actions"].items())
                lines.append(f"   {sid}: {st['signals']} ({acts})")

        return "\n".join(lines)

    @property
    def latest_report(self) -> dict | None:
        return self._report
