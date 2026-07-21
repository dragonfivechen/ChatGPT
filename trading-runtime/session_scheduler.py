"""
trading-runtime — session_scheduler.py (交易时间调度器)

职责:
  - 按交易日节奏驱动运行时生命周期
  - 状态机: WAITING → PRE_MARKET → OPEN → TRADING → CLOSE → REPORT
  - 盘前调度: Preloader → 数据准备
  - 盘中节奏: 开盘启动 → 交易运行 → 收盘停止
  - 收盘调度: DailyReport → 日报生成
  - 全程通知: Notifier → 状态变化/成交/风控

使用:
  scheduler = SessionScheduler()
  scheduler.run(report_dir, strategy_runner, ...)

  # 也可用钩子模式集成到 live_session:
  scheduler.on_quote(quote)
  scheduler.on_fill(fill)

状态机:
  WAITING ──(到准备时间)──→ PRE_MARKET ──(准备完成)──→ OPEN
     ↑                                                  │
     │                                                  ↓
  REPORT ←──(收盘)── CLOSE ←──(交易结束)── TRADING

依赖:
  - preloader.py   (盘前准备)
  - notifier.py     (通知)
  - daily_report.py (日报)
  - runtime_config.json / session_config.json
"""

import json
import os
import signal
import sys
import time
from datetime import datetime, timezone, timedelta, date

from preloader import Preloader
from notifier import Notifier
from daily_report import DailyReport

BJT = timezone(timedelta(hours=8))

# 全局运行标志
SCHEDULER_RUNNING = True


def _sighandler(sig, frame):
    global SCHEDULER_RUNNING
    print(f"\n[session_scheduler] 🛑 收到信号 {sig}")
    SCHEDULER_RUNNING = False


# ── 时间工具函数 ─────────────────────────────────────────

def _parse_time(t_str: str) -> tuple[int, int]:
    """"09:00" → (9, 0)"""
    parts = t_str.strip().split(":")
    return int(parts[0]), int(parts[1])


def _to_seconds(h: int, m: int) -> int:
    return h * 3600 + m * 60


def _current_seconds() -> int:
    now = datetime.now(BJT)
    return _to_seconds(now.hour, now.minute)


def _current_date_str() -> str:
    return date.today().isoformat()


