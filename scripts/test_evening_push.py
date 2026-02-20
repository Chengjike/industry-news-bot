#!/usr/bin/env python3
"""
测试晚报推送功能
手动触发一次晚报推送，验证金融数据获取和邮件发送
"""
import sys
sys.path.insert(0, '/app')

import asyncio
from backend.tasks.scheduler import run_evening_push

async def main():
    print("=" * 60)
    print("测试晚报推送功能")
    print("=" * 60)

    # 行业 ID = 1（新能源行业）
    industry_id = 1

    print(f"\n手动触发行业 ID={industry_id} 的晚报推送...\n")

    try:
        await run_evening_push(industry_id, triggered_by="manual_test")
        print("\n✅ 晚报推送完成")
        print("请检查邮箱是否收到邮件")
        return 0
    except Exception as e:
        print(f"\n❌ 晚报推送失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
