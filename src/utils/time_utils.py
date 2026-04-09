"""时间处理工具函数

提供 UTC 时间获取、日期格式化、时长解析和人类可读时间差等功能。
"""

import re
from datetime import datetime, timedelta, timezone

# 时长解析正则：匹配 "1d2h30m10s" 形式的字符串
_DURATION_PATTERN = re.compile(
    r"(?:(\d+)d)?"   # 天
    r"(?:(\d+)h)?"   # 小时
    r"(?:(\d+)m)?"   # 分钟
    r"(?:(\d+)s)?",  # 秒
    re.IGNORECASE,
)


def now_utc() -> datetime:
    """获取当前 UTC 时间

    Returns:
        带有 UTC 时区信息的当前时间
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """将 datetime 对象格式化为字符串

    Args:
        dt: 待格式化的 datetime 对象
        fmt: 格式字符串，默认 "YYYY-MM-DD HH:MM:SS"

    Returns:
        格式化后的时间字符串
    """
    return dt.strftime(fmt)


def parse_duration(text: str) -> timedelta | None:
    """解析时长字符串为 timedelta

    支持的格式示例：
    - "1h30m" -> 1小时30分钟
    - "2d"    -> 2天
    - "30s"   -> 30秒
    - "1d12h30m10s" -> 1天12小时30分钟10秒

    Args:
        text: 时长字符串

    Returns:
        解析成功返回 timedelta，失败返回 None
    """
    text = text.strip()
    if not text:
        return None

    match = _DURATION_PATTERN.fullmatch(text)
    if not match or not any(match.groups()):
        return None

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def human_readable_delta(delta: timedelta) -> str:
    """将 timedelta 转换为中文可读格式

    示例输出："2天3小时30分钟"、"45秒"

    Args:
        delta: 时间差对象

    Returns:
        中文可读的时间差字符串
    """
    total_seconds = int(abs(delta.total_seconds()))

    if total_seconds == 0:
        return "0秒"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if seconds:
        parts.append(f"{seconds}秒")

    return "".join(parts)
