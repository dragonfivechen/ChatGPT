"""pool_provider.py — 股票池提供者 v2

职责:
  从 discovery pipeline 的 candidate_pool.json 加载候选池；
  故障时回退内置池（生产不应触发）。

数据链:
  L3 candidate_pool.json (selected) → pool_provider.get_pool() → collector → V2 策略

依赖:
  candidate_pool.json 必须存在且包含 selected 状态的标的。
"""

import json, os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_FILE = os.path.join(_BASE_DIR, "candidate_pool.json")

# 最终回退
_FALLBACK_POOL = [
    "600519", "000001", "300750", "000333", "601318"
]


def get_pool(max_symbols: int = 50) -> tuple[list[str], dict]:
    """获取当日股票池

    从 candidate_pool.json 加载 L3 选出的 selected 标的。
    文件不存在或解析失败时回退到内置池（非生产预期）。

    Args:
        max_symbols: 返回最大数量

    Returns:
        (symbols: list[str], metadata: dict)
    """
    if os.path.exists(_CANDIDATE_FILE):
        try:
            with open(_CANDIDATE_FILE, "r") as f:
                pool = json.load(f)

            details = pool.get("details", [])
            selected = [
                d for d in details
                if d.get("candidate_status") == "selected"
            ]
            selected.sort(key=lambda d: d.get("selection", {}).get("capacity_rank", 999))

            symbols = [d["symbol"].strip() for d in selected if d.get("symbol")]

            if symbols:
                metadata = {
                    "date":      pool.get("generated_at", ""),
                    "version":   f"L3.{pool.get('version', '?')}",
                    "source":    f"discovery:{pool.get('pool_stage', 'candidate')}",
                    "sectors":   ["discovery_pipeline"],
                    "total":     len(symbols),
                    "pool_state": {
                        "total_submitted":   pool.get("total_submitted"),
                        "total_selected":    pool.get("total_selected"),
                        "total_rejected":    pool.get("total_rejected"),
                    },
                }
                return symbols[:max_symbols], metadata

        except (json.JSONDecodeError, IOError):
            pass

    # 回退
    return _FALLBACK_POOL[:max_symbols], {
        "date":    "",
        "version": "0",
        "source":  "fallback",
        "sectors": [],
        "total":   len(_FALLBACK_POOL[:max_symbols]),
    }


def format_pool_metadata(metadata: dict) -> str:
    """格式化池元数据为可读字符串"""
    return (
        f"pool v{metadata.get('version','?')} "
        f"({metadata.get('date','?')}) "
        f"[{', '.join(metadata.get('sectors',[]))}] "
        f"{metadata.get('total',0)} stocks"
    )


if __name__ == "__main__":
    symbols, meta = get_pool()
    print(f"股票池: {format_pool_metadata(meta)}")
    print(f"来源:   {meta.get('source','?')}")
    if "pool_state" in meta:
        ps = meta["pool_state"]
        print(f"L3 状态: submitted={ps.get('total_submitted')} "
              f"selected={ps.get('total_selected')} "
              f"rejected={ps.get('total_rejected')}")
    for i, s in enumerate(symbols):
        print(f"  {i+1:2d}. {s}")
