#!/usr/bin/env python3
"""
memory_feedback_detect.py — 反馈信号检测器

通过 Event Reader (event_source) 获取事件，自动识别纠偏信号。
返回结构化的 Feedback Events。
不直接读取 memory/events/ 文件。

用法:
  python3 tools/memory_feedback_detect.py                    # 检测最近事件
  python3 tools/memory_feedback_detect.py --days 3           # 最近3天
  python3 tools/memory_feedback_detect.py --agent huo        # 指定身份
"""
import re, json, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from event_source import query_events

# 明确纠偏信号（高置信度）
EXPLICIT_CORRECTION = [
    '不要', '不应该', '不允许', '禁止',
    '为什么又', '我说的是', '你应该',
    '不需要这样', '不要再', '不需要问',
    '放你妈屁', '你真让我无语',
    '少废话', '不是这个意思',
    '直接', '别问', '按我的',
    '按用户要求', '按照我说的',
    '我让你', '我之前说过',
]

# 隐式纠偏信号（中置信度）
IMPLICIT_CORRECTION = [
    '正确的是', '正确方式', '正确处理',
    '这才是', '方向对了', '这个才对',
    '不是', '错了', '不对',
    '注意', '记住', '记住了吗',
]

# 核心原则信号（用户制定长期规则）
PRINCIPLE_SIGNAL = [
    '以后都', '长期', '永远', '规则',
    '准则', '纪律', '边界', '原则',
    '分离', '隔离', '应该',
    '记住', '记下',
]

# 噪声模式 — 架构文档/审计表/review checklist → 不产生反馈信号
NOISE_PATTERNS = [
    r'^\|',                                       # 所有表格行（管道符开头）
    r'^\*\*Bypass\s+\d+',                       # Bypass 条目
    r'^Bypass\s+\w+',
    r'^##\s+(架构|边界|验证|契约|合同|Phase|冻结|审计|审查|基线|检查)',  # 架构章节标题
    r'^(Layer|Phase|Step|Step\s+\d+[.:])(\s+\d+)?',
    r'^\*\*B\d+',                               # B1, B2 等架构标识
    r'^\*\*Phase\s+\d+',
    r'^\*\*状态[：:]',
    r'^\*\*(已确认|已归档|完成|暂停|关闭)',
    r'^核心结论',
    r'^文档位置',
    r'^\*\*\d+\.\s',                            # 编号标题
    r'^`[^`]+`\s+\u2192\s+`[^`]+`',            # 路径映射
    r'^\d+\s+tok',
    r'^session_count',
    r'^total_tokens',
]


def is_noise(line: str) -> bool:
    """判断是否为噪声行（架构文档/审计/指标）"""
    return any(re.match(p, line) for p in NOISE_PATTERNS)


def filter_architecture_sections(text: str) -> str:
    """过滤架构/审计段落，只保留交互反馈段落"""
    # 架构段落标题特征
    ARCH_SECTION_HEADERS = [
        'Phase', 'Contract', 'FROZEN', 'Frozen', '冻结',
        '产出清单', '已知代转缺口', '已知缺口',
        '冻结条件', '冻结确认', '冻结边界',
        'ARCHITECTURE.md 更新', '产出文件',
        '下一入口', '观察窗口',
        'Step 1:', 'Step 2:', 'Step 3:',
        '不变量', '不变量通过',
        '设计重点', '组合设计',
        '验证范围', '验证结果', '可冻结条件',
        '完整链', 'Phase 6', 'Phase 7',
        '许可链',
    ]
    
    sections = re.split(r'^##\s+', text, flags=re.MULTILINE)
    filtered = []
    for sec in sections:
        if not sec.strip():
            continue
        # 检查是否是架构段落
        header = sec.split('\n')[0].strip()
        is_arch = any(h in header for h in ARCH_SECTION_HEADERS)
        if not is_arch:
            # 非架构段落：保留
            filtered.append(sec)
    
    return '\n'.join(filtered)


def detect_feedback_events(text: str, source_path: str) -> list:
    """从事件文本中检测反馈信号"""
    feedbacks = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line_s = line.strip()
        if not line_s:
            continue
        
        # 噪声过滤：架构文档/审计表/指标数据不产生反馈
        if is_noise(line_s):
            continue
        
        # 检测信号类型
        has_explicit = any(w in line_s for w in EXPLICIT_CORRECTION)
        has_implicit = any(w in line_s for w in IMPLICIT_CORRECTION)
        has_principle = any(w in line_s for w in PRINCIPLE_SIGNAL)
        
        if not has_explicit and not has_implicit and not has_principle:
            continue
        
        # 确定反馈类型
        feedback_type = 'unknown'
        confidence = 0.0
        
        if has_explicit:
            feedback_type = 'correction_explicit'
            confidence = max(0.85, confidence)
        if has_implicit:
            feedback_type = 'correction_implicit'
            confidence = max(0.65, confidence)
        if has_principle:
            feedback_type = 'principle'
            confidence = max(0.75, confidence)
        
        feedbacks.append({
            'type': feedback_type,
            'confidence': round(confidence, 2),
            'line': i + 1,
            'text': line_s[:200],
            'source': source_path,
            'matched_signals': {
                'explicit': has_explicit,
                'implicit': has_implicit,
                'principle': has_principle,
            }
        })
    
    return feedbacks


def scan_events(agent_id: str = None, days: int = 7) -> list:
    """通过 Event Reader (event_source) 获取事件，检测反馈信号"""
    all_feedbacks = []

    # 通过 Event Reader 获取事件（只走 Reader，不直接读文件）
    events = query_events(agent=agent_id, days=days)

    # 按源文件分组（保持每个文件的上下文）
    file_events = defaultdict(list)
    for evt in events:
        src_file = evt['source'].split('#L')[0]
        file_events[src_file].append(evt)

    for filepath, evts in file_events.items():
        # 重建文本（组合事件内容）
        text = '\n'.join(e['content'] for e in evts)

        # 段落级别过滤：跳过架构/审计段落
        text = filter_architecture_sections(text)

        feedbacks = detect_feedback_events(text, filepath)
        agent = evts[0]['agent']
        date = evts[0]['event_id'].split('-')[1]  # evt-YYYY-MM-DD-NNN
        for fb in feedbacks:
            fb['agent'] = agent
            fb['date'] = date
        all_feedbacks.extend(feedbacks)

    return all_feedbacks, len(file_events)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='反馈信号检测器')
    parser.add_argument('--agent', default=None, help='身份')
    parser.add_argument('--days', type=int, default=7, help='扫描天数范围')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    args = parser.parse_args()
    
    feedbacks, count = scan_events(args.agent, args.days)
    
    if args.json:
        print(json.dumps(feedbacks, ensure_ascii=False, indent=2))
    else:
        explicit = [f for f in feedbacks if f['type'] == 'correction_explicit']
        implicit = [f for f in feedbacks if f['type'] == 'correction_implicit']
        principle = [f for f in feedbacks if f['type'] == 'principle']
        
        print(f"扫描 {count} 个事件文件，发现 {len(feedbacks)} 条反馈信号")
        print(f"  明确纠偏: {len(explicit)}")
        print(f"  隐式纠偏: {len(implicit)}")
        print(f"  核心原则: {len(principle)}")
        print()
        
        if explicit:
            print("=== 明确纠偏 ===")
            for fb in explicit[:10]:
                print(f"  [{fb['agent']}/{fb['date']}] conf={fb['confidence']}")
                print(f"    {fb['text'][:80]}")


