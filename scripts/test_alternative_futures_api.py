#!/usr/bin/env python3
"""测试其他期货 API"""
import sys
sys.path.insert(0, '/app')

import akshare as ak
import pandas as pd

print("=" * 60)
print("测试替代期货 API")
print("=" * 60)

# 测试1: futures_zh_realtime（期货实时行情）
print("\n1. futures_zh_realtime（期货实时行情）")
try:
    df = ak.futures_zh_realtime(symbol="CU")
    print(f"✅ 成功获取数据，共 {len(df)} 条")
    print(f"列名: {list(df.columns)[:10]}")
    if len(df) > 0:
        print(f"前3行:")
        print(df.head(3))
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试2: futures_spot_price（现货价格）
print("\n\n2. futures_spot_price（现货价格）")
try:
    df = ak.futures_spot_price()
    print(f"✅ 成功获取数据，共 {len(df)} 条")
    print(f"列名: {list(df.columns)}")

    # 查找铜铝锂
    for keyword in ["铜", "铝", "锂"]:
        matches = df[df.iloc[:, 0].astype(str).str.contains(keyword, na=False)]
        if not matches.empty:
            print(f"\n包含'{keyword}'的数据:")
            print(matches.head(3))
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试3: futures_display_main_sina（主力合约显示）
print("\n\n3. futures_display_main_sina（主力合约显示）")
try:
    df = ak.futures_display_main_sina()
    print(f"✅ 成功获取数据，共 {len(df)} 条")
    print(f"列名: {list(df.columns)}")

    # 查找铜铝锂
    for keyword in ["铜", "铝", "锂"]:
        matches = df[df.iloc[:, 0].astype(str).str.contains(keyword, na=False)]
        if not matches.empty:
            print(f"\n包含'{keyword}'的数据:")
            print(matches.head(3))
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试4: futures_global_spot_em（全球商品现货-东方财富）
print("\n\n4. futures_global_spot_em（全球商品现货）")
try:
    df = ak.futures_global_spot_em()
    print(f"✅ 成功获取数据，共 {len(df)} 条")
    print(f"列名: {list(df.columns)}")

    # 查找铜铝锂
    for keyword in ["铜", "铝", "锂"]:
        matches = df[df.iloc[:, 0].astype(str).str.contains(keyword, na=False)]
        if not matches.empty:
            print(f"\n包含'{keyword}'的数据:")
            print(matches.head(3))
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n\n" + "=" * 60)
print("测试完成")
print("=" * 60)
