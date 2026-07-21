#!/usr/bin/env python3
"""
Futures-Sim 历史数据导入工具 (AkShare)
======================================
一次性数据获取脚本，独立于 Futures-Sim 核心架构。
职责：下载 → CSV 保存 → 结束。
输出文件可直接丢入 market_futures/data/historical/ 供 replay 消费。

用法:
  python3 akshare_export.py [--output-dir <path>] [--years 3]

输出:
  data/historical/<品种>_<年份>.csv  格式: ts,symbol,open,high,low,close,volume,oi

约束:
  - 独立工具，不属于 market_futures 核心模块
  - 不修改任何 Phase 1-5 代码
  - CSV 格式严格对齐 replay/schema.md
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

# ── 品种映射（akshare 主力连续代码 → 本系统品种代码） ────────────
SYMBOL_MAP = {
    "RB0": "RB",   # 螺纹钢
    "I0":  "I",    # 铁矿石
    "JM0": "JM",   # 焦煤
    "CU0": "CU",   # 沪铜
    "AL0": "AL",   # 沪铝
    "SC0": "SC",   # 原油
}

# 额外品种（可逐步启用）
EXTRA_SYMBOLS = {
    "AU0": "AU",   # 沪金
    "AG0": "AG",   # 沪银
    "ZN0": "ZN",   # 沪锌
    "J0":  "J",    # 焦炭
    "FU0": "FU",   # 燃料油
    "RU0": "RU",   # 橡胶
    "TA0": "TA",   # PTA
    "MA0": "MA",   # 甲醇
    "PP0": "PP",   # 聚丙烯
}

# ── AkShare 列名映射 ──────────────────────────────────────────
COLUMN_MAP = {
    "日期":      "datetime",
    "开盘价":    "open",
    "最高价":    "high",
    "最低价":    "low",
    "收盘价":    "close",
    "成交量":    "volume",
    "持仓量":    "oi",
}


def fetch_contract(symbol_ak: str, our_symbol: str, start_date: str,
                   end_date: str, output_dir: str) -> str | None:
    """拉取单个品种日线数据并保存 CSV。"""
    try:
        import akshare as ak
    except ImportError:
        print("[akshare] ❌ akshare 未安装: pip install akshare")
        sys.exit(1)

    print(f"  [{our_symbol}] 正在下载 {symbol_ak} ({start_date} → {end_date})...",
          end=" ", flush=True)

    try:
        df = ak.futures_main_sina(symbol=symbol_ak, start_date=start_date,
                                  end_date=end_date)
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None

    if df is None or df.empty:
        print("⚠️  无数据")
        return None

    # 列名映射
    df = df.rename(columns=COLUMN_MAP)

    # 只保留需要的列
    needed = list(COLUMN_MAP.values())
    df = df[[c for c in needed if c in df.columns]]

    # 添加品种代码（去掉末尾的 0）
    df["symbol"] = our_symbol

    # 排序
    df = df.sort_values("datetime")

    # 构建文件名
    first_ts = df["datetime"].iloc[0]
    last_ts = df["datetime"].iloc[-1]

    if hasattr(first_ts, "strftime"):
        start_year = first_ts.strftime("%Y")
        end_year = last_ts.strftime("%Y")
    else:
        start_year = str(first_ts)[:4]
        end_year = str(last_ts)[:4]
    if start_year == end_year:
        filename = f"{our_symbol}_{start_year}.csv"
    else:
        filename = f"{our_symbol}_{start_year}-{end_year}.csv"

    # 确保时间列排在最前
    cols = df.columns.tolist()
    if "datetime" in cols:
        cols.insert(0, cols.pop(cols.index("datetime")))
        df = df[cols]

    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)
    print(f"✅ {len(df)} 行 → {filename}")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Futures-Sim 历史数据导入工具 (AkShare)")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录（默认: 脚本所在目录下 data/historical/）")
    parser.add_argument("--years", type=int, default=4,
                        help="回溯年数（默认 4，即 2022-2026）")
    parser.add_argument("--all", action="store_true",
                        help="下载全部 15 品种（默认仅首批 6 品种）")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="指定品种代码，如 RB I CU（使用本系统代码）")
    args = parser.parse_args()

    # 确定输出目录
    if args.output_dir:
        output_dir = args.output_dir
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "..", "..",
                                  "market_futures", "data", "historical")

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 确定下载品种
    if args.symbols:
        # 反向映射：本系统代码 → akshare 代码
        reverse_map = {v: k for k, v in {**SYMBOL_MAP, **EXTRA_SYMBOLS}.items()}
        selected = {}
        for s in args.symbols:
            s = s.upper()
            if s in reverse_map:
                selected[reverse_map[s]] = s
            else:
                print(f"⚠️  未知品种: {s}，跳过")
    elif args.all:
        selected = {**SYMBOL_MAP, **EXTRA_SYMBOLS}
    else:
        selected = dict(SYMBOL_MAP)  # 默认 6 品种

    # 时间范围
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=args.years * 365)).strftime("%Y%m%d")

    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  Futures-Sim 历史数据导入                    ║")
    print(f"║  来源: AkShare (新浪财经)                    ║")
    print(f"║  周期: {args.years}年 ({start_date} ~ {end_date})       ")
    print(f"║  品种: {len(selected)} 个                      ")
    print(f"║  输出: {output_dir}")
    print(f"╚══════════════════════════════════════════════╝")
    print()

    results = []
    for symbol_ak, our_symbol in sorted(selected.items()):
        path = fetch_contract(symbol_ak, our_symbol, start_date,
                              end_date, output_dir)
        results.append((our_symbol, path))

    # 汇总
    print()
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  下载汇总                                    ║")
    print(f"╠══════════════════════════════════════════════╣")
    success = [r for r in results if r[1] is not None]
    failed = [r for r in results if r[1] is None]
    print(f"║  成功: {len(success)}  |  失败: {len(failed)}")
    if success:
        print(f"╠──────────────────────────────────────────────╣")
        for name, path in success:
            fname = os.path.basename(path) if path else "?"
            print(f"║  ✅ {name:4s} → {fname}")
    if failed:
        print(f"╠──────────────────────────────────────────────╣")
        for name, _ in failed:
            print(f"║  ❌ {name:4s}  下载失败")
    print(f"╚══════════════════════════════════════════════╝")

    # 写入数据清单 metadata
    metadata = {
        "provider": "akshare",
        "source": "新浪财经 (futures_main_sina)",
        "frequency": "daily",
        "contract_type": "主力连续",
        "fetch_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "period": f"{start_date}~{end_date}",
        "symbols": [r[0] for r in success],
        "files": [os.path.basename(r[1]) for r in success if r[1]],
    }
    import json
    meta_path = os.path.join(output_dir, ".source_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"\n📋 metadata 写入: {meta_path}")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
