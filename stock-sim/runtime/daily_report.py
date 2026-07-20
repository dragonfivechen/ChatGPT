#!/usr/bin/env python3
"""runtime/daily_report.py — 模拟收盘日报 v2

标准结构（按 龙哥 定稿）：
  📊 模拟交易日报
  日期

  【L2涨幅TOP5】       ← 全评分池今日涨幅前5
  【L3排名TOP5】       ← 评分排名前5当日表现
  【今日持仓表现】     ← 当前持仓涨跌
  【今日交易】         ← 当天买卖事件
  【L2 TOP5未持仓】    ← 涨幅榜中遗漏标的
  【账户状态】         ← 资金概况

数据源：
  - scoring_pool.json    → 评分排名 / 名称
  - market_events.jsonl  → 当日涨跌幅
  - portfolio_snapshots.jsonl → 持仓 / 资金
  - strategy_signals.jsonl   → 今日买卖信号
  - trade_ledger.jsonl       → 交易生命周期（退出原因/盈亏）
"""

import sys
import os
import json
import time

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

EVENTS_DIR = os.path.join(_PROJECT, "events")
POOL_PATH = os.path.join(_PROJECT, "market", "scoring_pool.json")

_RANK_EMOJI = {1: '🥇', 2: '🥈', 3: '🥉', 4: '4️⃣', 5: '5️⃣'}
_SELL_REASON_LABEL = {
    "RANK_DROP": "Rank下降",
    "STOP_LOSS": "止损",
    "TAKE_PROFIT": "止盈",
    "REPLACE": "替换",
    "DRAWDOWN": "回撤",
}


def _load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    result = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return result


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _today_prefix() -> str:
    """用于匹配当天事件的日期前缀"""
    return _today()


def _fmt_pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def _r(rank: int) -> str:
    return _RANK_EMOJI.get(rank, f"#{rank}")


def _parse_signal_note(note: str) -> dict:
    """从 signal note 中解析 rank 和操作语义

    示例 note="rank=3 建仓12%" → {rank:3, alloc_pct:12, kind:'建仓'}
             note="rank=2 加仓 10%" → {rank:2, alloc_pct:10, kind:'加仓'}
    """
    result = {"rank": 0, "alloc_pct": 0, "kind": ""}
    import re
    m = re.search(r"rank=(\d+)", note)
    if m:
        result["rank"] = int(m.group(1))

    m = re.search(r"(\d{1,2})%", note)
    if m:
        result["alloc_pct"] = int(m.group(1))

    if "建仓" in note:
        result["kind"] = "建仓"
    elif "加仓" in note:
        result["kind"] = "加仓"
    elif "减仓" in note:
        result["kind"] = "减仓"
    elif "止损" in note:
        result["kind"] = "止损"
    elif "止盈" in note:
        result["kind"] = "止盈"
    elif "替换" in note:
        result["kind"] = "替换"

    return result


