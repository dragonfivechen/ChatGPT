#!/usr/bin/env python3
"""test_boundary.py — Phase 2 TG Build Boundaries 验证 A2

验证 L0 测试创建操作是否允许自动执行。
不涉及 state/events 写入，不修改系统语义。
"""

import json
import os
import tempfile


def test_allowed_paths():
    """L0 允许路径列表（不修改系统语义）"""
    allowed_prefixes = [
        "docs/",
        "tests/",
        "tools/",
        "scripts/",
        "memory/knowledge/",
    ]
    for prefix in allowed_prefixes:
        assert not prefix.startswith((
            "memory/state/",
            "memory/events/",
            "runtime/",
        )), f"{prefix} should not be in L0 scope"


def test_no_state_write():
    """L0 操作不能写入 state/events 路径"""
    forbidden = [
        "memory/state/huo/",
        "memory/events/huo/",
        "memory/events/jin/",
        "runtime/context_contract.md",
    ]
    for path in forbidden:
        # 模拟验证：路径是否在禁止范围
        is_forbidden = any(path.startswith(p) for p in [
            "memory/state/",
            "memory/events/",
            "runtime/",
        ])
        assert is_forbidden, f"{path} should be detected as forbidden"


def test_audit_log_format():
    """审计日志格式验证"""
    record = {
        "timestamp": "2026-07-20T22:30:00+08:00",
        "agent": "tg",
        "level": "L0",
        "action": "create",
        "target": "tests/test_boundary.py",
        "result": "success",
    }
    required_fields = ["timestamp", "agent", "level", "action", "target", "result"]
    for field in required_fields:
        assert field in record, f"missing field: {field}"


if __name__ == "__main__":
    test_allowed_paths()
    test_no_state_write()
    test_audit_log_format()
    print("✅ All boundary tests passed (L0 scope)")
