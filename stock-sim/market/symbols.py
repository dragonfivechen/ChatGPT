"""symbols.py — A 股股票代码规范

6 位数字代码，无前缀后缀。市场由代码范围推导。
"""

def detect_market(symbol: str) -> str:
    """根据 6 位代码返回市场缩写：SH / SZ / 未知返回空

    A 股前缀规则:
      SH: 600-603, 605, 688 (科创板), 730 (新股申购)
      SZ: 000-003 (主板), 001-003, 002 (中小板), 300-301 (创业板)
    """
    if not isinstance(symbol, str) or len(symbol) != 6 or not symbol.isdigit():
        return ""

    code = int(symbol[:3])

    # 上海
    if 600 <= code <= 603 or code == 605 or code == 688 or code == 730:
        return "SH"
    # 深圳
    if code in (0, 1) or 2 <= code <= 3 or 300 <= code <= 301:
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

