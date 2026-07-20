#!/usr/bin/env python3
"""
Token Metrics Analyzer v1 — 每日衍生指标报告
读取 token-metrics.jsonl（每小时快照），产出趋势分析。

位置: scripts/analyze-token-metrics.py
输入: memory/data/system/token-metrics.jsonl
输出: memory/data/system/daily-token-report.jsonl (append-only)

不修改运行状态，不改配置，仅做离线推导。
"""
import json, os, sys
from datetime import datetime, timedelta
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "memory", "data", "system", "token-metrics.jsonl")
OUTPUT = os.path.join(BASE, "memory", "data", "system", "daily-token-report.jsonl")

def load_snapshots(path: str) -> list[dict]:
    """加载所有快照"""
    if not os.path.exists(path):
        return []
    snapshots = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                snapshots.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return snapshots

def compute_session_growth(snapshots: list[dict]) -> list[dict]:
    """计算 session 级别指标（单快照可独立计算）"""
    records = []
    for s in snapshots:
        ts = s.get("ts", "?")
        total_tok = s.get("total_tokens", 0)
        inp = s.get("input_tokens", 0)
        out = s.get("output_tokens", 0)
        cr = s.get("cache_read_tokens", 0)
        cw = s.get("cache_write_tokens", 0)
        sessions = s.get("sessions", 0)
        avg_ctx = s.get("avg_context_pct", 0)
        max_ctx = s.get("max_context_pct", 0)
        cache_eff = s.get("cache_efficiency", 0)

        # 成本估算（deepseek-v4-flash 公开定价）
        input_cost = inp * 0.14 / 1_000_000
        output_cost = out * 0.28 / 1_000_000
        cache_savings = cr * 0.028 / 1_000_000  # cache read 比 input 便宜
        estimated_cost = round(input_cost + output_cost, 6)
        cache_saved = round(cache_savings, 6)

        # 输入输出比
        io_ratio = round(inp / max(out, 1), 2)

        # 每 session 均值
        avg_tok_per_session = round(total_tok / max(sessions, 1)) if sessions else 0

        records.append({
            "ts": ts,
            "sessions": sessions,
            "total_tokens": total_tok,
            "avg_tokens_per_session": avg_tok_per_session,
            "input_output_ratio": io_ratio,
            "cache_efficiency": cache_eff,
            "avg_context_pct": avg_ctx,
            "max_context_pct": max_ctx,
            "estimated_cost_usd": estimated_cost,
            "cache_savings_usd": cache_saved,
        })
    return records

def compute_trends(snapshots: list[dict]) -> list[dict]:
    """计算跨快照趋势（需至少2个样本）"""
    if len(snapshots) < 2:
        return []

    trends = []

    for i in range(1, len(snapshots)):
        prev = snapshots[i-1]
        curr = snapshots[i]

        # 时间间隔
        try:
            t_prev = datetime.fromisoformat(prev["ts"].replace("+0800", "+08:00").replace("+", "+").replace("Z", "+00:00"))
            t_curr = datetime.fromisoformat(curr["ts"].replace("+0800", "+08:00").replace("+", "+").replace("Z", "+00:00"))
            gap_hours = (t_curr - t_prev).total_seconds() / 3600
        except (ValueError, KeyError):
            gap_hours = 1.0

        if gap_hours <= 0:
            continue

        # Token 增长率（总量/小时）
        prev_tok = prev.get("total_tokens", 0)
        curr_tok = curr.get("total_tokens", 0)
        tok_growth = max(curr_tok - prev_tok, 0)
        growth_rate = round(tok_growth / gap_hours, 0) if gap_hours else 0

        # Context 变化
        prev_ctx = prev.get("avg_context_pct", 0)
        curr_ctx = curr.get("avg_context_pct", 0)
        ctx_delta = round(curr_ctx - prev_ctx, 2)

        # Cache 效率趋势
        prev_ce = prev.get("cache_efficiency", 0)
        curr_ce = curr.get("cache_efficiency", 0)
        ce_delta = round(curr_ce - prev_ce, 4)

        # 总 tokens 变化（可能包含 compaction 导致的下降）
        tok_change = curr_tok - prev_tok
        compaction_suspected = tok_change < -5000 and gap_hours < 2

        trends.append({
            "ts_start": prev["ts"],
            "ts_end": curr["ts"],
            "gap_hours": round(gap_hours, 2),
            "token_growth_total": tok_growth,
            "token_growth_rate_per_hour": int(growth_rate),
            "context_pct_delta": ctx_delta,
            "cache_efficiency_delta": ce_delta,
            "compaction_suspected": compaction_suspected,
            "token_drop": int(tok_change) if tok_change < 0 else 0,
        })

    return trends

