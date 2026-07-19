#!/usr/bin/env python3
"""
Temporal Resolver — 解析自然语言相对时间表达为绝对时间。

输入：自然语言时间表达
输出：ISO 8601 绝对时间

用法:
  python3 runtime/temporal_resolver.py "明天04:30"
  python3 runtime/temporal_resolver.py "后天上午10点"
  python3 runtime/temporal_resolver.py --now "2026-07-20T00:13:00+08:00" "明天04:30"
  python3 runtime/temporal_resolver.py --list  # 列出支持的模式
"""
import re, json, sys
from datetime import datetime, timedelta, timezone
from typing import Optional

CST = timezone(timedelta(hours=8), 'Asia/Shanghai')

# 中文数字映射
CN_DIGITS = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10,
}

# 时段 → 时映射
PERIOD_HOUR = {
    '凌晨': (0, 5), '早上': (5, 8), '上午': (8, 12),
    '中午': (11, 13), '下午': (12, 18), '傍晚': (17, 19),
    '晚上': (18, 24), '半夜': (22, 24),
}


def parse_cn_number(s: str) -> Optional[int]:
    """解析中文数字"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)

    # 纯中文数字
    try:
        if s in CN_DIGITS:
            return CN_DIGITS[s]
        # 十几、二十几、一百
        if '十' in s:
            parts = s.split('十')
            left = CN_DIGITS.get(parts[0], 1) if parts[0] else 1
            right = CN_DIGITS.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return left * 10 + right
    except (KeyError, ValueError):
        pass
    return None


def parse_time_expr(s: str, now: datetime) -> Optional[dict]:
    """
    解析相对时间表达，返回绝对时间信息。
    返回: {"iso": str, "cst": str, "relative": str} 或 None
    """
    s = s.strip()
    base = now.replace(second=0, microsecond=0)
    result = {}

    # 模式1: 今天/明天/后天/大后天/昨天/前天 ± HH:MM
    m = re.match(r'(今天|明天|后天|大后天|昨晚|今晚|昨天|前天)\s*(\d{1,2})[：:.]?(\d{2})?', s)
    if m:
        day_offset = {'今天': 0, '明天': 1, '后天': 2, '大后天': 3,
                       '昨晚': -1, '今晚': 0, '昨天': -1, '前天': -2}[m.group(1)]
        h, mi = int(m.group(2)), int(m.group(3) or '0')
        # 如果是"今晚"，默认为 20:00
        if m.group(1) == '今晚' and not m.group(3):
            h, mi = 20, 0
        # 昨晚 → 取前一天 20:00
        if m.group(1) == '昨晚' and not m.group(3):
            h, mi = 20, 0
        resolved = base + timedelta(days=day_offset)
        resolved = resolved.replace(hour=h % 24, minute=min(min(mi, 59), 59))
        if h >= 24:
            resolved += timedelta(days=1)
            resolved = resolved.replace(hour=h % 24)
        return _fmt_result(resolved, s, now)

    # 模式2: 上午/下午/晚上/凌晨 + HH:MM
    m = re.match(r'(凌晨|早上|上午|中午|下午|傍晚|晚上|半夜)\s*(\d{1,2})[：:.]?(\d{2})?', s)
    if m:
        period = m.group(1)
        h = int(m.group(2))
        mi = int(m.group(3) or '0')
        lo, hi = PERIOD_HOUR.get(period, (0, 24))
        # 如果小时不在时段内但接近，自动调整
        if h < lo:
            h = lo
        resolved = base.replace(hour=min(h, 23), minute=min(mi, 59))
        return _fmt_result(resolved, s, now)

    # 模式3: N小时后 / N分钟后
    m = re.match(r'(\d+)\s*(小时|分钟|分|秒)后', s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit in ('分钟', '分'):
            resolved = base + timedelta(minutes=n)
        elif unit == '小时':
            resolved = base + timedelta(hours=n)
        else:
            resolved = base + timedelta(seconds=n)
        return _fmt_result(resolved, s, now)

    # 模式4: 纯HH:MM（今天）
    m = re.match(r'^(\d{1,2})[：:.](\d{2})$', s)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            resolved = base.replace(hour=h, minute=mi)
            # 如果时间已过，推到明天
            if resolved <= now:
                resolved += timedelta(days=1)
            return _fmt_result(resolved, s, now)

    # 模式5: 纯日期表达
    m = re.match(r'(今天|明天|后天|大后天|昨天|前天|大前天)$', s)
    if m:
        day_offset = {'今天': 0, '明天': 1, '后天': 2, '大后天': 3,
                       '昨天': -1, '前天': -2, '大前天': -3}[m.group(1)]
        resolved = (base + timedelta(days=day_offset)).replace(hour=9, minute=0)
        return _fmt_result(resolved, s, now)

    return None


def _fmt_result(resolved: datetime, original: str, now: datetime) -> dict:
    """格式化解析结果"""
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=CST)
    else:
        resolved = resolved.astimezone(CST)

    delta = resolved - now
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if days > 0:
        relative = f"{days}天后"
    elif hours > 0:
        relative = f"{hours}小时{minutes}分钟后" if minutes else f"{hours}小时后"
    elif minutes > 0:
        relative = f"{minutes}分钟后"
    else:
        relative = "现在"

    return {
        "original": original,
        "resolved_iso": resolved.strftime('%Y-%m-%dT%H:%M:%S%z'),
        "resolved_cst": resolved.strftime('%Y-%m-%d %H:%M CST'),
        "weekday": resolved.strftime('%A'),
        "relative": relative,
        "delta_seconds": int(delta.total_seconds()),
        "timestamp_unix": int(resolved.timestamp()),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('expr', nargs='?', help='时间表达，如 "明天04:30"')
    ap.add_argument('--now', help='基准时间 ISO 8601（默认当前时间）')
    ap.add_argument('--json', action='store_true', help='JSON 输出')
    ap.add_argument('--list', action='store_true', help='列出支持的模式')
    args = ap.parse_args()

    if args.list:
        patterns = [
            "今天 14:30",
            "明天 04:30",
            "后天上午10点",
            "大后天 09:15",
            "3小时后",
            "45分钟后",
            "凌晨 3:00",
            "22:30",
            "今晚",
            "昨天 14:30",
            "前天",
            "明天",
        ]
        print("支持的时间模式示例：")
        for p in patterns:
            print(f"  {p}")
        return

    if not args.expr:
        ap.print_help()
        return

    now = None
    if args.now:
        now = datetime.fromisoformat(args.now)
    else:
        now = datetime.now(CST)

    result = parse_time_expr(args.expr, now)
    if result is None:
        print(f"[resolver] 无法解析: {args.expr}")
        sys.exit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['original']} → {result['resolved_cst']} ({result['relative']})")


if __name__ == '__main__':
    main()
