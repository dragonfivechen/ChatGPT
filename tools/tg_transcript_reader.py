#!/usr/bin/env python3
"""
TG Transcript Reader v1.0
=========================
从 OpenClaw session store 中提取 TG Agent (烬🔥) 对话记录，
输出到 diagnostics/agent_behavior/telegram/raw/。

只复制：timestamp, role, user_text
不复制：thinking trace, tool calls, tool results, system prompt, memory

用途：行为诊断层的数据采集，不属于 Memory Pipeline。
"""

import json
import os
import re
import glob
from datetime import datetime, timezone
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────
SESSION_DIR = os.path.expanduser("~/.openclaw/agents/main/sessions")
RAW_DIR = os.path.expanduser(
    "~/.openclaw/workspace/diagnostics/agent_behavior/telegram/raw"
)
os.makedirs(RAW_DIR, exist_ok=True)

# ── 辅助函数 ─────────────────────────────────────────────────

def extract_user_text(content_blocks):
    """从 content blocks 中提取用户实际消息（去掉 metadata 包裹）。"""
    texts = []
    for block in content_blocks:
        if block.get("type") != "text":
            continue
        text = block.get("text", "")
        if text.startswith("Conversation info (untrusted metadata)"):
            # 跳过 metadata 块，提取真正消息（在 ```json ... ``` 后面的内容）
            parts = text.split("```")
            if len(parts) >= 3:
                # parts[2] 是 metadata json 块之后的纯文本
                remaining = parts[2].strip()
                if remaining:
                    texts.append(remaining)
            continue
        if text.strip():
            texts.append(text.strip())
    return "\n".join(texts)


def extract_assistant_text(content_blocks):
    """从 assistant 的 content blocks 提取 text（跳过 thinking）。"""
    texts = []
    for block in content_blocks:
        if block.get("type") == "text":
            text = block.get("text", "").strip()
            if text:
                texts.append(text)
    return "\n".join(texts)


def is_telegram_session(lines):
    """判断 session 是否是 TG 对话。"""
    for line in lines[:10]:  # 只扫前 10 行
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "message":
            continue
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if "telegram" in text.lower():
                        return True
    return False


def normalize_role(role):
    """统一 role 值。"""
    mapping = {
        "user": "user",
        "assistant": "assistant",
        "toolResult": "tool_result",
        "tool": "tool_result",
    }
    return mapping.get(role, role)


def parse_session_file(filepath):
    """解析单个 session JSONL 文件，返回行为记录列表。"""
    filename = os.path.basename(filepath)
    records = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (IOError, UnicodeDecodeError) as e:
        print(f"  [SKIP] 读取失败: {e}")
        return records

    if not lines:
        return records

    # 快速过滤：不是 TG 会话则跳过
    if not is_telegram_session(lines):
        return records

    print(f"  [TG] 识别为 Telegram 会话: {filename} ({len(lines)} lines)")

    for line in lines:
        try:
            entry = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        if entry.get("type") != "message":
            continue

        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue

        role = normalize_role(msg.get("role", "unknown"))
        content_blocks = msg.get("content", [])
        if not isinstance(content_blocks, list):
            continue

        timestamp = entry.get("timestamp", "")

        if role == "user":
            text = extract_user_text(content_blocks)
            if not text:
                continue
        elif role == "assistant":
            text = extract_assistant_text(content_blocks)
            if not text:
                continue
        else:
            # tool_result 等跳过
            continue

        record = {
            "source": "telegram",
            "session_id": Path(filepath).stem.split(".")[0],  # session UUID
            "session_file": filename,
            "timestamp": timestamp,
            "role": role,
            "text": text,
            "text_len": len(text),
        }
        records.append(record)

    return records


# ── 主流程 ───────────────────────────────────────────────────

def main():
    print("TG Transcript Reader v1.0")
    print(f"  Session dir: {SESSION_DIR}")
    print(f"  Raw output:  {RAW_DIR}")
    print()

    # 扫描 session 文件
    session_files = sorted(glob.glob(os.path.join(SESSION_DIR, "*.jsonl")))
    # 过滤掉 checkpoint / trajectory 文件
    session_files = [
        f
        for f in session_files
        if not any(x in os.path.basename(f) for x in [".checkpoint.", ".trajectory."])
    ]
    print(f"  发现 {len(session_files)} 个 session 文件")
    print()

    all_records = []
    for i, fp in enumerate(session_files):
        records = parse_session_file(fp)
        all_records.extend(records)

    # 按时间排序
    all_records.sort(key=lambda r: r["timestamp"])

    print(f"\n  共提取 {len(all_records)} 条 TG 对话记录")

    # 写入 raw/
    if all_records:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        outfile = os.path.join(RAW_DIR, f"tg_transcript_{timestamp_str}.jsonl")
        with open(outfile, "w", encoding="utf-8") as f:
            for rec in all_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  输出: {outfile} ({os.path.getsize(outfile)} bytes)")

        # 同时保留最新快照
        latest_link = os.path.join(RAW_DIR, "tg_transcript_latest.jsonl")
        with open(latest_link, "w", encoding="utf-8") as f:
            for rec in all_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  Latest: {latest_link}")
    else:
        print("  (无 TG 对话记录)")

    # 输出摘要
    roles = {}
    for r in all_records:
        roles[r["role"]] = roles.get(r["role"], 0) + 1
    print(f"\n  摘要: {dict(roles)}")

    session_ids = set(r["session_id"] for r in all_records)
    print(f"  涉及 TG Session: {len(session_ids)} 个")

    # 统计来自各个 session 的记录数
    from collections import Counter
    session_counts = Counter(r["session_id"] for r in all_records)
    for sid, count in session_counts.most_common():
        print(f"    {sid}: {count} 条")


if __name__ == "__main__":
    main()
