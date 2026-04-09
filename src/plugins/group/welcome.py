"""欢迎消息插件

当新用户加入群组时，发送欢迎消息。
支持自定义欢迎模板，使用变量替换。
"""

from telethon import events

from src.plugins.plugin_base import PluginBase


class WelcomePlugin(PluginBase):
    """欢迎消息插件 — 新成员加入时自动发送欢迎消息"""

    @property
    def name(self) -> str:
        return "group.welcome"

    @property
    def description(self) -> str:
        return "新成员加入群组时发送欢迎消息"

    async def setup(self) -> None:
        """注册群组加入事件处理器"""
        # 使用 Bot 监听（Bot 通常是群管理员，能收到加入事件）
        self.client.bot.client.add_event_handler(
            self._on_user_joined, events.ChatAction()
        )
        self._register_handler(self._on_user_joined)

        # 从配置加载欢迎模板
        cfg = self.get_plugin_config()
        self._template = cfg.get(
            "template",
            "欢迎 {user_name} 加入 {chat_title}！",
        )
        self._enabled_chats: list[int] = cfg.get("enabled_chats", [])
        self.logger.info("欢迎消息插件已启动")

    async def teardown(self) -> None:
        """移除事件处理器"""
        for handler in self._handlers:
            self.client.bot.client.remove_event_handler(handler)
        self._handlers.clear()

    async def _on_user_joined(self, event: events.ChatAction.Event) -> None:
        """处理用户加入事件"""
        try:
            # 仅处理加入事件
            if not (event.user_joined or event.user_added):
                return

            # 检查是否在启用的聊天列表中（空列表=全部群组）
            if self._enabled_chats and event.chat_id not in self._enabled_chats:
                return

            user = await event.get_user()
            chat = await event.get_chat()
            if not user:
                return

            # 渲染欢迎消息模板（转义用户可控字段中的花括号，防止模板注入）
            user_name = self._get_display_name(user)
            chat_title = getattr(chat, "title", "群组")
            safe_name = user_name.replace("{", "{{").replace("}", "}}")
            safe_title = chat_title.replace("{", "{{").replace("}", "}}")
            welcome_text = self._template.format(
                user_name=safe_name,
                user_id=user.id,
                chat_title=safe_title,
                chat_id=event.chat_id,
            )

            await self.client.bot.send_message(event.chat_id, welcome_text)
            self.logger.info("已发送欢迎消息给 %s (chat: %d)", user_name, event.chat_id)

        except Exception as e:
            self.logger.error("发送欢迎消息失败: %s", e)

    @staticmethod
    def _get_display_name(user) -> str:
        """获取用户显示名称"""
        if user.username:
            return f"@{user.username}"
        name = user.first_name or ""
        if user.last_name:
            name += f" {user.last_name}"
        return name or f"用户{user.id}"
