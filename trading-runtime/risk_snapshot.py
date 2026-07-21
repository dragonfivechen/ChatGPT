#!/usr/bin/env python3
"""
trading-runtime — risk_snapshot.py

职责: 风险快照 — 从估值结果生成风险状态报告

输入: PortfolioValuation 输出 + 账户历史
输出: 风险指标
      {
        "ts": "...",
        "equity": 998000,
        "total_margin": 15000,
        "margin_ratio": 1.5,
        "peak_equity": 1000000,
        "drawdown": 2000,
        "drawdown_pct": 0.2,
        "positions": 2,
        "total_upnl": -2000,
        "free_cash": 983000,
      }

特性:
  - 记录权益峰值 → 回撤
  - 记录最低 free_cash
  - 阈值警告
"""

import json
import os
from typing import Optional


class RiskSnapshot:
    """风险快照记录器"""

    def __init__(self, initial_balance: float = 1_000_000):
        self.peak_equity = initial_balance
        self.trough_equity = initial_balance
        self.lowest_free_cash = initial_balance
        self.snapshots: list[dict] = []
        self.drawdown_peak_equity = initial_balance

    def record(self, equity_info: dict, ts: str = "") -> dict:
        """记录一次风险快照"""
        equity = equity_info.get("equity", 0)
        free_cash = equity_info.get("free_cash", 0)

        if equity > self.peak_equity:
            self.peak_equity = equity
        if equity < self.trough_equity:
            self.trough_equity = equity
        if equity > self.drawdown_peak_equity:
            self.drawdown_peak_equity = equity
        if free_cash < self.lowest_free_cash:
            self.lowest_free_cash = free_cash

        dd = round(self.drawdown_peak_equity - equity, 2)
        dd_pct = round(dd / self.drawdown_peak_equity * 100, 4) if self.drawdown_peak_equity > 0 else 0

        snapshot = {
            "ts": ts,
            "equity": equity,
            "balance": equity_info.get("balance", 0),
            "total_margin": equity_info.get("total_margin_used", 0),
            "margin_ratio": equity_info.get("margin_ratio", 0),
            "total_upnl": equity_info.get("total_unrealized_pnl", 0),
            "free_cash": free_cash,
            "positions": len(equity_info.get("positions", {})),
            "peak_equity": self.peak_equity,
            "drawdown": dd,
            "drawdown_pct": dd_pct,
            "lowest_free_cash": self.lowest_free_cash,
        }

        self.snapshots.append(snapshot)
        return snapshot

    def latest(self) -> Optional[dict]:
        """最近一条快照"""
        return self.snapshots[-1] if self.snapshots else None

    def summary(self) -> dict:
        """累积风险摘要"""
        latest = self.latest()
        if not latest:
            return {"status": "NO_DATA"}

        warnings = []
        if latest["margin_ratio"] > 80:
            warnings.append("⚠️  保证金占比 > 80%")
        if latest["drawdown_pct"] > 20:
            warnings.append("⚠️  回撤 > 20%")
        if latest["free_cash"] < 0:
            warnings.append("🚨 可用资金为负")
        if latest["equity"] <= 0:
            warnings.append("🚨 权益归零")

        return {
            "current": latest,
            "peak_equity": self.peak_equity,
            "trough_equity": self.trough_equity,
            "total_drawdown": round(self.peak_equity - self.trough_equity, 2),
            "total_drawdown_pct": round(
                (self.peak_equity - self.trough_equity) / self.peak_equity * 100, 4
            ) if self.peak_equity > 0 else 0,
            "warnings": warnings,
        }

    def save(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for s in self.snapshots:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"[risk_snapshot] 💾 {len(self.snapshots)} 条快照 → {path}")

    @staticmethod
    def load(path: str) -> "RiskSnapshot":
        """从文件恢复风险状态"""
        rs = RiskSnapshot()
        if not os.path.exists(path):
            return rs
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                s = json.loads(line)
                rs.snapshots.append(s)
                # 恢复峰值/谷值
                eq = s.get("equity", 0)
                fc = s.get("free_cash", 0)
                rs.peak_equity = max(rs.peak_equity, eq)
                rs.trough_equity = min(rs.trough_equity, eq)
                rs.lowest_free_cash = min(rs.lowest_free_cash, fc)
                ppk = s.get("peak_equity", 0)
                rs.drawdown_peak_equity = max(rs.drawdown_peak_equity, ppk)
        return rs
