# TG Manager — 进度跟踪

## Phase 1: 基础骨架 ✅
- [x] 项目初始化：CLAUDE.md、pyproject.toml、.gitignore、.env.example
- [x] `src/core/config.py` — 配置加载与验证（含 AttrDict 属性访问）
- [x] `src/core/rate_limiter.py` — 速率限制器
- [x] `src/core/event_bus.py` — 事件总线
- [x] `src/core/exceptions.py` + `constants.py`
- [x] `src/clients/userbot.py` — Userbot 客户端封装
- [x] `src/clients/bot.py` — Bot 客户端封装
- [x] `src/clients/dual_client.py` — 双客户端协调器
- [x] `src/database/engine.py` + `base.py` — 数据库初始化
- [x] `src/plugins/plugin_base.py` — 插件基类
- [x] `src/plugins/plugin_loader.py` — 插件加载器
- [x] `src/plugins/plugin_manager.py` — 插件管理器
- [x] `src/main.py` — 程序入口
- [x] `src/bot_interface/command_router.py` + `start_handler.py`
- [x] `config/config.example.yaml`
- [x] `src/utils/` — 文本/时间/验证/媒体工具
- [x] `scripts/setup_session.py` — Session 设置脚本

## Phase 2: 核心功能 ✅
- [x] 数据库 models（TelegramMessage/Chat/User/AutoReplyRule/ForwardRule）
- [x] 数据库 repositories（BaseRepo/MessageRepo/ChatRepo/RuleRepo/ForwardRuleRepo）
- [x] 消息管理插件（sender/forwarder）
- [x] 频道管理插件（mirror/copy_clean）
- [x] 群组管理插件（admin_actions/welcome）
- [x] 自动回复插件（rule_engine/template_reply）
- [x] 监控插件（keyword_alert）
- [x] Bot 界面完善（admin_handler/plugin_handler/config_handler）
- [x] main.py 集成所有新处理器

## Phase 3: AI + 定时功能
- [ ] LLM 统一接口层
- [ ] AI 总结插件组
- [ ] 定时任务插件组
- [ ] Bot AI 命令处理器

## Phase 4: 完善与高级功能
- [ ] 反垃圾插件组
- [ ] 媒体插件组
- [ ] 剩余消息/频道/群组/监控插件
- [ ] Docker 部署文件
- [ ] 数据库迁移
