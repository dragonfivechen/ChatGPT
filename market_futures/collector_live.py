#!/usr/bin/env python3
"""collector_live.py — 期货实盘行情采集（Sina 财经）

用法:
  python3 collector_live.py                 # 单次采集
  python3 collector_live.py --verbose       # 详细输出

被 systemd timer 调用。每次运行：
  1. 检查是否交易时段
  2. 如果是：采集6品种行情 → 写入 futures_events.jsonl
  3. 如果否：退出

Sina futures 格式 (GBK, 逗号分隔):
  0=品种名称 1=代码 2=开盘 3=昨结算
  4=当前价  5=今最高 6=今最低 7=持仓量
  8=成交量  9=结算价 10=涨跌 ...
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

_BASE = os.path.dirname(os.path.abspath(__file__))
_EVENTS_FILE = os.path.join(_BASE, "futures_events.jsonl")

# ── 品种映射 ────────────────────────────────────────────
SYMBOLS = {
    "RB": "螺纹钢",
    "I":  "铁矿石",
    "JM": "焦煤",
    "CU": "沪铜",
    "AL": "沪铝",
    "SC": "原油",
}

SINA_URL = "https://hq.sinajs.cn/list={prefix}_{symbol}"


def is_trading_time() -> bool:
    """检查当前是否在交易时段（日盘+夜盘）"""
    now = datetime.now(BJT)
    wd = now.weekday()  # 0=Mon
    if wd >= 5:
        return False  # 周末休市
    h, m = now.hour, now.minute
    t = h * 100 + m
    # 日盘: 09:00-11:30, 13:30-15:00
    # 夜盘: 21:00-23:00 (部分品种到 02:30)
    return (
        (900 <= t <= 1130) or
        (1330 <= t <= 1500) or
        (2100 <= t <= 2359) or
        (0 <= t <= 230)  # 夜盘跨日
    )


def parse_response(text: str, symbol: str) -> dict | None:
    """解析 Sina 期货返回文本"""
    if "=\"" not in text:
        return None
    raw = text.split("=\"", 1)[1].rstrip("\";\n\r ")
    parts = raw.split(",")
    if len(parts) < 15:
        return None

    def sf(idx: int) -> float:
        try:
            return float(parts[idx]) if parts[idx] else 0.0
        except (ValueError, IndexError):
            return 0.0

    name = parts[0]
    price = sf(4)    # 当前价
    open_p = sf(2)   # 开盘
    high = sf(5)     # 最高
    low = sf(6)      # 最低
    prev_close = sf(3)  # 昨结算
    volume = int(sf(8))  # 成交量
    oi = int(sf(7))   # 持仓量

    now = datetime.now(BJT)

    return {
        "event_type": "FUTURES_QUOTE",
        "ts": now.isoformat(),
        "symbol": symbol,
        "name": name,
        "price": round(price, 2),
        "open": round(open_p, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "prev_close": round(prev_close, 2),
        "volume": volume,
        "oi": oi,
        "source": "sina_live",
    }


def fetch_symbol(symbol: str) -> dict | None:
    """采集单个品种"""
    url = SINA_URL.format(prefix="nf", symbol=symbol + "0")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("gbk")
        return parse_response(text, symbol)
    except Exception as e:
        print(f"[collector_live] ⚠️  {symbol}: {e}", file=sys.stderr)
        return None


def append_event(event: dict):
    """追加事件到 futures_events.jsonl"""
    os.makedirs(os.path.dirname(_EVENTS_FILE), exist_ok=True)
    with open(_EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def main(verbose: bool = False):
    if not is_trading_time():
        if verbose:
            print("[collector_live] 非交易时段，跳过")
        return

    collected = 0
    errors = 0
    for sym, cname in SYMBOLS.items():
        event = fetch_symbol(sym)
        if event:
            append_event(event)
            collected += 1
            if verbose:
                print(f"[collector_live] ✅ {sym} ({cname}): "
                      f"{event['price']} vol={event['volume']}")
        else:
            errors += 1
            if verbose:
                print(f"[collector_live] ❌ {sym} ({cname}): 采集失败")
        time.sleep(0.3)  # 避免频率限制

    print(f"[collector_live] 完成: {collected}成功/{errors}失败")


if __name__ == "__main__":
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    main(verbose=verbose)
