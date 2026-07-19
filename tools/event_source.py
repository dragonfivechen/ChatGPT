#!/usr/bin/env python3
"""
event_source.py — Event Truth Source Reader v1.0

Event Storage -> Event Reader -> Consumer

唯一事件事实入口。禁止消费者直接读取 memory/events/ 文件。
此模块只提供查询/过滤/回放，不推理、不摘要、不写入。
"""

import os
import re
import json
import glob
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

EVENTS_BASE = Path(__file__).resolve().parent.parent / 'memory' / 'events'

# —— 事件解析 ——

def _parse_md_events(filepath: Path, agent: str) -> list[dict]:
    """解析 Markdown 事件文件。每个 ## 标题为一个事件块。"""
    events = []
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    current_title = None
    current_content = []
    current_line = 0
    event_counter = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        # 检测 ## 标题（事件起始）
        if stripped.startswith('## '):
            # 保存上一个事件
            if current_title:
                event_counter += 1
                events.append(_build_md_event(
                    filepath, agent, current_title, current_content,
                    current_line, event_counter
                ))
            current_title = stripped[3:]
            current_content = []
            current_line = i + 1
        elif current_title is not None:
            current_content.append(line)

    # 最后的事件块
    if current_title:
        event_counter += 1
        events.append(_build_md_event(
            filepath, agent, current_title, current_content,
            current_line, event_counter
        ))

    return events


def _build_md_event(filepath, agent, title, content_lines, start_line, counter):
    """从 Markdown 事件块构建统一事件结构。"""
    content = ''.join(content_lines).strip()
    # 从标题中提取时间戳：格式 "## 标题 (HH:MM~)"
    ts_match = re.search(r'\((\d{2}:\d{2})', title)
    ts_fallback = _extract_date_from_filename(filepath.stem)

    if ts_match:
        timestamp = f"{ts_fallback.split('T')[0]}T{ts_match.group(1)}:00+08:00"
    else:
        timestamp = ts_fallback

    # 从标题内容判断类别
    category = _infer_category(title, content)

    return {
        "event_id": f"evt-{filepath.stem}-{counter:03d}",
        "timestamp": timestamp,
        "agent": agent,
        "category": category,
        "content": content,
        "source": f"{filepath}#L{start_line}",
    }


