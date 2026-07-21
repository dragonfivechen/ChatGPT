"""
trading-runtime — notifier.py (交易变化通知)

职责:
  - 监听 Runtime 状态变化
  - 输出成交/持仓/风险通知
  - 写入 notify JSONL (结构化)
  - 提供文本摘要 (用于控制台或TG推送)

事件类型:
  - fill:        成交记录
  - position:    持仓变化
  - risk_warning:风险告警
  - session_state:交易时段状态变更

格式:
  { "event_type": "NOTIFY", "ts": "...",
    "notify_type": "fill|position|risk_warning|session_state",
    "data": {...} }
"""

import json
import os
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))


class Notifier:
    """运行时通知器 — 结构化和文本输出"""

    def __init__(self, config: dict = None,
                 output_dir: str = None):
        """
        Args:
            config: session_config.json 内容 (notification 段)
            output_dir: notify 输出目录
        """
        self.config = config or {}
        self._enabled = self.config.get("notification", {}).get(
            "enable", True)
        notify_cfg = self.config.get("notification", {})
        self._events_filter = set(notify_cfg.get(
            "events", ["fill", "position", "risk_warning", "session_state"]))

        if output_dir:
            self._output_dir = output_dir
        elif config:
            self._output_dir = config.get("notification", {}).get(
                "output_dir", "reports/notifications")
        else:
            self._output_dir = "reports/notifications"

        self._log_file = None
        self._notify_log: list[dict] = []
        self._init_log()

    def _init_log(self):
        """初始化输出目录和日志文件"""
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self._output_dir)
        os.makedirs(log_path, exist_ok=True)
        self._log_file = os.path.join(
            log_path, f"notify_{datetime.now(BJT).strftime('%Y%m%d')}.jsonl")

    def notify_fill(self, fill: dict) -> dict | None:
        """成交通知"""
        if "fill" not in self._events_filter:
            return None
        data = {
            "notify_type": "fill",
            "symbol": fill.get("symbol", ""),
            "qty": fill.get("qty", 0),
            "price": fill.get("price", 0),
            "direction": "多" if fill.get("qty", 0) > 0 else "空",
            "strategy_id": fill.get("strategy_id", ""),
            "timestamp": fill.get("ts", ""),
        }
        text = (f"💱 成交 | {data['symbol']} "
                f"{data['direction']} {abs(data['qty'])}手 "
                f"@ ¥{data['price']:.1f} "
                f"[{data['strategy_id']}]")
        return self._emit(data, text)

    def notify_position_change(self, pos_info: dict) -> dict | None:
        """持仓变化通知"""
        if "position" not in self._events_filter:
            return None
        direction = "多" if pos_info.get("qty", 0) > 0 else "空"
        data = {
            "notify_type": "position",
            "symbol": pos_info.get("symbol", ""),
            "qty": pos_info.get("qty", 0),
            "direction": direction,
            "avg_cost": pos_info.get("avg_cost", 0),
            "unrealized_pnl": pos_info.get("unrealized_pnl", 0),
        }
        text = (f"📦 持仓 | {data['symbol']} "
                f"{direction} {abs(data['qty'])}手 "
                f"成本¥{data['avg_cost']:.1f} "
                f"浮盈¥{data['unrealized_pnl']:+.0f}")
        return self._emit(data, text)

    def notify_risk_warning(self, risk_info: dict) -> dict | None:
        """风险告警"""
        if "risk_warning" not in self._events_filter:
            return None
        warn_type = risk_info.get("warning_type", "未知")
        data = {
            "notify_type": "risk_warning",
            "warning_type": warn_type,
            "drawdown": risk_info.get("drawdown", 0),
            "drawdown_pct": risk_info.get("drawdown_pct", 0),
            "equity": risk_info.get("equity", 0),
            "margin_ratio": risk_info.get("margin_ratio", 0),
        }
        text = (f"⚠️ 风控 | {warn_type} "
                f"回撤¥{data['drawdown']:+.0f}({data['drawdown_pct']:+.2f}%) "
                f"权益¥{data['equity']:,.0f} "
                f"保证金{data['margin_ratio']:.1f}%")
        return self._emit(data, text)

    def notify_session_state(self, state_info: dict) -> dict | None:
        """交易时段状态变更通知"""
        if "session_state" not in self._events_filter:
            return None
        data = {
            "notify_type": "session_state",
            "session_name": state_info.get("session_name", ""),
            "state": state_info.get("state", ""),
            "timestamp": datetime.now(BJT).isoformat(),
        }
        state_emoji = {
            "PRE_MARKET": "🌅", "OPEN": "🔓", "TRADING": "📊",
            "CLOSE": "🔒", "REPORT": "📝", "WAITING": "⏳",
        }
        emoji = state_emoji.get(data["state"], "🔔")
        text = (f"{emoji} 时段 | "
                f"{data['session_name']} → {data['state']}")
        return self._emit(data, text)

    def notify_equity_change(self, equity: float,
                             change: float, pct: float) -> dict | None:
        """权益变化通知 (周期性)"""
        direction = "📈" if change >= 0 else "📉"
        text = (f"{direction} 权益 | "
                f"¥{equity:>10,.0f} "
                f"({change:+.0f}, {pct:+.2f}%)")
        data = {
            "notify_type": "equity_change",
            "equity": equity,
            "change": change,
            "change_pct": pct,
        }
        return self._emit(data, text)

    def _emit(self, data: dict, text: str) -> dict:
        """写入通知日志并返回结构化通知"""
        entry = {
            "event_type": "NOTIFY",
            "ts": datetime.now(BJT).isoformat(),
            **data,
            "text": text,
        }
        self._notify_log.append(entry)

        # 写入文件
        if self._log_file:
            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except OSError:
                pass

        print(f"  📢 {text}")
        return entry

    def recent_notifications(self, n: int = 10) -> list[dict]:
        """最近N条通知"""
        return self._notify_log[-n:]

    def summary(self) -> dict:
        """通知统计"""
        counts = {}
        for n in self._notify_log:
            nt = n.get("notify_type", "?")
            counts[nt] = counts.get(nt, 0) + 1
        return {
            "total": len(self._notify_log),
            "by_type": counts,
        }

    def close(self):
        """关闭"""
        if self._notify_log:
            print(f"[notifier] 📋 共 {len(self._notify_log)} 条通知")
