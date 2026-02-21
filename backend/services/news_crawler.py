"""网页新闻采集模块

抓取流程：
1. httpx 请求新闻列表页（支持 SSRF 防护）
2. BeautifulSoup 按 CSS 选择器提取文章链接
3. 对比数据库 SeenArticle 表，找出新增文章
4. 批量请求文章详情页，提取前 140 字作为摘要
5. 将新文章 URL 写入 SeenArticle，避免下次重复推送
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.seen_article import SeenArticle
from backend.utils.ssrf_protection import validate_url

logger = logging.getLogger(__name__)

# 模拟浏览器 User-Agent，避免被部分网站屏蔽
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass
class NewsItem:
    title: str
    url: str
    published_at: datetime   # 抓取时间（无法从网页稳定提取发布时间时用抓取时间代替）
    source_name: str
    source_weight: int
    keywords: Optional[str] = None
    summary: str = ""        # 文章摘要（不超过 140 字）
    source_id: Optional[int] = None  # 来源 ID，用于推送后写入 SeenArticle


def _extract_links(html: str, base_url: str, selector: str) -> list[tuple[str, str]]:
    """
    从 HTML 页面中提取文章链接。

    selector: CSS 选择器，指向 <a> 标签，例如：
      - 'a'               提取所有链接（默认）
      - 'a.article-title' 只提取 class="article-title" 的链接
      - '.news-list a'    提取 class="news-list" 容器内所有链接

    返回 [(title, absolute_url), ...]，已做以下过滤：
    - 跳过锚点链接（#...）和 javascript: 链接
    - 跳过 URL 路径过短（<5字符）的导航类链接
    - 跳过标题文字过短（<4字符）的按钮类链接（如"更多"）
    - 去重
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    tags = soup.select(selector)
    # 如果选择器选中的不是 <a>，则在其内部继续查找 <a>
    a_tags: list = []
    for tag in tags:
        if tag.name == "a":
            a_tags.append(tag)
        else:
            a_tags.extend(tag.find_all("a"))

    for tag in a_tags:
        href = tag.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if len(parsed.path) < 5:  # 过滤 /、/about 等短路径导航链接
            continue
        if abs_url in seen:
            continue
        seen.add(abs_url)

        # 标题优先取链接文字，其次取 title 属性
        title = tag.get_text(strip=True) or tag.get("title", "").strip()
        if not title or len(title) < 4:
            continue

        results.append((title, abs_url))

    return results


async def _fetch_page(client: httpx.AsyncClient, url: str, retries: int = 3) -> str:
    """带 SSRF 防护和指数退避重试的 HTTP 请求，返回 HTML 字符串

    网络超时或服务器 5xx 错误时自动重试（最多 retries 次），
    重试间隔：1s → 2s → 4s（指数退避）。
    4xx 客户端错误不重试，直接抛出。
    """
    validate_url(url)
    last_exc: Exception = RuntimeError("未知错误")
    for attempt in range(retries):
        try:
            resp = await client.get(url, timeout=20.0, follow_redirects=True)
            resp.raise_for_status()
            if resp.encoding and resp.encoding.upper() not in ("UTF-8", "UTF8"):
                return resp.content.decode(resp.encoding, errors="replace")
            return resp.text
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exc = e
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning("请求超时/网络错误（第%d次），%ds后重试: %s - %s", attempt + 1, wait, url, e)
                await asyncio.sleep(wait)
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and attempt < retries - 1:
                last_exc = e
                wait = 2 ** attempt
                logger.warning("服务器错误 %d（第%d次），%ds后重试: %s", e.response.status_code, attempt + 1, wait, url)
                await asyncio.sleep(wait)
            else:
                raise
    raise last_exc


