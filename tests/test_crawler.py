"""单元测试 - 网页新闻采集（HTML 解析 + 新文章识别）"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.news_crawler import NewsItem, _extract_links


# ────────────────────────────────────────
# _extract_links：测试链接提取逻辑
# ────────────────────────────────────────

class TestExtractLinks:
    BASE_URL = "https://news.example.com"

    def _html(self, links: list[tuple[str, str]], wrapper_class: str = "") -> str:
        """构造包含指定链接的 HTML 片段"""
        items = "".join(
            f'<a href="{href}">{title}</a>' for title, href in links
        )
        if wrapper_class:
            return f'<div class="{wrapper_class}">{items}</div>'
        return f"<body>{items}</body>"

    def test_extracts_absolute_urls(self):
        html = self._html([("中美贸易摩擦最新进展", "https://news.example.com/article/123")])
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1
        assert result[0][1] == "https://news.example.com/article/123"

    def test_converts_relative_urls(self):
        html = self._html([("科技行业周报", "/tech/2024/weekly")])
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1
        assert result[0][1] == "https://news.example.com/tech/2024/weekly"

    def test_skips_anchor_links(self):
        html = self._html([("锚点", "#section1"), ("正常新闻", "/news/article-001")])
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1
        assert result[0][0] == "正常新闻"

    def test_skips_javascript_links(self):
        html = self._html([
            ("JS链接", "javascript:void(0)"),
            ("真实文章", "/news/real-article"),
        ])
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1
        assert result[0][0] == "真实文章"

    def test_skips_short_path_navigation_links(self):
        """路径短于5字符的链接（如 /、/en）属于导航链接，应被过滤"""
        html = self._html([
            ("首页", "/"),
            ("EN", "/en"),
            ("正式新闻文章", "/news/2024/article-detail-page"),
        ])
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1
        assert result[0][0] == "正式新闻文章"

    def test_skips_short_title_button_links(self):
        """标题文字少于4字符的链接（如"更多"）是按钮，应被过滤"""
        html = self._html([
            ("更多", "/news/more"),
            ("国际原油价格大幅下跌", "/news/oil-price-drop"),
        ])
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1
        assert result[0][0] == "国际原油价格大幅下跌"

    def test_deduplicates_same_url(self):
        """同一 URL 出现多次只保留第一个"""
        html = '<a href="/news/article-001">第一次出现的标题</a><a href="/news/article-001">重复出现</a>'
        result = _extract_links(html, self.BASE_URL, "a")
        assert len(result) == 1

    def test_css_selector_filters_links(self):
        """指定 CSS 选择器时只提取匹配的链接"""
        html = '''
        <div class="news-list">
            <a href="/news/article-in-list">新闻列表里的文章标题</a>
        </div>
        <nav>
            <a href="/nav/about-page">导航栏关于我们链接</a>
        </nav>
        '''
        result = _extract_links(html, self.BASE_URL, ".news-list a")
        assert len(result) == 1
        assert result[0][0] == "新闻列表里的文章标题"

    def test_container_selector_finds_nested_anchors(self):
        """选择器命中容器元素时，自动在容器内查找 <a>"""
        html = '''
        <ul class="article-list">
            <li><a href="/news/article-alpha">量化宽松政策对市场的影响分析</a></li>
            <li><a href="/news/article-beta">新能源汽车销量创历史新高</a></li>
        </ul>
        '''
        result = _extract_links(html, self.BASE_URL, ".article-list li")
        assert len(result) == 2


# ────────────────────────────────────────
# _crawl_one_source：测试新/旧文章识别
# ────────────────────────────────────────

class TestCrawlOneSource:
    @pytest.mark.asyncio
    async def test_returns_only_new_articles(self):
        """已在 SeenArticle 表里的 URL 不应再次返回"""
        from backend.services.news_crawler import _crawl_one_source

        html = '''
        <a href="https://news.example.com/new-article-today">今天的全新文章标题内容</a>
        <a href="https://news.example.com/old-article-seen">昨天已推送过的旧文章</a>
        '''
        source = {
            "id": 1, "url": "https://news.example.com",
            "name": "测试源", "weight": 5,
            "keywords": None, "link_selector": "a",
        }

        # Mock DB session：已见过 old-article
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([("https://news.example.com/old-article-seen",)])
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add_all = MagicMock()
        mock_db.commit = AsyncMock()

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.encoding = "utf-8"
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("backend.services.news_crawler.validate_url"):
            items = await _crawl_one_source(mock_client, mock_db, source)

        assert len(items) == 1
        assert "new-article-today" in items[0].url

    @pytest.mark.asyncio
    async def test_saves_new_articles_to_db(self):
        """新文章应写入 SeenArticle 表"""
        from backend.services.news_crawler import _crawl_one_source

        html = '<a href="https://news.example.com/brand-new-article-2024">全新未见过的文章标题</a>'
        source = {
            "id": 1, "url": "https://news.example.com",
            "name": "测试源", "weight": 5,
            "keywords": None, "link_selector": "a",
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))  # 没有已见记录
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add_all = MagicMock()
        mock_db.commit = AsyncMock()

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.encoding = "utf-8"
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("backend.services.news_crawler.validate_url"):
            items = await _crawl_one_source(mock_client, mock_db, source)

        assert len(items) == 1
        assert items[0].source_id == 1  # source_id 应正确传递
        # SeenArticle 写入已移至 scheduler.py（推送成功后写入），此处不再调用 db.add_all
        mock_db.add_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_new_articles(self):
        """全部链接都已见过时，返回空列表"""
        from backend.services.news_crawler import _crawl_one_source

        html = '<a href="https://news.example.com/old-known-article">已知的旧文章标题内容</a>'
        source = {
            "id": 1, "url": "https://news.example.com",
            "name": "测试源", "weight": 5,
            "keywords": None, "link_selector": "a",
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([("https://news.example.com/old-known-article",)])
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add_all = MagicMock()
        mock_db.commit = AsyncMock()

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.encoding = "utf-8"
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("backend.services.news_crawler.validate_url"):
            items = await _crawl_one_source(mock_client, mock_db, source)

        assert items == []
        mock_db.add_all.assert_not_called()
