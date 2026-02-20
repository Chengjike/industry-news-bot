#!/usr/bin/env python3
"""
ECS 上验证金融数据获取
验证修复后的 finance_crawler.py 是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from backend.services.finance_crawler import fetch_quotes

# 测试数据项
test_items = [
    # A 股
    {"symbol": "300274", "name": "阳光电源", "item_type": "stock"},
    {"symbol": "300750", "name": "宁德时代", "item_type": "stock"},
    {"symbol": "601012", "name": "隆基绿能", "item_type": "stock"},

    # 期货（2026年2月，需要使用当前主力合约）
    {"symbol": "cu2505", "name": "沪铜主力", "item_type": "futures"},
    {"symbol": "al2505", "name": "沪铝主力", "item_type": "futures"},
    {"symbol": "lc2506", "name": "碳酸锂主力", "item_type": "futures"},
]

async def main():
    print("=" * 60)
    print("金融数据获取验证测试")
    print("=" * 60)

    print("\n测试数据项：")
    for item in test_items:
        print(f"  - {item['name']}（{item['symbol']}）[{item['item_type']}]")

    print("\n开始获取数据...\n")

    quotes = await fetch_quotes(test_items)

    print(f"\n成功获取 {len(quotes)}/{len(test_items)} 个数据项\n")

    if quotes:
        print("=" * 60)
        print("获取结果：")
        print("=" * 60)

        for quote in quotes:
            sign = "+" if quote.change_pct >= 0 else ""
            print(f"\n【{quote.name}】（{quote.symbol}）")
            print(f"  类型：{'股票' if quote.item_type == 'stock' else '期货'}")
            print(f"  最新价：{quote.price:.2f}")
            print(f"  涨跌幅：{sign}{quote.change_pct:.2f}%")
    else:
        print("❌ 未能获取任何数据")
        return 1

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
