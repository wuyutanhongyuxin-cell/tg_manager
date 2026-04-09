"""输入验证工具函数

提供 Telegram 聊天 ID、用户名、URL 验证以及文件名清理功能。
"""

import ipaddress
import re
import socket

# Telegram 用户名正则：以 @ 开头，5-32 个字母数字或下划线
_USERNAME_PATTERN = re.compile(r"^@[a-zA-Z][a-zA-Z0-9_]{4,31}$")

# 基础 URL 正则验证
_URL_PATTERN = re.compile(
    r"^https?://"
    r"[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*"
    r"(:\d{1,5})?"
    r"(/[^\s]*)?$"
)

# 文件名中不允许的字符
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_valid_chat_id(value: str | int) -> bool:
    """验证 Telegram 聊天 ID 是否合法

    合法的聊天 ID 为非零整数。
    超级群组和频道的 ID 通常以 -100 开头。

    Args:
        value: 待验证的值，可以是字符串或整数

    Returns:
        是否为合法的聊天 ID
    """
    try:
        chat_id = int(value)
        return chat_id != 0
    except (ValueError, TypeError):
        return False


def is_valid_username(value: str) -> bool:
    """验证 Telegram 用户名格式

    合法格式：以 @ 开头，5-32 个字符，
    首字符为字母，其余为字母、数字或下划线。

    Args:
        value: 待验证的用户名字符串

    Returns:
        是否为合法的用户名格式
    """
    if not isinstance(value, str):
        return False
    return bool(_USERNAME_PATTERN.match(value))


def is_valid_url(value: str) -> bool:
    """验证 URL 格式是否合法

    仅支持 http 和 https 协议。

    Args:
        value: 待验证的 URL 字符串

    Returns:
        是否为合法的 URL
    """
    if not isinstance(value, str):
        return False
    return bool(_URL_PATTERN.match(value))


def is_safe_url(value: str) -> bool:
    """验证 URL 是否安全可访问（防止 SSRF）

    检查 URL 格式合法性，并确保解析后的 IP 不是内网/回环/链路本地地址。

    Args:
        value: 待验证的 URL 字符串

    Returns:
        URL 格式合法且目标不是内网地址时返回 True
    """
    if not is_valid_url(value):
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(value)
        hostname = parsed.hostname
        if not hostname:
            return False
        # 解析域名获取 IP 地址
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        for _, _, _, _, sockaddr in addr_info:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except (socket.gaierror, ValueError, OSError):
        return False


def sanitize_filename(name: str) -> str:
    """清理文件名，移除不安全字符

    将不安全字符替换为下划线，并去除首尾空白。
    如果结果为空，返回 "unnamed"。

    Args:
        name: 原始文件名

    Returns:
        安全的文件名字符串
    """
    if not name:
        return "unnamed"

    # 替换不安全字符为下划线
    safe_name = _UNSAFE_FILENAME_CHARS.sub("_", name)
    safe_name = safe_name.strip(". ")

    return safe_name if safe_name else "unnamed"
