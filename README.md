# TG Manager

Telegram 管理工具，基于 Telethon、SQLAlchemy、APScheduler 和多提供商 LLM 封装构建，包含 Bot 交互层、Userbot 执行层、插件系统、消息归档和 AI 总结能力。

## 当前状态

已接通：

- 消息转发、复制、去标记复制
- 频道镜像同步
- 群组管理命令：`/ban`、`/mute`、`/warn`、`/kick`
- 欢迎消息
- 关键词监控告警
- AI 聊天总结、URL 总结、问答
- 定时任务发送
- 插件管理与配置摘要
- Telegram 消息入库，供搜索和总结复用

尚未接通：

- `media.*`
- `antispam.*`

这两类目录目前仍是预留占位，不应默认视为可用功能。

## 环境要求

- Python 3.11+
- Telegram `api_id` / `api_hash`
- Bot Token
- 一个可登录的 Telegram 用户账号，用于 Userbot session

## 安装

```bash
git clone https://github.com/wuyutanhongyuxin-cell/tg_manager.git
cd tg_manager
python -m pip install -e .
```

如果你只想装运行依赖，也可以使用：

```bash
python -m pip install -r requirements.txt
```

如果你的本机 `pip/setuptools` 较旧，`pip install -e .` 可能会因为缺少 PEP 660 editable 支持而失败。此时先升级工具链：

```bash
python -m pip install -U pip setuptools wheel
```

## 配置

1. 复制环境变量模板并填写凭据。

```bash
cp .env.example .env
```

建议至少配置：

```env
TG_API_ID=12345678
TG_API_HASH=abcdef1234567890abcdef1234567890
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_ADMIN_USER_ID=987654321
DATABASE_URL=sqlite+aiosqlite:///data/tg_manager.db
```

2. 复制配置模板。

```bash
cp config/config.example.yaml config/config.yaml
```

说明：

- `plugin_config` 现在支持“分组键 + 全名键”两层配置。
- 例如 `ai_summary` 会作用于 `ai_summary.*` 下的插件。
- 如果再配置 `ai_summary.chat_summarizer`，它会覆盖同名字段。

## 首次登录 Userbot

```bash
python scripts/setup_session.py
```

按提示完成验证码和二次验证，生成 `sessions/userbot.session`。

## 启动

```bash
python -m src.main
```

默认 SQLite 路径为 `data/tg_manager.db`。当前代码会自动创建缺失父目录。

## 命令

所有人可用：

- `/start`
- `/help`

仅管理员可用：

- `/status`
- `/plugins`
- `/reload <plugin_name>`
- `/config`
- `/ban <user_id> [原因]`
- `/mute <user_id> [分钟]`
- `/warn <user_id> [原因]`
- `/kick <user_id>`
- `/summarize [N]`
- `/ask <问题>`
- `/url <链接>`
- `/schedule list`
- `/schedule add <name> <cron(5段)> <message>`
- `/schedule remove <job_id>`

补充：

- 回复某条消息执行 `/mute 10` 时，现在会正确按 10 分钟处理。
- `/command@OtherBot` 不会再被本项目误接收。

## 插件配置约定

插件名采用 `category.plugin_name` 形式，例如：

- `message.sender`
- `message.recorder`
- `channel.mirror`
- `ai_summary.chat_summarizer`

`plugin_config` 支持如下写法：

```yaml
plugin_config:
  ai_summary:
    language: "zh-CN"
    chat_summary_limit: 200

  ai_summary.chat_summarizer:
    chat_summary_limit: 300
```

最终结果会按“分组默认值 + 全名覆盖值”合并。

## 菜单说明

主菜单只展示当前已接通的模块。点击后会显示对应模块的真实能力摘要，不再统一回退到“开发中”。

## 测试

```bash
python -m pytest -q
```

当前仓库已补入最小测试，覆盖：

- 插件配置合并
- SQLite 父目录创建
- 命令路由的 Bot 用户名匹配
- `/mute` 参数解析

## 技术栈

- Telethon
- SQLAlchemy 2.x async
- APScheduler 3.x
- httpx
- PyYAML
- python-dotenv

## 许可证

MIT
