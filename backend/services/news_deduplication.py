"""语义去重模块 - 使用 semhash"""
import logging
from semhash import SemHash

from backend.services.news_crawler import NewsItem

logger = logging.getLogger(__name__)


def deduplicate(items: list[NewsItem], threshold: float = 0.85) -> list[NewsItem]:
    """
    基于标题语义去重。
    threshold: 相似度阈值（0~1），越高越严格，默认 0.85。
    返回去重后的列表，保留每组中最早出现的条目。
    """
    if not items:
        return []

    titles = [item.title for item in items]
    semhash = SemHash.from_records(records=titles)
    result = semhash.self_deduplicate(threshold=threshold)

    # deduplicated 是保留下来的标题列表（顺序与原始一致）
    kept_titles = set(result.deduplicated)

    # 按原始顺序保留，每个标题只取第一次出现的 item
    seen: set[str] = set()
    deduped: list[NewsItem] = []
    for item in items:
        if item.title in kept_titles and item.title not in seen:
            deduped.append(item)
            seen.add(item.title)

    removed = len(items) - len(deduped)
    if removed:
        logger.info("语义去重：移除 %d 条重复新闻，剩余 %d 条", removed, len(deduped))

    return deduped
