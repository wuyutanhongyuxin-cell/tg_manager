"""消息发送插件

提供可编程的消息发送服务，支持通过事件总线触发发送，
并将发送记录保存到数据库。
"""

from typing import Any

from telethon.tl.types import Message

from src.database.repositories.message_repo import MessageRepository
from src.plugins.plugin_base import PluginBase


class SenderPlugin(PluginBase):
    """消息发送插件 — 其他插件和 Bot 命令通过事件总线触发发送"""

    @property
    def name(self) -> str:
        return "message.sender"

    @property
    def description(self) -> str:
        return "消息发送服务，支持文本和媒体发送"

    async def setup(self) -> None:
        """订阅发送事件"""
        await self.event_bus.subscribe("send_message", self._handle_send)
        self.logger.info("消息发送插件已启动")

    async def teardown(self) -> None:
        """取消事件订阅"""
        await self.event_bus.unsubscribe("send_message", self._handle_send)

    async def _handle_send(self, **kwargs: Any) -> None:
        """处理发送请求

        支持的参数:
            chat_id: 目标聊天 ID（必需）
            text: 消息文本（必需）
            prefer_bot: 是否优先使用 Bot（默认 True）
            file: 媒体文件路径或对象（可选）
            reply_to: 回复的消息 ID（可选）
        """
        chat_id = kwargs.get("chat_id")
        text = kwargs.get("text", "")
        if not chat_id:
            self.logger.warning("send_message 事件缺少 chat_id")
            return

        prefer_bot = kwargs.get("prefer_bot", True)
        # 构建额外参数（file、reply_to 等）
        extra: dict[str, Any] = {}
        if "file" in kwargs:
            extra["file"] = kwargs["file"]
        if "reply_to" in kwargs:
            extra["reply_to"] = kwargs["reply_to"]

        try:
            msg = await self.client.send_message(
                chat_id, text, prefer_bot=prefer_bot, **extra
            )
            # 保存发送记录到数据库
            await self._save_to_db(msg, chat_id)
            # 通知其他插件消息已发送
            await self.event_bus.emit(
                "message_sent", message_id=msg.id, chat_id=chat_id
            )
        except Exception as e:
            self.logger.error("发送消息到 %s 失败: %s", chat_id, e)

    async def _save_to_db(self, msg: Message, chat_id: Any) -> None:
        """将发送的消息保存到数据库"""
        try:
            session = self.db.get_session()
            async with session:
                async with session.begin():
                    repo = MessageRepository(session)
                    # 从 peer_id 解析标准 Telegram chat_id
                    # PeerChannel(id=X) → -100X, PeerChat(id=X) → -X, PeerUser(id=X) → X
                    resolved_chat_id = self._resolve_chat_id(msg, chat_id)
                    await repo.upsert(
                        message_id=msg.id,
                        chat_id=resolved_chat_id,
                        sender_id=msg.sender_id,
                        date=msg.date,
                        text=msg.message or "",
                        is_forward=False,
                    )
        except Exception as e:
            self.logger.warning("保存发送记录失败: %s", e)

    @staticmethod
    def _resolve_chat_id(msg: Message, fallback: Any) -> int:
        """从 Telethon Message 的 peer_id 解析标准 Telegram chat_id

        Telethon peer_id 类型映射：
        - PeerUser(user_id=X) → X（正数）
        - PeerChat(chat_id=X) → -X（负数，普通群组）
        - PeerChannel(channel_id=X) → -100X（负数，超级群组/频道）
        """
        from telethon.tl.types import PeerChannel, PeerChat, PeerUser
        peer = getattr(msg, "peer_id", None)
        if isinstance(peer, PeerChannel):
            return -1000000000000 - peer.channel_id
        if isinstance(peer, PeerChat):
            return -peer.chat_id
        if isinstance(peer, PeerUser):
            return peer.user_id
        # 兜底：使用传入的 chat_id
        return int(fallback) if isinstance(fallback, (int, str)) else 0
