"""APScheduler 定时任务配置"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Industry, NewsSource, FinanceItem, Recipient, SmtpConfig, PushSchedule
from backend.services.news_crawler import crawl_sources
from backend.services.news_deduplication import deduplicate
from backend.services.news_ranking import score_and_rank
from backend.services.finance_crawler import fetch_quotes
from backend.services.mailer import send_morning_report, send_evening_report

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def run_morning_push(industry_id: int) -> None:
    """早报推送任务"""
    async with AsyncSessionLocal() as db:
        industry = await db.get(Industry, industry_id)
        if not industry:
            return

        # 获取新闻源
        sources_result = await db.execute(
            select(NewsSource).where(NewsSource.industry_id == industry_id)
        )
        sources = sources_result.scalars().all()
        if not sources:
            logger.info("行业 %s 无新闻源，跳过早报", industry.name)
            return

        # 获取收件人
        recip_result = await db.execute(
            select(Recipient).where(Recipient.industry_id == industry_id)
        )
        recipients = [r.email for r in recip_result.scalars().all()]
        if not recipients:
            logger.info("行业 %s 无收件人，跳过早报", industry.name)
            return

        # 获取 SMTP 配置
        smtp_result = await db.execute(select(SmtpConfig).limit(1))
        smtp_cfg = smtp_result.scalar_one_or_none()
        if not smtp_cfg:
            logger.error("未配置 SMTP，跳过早报")
            return

        source_dicts = [
            {"url": s.url, "name": s.name, "weight": s.weight, "keywords": s.keywords}
            for s in sources
        ]

    # 采集 → 去重 → 打分
    try:
        raw_items = await crawl_sources(source_dicts)
        deduped = deduplicate(raw_items)
        top_items = score_and_rank(deduped, top_n=industry.top_n)
        await send_morning_report(
            smtp_cfg, recipients, industry.name, top_items,
            contact_email=smtp_cfg.contact_email or smtp_cfg.username,
        )
    except Exception as e:
        logger.exception("行业 %s 早报推送失败: %s", industry.name, e)


async def run_evening_push(industry_id: int) -> None:
    """晚报推送任务"""
    async with AsyncSessionLocal() as db:
        industry = await db.get(Industry, industry_id)
        if not industry:
            return

        fi_result = await db.execute(
            select(FinanceItem).where(FinanceItem.industry_id == industry_id)
        )
        finance_items = fi_result.scalars().all()
        if not finance_items:
            logger.info("行业 %s 无金融项，跳过晚报", industry.name)
            return

        recip_result = await db.execute(
            select(Recipient).where(Recipient.industry_id == industry_id)
        )
        recipients = [r.email for r in recip_result.scalars().all()]
        if not recipients:
            return

        smtp_result = await db.execute(select(SmtpConfig).limit(1))
        smtp_cfg = smtp_result.scalar_one_or_none()
        if not smtp_cfg:
            return

        items_dicts = [
            {"symbol": fi.symbol, "name": fi.name, "item_type": fi.item_type}
            for fi in finance_items
        ]

    try:
        quotes = await fetch_quotes(items_dicts)
        await send_evening_report(
            smtp_cfg, recipients, industry.name, quotes,
            contact_email=smtp_cfg.contact_email or smtp_cfg.username,
        )
    except Exception as e:
        logger.exception("行业 %s 晚报推送失败: %s", industry.name, e)


async def reload_schedules() -> None:
    """从数据库读取推送计划，注册定时任务（应用启动时调用）"""
    scheduler.remove_all_jobs()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PushSchedule).where(PushSchedule.enabled == True)  # noqa: E712
        )
        schedules = result.scalars().all()

    for sched in schedules:
        job_id = f"{sched.push_type}_{sched.industry_id}"
        fn = run_morning_push if sched.push_type == "morning" else run_evening_push

        scheduler.add_job(
            fn,
            trigger=CronTrigger(hour=sched.hour, minute=sched.minute, timezone="Asia/Shanghai"),
            args=[sched.industry_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info("注册定时任务: %s %02d:%02d (行业ID=%d)",
                    sched.push_type, sched.hour, sched.minute, sched.industry_id)

    if not schedules:
        logger.info("数据库中无推送计划，使用默认时间（09:00 早报，18:00 晚报）")
