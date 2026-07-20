"""market/discovery/candidate.py — L3 候选池决策层

职责：
  在 L2 评分基础上执行三层候选资格判断：
    Gate 1: Risk Gate（硬性淘汰）
    Gate 2: Factor Balance（因子平衡检查）
    Gate 3: Capacity Selection（容量选择）
  输出 candidate_pool.json，包含全量 114 支的决策记录。

L3 设计原则：
  不修改 L2 评分，不删除数据；
  全量保留决策过程（淘汰原因+通过的检查节点）；
  selected 子集 ⊆ L2 Scoring Pool。

Gate 规则（可配置）：
  Risk Gate:
    - score < min_score → reject: score_below_50
    - trend_quality < min_trend → reject: trend_quality_low
    - volatility_quality < min_volatility → reject: volatility_quality_low
  Factor Balance:
    - 5 个因子中至少 N 个 >= 50，否则 reject: factor_imbalance
  Capacity:
    - 通过前两门的按 score DESC 取 Top-N
    - 未进入容量的标记为 capacity_overflow（不视为淘汰）
"""

import json
import os
import time
from typing import Optional

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCORING_PATH  = os.path.join(BASE_DIR, "scoring_pool.json")
OUTPUT_PATH   = os.path.join(BASE_DIR, "candidate_pool.json")

# Gate 默认配置
GATE_CONFIG = {
    "risk_gate": {
        "min_score":               50.0,
        "min_trend_quality":       40.0,
        "min_volatility_quality":  30.0,
    },
    "factor_balance": {
        "factor_names": ["trend_quality", "money_flow", "volume_quality",
                         "volatility_quality", "price_structure"],
        "min_factors_above_50": 4,
    },
    "capacity": {
        "max_selected": 50,
    },
}


# ---------------------------------------------------------------------------
# 门 1: Risk Gate — 硬性淘汰
# ---------------------------------------------------------------------------

_risk_checks = [
    ("score_below_50",              lambda d: d["score"] < GATE_CONFIG["risk_gate"]["min_score"]),
    ("trend_quality_low",           lambda d: d["factors"]["trend_quality"] < GATE_CONFIG["risk_gate"]["min_trend_quality"]),
    ("volatility_quality_low",      lambda d: d["factors"]["volatility_quality"] < GATE_CONFIG["risk_gate"]["min_volatility_quality"]),
]

def _check_risk_gate(entry: dict) -> tuple[bool, list[str]]:
    """返回 (passed, reasons)"""
    reasons = []
    for tag, check_fn in _risk_checks:
        if check_fn(entry):
            reasons.append(tag)
    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# 门 2: Factor Balance — 因子平衡检查
# ---------------------------------------------------------------------------

def _check_factor_balance(entry: dict) -> tuple[bool, int, Optional[str]]:
    """返回 (passed, qualified_count, reason)"""
    factors = entry.get("factors", {})
    factor_names = GATE_CONFIG["factor_balance"]["factor_names"]
    min_above = GATE_CONFIG["factor_balance"]["min_factors_above_50"]

    qualified = 0
    for name in factor_names:
        if factors.get(name, 0) >= 50.0:
            qualified += 1

    if qualified >= min_above:
        return True, qualified, None
    else:
        return False, qualified, "factor_imbalance"


# ---------------------------------------------------------------------------
# 门 3: Capacity Selection — 容量选择
# ---------------------------------------------------------------------------

