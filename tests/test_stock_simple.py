#!/usr/bin/env python3
"""简化版金融数据验证 - 仅测试 A 股"""
import sys
import os
sys.path.insert(0, '/app')

import asyncio
from backend.services.finance_crawler import fetch_quotes

async def main():
    print("测试 A 股数据获取...")

    items = [
        {"symbol": "300274", "name": "阳光电源", "item_type": "stock"},
        {"symbol": "300750", "name": "宁德时代", "item_type": "stock"},
        {"symbol": "601012", "name": "隆基绿能", "item_type": "stock"},
    ]

    try:
        quotes = await fetch_quotes(items)
        print(f"\n成功获取 {len(quotes)} 个数据项\n")

        for quote in quotes:
            sign = "+" if quote.change_pct >= 0 else ""
            print(f"{quote.name}（{quote.symbol}）: {quote.price:.2f} ({sign}{quote.change_pct:.2f}%)")

        return 0 if quotes else 1
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
