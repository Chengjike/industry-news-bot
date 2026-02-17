"""新闻打分排序模块（参考 TrendRadar 思路的加权评分）"""
import heapq
import re
from datetime import datetime, timezone

from backend.services.news_crawler import NewsItem


def _timeliness_score(published_at: datetime) -> float:
    """
    时效性分：距发布时间越近分越高。
    最近 1h → 1.0，超过 24h → 0.0，线性衰减。
    """
    now = datetime.now(timezone.utc)
    age_hours = (now - published_at).total_seconds() / 3600
    return max(0.0, 1.0 - age_hours / 24.0)


def _parse_keywords(keyword_str: str) -> tuple[list[str], list[str], list[str]]:
    """
    解析关键词字符串，返回 (必须词, 排除词, 加分词)。
    +word  → 必须包含
    !word  → 必须排除
    word   → 命中加分
    """
    must_have: list[str] = []
    must_not: list[str] = []
    bonus: list[str] = []

    for token in keyword_str.split():
        token = token.strip()
        if not token:
            continue
        if token.startswith("+"):
            must_have.append(token[1:].lower())
        elif token.startswith("!"):
            must_not.append(token[1:].lower())
        else:
            bonus.append(token.lower())

    return must_have, must_not, bonus


def _keyword_score(title: str, keyword_str: str | None) -> float | None:
    """
    关键词匹配分（0.0~1.0）。
    返回 None 表示被过滤（+词未命中 或 !词命中）。
    """
    if not keyword_str:
        return 0.5  # 无关键词配置，给中性分

    title_lower = title.lower()
    must_have, must_not, bonus = _parse_keywords(keyword_str)

    # 必须包含 +词，否则过滤
    for word in must_have:
        if word not in title_lower:
            return None

    # 必须不包含 !词，否则过滤
    for word in must_not:
        if word in title_lower:
            return None

    # 加分词命中率
    if bonus:
        hits = sum(1 for w in bonus if w in title_lower)
        return hits / len(bonus)

    return 0.5


def _weight_score(weight: int) -> float:
    """来源权重分（1~10 → 0.1~1.0）"""
    return max(0.1, min(1.0, weight / 10.0))


def score_and_rank(items: list[NewsItem], top_n: int = 10) -> list[NewsItem]:
    """
    对新闻列表打分、过滤、排序，返回 Top N 条。

    综合评分 = 时效性(0.4) + 来源权重(0.3) + 关键词(0.3)
    """
    scored: list[tuple[float, NewsItem]] = []

    for item in items:
        kw_score = _keyword_score(item.title, item.keywords)
        if kw_score is None:
            # 被关键词规则过滤
            continue

        t_score = _timeliness_score(item.published_at)
        w_score = _weight_score(item.source_weight)

        total = t_score * 0.4 + w_score * 0.3 + kw_score * 0.3
        scored.append((total, item))

    # 取 Top N（heapq.nlargest 高效）
    top = heapq.nlargest(top_n, scored, key=lambda x: x[0])
    return [item for _, item in top]
