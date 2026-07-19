#!/usr/bin/env python3
"""
Runtime Context Provider — 唯一事实源，不由模型推断。

生成 runtime/context.json，内容来自 OS clock，不由模型生成。
被 AGENTS.md／SOUL.md 引用的可信上下文入口。

用法:
  python3 runtime/context_provider.py              # 写入默认路径
  python3 runtime/context_provider.py --path /tmp  # 指定输出目录
  python3 runtime/context_provider.py --stdout     # 只输出不写文件
"""
import json, sys, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', str(Path.home() / '.openclaw' / 'workspace')))
CST = timezone(timedelta(hours=8), 'Asia/Shanghai')


def runtime_timestamp() -> str:
    """RTM-02: 单一时间真值源，取代分散的 datetime.now()
    
    Returns:
        ISO 格式时间戳字符串
    """
    return datetime.now(CST).strftime('%Y-%m-%d %H:%M')


def build_context(now: datetime | None = None) -> dict:
    """构建运行时上下文"""
    if now is None:
        now = datetime.now(CST)

    return {
        # === 数据分类（runtime observation, not fact truth） ===
        "data_type": "runtime_observation",
        "authority": "runtime",
        # === 时间事实（唯一来源：OS clock） ===
        "timestamp_iso": now.strftime('%Y-%m-%dT%H:%M:%S%z'),
        "timestamp_cst": now.strftime('%Y-%m-%d %H:%M CST'),
        "date": now.strftime('%Y-%m-%d'),
        "time": now.strftime('%H:%M'),
        "hour": now.hour,
        "minute": now.minute,
        "weekday": now.strftime('%A'),
        "weekday_cn": ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][now.weekday()],
        "timezone": "Asia/Shanghai (UTC+8)",
        "unix_ts": int(now.timestamp()),
    }


def write_context(ctx: dict, path: Path | None = None):
    """写入 context.json"""
    if path is None:
        path = WORKSPACE / 'runtime' / 'time_context.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--path', help='输出目录（默认 runtime/）')
    ap.add_argument('--stdout', action='store_true', help='只输出不写文件')
    args = ap.parse_args()

    ctx = build_context()

    if args.stdout:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
        return

    if args.path:
        p = Path(args.path) / 'context.json'
    else:
        p = None  # 默认

    write_context(ctx, p)

    if p:
        print(f"[context] 写入 {p}")
    print(f"[context] {ctx['timestamp_cst']} | {ctx['weekday_cn']}")


if __name__ == '__main__':
    main()
