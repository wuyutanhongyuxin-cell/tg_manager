"""模板回复插件

订阅 auto_reply_matched 事件，渲染模板变量并发送回复。
支持 {user_name}、{chat_title}、{date} 等变量替换。
"""

from datetime import datetime, timezone

from src.plugins.plugin_base import PluginBase


class TemplateReplyPlugin(PluginBase):
    """模板回复插件 — 处理自动回复的模板渲染和发送"""

    @property
    def name(self) -> str:
        return "auto_reply.template_reply"

    @property
    def description(self) -> str:
        return "模板变量替换和自动回复发送"

    async def setup(self) -> None:
        """订阅规则匹配事件"""
        await self.event_bus.subscribe(
            "auto_reply_matched", self._handle_matched
        )
        self.logger.info("模板回复插件已启动")

    async def teardown(self) -> None:
        """取消事件订阅"""
        await self.event_bus.unsubscribe(
            "auto_reply_matched", self._handle_matched
        )

    async def _handle_matched(self, **kwargs) -> None:
        """处理规则匹配事件，渲染模板并发送回复

        期望的 kwargs:
            event: Telethon 消息事件
            response: 回复模板文本
            chat_id: 聊天 ID
        """
        try:
            event = kwargs.get("event")
            response_template = kwargs.get("response", "")
            chat_id = kwargs.get("chat_id")

            if not event or not response_template or not chat_id:
                return

            # 获取用户和聊天信息用于变量替换
            sender = await event.get_sender()
            chat = await event.get_chat()

            # 渲染模板
            reply_text = self._render_template(
                response_template, sender, chat, event
            )

            # 通过 Bot 发送回复
            await self.client.bot.reply(event, reply_text)
            self.logger.debug("已发送模板回复到聊天 %s", chat_id)

        except Exception as e:
            self.logger.error("发送模板回复失败: %s", e)

    def _render_template(self, template: str, sender, chat, event) -> str:
        """渲染模板，替换变量

        支持的变量:
            {user_name} — 发送者显示名
            {user_id} — 发送者 ID
            {username} — 发送者 @用户名
            {chat_title} — 聊天标题
            {chat_id} — 聊天 ID
            {date} — 当前日期
            {time} — 当前时间
            {message} — 原始消息文本
        """
        now = datetime.now(timezone.utc)
        user_name = ""
        if sender:
            user_name = getattr(sender, "first_name", "") or ""
            if getattr(sender, "last_name", None):
                user_name += f" {sender.last_name}"

        variables = {
            "user_name": user_name or "用户",
            "user_id": str(getattr(sender, "id", "")),
            "username": getattr(sender, "username", "") or "",
            "chat_title": getattr(chat, "title", "聊天") or "聊天",
            "chat_id": str(event.chat_id),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "message": event.raw_text or "",
        }

        try:
            return template.format(**variables)
        except KeyError as e:
            self.logger.warning("模板变量未定义: %s", e)
            return template
