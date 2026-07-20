"""market/discovery/admission.py — Admission Filter 准入过滤器

职责：
  对 Discovery candidate list 执行准入判断。
  回答：哪些候选值得消耗后续行情采集资源。
  不做交易评分，不自动替换 active pool。

输入：  candidate list（来自 discovery/eastmoney.py）
输出：  observation pool（admitted=True/False + 原因标签）

当前版本：
  第一版 — 只做准入，不做交易评分。
  暂不引入：自动换池、自动买卖、修改 V2。
"""

import json
import time
from typing import Optional

# ---------------------------------------------------------------------------
# 配置（可调阈值）
# ---------------------------------------------------------------------------

THRESHOLDS = {
    # 流动性
    "min_amount":         50_000_000,   # 最低成交额 5000 万
    "min_price":          5.0,          # 最低价
    "max_st_price":       10.0,         # ST/风险警示价（配合名称过滤）

    # 趋势
    "min_momentum_20d":   -10.0,        # 20日涨幅下限（>-10% 不处于深跌）

    # 波动
    "min_amplitude":      1.5,          # 最低振幅 %
    "max_amplitude":      20.0,         # 最高振幅 %（排除异常波动）
    "min_turnover":       0.3,          # 最低换手率 %

    # 异常排除
    "spike_change":       15.0,         # 单日涨幅超过此值视为异常脉冲
    "spike_amount_ratio": 0.3,          # 脉冲时成交额低于均值的倍数阈值
}

# ---------------------------------------------------------------------------
# 准入检查（逐项，返回 pass/fail + 标签）
# ---------------------------------------------------------------------------


def check_liquidity(m: dict) -> tuple[bool, str]:
    """流动性检查"""
    amount = m.get("amount", 0)
    price  = m.get("price", m.get("close", 0))

    if not amount or amount < THRESHOLDS["min_amount"]:
        return False, "liquidity_low"
    if isinstance(price, (int, float)) and price > 0 and price < THRESHOLDS["min_price"]:
        return False, "price_too_low"
    return True, "liquidity_ok"


def check_trend(m: dict) -> tuple[bool, str]:
    """趋势基础检查"""
    mom = m.get("momentum_20d_pct", None)

    # 无 20d 数据的视为中性（New上市等）, 不因无数据拒入
    if mom is None or mom == 0:
        return True, "trend_neutral"

    if isinstance(mom, (int, float)) and mom < THRESHOLDS["min_momentum_20d"]:
        return False, "trend_decline"

    # 趋势质量正向加分
    if mom > 5:
        return True, "trend_uptrend"
    if mom > 0:
        return True, "trend_neutral"
    return True, "trend_weak"


def check_volatility(m: dict) -> tuple[bool, str]:
    """波动质量检查（突破策略需要合适波动）"""
    amp     = m.get("amplitude_pct", 0)
    turnover = m.get("turnover_pct", 0)

    # 活水不足
    if isinstance(amp, (int, float)) and amp < THRESHOLDS["min_amplitude"]:
        return False, "volatility_dead"

    # 异常剧烈
    if isinstance(amp, (int, float)) and amp > THRESHOLDS["max_amplitude"]:
        return False, "volatility_wild"

    # 零换手
    if isinstance(turnover, (int, float)) and turnover < THRESHOLDS["min_turnover"]:
        return False, "no_turnover"

    # 有量有波动 → 适合突破
    if isinstance(amp, (int, float)) and amp > 3:
        return True, "volatility_good"
    return True, "volatility_ok"


def check_spike(m: dict) -> tuple[bool, str]:
    """异常脉冲排除"""
    change = m.get("change_pct", 0)
    amount = m.get("amount", 0)

    # 一日脉冲：涨幅异常 + 成交额未匹配
    if isinstance(change, (int, float)) and abs(change) > THRESHOLDS["spike_change"]:
        if amount < THRESHOLDS["min_amount"] * 2:
            return False, "spike_excluded"
    return True, "no_spike"


def check_capital_flow(m: dict) -> tuple[bool, str]:
    """资金流（仅加分，不作为否决项）"""
    flow = m.get("capital_flow", None)
    if flow is None:
        return True, "flow_unknown"
    if isinstance(flow, (int, float)) and flow > 0:
        return True, "flow_positive"
    return True, "flow_neutral"


# ---------------------------------------------------------------------------
# 准入过滤器
# ---------------------------------------------------------------------------

ADMISSION_CHECKS = [
    ("liquidity",    check_liquidity),     # 硬条件：流动性不足不采集
    ("trend",        check_trend),         # 硬条件：深跌趋势不浪费资源
    ("volatility",   check_volatility),    # 硬条件：死股/异常波动不进入
    ("spike",        check_spike),         # 硬条件：一日脉冲不跟
    # 注：资金流(capital_flow)是评分因子，不是准入硬条件，移至 Scoring 层
]


