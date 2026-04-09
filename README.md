# TG Manager

**全功能 Telegram 管理工具** -- 集消息管理、频道镜像、群组管理、自动转发、自动回复、AI 内容总结、关键词监控、反垃圾于一体的 Python 自动化框架。

```
  _____ ____   __  __
 |_   _/ ___| |  \/  | __ _ _ __   __ _  __ _  ___ _ __
   | || |  _  | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|
   | || |_| | | |  | | (_| | | | | (_| | (_| |  __/ |
   |_| \____| |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|
                                          |___/
```

---

## 核心特性

| 功能域 | 能力 | 状态 |
|--------|------|------|
| **消息管理** | 发送/转发/编辑/搜索/导出 | Phase 2 |
| **频道管理** | 镜像同步/去标签复制/发布/统计 | Phase 2 |
| **群组管理** | ban/mute/warn/kick/欢迎消息 | Phase 2 |
| **自动回复** | 关键词/正则/精确匹配 + 模板回复 | Phase 2 |
| **关键词监控** | 实时告警推送到管理员 | Phase 2 |
| **AI 总结** | 群聊总结/链接摘要（多模型） | ✅ Phase 3 |
| **定时任务** | Cron 定时消息发送 | ✅ Phase 3 |
| **反垃圾** | CAPTCHA/垃圾检测/黑名单 | Phase 4 |
| **媒体处理** | 批量下载/上传/格式转换 | Phase 4 |

---

## 架构设计

### 双客户端协作

```
用户 --> Bot 接收命令 --> 命令路由器 --> 插件逻辑层
                                         |-- Bot 执行（低风险操作）
                                         |-- Userbot 执行（高权限操作）
                                         '-- LLM 调用（AI 处理）
                                     --> 结果聚合 --> Bot 推送给用户
```

| 能力 | Userbot (MTProto) | Bot |
|------|-------------------|-----|
| 身份 | 个人账号 | @YourManagerBot |
| 消息监听 | 所有群/频道（含受限） | 被添加为管理员的群 |
| 受限内容 | 可读取 | 不可 |
| 交互界面 | 无 | InlineKeyboard/Command |
| 封号风险 | 高（需限速） | 极低 |

**原则：能用 Bot 做的绝不用 Userbot。**

### 插件系统

所有功能以插件形式存在，通过 `PluginBase` 基类统一管理：

```python
class MyPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "category.my_plugin"

    async def setup(self) -> None:
        # 注册事件处理器
        await self.event_bus.subscribe("some_event", self._handler)

    async def teardown(self) -> None:
        # 清理资源
        await self.event_bus.unsubscribe("some_event", self._handler)
```

插件通过事件总线解耦通信，无需直接依赖其他插件。

### 防封号策略（四层限速）

```
层级 1: 全局        -- 每分钟 30 条，每秒 1 条
层级 2: 单聊天      -- 同一聊天每 3 秒 1 条
层级 3: 操作类型    -- 加群每天 20 个，加人每天 50 个
层级 4: FloodWait   -- 等待 Telegram 指定秒数 x 1.5 倍
额外: 随机延迟 0.5~2s、连续 3 次 FloodWait 暂停 5 分钟
```

---

## 项目结构

```
tg_manager/
├── config/
│   └── config.example.yaml        # 配置模板
├── src/
│   ├── main.py                    # 程序入口
│   ├── core/                      # 核心基础设施
│   │   ├── config.py              #   配置加载与验证
│   │   ├── event_bus.py           #   异步事件总线
│   │   ├── rate_limiter.py        #   多维速率限制器
│   │   ├── exceptions.py          #   统一异常定义
│   │   └── constants.py           #   全局常量
│   ├── clients/                   # Telegram 客户端
│   │   ├── userbot.py             #   Userbot MTProto 封装
│   │   ├── bot.py                 #   Bot 客户端封装
│   │   └── dual_client.py         #   双客户端协调器
│   ├── database/                  # 数据库层
│   │   ├── engine.py              #   AsyncEngine 初始化
│   │   ├── models/                #   ORM 模型 (5 个)
│   │   └── repositories/          #   Repository 模式 (5 个)
│   ├── plugins/                   # 插件系统
│   │   ├── plugin_base.py         #   插件抽象基类
│   │   ├── plugin_loader.py       #   自动发现与加载
│   │   ├── plugin_manager.py      #   生命周期管理
│   │   ├── message/               #   消息管理插件组
│   │   ├── channel/               #   频道管理插件组
│   │   ├── group/                 #   群组管理插件组
│   │   ├── auto_reply/            #   自动回复插件组
│   │   └── monitor/               #   监控插件组
│   ├── bot_interface/             # Bot 交互界面
│   │   ├── command_router.py      #   命令路由
│   │   ├── callback_router.py     #   回调路由
│   │   ├── menu_builder.py        #   InlineKeyboard 构建
│   │   ├── handlers/              #   命令处理器 (4 个)
│   │   └── middlewares/           #   权限检查 + 节流
│   └── utils/                     # 公共工具
├── scripts/
│   └── setup_session.py           # 首次登录脚本
└── tasks/
    └── todo.md                    # 进度跟踪
```

> 68 个 Python 文件，~4800 行代码，所有单文件控制在 200 行以内。

---

## 快速开始

### 前置要求

- Python 3.11+
- Telegram 账号（获取 API ID/Hash）
- Bot Token（通过 @BotFather 创建）

### 1. 克隆项目

```bash
git clone https://github.com/wuyutanhongyuxin-cell/tg_manager.git
cd tg_manager
```

### 2. 安装依赖

```bash
pip install -e .
# 或者
pip install -r requirements.txt
```

