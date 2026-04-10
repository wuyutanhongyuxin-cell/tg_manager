"""Bot command routing helpers."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CommandRouter:
    """Register bot commands and bind them to Telethon handlers."""

    def __init__(self, bot_client: Any) -> None:
        self._bot = bot_client
        self._commands: dict[str, dict[str, Any]] = {}

    def register(self, command: str, handler: Callable, description: str = "") -> None:
        self._commands[command] = {
            "handler": handler,
            "description": description,
        }

    @staticmethod
    def matches_command(raw_text: str, command: str, bot_username: str = "") -> bool:
        """Match `/command` and `/command@ThisBot`, but reject other bot targets."""
        pattern = re.compile(
            rf"^/{re.escape(command)}(?:@(?P<target>[A-Za-z0-9_]+))?(?:\s|$)"
        )
        match = pattern.match(raw_text or "")
        if not match:
            return False

        target = match.group("target")
        if not target:
            return True

        return bool(bot_username) and target.lower() == bot_username.lower()

    def setup(self) -> None:
        from telethon import events

        bot_username = getattr(self._bot, "username", "")

        for cmd, info in self._commands.items():
            pattern = rf"^/{re.escape(cmd)}(?:@[A-Za-z0-9_]+)?(?:\s|$)"
            handler = info["handler"]

            self._bot.client.on(
                events.NewMessage(
                    incoming=True,
                    pattern=pattern,
                    func=lambda e, cmd=cmd, bot_username=bot_username: (
                        self.matches_command(e.raw_text, cmd, bot_username)
                    ),
                )
            )(handler)

            logger.info("registered command: /%s - %s", cmd, info["description"])

    def get_commands(self) -> list[dict[str, str]]:
        return [
            {"command": f"/{cmd}", "description": info["description"]}
            for cmd, info in self._commands.items()
        ]
