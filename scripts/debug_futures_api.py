#!/usr/bin/env python3
"""
调试期货 API 返回的数据结构
"""
import sys
sys.path.insert(0, '/app')

import akshare as ak
import pandas as pd

print("测试期货 API 数据结构\n")

test_symbols = ["cu2505", "al2505", "lc2506"]

for symbol in test_symbols:
    print(f"=" * 60)
    print(f"测试: {symbol}")
    print("=" * 60)

    try:
        df = ak.futures_zh_spot(symbol=symbol, market="CF")

        if df.empty:
            print(f"❌ 返回空数据\n")
            continue

        print(f"✅ 成功获取数据")
        print(f"数据行数: {len(df)}")
        print(f"数据列: {list(df.columns)}")
        print(f"\n前5行数据:")
        print(df.head())

        if len(df) > 0:
            print(f"\n第一行数据:")
            print(df.iloc[0].to_dict())

    except Exception as e:
        print(f"❌ 获取失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n")
