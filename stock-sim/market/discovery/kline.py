"""market/discovery/kline.py — 日 K 线事实源

职责：
  读取 admission_pool.json（L1），
  对每只合格股票获取最近 20 个交易日日 K 线，
  计算均线、振幅等衍生指标，
  输出 kline_snapshot.json。

数据契约：
  - 输入：admission_pool.json（只读 L1 通过标的）
  - 输出：kline_snapshot.json（L2 评分消费）
  - 覆盖范围 = L1 Admission Pool，不独立扩展
  - 失败不影响其他数据源（flow.py）

API 端点：
  https://push2his.eastmoney.com/api/qt/stock/kline/get
  secid = 1.{symbol} (SH) / 0.{symbol} (SZ)
  返回 field: f51=date, f52=open, f53=close, f54=high, f55=low, f56=volume, f57=amount
"""

import json
import os
import time
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
BAR_COUNT = 20  # 拉取 20 个交易日

REQUEST_INTERVAL = 0.12  # 请求间隔（秒）
REQUEST_TIMEOUT  = 10    # 单次超时（秒）

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMISSION_PATH = os.path.join(BASE_DIR, "admission_pool.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "kline_snapshot.json")

# ---------------------------------------------------------------------------
# 市场判定
# ---------------------------------------------------------------------------

SH_PREFIXES = {"600", "601", "603", "688", "605"}

def _secid(symbol: str) -> Optional[str]:
    """symbol → East Money secid（1=SH, 0=SZ）"""
    prefix = symbol[:3]
    if prefix in SH_PREFIXES or (prefix.startswith("6") and len(symbol) == 6):
        return f"1.{symbol}"
    else:
        return f"0.{symbol}"

# ---------------------------------------------------------------------------
# HTTP 请求
# ---------------------------------------------------------------------------

def _http_get(url: str) -> Optional[str]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Referer": "https://quote.eastmoney.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None

# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

def _parse_kline_response(text: str) -> Optional[dict]:
    """解析 kline API 响应，返回 {date: {open,close,high,low,vol,amt}, ...}"""
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    data = obj.get("data")
    if not isinstance(data, dict):
        return None
    klines = data.get("klines")
    if not isinstance(klines, list):
        return None

    result = {}
    for raw in klines:
        parts = raw.split(",")
        if len(parts) < 7:
            continue
        try:
            date = parts[0]
            result[date] = {
                "open":  float(parts[1]),
                "close": float(parts[2]),
                "high":  float(parts[3]),
                "low":   float(parts[4]),
                "volume": int(float(parts[5])),
                "amount": float(parts[6]),
            }
        except (ValueError, IndexError):
            continue
    return result

# ---------------------------------------------------------------------------
# 衍生计算
# ---------------------------------------------------------------------------

def _derive_ma(bars: dict, period: int) -> Optional[float]:
    """计算 N 日移动平均收盘价（取最新 N 根 bar）"""
    all_closes = list(bars.values())
    closes = [b["close"] for b in all_closes][-period:]
    if len(closes) < period:
        return None
    return sum(closes) / period


def _derive_high_low(bars: dict, period: int) -> tuple[Optional[float], Optional[float]]:
    """计算 N 日最高/最低（取最新 N 根 bar）"""
    all_bars = list(bars.values())
    recent = all_bars[-period:]
    if not recent:
        return None, None
    highs = [b["high"] for b in recent]
    lows  = [b["low"]  for b in recent]
    return max(highs), min(lows)


def _derive_amplitude_avg(bars: dict, period: int) -> Optional[float]:
    """计算 N 日振幅平均值（取最新 N 根 bar）"""
    all_bars = list(bars.values())
    recent = all_bars[-period:]
    amps = []
    for b in recent:
        _range = b["high"] - b["low"]
        if b["close"] > 0:
            amps.append(_range / b["close"] * 100)
    if len(amps) < period:
        return None
    return sum(amps) / period

# ---------------------------------------------------------------------------
# 每股 K 线获取
# ---------------------------------------------------------------------------

def _fetch_kline(symbol: str) -> Optional[dict]:
    """获取单只股票的 K 线数据"""
    sid = _secid(symbol)
    if not sid:
        return None

    import urllib.parse
    params = {
        "secid": sid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",   # 日 K
        "fqt": "1",     # 前复权
        "end": "20500101",
        "lmt": str(BAR_COUNT),
    }
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"{KLINE_URL}?{query}"
    text = _http_get(url)
    if not text:
        return None
    bars = _parse_kline_response(text)
    if not bars:
        return None

    # 计算衍生指标
    ma5  = _derive_ma(bars, 5)
    ma20 = _derive_ma(bars, 20)
    high_20d, low_20d = _derive_high_low(bars, 20)
    amp_avg = _derive_amplitude_avg(bars, 20)

    return {
        "bars": bars,
        "ma5": ma5,
        "ma20": ma20,
        "high_20d": high_20d,
        "low_20d": low_20d,
        "amplitude_avg_20d": amp_avg,
    }

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_kline_snapshot(
    admission_path: str = ADMISSION_PATH,
    output_path: str = OUTPUT_PATH,
) -> int:
    """执行 K 线快照采集

    Returns: 成功采集数量
    """
    # 1. 读取 admission_pool
    with open(admission_path, "r", encoding="utf-8") as f:
        admission = json.load(f)

    symbols = admission.get("symbols", [])
    details_data = admission.get("details", [])
    # 建立 symbol → detail 映射（取 trace_id 和 name）
    detail_map = {d["symbol"]: d for d in details_data}

    snapshot_date = time.strftime("%Y-%m-%d")
    generated_at  = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())
    source_ts = admission.get("generated_at", generated_at)

    # 2. 逐股获取 K 线
    result_details = []
    success_count = 0
    fail_count = 0

    for sym in symbols:
        time.sleep(REQUEST_INTERVAL)
        kline_data = _fetch_kline(sym)
        detail = detail_map.get(sym, {})

        record = {
            "symbol": sym,
            "name": detail.get("name", ""),
            "snapshot_date": snapshot_date,
            "source": "eastmoney_kline",
            "source_snapshot": admission.get("source_snapshot", ""),
            "trace_id": detail.get("trace_id", ""),
        }

        if kline_data:
            record.update({
                "available": True,
                "bar_count": len(kline_data["bars"]),
                "bars": kline_data["bars"],
                "ma5": kline_data["ma5"],
                "ma20": kline_data["ma20"],
                "high_20d": kline_data["high_20d"],
                "low_20d": kline_data["low_20d"],
                "amplitude_avg_20d": kline_data["amplitude_avg_20d"],
            })
            success_count += 1
        else:
            record["available"] = False
            record["bar_count"] = 0
            fail_count += 1

        result_details.append(record)

    # 3. 输出
    output = {
        "version": 1,
        "pool_stage": "kline",
        "generated_at": generated_at,
        "source_snapshot": admission.get("source_snapshot", ""),
        "source_time": source_ts,
        "description": "K线事实：日线 OHLCV 用于 L2 评分因子计算",
        "symbol_count": len(symbols),
        "success_count": success_count,
        "fail_count": fail_count,
        "symbols": symbols,
        "bar_count": BAR_COUNT,
        "details": result_details,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"kline_snapshot: {success_count}/{len(symbols)} OK, {fail_count} FAIL → {output_path}")
    return success_count


# ---------------------------------------------------------------------------
# 独立入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_kline_snapshot()
