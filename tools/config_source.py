#!/usr/bin/env python3
"""
config_source.py — Config Truth Source Reader v1.0

Config Registry -> Config Reader -> Consumer

唯一配置事实入口。禁止消费者自行拼接配置来源。
此模块只提供读取，不修改/不同步/不热更新。
"""

import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# —— 来源发现 ——

_CONFIG_PATHS = [
    Path(os.environ.get('OPENCLAW_CONFIG', '')),
    Path.home() / '.openclaw' / 'openclaw.json',
    Path.home() / '.config' / 'openclaw' / 'openclaw.json',
]

def _locate_config() -> Path:
    """定位配置文件。"""
    for p in _CONFIG_PATHS:
        if p and p.is_file():
            return p
    raise FileNotFoundError(
        "Config Truth Source: 未找到 openclaw.json 配置文件。"
        f" 已搜索: {[str(p) for p in _CONFIG_PATHS if str(p)]}"
    )


def _load_config() -> tuple[dict, Path]:
    """加载当前配置，返回 (数据, 路径)。"""
    path = _locate_config()
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data, path


def _mtime_iso(path: Path) -> str:
    """文件修改时间 → ISO-8601。"""
    ts = path.stat().st_mtime
    dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
    return dt.isoformat()


def _checksum(data: dict) -> str:
    """配置数据校验和。"""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _version(path: Path, section_key: str = None) -> str:
    """生成版本字符串。"""
    mtime = _mtime_iso(path).split('T')[0]
    return f"v{mtime}.{section_key or 'full'}"


# —— Config Reader ——

def get_config(
    key: Optional[str] = None,
    version: Optional[str] = None,
) -> dict:
    """
    获取当前配置。

    Args:
        key: 点分隔的配置路径，如 'models.providers.deepseek'
              None 返回全量配置
        version: 指定版本（当前仅返回当前版本，预留接口）

    Returns:
        { "key": ..., "value": ..., "version": ..., "source": ..., "checksum": ... }
    """
    data, path = _load_config()
    section_key = key.split('.')[0] if key else 'full'
    ver = version or _version(path, section_key)

    if key is None:
        value = data
        ver = _version(path, 'full')
    else:
        parts = key.split('.')
        cur = data
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            elif isinstance(cur, list):
                try:
                    idx = int(p)
                    cur = cur[idx]
                except (ValueError, IndexError):
                    return {
                        "key": key,
                        "value": None,
                        "version": ver,
                        "source": str(path),
                        "checksum": _checksum(data),
                        "error": f"路径 {key}: 列表索引 {p} 无效",
                    }
            else:
                return {
                    "key": key,
                    "value": None,
                    "version": ver,
                    "source": str(path),
                    "checksum": _checksum(data),
                    "error": f"路径 {key}: 键 {p} 不存在",
                }
        value = cur

    return {
        "key": key or "(full)",
        "value": value,
        "version": ver,
        "source": str(path),
        "checksum": _checksum(data),
        "updated_at": _mtime_iso(path),
    }


def get_version(key: Optional[str] = None) -> dict:
    """
    获取配置版本信息。

    Args:
        key: 配置键。None = 全量版本

    Returns:
        { "key": ..., "current_version": ..., "source": ..., "updated_at": ... }
    """
    data, path = _load_config()
    section_key = key.split('.')[0] if key else 'full'
    ver = _version(path, section_key)
    return {
        "key": key or "(full)",
        "current_version": ver,
        "source": str(path),
        "updated_at": _mtime_iso(path),
        "checksum": _checksum(data),
    }


def get_source(key: Optional[str] = None) -> dict:
    """
    获取配置来源信息。

    Args:
        key: 配置键。None = 全量

    Returns:
        { "key": ..., "primary_source": ..., "overrides": [...], "resolved": ... }
    """
    data, path = _load_config()

    # 当前无运行时覆盖机制，source = primary
    return {
        "key": key or "(full)",
        "primary_source": str(path),
        "overrides": [],
        "resolved": str(path),
        "checksum": _checksum(data),
    }


def list_sections() -> list[str]:
    """列出顶级配置段。"""
    data, _ = _load_config()
    return list(data.keys())


# —— CLI ——

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Config Truth Source Reader')
    parser.add_argument('--key', help='配置键路径')
    parser.add_argument('--version', action='store_true', help='版本信息')
    parser.add_argument('--source', action='store_true', help='来源信息')
    parser.add_argument('--sections', action='store_true', help='列出顶级段')
    args = parser.parse_args()

    try:
        if args.sections:
            print(json.dumps(list_sections(), ensure_ascii=False, indent=2))
        elif args.version:
            print(json.dumps(get_version(args.key), ensure_ascii=False, indent=2))
        elif args.source:
            print(json.dumps(get_source(args.key), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(get_config(args.key), ensure_ascii=False, indent=2))
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        exit(1)
