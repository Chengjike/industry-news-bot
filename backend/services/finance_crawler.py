"""金融数据采集模块 - 使用 AKShare"""
import asyncio
import logging
from dataclasses import dataclass
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
        )
    except Exception as e:
        logger.error("获取港股 %s 失败: %s", symbol, e)
        return None


def _fetch_futures(symbol: str, name: str) -> FinanceQuote | None:
    """获取大宗商品/期货现货价格"""
    try:
        # 注意：AKShare 1.18.25+ 使用 symbol 参数而非 subscribe_list
        df: pd.DataFrame = ak.futures_zh_spot(symbol=symbol, market="CF")
        if df.empty:
            logger.warning("大宗商品 %s 未找到", symbol)
            return None
        r = df.iloc[0]
        price = float(r.get("最新价", r.get("price", 0)))
        change_pct = float(r.get("涨跌幅", r.get("change_rate", 0)))

        # 格式化数据：保留2位小数
        return FinanceQuote(
            name=name or symbol,
            symbol=symbol,
            price=round(price, 2),
            change_pct=round(change_pct, 2),
            item_type="futures",
        )
    except Exception as e:
        logger.error("获取大宗商品 %s 失败: %s", symbol, e)
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
