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
- [x] 数据库 repositories（BaseRepo/MessageRepo/ChatRepo/RuleRepo/ForwardRuleRepo/UserRepo）
- [x] 消息管理插件（sender/forwarder）
- [x] 频道管理插件（mirror/copy_clean）
- [x] 群组管理插件（admin_actions/welcome）
- [x] 自动回复插件（rule_engine/template_reply）
- [x] 监控插件（keyword_alert）
- [x] Bot 界面完善（admin_handler/plugin_handler/config_handler）
- [x] main.py 集成所有新处理器

## 代码审查 ✅（2026-04-09）
三模型审查：Codex (gpt-5.3-codex, high) + Sonnet 4.6 + Opus 4.6 裁定

### 已修复（27 项）
- [x] **CRITICAL**: 插件配置读错字段 `enabled_plugins` → `plugins.enabled`
- [x] **MEDIUM**: upsert 竞态条件 → 原子 ON CONFLICT（SQLite + PostgreSQL 双方言）
- [x] **MEDIUM**: Userbot auth 失败未 disconnect → 添加 disconnect
- [x] **MEDIUM**: DualClient fallback 仅捕获 ClientError → 改为 Exception
- [x] **MEDIUM**: 插件回调缺少 admin 检查 → 添加权限校验
- [x] **MEDIUM**: Plugin reload 未清除模块缓存 → 添加 sys.modules 清除
- [x] **MEDIUM**: copy_clean 未规范化返回类型 → 处理 list + Message
- [x] **MEDIUM**: ChatBannedRights mute 不完整 → 添加 media/stickers/gifs/polls 等
- [x] **MEDIUM**: sender chat_id 存为 0 → 从 peer_id 解析标准 -100X 格式
- [x] **MEDIUM**: forwarder + mirror 双重转发 → forwarder 过滤频道消息
- [x] **MEDIUM**: RateLimiter 锁内 sleep 导致序列化 → 锁内计算/锁外 sleep
- [x] **MEDIUM**: 模板注入（str.format + 用户消息）→ 转义 {} 字符
- [x] **MEDIUM**: 缺 UserRepository → 创建 user_repo.py
- [x] **MEDIUM**: admin_actions 直接写 SQL → 改用 UserRepository
- [x] **MEDIUM**: FloodWait 绕过 RateLimiter → 统一委托
- [x] **MEDIUM**: dual_client.stop() 时序 → 先 emit 再断连
- [x] **LOW**: 命令正则未锚定 → `^/cmd(?:\s|@|$)`
- [x] **LOW**: callback decode 无容错 → `errors="replace"`
- [x] **LOW**: /reload 泄露原始异常 → 仅输出通用消息
- [x] **LOW**: setup_logging 空目录名 → guard check
- [x] **LOW**: 未使用 import 清理（sqlite_insert、ChatRepository）
- [x] **LOW**: admin_actions teardown 魔法字符串 → 显式字典映射
- [x] **LOW**: keyword_alert 属性缺失 → 提前初始化 _compiled_regex
- [x] **LOW**: event_bus.emit() 文档纠正（非 fire-and-forget）

### 已知但暂缓（Phase 3+ 处理）
- [ ] 规则/转发规则内存缓存（每条消息查 DB，高频群性能问题）
- [ ] 测试覆盖（test_rate_limiter/test_event_bus/test_plugin_loader）
- [ ] _check_admin 重复实现统一为装饰器
- [ ] /status 添加 admin_only 权限检查
- [ ] throttle.py _last_call 字典无清理（内存泄漏）

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
