"""APScheduler 定时任务配置"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, delete

from backend.database import AsyncSessionLocal
from backend.models import Industry, NewsSource, FinanceItem, Recipient, SmtpConfig, PushSchedule, SeenArticle
from backend.models.push_log import PushLog
from backend.services.news_crawler import crawl_sources
from backend.services.news_deduplication import deduplicate
from backend.services.news_ranking import score_and_rank
from backend.services.finance_crawler import fetch_quotes
from backend.services.mailer import send_morning_report, send_evening_report

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def run_morning_push(industry_id: int, triggered_by: str = "scheduler") -> None:
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
            db.add(PushLog(
                industry_id=industry_id, push_type="morning", status="skipped",
                error_msg="未配置新闻源", triggered_by=triggered_by,
            ))
            await db.commit()
            return

        # 获取收件人
        recip_result = await db.execute(
            select(Recipient).where(Recipient.industry_id == industry_id)
        )
        recipients = [r.email for r in recip_result.scalars().all()]
        if not recipients:
            logger.info("行业 %s 无收件人，跳过早报", industry.name)
            db.add(PushLog(
                industry_id=industry_id, push_type="morning", status="skipped",
                error_msg="未配置收件人", triggered_by=triggered_by,
            ))
            await db.commit()
            return

        # 获取 SMTP 配置
        smtp_result = await db.execute(select(SmtpConfig).limit(1))
        smtp_cfg = smtp_result.scalar_one_or_none()
        if not smtp_cfg:
            logger.error("未配置 SMTP，跳过早报")
            db.add(PushLog(
                industry_id=industry_id, push_type="morning", status="skipped",
                error_msg="未配置 SMTP", triggered_by=triggered_by,
            ))
            await db.commit()
            return

        source_dicts = [
            {
                "id": s.id,
                "url": s.url,
                "name": s.name,
                "weight": s.weight,
                "keywords": s.keywords,
                "link_selector": s.link_selector,
            }
            for s in sources
        ]

        # 采集 → 去重 → 打分 → 推送 → 写入 SeenArticle（仅推送成功的文章）
        try:
            raw_items = await crawl_sources(source_dicts, db)
            deduped = deduplicate(raw_items)
            top_items = score_and_rank(deduped, top_n=industry.top_n)
            html_snapshot = await send_morning_report(
                smtp_cfg, recipients, industry.name, top_items,
                contact_email=smtp_cfg.contact_email or smtp_cfg.username,
            )
            status = "success" if html_snapshot else "skipped"
            error_msg = None if html_snapshot else "无新增文章（所有文章已在历史记录中）"

            # 推送成功后，将本次推送的文章写入 SeenArticle（避免重复推送）
            if html_snapshot and top_items:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                seen_records = [
                    SeenArticle(
                        url=item.url,
                        title=item.title,
                        source_id=item.source_id,
                        first_seen_at=now,
                    )
                    for item in top_items
                ]
                db.add_all(seen_records)
                logger.info("已将 %d 篇推送文章写入 SeenArticle", len(seen_records))

            db.add(PushLog(
                industry_id=industry_id, push_type="morning", status=status,
                article_count=len(top_items), recipient_count=len(recipients),
                error_msg=error_msg, html_snapshot=html_snapshot, triggered_by=triggered_by,
            ))
            await db.commit()
        except Exception as e:
            logger.exception("行业 %s 早报推送失败: %s", industry.name, e)
            try:
                db.add(PushLog(
                    industry_id=industry_id, push_type="morning", status="failed",
                    recipient_count=len(recipients), error_msg=str(e)[:1000],
                    triggered_by=triggered_by,
                ))
                await db.commit()
            except Exception:
                pass


async def run_evening_push(industry_id: int, triggered_by: str = "scheduler") -> None:
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
            db.add(PushLog(
                industry_id=industry_id, push_type="evening", status="skipped",
                error_msg="未配置金融数据项", triggered_by=triggered_by,
            ))
            await db.commit()
            return

        recip_result = await db.execute(
            select(Recipient).where(Recipient.industry_id == industry_id)
        )
        recipients = [r.email for r in recip_result.scalars().all()]
        if not recipients:
            db.add(PushLog(
                industry_id=industry_id, push_type="evening", status="skipped",
                error_msg="未配置收件人", triggered_by=triggered_by,
            ))
            await db.commit()
            return

        smtp_result = await db.execute(select(SmtpConfig).limit(1))
        smtp_cfg = smtp_result.scalar_one_or_none()
        if not smtp_cfg:
            db.add(PushLog(
                industry_id=industry_id, push_type="evening", status="skipped",
                error_msg="未配置 SMTP", triggered_by=triggered_by,
            ))
            await db.commit()
            return

        items_dicts = [
            {"symbol": fi.symbol, "name": fi.name, "item_type": fi.item_type}
            for fi in finance_items
        ]
        # 提前读取需要在 session 外使用的属性
        industry_name = industry.name
        contact_email = smtp_cfg.contact_email or smtp_cfg.username

        try:
            quotes = await fetch_quotes(items_dicts)
            html_snapshot = await send_evening_report(
                smtp_cfg, recipients, industry_name, quotes,
                contact_email=contact_email,
            )
            status = "success" if html_snapshot else "skipped"
            error_msg = None if html_snapshot else "无金融行情数据"
            db.add(PushLog(
                industry_id=industry_id, push_type="evening", status=status,
                article_count=len(quotes), recipient_count=len(recipients),
                error_msg=error_msg, html_snapshot=html_snapshot, triggered_by=triggered_by,
            ))
            await db.commit()
        except Exception as e:
            logger.exception("行业 %s 晚报推送失败: %s", industry_name, e)
            try:
                db.add(PushLog(
                    industry_id=industry_id, push_type="evening", status="failed",
                    recipient_count=len(recipients), error_msg=str(e)[:1000],
                    triggered_by=triggered_by,
                ))
                await db.commit()
            except Exception:
                pass


async def cleanup_old_records() -> None:
    """每日凌晨清理超过 7 天的 SeenArticle 和 PushLog 记录，控制数据量"""
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    async with AsyncSessionLocal() as db:
        seen_result = await db.execute(
            delete(SeenArticle).where(SeenArticle.first_seen_at < cutoff)
        )
        log_result = await db.execute(
            delete(PushLog).where(PushLog.created_at < cutoff)
        )
        await db.commit()
        logger.info(
            "每日清理完成：删除 %d 条 SeenArticle，%d 条 PushLog（7天前）",
            seen_result.rowcount, log_result.rowcount,
        )


async def reset_seen_articles(industry_id: int) -> int:
    """清空行业新闻源的已见文章记录，返回删除条数"""
    async with AsyncSessionLocal() as db:
        sources_result = await db.execute(
            select(NewsSource.id).where(NewsSource.industry_id == industry_id)
        )
        source_ids = [row[0] for row in sources_result]
        if not source_ids:
            return 0
        result = await db.execute(
            delete(SeenArticle).where(SeenArticle.source_id.in_(source_ids))
        )
        await db.commit()
        return result.rowcount


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

    # 注册每日凌晨 2:00 清理任务（固定，不依赖数据库配置）
    scheduler.add_job(
        cleanup_old_records,
        trigger=CronTrigger(hour=2, minute=0, timezone="Asia/Shanghai"),
        id="daily_cleanup",
        replace_existing=True,
    )
    logger.info("注册每日清理任务: 02:00 (保留 7 天数据)")
