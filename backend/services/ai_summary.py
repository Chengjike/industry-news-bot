"""AI 摘要生成模块 - 使用阿里云通义千问 API 生成高质量新闻摘要"""
import logging
from typing import Optional

from bs4 import BeautifulSoup
import dashscope
from dashscope import Generation

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


async def generate_summary_with_ai(
    html: str,
    max_chars: int = 140,
    source_language: str = "zh",
    original_title: str = ""
) -> tuple[str, str]:
    """
    使用阿里云通义千问 API 阅读全文后生成高质量摘要。

    Args:
        html: 文章详情页 HTML
        max_chars: 摘要最大字数（默认 140 字）
        source_language: 源语言（zh=中文, en=英文）
        original_title: 原始标题（英文源时用于翻译）

    Returns:
        (标题, 摘要) 元组。中文源返回 (original_title, 摘要)，英文源返回 (中文标题, 中文摘要)
        失败时返回 (original_title, "")
    """
    if not settings.dashscope_api_key:
        logger.debug("未配置 DASHSCOPE_API_KEY，跳过 AI 摘要生成")
        return (original_title, "")

    try:
        # 提取完整正文
        full_text = _extract_article_text(html)

        # 过滤过短的文本（可能是导航页或错误页）
        # 英文文章通常较短，降低阈值到 50 字符
        min_length = 50 if source_language == "en" else 100
        if len(full_text) < min_length:
            logger.debug("文章正文过短（%d 字符），跳过 AI 摘要", len(full_text))
            return (original_title, "")

        # 限制输入长度（避免超过 API 限制和成本）
        # 通义千问 qwen-turbo 支持 8K tokens，约 6000 汉字
        # 为平衡质量和成本，限制在 5000 字
        original_length = len(full_text)
        if len(full_text) > 5000:
            # 取前 2500 字 + 后 2500 字（保留开头和结尾的关键信息）
            full_text = full_text[:2500] + "\n\n[中间部分省略]\n\n" + full_text[-2500:]
            logger.debug("文章过长（%d 字），截取前后各 2500 字", original_length)

        logger.debug("提取正文长度: %d 字，准备调用通义千问 API 生成摘要", len(full_text))

        # 配置 API Key
        dashscope.api_key = settings.dashscope_api_key

        # 根据源语言构建不同的 prompt
        if source_language == "en":
            prompt = f"""你是一个专业的新闻翻译和摘要助手。请完成以下任务：

任务 1：将英文标题翻译为中文
- 翻译要准确、简洁，符合中文新闻标题习惯
- 去除多余的前缀（如 "News"、日期等）
- 保持专业术语的准确性

任务 2：阅读英文文章全文，生成中文摘要
- 摘要必须准确概括文章核心内容、关键事实和重要信息
- 语言简洁流畅，适合邮件推送阅读
- 严格控制在 {max_chars} 个汉字以内

输出格式要求：
第一行：中文标题（不要包含 "News"、日期等前缀）
第二行：中文摘要
用 | 符号分隔

英文标题：
{original_title}

英文文章正文：
{full_text}"""
        else:
            prompt = f"""请仔细阅读以下新闻文章的完整内容，然后生成一段精炼的摘要。

要求：
1. 摘要必须准确概括文章的核心内容、关键事实和重要信息
2. 不要只是复制文章开头，要理解全文后提炼要点
3. 语言简洁流畅，适合邮件推送阅读
4. 严格控制在 {max_chars} 个汉字以内
5. 直接输出摘要文本，不要添加"摘要："、"本文"等前缀

文章正文：
{full_text}"""

        # 调用通义千问 API（同步调用，dashscope 暂不支持异步）
        response = Generation.call(
            model='qwen-turbo',
            prompt=prompt,
            max_tokens=400,
            temperature=0.3,
        )

        if response.status_code != 200:
            logger.warning("通义千问 API 调用失败: %s", response.message)
            return (original_title, "")

        result_text = response.output.text.strip()

        # 解析结果
        if source_language == "en":
            # 英文源：解析 "中文标题|中文摘要" 格式
            if "|" in result_text:
                parts = result_text.split("|", 1)
                translated_title = parts[0].strip()
                summary = parts[1].strip()
            else:
                # 如果没有 | 分隔符，尝试按行分割
                lines = [line.strip() for line in result_text.split("\n") if line.strip()]
                if len(lines) >= 2:
                    translated_title = lines[0]
                    summary = lines[1]
                elif len(lines) == 1:
                    # 只有一行，可能是标题或摘要
                    # 如果长度 > 30，视为摘要；否则视为标题
                    if len(lines[0]) > 30:
                        translated_title = original_title
                        summary = lines[0]
                    else:
                        translated_title = lines[0]
                        summary = ""
                else:
                    # 完全解析失败
                    logger.warning("AI 返回格式异常，无法解析标题和摘要: %s", result_text[:100])
                    translated_title = original_title
                    summary = ""

            # 清理标题中的多余前缀（包括分类标签）
            prefixes_to_remove = [
                "News", "news", "新闻", "标题：", "标题:",
                "Coal", "Electricity", "Natural Gas", "Oil", "Renewables",
                "Bioenergy", "Nuclear", "Hydrogen", "Energy Efficiency"
            ]
            for prefix in prefixes_to_remove:
                if translated_title.startswith(prefix):
                    translated_title = translated_title[len(prefix):].strip()
                    break  # 只移除第一个匹配的前缀

            # 确保不超过字数限制
            if len(summary) > max_chars:
                summary = summary[:max_chars] + "..."

            logger.info("英文文章翻译+摘要成功，原文 %d 字 → 标题: %s, 摘要 %d 字",
                       original_length, translated_title[:30], len(summary))
            return (translated_title, summary)
        else:
            # 中文源：直接返回摘要
            summary = result_text

            # 移除可能的前缀
            for prefix in ["摘要：", "摘要:", "本文", "文章", "新闻"]:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()

            # 确保不超过字数限制
            if len(summary) > max_chars:
                summary = summary[:max_chars] + "..."

            logger.info("AI 摘要生成成功，原文 %d 字 → 摘要 %d 字", original_length, len(summary))
            return (original_title, summary)

    except Exception as e:
        logger.warning("AI 摘要生成失败: %s", e)
        return (original_title, "")
