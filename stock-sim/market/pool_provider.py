"""pool_provider.py — 股票池提供者 v1

职责:
  从 strong_stock_pool.json 加载当日股票池。
  未来可接入外部排名 API 实现动态换股。

用法:
  from pool_provider import get_pool
  symbols = get_pool()
"""

import json, os, random
from datetime import datetime

_POOL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strong_stock_pool.json")


def get_pool(max_symbols: int = 30) -> tuple[list[str], dict]:
    """获取当日股票池

    Args:
        max_symbols: 返回最大数量

    Returns:
        (symbols: list[str], metadata: dict)
    """
    if not os.path.exists(_POOL_FILE):
        return _fallback_pool(), {"source": "fallback_default"}

    try:
        with open(_POOL_FILE) as f:
            pool = json.load(f)

        symbols = [s.strip() for s in pool.get("symbols", []) if s.strip()]
        # 去重保留顺序
        seen = set()
        unique = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        metadata = {
            "date": pool.get("date", ""),
            "version": pool.get("version", "?"),
            "source": pool.get("source", "unknown"),
            "sectors": pool.get("sectors", []),
            "total": len(unique),
        }

        return unique[:max_symbols], metadata
    except (json.JSONDecodeError, IOError):
        return _fallback_pool(), {"source": "fallback_error"}


def _fallback_pool() -> list[str]:
    """当池文件不可用时的回退"""
    return [
        "600519", "000001", "300750", "000333", "601318"
    ]


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
    for i, s in enumerate(symbols):
        print(f"  {i+1:2d}. {s}")
