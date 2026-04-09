"""菜单构建器

提供构建各类 InlineKeyboard 菜单的静态方法，
包括主菜单、插件列表、确认对话框等常用布局。
"""

from telethon import Button


class MenuBuilder:
    """构建 InlineKeyboard 菜单

    提供一组静态方法，用于生成标准化的按钮布局。
    所有方法返回 Telethon Button 的嵌套列表。
    """

    @staticmethod
    def main_menu() -> list[list[Button]]:
        """主菜单

        Returns:
            包含所有功能模块入口的按钮布局
        """
        return [
            [
                Button.inline("📨 消息管理", b"menu_message"),
                Button.inline("📢 频道管理", b"menu_channel"),
            ],
            [
                Button.inline("👥 群组管理", b"menu_group"),
                Button.inline("🤖 自动回复", b"menu_auto_reply"),
            ],
            [
                Button.inline("⏰ 定时任务", b"menu_scheduler"),
                Button.inline("📝 AI 总结", b"menu_ai_summary"),
            ],
            [
                Button.inline("🔍 监控", b"menu_monitor"),
                Button.inline("🛡 反垃圾", b"menu_antispam"),
            ],
            [Button.inline("⚙️ 系统设置", b"menu_settings")],
        ]

    @staticmethod
    def back_button(target: str = "main") -> list[Button]:
        """返回按钮

        Args:
            target: 返回目标菜单名称，默认为主菜单

        Returns:
            包含单个返回按钮的列表
        """
        return [Button.inline("« 返回", f"menu_{target}".encode())]

    @staticmethod
    def plugin_list(plugins: list[dict]) -> list[list[Button]]:
        """插件列表菜单

        根据插件信息生成带有启用/禁用状态图标的按钮列表。

        Args:
            plugins: 插件信息字典列表，每项需包含 name 字段，
                     可选 enabled 字段（默认 True）

        Returns:
            插件按钮布局，末尾附带返回按钮
        """
        buttons: list[list[Button]] = []

        for p in plugins:
            status_icon = "✅" if p.get("enabled", True) else "❌"
            buttons.append([
                Button.inline(
                    f"{status_icon} {p['name']}",
                    f"plugin_{p['name']}".encode(),
                )
            ])

        # 添加返回主菜单按钮
        buttons.append(MenuBuilder.back_button())
        return buttons

    @staticmethod
    def confirm(action: str) -> list[list[Button]]:
        """确认对话框

        Args:
            action: 操作标识，用于生成回调数据

        Returns:
            包含确认和取消按钮的布局
        """
        return [
            [
                Button.inline("✅ 确认", f"confirm_{action}".encode()),
                Button.inline("❌ 取消", b"cancel"),
            ],
        ]
