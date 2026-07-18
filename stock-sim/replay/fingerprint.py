"""replay/fingerprint.py — 确定性指纹

对整个 replay 结果生成确定性摘要。
相同输入必须产生相同指纹。
"""

import hashlib
import json


def compute_fingerprint(data: dict) -> str:
    """对字典递归排序后生成 SHA256 指纹。
    无论 Python dict 插入顺序如何，相同内容必出相同指纹。
    """
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def verify_fingerprint(data: dict, expected: str) -> bool:
    return compute_fingerprint(data) == expected
