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


def _industry_keyword_match(text: str, keyword_str: str) -> bool:
    """
    行业关键词过滤（OR 语义）：
    - +词 列表中至少命中一个 → 通过
    - !词 命中任意一个 → 过滤
    - 无 +词 配置 → 通过（仅做排除过滤）
    """
    text_lower = text.lower()
    must_have, must_not, _ = _parse_keywords(keyword_str)

    # 排除词：命中任意一个则过滤
    for word in must_not:
        if word in text_lower:
            return False

    # 必须词：OR 语义，至少命中一个
    if must_have:
        return any(word in text_lower for word in must_have)

    return True


def score_and_rank(items: list[NewsItem], top_n: int = 10,
                   industry_keywords: str | None = None) -> list[NewsItem]:
    """
    对新闻列表打分、过滤、排序，返回 Top N 条。

    综合评分 = 时效性(0.4) + 来源权重(0.3) + 关键词(0.3)

    industry_keywords: 行业级关键词（OR 语义），对标题+摘要做硬过滤。
    """
    scored: list[tuple[float, NewsItem]] = []
    filtered_count = 0

    for item in items:
        # 行业关键词硬过滤（标题 + 摘要，OR 语义）
        if industry_keywords:
            combined_text = (item.title or "") + " " + (item.summary or "")
            if not _industry_keyword_match(combined_text, industry_keywords):
                filtered_count += 1
                continue

        kw_score = _keyword_score(item.title, item.keywords)
        if kw_score is None:
            filtered_count += 1
            continue

        t_score = _timeliness_score(item.published_at)
        w_score = _weight_score(item.source_weight)

        total = t_score * 0.4 + w_score * 0.3 + kw_score * 0.3
        scored.append((total, item))

    if filtered_count:
        import logging
        logging.getLogger(__name__).info(
            "score_and_rank: 共 %d 条，过滤 %d 条，剩余 %d 条，取 Top %d",
            len(items), filtered_count, len(scored), top_n
        )

    # 取 Top N（heapq.nlargest 高效）
    top = heapq.nlargest(top_n, scored, key=lambda x: x[0])
    return [item for _, item in top]
