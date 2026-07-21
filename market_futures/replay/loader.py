#!/usr/bin/env python3
"""
Futures-Sim v0.1 — replay/loader.py（历史数据加载器）

职责:
  1. 加载 CSV 格式的历史行情数据
  2. 验证列结构和数据类型
  3. 支持单品种/多品种过滤
  4. 返回统一的行 dict 列表供 converter.py 消费

输入 CSV 规范:
  标准分钟K线格式:
    datetime,symbol,open,high,low,close,volume,oi
  示例:
    2026-01-06 09:00:00,RB,3300,3310,3295,3305,12500,100000

字段类型:
  datetime:   str "%Y-%m-%d %H:%M:%S" 或 ISO-8601
  symbol:     str (RB / CU / AL / ... )
  open/high/low/close: float
  volume:     int
  oi:         int (open interest)

冻结约束:
  - 不修改原始 CSV 文件
  - 不缓存高级指标
  - 不接入交易所接口
"""

import csv
import os
import sys
from typing import Optional

REQUIRED_COLUMNS = ["datetime", "symbol", "open", "high", "low", "close", "volume", "oi"]


def load_historical(path: str,
                    symbols: Optional[list[str]] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> list[dict]:
    """加载历史行情 CSV

    参数:
      path:       CSV 文件路径
      symbols:    品种过滤，如 ["RB","CU"]；None=全部
      start_date: 起始日期 "%Y-%m-%d"；None=不限制
      end_date:   截止日期 "%Y-%m-%d"；None=不限制

    返回: list[dict]，每行包含 REQUIRED_COLUMNS + 原始行号
    """
    if not os.path.exists(path):
        print(f"[loader] ❌ 文件不存在: {path}")
        return []

    rows = []
    line_no = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # 验证列
        if not reader.fieldnames:
            print(f"[loader] ❌ 空文件或无法读取列名: {path}")
            return []

        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing:
            print(f"[loader] ❌ 缺少必需列: {', '.join(sorted(missing))}")
            print(f"[loader]    现有列: {', '.join(reader.fieldnames)}")
            return []

        for row in reader:
            line_no += 1
            try:
                # 品种过滤
                sym = row.get("symbol", "").strip().upper()
                if symbols and sym not in symbols:
                    continue

                # 日期过滤
                dt_str = row.get("datetime", "").strip()
                if start_date and dt_str[:10] < start_date:
                    continue
                if end_date and dt_str[:10] > end_date:
                    continue

                # 类型转换
                parsed = {
                    "datetime": dt_str,
                    "symbol": sym,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(float(row.get("volume", 0))),
                    "oi": int(float(row.get("oi", 0))),
                    "_line": line_no,
                }

                # 基本验证
                if parsed["close"] <= 0:
                    print(f"[loader] ⚠ 第 {line_no} 行 close 无效: {parsed['close']}, 跳过")
                    continue

                rows.append(parsed)

            except (ValueError, TypeError) as e:
                print(f"[loader] ⚠ 第 {line_no} 行解析失败: {e}")
                continue

    print(f"[loader] ✅ 加载完成: {len(rows)} 行 (总扫描 {line_no} 行)")
    return rows


def validate_csv(path: str) -> dict:
    """快速验证 csv 文件可用性

    返回:
      {"ok": True/False, "rows": int, "symbols": list, "period": (start, end)}
    """
    result = {
        "ok": False,
        "rows": 0,
        "symbols": [],
        "period": ("", ""),
    }

    if not os.path.exists(path):
        result["error"] = "文件不存在"
        return result

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            result["error"] = "空文件"
            return result
        if not set(REQUIRED_COLUMNS).issubset(set(reader.fieldnames)):
            missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
            result["error"] = f"缺少列: {missing}"
            return result

        symbols = set()
        dates = set()
        count = 0
        for row in reader:
            count += 1
            sym = row.get("symbol", "").strip().upper()
            if sym:
                symbols.add(sym)
            dt = row.get("datetime", "").strip()[:10]
            if dt:
                dates.add(dt)

    result["ok"] = True
    result["rows"] = count
    result["symbols"] = sorted(symbols)
    if dates:
        result["period"] = (min(dates), max(dates))
    else:
        result["period"] = ("", "")

    return result


if __name__ == "__main__":
    import json
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    if not path:
        print("用法: python3 loader.py <csv_path> [symbol_filter]")
        sys.exit(1)

    symbols = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    result = validate_csv(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["ok"]:
        rows = load_historical(path, symbols=symbols)
        print(f"  首行: {rows[0] if rows else '∅'}")
        print(f"  末行: {rows[-1] if rows else '∅'}")