def build_body() -> str:
    lines = []
    today = _today()
    today_prefix = today

    # ── 加载全部数据源 ──
    pool = _load_json(POOL_PATH)
    prices = {}   # symbol → {price, pre_close, change_pct}
    for q in _load_jsonl(os.path.join(EVENTS_DIR, "market_events.jsonl")):
        if q.get("event_type") != "MARKET_QUOTE":
            continue
        sym = q["symbol"]
        d = q.get("data", {})
        p = d.get("price", 0)
        if p <= 0:
            continue
        pc = d.get("pre_close", 0)
        change = (p - pc) / pc * 100 if pc > 0 else 0
        prices[sym] = {"price": p, "pre_close": pc, "change_pct": round(change, 1)}

    snapshots = _load_jsonl(os.path.join(EVENTS_DIR, "portfolio_snapshots.jsonl"))
    last_snapshot = snapshots[-1] if snapshots else None

    today_signals = [s for s in _load_jsonl(os.path.join(EVENTS_DIR, "strategy_signals.jsonl"))
                     if s.get("timestamp", "").startswith(today_prefix)]

    today_trades = [t for t in _load_jsonl(os.path.join(EVENTS_DIR, "trade_ledger.jsonl"))
                    if t.get("timestamp", "").startswith(today_prefix)]

    # ── 评分池索引 ──
    details = pool.get("details", []) if pool else []
    name_map  = {d.get("symbol", ""): d.get("name", "") for d in details}
    score_map = {d.get("symbol", ""): d.get("score", 0) for d in details}
    rank_map  = {d.get("symbol", ""): d.get("rank", 999) for d in details}

    # ── 当前持仓 ──
    holdings = {}
    if last_snapshot:
        pf = last_snapshot.get("portfolio", {})
        for h in pf.get("holdings", []):
            holdings[h["symbol"]] = h

    # ════════════════════════════════════════════════════════════════
    # 标题
    # ════════════════════════════════════════════════════════════════
    lines.append("📊 模拟交易日报")
    lines.append(today)
    lines.append("")

    # ════════════════════════════════════════════════════════════════
    # ① L2涨幅TOP5（全评分池今日涨幅最大）
    # ════════════════════════════════════════════════════════════════
    scored_gainers = [(d, prices.get(d["symbol"], {}).get("change_pct", 0))
                      for d in details if d["symbol"] in prices]
    scored_gainers.sort(key=lambda x: x[1], reverse=True)
    top5_l2 = scored_gainers[:5]

    lines.append("【L2涨幅TOP5】")
    for i, (d, chg) in enumerate(top5_l2):
        sym = d["symbol"]
        nm = name_map.get(sym, "")
        label = _r(i + 1)
        stock = f"{sym} {nm}" if nm else sym
        lines.append(f"{label} {stock}  {_fmt_pct(chg)}")
    lines.append("")

    # ════════════════════════════════════════════════════════════════
    # ② L3排名TOP5（评分排名前5当日表现）
    # ════════════════════════════════════════════════════════════════
    top5_by_rank = sorted(details, key=lambda x: x.get("rank", 999))[:5]

    lines.append("【L3排名TOP5】")
    for i, d in enumerate(top5_by_rank):
        sym = d["symbol"]
        nm = name_map.get(sym, "")
        sc = d.get("score", 0)
        chg = prices.get(sym, {}).get("change_pct", 0)
        label = _r(i + 1)
        stock = f"{sym} {nm}" if nm else sym
        lines.append(f"{label} {stock}  L3:{sc:.1f}  {_fmt_pct(chg)}")
    lines.append("")

    # ════════════════════════════════════════════════════════════════
    # ③ 今日持仓表现
    # ════════════════════════════════════════════════════════════════
    held_list = []
    for sym, h in holdings.items():
        chg = prices.get(sym, {}).get("change_pct", 0)
        held_list.append({
            "symbol": sym, "name": name_map.get(sym, ""),
            "change_pct": chg, "rank": rank_map.get(sym, 999),
            "weight": h.get("weight", 0),
        })
    held_list.sort(key=lambda x: x["rank"])

    lines.append("【今日持仓表现】")
    if held_list:
        for h in held_list:
            label = _r(h["rank"])
            stock = f"{h['symbol']} {h['name']}" if h['name'] else h['symbol']
            wt = f"{h['weight']*100:.0f}%" if h["weight"] else ""
            lines.append(f"{label} {stock}  {_fmt_pct(h['change_pct'])}  {wt}")
    else:
        lines.append("（无持仓）")
    lines.append("")

    # ════════════════════════════════════════════════════════════════
    # ④ 今日交易（去重 — 每只股票只展示最终状态）
    # ════════════════════════════════════════════════════════════════
    closed_trades = [t for t in today_trades if t.get("event_type") == "TRADE_CLOSE"]
    today_buy_signals  = [s for s in today_signals if s.get("action") == "BUY"]
    today_sell_signals = [s for s in today_signals if s.get("action") == "SELL"]

    lines.append("【今日交易】")
    has_trade = False

    # BUY: 按 symbol 去重，保留最后一条（含最终仓位）
    buy_by_sym: dict[str, dict] = {}
    for s in today_buy_signals:
        buy_by_sym[s["symbol"]] = s
    if buy_by_sym:
        has_trade = True
        lines.append("BUY:")
        # 按 rank 排序
        buy_sorted = sorted(buy_by_sym.values(),
                            key=lambda x: _parse_signal_note(x.get("note", ""))["rank"] or rank_map.get(x["symbol"], 999))
        for s in buy_sorted:
            sym = s["symbol"]
            nm = name_map.get(sym, "")
            note_info = _parse_signal_note(s.get("note", ""))
            rk = note_info["rank"] or rank_map.get(sym, "")
            stock = f"{sym} {nm}" if nm else sym
            alloc = f" {note_info['alloc_pct']}%" if note_info['alloc_pct'] else ""
            lines.append(f"  {_r(rk)} {stock}{alloc}")

    sell_by_sym: dict[str, dict] = {}
    for t in closed_trades:
        sell_by_sym[t["symbol"]] = ("TRADE_CLOSE", t)
    for s in today_sell_signals:
        if s["symbol"] not in sell_by_sym:
            sell_by_sym[s["symbol"]] = ("SIGNAL", s)
    if sell_by_sym:
        has_trade = True
        lines.append("SELL:")
        for sym, (src, item) in sell_by_sym.items():
            nm = name_map.get(sym, "")
            stock = f"{sym} {nm}" if nm else sym
            if src == "TRADE_CLOSE":
                reason = item.get("exit_reason", "")
                pnl = item.get("pnl_pct", 0) or item.get("return_pct", 0)
                reason_label = _SELL_REASON_LABEL.get(reason, reason)
                lines.append(f"  {stock}  原因:{reason_label}  收益:{_fmt_pct(pnl)}")
            else:
                note_info = _parse_signal_note(item.get("note", ""))
                lines.append(f"  {stock}  {note_info['kind']}")

    if not has_trade:
        lines.append("今日交易: 无")
    lines.append("")

    # ════════════════════════════════════════════════════════════════
    # ⑤ L2 TOP5未持仓（漏检分析 + 排除原因）
    # ════════════════════════════════════════════════════════════════
    l2_unheld = [(d, chg) for d, chg in top5_l2 if d["symbol"] not in holdings]

    # 计算Top5门槛信息
    ranked_by_score = sorted(details, key=lambda x: x.get("rank", 999))
    rank5_entry = ranked_by_score[4] if len(ranked_by_score) >= 5 else None
    cutoff_rank = rank5_entry.get("rank", 5) if rank5_entry else 5
    cutoff_score = rank5_entry.get("score", 0) if rank5_entry else 0
    cutoff_sym = rank5_entry.get("symbol", "") if rank5_entry else ""
    cutoff_name = name_map.get(cutoff_sym, "")
    held_symbols = set(holdings.keys())
    holding_count = len(holdings)

    def _exclude_reason(rk: int, sc: float) -> dict:
        """根据规则推断排除原因（不依赖策略内部状态）"""
        if rk > 5:
            return {
                "reason": "RANK_OUTSIDE_TOP5",
                "label": "L3排名不在Top5",
                "rank_gap": rk - cutoff_rank,
                "score_gap": sc - cutoff_score,
            }
        if holding_count >= 5:
            return {
                "reason": "CAPACITY_FULL",
                "label": "持仓已满5只",
                "rank_gap": 0,
                "score_gap": 0,
            }
        return {
            "reason": "OTHER",
            "label": "其他",
            "rank_gap": 0,
            "score_gap": 0,
        }

    lines.append("【L2 TOP5未持仓】")
    if l2_unheld:
        for d, chg in l2_unheld:
            sym = d["symbol"]
            nm = name_map.get(sym, "")
            sc = d.get("score", 0)
            rk = rank_map.get(sym, 999)
            info = _exclude_reason(rk, sc)
            stock = f"{sym} {nm}" if nm else sym
            lines.append(f"  {stock}  {_fmt_pct(chg)}")
            lines.append(f"    L3:{sc:.1f} Rank:{rk}  ❌ {info['label']}")
            if info['reason'] == 'RANK_OUTSIDE_TOP5':
                comp = f"{cutoff_sym} {cutoff_name}" if cutoff_name else cutoff_sym
                lines.append(f"    门槛: {cutoff_score:.1f}分 ({comp})")
                lines.append(f"    差距: 超{info['rank_gap']}位 | 低{abs(info['score_gap']):.1f}分")
    else:
        lines.append("（无 — 涨幅前五均已持仓）")
    lines.append("")

    # ════════════════════════════════════════════════════════════════
    # ⑥ 账户状态
    # ════════════════════════════════════════════════════════════════
    if last_snapshot:
        pf = last_snapshot.get("portfolio", {})
        lines.append("【账户状态】")
        dr = pf.get("drawdown", 0)
        lines.append(f"总权益:{pf['equity']/10000:.0f}万")
        lines.append(f"持仓:{pf['market_value']/10000:.0f}万")
        lines.append(f"现金:{pf['cash']/10000:.1f}万")
        lines.append(f"持仓数:{len(pf.get('holdings',[]))}/5")
        if dr != 0:
            lines.append(f"回撤:{_fmt_pct(dr*100)}")

    return "\n".join(lines)


def main():
    # 只在终端直接运行时打印；cron 会自动推送标准输出
    body = build_body()
    print(body)


if __name__ == "__main__":
    main()
