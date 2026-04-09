"""文本处理工具函数

提供 Telegram 消息文本的常用处理功能，包括截断、转义、
HTML 标签清除、URL 提取和用户提及格式化。
"""

import re

# Telegram MarkdownV2 需要转义的特殊字符
_MARKDOWN_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!\\"

# URL 匹配正则表达式
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]，。！？、；：）】}]+"
)

# HTML 标签匹配正则表达式
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def truncate(text: str, max_length: int = 4096) -> str:
    """截断文本到指定长度

    如果文本超出最大长度，在末尾添加省略号。
    Telegram 单条消息限制为 4096 字符。

    Args:
        text: 原始文本
        max_length: 最大长度，默认 4096

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    # 留出省略号的空间
    return text[: max_length - 3] + "..."


def escape_markdown(text: str) -> str:
    """转义 Telegram MarkdownV2 特殊字符

    将所有 MarkdownV2 模式中的特殊字符前加反斜杠转义，
    避免消息发送时格式解析错误。

    Args:
        text: 原始文本

    Returns:
        转义后的文本
    """
    result = []
    for char in text:
        if char in _MARKDOWN_SPECIAL_CHARS:
            result.append("\\")
        result.append(char)
    return "".join(result)


def strip_html_tags(text: str) -> str:
    """移除文本中的 HTML 标签

    Args:
        text: 包含 HTML 标签的文本

    Returns:
        纯文本内容
    """
    return _HTML_TAG_PATTERN.sub("", text)


def extract_urls(text: str) -> list[str]:
    """从文本中提取所有 URL

    支持 http 和 https 协议的链接。

    Args:
        text: 待提取的文本

    Returns:
        URL 列表
    """
    return _URL_PATTERN.findall(text)


def format_user_mention(user_id: int, name: str) -> str:
    """生成 Telegram 用户提及链接

    使用 Telegram 的 tg://user 协议创建可点击的用户提及，
    适用于 HTML 解析模式。

    Args:
        user_id: 用户 ID
        name: 显示名称

    Returns:
        HTML 格式的用户提及链接
    """
    return f'<a href="tg://user?id={user_id}">{name}</a>'
