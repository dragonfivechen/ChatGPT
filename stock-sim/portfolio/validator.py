"""portfolio/validator.py — 组合数据检查"""


def validate_snapshot_data(
    account_id: str,
    cash: float,
    market_value: float,
    equity: float,
    holdings: list,
) -> tuple[bool, list[str]]:
    """检查快照数据是否合理"""
    errors = []

    if not account_id:
        errors.append("missing account_id")
    if cash < 0:
        errors.append(f"negative cash: {cash}")
    if market_value < 0:
        errors.append(f"negative market_value: {market_value}")
    if equity < 0:
        errors.append(f"negative equity: {equity}")

    # 资产守恒检查
    if abs(equity - (cash + market_value)) > 0.02:
        errors.append(
            f"equity mismatch: equity={equity} ≠ cash+mv={cash + market_value}"
        )

    # 权重检查
    total_weight = sum(h.get("weight", 0) for h in holdings)
    if abs(total_weight - 1.0) > 0.02 and total_weight > 0:
        errors.append(f"total weight={total_weight:.4f} ≠ 1.0")

    return len(errors) == 0, errors
