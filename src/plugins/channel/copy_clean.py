"""去转发标签复制插件

提供将消息"干净"地复制到目标聊天的功能，
去除所有"转发自"标签和来源标记。通过事件总线触发。
"""

from typing import Any

from telethon.tl.types import Message

from src.plugins.plugin_base import PluginBase


class CopyCleanPlugin(PluginBase):
    """去标签复制插件 — 复制消息时移除转发标签"""

    @property
    def name(self) -> str:
        return "channel.copy_clean"

    @property
    def description(self) -> str:
        return "去除转发标签的消息复制服务"

    async def setup(self) -> None:
        """订阅复制请求事件"""
        await self.event_bus.subscribe("copy_clean_message", self._handle_copy)
        self.logger.info("去标签复制插件已启动")

    async def teardown(self) -> None:
        """取消事件订阅"""
        await self.event_bus.unsubscribe("copy_clean_message", self._handle_copy)

    async def _handle_copy(self, **kwargs: Any) -> None:
        """处理复制请求

        期望的 kwargs:
            source_chat_id: 源聊天 ID
            message_id: 消息 ID
            target_chat_id: 目标聊天 ID
        """
        source_chat = kwargs.get("source_chat_id")
        message_id = kwargs.get("message_id")
        target_chat = kwargs.get("target_chat_id")

        if not all([source_chat, message_id, target_chat]):
            self.logger.warning("copy_clean 事件参数不完整")
            return

        try:
            # 通过 Userbot 获取原始消息（可访问受限频道）
            result = await self.client.userbot.get_messages(
                source_chat, limit=1, ids=message_id
            )
            # get_messages 可能返回单个 Message 或列表，统一处理
            if not result:
                self.logger.warning("未找到消息 %d in %s", message_id, source_chat)
                return
            msg = result[0] if isinstance(result, list) else result
            if msg is None:
                self.logger.warning("消息 %d 在 %s 中不存在", message_id, source_chat)
                return
            await self._send_clean_copy(msg, target_chat)

        except Exception as e:
            self.logger.error("去标签复制失败: %s", e)

    async def _send_clean_copy(self, msg: Message, target_chat: int) -> None:
        """将消息内容重新发送到目标（不带转发标签）

        Args:
            msg: 原始 Telethon 消息对象
            target_chat: 目标聊天 ID
        """
        text = msg.message or ""
        kwargs: dict[str, Any] = {}

        # 保留媒体文件
        if msg.media:
            kwargs["file"] = msg.media

        # 保留文本格式（粗体/链接等）
        if msg.entities:
            kwargs["formatting_entities"] = msg.entities

        if not text and not msg.media:
            self.logger.debug("消息无文本也无媒体，跳过复制")
            return

        await self.client.userbot.send_message(target_chat, text, **kwargs)
        self.logger.debug("已去标签复制消息到 %d", target_chat)
