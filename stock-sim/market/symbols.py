"""symbols.py — A 股股票代码规范

6 位数字代码，无前缀后缀。市场由代码范围推导。
"""

def detect_market(symbol: str) -> str:
    """根据 6 位代码返回市场缩写：SH / SZ / 未知返回空"""
    if not isinstance(symbol, str) or len(symbol) != 6 or not symbol.isdigit():
        return ""

    code = int(symbol[:3])

    if 600 <= code <= 603 or code == 688:
        return "SH"
    if code in (0, 1) or 2 <= code <= 3 or code == 300:
        return "SZ"

    return ""


def format_symbol(symbol: str) -> str:
    """统一清理：去空格、去市场后缀"""
    s = symbol.strip().upper()
    for suffix in (".SH", ".SZ", ".SS", ".SHH"):
        if s.endswith(suffix):
            s = s[:-len(suffix)]
            break
    return s.zfill(6)


def is_valid_symbol(symbol: str) -> bool:
    """有效 A 股代码：6 位数字 + 已知市场"""
    return bool(detect_market(format_symbol(symbol)))


# 常用检查
SH_PREFIXES = (600, 601, 603, 688)
SZ_PREFIXES = (0, 1, 2, 3)

