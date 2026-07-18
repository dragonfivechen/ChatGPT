"""portfolio/drawdown.py — peak_equity 跟踪 + 回撤计算

维护历史最高权益，用于计算当前回撤。
"""


class DrawdownTracker:
    """回撤跟踪器。记录 peak_equity，计算 drawdown。"""

    def __init__(self, initial_equity: float = 0):
        self.peak_equity = initial_equity

    def update(self, current_equity: float) -> tuple[float, float]:
        """更新并返回 (peak_equity, drawdown)"""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        drawdown = (
            (current_equity - self.peak_equity) / self.peak_equity
            if self.peak_equity > 0
            else 0.0
        )
        return self.peak_equity, drawdown