def _select_capacity(passed_entries: list[dict], max_n: int) -> tuple[list[dict], list[dict]]:
    """返回 (selected, overflow)"""
    # 已按 score DESC 排序
    selected = passed_entries[:max_n]
    overflow = passed_entries[max_n:]
    return selected, overflow


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def evaluate_candidates(
    scoring_path: str = SCORING_PATH,
    output_path: str = OUTPUT_PATH,
    max_selected: int = None,
) -> int:
    """执行 L3 候选决策

    Returns: 最终选入候选池的数量
    """
    if max_selected is not None:
        GATE_CONFIG["capacity"]["max_selected"] = max_selected

    # 1. 加载 L2 评分池
    with open(scoring_path, "r", encoding="utf-8") as f:
        scoring_data = json.load(f)

    source_snapshot = scoring_data.get("source_snapshot", "")
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

    details = scoring_data.get("details", [])

    # 2. 逐条评估
    passed_gate1 = []   # 通过风险门
    passed_gate2 = []   # 通过因子平衡门
    all_results  = []

    for d in details:
        entry = {
            "symbol":   d["symbol"],
            "name":     d.get("name", ""),
            "trace_id": d.get("trace_id", ""),
            "score":    d["score"],
            "factors":  d["factors"],
        }

        # Gate 1: Risk
        risk_passed, risk_reasons = _check_risk_gate(entry)
        gate1_result = {
            "passed":   risk_passed,
            "reasons":  risk_reasons if not risk_passed else [],
        }

        # Gate 2: Factor Balance (仅在通过 Gate 1 后检查)
        if risk_passed:
            bal_passed, bal_count, bal_reason = _check_factor_balance(entry)
            gate2_result = {
                "passed":            bal_passed,
                "qualified_factors": bal_count,
                "reasons":           [bal_reason] if not bal_passed else [],
            }
        else:
            gate2_result = {"passed": False, "qualified_factors": 0, "reasons": []}

        # 统计
        if risk_passed and bal_passed:
            passed_gate2.append(entry)

        entry["gate_results"] = {
            "risk_gate":       gate1_result,
            "factor_balance":  gate2_result,
        }
        all_results.append(entry)

    # 3. 按 score DESC 排序后再执行容量选择
    passed_gate2.sort(key=lambda x: -x["score"])
    max_n = GATE_CONFIG["capacity"]["max_selected"]
    selected, overflow = _select_capacity(passed_gate2, max_n)

    selected_syms = set(e["symbol"] for e in selected)
    overflow_syms = set(e["symbol"] for e in overflow)

    # 4. 构建最终详情
    final_details = []
    for entry in all_results:
        sym = entry["symbol"]

        risk_pass  = entry["gate_results"]["risk_gate"]["passed"]
        bal_pass   = entry["gate_results"]["factor_balance"]["passed"]

        if sym in selected_syms:
            # 通过三门，获选
            cap_rank = next(i+1 for i, e in enumerate(selected) if e["symbol"] == sym)
            status = "selected"
            reject_reasons = []
            entry["gate_results"]["capacity_gate"] = {"passed": True, "rank": cap_rank}
            selection = {"passed_gate": True, "capacity_rank": cap_rank}

        elif risk_pass and bal_pass:
            # 通过前两门但超出容量
            status = "overflow"
            reject_reasons = []
            entry["gate_results"]["capacity_gate"] = {"passed": False, "reason": "capacity_limit"}
            selection = {
                "passed_gate": True,
                "capacity_rank": None,
                "overflow_reason": "capacity_limit",
            }

        else:
            # 被前两门之一淘汰
            status = "rejected"
            reject_reasons = []
            if not risk_pass:
                reject_reasons.extend(entry["gate_results"]["risk_gate"]["reasons"])
            if not bal_pass:
                reject_reasons.extend(entry["gate_results"]["factor_balance"]["reasons"])
            entry["gate_results"]["capacity_gate"] = {"passed": False, "reason": "gate_blocked"}
            selection = {"passed_gate": False, "capacity_rank": None}

        entry["candidate_status"] = status
        entry["reject_reason"] = reject_reasons if reject_reasons else None
        entry["selection"] = selection

        final_entry = {
            "symbol":           entry["symbol"],
            "name":             entry["name"],
            "trace_id":         entry["trace_id"],
            "score":            entry["score"],
            "factors":          entry["factors"],
            "candidate_status": entry["candidate_status"],
            "reject_reason":    entry["reject_reason"],
            "selection":        entry["selection"],
            "gate_results":     entry["gate_results"],
        }
        final_details.append(final_entry)

    # 5. 输出统计
    total   = len(details)
    g1_pass = sum(1 for d in all_results if d["gate_results"]["risk_gate"]["passed"])
    g2_pass = len(passed_gate2)
    sel_cnt = len(selected)
    rej_cnt = total - sel_cnt
    overflow_cnt = len(overflow)
    g1_fail = total - g1_pass
    g2_fail = g1_pass - g2_pass

    print(f"candidate_pool: {total} evaluated")
    print(f"  Gate1 Risk:       {g1_pass}/{total} passed  ({g1_fail} rejected)")
    print(f"  Gate2 Balance:    {g2_pass}/{g1_pass} passed  ({g2_fail} rejected)")
    print(f"  Gate3 Capacity:   {sel_cnt} selected (max={max_n})")
    print(f"    - overflow:     {overflow_cnt} (passed gates, exceeded capacity)")
    print(f"  Total rejected:   {rej_cnt}")
    print(f"  Final selected:   {sel_cnt}")

    # 6. 写入
    output = {
        "version": 1,
        "pool_stage": "candidate",
        "generated_at": generated_at,
        "source_snapshot": source_snapshot,
        "description": "L3 候选池：三层 Gate 决策（风险门 + 因子平衡 + 容量选择）",
        "gate_config": GATE_CONFIG,
        "total_submitted": total,
        "risk_gate_passed": g1_pass,
        "balance_gate_passed": g2_pass,
        "total_selected": sel_cnt,
        "total_rejected": total - sel_cnt,
        "symbols": [d["symbol"] for d in final_details],
        "details": final_details,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  → {output_path}")
    return sel_cnt


# ---------------------------------------------------------------------------
# 独立入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    evaluate_candidates()
