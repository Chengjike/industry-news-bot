#!/usr/bin/env python3
"""
修复晚报推送时间错误的数据迁移脚本
将晚报推送时间从上午改为下午（6→18，9→18）
"""
import os
import sys
import asyncio
from sqlalchemy import update
from sqlalchemy.future import select

# 设置环境变量（避免配置验证失败）
os.environ.update({
    "SECRET_KEY": "dummy-secret-key-for-fix-script",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "dummy-password",
    "FERNET_KEY": "dummy-fernet-key",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "LOG_LEVEL": "INFO",
})

# 添加项目路径
sys.path.insert(0, '/home/CJK-Claude/workspace/industry-news-bot')

from backend.database import AsyncSessionLocal
from backend.models.push_schedule import PushSchedule


async def fix_evening_schedules():
    """修复晚报推送时间错误"""
    async with AsyncSessionLocal() as db:
        # 查询所有晚报推送计划
        result = await db.execute(
            select(PushSchedule).where(PushSchedule.push_type == "evening")
        )
        evening_schedules = result.scalars().all()

        fixed_count = 0
        for schedule in evening_schedules:
            # 检查时间是否在上午（hour < 12）
            if schedule.hour < 12:
                original_time = f"{schedule.hour:02d}:{schedule.minute:02d}"
                schedule.hour = 18  # 改为下午6点
                schedule.minute = 0  # 整点
                fixed_count += 1
                print(f"修复: 行业ID={schedule.industry_id} 晚报时间从 {original_time} 改为 18:00")

        if fixed_count > 0:
            await db.commit()
            print(f"\n✅ 共修复 {fixed_count} 条晚报推送计划")
        else:
            print("✅ 没有需要修复的晚报推送计划")

        # 显示修复后的结果
        result = await db.execute(
            select(PushSchedule).where(PushSchedule.push_type == "evening")
        )
        evening_schedules = result.scalars().all()

        print("\n修复后的晚报推送计划:")
        for schedule in evening_schedules:
            print(f"  行业ID={schedule.industry_id}: {schedule.hour:02d}:{schedule.minute:02d}")

        return fixed_count


async def main():
    print("=" * 60)
    print("晚报推送时间修复脚本")
    print("=" * 60)

    try:
        fixed = await fix_evening_schedules()
        if fixed == 0:
            print("\n✅ 所有晚报推送时间已正确配置")
        return 0
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)