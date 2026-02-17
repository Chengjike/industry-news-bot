"""网页新闻采集模块

抓取流程：
1. httpx 请求新闻列表页（支持 SSRF 防护）
2. BeautifulSoup 按 CSS 选择器提取文章链接
3. 对比数据库 SeenArticle 表，找出新增文章
4. 将新文章 URL 写入 SeenArticle，避免下次重复推送
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


async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """带 SSRF 防护的 HTTP 请求，返回 HTML 字符串"""
    validate_url(url)
    resp = await client.get(url, timeout=20.0, follow_redirects=True)
    resp.raise_for_status()
    # 处理 GBK/GB2312 等中文编码
    if resp.encoding and resp.encoding.upper() not in ("UTF-8", "UTF8"):
        return resp.content.decode(resp.encoding, errors="replace")
    return resp.text


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
    3. 批量查询 SeenArticle 表，过滤掉已见过的 URL
    4. 将新 URL 写入 SeenArticle
    5. 返回新文章
    """
    url = source["url"]
    name = source["name"]
    weight = source["weight"]
    keywords = source.get("keywords")
    selector = source.get("link_selector") or "a"

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

    now = datetime.now(timezone.utc)
    new_items: list[NewsItem] = []
    new_records: list[SeenArticle] = []

    for title, article_url in candidate_links:
        if article_url in seen_urls:
            continue
        new_items.append(NewsItem(
            title=title,
            url=article_url,
            published_at=now,
            source_name=name,
            source_weight=weight,
            keywords=keywords,
        ))
        new_records.append(SeenArticle(
            url=article_url,
            title=title,
            source_id=source.get("id"),
            first_seen_at=now,
        ))

    if new_records:
        db.add_all(new_records)
        await db.commit()
        logger.info(
            "源 [%s]：发现 %d 篇新文章（共提取 %d 篇候选）",
            name, len(new_items), len(candidate_links),
        )

    return new_items


async def crawl_sources(sources: list[dict], db: AsyncSession) -> list[NewsItem]:
    """
    并发爬取多个新闻网站，汇总返回今日新增文章。

    sources 列表中每条记录包含：
      id, url, name, weight, keywords, link_selector
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
