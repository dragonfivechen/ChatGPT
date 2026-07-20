#!/usr/bin/env python3
"""check_boundary.py — TG Build Boundaries Phase 2 验证 A3

检查目标路径是否在 L0/L1/L2 允许范围内。
不修改任何系统状态。
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta

# 时区
CST = timezone(timedelta(hours=8))

# L2 禁止路径前缀（硬禁止）
FORBIDDEN_PREFIXES = [
    "memory/state/",
    "memory/events/",
    # runtime 核心文件（粗粒度检查）
]

# L0 允许路径前缀
L0_PREFIXES = [
    "docs/",
    "tests/",
    "tools/",
    "scripts/",
    "memory/knowledge/",
]

# L1 允许路径前缀（受控）
L1_PREFIXES = [
    # 独立项目目录（需 change-plan + change-report）
]


def classify_path(path: str) -> tuple:
    """
    返回 (level, allowed, reason)
    level: "L0" | "L1" | "L2"
    allowed: bool
    """
    # 检查禁止区
    for prefix in FORBIDDEN_PREFIXES:
        if path.startswith(prefix):
            return ("L2", False, f"禁止路径前缀: {prefix}")

    # 检查 L0
    for prefix in L0_PREFIXES:
        if path.startswith(prefix):
            return ("L0", True, f"L0 自动执行: {prefix}")

    # 检查 L1
    for prefix in L1_PREFIXES:
        if path.startswith(prefix):
            return ("L1", True, f"L1 受控执行: {prefix}")

    return ("UNKNOWN", False, "未分类路径，需升级判断")


def build_audit_record(path: str, action: str, level: str, result: str) -> dict:
    """生成审计记录"""
    return {
        "timestamp": datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "agent": "tg",
        "level": level,
        "action": action,
        "target": path,
        "result": result,
    }


def main():
    test_paths = [
        ("docs/new-guide.md", "create"),
        ("tests/test_x.py", "create"),
        ("tools/analyzer.py", "create"),
        ("memory/knowledge/some-topic.md", "create"),
        ("memory/state/huo/ARCHITECTURE.md", "modify"),
        ("memory/events/huo/2026-07-20.md", "modify"),
        ("runtime/time_context.json", "modify"),
    ]

    all_pass = True
    for path, action in test_paths:
        level, allowed, reason = classify_path(path)
        record = build_audit_record(path, action, level, "allowed" if allowed else "denied")
        status = "✅" if allowed else "❌"
        print(f"{status} [{level}] {action} {path} — {reason}")
        if not allowed:
            all_pass = False

    print(f"\n边界检查示例完成，共 {len(test_paths)} 条路径")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
