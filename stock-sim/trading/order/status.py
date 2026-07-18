"""order/status.py — Order 生命周期状态机

CREATED → SUBMITTED → FILLED → CLOSED
异常: REJECTED / CANCELLED
"""

CREATED = "CREATED"
SUBMITTED = "SUBMITTED"
FILLED = "FILLED"
CLOSED = "CLOSED"
REJECTED = "REJECTED"
CANCELLED = "CANCELLED"

_ALL_STATES = {CREATED, SUBMITTED, FILLED, CLOSED, REJECTED, CANCELLED}

# 合法转移
_TRANSITIONS = {
    CREATED: {SUBMITTED, REJECTED, CANCELLED},
    SUBMITTED: {FILLED, REJECTED, CANCELLED},
    FILLED: {CLOSED},
    CLOSED: set(),
    REJECTED: set(),
    CANCELLED: set(),
}


def is_valid_transition(current: str, next_state: str) -> bool:
    """检查状态转移是否合法"""
    if current not in _TRANSITIONS:
        return False
    return next_state in _TRANSITIONS[current]


def terminal(state: str) -> bool:
    """是否终态"""
    return state in (CLOSED, REJECTED, CANCELLED)
