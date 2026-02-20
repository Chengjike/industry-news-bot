"""金融数据采集模块 - 使用 AKShare"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FinanceQuote:
    name: str
    symbol: str
    price: float
    change_pct: float   # 涨跌幅，单位 %
    item_type: str      # "stock" | "futures"
    timestamp: datetime  # 数据获取时间


def _fetch_stock_a(symbol: str, name: str) -> FinanceQuote | None:
    """获取 A 股行情"""
    try:
        df: pd.DataFrame = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == symbol]
        if row.empty:
            logger.warning("A股 %s 未找到", symbol)
            return None
        r = row.iloc[0]

        # 格式化数据：保留2位小数
        return FinanceQuote(
            name=name or str(r.get("名称", symbol)),
            symbol=symbol,
            price=round(float(r.get("最新价", 0)), 2),
            change_pct=round(float(r.get("涨跌幅", 0)), 2),
            item_type="stock",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("获取A股 %s 失败: %s", symbol, e)
        return None


def _fetch_stock_hk(symbol: str, name: str) -> FinanceQuote | None:
    """获取港股行情"""
    try:
        df: pd.DataFrame = ak.stock_hk_spot_em()
        row = df[df["代码"] == symbol]
        if row.empty:
            logger.warning("港股 %s 未找到", symbol)
            return None
        r = row.iloc[0]

        # 格式化数据：保留2位小数
        return FinanceQuote(
            name=name or str(r.get("名称", symbol)),
            symbol=symbol,
            price=round(float(r.get("最新价", 0)), 2),
            change_pct=round(float(r.get("涨跌幅", 0)), 2),
            item_type="stock",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("获取港股 %s 失败: %s", symbol, e)
        return None


def _fetch_futures(symbol: str, name: str) -> FinanceQuote | None:
    """
    获取大宗商品/期货现货价格

    注意：由于 AKShare 的 futures_zh_spot() API 存在 Bug，改用 futures_global_spot_em() 获取全球现货数据。

    商品代码映射：
    - cu2505/沪铜 -> 综合铜 (LCPT/LMECu/etc)
    - al2505/沪铝 -> 综合铝 (LALT/LMEAl/etc)
    - lc2506/碳酸锂 -> 碳酸锂/氢氧化锂相关品种
    """
    try:
        # 获取全球商品现货数据
        df: pd.DataFrame = ak.futures_global_spot_em()

        if df.empty:
            logger.warning("futures_global_spot_em() 返回空数据")
            return None

        # 商品名称关键词映射
        keyword_map = {
            "cu": ["铜", "Copper", "Cu"],
            "al": ["铝", "Aluminum", "Al"],
            "lc": ["锂", "碳酸锂", "氢氧化锂", "Lithium"],
        }

        # 提取商品类型（如 cu2505 -> cu）
        commodity_type = symbol[:2].lower() if len(symbol) >= 2 else ""

        # 查找匹配的商品
        matched_row = None

        # 方法1：直接按代码匹配（如 LCPT, LALT）
        code_matches = df[df["代码"] == symbol.upper()]
        if not code_matches.empty:
            matched_row = code_matches.iloc[0]

        # 方法2：按名称关键词模糊匹配
        if matched_row is None and commodity_type in keyword_map:
            keywords = keyword_map[commodity_type]
            for keyword in keywords:
                name_matches = df[df["名称"].str.contains(keyword, na=False, case=False)]
                if not name_matches.empty:
                    # 优先选择名称包含"综合"的（通常是主力品种）
                    priority_matches = name_matches[name_matches["名称"].str.contains("综合", na=False)]
                    if not priority_matches.empty:
                        matched_row = priority_matches.iloc[0]
                    else:
                        matched_row = name_matches.iloc[0]
                    break

        if matched_row is None:
            logger.warning("大宗商品 %s (%s) 未找到匹配数据", symbol, name)
            return None

        # 提取价格和涨跌幅
        price = float(matched_row.get("最新价", 0))
        change_pct_str = str(matched_row.get("涨跌幅", "0"))

        # 处理涨跌幅（可能带 % 符号）
        if "%" in change_pct_str:
            change_pct = float(change_pct_str.replace("%", ""))
        else:
            change_pct = float(change_pct_str)

        # 检查价格有效性
        if price == 0 or pd.isna(price):
            logger.warning("大宗商品 %s 价格无效: %s", symbol, price)
            return None

        # 使用匹配到的商品名称（更准确）
        actual_name = str(matched_row.get("名称", name))

        # 格式化数据：保留2位小数
        return FinanceQuote(
            name=name or actual_name,  # 优先使用用户配置的名称
            symbol=symbol,
            price=round(price, 2),
            change_pct=round(change_pct, 2),
            item_type="futures",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("获取大宗商品 %s 失败: %s", symbol, e)
        import traceback
        logger.error(traceback.format_exc())
        return None


async def fetch_quotes(items: list[dict]) -> list[FinanceQuote]:
    """
    并发获取多个金融数据项行情。
    items: [{"symbol": ..., "name": ..., "item_type": "stock"|"futures"}]
    """
    loop = asyncio.get_event_loop()
    tasks = []
    for item in items:
        symbol = item["symbol"]
        name = item.get("name", symbol)
        item_type = item.get("item_type", "stock")

        if item_type == "futures":
            tasks.append(loop.run_in_executor(None, _fetch_futures, symbol, name))
        elif item_type == "stock_hk":
            tasks.append(loop.run_in_executor(None, _fetch_stock_hk, symbol, name))
        else:
            tasks.append(loop.run_in_executor(None, _fetch_stock_a, symbol, name))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    quotes: list[FinanceQuote] = []
    for r in results:
        if isinstance(r, Exception):
            logger.error("获取行情异常: %s", r)
        elif r is not None:
            quotes.append(r)
    return quotes
