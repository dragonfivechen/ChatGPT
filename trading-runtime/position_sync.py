#!/usr/bin/env python3
"""
trading-runtime — position_sync.py

职责: 持仓一致性校验 — FILL 事件产生的持仓与 account 状态是否一致

验证方法:
  - 将 FILL 事件流独立重放 → 理论持仓
  - 对比 runtime_account 实际持仓
  - 偏差报告
"""

import json
from collections import defaultdict


def compute_theoretical_positions(fills_path: str) -> dict:
    """从 FILL 事件流独立重放持仓"""
    positions: dict[str, int] = defaultdict(int)
    fills = []
    with open(fills_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fills.append(json.loads(line))

    for fill in fills:
        sym = fill.get("symbol", "")
        action = fill.get("action", "").upper()
        qty = fill.get("qty", 0)

        if action == "BUY":
            positions[sym] += qty
        elif action == "SELL":
            positions[sym] -= qty
        elif action == "CLOSE":
            # 平仓: 归零（简化处理）
            positions[sym] = 0

    return dict(positions)


def verify(account_positions: dict, fills_path: str) -> dict:
    """校验 account 持仓 vs FILL 重放持仓"""
    theoretical = compute_theoretical_positions(fills_path)

    mismatches = []
    all_symbols = set(theoretical.keys()) | set(account_positions.keys())

    for sym in sorted(all_symbols):
        t_qty = theoretical.get(sym, 0)
        a_qty = account_positions.get(sym, {}).get("qty", 0) if isinstance(
            account_positions.get(sym), dict) else account_positions.get(sym, 0)

        if t_qty != a_qty:
            mismatches.append({
                "symbol": sym,
                "theoretical_qty": t_qty,
                "account_qty": a_qty,
                "delta": t_qty - a_qty,
            })

    return {
        "verified": len(mismatches) == 0,
        "total_symbols": len(all_symbols),
        "mismatches": mismatches,
    }


def report(result: dict) -> str:
    """格式化的校验报告"""
    lines = []
    lines.append(f"持仓一致性校验: {'✅ PASS' if result['verified'] else '❌ FAIL'}")
    lines.append(f"  品种数: {result['total_symbols']}")
    if result["mismatches"]:
        for m in result["mismatches"]:
            lines.append(f"  ❌ {m['symbol']}: 理论 {m['theoretical_qty']} ≠ 账户 {m['account_qty']} (Δ={m['delta']})")
    return "\n".join(lines)
