"""URL/文章内容总结插件

接收 URL，提取正文内容，通过 LLM 生成摘要。
支持网页文章提取（readability + BeautifulSoup）。
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from src.core.exceptions import LLMError
from src.llm.base_provider import ChatMessage
from src.llm.prompt_templates import CONTENT_SUMMARY
from src.plugins.plugin_base import PluginBase

# 内容提取的最大字符数（避免超出 LLM 上下文限制）
MAX_CONTENT_LENGTH = 8000
# HTTP 请求超时（秒）
FETCH_TIMEOUT = 15


class ContentSummarizerPlugin(PluginBase):
    """内容总结插件 — 提取 URL 正文并生成 AI 摘要"""

    @property
    def name(self) -> str:
        return "ai_summary.content_summarizer"

    @property
    def description(self) -> str:
        return "URL/文章内容 AI 总结"

    async def setup(self) -> None:
        """订阅内容总结事件"""
        cfg = self.get_plugin_config()
        self._language = cfg.get("language", "zh-CN")

        await self.event_bus.subscribe("summarize_content", self._handle_summarize)
        self.logger.info("内容总结插件已启动")

    async def teardown(self) -> None:
        """取消事件订阅"""
        await self.event_bus.unsubscribe("summarize_content", self._handle_summarize)

    async def _handle_summarize(self, **kwargs: Any) -> None:
        """处理内容总结请求

        事件参数:
            url: 目标 URL（必需）
            reply_to_chat: 回复发送到哪个聊天（必需）
        """
        url = kwargs.get("url", "")
        reply_to = kwargs.get("reply_to_chat")
        if not url or not reply_to:
            return

        try:
            # 1. 获取并提取正文
            content = await self._fetch_content(url)
            if not content:
                await self.client.send_message(reply_to, "无法提取该 URL 的内容。")
                return

            # 2. 截断过长内容
            if len(content) > MAX_CONTENT_LENGTH:
                content = content[:MAX_CONTENT_LENGTH] + "\n...(内容已截断)"

            # 3. 调用 LLM 总结
            summary = await self._generate_summary(content)

            # 4. 发送结果
            header = f"📄 内容总结：\n🔗 {url}\n\n"
            await self.client.send_message(reply_to, header + summary)
            self.logger.info("已发送内容总结: %s", url)

        except LLMError as e:
            await self.client.send_message(reply_to, f"总结生成失败: {e}")
            self.logger.error("LLM 调用失败: %s", e)
        except Exception as e:
            await self.client.send_message(reply_to, "内容提取或总结失败，请稍后重试。")
            self.logger.error("内容总结异常: %s", e)

    async def _fetch_content(self, url: str) -> str:
        """获取 URL 内容并提取正文（含 SSRF 防护）"""
        # SSRF 防护：验证 URL 格式且目标非内网地址
        from src.utils.validators import is_safe_url
        if not is_safe_url(url):
            self.logger.warning("URL 安全检查未通过（内网或无效地址）: %s", url)
            return ""

        try:
            async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
                html = await self._fetch_with_safe_redirects(client, url, is_safe_url)
        except httpx.RequestError as e:
            self.logger.warning("获取 URL 失败: %s — %s", url, e)
            return ""

        return self._extract_text(html)

    async def _fetch_with_safe_redirects(
        self,
        client: httpx.AsyncClient,
        url: str,
        is_safe_url,
        max_redirects: int = 5,
    ) -> str:
        """Fetch content while validating every redirect hop."""
        current_url = url

        for _ in range(max_redirects + 1):
            response = await client.get(current_url, follow_redirects=False)

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise httpx.RequestError("redirect response missing Location header")

                next_url = urljoin(current_url, location)
                if not is_safe_url(next_url):
                    self.logger.warning("Redirect target blocked by SSRF guard: %s", next_url)
                    return ""

                current_url = next_url
                continue

            response.raise_for_status()
            return response.text

        raise httpx.RequestError(f"too many redirects while fetching {url}")

    @staticmethod
    def _extract_text(html: str) -> str:
        """从 HTML 提取正文文本

        优先使用 readability 提取主体内容，回退到 BeautifulSoup。
        """
        # 尝试使用 readability 提取
        try:
            from readability import Document
            doc = Document(html)
            summary_html = doc.summary()
        except ImportError:
            summary_html = html
        except Exception:
            summary_html = html

        # 用 BeautifulSoup 提取纯文本
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(summary_html, "html.parser")
            # 移除脚本和样式
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            # 极简 HTML 标签剥离
            import re
            return re.sub(r"<[^>]+>", "", summary_html).strip()

    async def _generate_summary(self, content: str) -> str:
        """调用 LLM 生成内容总结"""
        if not self.llm:
            raise LLMError("LLM 管理器未配置，无法生成总结")

        provider = self.llm.get_provider()
        system_msg = CONTENT_SUMMARY.system.format(language=self._language)
        user_msg = CONTENT_SUMMARY.user.format(content=content)
        response = await provider.chat([
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=user_msg),
        ])
        return response.content