TRACE_DATE = None  # 在同一天内复用，避免重复 strftime


def _trace_date() -> str:
    global TRACE_DATE
    if TRACE_DATE is None:
        TRACE_DATE = time.strftime("%Y%m%d")
    return TRACE_DATE


_TRACE_COUNTER: int = 0


def _next_trace_id(symbol: str) -> str:
    """生成 trace_id: {symbol}-{YYYYMMDD}-{seq}
    seq 为 3 位流水号，确保同日内唯一。
    """
    global _TRACE_COUNTER
    _TRACE_COUNTER += 1
    return f"{symbol}-{_trace_date()}-{_TRACE_COUNTER:03d}"


def _reset_trace_counter():
    global _TRACE_COUNTER
    _TRACE_COUNTER = 0


def admit_candidate(cand: dict, assign_trace: bool = False) -> dict:
    """对单个候选执行准入判断

    Parameters
    ----------
    cand : dict
        来自 Discovery 的候选
    assign_trace : bool
        通过时是否分配 trace_id（仅 admission pass 时分配）
    """
    metrics = cand.get("metrics", {})
    admitted = True
    check_results = {}

    for check_name, check_fn in ADMISSION_CHECKS:
        passed, label = check_fn(metrics)
        check_results[check_name] = {
            "passed": passed,
            "label": label,
        }
        if not passed:
            admitted = False

    # 准入原因（通过的检查标签）
    reasons = [
        r["label"]
        for r in check_results.values()
        if r["passed"]
    ]
    # 否决原因（未通过的检查标签）
    reject_reasons = [
        r["label"]
        for r in check_results.values()
        if not r["passed"]
    ]

    # filters 展开：每项检查独立记录
    filters = {}
    for check_name, cr in check_results.items():
        filters[check_name] = {
            "passed": cr["passed"],
            "tag": cr["label"],
        }

    result = {
        "symbol":        cand["symbol"],
        "name":          cand.get("name", ""),
        "pool_stage":    "admission",  # L1 标识
        "admitted":      admitted,
        "reasons":       reasons,       # 保留（兼容）
        "reject_reason": reject_reasons if reject_reasons else None,
        "filters":       filters,       # 展开的过滤明细
        "metrics":       metrics,       # L0 事实快照
        "discovery": {
            "reasons":   cand.get("reasons", []),
            "dimensions": cand.get("source_dimensions", []),
        },
        "checked_at":    time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
    }

    if admitted and assign_trace:
        result["trace_id"] = _next_trace_id(cand["symbol"])

    return result


def filter_observation_pool(candidates: list[dict]) -> dict:
    """批量准入，返回全量 Admission Pool（L1）

    不做截断。容量限制在后续 Scoring → Candidate Pool（L3）层。
    通过 L1 的候选获得 trace_id。
    """
    _reset_trace_counter()
    admitted = []
    rejected = []

    for c in candidates:
        # 通过时分配 trace_id
        result = admit_candidate(c, assign_trace=True)
        if result["admitted"]:
            admitted.append(result)
        else:
            rejected.append(result)

    # 排序：按命中维度数 desc + 成交额 desc（便于查看，非截断依据）
    def sort_key(x):
        dims = -len(x["discovery"]["reasons"])
        amt = 0
        if "metrics" in x:
            amt = x["metrics"].get("amount", 0)
            if not isinstance(amt, (int, float)):
                amt = 0
        return (dims, -amt)

    admitted.sort(key=sort_key)

    return {
        "admitted_count":     len(admitted),
        "rejected_count":     len(rejected),
        "total_candidates":   len(candidates),
        "admission_pool":     admitted,     # L1：全量通过基础过滤
        "rejected_pool":      rejected,
        "filtered_at":        time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "trace_start":        admitted[0]["trace_id"] if admitted else None,
        "trace_end":          admitted[-1]["trace_id"] if admitted else None,
    }


# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

def run_admission(candidates: list[dict]) -> dict:
    """完整准入流程（L0 → L1）"""
    return filter_observation_pool(candidates)


