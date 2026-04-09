# CLAUDE.md — AI 编程规范（TG Manager 项目）

> 把这个文件放在项目根目录。Claude Code 每次启动自动读取。

---

## [项目专属区域]

### 项目名称
TG Manager

### 一句话描述
全功能 Telegram 管理工具 — 集消息/频道/群组管理、自动转发、定时发送、自动回复、AI 内容总结、监控抓取、反垃圾于一体的 Python 脚本，面向个人用户和小团队运营者。

### 技术栈

| 组件 | 选型 | 版本要求 |
|------|------|----------|
| 语言 | Python | 3.11+ |
| Userbot 核心 | Telethon (MTProto) | >=1.36.0 |
| Bot 交互 | Telethon Bot 模式 | 同上 |
| 数据库 ORM | SQLAlchemy async | >=2.0 |
| 开发数据库 | SQLite + aiosqlite | >=0.19 |
| 生产数据库 | PostgreSQL + asyncpg | >=0.29 |
| 定时调度 | APScheduler | >=3.10 |
| HTTP 客户端 | httpx | >=0.27（调用 LLM API） |
| 配置 | YAML + python-dotenv | pyyaml>=6.0 |
| AI/LLM | 多模型统一接口 | OpenAI/Claude/Gemini/DeepSeek/Ollama |
| RSS | feedparser | >=6.0 |
| 内容提取 | beautifulsoup4 + readability-lxml | - |
| 部署 | Docker Compose | - |

**注意：不要引入上表之外的依赖。需要新库时先问我。**

### 当前阶段
Phase 3 已完成（AI + 定时功能），准备 Phase 4（完善与高级功能）。详见 `tasks/todo.md`。

---

## 开发者背景

我不是专业开发者，使用 Claude Code 辅助编程。请：
- 代码加中文注释，关键逻辑额外解释
- 遇到复杂问题先给方案让我确认，不要直接大改
- 报错时解释原因 + 修复方案，不要只贴代码
- 优先最简实现，不要过度工程化

---

## 项目专属规范

### 架构核心原则

1. **双客户端分工**：Userbot 负责高权限执行（受限频道、成员操作），Bot 负责用户交互（命令、菜单、通知推送）。能用 Bot 做的绝不用 Userbot。
2. **插件化一切**：所有功能以插件形式存在，通过 `PluginBase` 基类 + `PluginManager` 管理。新功能 = 新插件文件，不改核心代码。
3. **防封号第一**：所有 Telegram API 调用必须经过 `RateLimiter`。触发 `FloodWaitError` 时自动退避，绝不硬重试。
4. **LLM 可插拔**：所有 AI 调用通过 `BaseLLMProvider` 统一接口，配置切换模型，不在业务代码中硬编码任何模型名。

### Telethon 使用规范

- Userbot 和 Bot 都使用 Telethon（不混用 python-telegram-bot），保持 API 风格统一
- 所有客户端操作使用 async/await，绝不使用同步阻塞调用
- Session 文件（`.session`）必须加入 `.gitignore`，绝不提交
- 首次登录通过 `scripts/setup_session.py` 交互式完成，运行时使用已有 session
- 捕获所有 `telethon.errors` 异常，特别是 `FloodWaitError`、`ChatAdminRequiredError`、`UserBannedInChannelError`

### 速率限制规则（硬性）

```
全局：每分钟 30 条消息，每秒 1 条
单聊天：每 3 秒 1 条
加入群组：每天 20 个
添加成员：每天 50 个，间隔 30 秒
文件下载：并发最多 3 个
FloodWait：等待 Telegram 指定秒数 * 1.5 倍
连续 3 次 FloodWait：暂停所有操作 5 分钟
所有间隔添加 0.5-2 秒随机抖动
```

### 插件开发规范

每个插件文件必须：
1. 继承 `PluginBase`，实现 `name`、`description`、`setup()`、`teardown()`
2. 在 `setup()` 中注册事件处理器
3. 在 `teardown()` 中取消所有注册
4. 所有 Telegram 操作通过 `self.client`（DualClient）而非直接调用 Telethon
5. 所有 LLM 调用通过 `self.llm_provider` 而非直接调用 API
6. 异步方法，不使用阻塞 I/O

### 配置规范

- 敏感信息（API Key、Bot Token、手机号）放 `.env`
- 结构化配置放 `config/config.yaml`
- 配置通过 `${ENV_VAR}` 语法引用环境变量
- 每个插件的专属配置放在 `plugin_config.<plugin_name>` 下
- 绝不在代码中硬编码任何密钥、chat_id、手机号

### 数据库规范

- 开发用 SQLite，生产用 PostgreSQL，通过配置切换
- 所有操作使用 `async with session_factory() as session`
- 模型定义在 `database/models/`，每个表一个文件
- CRUD 操作通过 `repositories/` 封装，业务代码不直接写 SQL

---

## 上下文管理规范

### 文件行数硬限制

| 文件类型 | 最大行数 | 超限动作 |
|----------|----------|----------|
| 单个源代码文件 | **200 行** | 立即拆分 |
| 测试文件 | **300 行** | 按功能拆分 |
| 配置文件 | **100 行** | 拆分 |

### 关键词触发

| 我说 | 你做 |
|------|------|
| "清理一下" | 行数审计 + 死代码检测 + TODO 清理 |
| "拆一下" | 检查文件行数，给出拆分方案 |
| "健康检查" | 完整项目健康度检查 |
| "现在到哪了" | 总结当前进度，参考 todo.md |

---

## 编码规范

### 错误处理
- 所有外部调用必须 try-except
- 失败时 graceful degradation：日志记录 + 友好提示
- Telegram FloodWaitError 特殊处理：自动等待后重试

### 函数设计
- 单个函数不超过 30 行
- 函数名用动词开头
- 每个函数有 docstring

### 依赖管理
- 不要自行引入新依赖
- 每次新增依赖立即更新 requirements.txt

### 配置管理
- 敏感信息放 `.env`
- 非敏感配置放 `config/config.yaml`
- 绝不在代码中硬编码任何密钥或 URL

---

## Git 规范

### Commit 信息格式
```
<类型>: <一句话描述>
类型：feat | fix | refactor | docs | chore
```

### 每次 commit 前
- 确认没有把 .env、.session、__pycache__/ 提交进去
- 确认代码能正常运行