### 3. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的凭据
# TG_API_ID      -- 从 https://my.telegram.org 获取
# TG_API_HASH    -- 同上
# TG_BOT_TOKEN   -- 从 @BotFather 获取
# TG_ADMIN_USER_ID -- 你的 Telegram 数字 ID
# DATABASE_URL   -- 默认 SQLite，生产建议 PostgreSQL
```

```bash
# 复制配置文件模板
cp config/config.example.yaml config/config.yaml
# 按需调整插件开关、速率限制等参数
```

### 4. 首次登录

```bash
python scripts/setup_session.py
```

按照提示输入手机号和验证码，完成 Userbot 的 Telethon session 创建。

### 5. 启动

```bash
python -m src.main
```

启动后，向你的 Bot 发送 `/start` 即可开始使用。

---

## Bot 命令一览

| 命令 | 说明 | 权限 |
|------|------|------|
| `/start` | 显示欢迎信息和功能概览 | 所有人 |
| `/help` | 显示帮助信息 | 所有人 |
| `/status` | 查看系统运行状态 | 管理员 |
| `/plugins` | 列出所有已加载插件 | 管理员 |
| `/reload <name>` | 热重载指定插件 | 管理员 |
| `/config` | 查看当前配置摘要 | 管理员 |
| `/ban` | 封禁用户（回复消息或指定 ID） | 管理员 |
| `/mute [分钟]` | 禁言用户 | 管理员 |
| `/warn` | 警告用户（达阈值自动封禁） | 管理员 |
| `/kick` | 踢出用户 | 管理员 |
| `/summarize [N]` | AI 总结当前群聊最近 N 条消息 | 管理员 |
| `/ask <问题>` | AI 问答 | 管理员 |
| `/url <链接>` | 提取并总结 URL 内容 | 管理员 |
| `/schedule list` | 查看定时任务列表 | 管理员 |
| `/schedule add` | 添加定时发送任务（cron 表达式） | 管理员 |
| `/schedule remove <ID>` | 删除定时任务 | 管理员 |

---

## 配置说明

### 环境变量 (`.env`)

存放**敏感信息**，绝不提交到 Git：

```env
TG_API_ID=12345678
TG_API_HASH=abcdef1234567890abcdef1234567890
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_ADMIN_USER_ID=987654321
DATABASE_URL=sqlite+aiosqlite:///data/tg_manager.db
```

### 配置文件 (`config/config.yaml`)

存放**结构化配置**，通过 `${ENV_VAR}` 引用环境变量：

```yaml
# 插件启用控制（支持通配符）
plugins:
  enabled:
    - "message.*"      # 全部消息插件
    - "channel.mirror"  # 仅频道镜像
    - "group.*"         # 全部群组插件

# 插件专属配置
plugin_config:
  keyword_alert:
    keywords: ["重要", "紧急", "urgent"]
    alert_target: ${TG_ADMIN_USER_ID}
```

---

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 核心框架 | [Telethon](https://github.com/LonamiWebs/Telethon) | MTProto 协议，Userbot + Bot 统一 API |
| 数据库 ORM | SQLAlchemy 2.0 async | 支持 SQLite（开发）/ PostgreSQL（生产）|
| 定时调度 | APScheduler | Cron 表达式定时任务 |
| HTTP 客户端 | httpx | 异步调用 LLM API |
| AI/LLM | 多模型统一接口 | OpenAI / Claude / Gemini / DeepSeek / Ollama |
| 配置 | YAML + python-dotenv | 结构化配置 + 敏感信息隔离 |

---

## 开发指南

### 添加新插件

1. 在 `src/plugins/<category>/` 下创建新文件
2. 继承 `PluginBase`，实现 `name`、`description`、`setup()`、`teardown()`
3. 通过事件总线与其他插件通信
4. 所有 Telegram 操作经 `self.client`（DualClient），自动限速

```python
# src/plugins/my_category/my_feature.py
from src.plugins.plugin_base import PluginBase

class MyFeaturePlugin(PluginBase):
    @property
    def name(self) -> str:
        return "my_category.my_feature"

    @property
    def description(self) -> str:
        return "我的自定义功能"

    async def setup(self) -> None:
        await self.event_bus.subscribe("trigger_event", self._handler)
        self.logger.info("自定义插件已启动")

    async def teardown(self) -> None:
        await self.event_bus.unsubscribe("trigger_event", self._handler)

    async def _handler(self, **kwargs) -> None:
        # 你的业务逻辑
        await self.client.send_message(
            kwargs["chat_id"], "Hello!", prefer_bot=True
        )
```

### 代码规范

- 单文件不超过 **200 行**，单函数不超过 **30 行**
- 所有异步操作使用 `async/await`
- Telegram API 调用必须经过 `RateLimiter`
- 异常处理：`try-except` + 日志记录 + 优雅降级

---

## 开发路线图

- [x] **Phase 1** -- 基础骨架（核心模块 + 客户端 + 数据库 + 插件系统）
- [x] **Phase 2** -- 核心功能（消息/频道/群组/自动回复/监控插件 + Bot 界面）
- [ ] **Phase 3** -- AI + 定时功能（LLM 统一接口 + AI 总结 + 定时任务）
- [ ] **Phase 4** -- 完善（反垃圾 + 媒体 + Docker 部署 + 数据库迁移）

---

## 许可证

MIT License

---

## 致谢

- [Telethon](https://github.com/LonamiWebs/Telethon) -- 强大的 Telegram MTProto 库
- [SQLAlchemy](https://www.sqlalchemy.org/) -- Python SQL 工具包
- [APScheduler](https://github.com/agronholm/apscheduler) -- 高级定时调度

---

> Built with Claude Code (Opus 4.6)
