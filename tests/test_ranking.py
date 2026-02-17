"""单元测试 - 新闻打分排序"""
import pytest
from datetime import datetime, timedelta, timezone

from backend.services.news_crawler import NewsItem
from backend.services.news_ranking import (
    _parse_keywords,
    _keyword_score,
    _timeliness_score,
    _weight_score,
    score_and_rank,
)


def make_item(title: str, hours_ago: float = 2, weight: int = 5, keywords: str | None = None) -> NewsItem:
    pub = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return NewsItem(
        title=title,
        url="https://example.com",
        published_at=pub,
        source_name="测试源",
        source_weight=weight,
        keywords=keywords,
    )


# ── _parse_keywords ──────────────────────────────────────
class TestParseKeywords:
    def test_empty(self):
        must, must_not, bonus = _parse_keywords("")
        assert must == [] and must_not == [] and bonus == []

    def test_must_have(self):
        must, must_not, bonus = _parse_keywords("+原油 +期货")
        assert must == ["原油", "期货"]
        assert must_not == []
        assert bonus == []

    def test_must_not(self):
        must, must_not, bonus = _parse_keywords("!广告 !推广")
        assert must_not == ["广告", "推广"]

    def test_bonus(self):
        must, must_not, bonus = _parse_keywords("原油 价格")
        assert bonus == ["原油", "价格"]

    def test_mixed(self):
        must, must_not, bonus = _parse_keywords("+原油 !广告 价格 涨跌")
        assert must == ["原油"]
        assert must_not == ["广告"]
        assert bonus == ["价格", "涨跌"]


# ── _keyword_score ────────────────────────────────────────
class TestKeywordScore:
    def test_no_keywords_returns_neutral(self):
        assert _keyword_score("任意标题", None) == 0.5

    def test_must_have_present(self):
        score = _keyword_score("原油价格上涨", "+原油")
        assert score is not None and score >= 0

    def test_must_have_missing_filters(self):
        assert _keyword_score("苹果公司新闻", "+原油") is None

    def test_must_not_present_filters(self):
        assert _keyword_score("这是广告推广内容", "!广告") is None

    def test_must_not_absent_passes(self):
        score = _keyword_score("原油价格上涨分析", "!广告")
        assert score is not None

    def test_bonus_full_match(self):
        score = _keyword_score("原油价格涨跌分析", "原油 价格 涨跌")
        assert score == pytest.approx(1.0)

    def test_bonus_partial_match(self):
        score = _keyword_score("原油分析", "原油 价格 涨跌")
        assert score == pytest.approx(1 / 3)

    def test_bonus_no_match(self):
        score = _keyword_score("科技公司新闻", "原油 价格")
        assert score == pytest.approx(0.0)


# ── _timeliness_score ─────────────────────────────────────
class TestTimelinessScore:
    def test_very_recent(self):
        pub = datetime.now(timezone.utc) - timedelta(minutes=30)
        score = _timeliness_score(pub)
        assert score > 0.97

    def test_12_hours_ago(self):
        pub = datetime.now(timezone.utc) - timedelta(hours=12)
        score = _timeliness_score(pub)
        assert 0.49 < score < 0.51

    def test_24_hours_ago(self):
        pub = datetime.now(timezone.utc) - timedelta(hours=24)
        score = _timeliness_score(pub)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_older_than_24h_clamps_to_zero(self):
        pub = datetime.now(timezone.utc) - timedelta(hours=48)
        assert _timeliness_score(pub) == 0.0


# ── _weight_score ─────────────────────────────────────────
class TestWeightScore:
    def test_max_weight(self):
        assert _weight_score(10) == pytest.approx(1.0)

    def test_mid_weight(self):
        assert _weight_score(5) == pytest.approx(0.5)

    def test_min_weight(self):
        assert _weight_score(1) == pytest.approx(0.1)

    def test_zero_clamps_to_min(self):
        assert _weight_score(0) == pytest.approx(0.1)


# ── score_and_rank ────────────────────────────────────────
class TestScoreAndRank:
    def test_returns_top_n(self):
        items = [make_item(f"新闻{i}") for i in range(20)]
        result = score_and_rank(items, top_n=5)
        assert len(result) == 5

    def test_filters_must_not(self):
        items = [
            make_item("广告推广内容", keywords="!广告"),
            make_item("正常行业新闻", keywords="!广告"),
        ]
        result = score_and_rank(items, top_n=10)
        assert len(result) == 1
        assert result[0].title == "正常行业新闻"

    def test_higher_weight_ranks_first(self):
        items = [
            make_item("同等时效新闻A", hours_ago=2, weight=2),
            make_item("同等时效新闻B", hours_ago=2, weight=9),
        ]
        result = score_and_rank(items, top_n=2)
        # weight=9 的应排在前面
        assert result[0].title == "同等时效新闻B"

    def test_fresher_news_ranks_first(self):
        items = [
            make_item("旧新闻", hours_ago=20, weight=5),
            make_item("新新闻", hours_ago=1, weight=5),
        ]
        result = score_and_rank(items, top_n=2)
        assert result[0].title == "新新闻"

    def test_empty_input(self):
        assert score_and_rank([], top_n=5) == []

    def test_fewer_items_than_top_n(self):
        items = [make_item("唯一新闻")]
        result = score_and_rank(items, top_n=10)
        assert len(result) == 1
