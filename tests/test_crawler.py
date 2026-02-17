"""单元测试 - RSS 新闻采集（时间过滤）"""
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from backend.services.news_crawler import parse_feed, _is_yesterday, _parse_entry_time


class TestIsYesterday:
    def test_yesterday_is_true(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        assert _is_yesterday(yesterday) is True

    def test_today_is_false(self):
        today = datetime.now(timezone.utc)
        assert _is_yesterday(today) is False

    def test_two_days_ago_is_false(self):
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        assert _is_yesterday(two_days_ago) is False


class TestParseFeed:
    def _make_rss(self, title: str, link: str, pub_time: datetime) -> bytes:
        """构造简单的 RSS XML"""
        ts = pub_time.strftime("%a, %d %b %Y %H:%M:%S +0000")
        return f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <pubDate>{ts}</pubDate>
    </item>
  </channel>
</rss>""".encode()

    def test_keeps_yesterday_article(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        content = self._make_rss("昨天的新闻", "https://example.com/1", yesterday)
        items = parse_feed(content, "测试源", 5, None)
        assert len(items) == 1
        assert items[0].title == "昨天的新闻"

    def test_skips_today_article(self):
        today = datetime.now(timezone.utc)
        content = self._make_rss("今天的新闻", "https://example.com/2", today)
        items = parse_feed(content, "测试源", 5, None)
        assert len(items) == 0

    def test_skips_old_article(self):
        old = datetime.now(timezone.utc) - timedelta(days=5)
        content = self._make_rss("旧新闻", "https://example.com/3", old)
        items = parse_feed(content, "测试源", 5, None)
        assert len(items) == 0

    def test_news_item_fields(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        content = self._make_rss("测试标题", "https://example.com/news", yesterday)
        items = parse_feed(content, "来源名称", 7, "+关键词")
        assert len(items) == 1
        item = items[0]
        assert item.title == "测试标题"
        assert item.url == "https://example.com/news"
        assert item.source_name == "来源名称"
        assert item.source_weight == 7
        assert item.keywords == "+关键词"

    def test_skips_entry_without_title(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ts = yesterday.strftime("%a, %d %b %Y %H:%M:%S +0000")
        content = f"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><link>https://example.com</link><pubDate>{ts}</pubDate></item>
</channel></rss>""".encode()
        assert parse_feed(content, "源", 5, None) == []

    def test_skips_entry_without_link(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ts = yesterday.strftime("%a, %d %b %Y %H:%M:%S +0000")
        content = f"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>有标题无链接</title><pubDate>{ts}</pubDate></item>
</channel></rss>""".encode()
        assert parse_feed(content, "源", 5, None) == []
