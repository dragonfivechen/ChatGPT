#!/usr/bin/env python3
"""
trading-runtime — account_init.py

Phase 6.3 账户初始化: 创建纸交易账户 + 注入初始资金

职责:
  - 从 runtime_config.json 读取参数
  - 创建 RuntimeAccount 实例
  - 注入 10,000,000 CNY 模拟资金
  - 输出初始状态报告

使用:
  from account_init import create_account, load_config

  config = load_config()
  account = create_account(config)
"""

import json
import os
from datetime import datetime
from typing import Optional

from runtime_account import RuntimeAccount

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "runtime_config.json"
)


def load_config(path: Optional[str] = None) -> dict:
    """加载运行时配置"""
    config_path = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(config_path):
        print(f"[account_init] ⚠️  配置文件不存在: {config_path}")
        print(f"[account_init] ⚠️  使用默认配置 (10,000,000 CNY)")
        return {
            "account": {
                "initial_cash": 10000000,
                "currency": "CNY",
                "account_type": "PAPER",
            }
        }

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    print(f"[account_init] 📋 配置加载: {config_path}")
    return config


def create_account(config: Optional[dict] = None) -> RuntimeAccount:
    """
    创建账户并注入初始资金

    Args:
        config: 配置字典。None 时从默认路径加载。

    Returns:
        RuntimeAccount: 初始化的纸交易账户
    """
    if config is None:
        config = load_config()

    account_config = config.get("account", {})
    initial_cash = float(account_config.get("initial_cash", 10_000_000))
    currency = account_config.get("currency", "CNY")
    account_type = account_config.get("account_type", "PAPER")

    account = RuntimeAccount(initial_balance=initial_cash)

    ts = datetime.now().isoformat()

    print(f"\n╔══════════════════════════════════════════════════╗")
    print(f"║  📦 纸交易账户初始化完成                          ║")
    print(f"╠══════════════════════════════════════════════════╣")
    print(f"║  初始资金: ¥{initial_cash:>12,.0f}")
    print(f"║  币种:     {currency:>14s}")
    print(f"║  类型:     {account_type:>14s}")
    print(f"║  时间:     {ts:>28s}")
    print(f"║  可用资金: ¥{account.balance:>12,.2f}")
    print(f"║  总权益:   ¥{account.equity:>12,.2f}")
    print(f"║  持仓:     {len(account.positions):>3d} 品种")
    print(f"╚══════════════════════════════════════════════════╝")

    return account


def init_status_report(account: RuntimeAccount) -> dict:
    """生成初始状态报告"""
    summary = account.summary()
    report = {
        "event_type": "ACCOUNT_INIT",
        "ts": datetime.now().isoformat(),
        "initial_cash": summary["initial_balance"],
        "balance": summary["balance"],
        "equity": summary["equity"],
        "free_cash": summary["free_cash"],
        "margin": summary["total_margin"],
        "positions": len(summary.get("positions", {})),
    }
    return report


# ── 独立运行 ──────────────────────────────────────────────

def _main():
    """独立运行: 创建账户 + 打印状态"""
    config = load_config()
    account = create_account(config)
    report = init_status_report(account)
    print()
    print(f"[account_init] ✅ 初始化状态:")
    print(f"  {json.dumps(report, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    _main()
