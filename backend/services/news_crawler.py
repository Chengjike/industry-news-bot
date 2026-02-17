"""RSS 新闻采集模块 - 使用 feedparser + httpx"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import httpx

from backend.utils.ssrf_protection import validate_url

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    published_at: datetime
    source_name: str
    source_weight: int
    keywords: Optional[str] = None


async def _fetch_feed(client: httpx.AsyncClient, url: str, source_name: str) -> bytes:
    """带 SSRF 防护的 HTTP 请求"""
    validate_url(url)
    resp = await client.get(url, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def _parse_entry_time(entry) -> Optional[datetime]:
    """从 feedparser entry 解析发布时间，统一转为 UTC aware datetime"""
    import time as time_mod

    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t is None:
        return None
    ts = time_mod.mktime(t)
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _is_yesterday(dt: datetime) -> bool:
    """判断是否是前一天（UTC）"""
    now_utc = datetime.now(timezone.utc)
    yesterday = (now_utc - timedelta(days=1)).date()
    return dt.date() == yesterday


def parse_feed(content: bytes, source_name: str, source_weight: int, keywords: Optional[str]) -> list[NewsItem]:
    """解析 RSS/Atom 内容，只保留昨天的文章"""
    feed = feedparser.parse(content)
    items: list[NewsItem] = []

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        pub_time = _parse_entry_time(entry)
        if pub_time is None or not _is_yesterday(pub_time):
            continue

        items.append(NewsItem(
            title=title,
            url=link,
            published_at=pub_time,
            source_name=source_name,
            source_weight=source_weight,
            keywords=keywords,
        ))

    return items


async def crawl_sources(sources: list[dict]) -> list[NewsItem]:
    """
    并发爬取多个 RSS 源。
    sources: [{"url": ..., "name": ..., "weight": ..., "keywords": ...}]
    """
    all_items: list[NewsItem] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "industry-news-bot/1.0"},
        follow_redirects=True,
    ) as client:
        tasks = [
            _fetch_one(client, s["url"], s["name"], s["weight"], s.get("keywords"))
            for s in sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            logger.warning("爬取 %s 失败: %s", source["name"], result)
        else:
            all_items.extend(result)

    return all_items


async def _fetch_one(
    client: httpx.AsyncClient,
    url: str,
    name: str,
    weight: int,
    keywords: Optional[str],
) -> list[NewsItem]:
    content = await _fetch_feed(client, url, name)
    return parse_feed(content, name, weight, keywords)
