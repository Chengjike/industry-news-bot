"""AI 摘要生成模块 - 使用 Claude API 生成高质量新闻摘要"""
import logging
from typing import Optional

from anthropic import AsyncAnthropic
from bs4 import BeautifulSoup

from backend.config import settings

logger = logging.getLogger(__name__)


def _extract_article_text(html: str) -> str:
    """
    从 HTML 中提取文章正文（完整版）。

    策略：
    1. 查找主内容区域（article/main/.content 等）
    2. 移除无关标签（script/style/nav/footer/aside/header）
    3. 提取所有段落文本，过滤导航、版权等无关内容
    4. 返回完整正文（用于 AI 理解）
    """
    soup = BeautifulSoup(html, "html.parser")

    # 查找主内容区域（扩展选择器列表，提高匹配率）
    content_area = None
    for selector in [
        "article", "main",
        ".content", ".article-content", ".post-content",
        "#content", "#article", "#main",
        ".detail", ".text", ".entry-content",
        "[class*='article']", "[class*='content']", "[id*='article']",
    ]:
        content_area = soup.select_one(selector)
        if content_area:
            logger.debug(f"找到主内容区域: {selector}")
            break

    if not content_area:
        content_area = soup.find("body") or soup
        logger.debug("未找到主内容区域，使用整个 body")

    # 移除无关标签（扩展列表，更彻底清理）
    for tag in content_area([
        "script", "style", "nav", "footer", "aside", "header",
        "iframe", "form", "button", "noscript",
        # 常见广告和导航容器
        ".nav", ".navigation", ".menu", ".sidebar",
        ".ad", ".advertisement", ".banner",
        ".related", ".recommend", ".comment",
    ]):
        tag.decompose()

    # 提取所有段落
    paragraphs = content_area.find_all("p", recursive=True)
    text_parts = []

    skip_keywords = [
        "版权所有", "转载请注明", "相关阅读", "点击进入", "网站地图",
        "关于我们", "English", "联系我们", "免责声明", "隐私政策",
        "订阅", "分享到", "责任编辑", "来源：", "编辑：", "审核：",
        "更多精彩", "扫一扫", "关注公众号", "下载APP",
    ]

    for p in paragraphs:
        p_text = p.get_text(strip=True)

        # 过滤过短段落
        if len(p_text) < 15:
            continue

        # 过滤导航、版权等无关段落
        if any(keyword in p_text for keyword in skip_keywords):
            continue

        # 过滤纯链接文本
        if p_text.count("|") >= 3 or p_text.count(">>") >= 2:
            continue

        # 过滤纯数字、纯符号
        if p_text.replace(" ", "").replace(".", "").replace(",", "").isdigit():
            continue

        text_parts.append(p_text)

    # 拼接段落，保留段落分隔
    full_text = "\n\n".join(text_parts)
    logger.debug(f"提取到 {len(text_parts)} 个段落，总长度 {len(full_text)} 字")
    return full_text


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
        # 提取完整正文
        full_text = _extract_article_text(html)

        # 过滤过短的文本（可能是导航页或错误页）
        if len(full_text) < 200:
            logger.debug("文章正文过短（%d 字），跳过 AI 摘要", len(full_text))
            return ""

        # 限制输入长度（避免超过 API 限制和成本）
        # Claude Haiku 支持 200K tokens，约 15 万汉字
        # 为平衡质量和成本，限制在 2 万字（约 20 篇新闻的总和）
        original_length = len(full_text)
        if len(full_text) > 20000:
            # 取前 10000 字 + 后 10000 字（保留开头和结尾的关键信息）
            full_text = full_text[:10000] + "\n\n[中间部分省略]\n\n" + full_text[-10000:]
            logger.debug("文章过长（%d 字），截取前后各 10000 字", original_length)

        logger.debug("提取正文长度: %d 字，准备调用 Claude API 生成摘要", len(full_text))

        # 调用 Claude API 生成摘要
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        prompt = f"""请仔细阅读以下新闻文章的完整内容，然后生成一段精炼的摘要。

要求：
1. 摘要必须准确概括文章的核心内容、关键事实和重要信息
2. 不要只是复制文章开头，要理解全文后提炼要点
3. 语言简洁流畅，适合邮件推送阅读
4. 严格控制在 {max_chars} 个汉字以内
5. 直接输出摘要文本，不要添加"摘要："、"本文"等前缀

文章正文：
{full_text}"""

        message = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=400,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        summary = message.content[0].text.strip()

        # 移除可能的前缀
        for prefix in ["摘要：", "摘要:", "本文", "文章", "新闻"]:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()

        # 确保不超过字数限制
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        logger.info("AI 摘要生成成功，原文 %d 字 → 摘要 %d 字", original_length, len(summary))
        return summary

    except Exception as e:
        logger.warning("AI 摘要生成失败: %s", e)
        return ""
