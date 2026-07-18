"""replay/verifier.py — Replay 结果验证器

验证:
  A. 同输入必同输出 (fingerprint)
  B. 状态闭环 (quantity/asset conservation)
  C. 无外部调用穿透
"""


def verify_account_conservation(
    initial_cash: float,
    trades: list[dict],
    final_cash: float,
    final_positions: dict,
    total_fees: float,
) -> tuple[bool, list[str]]:
    """验证资金守恒: cash_before - Σcost - fees + Σincome = cash_after"""
    errors = []
    total_cost = 0.0
    total_income = 0.0

    for t in trades:
        t = t.get("trade", t)
        side = t.get("side", "").upper()
        price = float(t.get("price", 0))
        qty = int(t.get("quantity", 0))
        amount = price * qty
        if side == "BUY":
            total_cost += amount
        elif side == "SELL":
            total_income += amount

    expected_cash = initial_cash - total_cost + total_income - total_fees
    if abs(expected_cash - final_cash) > 0.02:
        errors.append(
            f"cash mismatch: expected={expected_cash:.2f}, actual={final_cash:.2f}"
        )

    return len(errors) == 0, errors


def verify_position_conservation(
    trades: list[dict],
    final_positions: dict[str, int],
) -> tuple[bool, list[str]]:
    """验证持仓守恒: Σbuy_qty - Σsell_qty = final_qty"""
    errors = []
    net: dict[str, int] = {}

    for t in trades:
        t = t.get("trade", t)
        sym = t.get("symbol", "")
        side = t.get("side", "").upper()
        qty = int(t.get("quantity", 0))
        if sym not in net:
            net[sym] = 0
        net[sym] += qty if side == "BUY" else -qty

    for sym, expected_qty in net.items():
        actual_qty = final_positions.get(sym, {}).get("quantity", 0)
        if expected_qty != actual_qty:
            errors.append(
                f"position mismatch {sym}: expected={expected_qty}, actual={actual_qty}"
            )

    return len(errors) == 0, errors


def verify_no_external_calls(log: list[str]) -> tuple[bool, list[str]]:
    """验证 replay 过程中没有外部调用"""
    blocked = ["tencent", "sina", "urllib", "request", "systemd", "network"]
    violations = []
    for entry in log:
        for b in blocked:
            if b in entry.lower():
                violations.append(f"external call detected: {entry}")
                break
    return len(violations) == 0, violations
