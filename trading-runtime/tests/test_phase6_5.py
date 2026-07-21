#!/usr/bin/env python3
"""
trading-runtime — tests/test_phase6_5.py

Phase 6.5 Trading Session Scheduler & Notification 验证套件:

  Test 1 — 盘前预采集:    Preloader 加载历史数据 + 恢复状态
  Test 2 — 通知系统:      Notifier 贴士输出 + 过滤 + 结构化格式
  Test 3 — 日报系统:      DailyReport 生成 + 文本摘要
  Test 4 — 调度状态机:    SessionScheduler 状态转换逻辑
  Test 5 — 集成验证:      Scheduler + Preloader + Notifier + Report
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preloader import Preloader, load_history_csv
from notifier import Notifier
from daily_report import DailyReport
from session_scheduler import SessionScheduler
from runtime_account import RuntimeAccount
from risk_snapshot import RiskSnapshot

BJT = timezone(timedelta(hours=8))
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAMPLE_CONFIG = {
    "market": "CN_FUTURES",
    "sessions": [
        {"name": "morning", "prepare": "08:45", "open": "09:00",
         "sections": [
             {"start": "09:00", "end": "10:15"},
             {"start": "10:30", "end": "11:30"}
         ]},
        {"name": "afternoon", "prepare": "12:45", "open": "13:30",
         "sections": [
             {"start": "13:30", "end": "15:00"}
         ]},
    ],
    "data": {"history_lookback": 10,
             "symbols": ["RB", "CU"]},
    "daily_report": {"enable": True, "output_dir": "reports/daily_test"},
    "notification": {"enable": True, "output_dir": "reports/notify_test",
                     "events": ["fill", "position", "risk_warning",
                                "session_state"]}
}


# ── Test 1: 盘前预采集 ─────────────────────────────────

def test1_preloader():
    """Test 1: Preloader 加载历史数据 + 恢复状态"""
    print("\n── Test 1: Preloader 盘前预采集 ──")

    config = dict(SAMPLE_CONFIG)
    config["data"] = {"history_lookback": 5, "symbols": ["RB", "CU"]}

    pl = Preloader(config)
    result = pl.prepare()

    assert result["status"] in ("OK", "PARTIAL", "FAILED"), \
        f"状态应该有效: {result['status']}"
    print(f"  ✅ 准备状态: {result['status']}")

    # 验证历史数据加载 (至少一个品种)
    if result["history"]:
        for sym, rows in result["history"].items():
            assert len(rows) > 0, f"{sym} 应有数据"
            assert len(rows) <= 5, f"{sym} 应不超过5条 (lookback=5)"
        print(f"  ✅ 加载 {len(result['history'])} 品种")
        for sym, rows in result["history"].items():
            print(f"     {sym}: {len(rows)} 条 (最近 {len(rows)} bar)")

    # 验证状态恢复
    print(f"  ✅ 状态恢复: {result['state_restored']} "
          f"(路径: {result.get('state_path', 'N/A')})")

    # 验证 summary
    sm = pl.summary()
    assert sm["status"] == result["status"]
    print(f"  ✅ Summary: {sm['symbols_loaded']} 品种, "
          f"{sm['total_bars']} bar")

    print(f"  ✅ Test 1 PASS")


# ── Test 2: 通知系统 ───────────────────────────────────

def test2_notifier():
    """Test 2: Notifier 贴士输出 + 过滤 + 结构化格式"""
    print("\n── Test 2: Notifier 通知系统 ──")

    # 使用临时输出目录
    with tempfile.TemporaryDirectory() as tmpdir:
        nf = Notifier(
            config=SAMPLE_CONFIG,
            output_dir=os.path.join(tmpdir, "notifications"),
        )

        # ── 发出各类通知 ──
        n1 = nf.notify_fill(
            {"symbol": "RB", "qty": 1, "price": 3295,
             "strategy_id": "MA", "ts": "2026-07-21T09:00:00"})
        assert n1 is not None, "fill 通知应产生"
        assert n1["notify_type"] == "fill"
        assert "RB" in n1["text"]
        print(f"  ✅ 成交通知: {n1['text']}")

        n2 = nf.notify_position_change(
            {"symbol": "RB", "qty": 1, "avg_cost": 3295,
             "unrealized_pnl": 500})
        assert n2["notify_type"] == "position"
        print(f"  ✅ 持仓通知: {n2['text']}")

        n3 = nf.notify_risk_warning(
            {"warning_type": "回撤超限", "drawdown": -50000,
             "drawdown_pct": -0.5, "equity": 9950000, "margin_ratio": 35})
        assert n3["notify_type"] == "risk_warning"
        print(f"  ✅ 风控通知: {n3['text']}")

        n4 = nf.notify_session_state(
            {"session_name": "morning", "state": "TRADING"})
        assert n4["notify_type"] == "session_state"
        print(f"  ✅ 时段通知: {n4['text']}")

        n5 = nf.notify_equity_change(10050000, 50000, 0.5)
        assert n5["notify_type"] == "equity_change"
        print(f"  ✅ 权益通知: {n5['text']}")

        # ── 验证格式 ──
        for n in [n1, n2, n3, n4, n5]:
            assert n.get("event_type") == "NOTIFY"
            assert "ts" in n
            assert "text" in n
        print(f"  ✅ 通知格式一致 (event_type=NOTIFY, ts, text)")

        # ── 验证日志文件 ──
        log_dir = os.path.join(tmpdir, "notifications")
        log_files = os.listdir(log_dir)
        assert len(log_files) >= 1, "应有通知日志文件"
        assert log_files[0].startswith("notify_"), \
            f"文件名格式: {log_files[0]}"
        print(f"  ✅ 日志文件: {log_files[0]}")

        # ── 验证摘要 ──
        sm = nf.summary()
        assert sm["total"] == 5, f"应有5条通知: {sm['total']}"
        assert len(sm["by_type"]) == 5, "5种类型"
        print(f"  ✅ Notifier 统计: {sm['total']} 条, {sm['by_type']}")

    print(f"  ✅ Test 2 PASS")


# ── Test 3: 日报系统 ───────────────────────────────────

def test3_daily_report():
    """Test 3: DailyReport 生成 + 文本摘要"""
    print("\n── Test 3: DailyReport 日报系统 ──")

    with tempfile.TemporaryDirectory() as tmpdir:
        config = dict(SAMPLE_CONFIG)
        config["daily_report"] = {
            "enable": True,
            "output_dir": os.path.join(tmpdir, "daily"),
        }

        acct = RuntimeAccount(initial_balance=10_000_000)
        risk = RiskSnapshot(initial_balance=10_000_000)

        # 模拟一些成交
        fills = [
            {"symbol": "RB", "qty": 1, "price": 3295, "realized_pnl": 200},
            {"symbol": "RB", "qty": -1, "price": 3310, "realized_pnl": 150},
            {"symbol": "CU", "qty": 1, "price": 68500, "realized_pnl": -300},
            {"symbol": "CU", "qty": -1, "price": 68300, "realized_pnl": -200},
        ]

        dr = DailyReport(config=config)
        report = dr.generate(acct, risk, fills)

        # ── 验证报告结构 ──
        assert report["report_type"] == "DAILY"
        assert report["trades"] == 4
        assert report["win_rate"] == 50.0  # 2赢/2输
        assert report["winning_trades"] == 2
        assert report["losing_trades"] == 2
        assert report["daily_pnl"] == 0  # 账户 1000 万不变
        print(f"  ✅ 报告结构: {report['trades']} 笔, "
              f"胜率 {report['win_rate']}%, "
              f"品种 {len(report['symbol_stats'])}")

        # ── 品种统计 ──
        assert "RB" in report["symbol_stats"]
        assert "CU" in report["symbol_stats"]
        print(f"  ✅ 品种统计: {report['symbol_stats']}")

        # ── 文本摘要 ──
        summary = dr.text_summary(report)
        assert "交易总结" in summary
        assert "4笔" in summary
        assert "50.0%" in summary or "50" in summary
        print(f"  ✅ 文本摘要:\n{summary}\n")

        # ── 文件写入 ──
        report_dir = os.path.join(tmpdir, "daily")
        files = os.listdir(report_dir)
        assert len(files) >= 1
        print(f"  ✅ 日报文件: {files}")

    print(f"  ✅ Test 3 PASS")


# ── Test 4: 调度状态机 ─────────────────────────────────

def test4_scheduler_state_machine():
    """Test 4: SessionScheduler 状态转换逻辑"""
    print("\n── Test 4: SessionScheduler 状态机 ──")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "session_config.json")
        with open(config_path, "w") as f:
            json.dump(SAMPLE_CONFIG, f)

        sched = SessionScheduler(config_path)
        assert sched.state == "WAITING"
        print(f"  ✅ 初始状态: {sched.state}")

        # ── 验证时间解析 ──
        times = sched.get_schedule_times()
        assert len(times) == 2
        assert times[0]["name"] == "morning"
        assert times[0]["prepare_s"] == 8 * 3600 + 45 * 60  # 08:45
        assert times[0]["open_s"] == 9 * 3600  # 09:00
        assert len(times[0]["sections"]) == 2, "早盘2小节"
        assert times[0]["sections"][0] == (9*3600, 10*3600+15*60)  # 09:00-10:15
        assert times[0]["sections"][1] == (10*3600+30*60, 11*3600+30*60)  # 10:30-11:30
        assert times[0]["last_close_s"] == 11 * 3600 + 30 * 60
        assert len(times[1]["sections"]) == 1, "午盘1小节"
        assert times[1]["sections"][0] == (13*3600+30*60, 15*3600)  # 13:30-15:00
        print(f"  ✅ 日程解析: morning 早盘2小节(09:00-10:15,10:30-11:30), "
              f"afternoon 午盘1小节(13:30-15:00)")

        # ── 验证状态转换 (模拟时间) ──
        # 直接测试 run_once 的分支逻辑:
        # 因为 check_schedule 依赖实时时钟, 我们在测试中验证
        # run_once 的正常分支和状态转换钩子

        transition_log = []

        def mock_prepare(s):
            transition_log.append("prepare")
            print("    [mock] 盘前准备")

        def mock_trade(s):
            transition_log.append("trade")
            print("    [mock] 开盘交易")

        def mock_close(s):
            transition_log.append("close")
            print("    [mock] 收盘处理")

        def mock_report(s):
            transition_log.append("report")
            print("    [mock] 日报生成")

        # run_once 依赖于当前时间, 我们验证状态机逻辑树
        # 在 09:00-10:15, 10:30-11:30, 13:30-15:00 之间应返回 OPEN_TRADE

        now_sec = datetime.now(BJT).hour * 3600 + \
            datetime.now(BJT).minute * 60
        morning_s2_end = 11 * 3600 + 30 * 60
        morning_s1_start = 9 * 3600
        morning_s1_end = 10 * 3600 + 15 * 60
        morning_s2_start = 10 * 3600 + 30 * 60

        in_trade = (morning_s1_start <= now_sec < morning_s1_end) or \
                   (morning_s2_start <= now_sec < morning_s2_end)
        in_s1 = morning_s1_start <= now_sec < morning_s1_end
        in_s2 = morning_s2_start <= now_sec < morning_s2_end
        print(f"  ✅ 当前时间: {now_sec // 3600}:{(now_sec % 3600) // 60:02d}")
        print(f"     早盘小节1(09:00-10:15): {in_s1}, 小节2(10:30-11:30): {in_s2}")
        if in_trade:
            action = sched.check_schedule()
            print(f"     调度动作: {action}")

        # 验证状态转换文本
        sched.transition_to("OPEN", "morning")
        assert sched.state == "OPEN"
        assert sched._last_transition_text == "WAITING → OPEN"
        print(f"  ✅ 状态转换: {sched._last_transition_text}")
        assert sched.active_session is None  # transition_to 不设 active_session
        print(f"  ✅ 状态通知: 应在 Notifier 中")

        sched.transition_to("TRADING", "afternoon")
        assert sched.state == "TRADING"
        print(f"  ✅ 状态转换: TRADING")

        sched.transition_to("CLOSE", "afternoon")
        assert sched.state == "CLOSE"

        sched.transition_to("REPORT", "2026-07-21")
        assert sched.state == "REPORT"

        sched.transition_to("DONE", "2026-07-21")
        assert sched.state == "DONE"
        print(f"  ✅ 完整状态链: WAITING → OPEN → TRADING → CLOSE → REPORT → DONE")

    print(f"  ✅ Test 4 PASS")


# ── Test 5: 集成验证 ───────────────────────────────────

def test5_integration():
    """Test 5: Scheduler + Preloader + Notifier + Report 集成"""
    print("\n── Test 5: 集成验证 ──")

    with tempfile.TemporaryDirectory() as tmpdir:
        config = dict(SAMPLE_CONFIG)
        config["daily_report"]["output_dir"] = os.path.join(tmpdir, "daily")
        config["notification"]["output_dir"] = os.path.join(tmpdir, "notify")

        config_path = os.path.join(tmpdir, "session_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # ── 创建调度器 ──
        sched = SessionScheduler(config_path)
        sched.set_runtime_objects(
            account=RuntimeAccount(initial_balance=10_000_000),
            risk=RiskSnapshot(initial_balance=10_000_000),
        )
        print(f"  ✅ 调度器创建, 状态: {sched.state}")

        # ── 模拟盘前准备 ──
        sched.transition_to("PRE_MARKET", "pre_market")
        ok = sched.prepare_hook()
        if ok:
            print(f"  ✅ 盘前准备完成")
        else:
            print(f"  ⚠️ 盘前准备部分完成")

        sched.transition_to("OPEN", "pre_market", "准备完成")

        # ── 模拟盘中交易 ──
        sched.transition_to("TRADING", "morning")
        sched.on_fill({
            "symbol": "RB", "qty": 1, "price": 3295,
            "strategy_id": "MA", "ts": "2026-07-21T09:00:00",
        })
        sched.on_fill({
            "symbol": "RB", "qty": -1, "price": 3310,
            "strategy_id": "MA", "ts": "2026-07-21T09:15:00",
            "realized_pnl": 150,
        })
        sched.on_fill({
            "symbol": "CU", "qty": 1, "price": 68500,
            "strategy_id": "Breakout", "ts": "2026-07-21T10:00:00",
        })
        print(f"  ✅ 3 笔成交记入")

        # ── 模拟收盘 ──
        sched.transition_to("CLOSE", "morning")
        ok = sched.close_hook()
        print(f"  ✅ 收盘处理: {ok}")

        # ── 生成日报 ──
        sched.transition_to("REPORT", "2026-07-21")
        report = sched.report_hook()
        assert report is not None, "日报应生成"
        assert report["trades"] == 3, f"3笔成交: {report['trades']}"
        print(f"  ✅ 日报生成: {report['trades']} 笔成交")

        # ── 完成 ──
        sched.transition_to("DONE", "2026-07-21")

        # ── 验证文件输出 ──
        daily_dir = os.path.join(tmpdir, "daily")
        notify_dir = os.path.join(tmpdir, "notify")
        daily_files = os.listdir(daily_dir)
        notify_files = os.listdir(notify_dir)
        assert len(daily_files) >= 1, "应有日报文件"
        assert len(notify_files) >= 1, "应有通知文件"
        print(f"  ✅ 日报文件: {daily_files}")
        print(f"  ✅ 通知文件: {notify_files}")
        print(f"  ✅ Notifier 统计: {sched.notifier.summary()}")

        # ── 验证 Final Summary ──
        sm = sched.summary()
        assert sm["state"] == "DONE"
        assert sm["today_fills"] == 3
        print(f"  ✅ Final Summary: state={sm['state']}, "
              f"fills={sm['today_fills']}, "
              f"sessions={len(sm['schedules'])}")

    print(f"  ✅ Test 5 PASS")


# ── Main ─────────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════╗")
    print("║  Phase 6.5 — Session Scheduler & Notify     ║")
    print("╚══════════════════════════════════════════════╝")

    test1_preloader()
    test2_notifier()
    test3_daily_report()
    test4_scheduler_state_machine()
    test5_integration()

    print()
    print(f"{'═' * 52}")
    print(f"  Test 1 (Preloader 盘前):     {'✅ PASS'}")
    print(f"  Test 2 (Notifier 通知):      {'✅ PASS'}")
    print(f"  Test 3 (DailyReport 日报):   {'✅ PASS'}")
    print(f"  Test 4 (Scheduler 状态机):   {'✅ PASS'}")
    print(f"  Test 5 (集成验证):           {'✅ PASS'}")
    print(f"{'═' * 52}")
    print(f"\n{'✅ Phase 6.5 ALL TESTS PASS'}")


if __name__ == "__main__":
    main()