def write_l0_scan(candidates: list[dict], path: str = None) -> str:
    """将 L0 原始扫描结果写入 JSON

    不判断好坏，只保存接口事实。
    """
    if path is None:
        import os
        _dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_dir, "l0_scan.json")

    ts = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())
    data = {
        "version": 1,
        "pool_stage": "scan",
        "generated_at": ts,
        "total": len(candidates),
        "description": "L0 Scan: 原始行情事实，不做判断",
        "symbols": [c["symbol"] for c in candidates],
        "details": [
            {
                "symbol": c["symbol"],
                "name": c.get("name", ""),
                "metrics": dict(c.get("metrics", {})),
                "discovery_tags": c.get("source_dimensions", c.get("reasons", [])),
            }
            for c in candidates
        ],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def write_l1_admission(result: dict, path: str = None, source_snapshot: str = None) -> str:
    """将 Admission Pool（L1）写入 JSON 文件

    全量输出，不做截断。容量控制由后续 Scoring → Candidate Pool (L3) 负责。
    每只通过股票带 trace_id，生命周期可追踪。

    Parameters
    ----------
    source_snapshot : str
        引用 L0 快照标识，保证 L2 评分使用同一数据快照。
    """
    if path is None:
        import os
        _dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_dir, "admission_pool.json")

    pool_data = {
        "version": 1,
        "pool_stage": "admission",
        "generated_by": "admission_filter",
        "generated_at": result["filtered_at"],
        "source_snapshot": source_snapshot or f"l0_scan_{time.strftime('%Y%m%d_%H%M%S')}",
        "total_candidates": result["total_candidates"],
        "admitted_count": result["admitted_count"],
        "rejected_count": result["rejected_count"],
        "trace_start": result.get("trace_start"),
        "trace_end": result.get("trace_end"),
        "description": "Admission Pool (L1): 全量通过基础过滤，等待评分",
        "symbols": [c["symbol"] for c in result["admission_pool"]],
        "details": [
            {
                "symbol": c["symbol"],
                "name": c["name"],
                "pool_stage": c.get("pool_stage", "admission"),
                "trace_id": c.get("trace_id"),
                "admitted": c["admitted"],
                "filters": c.get("filters", {}),
                "admission_reasons": c["reasons"],
                "discovery_tags": c["discovery"]["reasons"],
            }
            for c in result["admission_pool"]
        ],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(pool_data, f, ensure_ascii=False, indent=2)

    return path


def write_l2_scoring_stub(path: str = None) -> str:
    """L2 Scoring 数据结构定义（占位，待评分模型实现后填充）

    Scoring Pool 不重新过滤，只对 L1 进行评分增强。
    """
    if path is None:
        import os
        _dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_dir, "scoring_pool.json")

    data = {
        "version": 1,
        "pool_stage": "scoring",
        "generated_at": None,
        "description": "Scoring Pool (L2): 评分层 - 待实现",
        "expected_fields": {
            "symbol": "股票代码",
            "pool_stage": "'scoring'",
            "trace_id": "继承自 L1",
            "base": {
                "pool_stage": "'scoring'",
                "admission": True,
            },
            "factors": {
                "money_flow": "0-100, 资金流向评分",
                "trend_quality": "0-100, 趋势质量评分",
                "volume_quality": "0-100, 量价结构评分",
                "price_structure": "0-100, 价格形态评分",
            },
            "score": "综合评分 0-100",
        },
        "details": [],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def write_l3_candidate_stub(path: str = None) -> str:
    """L3 Candidate 数据结构定义（占位）

    Candidate Pool = Scoring Pool score 排名后按容量截断。
    """
    if path is None:
        import os
        _dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(_dir, "candidate_pool.json")

    data = {
        "version": 1,
        "pool_stage": "candidate",
        "generated_at": None,
        "description": "Candidate Pool (L3): 容量控制后的候选池",
        "expected_fields": {
            "candidate_rank": "排名",
            "symbol": "股票代码",
            "pool_stage": "'candidate'",
            "trace_id": "继承自 L1",
            "score": "综合评分",
        },
        "details": [],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


# ---------------------------------------------------------------------------
# 独立测试
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from .eastmoney import run_discovery

    cands = run_discovery()
    print(f"发现候选: {len(cands)}")

    result = run_admission(cands)
    print(f"准入通过: {result['admitted_count']}")
    print(f"准入拒绝: {result['rejected_count']}")
    print()

    # 展示 admission pool 前 10
    print("--- Admission Pool (L1) top 10 ---")
    for c in result["admission_pool"][:10]:
        print(f"  {c['symbol']} {c['name']}  [{' '.join(c['reasons'])}]")

    print()
    # 展示拒绝的前 5
    print("--- rejected (top 5) ---")
    for c in result["rejected_pool"][:5]:
        print(f"  {c['symbol']} {c['name']}  ❌ {' '.join(c['reject_reason'])}")

    print()
    # 写入各层
    l0_path = write_l0_scan(cands)
    l1_path = write_l1_admission(result, source_snapshot=f"l0_scan_{time.strftime('%Y%m%d_%H%M%S')}")
    l2_path = write_l2_scoring_stub()
    l3_path = write_l3_candidate_stub()
    print(f"L0 → {l0_path}")
    print(f"L1 → {l1_path}")
    print(f"L2 → {l2_path} (待实现)")
    print(f"L3 → {l3_path} (待实现)")
