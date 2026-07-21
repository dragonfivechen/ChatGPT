#!/usr/bin/env python3
"""
trading-runtime — market_stream.py

Phase 6.3 实时行情流组件

职责: 读取历史日线 CSV → 按真实时钟节奏输出 QUOTE 事件

工作模式:
  1. realtime (默认): 每 N 秒输出一条 QUOTE (墙钟驱动)
  2. batch: 一次性输出所有 QUOTE (等价于 replay)
  3. scheduled: 仅在指定交易时段输出

边界:
  - 不参与信号生成
  - 不参与下单
  - 不参与风控
  - 仅提供 QUOTE 事件流

使用:
  from market_stream import MarketStream

  stream = MarketStream(speed_sec=10)
  stream.load_csv("RB_2022-2026.csv")

  for quote in stream.run():
      print(quote)  # yield QUOTE dict
"""

import csv
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Generator, Optional

BJT = timezone(timedelta(hours=8))

# ── CSV 列名映射 ──────────────────────────────────────────
CSV_FIELD_MAP = {
    "datetime": "ts",
    "close": "price",
    "symbol": "symbol",
    "open": "open",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "oi": "oi",
}


class MarketStream:
    """实时行情流 — 历史 CSV → QUOTE 事件"""

    def __init__(self, speed_sec: float = 10.0):
        """
        Args:
            speed_sec: 每输出一条 QUOTE 间隔秒数 (墙钟)。1.0 = 1秒/条
        """
        self.speed_sec = speed_sec
        self.bars: list[dict] = []        # 原始 bars
        self.index = 0                    # 当前 bar 索引
        self.total_bars = 0
        self.start_time: Optional[float] = None
        self.running = False

        # 统计
        self.stats = {
            "loaded": 0,
            "emitted": 0,
            "elapsed_seconds": 0,
        }

    def load_csv(self, path: str) -> int:
        """加载一个 CSV 行情文件"""
        n = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_raw = row.get("datetime", "")
                sym = row.get("symbol", "")
                close = row.get("close", "0")

                if not ts_raw or not sym:
                    continue

                bar = {
                    "event_type": "FUTURES_QUOTE",
                    "ts": ts_raw,
                    "symbol": sym,
                    "price": float(close),
                    "open": float(row.get("open", close)),
                    "high": float(row.get("high", close)),
                    "low": float(row.get("low", close)),
                    "volume": int(float(row.get("volume", 0))),
                    "oi": int(float(row.get("oi", 0))),
                }
                self.bars.append(bar)
                n += 1

        # 按时间排序
        self.bars.sort(key=lambda x: x["ts"])
        self.total_bars = len(self.bars)
        self.stats["loaded"] = self.total_bars
        print(f"[market_stream] 📥 加载 {n} 条日线 → {path}")
        return n

    def load_csvs(self, paths: list[str]) -> int:
        """加载多个 CSV 文件"""
        total = 0
        for p in paths:
            total += self.load_csv(p)
        self.total_bars = len(self.bars)
        print(f"[market_stream] 📥 共加载 {total} 条日线 ({len(paths)} 文件)")
        return total

    def load_historical_dir(self, directory: str) -> int:
        """从目录加载所有 *_2022-2026.csv 文件"""
        total = 0
        for fname in sorted(os.listdir(directory)):
            if fname.endswith(".csv") and "schema" not in fname and "sample" not in fname:
                total += self.load_csv(os.path.join(directory, fname))
        self.total_bars = len(self.bars)
        print(f"[market_stream] 📥 目录加载: {total} 条日线")
        return total

    def run(self) -> Generator[dict, None, None]:
        """
        实时行情流生成器

        按 speed_sec 间隔 yield QUOTE 事件。
        每次 yield 后通过 send() 可接收外部信号：
          stream.send("STOP") → 停止

        Yields:
            dict: FUTURES_QUOTE 事件
        """
        if not self.bars:
            print("[market_stream] ⚠️  无行情数据")
            return

        self.running = True
        self.index = 0
        self.start_time = time.time()

        for bar in self.bars:
            if not self.running:
                break

            # 等待 speed_sec 秒
            time.sleep(self.speed_sec)

            # 更新时间统计
            self.stats["elapsed_seconds"] = time.time() - self.start_time
            self.stats["emitted"] = self.index + 1

            # 添加 stream_ts (墙钟时间)
            bar_with_meta = dict(bar)
            bar_with_meta["stream_ts"] = datetime.now(BJT).isoformat()
            bar_with_meta["bar_index"] = self.index

            yield bar_with_meta
            self.index += 1

        self.running = False
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"[market_stream] ✅ 流结束: {self.stats['emitted']} QUOTE "
              f"({elapsed:.1f}s 墙钟)")

    def skip_to(self, target_ts: str) -> int:
        """跳过直到指定时间戳 (用于断点恢复后追数据)"""
        skipped = 0
        for i, bar in enumerate(self.bars):
            if bar["ts"] >= target_ts:
                self.index = i
                break
            skipped += 1
        print(f"[market_stream] ⏩ 跳过 {skipped} 条到 {target_ts}")
        return skipped

    def stop(self):
        """停止流"""
        self.running = False

    def summary(self) -> dict:
        """当前流状态"""
        remaining = self.total_bars - self.index
        progress = 0
        if self.total_bars > 0:
            progress = round(self.index / self.total_bars * 100, 1)

        return {
            "total_bars": self.total_bars,
            "emitted": self.stats["emitted"],
            "remaining": max(0, remaining),
            "progress_pct": progress,
            "running": self.running,
            "speed_sec_per_bar": self.speed_sec,
            "elapsed_seconds": round(self.stats["elapsed_seconds"], 1),
        }


def parse_ts(ts_str: str) -> datetime:
    """解析多种格式的时间戳"""
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=BJT)
            return dt
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {ts_str}")


# ── 独立测试 ──────────────────────────────────────────────

def _demo():
    """demo: 加载历史数据，输出前 5 条"""
    hist_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "market_futures", "data", "historical"
    )
    if not os.path.exists(hist_dir):
        print(f"[demo] ❌ 历史数据目录不存在: {hist_dir}")
        return

    stream = MarketStream(speed_sec=0.5)  # 0.5秒/条
    stream.load_historical_dir(hist_dir)

    count = 0
    for quote in stream.run():
        print(f"  [{count + 1}] {quote['symbol']} @{quote['ts']}  ¥{quote['price']}")
        count += 1
        if count >= 5:
            stream.stop()
            break

    print(f"\n[demo] ✅ 流测试: {count} QUOTE")
    print(f"[demo] 📊 摘要: {json.dumps(stream.summary(), ensure_ascii=False)}")


if __name__ == "__main__":
    _demo()
