"""频道镜像同步插件

实时监控源频道的新消息，自动同步到目标频道。
支持带媒体的消息同步和去标签复制。
"""

from telethon import events

from src.database.repositories.forward_rule_repo import ForwardRuleRepository
from src.plugins.plugin_base import PluginBase


class MirrorPlugin(PluginBase):
    """频道镜像插件 — 实时同步源频道消息到目标频道"""

    @property
    def name(self) -> str:
        return "channel.mirror"

    @property
    def description(self) -> str:
        return "频道镜像同步，实时复制消息到目标频道"

    async def setup(self) -> None:
        """加载镜像规则并注册事件处理器"""
        # 注册 Userbot 新消息处理器（能访问受限频道）
        self.client.userbot.client.add_event_handler(
            self._on_channel_message,
            events.NewMessage(),
        )
        self._register_handler(self._on_channel_message)
        self.logger.info("频道镜像插件已启动")

    async def teardown(self) -> None:
        """移除事件处理器"""
        for handler in self._handlers:
            self.client.userbot.client.remove_event_handler(handler)
        self._handlers.clear()

    async def _on_channel_message(self, event: events.NewMessage.Event) -> None:
        """处理频道新消息，检查是否需要镜像"""
        try:
            # 仅处理频道/超级群消息
            if not event.is_channel:
                return
            # 忽略自己发的消息
            if event.out:
                return

            # 查询该频道的镜像规则（forward_type 为 copy 或 copy_clean）
            session = self.db.get_session()
            async with session:
                repo = ForwardRuleRepository(session)
                rules = await repo.get_by_source(event.chat_id)

            if not rules:
                return

            # 对每条规则执行镜像
            for rule in rules:
                await self._mirror_message(event, rule.target_chat_id, rule.forward_type)

        except Exception as e:
            self.logger.error("镜像处理失败 (chat %d): %s", event.chat_id, e)

    async def _mirror_message(
        self, event: events.NewMessage.Event, target_id: int, mode: str
    ) -> None:
        """将消息镜像到目标频道

        Args:
            event: 源消息事件
            target_id: 目标频道 ID
            mode: 镜像模式 (forward/copy/copy_clean)
        """
        msg = event.message
        try:
            if mode == "forward":
                await self.client.userbot.forward_message(
                    event.chat_id, msg.id, target_id
                )
            elif mode == "copy":
                # copy 和 copy_clean 均为重新发送（无转发标签）
                kwargs: dict = {}
                if msg.media:
                    kwargs["file"] = msg.media
                if msg.entities:
                    kwargs["formatting_entities"] = msg.entities
                await self.client.userbot.send_message(
                    target_id, msg.message or "", **kwargs
                )
            else:
                await self.event_bus.emit(
                    "copy_clean_message",
                    source_chat_id=event.chat_id,
                    message_id=msg.id,
                    target_chat_id=target_id,
                )

            self.logger.debug(
                "镜像消息 %d: %d -> %d (%s)",
                msg.id, event.chat_id, target_id, mode,
            )
            await self.event_bus.emit(
                "message_mirrored",
                source_chat=event.chat_id,
                target_chat=target_id,
                message_id=msg.id,
            )
        except Exception as e:
            self.logger.error(
                "镜像消息 %d 到 %d 失败: %s", msg.id, target_id, e
            )
