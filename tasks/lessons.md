# TG Manager — 经验教训

> 记录开发过程中的错误模式和解决方案，避免重复犯错。

## 模板

```
### [日期] 问题简述
- **现象**：
- **原因**：
- **修复**：
- **规则**：今后应该...
```

---

### [2026-04-09] asyncio.Lock 内不能 sleep
- **现象**：RateLimiter.acquire() 在 `async with self._lock` 内执行多处 `await asyncio.sleep()`，导致所有消息发送被全局序列化，高并发下吞吐量趋近于 0
- **原因**：asyncio.Lock 不是可重入锁，持锁期间 sleep 会阻塞其他所有协程获取锁
- **修复**：锁内只计算需要等待的时间，锁外执行 sleep，再锁内更新时间戳
- **规则**：`async with lock:` 内绝不 await sleep/IO，只做计算和状态读写

### [2026-04-09] 插件间事件监听重叠导致双重执行
- **现象**：forwarder 和 mirror 都注册 `events.NewMessage()` 监听所有消息，频道消息被两个插件各转发一次
- **原因**：两个插件功能重叠，未明确职责边界
- **修复**：forwarder 添加 `func=lambda e: not e.is_channel` 过滤，频道消息专交 mirror
- **规则**：注册 Telethon 事件处理器时必须明确过滤条件，避免多个插件监听同一事件源

### [2026-04-09] str.format() 的模板注入风险
- **现象**：template_reply 用 `template.format(**variables)` 渲染回复，用户发送 `{user_id}` 会泄露实际 ID
- **原因**：用户消息作为 format 变量传入，未转义花括号
- **修复**：对用户输入 `message` 做 `replace("{", "{{").replace("}", "}}")` 转义
- **规则**：任何用户可控的字符串参与 str.format() 前必须转义 `{}` 或使用 string.Template

### [2026-04-09] 配置字段路径必须与实际 YAML 结构完全一致
- **现象**：plugin_manager 使用 `getattr(self._config, "enabled_plugins", [])` 读不到值，所有插件无条件加载
- **原因**：YAML 中实际路径是 `plugins.enabled`，代码读的是不存在的顶层属性
- **修复**：改为 `self._config.plugins.get("enabled", [])`
- **规则**：配置读取必须与 config.example.yaml 中的路径一一对应，新增配置项时先检查 YAML 结构

### [2026-04-09] 业务代码绝不直接写 SQL
- **现象**：admin_actions 中 `_increment_warn` 和 `_update_user_status` 直接 `from sqlalchemy import select` 操作 session
- **原因**：缺少 UserRepository，开发时图方便直接写
- **修复**：创建 `user_repo.py`，插件层只调用 repo 方法
- **规则**：发现需要 DB 操作但缺少 repo 时，先建 repo 再写业务逻辑，绝不绕过

### [2026-04-09] FloodWait 处理必须统一走 RateLimiter
- **现象**：clients 里的 `_handle_flood_wait` 独立实现 sleep，绕过了 RateLimiter 的连续触发暂停机制
- **原因**：两套独立实现，clients 不知道 RateLimiter 的全局暂停逻辑
- **修复**：clients 的 `_handle_flood_wait` 委托 `self._rate_limiter.handle_flood_wait()`
- **规则**：所有 Telegram 限流处理必须经过 RateLimiter，不允许独立 sleep