def _format_time(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"


# ── Session Scheduler ────────────────────────────────────

class SessionScheduler:
    """
    交易时段调度器 — 状态机实现

    States: WAITING / PRE_MARKET / OPEN / TRADING / CLOSE / REPORT / DONE
    """

    WAITING = "WAITING"
    PRE_MARKET = "PRE_MARKET"
    OPEN = "OPEN"
    TRADING = "TRADING"
    CLOSE = "CLOSE"
    REPORT = "REPORT"
    DONE = "DONE"

    STATE_EMOJI = {
        WAITING: "⏳", PRE_MARKET: "🌅", OPEN: "🔓",
        TRADING: "📊", CLOSE: "🔒", REPORT: "📝", DONE: "✅",
    }

    def __init__(self, session_config_path: str = None,
                 runtime_config: dict = None):
        """
        Args:
            session_config_path: session_config.json 路径
            runtime_config: live_session 的 runtime_config
        """
        self.config = self._load_config(session_config_path)
        self.runtime_config = runtime_config or {}

        self.state = self.WAITING
        self.active_session = None  # 当前交易时段名 (morning/afternoon)
        self.session_index = 0

        # 子组件
        self.preloader = None
        self.notifier = Notifier(config=self.config)
        self.daily_report = DailyReport(config=self.config)

        # 当日数据
        self._today_fills: list[dict] = []
        self._current_account = None
        self._current_risk = None
        self._current_strategy_runner = None
        self._report_generated = False

        self._last_transition_ts = None
        self._last_transition_text = ""

    def _load_config(self, path: str | None) -> dict:
        """加载 session_config.json"""
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        # 默认路径
        default = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "session_config.json")
        if os.path.exists(default):
            with open(default, "r", encoding="utf-8") as f:
                return json.load(f)
        print("[session_scheduler] ⚠️ 未找到 session_config, 使用默认配置")
        return {
            "sessions": [
                {"name": "morning", "prepare": "08:45",
                 "open": "09:00",
                 "sections": [
                     {"start": "09:00", "end": "10:15"},
                     {"start": "10:30", "end": "11:30"}
                 ]},
                {"name": "afternoon", "prepare": "12:45",
                 "open": "13:30",
                 "sections": [
                     {"start": "13:30", "end": "15:00"}
                 ]},
            ],
            "data": {"history_lookback": 120,
                     "symbols": ["RB", "I", "JM", "CU", "AL", "SC"]},
            "daily_report": {"enable": True, "output_dir": "reports/daily"},
            "notification": {"enable": True,
                             "output_dir": "reports/notifications"},
        }

    def get_schedule_times(self) -> list[dict]:
        """
        返回今日所有交易时段的时间表 (秒)
        支持 sections 数组 (小节分段, 含中间休息)
        支持 night_session 配置

        Returns:
          [{"name":"morning","prepare_s":945,"open_s":540,
             "sections":[(540,615),(630,690)], "last_close_s":690}, ...]
        """
        schedules = []

        def _build_session(s, default_prepare="08:45", default_open="09:00"):
            prep_h, prep_m = _parse_time(s.get("prepare", default_prepare))
            open_h, open_m = _parse_time(s.get("open", default_open))
            open_s = _to_seconds(open_h, open_m)

            sections = []
            last_close_s = open_s
            raw_sections = s.get("sections", [])
            if raw_sections:
                for sec in raw_sections:
                    sh, sm = _parse_time(sec.get("start", "09:00"))
                    eh, em = _parse_time(sec.get("end", "10:15"))
                    sec_pair = (_to_seconds(sh, sm), _to_seconds(eh, em))
                    sections.append(sec_pair)
                    last_close_s = max(last_close_s, sec_pair[1])
            else:
                close_h, close_m = _parse_time(s.get("close_minute", "11:30"))
                close_s = _to_seconds(close_h, close_m)
                sections.append((open_s, close_s))
                last_close_s = close_s

            return {
                "name": s.get("name", "?"),
                "prepare_s": _to_seconds(prep_h, prep_m),
                "open_s": open_s,
                "sections": sections,
                "last_close_s": last_close_s,
            }

        # 日盘时段
        for s in self.config.get("sessions", []):
            schedules.append(_build_session(s))

        # 夜盘时段 (启用时)
        night = self.config.get("night_session", {})
        if night.get("enabled", False):
            night_s = dict(night)
            night_s["name"] = "night"
            schedules.append(_build_session(
                night_s, default_prepare="20:45", default_open="21:00"))

        return schedules

    def _now_in_section(self, sections: list[tuple[int,int]]) -> tuple[bool, str]:
        """
        检查当前时间是否在任一小节内

        Returns: (in_trading, in_break)
          (True, "")     → 正在交易
          (False, "break") → 小节休
          (False, "")    → 非交易时段也无休息
        """
        now_sec = _current_seconds()
        for start_s, end_s in sections:
            if start_s <= now_sec < end_s:
                return True, ""
        # 检查是否在小节间的休息时间
        for i in range(len(sections) - 1):
            gap_start = sections[i][1]
            gap_end = sections[i + 1][0]
            if gap_start <= now_sec < gap_end:
                return False, "break"
        return False, ""

    def set_runtime_objects(self, account=None, risk=None,
                            strategy_runner=None):
        """设置运行时对象引用 (由 live_session 注入)"""
        self._current_account = account
        self._current_risk = risk
        self._current_strategy_runner = strategy_runner

    # ── 状态转换 ──────────────────────────────────────────

    def transition_to(self, new_state: str, session_name: str = None,
                      detail: str = ""):
        """执行状态转换"""
        old_state = self.state
        self.state = new_state
        self._last_transition_ts = datetime.now(BJT).isoformat()
        self._last_transition_text = f"{old_state} → {new_state}"

        emoji = self.STATE_EMOJI.get(new_state, "🔔")
        print(f"\n{emoji} [session_scheduler] 状态: "
              f"{self._last_transition_text} | {detail}")

        # 通知
        if session_name:
            self.notifier.notify_session_state({
                "session_name": session_name,
                "state": new_state,
            })

    def on_fill(self, fill: dict):
        """成交事件钩子 (由外部调用)"""
        self._today_fills.append(fill)
        self.notifier.notify_fill(fill)

    def on_quote(self, quote: dict):
        """行情事件钩子 (当前不处理)"""
        pass

    # ── 核心运行逻辑 ──────────────────────────────────────

    def check_schedule(self) -> str:
        """
        检查当前时间, 返回应执行的动作
        支持期货小节分段 (含 10:15-10:30 休息)

        Returns:
          "WAIT" | "PREPARE" | "OPEN_TRADE" | "CLOSE_TRADE" | "GENERATE_REPORT"
          | "BREAK"
        """
        now_sec = _current_seconds()
        schedules = self.get_schedule_times()

        for s in schedules:
            # ── 准备阶段 ──
            if s["prepare_s"] <= now_sec < s["open_s"]:
                if self.state == self.WAITING:
                    return "PREPARE"
                return "WAIT"

            # ── 交易或休息 ──
            in_trade, extra = self._now_in_section(s["sections"])
            if in_trade and self.state in (self.OPEN, self.TRADING, self.WAITING, self.PRE_MARKET):
                return "OPEN_TRADE"

            if extra == "break":
                # 小节休 — 只上报, 不切换状态
                return "BREAK"

            # ── 收盘检查 (最后小节结束 + 10分钟窗口) ──
            close_window_end = s["last_close_s"] + 600
            if s["last_close_s"] <= now_sec < close_window_end and \
               self.state in (self.TRADING, self.OPEN):
                return "CLOSE_TRADE"

        # ── 上报 ──
        if self.state == self.CLOSE and not self._report_generated:
            return "GENERATE_REPORT"

        return "WAIT"

    def run_once(self, actions: dict = None) -> str:
        """
        执行一次调度周期

        Args:
            actions: {
                "prepare_callback": callable(scheduler) → bool,
                "trade_callback": callable(scheduler) → bool,
                "report_callback": callable(scheduler) → bool,
            }

        Returns: 当前状态名
        """
        action = self.check_schedule()
        actions = actions or {}

        if action == "PREPARE" and self.state == self.WAITING:
            self.transition_to(self.PRE_MARKET, "盘前", "开始准备")
            cb = actions.get("prepare_callback")
            if cb:
                cb(self)
            self.transition_to(self.OPEN, "盘前", "准备完成")

        elif action == "OPEN_TRADE" and self.state in (self.OPEN, self.WAITING):
            self.transition_to(self.TRADING, "盘中", "开始交易")
            cb = actions.get("trade_callback")
            if cb:
                cb(self)

        elif action == "CLOSE_TRADE" and self.state == self.TRADING:
            self.transition_to(self.CLOSE, "收盘", "交易结束")
            cb = actions.get("close_callback")
            if cb:
                cb(self)

        elif action == "GENERATE_REPORT" and self.state == self.CLOSE:
            self.transition_to(self.REPORT, _current_date_str(), "生成日报")
            cb = actions.get("report_callback")
            if cb:
                cb(self)
            self.transition_to(self.DONE, _current_date_str(), "当日完成")

        return self.state

    # ── 完整运行 ──────────────────────────────────────────

    def run_day(self, prepare_cb=None, trade_cb=None,
                close_cb=None, report_cb=None,
                poll_interval: float = 30.0,
                timeout_until: str = None):
        """
        全天候运行 (阻塞直到收盘+日报完成)

        Args:
            prepare_cb: callable(scheduler) — 盘前准备
            trade_cb:   callable(scheduler) — 开盘交易
            close_cb:   callable(scheduler) — 收盘处理
            report_cb:  callable(scheduler) — 日报生成
            poll_interval: 轮询间隔 (秒)
            timeout_until: "HH:MM" — 等待到该时间 (仅今日)
        """
        global SCHEDULER_RUNNING

        signal.signal(signal.SIGINT, _sighandler)
        signal.signal(signal.SIGTERM, _sighandler)

        print(f"\n{'─' * 55}")
        print(f"  🌐 Session Scheduler — 交易日调度")
        print(f"  当前时间: {datetime.now(BJT).strftime('%H:%M:%S')} ")
        print(f"  状态: {self.STATE_EMOJI[self.state]} {self.state}")
        print(f"{'─' * 55}")

        # ── 等待到指定时间 ──
        if timeout_until and self.state == self.WAITING:
            target_h, target_m = _parse_time(timeout_until)
            target_s = _to_seconds(target_h, target_m)
            now_s = _current_seconds()
            if now_s < target_s:
                wait_s = target_s - now_s
                print(f"  ⏳ 等待到 {timeout_until} (剩余{wait_s // 60}分钟)...")
                time.sleep(wait_s)

        # ── 调度循环 ──
        actions = {
            "prepare_callback": prepare_cb,
            "trade_callback": trade_cb,
            "close_callback": close_cb,
            "report_callback": report_cb,
        }

        try:
            while SCHEDULER_RUNNING and self.state != self.DONE:
                self.run_once(actions)
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print(f"\n[session_scheduler] 🛑 用户中断")

        self.notifier.close()

        if self.state == self.DONE:
            print(f"\n{'─' * 55}")
            print(f"  ✅ 交易日 {_current_date_str()} 完成")
            print(f"{'─' * 55}")

    # ── 集成钩子 (供 live_session 使用) ──────────────────

    def prepare_hook(self) -> bool:
        """
        盘前准备钩子 — 供 live_session 在 PRE_MARKET 阶段调用

        Returns: True if successful
        """
        print("[session_scheduler] 🌅 盘前准备...")
        self.preloader = Preloader(
            self.config,
            data_dir=self.runtime_config.get("market", {}).get(
                "stream", {}).get("history_dir"),
        )
        result = self.preloader.prepare()
        if result["status"] == "FAILED":
            print("[session_scheduler] ⚠️ 盘前准备失败, 继续尝试")
            return False
        self.notifier.notify_session_state({
            "session_name": "pre_market",
            "state": "PRE_MARKET",
        })
        return True

    def close_hook(self) -> bool:
        """
        收盘钩子 — 关闭交易, 生成日报

        Returns: True if successful
        """
        print("[session_scheduler] 🔒 收盘处理...")
        self.notifier.notify_session_state({
            "session_name": "close",
            "state": "CLOSE",
        })
        return True

    def report_hook(self) -> dict | None:
        """
        日报钩子 — 生成并推送日报

        Returns: report dict or None
        """
        if not self._current_account:
            print("[session_scheduler] ⚠️ 无账户数据, 跳过日报")
            return None

        report = self.daily_report.generate(
            account=self._current_account,
            risk_snapshot=self._current_risk,
            fills=self._today_fills,
            strategy_runner=self._current_strategy_runner,
        )
        if report.get("status") != "DISABLED":
            summary = self.daily_report.text_summary(report)
            print(f"\n📊 收盘总结:\n{summary}")
            self._report_generated = True
        return report

    # ── 辅助 ──────────────────────────────────────────────

    def summary(self) -> dict:
        """当前状态摘要"""
        return {
            "state": self.state,
            "active_session": self.active_session,
            "session_index": self.session_index,
            "last_transition": self._last_transition_text,
            "today_fills": len(self._today_fills),
            "report_generated": self._report_generated,
            "schedules": self.get_schedule_times(),
            "current_time": datetime.now(BJT).strftime("%H:%M:%S"),
        }
