"""Bot 命令路由分发

负责注册和管理所有 Bot 命令处理器，
将命令与对应的处理函数绑定到 Telethon 事件系统。
"""

import logging
from telethon import events
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CommandRouter:
    """注册和分发 Bot 命令

    维护一个命令注册表，在 setup() 时将所有命令
    绑定到 BotClient 的事件处理器。
    """

    def __init__(self, bot_client: Any) -> None:
        """初始化命令路由器

        Args:
            bot_client: BotClient 实例，提供 client 属性用于事件绑定
        """
        self._bot = bot_client
        self._commands: dict[str, dict[str, Any]] = {}  # command -> {handler, description}

    def register(self, command: str, handler: Callable, description: str = "") -> None:
        """注册命令处理器

        Args:
            command: 命令名（不含 /）
            handler: async 处理函数，接收 event 参数
            description: 命令描述，用于帮助信息
        """
        self._commands[command] = {
            "handler": handler,
            "description": description,
        }

    def setup(self) -> None:
        """将所有已注册的命令绑定到 Bot 客户端事件

        遍历命令注册表，为每个命令创建 Telethon 事件处理器。
        必须在所有命令注册完成后调用。
        """
        for cmd, info in self._commands.items():
            # 严格锚定命令匹配：仅匹配 /cmd 或 /cmd 后跟空格/@ 的情况
            pattern = rf"^/{cmd}(?:\s|@|$)"
            handler = info["handler"]

            # 绑定到 Telethon 事件系统
            self._bot.client.on(
                events.NewMessage(pattern=pattern, incoming=True)
            )(handler)

            logger.info(f"注册命令: /{cmd} - {info['description']}")

    def get_commands(self) -> list[dict[str, str]]:
        """返回所有已注册命令的列表

        Returns:
            命令信息列表，每项包含 command 和 description
        """
        return [
            {"command": f"/{cmd}", "description": info["description"]}
            for cmd, info in self._commands.items()
        ]
