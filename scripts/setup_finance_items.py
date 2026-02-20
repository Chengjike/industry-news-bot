#!/usr/bin/env python3
"""
配置金融数据项
为新能源行业添加 A 股和期货金融数据项
"""
import sys
import os
sys.path.insert(0, '/app')

import asyncio
from backend.database import get_db
from backend.models import Industry, FinanceItem

async def main():
    async for db in get_db():
        # 查询行业
        from sqlalchemy import select
        result = await db.execute(select(Industry))
        industries = result.scalars().all()

        if not industries:
            print("❌ 未找到任何行业，请先创建行业")
            return 1

        print("现有行业：")
        for ind in industries:
            print(f"  {ind.id}. {ind.name}")

        # 选择第一个行业（通常是新能源或能源）
        industry = industries[0]
        industry_id = industry.id
        print(f"\n将为行业「{industry.name}」(ID={industry_id}) 添加金融数据项\n")

        # 定义金融数据项
        finance_items = [
            # A 股
            {"symbol": "300274", "name": "阳光电源", "item_type": "stock", "industry_id": industry_id},
            {"symbol": "300750", "name": "宁德时代", "item_type": "stock", "industry_id": industry_id},
            {"symbol": "601012", "name": "隆基绿能", "item_type": "stock", "industry_id": industry_id},

            # 期货（2026年2月，使用2505/2506合约）
            {"symbol": "cu2505", "name": "沪铜主力", "item_type": "futures", "industry_id": industry_id},
            {"symbol": "al2505", "name": "沪铝主力", "item_type": "futures", "industry_id": industry_id},
            {"symbol": "lc2506", "name": "碳酸锂主力", "item_type": "futures", "industry_id": industry_id},
        ]

        # 检查是否已存在
        existing_result = await db.execute(
            select(FinanceItem).where(FinanceItem.industry_id == industry_id)
        )
        existing = existing_result.scalars().all()

        if existing:
            print(f"已存在 {len(existing)} 个金融数据项，将全部删除后重新添加")
            for item in existing:
                await db.delete(item)
            await db.commit()

        # 添加新的金融数据项
        print(f"添加 {len(finance_items)} 个金融数据项：\n")
        for item_data in finance_items:
            item = FinanceItem(**item_data)
            db.add(item)
            item_type_cn = "股票" if item.item_type == "stock" else "期货"
            print(f"  ✅ {item.name}（{item.symbol}）[{item_type_cn}]")

        await db.commit()

        print(f"\n✅ 配置完成！共添加 {len(finance_items)} 个金融数据项")

        # 验证
        verify_result = await db.execute(
            select(FinanceItem).where(FinanceItem.industry_id == industry_id)
        )
        verify_items = verify_result.scalars().all()
        print(f"\n验证：数据库中现有 {len(verify_items)} 个金融数据项")

        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
