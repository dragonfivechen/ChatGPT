"""replay/loader.py — 从 events.jsonl 加载事件

支持加载单个文件或多个文件中的事件。
"""

import json
import os


def load_events(filepath: str) -> list[dict]:
    """从单个 jsonl 文件加载所有事件"""
    events = []
    if not os.path.exists(filepath):
        return events
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def load_events_from_dir(dirpath: str, patterns: list[str] = None) -> list[dict]:
    """从目录加载多个 jsonl 文件的事件"""
    all_events = []
    if patterns is None:
        patterns = ["*.jsonl"]
    if not os.path.isdir(dirpath):
        return all_events

    for fname in os.listdir(dirpath):
        if not fname.endswith(".jsonl"):
            continue
        if patterns and not any(
            fname.startswith(p.rstrip("*")) for p in patterns
        ):
            continue
        fpath = os.path.join(dirpath, fname)
        all_events.extend(load_events(fpath))

    return all_events