def _extract_summary(html: str, max_chars: int = 140) -> str:
    """
    从文章详情页 HTML 提取摘要（前 140 字正文）。

    策略：
    1. 优先从 article/main/.content 等容器中查找段落
    2. 过滤导航、版权声明等无关内容
    3. 拼接段落文本直到达到字数限制
    4. 返回截断后的文本（不超过 max_chars 字符）
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 优先查找主内容区域（在删除标签之前查找）
        content_area = None
        for selector in ["article", "main", ".content", ".article-content", "#content", ".post-content"]:
            content_area = soup.select_one(selector)
            if content_area:
                break

        # 如果找不到主内容区，就从整个 body 中提取
        if not content_area:
            content_area = soup.find("body") or soup

        # 移除无关标签（在选定区域内删除）
        for tag in content_area(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()

        # 提取所有段落文本（递归查找）
        paragraphs = content_area.find_all("p", recursive=True)
        text_parts: list[str] = []
        total_len = 0

        for p in paragraphs:
            p_text = p.get_text(strip=True)
            # 过滤过短、纯符号、导航/版权声明等无关段落
            if len(p_text) < 10:
                continue
            # 扩展过滤关键词：导航、版权、功能链接等
            skip_keywords = [
                "版权所有", "转载请注明", "相关阅读", "点击进入",
                "网站地图", "关于我们", "English", "联系我们",
                "免责声明", "隐私政策", "订阅", "分享到",
            ]
            if any(keyword in p_text for keyword in skip_keywords):
                continue
            # 过滤纯链接文本（连续多个 | 分隔符）
            if p_text.count("|") >= 3:
                continue

            text_parts.append(p_text)
            total_len += len(p_text)
            if total_len >= max_chars:
                break

        summary = "".join(text_parts)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary
    except Exception as e:
        logger.debug("摘要提取失败: %s", e)
        return ""


async def _fetch_article_summary(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
    max_chars: int = 140,
    source_language: str = "zh",
    original_title: str = ""
) -> tuple[str, str]:
    """
    请求文章详情页并提取摘要。

    优先使用 AI 生成高质量摘要（需配置 DASHSCOPE_API_KEY），
    失败时降级为简单文本提取。

    使用 Semaphore 限制并发数，避免同时发起过多请求。
    失败时返回 (original_title, "")，不阻塞主流程。

    Args:
        source_language: 源语言（zh=中文, en=英文）
        original_title: 原始标题（英文源时用于翻译）

    Returns:
        (标题, 摘要) 元组。中文源返回 (original_title, 摘要)，英文源返回 (中文标题, 中文摘要)
    """
    async with semaphore:
        try:
            html = await _fetch_page(client, url)

            # 优先尝试 AI 摘要生成
            from backend.services.ai_summary import generate_summary_with_ai
            title, summary = await generate_summary_with_ai(
                html, max_chars, source_language, original_title
            )

            # AI 失败时降级为简单提取
            if not summary:
                summary = _extract_summary(html, max_chars)

            return (title, summary)
        except Exception as e:
            logger.debug("获取摘要失败 [%s]: %s", url, e)
            return (original_title, "")


async def _crawl_one_source(
    client: httpx.AsyncClient,
    db: AsyncSession,
    source: dict,
) -> list[NewsItem]:
    """
    爬取单个新闻网站，返回本次新增（之前未见过）的文章列表。

    流程：
    1. 请求新闻列表页
    2. 用 CSS 选择器提取候选链接
    3. 批量查询 SeenArticle 表，过滤掉已推送过的 URL
    4. 并发请求新文章详情页，提取摘要
    5. 返回新文章（含摘要）；SeenArticle 写入由调用方在推送成功后完成
    """
    url = source["url"]
    name = source["name"]
    weight = source["weight"]
    keywords = source.get("keywords")
    selector = source.get("link_selector") or "a"
    language = source.get("language", "zh")

    html = await _fetch_page(client, url)
    candidate_links = _extract_links(html, url, selector)

    if not candidate_links:
        logger.info("源 [%s] 未提取到任何链接（selector=%s）", name, selector)
        return []

    # 批量查询哪些 URL 已见过
    candidate_urls = [u for _, u in candidate_links]
    existing_result = await db.execute(
        select(SeenArticle.url).where(SeenArticle.url.in_(candidate_urls))
    )
    seen_urls = {row[0] for row in existing_result}

    # 筛选出新文章
    new_articles: list[tuple[str, str]] = [
        (title, article_url)
        for title, article_url in candidate_links
        if article_url not in seen_urls
    ]

    if not new_articles:
        return []

    # 并发请求新文章详情页提取摘要（限制并发数为 5，避免触发反爬）
    semaphore = asyncio.Semaphore(5)
    summary_tasks = [
        _fetch_article_summary(client, article_url, semaphore, source_language=language, original_title=title)
        for title, article_url in new_articles
    ]
    results = await asyncio.gather(*summary_tasks)

    # 构建 NewsItem（不再在此处写入 SeenArticle，由调用方在推送成功后写入）
    now = datetime.now(timezone.utc)
    new_items: list[NewsItem] = []

    for (original_title, article_url), (final_title, summary) in zip(new_articles, results):
        new_items.append(NewsItem(
            title=final_title,  # 英文源时为翻译后的中文标题
            url=article_url,
            published_at=now,
            source_name=name,
            source_weight=weight,
            keywords=keywords,
            summary=summary,
            source_id=source.get("id"),
        ))

    logger.info(
        "源 [%s]：发现 %d 篇新文章（共提取 %d 篇候选）",
        name, len(new_items), len(candidate_links),
    )

    return new_items


async def crawl_sources(sources: list[dict], db: AsyncSession) -> list[NewsItem]:
    """
    并发爬取多个新闻网站，汇总返回今日新增文章。

    sources 列表中每条记录包含：
      id, url, name, weight, keywords, link_selector, language
    db: 需要传入 AsyncSession，用于读写 SeenArticle 表
    """
    all_items: list[NewsItem] = []

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        tasks = [_crawl_one_source(client, db, s) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            logger.warning("爬取 [%s] 失败: %s", source["name"], result)
        else:
            all_items.extend(result)

    return all_items
