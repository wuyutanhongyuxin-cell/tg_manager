"""LLM 提示词模板管理

为各种 AI 功能提供标准化的 system/user 提示词模板。
所有模板使用 str.format() 占位符，调用时填充变量。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    """提示词模板

    Attributes:
        system: system 角色提示词
        user: user 角色提示词模板（含 {变量} 占位符）
    """

    system: str
    user: str


# === 群聊总结 ===
CHAT_SUMMARY = PromptTemplate(
    system=(
        "你是一个专业的群聊消息总结助手。"
        "请用简洁的{language}总结以下群聊消息，提取关键讨论话题和重要信息。"
        "使用 bullet points 格式，按话题分组。忽略无意义的闲聊。"
    ),
    user=(
        "以下是来自「{chat_title}」的最近 {count} 条消息：\n\n"
        "{messages}\n\n"
        "请总结以上对话的核心内容。"
    ),
)

# === 文章/URL 内容总结 ===
CONTENT_SUMMARY = PromptTemplate(
    system=(
        "你是一个内容总结助手。请用{language}简洁总结以下内容，"
        "保留关键信息、数据和结论。控制在 300 字以内。"
    ),
    user="请总结以下内容：\n\n{content}",
)

# === 智能问答 ===
QA_ASSISTANT = PromptTemplate(
    system=(
        "你是 Telegram 群组的 AI 助手。用{language}简洁回答问题。"
        "如果不确定答案，请诚实说明。"
    ),
    user="{question}",
)

# === 翻译 ===
TRANSLATION = PromptTemplate(
    system="你是一个专业翻译，请将以下内容翻译为{target_lang}，保持原意和风格。",
    user="{text}",
)

# 模板注册表（按名称查找）
TEMPLATES: dict[str, PromptTemplate] = {
    "chat_summary": CHAT_SUMMARY,
    "content_summary": CONTENT_SUMMARY,
    "qa_assistant": QA_ASSISTANT,
    "translation": TRANSLATION,
}


def get_template(name: str) -> PromptTemplate:
    """根据名称获取模板

    Args:
        name: 模板名称

    Returns:
        对应的 PromptTemplate

    Raises:
        KeyError: 模板不存在
    """
    if name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"未知模板 '{name}'，可用: {available}")
    return TEMPLATES[name]
