"""market/discovery/flow.py — 资金流向事实源

职责：
  读取 admission_pool.json（L1），
  对每只合格股票获取日资金流向数据，
  计算方向、强度、持续性，
  输出 flow_snapshot.json。

数据契约：
  - 输入：admission_pool.json（只读 L1 通过标的）
  - 输出：flow_snapshot.json（L2 评分消费）
  - 覆盖范围 = L1 Admission Pool，不独立扩展
  - 失败不影响其他数据源（kline.py）

API 端点：
  https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get
  secid = 1.{symbol} (SH) / 0.{symbol} (SZ)
  f52=主力净流入额, f57=主力净流入占比%, f56=小单净流入额
"""

import json
import os
import time
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

FLOW_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
BAR_COUNT = 20  # 拉取 20 日资金流（用于判断持续性）

REQUEST_INTERVAL = 0.12
REQUEST_TIMEOUT  = 10

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMISSION_PATH = os.path.join(BASE_DIR, "admission_pool.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "flow_snapshot.json")

# ---------------------------------------------------------------------------
# 市场判定
# ---------------------------------------------------------------------------

SH_PREFIXES = {"600", "601", "603", "688", "605"}

def _secid(symbol: str) -> Optional[str]:
    prefix = symbol[:3]
    if prefix in SH_PREFIXES or (prefix.startswith("6") and len(symbol) == 6):
        return f"1.{symbol}"
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

def _parse_flow_response(text: str) -> Optional[list[dict]]:
    """解析资金流 API 响应，返回按日期排序的列表

    API 返回字段（已验证）：
      f52 = 主力净流入额（float）
      f57 = 主力净流入占比 %（float）
      f56 = 小单净流入额（float）
    """
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

    result = []
    for raw in klines:
        parts = raw.split(",")
        if len(parts) < 8:
            continue
        try:
            result.append({
                "date": parts[0],
                "main_net_inflow": float(parts[1]) if parts[1] else 0.0,
                "main_ratio_pct":  float(parts[6]) if parts[6] else 0.0,
                "retail_net_inflow": float(parts[5]) if parts[5] else 0.0,
            })
        except (ValueError, IndexError):
            continue
    return result

# ---------------------------------------------------------------------------
# 持续性计算
# ---------------------------------------------------------------------------

def _count_consecutive_days(flow_records: list[dict]) -> int:
    """计算主力资金连续同方向天数（从最新向前推）

    Returns:
        正数=连续净流入天数, 负数=连续净流出天数
    """
    if not flow_records:
        return 0

    # 从最新开始
    latest = flow_records[0]
    latest_sign = latest["main_net_inflow"] >= 0

    count = 1
    for rec in flow_records[1:]:
        if (rec["main_net_inflow"] >= 0) == latest_sign:
            count += 1
        else:
            break

    return count if latest_sign else -count

# ---------------------------------------------------------------------------
# 每股资金流获取
# ---------------------------------------------------------------------------

def _fetch_flow(symbol: str) -> Optional[dict]:
    """获取单只股票的资金流数据"""
    sid = _secid(symbol)
    if not sid:
        return None

    import urllib.parse
    params = {
        "secid": sid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "lmt": str(BAR_COUNT),
    }
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"{FLOW_URL}?{query}"
    text = _http_get(url)
    if not text:
        return None
    records = _parse_flow_response(text)
    if not records:
        return None

    # 当日（最新）数据
    today = records[0]

    # 平均主力净流入占比（20 日）
    ratios = [r["main_ratio_pct"] for r in records if r["main_ratio_pct"] != 0]
    avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0

    return {
        "records": records,
        "main_net_inflow": today["main_net_inflow"],
        "main_ratio_pct":  today["main_ratio_pct"],
        "retail_net_inflow": today["retail_net_inflow"],
        "avg_main_ratio_20d": avg_ratio,
        "consecutive_days": _count_consecutive_days(records),
    }

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_flow_snapshot(
    admission_path: str = ADMISSION_PATH,
    output_path: str = OUTPUT_PATH,
) -> int:
    """执行资金流快照采集

    Returns: 成功采集数量
    """
    # 1. 读取 admission_pool
    with open(admission_path, "r", encoding="utf-8") as f:
        admission = json.load(f)

    symbols = admission.get("symbols", [])
    details_data = admission.get("details", [])
    detail_map = {d["symbol"]: d for d in details_data}

    snapshot_date = time.strftime("%Y-%m-%d")
    generated_at  = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())
    source_ts = admission.get("generated_at", generated_at)

    # 2. 逐股获取资金流
    result_details = []
    success_count = 0
    fail_count = 0

    for sym in symbols:
        time.sleep(REQUEST_INTERVAL)
        flow_data = _fetch_flow(sym)
        detail = detail_map.get(sym, {})

        record = {
            "symbol": sym,
            "name": detail.get("name", ""),
            "snapshot_date": snapshot_date,
            "source": "eastmoney_flow",
            "source_snapshot": admission.get("source_snapshot", ""),
            "trace_id": detail.get("trace_id", ""),
        }

        if flow_data:
            record.update({
                "available": True,
                "record_count": len(flow_data["records"]),
                "main_net_inflow": flow_data["main_net_inflow"],
                "main_ratio_pct":  flow_data["main_ratio_pct"],
                "retail_net_inflow": flow_data["retail_net_inflow"],
                "avg_main_ratio_20d": flow_data["avg_main_ratio_20d"],
                "consecutive_days": flow_data["consecutive_days"],
                "direction": "inflow" if flow_data["main_net_inflow"] >= 0 else "outflow",
            })
            success_count += 1
        else:
            record["available"] = False
            fail_count += 1

        result_details.append(record)

    # 3. 输出
    output = {
        "version": 1,
        "pool_stage": "flow",
        "generated_at": generated_at,
        "source_snapshot": admission.get("source_snapshot", ""),
        "source_time": source_ts,
        "description": "资金流事实：主力资金流向用于 L2 评分因子计算",
        "symbol_count": len(symbols),
        "success_count": success_count,
        "fail_count": fail_count,
        "symbols": symbols,
        "details": result_details,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"flow_snapshot: {success_count}/{len(symbols)} OK, {fail_count} FAIL → {output_path}")
    return success_count


# ---------------------------------------------------------------------------
# 独立入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_flow_snapshot()
