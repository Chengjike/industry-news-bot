"""语义去重模块 - 使用 semhash

若 semhash 模型下载失败（如网络不通），自动降级为标题精确去重，
不会阻断新闻推送流程。
"""
import logging
from semhash import SemHash

from backend.services.news_crawler import NewsItem

logger = logging.getLogger(__name__)


def _exact_deduplicate(items: list[NewsItem]) -> list[NewsItem]:
    """精确去重（按标题字符串完全匹配）"""
    seen: set[str] = set()
    result = []
    for item in items:
        if item.title not in seen:
            result.append(item)
            seen.add(item.title)
    return result


def deduplicate(items: list[NewsItem], threshold: float = 0.85) -> list[NewsItem]:
    """
    基于标题语义去重。
    threshold: 相似度阈值（0~1），越高越严格，默认 0.85。
    返回去重后的列表，保留每组中最早出现的条目。
    若 semhash 模型加载失败，自动降级为精确去重。
    """
    if not items:
        return []

    try:
        titles = [item.title for item in items]
        semhash_obj = SemHash.from_records(records=titles)
        result = semhash_obj.self_deduplicate(threshold=threshold)

        kept_titles = set(result.deduplicated)
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

    except Exception as e:
        logger.warning("semhash 语义去重失败（%s），降级为精确去重", e)
        return _exact_deduplicate(items)
