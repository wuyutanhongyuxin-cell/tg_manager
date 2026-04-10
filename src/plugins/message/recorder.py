"""Incoming/outgoing message recorder plugin."""

from __future__ import annotations

from typing import Any

from telethon import events
from telethon.tl.types import PeerChannel, PeerChat, PeerUser

from src.database.repositories.message_repo import MessageRepository
from src.plugins.plugin_base import PluginBase


class MessageRecorderPlugin(PluginBase):
    """Persist Telegram messages so search/summarization have a real data source."""

    @property
    def name(self) -> str:
        return "message.recorder"

    @property
    def description(self) -> str:
        return "Persist incoming and outgoing Telegram messages to the database"

    async def setup(self) -> None:
        self.client.userbot.client.add_event_handler(
            self._on_new_message,
            events.NewMessage(),
        )
        self._register_handler(self._on_new_message)
        self.logger.info("message recorder plugin started")

    async def teardown(self) -> None:
        for handler in self._handlers:
            self.client.userbot.client.remove_event_handler(handler)
        self._handlers.clear()

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        try:
            message = event.message
            session = self.db.get_session()
            async with session:
                async with session.begin():
                    repo = MessageRepository(session)
                    await repo.upsert(
                        message_id=message.id,
                        chat_id=event.chat_id,
                        sender_id=message.sender_id,
                        date=message.date,
                        text=message.message or "",
                        media_type=self._get_media_type(message),
                        is_forward=bool(message.fwd_from),
                        forward_from_chat_id=self._peer_to_chat_id(
                            getattr(message.fwd_from, "from_id", None)
                        ),
                        forward_from_msg_id=getattr(message.fwd_from, "channel_post", None),
                        reply_to_msg_id=getattr(message.reply_to, "reply_to_msg_id", None),
                        grouped_id=message.grouped_id,
                        views=message.views,
                        is_pinned=bool(getattr(message, "pinned", False)),
                    )

            await self.event_bus.emit(
                "message_received",
                chat_id=event.chat_id,
                message_id=message.id,
                sender_id=message.sender_id,
                outgoing=bool(event.out),
            )
        except Exception as exc:
            self.logger.error("failed to persist message %s: %s", event.message.id, exc)

    @staticmethod
    def _peer_to_chat_id(peer: Any) -> int | None:
        if isinstance(peer, PeerChannel):
            return -1000000000000 - peer.channel_id
        if isinstance(peer, PeerChat):
            return -peer.chat_id
        if isinstance(peer, PeerUser):
            return peer.user_id
        return None

    @staticmethod
    def _get_media_type(message: Any) -> str | None:
        if getattr(message, "photo", None):
            return "photo"
        if getattr(message, "video", None):
            return "video"
        if getattr(message, "audio", None):
            return "audio"
        if getattr(message, "voice", None):
            return "voice"
        if getattr(message, "document", None):
            return "document"
        return None
