#!/usr/bin/env python3
"""
fact_source.py — Fact Truth Source Reader v1.0

memory/facts/ -> Fact Reader -> Consumer

唯一事实入口。只读取已确认事实，不推理/不生成/不提升置信度。
"""

import os
import json
from pathlib import Path
from typing import Optional

FACTS_DIR = Path(__file__).resolve().parent.parent / 'memory' / 'facts'

# —— 解析 ——

def _parse_jsonl(filepath: Path) -> list[dict]:
    """解析 JSONL 事实文件。"""
    facts = []
    with open(filepath, encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            obj.setdefault('fact_id', f"fact-{filepath.stem}-{line_no:04d}")
            obj.setdefault('source_event', '')
            obj.setdefault('confidence', 'medium')
            obj.setdefault('validator', 'system')
            obj.setdefault('created_at', '')
            obj.setdefault('domain', 'general')
            obj.setdefault('content', '')
            facts.append(obj)
    return facts


def _parse_md(filepath: Path) -> list[dict]:
    """解析 Markdown 事实文件。每个 ## 标题为一个事实。"""
    facts = []
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    current_title = None
    current_content = []
    event_counter = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('## '):
            if current_title:
                event_counter += 1
                facts.append({
                    'fact_id': f"fact-{filepath.stem}-{event_counter:04d}",
                    'content': ''.join(current_content).strip(),
                    'confidence': _default_confidence(),
                    'source_event': '',
                    'validator': 'manual',
                    'created_at': '',
                    'domain': _default_domain(),
                })
            current_title = stripped[3:]
            current_content = []
        elif current_title is not None:
            current_content.append(line)

    if current_title:
        event_counter += 1
        facts.append({
            'fact_id': f"fact-{filepath.stem}-{event_counter:04d}",
            'content': ''.join(current_content).strip(),
            'confidence': _infer_confidence(current_title, current_content),
            'source_event': '',
            'validator': 'manual',
            'created_at': '',
            'domain': _infer_domain(current_title, current_content),
        })

    return facts


def _default_confidence() -> str:
    """返回默认置信度。Reader 不做推断，由 promotion 层指定。

    Patch-007: 重命名以消除"infer"语义，原 _infer_confidence 保留为兼容别名。
    """
    return 'candidate'


def _default_domain() -> str:
    """返回默认领域。Reader 不做推断，由 promotion 层指定。

    Patch-007: 重命名以消除"infer"语义，原 _infer_domain 保留为兼容别名。
    """
    return 'general'


# 兼容别名：旧命名保持可调用
_infer_confidence = _default_confidence  # compatibility alias only — MUST NOT introduce inference logic
_infer_domain = _default_domain          # compatibility alias only — MUST NOT introduce inference logic


# —— Patch-006: Provenance Status ——

PROVENANCE_STATES = frozenset({'valid', 'manual', 'missing'})


def get_provenance_status(fact: dict) -> str:
    """
    返回事实的 provenance 状态。

    原则：不对历史数据进行静默降级，只标注 provenance 可观测性。

    Returns:
        'valid'   — source_event 存在
        'manual'  — 无 source_event 但有 manual_reason
        'missing' — 无 source_event 且无 manual_reason（历史遗留）
    """
    if fact.get('source_event'):
        return 'valid'
    if fact.get('manual_reason'):
        return 'manual'
    return 'missing'


# —— 读取 ——

def _scan_facts() -> list[dict]:
    """扫描 facts 目录，返回所有事实。"""
    if not FACTS_DIR.is_dir():
        return []

    all_facts = []
    for f in sorted(FACTS_DIR.iterdir()):
        if f.is_dir() or f.name.startswith('.'):
            continue
        if f.name.endswith('.jsonl'):
            all_facts.extend(_parse_jsonl(f))
        elif f.name.endswith('.md'):
            all_facts.extend(_parse_md(f))

    # Patch-006: 为每条事实标注 provenance_status
    for fact in all_facts:
        fact['provenance_status'] = get_provenance_status(fact)

    return all_facts


# —— 公共 API ——

def query_facts(
    domain: Optional[str] = None,
    confidence: Optional[str] = None,
    keyword: Optional[str] = None,
    source_event: Optional[str] = None,
    provenance: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """
    查询事实。

    Args:
        domain: 领域过滤 (governance / architecture / interaction / ...)
        confidence: 置信度过滤 (high / medium / low)
        keyword: 内容关键词
        source_event: 来源事件 ID
        provenance: provenance 过滤 (valid / manual / missing)
        limit: 返回条数上限

    Returns:
        事实列表
    """
    facts = _scan_facts()

    if domain:
        facts = [f for f in facts if f.get('domain') == domain.lower()]
    if confidence:
        facts = [f for f in facts if f.get('confidence') == confidence.lower()]
    if keyword:
        kw = keyword.lower()
        facts = [f for f in facts if kw in f.get('content', '').lower()]
    if source_event:
        facts = [f for f in facts if f.get('source_event') == source_event]
    if provenance:
        facts = [f for f in facts if f.get('provenance_status') == provenance.lower()]

    conf_order = {'high': 0, 'medium': 1, 'low': 2, 'candidate': 3, 'unknown': 99}
    facts.sort(key=lambda f: conf_order.get(f.get('confidence', 'low'), 3))

    if limit:
        facts = facts[:limit]

    return facts


def get_fact(fact_id: str) -> Optional[dict]:
    """按 ID 获取单个事实。"""
    facts = _scan_facts()
    for f in facts:
        if f.get('fact_id') == fact_id:
            return f
    return None


def get_source_event(fact_id: str) -> Optional[str]:
    """
    获取事实的来源事件 ID。

    Returns:
        事件 ID 字符串，或 None
    """
    fact = get_fact(fact_id)
    if fact:
        return fact.get('source_event')
    return None


def count_facts(**kwargs) -> int:
    """快速计数。"""
    return len(query_facts(**kwargs))


def get_provenance_stats() -> dict:
    """统计 provenance 状态分布。"""
    facts = _scan_facts()
    stats = {'valid': 0, 'manual': 0, 'missing': 0}
    for f in facts:
        status = f.get('provenance_status', 'missing')
        stats[status] = stats.get(status, 0) + 1
    return stats


# —— CLI ——

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fact Truth Source Reader')
    parser.add_argument('--domain', help='领域过滤')
    parser.add_argument('--confidence', help='置信度过滤 (high/medium/low)')
    parser.add_argument('--keyword', help='内容关键词')
    parser.add_argument('--source-event', help='来源事件 ID')
    parser.add_argument('--provenance', help='Provenance 过滤 (valid/manual/missing)')
    parser.add_argument('--limit', type=int, default=20, help='输出条数上限')
    parser.add_argument('--get', help='按 fact_id 查询')
    parser.add_argument('--source-of', help='获取事实的来源事件')
    parser.add_argument('--count', action='store_true', help='仅计数')
    parser.add_argument('--provenance-stats', action='store_true', help='Provenance 统计')
    args = parser.parse_args()

    if args.get:
        fact = get_fact(args.get)
        print(json.dumps(fact, ensure_ascii=False, indent=2) if fact else 'null')
    elif args.source_of:
        ev = get_source_event(args.source_of)
        print(json.dumps(ev, ensure_ascii=False) if ev else 'null')
    elif args.provenance_stats:
        print(json.dumps(get_provenance_stats(), ensure_ascii=False, indent=2))
    elif args.count:
        print(json.dumps({
            "total": count_facts(
                domain=args.domain,
                confidence=args.confidence,
                keyword=args.keyword,
                provenance=args.provenance,
            ),
        }, ensure_ascii=False))
    else:
        results = query_facts(
            domain=args.domain,
            confidence=args.confidence,
            keyword=args.keyword,
            source_event=args.source_event,
            provenance=args.provenance,
            limit=args.limit,
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))