def _parse_jsonl_events(filepath: Path, agent: str, include_payload: bool = False) -> list[dict]:
    """解析 JSONL 事件文件。每行一个 JSON 对象。"""
    events = []
    with open(filepath, encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_id = obj.get('event_id', f"evt-{filepath.stem}-{line_no:04d}")
            timestamp = obj.get('timestamp', obj.get('draw_date', obj.get('created_at', '')))
            category = obj.get('type', '').lower() if obj.get('type') else _infer_json_category(obj)
            content = _summarize_json(obj)

            event = {
                "event_id": event_id,
                "timestamp": timestamp,
                "agent": agent,
                "category": category,
                "content": content,
                "source": f"{filepath}#L{line_no}",
            }

            # --payload 模式：保留原始载荷
            if include_payload:
                event["payload"] = obj.get("payload", obj)

            events.append(event)

    return events


def _summarize_json(obj: dict) -> str:
    """将 JSON 事件转为人类可读摘要。"""
    t = obj.get('type', '')
    game = obj.get('game', obj.get('name', ''))
    issue = obj.get('issue', '')
    payload = obj.get('payload', {})

    if 'front' in payload and 'back' in payload:
        return f"[{game}] {issue}: 前区{payload['front']} 后区{payload['back']}"
    if 'red' in payload and 'blue' in payload:
        return f"[{game}] {issue}: 红球{payload['red']} 蓝球{payload['blue']}"
    if t == 'TASK_COMPLETE':
        return f"[{game}] {issue}: {obj.get('draw_date', '')}"
    if 'result' in obj:
        return json.dumps(obj.get('result', ''), ensure_ascii=False)
    return json.dumps(obj, ensure_ascii=False, default=str)


def _infer_category(title: str, content: str) -> str:
    """从标题和内容推断事件类别。"""
    category_map = [
        (['架构', '审计', '契约', '边界', '治理', 'Freeze', 'Contract'], 'architecture'),
        (['规则', '准则', '原则', '标准化', '规范'], 'governance'),
        (['纠偏', '纠正', '修正', '正确'], 'correction'),
        (['完成', 'Complete', 'DONE', 'FROZEN'], 'completion'),
        (['彩票', 'lottery', '日报', '开奖', '预测'], 'lottery'),
        (['验证', 'Validation', 'verification', '验收'], 'validation'),
        (['BUG', 'bug', '问题', '故障', '异常', '错误'], 'bug'),
        (['部署', 'deploy', '发布', '上线'], 'deployment'),
    ]
    combined = (title + ' ' + content).lower()
    for keywords, cat in category_map:
        if any(k.lower() in combined for k in keywords):
            return cat
    return 'general'


def _infer_json_category(obj: dict) -> str:
    """从 JSON 事件的 schema 推断类别。"""
    t = obj.get('type', '')
    if 'DRAW' in t:
        return 'draw'
    if 'PREDICTION' in t:
        return 'prediction'
    if 'CHECK' in t:
        return 'validation'
    if 'TASK' in t:
        return 'task'
    return 'data'


def _extract_date_from_filename(stem: str) -> str:
    """从文件名提取 ISO 时间戳。例如 '2026-07-20' → '2026-07-20T00:00:00+08:00'。"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', stem)
    if match:
        return f"{match.group(1)}T00:00:00+08:00"
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


# —— 扫描 ——

def _scan_events(agent: Optional[str] = None, days: Optional[int] = None, include_payload: bool = False) -> list[dict]:
    """扫描 events 目录，返回所有事件列表。"""
    all_events = []
    if agent:
        targets = [EVENTS_BASE / agent]
    else:
        targets = sorted([d for d in EVENTS_BASE.iterdir() if d.is_dir()])

    now = datetime.now(timezone(timedelta(hours=8)))

    for target in targets:
        if not target.is_dir():
            continue
        agent_name = target.name

        for f in sorted(target.iterdir()):
            if f.is_dir():
                continue
            if not f.name.endswith(('.md', '.jsonl')):
                continue

            # 日期过滤
            if days is not None:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', f.stem)
                if date_match:
                    try:
                        file_dt = datetime.strptime(date_match.group(1), '%Y-%m-%d').replace(
                            tzinfo=timezone(timedelta(hours=8)))
                        if (now - file_dt) > timedelta(days=days):
                            continue
                    except ValueError:
                        pass

            if f.name.endswith('.md'):
                all_events.extend(_parse_md_events(f, agent_name))
            elif f.name.endswith('.jsonl'):
                all_events.extend(_parse_jsonl_events(f, agent_name, include_payload=include_payload))

    return all_events


# —— 公共 API ——

def query_events(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    agent: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: Optional[int] = None,
    days: Optional[int] = None,
    payload: bool = False,
) -> list[dict]:
    """
    查询事件。

    Args:
        start_time: ISO-8601 起始时间
        end_time: ISO-8601 截止时间
        agent: 来源身份/域 ('huo', 'jin', 'lottery', ...)
        category: 事件类别过滤
        keyword: 内容关键词
        limit: 返回条数上限
        days: 限制扫描天数（None = 不限）

    Returns:
        事件列表，按时间戳倒序排列
    """
    events = _scan_events(agent=agent, days=days, include_payload=payload)

    # 时间过滤
    if start_time:
        try:
            st = datetime.fromisoformat(start_time)
            events = [e for e in events if e['timestamp'] and datetime.fromisoformat(e['timestamp']) >= st]
        except (ValueError, TypeError):
            pass

    if end_time:
        try:
            et = datetime.fromisoformat(end_time)
            events = [e for e in events if e['timestamp'] and datetime.fromisoformat(e['timestamp']) <= et]
        except (ValueError, TypeError):
            pass

    # 类别过滤
    if category:
        cat_lower = category.lower()
        events = [e for e in events if e['category'] == cat_lower]

    if keyword:
        kw_lower = keyword.lower()
        events = [e for e in events if kw_lower in e['content'].lower() or kw_lower in e['event_id'].lower()]

    # 按时间倒序排序
    def _sort_key(e):
        try:
            return datetime.fromisoformat(e['timestamp'])
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=timezone(timedelta(hours=8)))
    events.sort(key=_sort_key, reverse=True)

    if limit and limit > 0:
        events = events[:limit]

    return events


def count_events(**kwargs) -> int:
    """快速计数，不返回详细信息。"""
    return len(_scan_events(agent=kwargs.get('agent'), days=kwargs.get('days')))


# —— CLI ——

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Event Truth Source Reader')
    parser.add_argument('--agent', help='过滤身份/域')
    parser.add_argument('--category', help='过滤类别')
    parser.add_argument('--keyword', help='内容关键词')
    parser.add_argument('--days', type=int, default=7, help='扫描天数（默认7天）')
    parser.add_argument('--start', help='起始时间 ISO-8601')
    parser.add_argument('--end', help='截止时间 ISO-8601')
    parser.add_argument('--limit', type=int, default=20, help='输出条数上限（默认20，0=不限）')
    parser.add_argument('--payload', action='store_true', help='保留原始载荷（JSONL事件）')
    parser.add_argument('--count', action='store_true', help='仅计数')
    parser.add_argument('--stats', action='store_true', help='统计各域事件数')

    args = parser.parse_args()

    if args.stats:
        print("=== Event Truth Source 统计 ===")
        for d in sorted(EVENTS_BASE.iterdir()):
            if not d.is_dir():
                continue
            total = len(_scan_events(agent=d.name, days=args.days))
            print(f"  {d.name}: {total} events")
        print(f"  (days={args.days})")
        exit(0)

    if args.count:
        total = count_events(agent=args.agent, days=args.days)
        print(json.dumps({"total_events": total, "days": args.days}, ensure_ascii=False))
        exit(0)

    limit = None if args.limit == 0 else args.limit
    results = query_events(
        start_time=args.start,
        end_time=args.end,
        agent=args.agent,
        category=args.category,
        keyword=args.keyword,
        limit=limit,
        days=args.days,
        payload=args.payload,
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))
