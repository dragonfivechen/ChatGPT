#!/usr/bin/env python3
"""
Context Validator — 校验输出文本中的时间表达一致性。

职责：发现歧义，标记事实矛盾，不自动纠正。
不替用户决定"明天"是否应为"今天"。

用法:
  python3 runtime/context_validator.py "明天04:30收到报告"
  python3 runtime/context_validator.py --now "2026-07-20T00:13:00+08:00" --text "明天04:30"
  cat output.txt | python3 runtime/context_validator.py
"""
import re, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
CST = timezone(timedelta(hours=8), 'Asia/Shanghai')


def load_context(path: Optional[Path] = None) -> dict:
    """加载 runtime/time_context.json"""
    if path is None:
        path = WORKSPACE / 'runtime' / 'time_context.json'
    if path.exists():
        return json.loads(path.read_text())
    return {}


def extract_temporal_expressions(text: str) -> list[dict]:
    """提取文本中的时间表达"""
    found = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        patterns = [
            (r'(今天|明天|后天|大后天)\s*\d{1,2}[:：.]\d{2}', '精确时间'),
            (r'(今天|明天|后天|大后天)', '日期'),
            (r'\d{1,2}[:：.]\d{2}\s*[分时]?', '时钟时间'),
            (r'(凌晨|早上|上午|中午|下午|傍晚|晚上|半夜|今晚|明早|明晚)\s*\d{1,2}[:：.]?\d{0,2}', '时段时间'),
            (r'(\d+)\s*(小时|分钟|秒)后', '相对时间'),
        ]
        for pat, label in patterns:
            for m in re.finditer(pat, line):
                found.append({
                    'line': i + 1,
                    'text': m.group(0),
                    'type': label,
                    'full_line': line.strip()[:80],
                })
    return found


def validate_text(text: str, now: Optional[datetime] = None) -> dict:
    """
    校验文本中的时间表达。

    - Resolver: 将相对表达解析为绝对时间（字面语义，不做意图判断）
    - Validator: 仅标记可能矛盾的表达（不自动纠正，不做出经验推断）
    - 任何涉及模型输出语义的修正应由模型自身完成
    """
    if now is None:
        now = datetime.now(CST)

    context = load_context()
    context_time_str = context.get('timestamp_cst', '')

    expressions = extract_temporal_expressions(text)
    ambiguities = []

    sys.path.insert(0, str(WORKSPACE / 'runtime'))
    from temporal_resolver import parse_time_expr

    for expr in expressions:
        resolved = parse_time_expr(expr['text'], now)
        if resolved:
            expr['resolved'] = resolved['resolved_cst']
            expr['relative'] = resolved['relative']
            expr['delta_seconds'] = resolved['delta_seconds']

            # 标记：跨天边界的相对表达在当前时间段可能产生歧义
            # 仅标记事实，不下结论，不自动改写
            if '明天' in expr['text'] and now.hour < 6:
                ambiguities.append({
                    'type': 'temporal_ambiguity',
                    'message': (
                        f"当前 {now.hour:02d}:{now.minute:02d}，凌晨时段使用 '{expr['text']}' "
                        f"(解析为 {resolved['resolved_cst']}，{resolved['relative']})。"
                        f"注意：若事件发生在今日凌晨/上午，'明天' 与 '今天' 可能产生歧义。"
                    ),
                    'expression': expr,
                })
        else:
            ambiguities.append({
                'type': 'unresolved',
                'message': f"无法解析时间表达: '{expr['text']}' (第{expr['line']}行)",
                'expression': expr,
            })

    return {
        'context_time': context_time_str,
        'now': now.strftime('%Y-%m-%d %H:%M CST'),
        'expressions_found': len(expressions),
        'expressions': expressions,
        'ambiguities': ambiguities,
        'ambiguity_count': len(ambiguities),
        'pass': True,  # Validator 不做"通过/拒绝"判定，标记即完成
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('text', nargs='?', help='要校验的文本')
    ap.add_argument('--now', help='基准时间 ISO 8601（默认当前）')
    ap.add_argument('--json', action='store_true', help='JSON 输出')
    args = ap.parse_args()

    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        ap.print_help()
        return

    now = None
    if args.now:
        now = datetime.fromisoformat(args.now)
    else:
        now = datetime.now(CST)

    result = validate_text(text, now)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        ctx = result['context_time'] or '未加载'
        print(f"[validator] 上下文时间: {ctx}")
        print(f"[validator] 当前时间:   {result['now']}")
        print(f"[validator] 发现 {result['expressions_found']} 个时间表达")
        if result['ambiguities']:
            print(f"[validator] ⚠️ {result['ambiguity_count']} 个歧义标记:")
            for a in result['ambiguities']:
                print(f"  {a['message']}")
        else:
            print("[validator] 无歧义标记")
        for expr in result['expressions'][:5]:
            resolved = expr.get('resolved', '-')
            print(f"  · {expr['text']} → {resolved}")
        if len(result['expressions']) > 5:
            print(f"  ... 还有 {len(result['expressions']) - 5} 个")


if __name__ == '__main__':
    main()
