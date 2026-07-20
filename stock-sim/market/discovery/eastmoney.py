"""market/discovery/eastmoney.py — 东方财富 clist 市场发现源

职责限定：
  调用 push2.eastmoney.com/api/qt/clist/get 获取多维度排行；
  合并去重；
  输出 candidate list（含来源标签 + 原始指标）。
  不做评分、不做交易判断。

输出格式（list[dict]）：
  {
    "symbol": "000001",
    "name": "平安银行",
    "reasons": ["amount_rank", "momentum_rank"],
    "metrics": { "amount": 1.23e9, "change_pct": 2.34, ... },
    "discovered_at": "2026-07-20T11:00:00+08:00"
  }

架构边界：
  ✅ 独立于 feeds/ 层（不参与行情采集）
  ✅ 输出现察候选事件（不是交易事实）
  ❌ 不进 events.jsonl
  ❌ 不修改 V2
"""

import json
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

CLIST_URL = "http://push2.eastmoney.com/api/qt/clist/get"

# 通用参数（ut 为公共 token，来自开源社区，仅用于读取公开排行数据）
BASE_PARAMS = {
    "np": "1",
    "fltt": "2",
    "invt": "2",
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",   # 沪深A + 北交所
    "fields": "f2,f3,f5,f6,f7,f8,f10,f12,f14,f15,f16,f17,f18,f20,f21,f37,f62,f100,f109,f184",
}

# ── 排行维度定义 ──────────────────────────────────────────────────────────
# (name, fid, po, pz, label)
#   fid=排序字段, po=1降序/0升序, pz=拉取条数
RANK_DIMENSIONS = [
    ("amount",      "f6",   1, 100, "成交额排行"),       # 成交额 TOP100
    ("gainers",     "f3",   1,  80, "涨幅排行"),         # 涨幅 TOP80
    ("turnover",    "f8",   1,  80, "换手率排行"),       # 换手率 TOP80
    ("vol_ratio",   "f10",  1,  80, "量比排行"),         # 量比 TOP80
    ("amplitude",   "f7",   1,  80, "振幅排行"),         # 振幅 TOP80
    ("momentum_20d","f109", 1,  80, "20日涨幅排行"),     # 趋势动量 TOP80（f109=20日涨跌幅）
    ("capital_flow","f62",  1,  80, "主力资金流入排行"), # 资金关注 TOP80
]

# 基础过滤
MIN_PRICE       = 2.0    # 低于 2 元视为低价股/风险股，不纳入
MAX_STOCK_COUNT = 200    # 候选上限
FETCH_INTERVAL  = 0.15   # 请求间隔 s（东方财富对 clist 频率限制宽松，但保持礼貌）

# ---------------------------------------------------------------------------
# 模型
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    symbol: str
    name: str
    reasons: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    discovered_at: str = ""
    source_dimensions: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# 发现引擎
# ---------------------------------------------------------------------------

