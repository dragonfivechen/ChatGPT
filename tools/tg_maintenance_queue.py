#!/usr/bin/env python3
"""
TG Maintenance Queue v1.0
=========================
读取 findings latest，按状态管道管理。

状态流转:
  observe → confirmed → patch_required → closed

文件:
  maintenance_queue.jsonl  — 当前所有任务
  maintenance_queue.log    — 变更历史
"""

import json
import os
import uuid
from datetime import datetime, timezone
from collections import defaultdict

# ── 路径 ────────────────────────────────────────────────────
FINDINGS_FILE = os.path.expanduser(
    "~/.openclaw/workspace/diagnostics/agent_behavior/telegram/findings/tg_findings_latest.jsonl"
)
MAINT_DIR = os.path.expanduser(
    "~/.openclaw/workspace/diagnostics/agent_behavior/telegram/maintenance"
)
QUEUE_FILE = os.path.join(MAINT_DIR, "maintenance_queue.jsonl")
LOG_FILE = os.path.join(MAINT_DIR, "maintenance_queue.log")
os.makedirs(MAINT_DIR, exist_ok=True)

# ── 现有队列加载 ────────────────────────────────────────────


def load_existing_queue():
    """加载已存在的维护队列。"""
    queue = {}
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        queue[item["id"]] = item
                    except json.JSONDecodeError:
                        continue
    return queue


def save_queue(queue):
    """保存维护队列。"""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        for item_id in sorted(queue.keys()):
            f.write(json.dumps(queue[item_id], ensure_ascii=False) + "\n")


def append_log(entry):
    """追加日志。"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 主流程 ───────────────────────────────────────────────────


def main():
    print("TG Maintenance Queue v1.0")
    print()

    # 加载现有队列
    queue = load_existing_queue()
    print(f"  现有队列: {len(queue)} 条")
    status_counts = defaultdict(int)
    for item in queue.values():
        status_counts[item["status"]] += 1
    if status_counts:
        print(f"  状态分布: {dict(status_counts)}")

    # 读取最新 findings
    if not os.path.exists(FINDINGS_FILE):
        print("  [ABORT] findings 不存在，先运行 tg_behavior_analyzer.py")
        return

    with open(FINDINGS_FILE, "r", encoding="utf-8") as f:
        findings = [json.loads(line) for line in f if line.strip()]

    print(f"  新 findings: {len(findings)} 条")

    # 新发现入队（去重）
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    new_count = 0
    for finding in findings:
        # 生成唯一 ID
        cat = finding["category"]
        session = finding["evidence"].get("session", "unknown")
        ts = finding["evidence"].get("timestamp", "")
        # 用 session+category+timestamp 做 dedup key
        dedup_key = (session, cat, ts)

        already_exists = False
        for item in queue.values():
            existing_key = (
                item.get("evidence", {}).get("session", ""),
                item["issue"],
                item.get("evidence", {}).get("timestamp", ""),
            )
            if existing_key == dedup_key:
                already_exists = True
                break

        if already_exists:
            continue

        item_id = f"TG-{date_str}-{str(uuid.uuid4())[:8]}"
        queue[item_id] = {
            "id": item_id,
            "source": "telegram",
            "issue": cat,
            "severity": finding.get("severity", "low"),
            "status": "observe",
            "evidence": finding["evidence"],
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        new_count += 1

    if new_count > 0:
        save_queue(queue)
        append_log(
            {
                "event": "new_items",
                "count": new_count,
                "timestamp": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        )
        print(f"  新入队: {new_count} 条")
    else:
        print("  无新条目")

    # 统计
    status_counts = defaultdict(int)
    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    for item in queue.values():
        status_counts[item["status"]] += 1
        severity_counts[item["severity"]] += 1
        category_counts[item["issue"]] += 1

    print(f"\n  队列状态:")
    for s in ["observe", "confirmed", "patch_required", "closed"]:
        c = status_counts.get(s, 0)
        print(f"    {s}: {c}")
    print(f"\n  类别分布:")
    for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {cnt}")
    print(f"\n  严重度分布: {dict(severity_counts)}")

    # 显示 observe 状态的待处理条目
    pending = [item for item in queue.values() if item["status"] == "observe"]
    if pending:
        print(f"\n  待处理 ({len(pending)}):")
        for item in sorted(pending, key=lambda x: -len(x["evidence"].get("text_snippet", "")))[:5]:
            snippet = item["evidence"].get("text_snippet", str(item["evidence"])[:80])
            print(f"    [{item['severity']}] {item['id']} | {item['issue']}")
            print(f"       {snippet[:120]}...")


if __name__ == "__main__":
    main()