def compute_daily_summary(snapshots: list[dict], trends: list[dict]) -> dict:
    """计算日报摘要"""
    if not snapshots:
        return {"error": "no_data"}

    # 聚合
    first_ts = snapshots[0]["ts"][:10] if snapshots[0].get("ts") else "?"
    last_ts = snapshots[-1]["ts"][:10] if snapshots[-1].get("ts") else "?"

    total_sessions = max(s["sessions"] for s in snapshots) if snapshots else 0
    max_tokens = max(s["total_tokens"] for s in snapshots) if snapshots else 0
    avg_cache_eff = sum(s["cache_efficiency"] for s in snapshots) / max(len(snapshots), 1)
    avg_ctx = sum(s["avg_context_pct"] for s in snapshots) / max(len(snapshots), 1)
    max_ctx = max(s["max_context_pct"] for s in snapshots) if snapshots else 0

    total_input = max(s["input_tokens"] for s in snapshots) if "input_tokens" in (snapshots[-1] if snapshots else {}) else 0
    total_output = max(s["output_tokens"] for s in snapshots) if "output_tokens" in (snapshots[-1] if snapshots else {}) else 0

    # 成本
    latest = snapshots[-1] if snapshots else {}
    input_cost = latest.get("input_tokens", 0) * 0.14 / 1_000_000
    output_cost = latest.get("output_tokens", 0) * 0.28 / 1_000_000
    cache_savings = latest.get("cache_read_tokens", 0) * 0.028 / 1_000_000

    # Compaction 怀疑事件数
    compaction_events = sum(1 for t in trends if t.get("compaction_suspected"))

    # 增长率
    if trends:
        avg_growth = sum(t["token_growth_rate_per_hour"] for t in trends) / len(trends)
        peak_growth = max(t["token_growth_rate_per_hour"] for t in trends)
    else:
        avg_growth = 0
        peak_growth = 0

    summary = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "period": {"from": first_ts, "to": last_ts},
        "snapshots": len(snapshots),
        "sessions_peak": total_sessions,
        "tokens_peak": max_tokens,
        "avg_context_pct": round(avg_ctx, 2),
        "max_context_pct": max_ctx,
        "avg_cache_efficiency": round(avg_cache_eff, 2),
        "estimated_cost_usd": round(input_cost + output_cost, 4),
        "cache_savings_usd": round(cache_savings, 4),
        "input_output_ratio": round(total_input / max(total_output, 1), 2) if total_output else 0,
        "trends": {
            "compaction_suspected_events": compaction_events,
            "token_growth_rate_per_hour": round(avg_growth, 1),
            "token_growth_peak_per_hour": int(peak_growth),
        },
    }
    return summary

def main():
    snapshots = load_snapshots(INPUT)
    if not snapshots:
        print("[analyze-token-metrics] 无数据")
        return

    records = compute_session_growth(snapshots)
    trends = compute_trends(snapshots)
    summary = compute_daily_summary(snapshots, trends)

    # 写 summary
    out_dir = os.path.dirname(OUTPUT)
    os.makedirs(out_dir, exist_ok=True)

    record = {
        "type": "daily_summary",
        "data": summary,
    }
    if trends:
        record["trends"] = trends[-12:]  # 最近12个区间

    with open(OUTPUT, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[analyze-token-metrics] 完成: {summary['period']['from']} → {summary['period']['to']}")
    print(f"  快照数: {summary['snapshots']}")
    print(f"  怀疑 compaction 事件: {summary['trends']['compaction_suspected_events']}")
    print(f"  平均 token 增长率: {summary['trends']['token_growth_rate_per_hour']}/h")
    print(f"  Context 峰值: {summary['max_context_pct']}%")
    print(f"  估算成本: ${summary['estimated_cost_usd']:.4f} (cache节省: ${summary['cache_savings_usd']:.4f})")
    print()

    # 显示各时间区间趋势
    if trends:
        print("  时间区间趋势:")
        for t in trends[-6:]:
            flag = " ⚠️ compaction?" if t.get("compaction_suspected") else ""
            print(f"    {t['ts_start'][11:16]}→{t['ts_end'][11:16]}: "
                  f"token={t['token_growth_rate_per_hour']:>6}/h "
                  f"ctx={t['context_pct_delta']:>+.1f}% "
                  f"cache_eff={t['cache_efficiency_delta']:>+.2f}"
                  f"{flag}")


if __name__ == "__main__":
    main()