class EastMoneyDiscovery:
    """东方财富市场发现源"""

    def __init__(self):
        self._url_template = CLIST_URL

    # ── 公共入口 ──────────────────────────────────────────────────────────

    def discover(self) -> list[dict]:
        """执行多维度发现，返回合并去重后的候选列表"""
        merged: dict[str, Candidate] = {}

        for dim_name, fid, po, pz, label in RANK_DIMENSIONS:
            try:
                rows = self._fetch_rank(fid, po, pz)
            except Exception as e:
                # 单维度失败不影响其他维度
                continue

            for row in rows:
                sym = row.get("f12", "")
                if not sym:
                    continue
                # 基础过滤
                if not self._pass_basic_filter(row):
                    continue

                if sym not in merged:
                    merged[sym] = Candidate(
                        symbol=sym,
                        name=row.get("f14", ""),
                        discovered_at=time.strftime(
                            "%Y-%m-%dT%H:%M:%S+08:00", time.localtime()
                        ),
                    )
                cand = merged[sym]
                cand.reasons.append(dim_name)
                cand.source_dimensions.append(label)
                # 合并指标（保留每个维度最新值）
                # 安全取值 + 数值类型转换
                def _num(v, default=0):
                    if isinstance(v, (int, float)):
                        return v
                    try:
                        return float(v) if v is not None else default
                    except (ValueError, TypeError):
                        return default

                cand.metrics.setdefault("amount", _num(row.get("f6", 0)))
                cand.metrics.setdefault("change_pct", _num(row.get("f3", 0)))
                cand.metrics.setdefault("volume", int(_num(row.get("f5", 0))))
                cand.metrics.setdefault("turnover_pct", _num(row.get("f8", 0)))
                cand.metrics.setdefault("vol_ratio", _num(row.get("f10", 0)))
                cand.metrics.setdefault("amplitude_pct", _num(row.get("f7", 0)))
                cand.metrics.setdefault("momentum_20d_pct", _num(row.get("f109", 0)))
                cand.metrics.setdefault("capital_flow", _num(row.get("f62", 0)))
                cand.metrics.setdefault("total_market_cap", _num(row.get("f20", 0)))
                cand.metrics.setdefault("industry", row.get("f100", "") or "")

        # 按出现次数排序（多个维度同时命中 → 更值得关注）
        def sort_key(c):
            amt = c.metrics.get("amount", 0)
            if not isinstance(amt, (int, float)):
                amt = 0
            return (-len(c.reasons), -amt)

        candidates = sorted(merged.values(), key=sort_key)

        result = [c.to_dict() for c in candidates[:MAX_STOCK_COUNT]]
        return result

    # ── 过滤 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _pass_basic_filter(row: dict) -> bool:
        """基础准入判断"""
        price = row.get("f2", 0)
        name  = row.get("f14", "")

        # 退市/停牌/异常: price <= 0
        if not price or price is None or (isinstance(price, (int, float)) and price <= 0):
            return False

        # 低价股过滤
        if isinstance(price, (int, float)) and price < MIN_PRICE:
            return False

        # ST / *ST / 退市
        if "ST" in name or "退" in name or "S" in name:
            return False

        # 成交额过低（< 500 万视为流动性不足）
        amount = row.get("f6", 0)
        if isinstance(amount, (int, float)) and amount < 5_000_000:
            return False

        return True

    # ── 网络 ──────────────────────────────────────────────────────────────

    def _fetch_rank(self, fid: str, po: int, pz: int) -> list[dict]:
        """拉取单维度排行"""
        params = dict(BASE_PARAMS)
        params["fid"] = fid
        params["po"]  = str(po)
        params["pz"]  = str(pz)
        params["pn"]  = "1"

        url = self._build_url(params)
        data = self._http_get(url)
        if not data:
            return []

        rows = self._parse_response(data)
        time.sleep(FETCH_INTERVAL)
        return rows

    @staticmethod
    def _build_url(params: dict) -> str:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{CLIST_URL}?{query}"

    @staticmethod
    def _http_get(url: str) -> Optional[str]:
        """GET 请求，返回原始 JSON 文本"""
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

    @staticmethod
    def _parse_response(text: str) -> list[dict]:
        """解析 clist JSONP/JSON 响应"""
        # 有时返回 JSONP 包装: jQuery(...{...})
        if not text:
            return []

        # 尝试去掉 JSONP 回调
        if text.startswith("jQuery") or text.startswith("callback"):
            start = text.find("(")
            end   = text.rfind(")")
            if start != -1 and end != -1:
                text = text[start + 1 : end]

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return []

        if not isinstance(obj, dict):
            return []
        data = obj.get("data")
        if not isinstance(data, dict):
            return []
        diff = data.get("diff", [])
        if not isinstance(diff, list):
            return []
        return diff


# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

def run_discovery() -> list[dict]:
    """一次完整的发现流程"""
    engine = EastMoneyDiscovery()
    return engine.discover()


# ---------------------------------------------------------------------------
# 独立测试
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cands = run_discovery()
    print(f"candidates: {len(cands)}")
    print()
    for c in cands[:5]:
        reasons = ", ".join(c["reasons"])
        print(f"  {c['symbol']} {c['name']}  [{reasons}]")
        m = c["metrics"]
        print(f"    成交额={m.get('amount',0):,.0f}  "
              f"涨幅={m.get('change_pct',0):+.2f}%  "
              f"换手={m.get('turnover_pct',0):.2f}%")
    print(f"\n... (共 {len(cands)} 只候选)")
