"""market/discovery/scoring.py — L2 评分池

职责：
  消费 L0 原始事实 + Kline 事实 + Flow 事实，
  对每只 L1 准入股票计算 5 因子评分，
  按固定权重生成总分与排名，
  输出 scoring_pool.json。

评分模型 v1：
  总分 = 趋势质量×25% + 资金质量×25% + 成交质量×20% + 波动质量×15% + 结构质量×15%
  满分 100，全部为排序因子（无淘汰）。

数据契约：
  - 输入：l0_scan.json + kline_snapshot.json + flow_snapshot.json（只读）
  - 输出：scoring_pool.json（L3 消费）
  - 输出范围 = L1 Admission Pool 全量，不截断
  - 不修改任何输入数据
"""

import json
import os
import time
from typing import Optional

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

L0_PATH      = os.path.join(BASE_DIR, "l0_scan.json")
KLINE_PATH   = os.path.join(BASE_DIR, "kline_snapshot.json")
FLOW_PATH    = os.path.join(BASE_DIR, "flow_snapshot.json")
OUTPUT_PATH  = os.path.join(BASE_DIR, "scoring_pool.json")

# 固定权重（总和 = 1.0）
WEIGHTS = {
    "trend_quality":     0.25,
    "money_flow":        0.25,
    "volume_quality":    0.20,
    "volatility_quality": 0.15,
    "price_structure":   0.15,
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _num(v, default=0.0) -> float:
    """安全数值转换"""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (ValueError, TypeError):
        return default

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _build_index(details: list[dict], key: str = "symbol") -> dict:
    """构建 symbol → record 的快速索引"""
    return {d.get(key, ""): d for d in details}


# ---------------------------------------------------------------------------
# 因子: 趋势质量 Trend Quality (25分权重)
# ---------------------------------------------------------------------------

def _score_trend_quality(d0: dict, dk: dict) -> float:
    """
    子因子（权重占比按 40%:32%:28%）：
      MA5 > MA20         (10/25)
      20d 涨跌幅稳定     (8/25)
      价格位置           (7/25)
    """
    # --- A: MA 排列质量 ---
    ma5  = _num(dk.get("ma5"))
    ma20 = _num(dk.get("ma20"))

    if ma5 and ma20 and ma20 > 0:
        ma_ratio = ma5 / ma20  # >1 = 多头排列
        if ma_ratio >= 1.05:
            ma_score = 100.0
        elif ma_ratio >= 1.0:
            ma_score = 50.0 + (ma_ratio - 1.0) / 0.05 * 50.0  # 50→100
        else:
            ma_score = max(0.0, 50.0 + (ma_ratio - 1.0) / 0.05 * 25.0)  # 0→50
    else:
        ma_score = 50.0  # 无数据时中性

    # --- B: 20 日涨跌幅稳定性 ---
    mom = _num(d0.get("momentum_20d_pct"))
    if mom > 0:
        mom_score = _clamp(50.0 + mom * 2.0)  # +10% → 70, +25% → 100
    elif mom < 0:
        mom_score = _clamp(50.0 + mom * 1.5)  # -10% → 35, -33% → 0
    else:
        mom_score = 50.0

    # --- C: 价格位置（当前价在 20 日区间的位置）---
    bars = dk.get("bars", {})
    high_20d = _num(dk.get("high_20d"))
    low_20d  = _num(dk.get("low_20d"))

    if bars and high_20d and low_20d and (high_20d - low_20d) > 0.001:
        # 取最新 bar 收盘价
        bar_vals = list(bars.values())
        close = _num(bar_vals[-1].get("close", 0))
        position = (close - low_20d) / (high_20d - low_20d) * 100.0
        pos_score = _clamp(position)
    else:
        pos_score = 50.0

    # 加权总分
    score = ma_score * 0.40 + mom_score * 0.32 + pos_score * 0.28
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# 因子: 资金质量 Money Flow (25分权重)
# ---------------------------------------------------------------------------

def _score_money_flow(df: dict) -> float:
    """
    子因子：
      主力资金方向        (10/25)
      持续性             (8/25)
      资金强度占比       (7/25)
    """
    # --- A: 主力方向 ---
    ratio = _num(df.get("main_ratio_pct"))
    if ratio > 0:
        dir_score = _clamp(50.0 + ratio * 3.0)  # +5% → 65, +17% → 100
    elif ratio < 0:
        dir_score = _clamp(50.0 + ratio * 3.0)  # -5% → 35, -17% → 0
    else:
        dir_score = 50.0

    # --- B: 持续性 ---
    consec = _num(df.get("consecutive_days"), 0)
    if consec > 0:
        consec_score = _clamp(50.0 + consec * 10.0)  # +1d→60, +5d→100
    elif consec < 0:
        consec_score = _clamp(50.0 + consec * 10.0)  # -1d→40, -5d→0
    else:
        consec_score = 50.0

    # --- C: 平均强度（20 日均值） ---
    avg_ratio = _num(df.get("avg_main_ratio_20d"))
    if avg_ratio > 0:
        avg_score = _clamp(50.0 + avg_ratio * 3.0)  # +5% → 65
    elif avg_ratio < 0:
        avg_score = _clamp(50.0 + avg_ratio * 3.0)  # -5% → 35
    else:
        avg_score = 50.0

    score = dir_score * 0.40 + consec_score * 0.32 + avg_score * 0.28
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# 因子: 成交质量 Volume Quality (20分权重)
# ---------------------------------------------------------------------------

def _score_volume_quality(d0: dict) -> float:
    """
    子因子：
      成交量稳定性      (8/20)
      价量配合          (7/20)
      换手健康度        (5/20)
    """
    vol_ratio     = _num(d0.get("vol_ratio"))
    change_pct    = _num(d0.get("change_pct"))
    turnover_pct  = _num(d0.get("turnover_pct"))

    # --- A: 成交量稳定性 ---
    if vol_ratio > 0:
        # 理想区间 0.8~2.0, 峰值 1.0~1.5
        if vol_ratio <= 0.5:
            vol_stable = 10.0
        elif vol_ratio <= 1.0:
            vol_stable = 10.0 + (vol_ratio - 0.5) / 0.5 * 70.0  # 10→80
        elif vol_ratio <= 1.5:
            vol_stable = 80.0 + (vol_ratio - 1.0) / 0.5 * 20.0  # 80→100
        elif vol_ratio <= 2.0:
            vol_stable = 100.0 - (vol_ratio - 1.5) / 0.5 * 20.0  # 100→80
        elif vol_ratio <= 3.0:
            vol_stable = 80.0 - (vol_ratio - 2.0) / 1.0 * 30.0  # 80→50
        elif vol_ratio <= 5.0:
            vol_stable = 50.0 - (vol_ratio - 3.0) / 2.0 * 30.0  # 50→20
        else:
            vol_stable = max(5.0, 20.0 - (vol_ratio - 5.0) * 5.0)  # 20→0
    else:
        vol_stable = 50.0

    # --- B: 价量配合 ---
    if change_pct > 0 and vol_ratio > 1.2:
        # 上涨放量 → 买入确认
        pv_score = _clamp(70.0 + change_pct * 2.0)
    elif change_pct > 0 and vol_ratio >= 0.7:
        # 上涨正常量
        pv_score = _clamp(50.0 + change_pct * 1.5)
    elif change_pct > 0:
        # 上涨缩量 → 强度不足
        pv_score = _clamp(30.0 + change_pct * 1.0)
    elif change_pct <= 0 and vol_ratio > 1.2:
        # 下跌放量 → 卖出压力
        pv_score = _clamp(30.0 + change_pct * 2.0)  # change_pct 负值拉低
    elif change_pct <= 0 and vol_ratio >= 0.7:
        # 下跌正常量
        pv_score = _clamp(40.0 + change_pct * 1.5)
    else:
        # 下跌缩量 → 无抛售
        pv_score = _clamp(50.0 + change_pct * 1.0)

    # --- C: 换手健康度 ---
    if turnover_pct <= 0.5:
        tr_score = turnover_pct * 20.0  # 0→10
    elif turnover_pct <= 1.0:
        tr_score = 10.0 + (turnover_pct - 0.5) / 0.5 * 20.0  # 10→30
    elif turnover_pct <= 2.0:
        tr_score = 30.0 + (turnover_pct - 1.0) / 1.0 * 20.0  # 30→50
    elif turnover_pct <= 5.0:
        tr_score = 50.0 + (turnover_pct - 2.0) / 3.0 * 30.0  # 50→80
    elif turnover_pct <= 10.0:
        tr_score = 80.0 + (turnover_pct - 5.0) / 5.0 * 20.0  # 80→100
    elif turnover_pct <= 20.0:
        tr_score = 100.0 - (turnover_pct - 10.0) / 10.0 * 30.0  # 100→70
    else:
        tr_score = max(10.0, 70.0 - (turnover_pct - 20.0) * 2.0)  # 70→10

    score = vol_stable * 0.40 + pv_score * 0.35 + tr_score * 0.25
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# 因子: 波动质量 Volatility Quality (15分权重)
# ---------------------------------------------------------------------------

def _score_volatility_quality(d0: dict, dk: dict) -> float:
    """
    子因子：
      适中的振幅          (8/15)
      波动稳定性          (7/15)
    """
    amp_today  = _num(d0.get("amplitude_pct"))
    amp_avg_20d = _num(dk.get("amplitude_avg_20d"))

    # --- A: 振幅适中 ---
    # 使用日均振幅（20 日均值）更稳定
    avg_amp = amp_avg_20d if amp_avg_20d > 0 else amp_today
    if avg_amp <= 0:
        amp_score = 50.0
    elif avg_amp <= 2.0:
        amp_score = 10.0 + (avg_amp / 2.0) * 30.0  # 0→40
    elif avg_amp <= 4.0:
        amp_score = 40.0 + (avg_amp - 2.0) / 2.0 * 25.0  # 40→65
    elif avg_amp <= 7.0:
        amp_score = 65.0 + (avg_amp - 4.0) / 3.0 * 25.0  # 65→90 (理想区)
    elif avg_amp <= 10.0:
        amp_score = 90.0 - (avg_amp - 7.0) / 3.0 * 30.0  # 90→60
    else:
        amp_score = max(0.0, 60.0 - (avg_amp - 10.0) * 5.0)  # 60→0

    # --- B: 波动稳定性（当日 vs 20 日均值）---
    if amp_avg_20d > 0 and amp_today > 0:
        ratio = amp_today / amp_avg_20d
        # ratio ~ 1 → 稳定 ; 偏离大 → 不稳定
        deviation = abs(ratio - 1.0)
        stable_score = _clamp(100.0 - deviation * 60.0)
        # ratio 1.0 → 100; 0.5→70; 2.0→40; 3.0→0
    else:
        stable_score = 50.0

    score = amp_score * 0.53 + stable_score * 0.47
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# 因子: 结构质量 Price Structure (15分权重)
# ---------------------------------------------------------------------------

def _score_price_structure(dk: dict) -> float:
    """
    子因子：
      突破接近度          (8/15)
      K 线结构           (7/15)
    """
    bars = dk.get("bars", {})
    high_20d = _num(dk.get("high_20d"))
    low_20d  = _num(dk.get("low_20d"))

    if not bars:
        return 50.0

    bar_vals = list(bars.values())
    latest   = bar_vals[-1]

    latest_close = _num(latest.get("close", 0))
    latest_open  = _num(latest.get("open", 0))
    latest_high  = _num(latest.get("high", 0))
    latest_low   = _num(latest.get("low", 0))

    # --- A: 突破接近度 ---
    if high_20d and low_20d and (high_20d - low_20d) > 0.001:
        pos_ratio = (latest_close - low_20d) / (high_20d - low_20d) * 100.0
        bp_score = _clamp((pos_ratio - 30.0) / 70.0 * 100.0)  # 在区间 30%~100% 之间线性映射到 0~100
        # 即 30% 位置 → 0, 65% → 50, 100% → 100
    else:
        bp_score = 50.0

    # --- B: K 线结构（最新 bar）---
    bar_range = latest_high - latest_low
    if bar_range > 0.001:
        close_in_range = (latest_close - latest_low) / bar_range * 100.0
        body_pct = abs(latest_close - latest_open) / bar_range * 100.0

        if latest_close > latest_open:  # 阳线
            # 实体大 + 阳线高收 → 强
            k_score = close_in_range * 0.6 + body_pct * 0.4
        elif latest_close < latest_open:  # 阴线
            # 实体小 + 下影线 → 可接受 ; 实体大 + 近低收 → 差
            tail_bottom = 100.0 - close_in_range
            k_score = tail_bottom * 0.6 + (100.0 - body_pct) * 0.4
        else:
            k_score = 50.0
    else:
        k_score = 50.0

    k_score = _clamp(k_score)
    score = bp_score * 0.53 + k_score * 0.47
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# 评分入口
# ---------------------------------------------------------------------------

def score_all(
    l0_path: str = L0_PATH,
    kline_path: str = KLINE_PATH,
    flow_path: str = FLOW_PATH,
    output_path: str = OUTPUT_PATH,
) -> int:
    """对所有 L1 准入股票计算评分

    Returns: 成功评分数
    """
    # 1. 加载数据
    l0_data    = _load_json(l0_path)
    kline_data = _load_json(kline_path)
    flow_data  = _load_json(flow_path)

    l0_idx    = _build_index(l0_data.get("details", []))
    kline_idx = _build_index(kline_data.get("details", []))
    flow_idx  = _build_index(flow_data.get("details", []))

    # 取三方 symbol 交集 (应为 L1 全量)
    symbols = kline_data.get("symbols", [])  # 114 支
    source_snapshot = kline_data.get("source_snapshot", "")

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

    details = []
    for sym in symbols:
        d0  = l0_idx.get(sym, {})
        dk  = kline_idx.get(sym, {})
        df  = flow_idx.get(sym, {})

        # 提取基础信息
        metrics = d0.get("metrics", {})

        # 因子计算
        trend_f   = _score_trend_quality(metrics, dk)
        money_f   = _score_money_flow(df)
        volume_f  = _score_volume_quality(metrics)
        vola_f    = _score_volatility_quality(metrics, dk)
        struct_f  = _score_price_structure(dk)

        factors = {
            "trend_quality":     trend_f,
            "money_flow":        money_f,
            "volume_quality":    volume_f,
            "volatility_quality": vola_f,
            "price_structure":   struct_f,
        }

        total_score = (
            trend_f * WEIGHTS["trend_quality"]
            + money_f * WEIGHTS["money_flow"]
            + volume_f * WEIGHTS["volume_quality"]
            + vola_f * WEIGHTS["volatility_quality"]
            + struct_f * WEIGHTS["price_structure"]
        )

        details.append({
            "symbol": sym,
            "name": d0.get("name", "") or dk.get("name", ""),
            "trace_id": dk.get("trace_id", ""),
            "source_snapshot": source_snapshot,
            "factors": factors,
            "score": round(total_score, 2),
        })

    # 2. 按分数降序排名
    details.sort(key=lambda x: -x["score"])
    for i, d in enumerate(details):
        d["rank"] = i + 1

    # 3. 输出
    output = {
        "version": 1,
        "pool_stage": "scoring",
        "generated_at": generated_at,
        "source_snapshot": source_snapshot,
        "description": "L2 评分池：5 因子 × 固定权重，全量排名（不截断）",
        "weights": WEIGHTS,
        "symbol_count": len(details),
        "symbols": [d["symbol"] for d in details],
        "details": details,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"scoring_pool: {len(details)} symbols scored → {output_path}")
    print(f"  分数范围: {details[-1]['score']:.1f} ~ {details[0]['score']:.1f}")
    return len(details)


# ---------------------------------------------------------------------------
# 独立入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    score_all()
