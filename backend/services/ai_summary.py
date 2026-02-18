"""AI 摘要生成模块 - 使用 Claude API 生成高质量新闻摘要"""
import logging
from typing import Optional

from anthropic import AsyncAnthropic
from bs4 import BeautifulSoup

from backend.config import settings

logger = logging.getLogger(__name__)


async def generate_summary_with_ai(html: str, max_chars: int = 140) -> str:
    """
    使用 Claude API 阅读全文后生成高质量摘要。

    Args:
        html: 文章详情页 HTML
        max_chars: 摘要最大字数（默认 140 字）

    Returns:
        AI 生成的摘要文本，失败时返回空字符串
    """
    if not settings.anthropic_api_key:
        logger.debug("未配置 ANTHROPIC_API_KEY，跳过 AI 摘要生成")
        return ""

    try:
        # 提取正文文本
        soup = BeautifulSoup(html, "html.parser")

        # 移除无关标签
        for tag in soup(["script", "style", "nav", "footer", "aside", "header", "iframe"]):
            tag.decompose()

        # 查找主内容区域
        content_area = None
        for selector in ["article", "main", ".content", ".article-content", "#content", ".post-content"]:
            content_area = soup.select_one(selector)
            if content_area:
                break

        if not content_area:
            content_area = soup.find("body") or soup

        # 提取纯文本
        full_text = content_area.get_text(separator="\n", strip=True)

        # 过滤过短的文本（可能是导航页或错误页）
        if len(full_text) < 100:
            logger.debug("文章正文过短（%d 字），跳过 AI 摘要", len(full_text))
            return ""

        # 限制输入长度（避免超过 API 限制，取前 3000 字）
        if len(full_text) > 3000:
            full_text = full_text[:3000] + "..."

        # 调用 Claude API 生成摘要
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        prompt = f"""请阅读以下新闻文章，生成一段不超过 {max_chars} 字的摘要。

要求：
1. 准确概括文章核心内容和关键信息
2. 语言简洁流畅，适合邮件推送
3. 不超过 {max_chars} 个汉字
4. 直接输出摘要文本，不要添加"摘要："等前缀

文章正文：
{full_text}"""

        message = await client.messages.create(
            model="claude-3-5-haiku-20241022",  # 使用 Haiku 模型（快速且经济）
            max_tokens=300,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        summary = message.content[0].text.strip()

        # 确保不超过字数限制
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        logger.debug("AI 摘要生成成功，长度: %d 字", len(summary))
        return summary

    except Exception as e:
        logger.warning("AI 摘要生成失败: %s", e)
        return ""
