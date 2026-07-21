#!/usr/bin/env python3
"""
Futures-Sim v0.1 — replay/converter.py（历史数据→FUTURES_QUOTE 转换器）

职责:
  1. 将 loader 输出的原始行 dict 转换为 FUTURES_QUOTE 事件
  2. 与 collector.py 输出的 Schema 完全一致
  3. 增加 source 字段区分数据源
  4. 自动填充 pre_close（基于每个品种首笔交易）

输入: CSV 原始行（含 datetime, symbol, open, high, low, close, volume, oi）
输出: FUTURES_QUOTE 事件（与 collector.py make_quote() 相同 Schema）

冻结约束:
  - 输出必须与现有 GET_QUOTE 事件格式完全兼容
  - 不修改 collector.py / simulator.py / account.py
  - 不依赖任何 trading 模块
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional


def convert_to_quotes(rows: list[dict],
                      source: str = "historical",
                      tz_offset: int = 8) -> list[dict]:
    """将 loader 原始行列表转换为 FUTURES_QUOTE 事件列表

    参数:
      rows:      loader.load_historical() 返回的行列表
      source:    "historical" / "replay"
      tz_offset: 时区偏移 (北京时间 +8)

    返回: FUTURES_QUOTE 事件 dict 列表
    """
    if not rows:
        return []

    quotes = []
    last_prices: dict[str, float] = {}       # 品种 → 上一个 close（用于 pre_close）

    for row in rows:
        symbol = row["symbol"]

        # pre_close 逻辑: 当日第一笔用昨收，之后用上一笔的 close
        pre_close = last_prices.get(symbol, row["close"])

        # 时间戳处理
        dt_raw = row.get("datetime", "")
        ts = _normalize_ts(dt_raw, tz_offset)

        quote = {
            "event_type": "FUTURES_QUOTE",
            "ts": ts,
            "symbol": symbol,
            "price": round(row["close"], 2),
            "open": round(row["open"], 2),
            "high": round(row["high"], 2),
            "low": round(row["low"], 2),
            "pre_close": round(pre_close, 2),
            "volume": row["volume"],
            "oi": row["oi"],
            "source": source,  # 新：标记数据源
        }

        quotes.append(quote)
        last_prices[symbol] = row["close"]

    return quotes


def _normalize_ts(dt_str: str, tz_offset: int = 8) -> str:
    """将 datetime 字符串统一为 ISO-8601 +08:00 格式"""
    if not dt_str:
        return datetime.now(timezone(timedelta(hours=tz_offset))).strftime(
            "%Y-%m-%dT%H:%M:%S+08:00")

    # 已含时区信息 → 直接返回
    if "+" in dt_str or "Z" in dt_str or "z" in dt_str:
        return dt_str

    # 含 T 分隔 → ISO-8601 无时区
    if "T" in dt_str:
        return f"{dt_str}+08:00"

    # 标准空格分隔 "2026-01-06 09:00:00"
    dt_str = dt_str.strip()
    if " " in dt_str and "-" in dt_str:
        ts_base = dt_str.replace(" ", "T")
        # ts_base 已包含秒: 2026-01-06T09:00:00 → 直接加时区
        return f"{ts_base}+08:00"

    # fallback
    return f"{dt_str}+08:00"


def write_replay_events(quotes: list[dict],
                        output_path: str,
                        append: bool = False) -> str:
    """将转换后的事件写入 JSONL 文件

    参数:
      quotes:    convert_to_quotes() 返回值
      output_path: 输出路径（如 replay_events.jsonl）
      append:   是否追加（默认覆盖）

    返回: 写入条数
    """
    mode = "a" if append else "w"
    count = 0
    with open(output_path, mode, encoding="utf-8") as f:
        for q in quotes:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
            count += 1

    return count


def merge_events(events: list[dict], output_path: str) -> int:
    """合并事件到已有的 events.jsonl（按时间排序插入）"""
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]
    else:
        existing = []

    all_events = existing + events
    all_events.sort(key=lambda e: e.get("ts", ""))

    with open(output_path, "w", encoding="utf-8") as f:
        for evt in all_events:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")

    return len(all_events)


if __name__ == "__main__":
    import sys
    from loader import load_historical

    if len(sys.argv) < 2:
        print("用法: python3 converter.py <csv_path> [output_path]")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "replay_events.jsonl"

    rows = load_historical(csv_path)
    if not rows:
        print("[converter] ❌ 无数据可转换")
        sys.exit(1)

    quotes = convert_to_quotes(rows)
    n = write_replay_events(quotes, output_path)
    print(f"[converter] ✅ {n} 条 FUTURES_QUOTE 已写入 {output_path}")

    # 输出样本验证
    print(f"\n示例事件:")
    for q in quotes[:3]:
        print(json.dumps(q, ensure_ascii=False, indent=2))
    if len(quotes) > 3:
        print(f"  ... 共 {len(quotes)} 条")
