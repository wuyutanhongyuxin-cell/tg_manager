"""Helpers for building inline keyboard menus."""

from __future__ import annotations

from telethon import Button


class MenuBuilder:
    """Build consistent inline keyboard layouts."""

    @staticmethod
    def main_menu() -> list[list[Button]]:
        return [
            [
                Button.inline("消息管理", b"menu_message"),
                Button.inline("频道管理", b"menu_channel"),
            ],
            [
                Button.inline("群组管理", b"menu_group"),
                Button.inline("自动回复", b"menu_auto_reply"),
            ],
            [
                Button.inline("定时任务", b"menu_scheduler"),
                Button.inline("AI 总结", b"menu_ai_summary"),
            ],
            [
                Button.inline("监控告警", b"menu_monitor"),
                Button.inline("系统设置", b"menu_settings"),
            ],
        ]

    @staticmethod
    def back_button(target: str = "main") -> list[Button]:
        return [Button.inline("返回", f"menu_{target}".encode())]

    @staticmethod
    def plugin_list(plugins: list[dict]) -> list[list[Button]]:
        buttons: list[list[Button]] = []

        for plugin in plugins:
            status_icon = "✅" if plugin.get("enabled", True) else "❌"
            buttons.append(
                [
                    Button.inline(
                        f"{status_icon} {plugin['name']}",
                        f"plugin_{plugin['name']}".encode(),
                    )
                ]
            )

        buttons.append(MenuBuilder.back_button())
        return buttons

    @staticmethod
    def confirm(action: str) -> list[list[Button]]:
        return [
            [
                Button.inline("确认", f"confirm_{action}".encode()),
                Button.inline("取消", b"cancel"),
            ],
        ]
